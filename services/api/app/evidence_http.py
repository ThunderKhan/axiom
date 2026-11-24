"""Workspace-authorized, read-only assessment of saved *manual* evidence.

This is deliberately not a live-source verification, an inferred customer-intent
classifier, a persisted snapshot, or a competitor research endpoint.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field, field_validator

from app.auth import VerifiedPrincipal, get_verified_principal
from app.evidence_engine import (
    Capability,
    EvidenceInputError,
    Need,
    Source,
    Verdict,
    assess,
)
from app.leads_http import LeadDTO, get_lead_store
from app.leads_store import LeadStore
from app.profile_contract import ProfileAnswers
from app.profile_http import ProfileStateDTO, get_profile_store
from app.profile_store import ProfileIncomplete, ProfileStore
from app.workspace_http import ApiFailure, ErrorDTO, StrictBody

Intent = Literal["buying", "seeking_solution", "discussion", "unknown"]
_CAPABILITY_SEPARATOR = re.compile(r"[,;\n]")


class CitedNeed(StrictBody):
    requirement: str = Field(min_length=1, max_length=120)
    locator: str = Field(min_length=1, max_length=200)
    intent: Intent

    @field_validator("requirement", "locator")
    @classmethod
    def valid_phrase(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped or any(ord(ch) < 32 or ord(ch) == 127 for ch in stripped):
            raise ValueError("A single-line, nonempty citation is required")
        if any(0xD800 <= ord(ch) <= 0xDFFF for ch in stripped):
            raise ValueError("Invalid citation characters")
        return stripped


class AssessSavedLead(StrictBody):
    needs: list[CitedNeed] = Field(min_length=0, max_length=8)


class RelationshipDTO(BaseModel):
    source_id: str
    need_id: str
    capability: str | None
    relation: Literal["supports_need", "covers", "contradicts", "unverified"]
    explanation: str


class EvidenceReportDTO(BaseModel):
    workspace_id: UUID
    lead_id: UUID
    lead_version: int
    confirmed_profile_revision: int
    source_url: str
    source_origin: Literal["user_provided"]
    source_recorded_at: datetime
    live_source_verified: Literal[False] = False
    persisted_assessment: Literal[False] = False
    verdict: Verdict
    reason_codes: list[str]
    intent: Intent
    compatibility: Literal["supported", "contradicted", "partial", "unknown"]
    supported_need_ids: list[str]
    hypothetical_need_ids: list[str]
    missing_need_ids: list[str]
    unknown_need_ids: list[str]
    relationships: list[RelationshipDTO]
    report_lines: list[str]


def _declared_names(value: str) -> set[str]:
    # Only delimiters the founder explicitly supplied; no semantic extraction.
    return {
        " ".join(item.casefold().split())
        for item in _CAPABILITY_SEPARATOR.split(value)
        if item.strip()
    }


def assess_saved_manual_lead(
    workspace_id: UUID,
    lead: LeadDTO,
    profile: ProfileStateDTO,
    request: AssessSavedLead,
) -> EvidenceReportDTO:
    """Produce a traceable, nonpersistent report from the *current* owned records."""
    if lead.workspace_id != workspace_id or lead.source_origin != "user_provided":
        raise ApiFailure("NOT_FOUND", 404, "Workspace resource not found.")
    if profile.confirmed is None:
        raise ProfileIncomplete()
    answers: ProfileAnswers = profile.confirmed.answers
    if answers.stage is None:
        raise ProfileIncomplete()

    available = _declared_names(answers.capabilities)
    missing = _declared_names(answers.missing_capabilities)
    capabilities_by_name: dict[str, Capability] = {}
    for cited in request.needs:
        normalized = " ".join(cited.requirement.casefold().split())
        # Conflicting or undeclared founder input is Unknown, never auto-resolved.
        status: Literal["available", "proposed", "missing", "unknown"] = "unknown"
        if normalized in available and normalized not in missing:
            status = "available" if answers.stage == "live" else "proposed"
        elif normalized in missing and normalized not in available:
            status = "missing"
        capabilities_by_name[normalized] = Capability(cited.requirement, status)

    try:
        source = Source(
            id=str(lead.id),
            url=lead.source_url,
            excerpt=lead.source_excerpt,
            retrieved_at=lead.created_at,
            origin="user_provided",
        )
        needs = tuple(
            Need(
                id=f"need-{index}",
                requirement=item.requirement,
                source_id=source.id,
                locator=item.locator,
                intent=item.intent,
            )
            for index, item in enumerate(request.needs, start=1)
        )
        assessment = assess(
            (source,), needs, tuple(capabilities_by_name.values()), launched=answers.stage == "live"
        )
    except EvidenceInputError as exc:
        raise ApiFailure("VALIDATION_FAILED", 422, "Citation does not match saved source.") from exc

    # The founder entered both the text and the intent. Never promote this to a
    # verified acquisition signal even if declared feature coverage would fit.
    verdict = Verdict.RESEARCH if assessment.verdict == Verdict.PURSUE else assessment.verdict
    codes = [*assessment.reason_codes, "USER_PROVIDED_SOURCE_UNVERIFIED"]
    report = [
        *assessment.report_lines,
        "Source and intent were supplied by the founder and were not independently verified.",
        "This report is computed on request; no durable evidence snapshot is saved.",
    ]
    return EvidenceReportDTO(
        workspace_id=workspace_id,
        lead_id=lead.id,
        lead_version=lead.version,
        confirmed_profile_revision=profile.confirmed.revision,
        source_url=lead.source_url,
        source_origin="user_provided",
        source_recorded_at=lead.created_at,
        verdict=verdict,
        reason_codes=codes,
        intent=assessment.intent,
        compatibility=assessment.compatibility,
        supported_need_ids=list(assessment.supported_need_ids),
        hypothetical_need_ids=list(assessment.hypothetical_need_ids),
        missing_need_ids=list(assessment.missing_need_ids),
        unknown_need_ids=list(assessment.unknown_need_ids),
        relationships=[
            RelationshipDTO.model_validate(
                {
                    "source_id": item.source_id,
                    "need_id": item.need_id,
                    "capability": item.capability,
                    "relation": item.relation,
                    "explanation": item.explanation,
                }
            )
            for item in assessment.relationships
        ],
        report_lines=report,
    )


Principal = Annotated[VerifiedPrincipal, Depends(get_verified_principal)]
Leads = Annotated[LeadStore, Depends(get_lead_store)]
Profiles = Annotated[ProfileStore, Depends(get_profile_store)]

router = APIRouter(
    prefix="/api/v1/workspaces/{workspace_id}/leads",
    tags=["evidence"],
    responses={
        401: {"model": ErrorDTO},
        403: {"model": ErrorDTO},
        404: {"model": ErrorDTO},
        422: {"model": ErrorDTO},
        503: {"model": ErrorDTO},
    },
)


@router.post("/{lead_id}/assessment", response_model=EvidenceReportDTO)
def assess_saved_lead(
    workspace_id: UUID,
    lead_id: UUID,
    payload: AssessSavedLead,
    principal: Principal,
    leads: Leads,
    profiles: Profiles,
) -> EvidenceReportDTO:
    # BOTH reads independently enforce app-user status, verified ownership and
    # session-local RLS. No caller-supplied owner or profile revision is trusted.
    lead = LeadDTO.model_validate(leads.read(principal, workspace_id, lead_id))
    profile = ProfileStateDTO.model_validate(profiles.read(principal, workspace_id))
    return assess_saved_manual_lead(workspace_id, lead, profile, payload)
