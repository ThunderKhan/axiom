"""Real, bounded feed discovery and immutable result reopening.

The provider fetch is outside database transactions. Only a reviewed
storage permission authorizes persistence. No result claims purchase intent.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID, uuid4, uuid5

from fastapi import APIRouter, Depends, Header, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.auth import VerifiedPrincipal, get_verified_principal
from app.database import Database
from app.evidence_engine import Assessment, Capability, EvidenceInputError, Need, Source, assess
from app.evidence_http import AssessSavedLead, _declared_names
from app.leads_contract import validate_idempotency_key
from app.models import ProductProfile, ProfileVersion, ResearchRun
from app.profile_contract import ProfileAnswers
from app.profile_store import ProfileStore
from app.public_source import SourceAccessBlocked, SourceAcquisitionFailed
from app.source_http import get_source_registry
from app.source_registry import ReviewedSourceRegistry, SourceRateLimited
from app.workspace_http import ApiFailure, StrictBody, get_workspace_store
from app.workspace_store import (
    IdempotencyConflict,
    VersionConflict,
    WorkspaceNotFound,
    WorkspaceStore,
)


class DiscoverFeed(StrictBody):
    profile_version_id: UUID = Field(strict=False)
    url: str = Field(min_length=10, max_length=2048)
    query: str = Field(default="", max_length=120)
    limit: int = Field(default=10, ge=1, le=20)


class SignalDTO(BaseModel):
    signal_id: UUID
    source_id: str
    source_url: str
    title: str
    excerpt: str
    published_at: datetime | None
    intent: Literal["unknown"] = "unknown"


class ResearchResult(BaseModel):
    profile_version_id: UUID
    feed_url: str
    query: str
    retrieved_at: datetime
    feed_content_digest: str
    publisher: str
    policy_review_id: str
    items: list[SignalDTO]
    source_family: Literal["rss_atom"] = "rss_atom"
    origin: Literal["live"] = "live"
    query_method: Literal["literal_all_terms"] = "literal_all_terms"
    independent_fact_verification: Literal[False] = False


class SavedResearchDTO(BaseModel):
    run_id: UUID
    workspace_id: UUID
    profile_revision: int
    status: Literal["completed"] = "completed"
    created_at: datetime
    result: ResearchResult


class SignalAssessmentDTO(BaseModel):
    workspace_id: UUID
    run_id: UUID
    signal_id: UUID
    profile_revision: int
    profile_version_id: UUID
    source_url: str
    source_excerpt: str
    retrieved_at: datetime
    policy_review_id: str
    feed_content_digest: str
    source_origin: Literal["live"] = "live"
    article_independently_verified: Literal[False] = False
    persisted_assessment: Literal[False] = False
    assessment: Assessment


def _dto(row: ResearchRun) -> SavedResearchDTO:
    return SavedResearchDTO(
        run_id=row.id,
        workspace_id=row.workspace_id,
        profile_revision=row.profile_revision,
        created_at=row.created_at,
        result=ResearchResult.model_validate(row.result),
    )


class ResearchStore:
    def __init__(self, database: Database, registry: ReviewedSourceRegistry) -> None:
        self.database = database
        self.registry = registry

    @staticmethod
    def _existing(
        session: Session, workspace_id: UUID, key: str, fingerprint: str
    ) -> SavedResearchDTO | None:
        row = session.scalar(
            select(ResearchRun).where(
                ResearchRun.workspace_id == workspace_id, ResearchRun.create_key == key
            )
        )
        if row is None:
            return None
        if row.create_fingerprint != fingerprint:
            raise IdempotencyConflict()
        return _dto(row)

    @staticmethod
    def _current_profile(session: Session, workspace_id: UUID, profile_version_id: UUID) -> int:
        revision = session.scalar(
            select(ProfileVersion.revision)
            .join(ProductProfile, ProductProfile.workspace_id == ProfileVersion.workspace_id)
            .where(
                ProfileVersion.workspace_id == workspace_id,
                ProfileVersion.id == profile_version_id,
                ProfileVersion.revision == ProductProfile.confirmed_revision,
            )
        )
        if revision is None:
            raise VersionConflict()
        return revision

    def discover(
        self, principal: VerifiedPrincipal, workspace_id: UUID, body: DiscoverFeed, key: str
    ) -> tuple[SavedResearchDTO, bool]:
        try:
            validate_idempotency_key(key)
        except ValueError as exc:
            raise ApiFailure("VALIDATION_FAILED", 422, "Invalid idempotency key.") from exc
        canonical = json.dumps(body.model_dump(mode="json"), sort_keys=True, separators=(",", ":"))
        fingerprint = hashlib.sha256(canonical.encode()).hexdigest()
        with self.database.transaction(principal) as session:
            ProfileStore._owned(session, principal, workspace_id)
            existing = self._existing(session, workspace_id, key, fingerprint)
            if existing is not None:
                return existing, True
            revision = self._current_profile(session, workspace_id, body.profile_version_id)
        try:
            review, document, items = self.registry.retrieve_feed_for_storage(
                body.url, query=body.query, limit=body.limit
            )
        except SourceAccessBlocked as exc:
            raise ApiFailure("SOURCE_BLOCKED", 403, "Source retention not permitted.") from exc
        except SourceRateLimited as exc:
            raise ApiFailure("SOURCE_RATE_LIMITED", 429, "Source request limit reached.") from exc
        except SourceAcquisitionFailed as exc:
            raise ApiFailure("SOURCE_UNAVAILABLE", 502, "Feed could not be retrieved.") from exc

        run_id = uuid4()
        result = ResearchResult(
            profile_version_id=body.profile_version_id,
            feed_url=document.url,
            query=body.query,
            retrieved_at=document.retrieved_at,
            feed_content_digest=hashlib.sha256(document.body).hexdigest(),
            publisher=review.publisher,
            policy_review_id=review.review_id,
            items=[
                SignalDTO(
                    signal_id=uuid5(run_id, item.source_id),
                    source_id=item.source_id,
                    source_url=item.source_url,
                    title=item.title,
                    excerpt=item.excerpt,
                    published_at=item.published_at,
                )
                for item in items
            ],
        )
        with self.database.transaction(principal) as session:
            ProfileStore._owned(session, principal, workspace_id)
            existing = self._existing(session, workspace_id, key, fingerprint)
            if existing is not None:
                return existing, True
            # Serialize with profile confirmation only after the bounded network operation.
            session.scalar(
                select(ProductProfile)
                .where(ProductProfile.workspace_id == workspace_id)
                .with_for_update()
            )
            existing = self._existing(session, workspace_id, key, fingerprint)
            if existing is not None:
                return existing, True
            if self._current_profile(session, workspace_id, body.profile_version_id) != revision:
                raise VersionConflict()
            inserted = session.execute(
                insert(ResearchRun)
                .values(
                    id=run_id,
                    workspace_id=workspace_id,
                    profile_revision=revision,
                    create_key=key,
                    create_fingerprint=fingerprint,
                    result=result.model_dump(mode="json"),
                )
                .on_conflict_do_nothing()
                .returning(ResearchRun.id)
            ).scalar_one_or_none()
            if inserted is None:
                existing = self._existing(session, workspace_id, key, fingerprint)
                if existing is None:
                    raise RuntimeError("Conflicting research result not visible")
                return existing, True
            row = session.get(ResearchRun, inserted)
            if row is None:
                raise RuntimeError("Saved research result not visible")
            return _dto(row), False

    def read(
        self, principal: VerifiedPrincipal, workspace_id: UUID, run_id: UUID
    ) -> SavedResearchDTO:
        with self.database.transaction(principal) as session:
            ProfileStore._owned(session, principal, workspace_id)
            row = session.scalar(
                select(ResearchRun).where(
                    ResearchRun.workspace_id == workspace_id, ResearchRun.id == run_id
                )
            )
            if row is None:
                raise WorkspaceNotFound()
            return _dto(row)


    def assess_signal(
        self,
        principal: VerifiedPrincipal,
        workspace_id: UUID,
        run_id: UUID,
        signal_id: UUID,
        request: AssessSavedLead,
    ) -> SignalAssessmentDTO:
        # A historical assessment uses the immutable profile recorded at retrieval,
        # never a later profile or caller-supplied excerpt.
        with self.database.transaction(principal) as session:
            ProfileStore._owned(session, principal, workspace_id)
            row = session.scalar(
                select(ResearchRun).where(
                    ResearchRun.workspace_id == workspace_id, ResearchRun.id == run_id
                )
            )
            if row is None:
                raise WorkspaceNotFound()
            saved = _dto(row)
            item = next((item for item in saved.result.items if item.signal_id == signal_id), None)
            if item is None:
                raise WorkspaceNotFound()
            profile = session.scalar(
                select(ProfileVersion).where(
                    ProfileVersion.workspace_id == workspace_id,
                    ProfileVersion.revision == row.profile_revision,
                    ProfileVersion.id == saved.result.profile_version_id,
                )
            )
            if profile is None:
                raise RuntimeError("Stored research profile is inconsistent")
            answers = ProfileAnswers.model_validate(profile.answers)

        available = _declared_names(answers.capabilities)
        missing = _declared_names(answers.missing_capabilities)
        capabilities: dict[str, Capability] = {}
        for cited in request.needs:
            key = " ".join(cited.requirement.casefold().split())
            status: Literal["available", "proposed", "missing", "unknown"] = "unknown"
            if key in available and key not in missing:
                status = "available" if answers.stage == "live" else "proposed"
            elif key in missing and key not in available:
                status = "missing"
            capabilities[key] = Capability(cited.requirement, status)
        try:
            source = Source(
                id=str(item.signal_id),
                url=item.source_url,
                excerpt=item.excerpt,
                retrieved_at=saved.result.retrieved_at,
                origin="live",
            )
            # Feed syndication is not evidence of buying intent. Even if the
            # founder supplies an intent interpretation, do not promote it.
            needs = tuple(
                Need(
                    id=f"need-{index}",
                    requirement=cited.requirement,
                    source_id=source.id,
                    locator=cited.locator,
                    intent="unknown",
                )
                for index, cited in enumerate(request.needs, start=1)
            )
            report = assess(
                (source,), needs, tuple(capabilities.values()), launched=answers.stage == "live"
            )
        except EvidenceInputError as exc:
            raise ApiFailure("VALIDATION_FAILED", 422, "Citation does not match saved feed.") from exc
        return SignalAssessmentDTO(
            workspace_id=workspace_id,
            run_id=run_id,
            signal_id=signal_id,
            profile_revision=saved.profile_revision,
            profile_version_id=saved.result.profile_version_id,
            source_url=item.source_url,
            source_excerpt=item.excerpt,
            retrieved_at=saved.result.retrieved_at,
            policy_review_id=saved.result.policy_review_id,
            feed_content_digest=saved.result.feed_content_digest,
            assessment=report,
        )


def get_research_store(
    workspaces: Annotated[WorkspaceStore, Depends(get_workspace_store)],
    registry: Annotated[ReviewedSourceRegistry, Depends(get_source_registry)],
) -> ResearchStore:
    return ResearchStore(workspaces.database, registry)


Principal = Annotated[VerifiedPrincipal, Depends(get_verified_principal)]
Store = Annotated[ResearchStore, Depends(get_research_store)]
router = APIRouter(prefix="/api/v1/workspaces/{workspace_id}/research/runs", tags=["research"])


@router.post("", response_model=SavedResearchDTO, status_code=201)
def discover(
    workspace_id: UUID,
    body: DiscoverFeed,
    principal: Principal,
    store: Store,
    response: Response,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=128)],
) -> SavedResearchDTO:
    result, replay = store.discover(principal, workspace_id, body, idempotency_key)
    response.status_code = 200 if replay else 201
    response.headers["Cache-Control"] = "no-store"
    return result


@router.get("/{run_id}", response_model=SavedResearchDTO)
def read(
    workspace_id: UUID, run_id: UUID, principal: Principal, store: Store, response: Response
) -> SavedResearchDTO:
    response.headers["Cache-Control"] = "no-store"
    return store.read(principal, workspace_id, run_id)


@router.post("/{run_id}/signals/{signal_id}/assessment", response_model=SignalAssessmentDTO)
def assess_signal(
    workspace_id: UUID,
    run_id: UUID,
    signal_id: UUID,
    body: AssessSavedLead,
    principal: Principal,
    store: Store,
    response: Response,
) -> SignalAssessmentDTO:
    response.headers["Cache-Control"] = "no-store"
    return store.assess_signal(principal, workspace_id, run_id, signal_id, body)
