"""Workspace-scoped founder profile HTTP surface, never direct Supabase data writes."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field

from app.auth import VerifiedPrincipal, get_verified_principal
from app.profile_contract import ProfileAnswers
from app.profile_store import ProfileStore
from app.workspace_http import ErrorDTO, StrictBody, get_workspace_store
from app.workspace_store import WorkspaceStore


class DraftBody(StrictBody):
    expected_revision: int = Field(ge=0, lt=9223372036854775807)
    answers: ProfileAnswers


class ConfirmBody(StrictBody):
    expected_revision: int = Field(ge=1, lt=9223372036854775807)


class ConfirmedProfileDTO(BaseModel):
    id: UUID
    revision: int
    answers: ProfileAnswers
    confirmed_at: datetime


class ProfileStateDTO(BaseModel):
    draft_revision: int
    answers: ProfileAnswers | None
    confirmed_revision: int
    confirmed: ConfirmedProfileDTO | None


def get_profile_store(
    workspaces: Annotated[WorkspaceStore, Depends(get_workspace_store)],
) -> ProfileStore:
    return ProfileStore(workspaces.database)


router = APIRouter(
    prefix="/api/v1/workspaces/{workspace_id}/profile",
    tags=["profiles"],
    responses={
        401: {"model": ErrorDTO},
        403: {"model": ErrorDTO},
        404: {"model": ErrorDTO},
        409: {"model": ErrorDTO},
        422: {"model": ErrorDTO},
        503: {"model": ErrorDTO},
    },
)

Principal = Annotated[VerifiedPrincipal, Depends(get_verified_principal)]
Store = Annotated[ProfileStore, Depends(get_profile_store)]


@router.get("", response_model=ProfileStateDTO)
def read_profile(workspace_id: UUID, principal: Principal, store: Store) -> ProfileStateDTO:
    return ProfileStateDTO.model_validate(store.read(principal, workspace_id))


@router.put("/draft", response_model=ProfileStateDTO)
def save_draft(
    workspace_id: UUID, body: DraftBody, principal: Principal, store: Store
) -> ProfileStateDTO:
    return ProfileStateDTO.model_validate(
        store.save(
            principal, workspace_id, answers=body.answers, expected_revision=body.expected_revision
        )
    )


@router.post("/confirm", response_model=ProfileStateDTO)
def confirm_profile(
    workspace_id: UUID, body: ConfirmBody, principal: Principal, store: Store
) -> ProfileStateDTO:
    return ProfileStateDTO.model_validate(
        store.confirm(principal, workspace_id, expected_revision=body.expected_revision)
    )
