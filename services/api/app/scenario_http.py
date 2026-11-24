"""Owner-scoped persistence for immutable counterfactual comparison sets."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict
from datetime import UTC, datetime
from typing import Annotated, Literal
from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, Header, Query, Response
from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert

from app.auth import VerifiedPrincipal, get_verified_principal
from app.counterfactual import Comparison
from app.database import Database
from app.evidence_http import CompareSavedLead, ScenarioPreviewDTO, build_comparison
from app.leads_contract import validate_idempotency_key
from app.leads_http import LeadDTO
from app.leads_store import LeadStore, _payload
from app.models import Lead, ProductProfile, ScenarioComparison
from app.profile_http import ProfileStateDTO
from app.profile_store import ProfileStore
from app.workspace_http import ApiFailure, ErrorDTO, get_workspace_store
from app.workspace_store import IdempotencyConflict, WorkspaceNotFound, WorkspaceStore


class SavedComparisonDTO(BaseModel):
    id: UUID
    workspace_id: UUID
    lead_id: UUID
    lead_version: int
    confirmed_profile_revision: int
    created_at: datetime
    source_url: str
    source_excerpt: str
    source_recorded_at: datetime
    source_origin: Literal["user_provided"] = "user_provided"
    persisted_comparison: Literal[True] = True
    live_source_verified: Literal[False] = False
    comparison: Comparison


class SavedComparisonListDTO(BaseModel):
    items: list[SavedComparisonDTO]


def _dto(row: ScenarioComparison) -> SavedComparisonDTO:
    preview = ScenarioPreviewDTO.model_validate(row.result)
    # The saved computation and immutable baseline must match the relational owner.
    sources = row.snapshot.get("sources")
    if (
        preview.workspace_id != row.workspace_id
        or preview.lead_id != row.lead_id
        or preview.lead_version != row.lead_version
        or preview.confirmed_profile_revision != row.profile_revision
        or not isinstance(sources, list)
        or len(sources) != 1
        or not isinstance(sources[0], dict)
        or sources[0].get("id") != str(row.lead_id)
        or sources[0].get("url") != preview.source_url
        or sources[0].get("origin") != "user_provided"
        or not isinstance(sources[0].get("excerpt"), str)
    ):
        raise RuntimeError("Inconsistent stored scenario comparison")
    return SavedComparisonDTO(
        id=row.id,
        workspace_id=row.workspace_id,
        lead_id=row.lead_id,
        lead_version=row.lead_version,
        confirmed_profile_revision=row.profile_revision,
        created_at=row.created_at.astimezone(UTC),
        source_url=preview.source_url,
        source_excerpt=sources[0]["excerpt"],
        source_recorded_at=preview.source_recorded_at,
        comparison=preview.comparison,
    )


class ScenarioStore:
    def __init__(self, database: Database) -> None:
        self.database = database

    def save(
        self,
        principal: VerifiedPrincipal,
        workspace_id: UUID,
        lead_id: UUID,
        payload: CompareSavedLead,
        key: str,
    ) -> tuple[SavedComparisonDTO, bool]:
        try:
            validate_idempotency_key(key)
        except ValueError as exc:
            raise ApiFailure("VALIDATION_FAILED", 422, "Invalid idempotency key.") from exc
        canonical = json.dumps(
            {"lead_id": str(lead_id), "request": payload.model_dump(mode="json")},
            sort_keys=True,
            separators=(",", ":"),
        )
        fingerprint = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        with self.database.transaction(principal) as session:
            ProfileStore._owned(session, principal, workspace_id)
            existing = session.scalar(
                select(ScenarioComparison).where(
                    ScenarioComparison.workspace_id == workspace_id,
                    ScenarioComparison.create_key == key,
                )
            )
            if existing is not None:
                if existing.create_fingerprint != fingerprint:
                    raise IdempotencyConflict()
                return _dto(existing), True
            # Lock current profile and lead before reading the versions used by the computation.
            profile = session.scalar(
                select(ProductProfile)
                .where(ProductProfile.workspace_id == workspace_id)
                .with_for_update()
            )
            lead = session.scalar(
                select(Lead)
                .where(
                    Lead.workspace_id == workspace_id,
                    Lead.id == lead_id,
                    Lead.archived_at.is_(None),
                )
                .with_for_update()
            )
            if lead is None:
                raise WorkspaceNotFound()
            # A concurrent identical request may have saved while we waited on the locks.
            existing = session.scalar(
                select(ScenarioComparison).where(
                    ScenarioComparison.workspace_id == workspace_id,
                    ScenarioComparison.create_key == key,
                )
            )
            if existing is not None:
                if existing.create_fingerprint != fingerprint:
                    raise IdempotencyConflict()
                return _dto(existing), True
            snapshot, preview = build_comparison(
                workspace_id,
                LeadDTO.model_validate(_payload(lead)),
                ProfileStateDTO.model_validate(ProfileStore._state(session, workspace_id, profile)),
                payload,
            )
            inserted = session.execute(
                insert(ScenarioComparison)
                .values(
                    id=uuid4(),
                    workspace_id=workspace_id,
                    lead_id=lead_id,
                    lead_version=lead.version,
                    profile_revision=snapshot.profile_revision,
                    create_key=key,
                    create_fingerprint=fingerprint,
                    snapshot=jsonable_encoder(asdict(snapshot)),
                    result=preview.model_dump(mode="json"),
                )
                .on_conflict_do_nothing(
                    index_elements=[
                        ScenarioComparison.workspace_id,
                        ScenarioComparison.create_key,
                    ]
                )
                .returning(ScenarioComparison.id)
            ).scalar_one_or_none()
            if inserted is None:
                existing = session.scalar(
                    select(ScenarioComparison).where(
                        ScenarioComparison.workspace_id == workspace_id,
                        ScenarioComparison.create_key == key,
                    )
                )
                if existing is None:
                    raise RuntimeError("Conflicting comparison not visible to owner")
                if existing.create_fingerprint != fingerprint:
                    raise IdempotencyConflict()
                return _dto(existing), True
            saved = session.get(ScenarioComparison, inserted)
            if saved is None:
                raise RuntimeError("Saved comparison not visible to owner")
            return _dto(saved), False

    def list(
        self,
        principal: VerifiedPrincipal,
        workspace_id: UUID,
        lead_id: UUID,
        limit: int,
    ) -> list[SavedComparisonDTO]:
        if type(limit) is not int or not 1 <= limit <= 50:
            raise ApiFailure("VALIDATION_FAILED", 422, "Invalid comparison page size.")
        with self.database.transaction(principal) as session:
            ProfileStore._owned(session, principal, workspace_id)
            LeadStore._lead(session, workspace_id, lead_id)
            rows = session.scalars(
                select(ScenarioComparison)
                .where(
                    ScenarioComparison.workspace_id == workspace_id,
                    ScenarioComparison.lead_id == lead_id,
                )
                .order_by(ScenarioComparison.created_at.desc(), ScenarioComparison.id.desc())
                .limit(limit)
            )
            return [_dto(row) for row in rows]


def get_scenario_store(
    workspaces: Annotated[WorkspaceStore, Depends(get_workspace_store)],
) -> ScenarioStore:
    return ScenarioStore(workspaces.database)


Principal = Annotated[VerifiedPrincipal, Depends(get_verified_principal)]
Store = Annotated[ScenarioStore, Depends(get_scenario_store)]
router = APIRouter(
    prefix="/api/v1/workspaces/{workspace_id}/leads/{lead_id}/scenario-comparisons",
    tags=["counterfactual"],
    responses={
        401: {"model": ErrorDTO},
        403: {"model": ErrorDTO},
        404: {"model": ErrorDTO},
        409: {"model": ErrorDTO},
        422: {"model": ErrorDTO},
        503: {"model": ErrorDTO},
    },
)


@router.post("", response_model=SavedComparisonDTO, status_code=201)
def save_comparison(
    workspace_id: UUID,
    lead_id: UUID,
    payload: CompareSavedLead,
    principal: Principal,
    store: Store,
    response: Response,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=128)],
) -> SavedComparisonDTO:
    saved, replay = store.save(principal, workspace_id, lead_id, payload, idempotency_key)
    response.status_code = 200 if replay else 201
    response.headers["Cache-Control"] = "no-store"
    return saved


@router.get("", response_model=SavedComparisonListDTO)
def list_comparisons(
    workspace_id: UUID,
    lead_id: UUID,
    principal: Principal,
    store: Store,
    response: Response,
    limit: Annotated[int, Query(ge=1, le=50)] = 20,
) -> SavedComparisonListDTO:
    response.headers["Cache-Control"] = "no-store"
    return SavedComparisonListDTO(items=store.list(principal, workspace_id, lead_id, limit))
