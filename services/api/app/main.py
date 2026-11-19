"""Versioned HTTP health interface with reusable fail-closed Supabase JWT boundary."""

from __future__ import annotations

from typing import Literal
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.auth import AuthFailure, JwtVerifier
from app.settings import RuntimeSettings, load_settings


class Liveness(BaseModel):
    status: Literal["alive"] = "alive"
    service: Literal["axiom-api"] = "axiom-api"


class Readiness(BaseModel):
    status: Literal["ready", "not_ready"]
    scope: Literal["foundation_only"] = "foundation_only"
    dependencies: Literal["none_configured", "database_not_verified", "auth_not_verified"]


def create_app(settings: RuntimeSettings | None = None) -> FastAPI:
    resolved = settings if settings is not None else load_settings()
    application = FastAPI(title="Axiom API (foundation only)", version="0.2.0")
    application.state.jwt_verifier = JwtVerifier(resolved) if resolved.auth_configured else None
    application.add_middleware(
        CORSMiddleware,
        allow_origins=resolved.cors_origins.split(","),
        allow_methods=["GET"],
        allow_headers=["Authorization"],
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
        if resolved.database_required or resolved.database_url is not None:
            # No DB client or schema exists in WP-01; a configured DB is unverified.
            return JSONResponse(
                status_code=503,
                content=Readiness(
                    status="not_ready", dependencies="database_not_verified"
                ).model_dump(),
            )
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
