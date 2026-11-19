"""Versioned HTTP health interface; no business or authentication routes yet."""

from __future__ import annotations

from typing import Literal

from fastapi import FastAPI
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from app.settings import RuntimeSettings, load_settings


class Liveness(BaseModel):
    status: Literal["alive"] = "alive"
    service: Literal["axiom-api"] = "axiom-api"


class Readiness(BaseModel):
    status: Literal["ready", "not_ready"]
    scope: Literal["foundation_only"] = "foundation_only"
    dependencies: Literal["none_configured", "database_not_verified"]


def create_app(settings: RuntimeSettings | None = None) -> FastAPI:
    resolved = settings if settings is not None else load_settings()
    application = FastAPI(title="Axiom API (foundation only)", version="0.2.0")

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
        return Readiness(status="ready", dependencies="none_configured")

    return application


app = create_app()
