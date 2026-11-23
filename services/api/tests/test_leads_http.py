"""Real FastAPI body parsing for ISO follow-ups; isolated fake store only for transport."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID, uuid4

from fastapi.testclient import TestClient

from app.auth import VerifiedPrincipal, get_verified_principal
from app.leads_contract import CreateLead
from app.leads_http import get_lead_store
from app.main import create_app
from app.settings import RuntimeSettings


class TransportOnlyStore:
    def __init__(self) -> None:
        self.received: CreateLead | None = None

    def create(
        self,
        principal: VerifiedPrincipal,
        workspace_id: UUID,
        *,
        payload: CreateLead,
        key: str,
    ) -> dict[str, object]:
        assert principal.user_id.int != 0
        assert key == "knownKey123"
        self.received = payload
        now = datetime.now(UTC)
        return {
            "id": uuid4(),
            "workspace_id": workspace_id,
            **payload.model_dump(),
            "source_origin": "user_provided",
            "version": 1,
            "created_at": now,
            "updated_at": now,
            "already_exists": False,
        }


def test_authenticated_http_accepts_timezone_json_and_rejects_naive_time() -> None:
    app = create_app(RuntimeSettings())
    principal = VerifiedPrincipal(user_id=uuid4(), session_id=None)
    isolated = TransportOnlyStore()
    app.dependency_overrides[get_verified_principal] = lambda: principal
    app.dependency_overrides[get_lead_store] = lambda: isolated
    workspace_id = uuid4()
    url = f"/api/v1/workspaces/{workspace_id}/leads"
    payload = {
        "title": "Manual report",
        "source_url": "https://example.org/manual",
        "source_excerpt": "Manual evidence, not fetched",
        "follow_up_at": "2026-11-26T12:00:00Z",
        "follow_up_done": True,
    }
    with TestClient(app) as client:
        valid = client.post(url, json=payload, headers={"Idempotency-Key": "knownKey123"})
        assert valid.status_code == 201
        assert valid.json()["follow_up_at"] == "2026-11-26T12:00:00Z"
        assert valid.json()["source_origin"] == "user_provided"
        assert isolated.received is not None
        assert isolated.received.follow_up_at is not None
        assert isolated.received.follow_up_at.utcoffset().total_seconds() == 0
        invalid = client.post(
            url,
            json={**payload, "follow_up_at": "2026-11-26T12:00:00"},
            headers={"Idempotency-Key": "knownKey123"},
        )
        assert invalid.status_code == 422
