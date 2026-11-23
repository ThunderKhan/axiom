"""Versioned HTTP health interface with reusable fail-closed Supabase JWT boundary."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.exc import SQLAlchemyError

from app.auth import AuthFailure, JwtVerifier
from app.database import Database
from app.leads_http import router as leads_router
from app.leads_store import InvalidLeadInput, LeadAlreadySaved
from app.profile_http import router as profile_router
from app.profile_store import ProfileIncomplete
from app.settings import RuntimeSettings, load_settings
from app.workspace_cursor import InvalidCursor
from app.workspace_http import ApiFailure, router
from app.workspace_store import (
    AccountDisabled,
    IdempotencyConflict,
    InvalidWorkspaceInput,
    ProvisioningRequired,
    VersionConflict,
    WorkspaceNotFound,
)


class Liveness(BaseModel):
    status: Literal["alive"] = "alive"
    service: Literal["axiom-api"] = "axiom-api"


class Readiness(BaseModel):
    status: Literal["ready", "not_ready"]
    scope: Literal["foundation_only"] = "foundation_only"
    dependencies: Literal[
        "none_configured", "database_not_verified", "database_verified", "auth_not_verified"
    ]


def create_app(settings: RuntimeSettings | None = None) -> FastAPI:
    resolved = settings if settings is not None else load_settings()
    database = Database(resolved) if resolved.database_url is not None else None

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        try:
            yield
        finally:
            if database is not None:
                database.close()

    application = FastAPI(title="Axiom API", version="0.2.0", lifespan=lifespan)
    application.state.jwt_verifier = JwtVerifier(resolved) if resolved.auth_configured else None
    application.state.database = database
    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.cors_origins.split(","),
        allow_methods=["GET", "POST", "PATCH", "PUT", "DELETE"],
        allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
        allow_credentials=False,
    )

    @application.exception_handler(AuthFailure)
    def auth_failure(_request: Request, exc: AuthFailure) -> JSONResponse:
        unavailable = exc.unavailable
        return JSONResponse(
            status_code=503 if unavailable else 401,
            content={
                "error": {
                    "code": "AUTH_UNAVAILABLE" if unavailable else "AUTH_REQUIRED",
                    "message": (
                        "Authentication verification unavailable."
                        if unavailable
                        else "Authentication required."
                    ),
                    "retryable": unavailable,
                    "details": {},
                },
                "request_id": f"req_{uuid4().hex}",
            },
            headers={} if unavailable else {"WWW-Authenticate": "Bearer"},
        )

    def api_error(code: str, status: int, message: str, *, retryable: bool = False) -> JSONResponse:
        return JSONResponse(
            status_code=status,
            content={
                "error": {"code": code, "message": message, "retryable": retryable, "details": {}},
                "request_id": f"req_{uuid4().hex}",
            },
        )

    @application.exception_handler(ApiFailure)
    def workspace_api_error(_request: Request, exc: ApiFailure) -> JSONResponse:
        return api_error(exc.code, exc.status, exc.message, retryable=exc.retryable)

    @application.exception_handler(AccountDisabled)
    def disabled_account(_request: Request, _exc: AccountDisabled) -> JSONResponse:
        return api_error("ACCOUNT_DISABLED", 403, "Account disabled.")

    @application.exception_handler(ProvisioningRequired)
    def provisioning_required(_request: Request, _exc: ProvisioningRequired) -> JSONResponse:
        return api_error("PROVISIONING_REQUIRED", 409, "Account provisioning required.")

    @application.exception_handler(WorkspaceNotFound)
    def workspace_not_found(_request: Request, _exc: WorkspaceNotFound) -> JSONResponse:
        return api_error("NOT_FOUND", 404, "Workspace not found.")

    @application.exception_handler(ProfileIncomplete)
    def incomplete_profile(_request: Request, _exc: ProfileIncomplete) -> JSONResponse:
        return api_error("PROFILE_INCOMPLETE", 422, "Complete the required profile fields.")

    @application.exception_handler(VersionConflict)
    def version_conflict(_request: Request, _exc: VersionConflict) -> JSONResponse:
        return api_error("VERSION_CONFLICT", 409, "Workspace version conflict.")

    @application.exception_handler(IdempotencyConflict)
    def idempotency_conflict(_request: Request, _exc: IdempotencyConflict) -> JSONResponse:
        return api_error("IDEMPOTENCY_CONFLICT", 409, "Idempotency key conflict.")

    def invalid_domain_input(_request: Request, _exc: Exception) -> JSONResponse:
        return api_error("VALIDATION_FAILED", 422, "Invalid workspace input.")

    application.add_exception_handler(InvalidWorkspaceInput, invalid_domain_input)
    application.add_exception_handler(InvalidLeadInput, invalid_domain_input)

    @application.exception_handler(LeadAlreadySaved)
    def duplicate_lead(_request: Request, _exc: LeadAlreadySaved) -> JSONResponse:
        return api_error("LEAD_ALREADY_SAVED", 409, "Source URL is already saved.")
    application.add_exception_handler(InvalidCursor, invalid_domain_input)

    @application.exception_handler(RequestValidationError)
    def invalid_http_input(_request: Request, _exc: RequestValidationError) -> JSONResponse:
        # Never serialize untrusted validation inputs or bearer values.
        return api_error("VALIDATION_FAILED", 422, "Invalid request input.")

    @application.exception_handler(SQLAlchemyError)
    def database_error(_request: Request, _exc: SQLAlchemyError) -> JSONResponse:
        return api_error("DATABASE_UNAVAILABLE", 503, "Database unavailable.", retryable=True)

    application.include_router(router)
    application.include_router(profile_router)
    application.include_router(leads_router)

    @application.get("/api/v1/health/live", response_model=Liveness, tags=["health"])
    def liveness() -> Liveness:
        return Liveness()

    @application.get(
        "/api/v1/health/ready",
        response_model=Readiness,
        responses={503: {"model": Readiness}},
        tags=["health"],
    )
    def readiness() -> Readiness | JSONResponse:
        if resolved.database_required or database is not None:
            if database is None or not database.ready():
                return JSONResponse(
                    status_code=503,
                    content=Readiness(
                        status="not_ready", dependencies="database_not_verified"
                    ).model_dump(),
                )
            return Readiness(status="ready", dependencies="database_verified")
        if resolved.auth_configured:
            # JWT/JWKS and account persistence have not been provider-verified at this milestone.
            return JSONResponse(
                status_code=503,
                content=Readiness(
                    status="not_ready", dependencies="auth_not_verified"
                ).model_dump(),
            )
        return Readiness(status="ready", dependencies="none_configured")

    return application


app = create_app()
