"""M1.5 typed workspace HTTP boundary. Auth is distinct from app-user authorization."""

from __future__ import annotations

from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Body, Depends, Header, Query, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from app.auth import VerifiedPrincipal, get_verified_principal
from app.workspace_store import WorkspaceStore


class StrictBody(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class BootstrapBody(StrictBody):
    """Only an empty object is accepted; caller-owned IDs/status are forbidden."""


class CreateWorkspaceBody(StrictBody):
    name: str


class UpdateWorkspaceBody(StrictBody):
    name: str
    expected_version: int = Field(gt=0, le=9223372036854775807)


class UserDTO(BaseModel):
    id: UUID
    status: Literal["active"]
    created_at: datetime


class BootstrapDTO(BaseModel):
    user: UserDTO
    created: bool


class WorkspaceDTO(BaseModel):
    id: UUID
    name: str
    created_at: datetime
    updated_at: datetime
    version: int


class WorkspaceListDTO(BaseModel):
    items: list[WorkspaceDTO]
    next_cursor: str | None


class ErrorData(BaseModel):
    code: str
    message: str
    retryable: bool
    details: dict[str, object] = Field(default_factory=dict)


class ErrorDTO(BaseModel):
    error: ErrorData
    request_id: str


class ApiFailure(Exception):
    """Public error classification, with no raw SQL/claims/request contents."""

    def __init__(
        self, code: str, status: int, message: str, *, retryable: bool = False
    ) -> None:
        self.code = code
        self.status = status
        self.message = message
        self.retryable = retryable
        super().__init__(code)


def get_workspace_store(request: Request) -> WorkspaceStore:
    database = getattr(request.app.state, "database", None)
    if database is None:
        raise ApiFailure(
            "DATABASE_UNAVAILABLE", 503, "Database unavailable.", retryable=True
        )
    return WorkspaceStore(database)


Principal = Annotated[VerifiedPrincipal, Depends(get_verified_principal)]
Store = Annotated[WorkspaceStore, Depends(get_workspace_store)]

_errors = {
    401: {"model": ErrorDTO},
    403: {"model": ErrorDTO},
    404: {"model": ErrorDTO},
    409: {"model": ErrorDTO},
    422: {"model": ErrorDTO},
    503: {"model": ErrorDTO},
}
router = APIRouter(prefix="/api/v1", tags=["workspace"], responses=_errors)


@router.post(
    "/me/bootstrap",
    response_model=BootstrapDTO,
    status_code=201,
    responses={200: {"model": BootstrapDTO}},
)
def bootstrap(
    principal: Principal,
    store: Store,
    response: Response,
    payload: Annotated[BootstrapBody | None, Body()] = None,
) -> BootstrapDTO:
    # FastAPI validates optional body when provided; do not accept injected identity fields.
    del payload
    outcome = store.bootstrap(principal)
    response.status_code = 201 if outcome.created else 200
    return BootstrapDTO(
        user=UserDTO(id=principal.user_id, status="active", created_at=outcome.created_at),
        created=outcome.created,
    )


@router.get("/me", response_model=UserDTO)
def me(principal: Principal, store: Store) -> UserDTO:
    user = store.get_user(principal)
    return UserDTO.model_validate(user)


@router.get("/workspaces", response_model=WorkspaceListDTO)
def list_workspaces(
    principal: Principal,
    store: Store,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
    cursor: Annotated[str | None, Query(max_length=512)] = None,
) -> WorkspaceListDTO:
    result = store.page_workspaces(principal, limit=limit, cursor=cursor)
    return WorkspaceListDTO.model_validate(result)


@router.post("/workspaces", response_model=WorkspaceDTO, status_code=201)
def create_workspace(
    principal: Principal,
    store: Store,
    payload: CreateWorkspaceBody,
    idempotency_key: Annotated[str, Header(alias="Idempotency-Key", min_length=8, max_length=128)],
) -> WorkspaceDTO:
    result = store.create_workspace(principal, name=payload.name, key=idempotency_key)
    return WorkspaceDTO.model_validate(result.response_body)


@router.get("/workspaces/{workspace_id}", response_model=WorkspaceDTO)
def get_workspace(principal: Principal, store: Store, workspace_id: UUID) -> WorkspaceDTO:
    value = store.get_workspace(principal, workspace_id)
    return WorkspaceDTO.model_validate(value)


@router.patch("/workspaces/{workspace_id}", response_model=WorkspaceDTO)
def update_workspace(
    principal: Principal, store: Store, workspace_id: UUID, payload: UpdateWorkspaceBody
) -> WorkspaceDTO:
    value = store.update_workspace(
        principal, workspace_id, name=payload.name, expected_version=payload.expected_version
    )
    return WorkspaceDTO.model_validate(value)
