"""Authenticated, workspace-scoped saved lead HTTP interface (no outbound sending)."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Header, Query, Response
from pydantic import BaseModel

from app.auth import VerifiedPrincipal, get_verified_principal
from app.leads_contract import CreateLead, LeadStage, PatchLead
from app.leads_store import LeadStore
from app.workspace_http import ErrorDTO, get_workspace_store
from app.workspace_store import WorkspaceStore


class LeadDTO(BaseModel):
    id: UUID
    workspace_id: UUID
    title: str
    source_url: str
    source_excerpt: str
    source_origin: Literal["user_provided", "live"]
    research_run_id: UUID | None = None
    research_signal_id: UUID | None = None
    stage: LeadStage
    note: str
    follow_up_at: datetime | None
    follow_up_done: bool
    unsent_draft: str
    version: int
    created_at: datetime
    updated_at: datetime


class CreatedLeadDTO(LeadDTO):
    already_exists: bool


class LeadListDTO(BaseModel):
    items: list[LeadDTO]


class LeadEventDTO(BaseModel):
    id: UUID
    actor_id: UUID
    event_type: Literal["created", "updated", "archived"]
    changed_fields: list[str]
    created_at: datetime


class LeadHistoryDTO(BaseModel):
    items: list[LeadEventDTO]


def get_lead_store(
    workspaces: Annotated[WorkspaceStore, Depends(get_workspace_store)],
) -> LeadStore:
    return LeadStore(workspaces.database)


Principal = Annotated[VerifiedPrincipal, Depends(get_verified_principal)]
Store = Annotated[LeadStore, Depends(get_lead_store)]

router = APIRouter(
    prefix="/api/v1/workspaces/{workspace_id}/leads",
    tags=["crm"],
    responses={
        401: {"model": ErrorDTO},
        403: {"model": ErrorDTO},
        404: {"model": ErrorDTO},
        409: {"model": ErrorDTO},
        422: {"model": ErrorDTO},
        503: {"model": ErrorDTO},
    },
)


@router.post("", response_model=CreatedLeadDTO, status_code=201)
def create_lead(
    workspace_id: UUID,
    payload: CreateLead,
    principal: Principal,
    store: Store,
    response: Response,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=128)],
) -> CreatedLeadDTO:
    saved = store.create(principal, workspace_id, payload=payload, key=idempotency_key)
    response.status_code = 200 if saved["already_exists"] else 201
    return CreatedLeadDTO.model_validate(saved)


@router.get("", response_model=LeadListDTO)
def list_leads(
    workspace_id: UUID,
    principal: Principal,
    store: Store,
    stage: LeadStage | None = None,
    query: Annotated[str | None, Query(max_length=100)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> LeadListDTO:
    return LeadListDTO.model_validate(
        store.list(principal, workspace_id, stage=stage, query=query, limit=limit)
    )


@router.get("/{lead_id}", response_model=LeadDTO)
def get_lead(workspace_id: UUID, lead_id: UUID, principal: Principal, store: Store) -> LeadDTO:
    return LeadDTO.model_validate(store.read(principal, workspace_id, lead_id))


@router.patch("/{lead_id}", response_model=LeadDTO)
def update_lead(
    workspace_id: UUID, lead_id: UUID, payload: PatchLead, principal: Principal, store: Store
) -> LeadDTO:
    return LeadDTO.model_validate(store.patch(principal, workspace_id, lead_id, payload=payload))


@router.delete("/{lead_id}", status_code=204)
def archive_lead(
    workspace_id: UUID,
    lead_id: UUID,
    principal: Principal,
    store: Store,
    expected_version: Annotated[int, Query(ge=1, lt=9223372036854775807)],
) -> None:
    # Logical archive retains prior activity; no permanent deletion without a retention decision.
    store.archive(principal, workspace_id, lead_id, expected_version=expected_version)


@router.get("/{lead_id}/activity", response_model=LeadHistoryDTO)
def lead_history(
    workspace_id: UUID, lead_id: UUID, principal: Principal, store: Store
) -> LeadHistoryDTO:
    return LeadHistoryDTO(
        items=[
            LeadEventDTO.model_validate(event)
            for event in store.history(principal, workspace_id, lead_id)
        ]
    )
