"""Manual-source graph/report contract: honest provenance and fail-closed HTTP."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.auth import VerifiedPrincipal, get_verified_principal
from app.evidence_engine import Verdict
from app.evidence_http import AssessSavedLead, assess_saved_manual_lead
from app.leads_http import LeadDTO, get_lead_store
from app.main import create_app
from app.profile_contract import ProfileAnswers
from app.profile_http import ConfirmedProfileDTO, ProfileStateDTO, get_profile_store
from app.profile_store import ProfileIncomplete
from app.settings import RuntimeSettings
from app.workspace_http import ApiFailure
from app.workspace_store import WorkspaceNotFound

NOW = datetime(2026, 11, 24, tzinfo=UTC)


def lead(workspace_id: UUID) -> LeadDTO:
    return LeadDTO(
        id=uuid4(),
        workspace_id=workspace_id,
        title="Customer research",
        source_url="https://example.org/manual",
        source_excerpt="I need offline sync for my notes",
        source_origin="user_provided",
        stage="spotted",
        note="",
        follow_up_at=None,
        follow_up_done=False,
        unsent_draft="",
        version=2,
        created_at=NOW,
        updated_at=NOW,
    )


def profile(
    *,
    stage: Literal["idea", "live"] = "live",
    capabilities: str = "offline sync",
    missing: str = "",
) -> ProfileStateDTO:
    answers = ProfileAnswers(
        stage=stage,
        name="Founder tool",
        problem="Some people lack offline notes",
        audience="Students",
        capabilities=capabilities,
        missing_capabilities=missing,
    )
    return ProfileStateDTO(
        draft_revision=3,
        draft_step=14,
        answers=answers,
        confirmed_revision=1,
        confirmed=ConfirmedProfileDTO(
            id=uuid4(), revision=1, answers=answers, confirmed_at=NOW
        ),
    )


def request(requirement: str = "offline sync", *, intent: str = "buying") -> AssessSavedLead:
    return AssessSavedLead.model_validate(
        {"needs": [{"requirement": requirement, "locator": requirement, "intent": intent}]}
    )


def test_manual_evidence_never_promoted_to_verified_live_demand() -> None:
    workspace_id = uuid4()
    result = assess_saved_manual_lead(workspace_id, lead(workspace_id), profile(), request())
    assert result.verdict == Verdict.RESEARCH
    assert result.live_source_verified is False
    assert result.persisted_assessment is False
    assert result.source_origin == "user_provided"
    assert result.confirmed_profile_revision == 1
    assert result.lead_version == 2
    assert "USER_PROVIDED_SOURCE_UNVERIFIED" in result.reason_codes
    assert result.supported_need_ids == ["need-1"]
    assert result.relationships[0].source_id == str(result.lead_id)
    assert "saved_at=" in " ".join(result.report_lines)
    assert "retrieved_at=" not in " ".join(result.report_lines)
    assert any("not independently verified" in item for item in result.report_lines)


def test_missing_or_proposed_capability_does_not_become_positive_fit() -> None:
    wid = uuid4()
    saved = lead(wid)
    missing = assess_saved_manual_lead(
        wid, saved, profile(capabilities="export", missing="offline sync"), request()
    )
    assert missing.verdict == Verdict.SKIP
    assert missing.missing_need_ids == ["need-1"]
    hypothetical = assess_saved_manual_lead(
        wid, saved, profile(stage="idea"), request()
    )
    assert hypothetical.verdict == Verdict.RESEARCH
    assert hypothetical.hypothetical_need_ids == ["need-1"]
    contradictory = assess_saved_manual_lead(
        wid, saved, profile(missing="offline sync"), request()
    )
    assert contradictory.verdict == Verdict.RESEARCH
    assert contradictory.unknown_need_ids == ["need-1"]


def test_no_needs_abstains_and_duplicate_capability_names_are_safe() -> None:
    wid = uuid4()
    saved = lead(wid)
    empty = assess_saved_manual_lead(
        wid, saved, profile(), AssessSavedLead(needs=[])
    )
    assert empty.verdict == Verdict.INSUFFICIENT
    both = AssessSavedLead.model_validate(
        {
            "needs": [
                {"requirement": "offline sync", "locator": "offline sync", "intent": "buying"},
                {"requirement": "OFFLINE SYNC", "locator": "offline sync", "intent": "discussion"},
            ]
        }
    )
    result = assess_saved_manual_lead(wid, saved, profile(), both)
    assert result.supported_need_ids == ["need-1", "need-2"]


def test_foreign_workspace_unconfirmed_and_nonmatching_citations_denied() -> None:
    wid = uuid4()
    with pytest.raises(ApiFailure) as wrong_workspace:
        assess_saved_manual_lead(uuid4(), lead(wid), profile(), request())
    assert wrong_workspace.value.status == 404
    unconfirmed = ProfileStateDTO(
        draft_revision=0,
        draft_step=0,
        answers=None,
        confirmed_revision=0,
        confirmed=None,
    )
    with pytest.raises(ProfileIncomplete):
        assess_saved_manual_lead(wid, lead(wid), unconfirmed, request())
    with pytest.raises(ApiFailure) as error:
        assess_saved_manual_lead(wid, lead(wid), profile(), request("export"))
    assert error.value.status == 422


@pytest.mark.parametrize(
    "needs",
    [
        [{"requirement": "offline sync", "locator": "offline sync", "intent": "fabricated"}],
        [{"requirement": " offline\\nsync", "locator": "offline sync", "intent": "buying"}],
        [{"requirement": "offline sync", "locator": "offline sync", "intent": "buying",
          "source_origin": "live"}],
        [{"requirement": "offline sync", "locator": "offline sync", "intent": "buying"}] * 9,
    ],
)
def test_request_cannot_claim_live_source_or_bypass_bounded_contract(needs: list[object]) -> None:
    with pytest.raises(ValidationError):
        AssessSavedLead.model_validate({"needs": needs})


def test_http_reads_both_resources_under_same_verified_principal() -> None:
    workspace_id = uuid4()
    saved = lead(workspace_id)
    confirmed = profile()
    alice = VerifiedPrincipal(uuid4(), None)
    bob = VerifiedPrincipal(uuid4(), None)

    class Leads:
        def read(self, principal: VerifiedPrincipal, wid: UUID, lid: UUID) -> dict[str, object]:
            if principal != alice or wid != workspace_id or lid != saved.id:
                raise WorkspaceNotFound()
            return saved.model_dump()

    class Profiles:
        def read(self, principal: VerifiedPrincipal, wid: UUID) -> dict[str, object]:
            if principal != alice or wid != workspace_id:
                raise WorkspaceNotFound()
            return confirmed.model_dump()

    app = create_app(RuntimeSettings())
    app.dependency_overrides[get_lead_store] = lambda: Leads()
    app.dependency_overrides[get_profile_store] = lambda: Profiles()
    app.dependency_overrides[get_verified_principal] = lambda: alice
    route = f"/api/v1/workspaces/{workspace_id}/leads/{saved.id}/assessment"
    with TestClient(app) as client:
        response = client.post(route, json=request().model_dump())
        assert response.status_code == 200
        assert response.json()["verdict"] == "research_further"
        assert response.json()["source_origin"] == "user_provided"
        invalid = client.post(
            route,
            json={"needs": [{"requirement": "offline sync", "locator": "unrelated",
                             "intent": "buying"}]},
        )
        assert invalid.status_code == 422
        forged = client.post(route, json={"needs": [], "live_source_verified": True})
        assert forged.status_code == 422
        app.dependency_overrides[get_verified_principal] = lambda: bob
        denied = client.post(route, json={"needs": []})
        assert denied.status_code == 404
