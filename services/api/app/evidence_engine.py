"""Pure evidence-linked founder decision core, without invented prediction scores."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Literal
from urllib.parse import urlsplit

Origin = Literal["live", "cached", "seeded", "user_provided"]
Intent = Literal["buying", "seeking_solution", "discussion", "unknown"]
Availability = Literal["available", "proposed", "missing", "unknown"]


class EvidenceInputError(ValueError):
    """Refuse material claims with absent or contradictory source references."""


class Verdict(StrEnum):
    PURSUE = "pursue"
    RESEARCH = "research_further"
    SKIP = "skip"
    INSUFFICIENT = "insufficient_evidence"


@dataclass(frozen=True, slots=True)
class Source:
    id: str
    url: str
    excerpt: str
    retrieved_at: datetime
    origin: Origin

    def __post_init__(self) -> None:
        if not self.id or not self.url.startswith("https://"):
            raise EvidenceInputError("Source identity or HTTPS URL is missing")
        try:
            address = urlsplit(self.url)
            if (
                address.scheme != "https"
                or not address.hostname
                or address.username is not None
                or address.password is not None
                or (address.port is not None and address.port < 1)
                or any(character.isspace() for character in address.netloc)
                or any(ord(character) < 32 for character in self.url)
            ):
                raise EvidenceInputError("Source HTTPS authority is malformed")
        except ValueError as exc:
            raise EvidenceInputError("Source HTTPS authority is malformed") from exc
        if not self.excerpt.strip() or len(self.excerpt) > 1500:
            raise EvidenceInputError("Source excerpt missing or oversized")
        if self.retrieved_at.tzinfo is None:
            raise EvidenceInputError("Source timestamp must be timezone-aware")
        if self.origin not in ("live", "cached", "seeded", "user_provided"):
            raise EvidenceInputError("Unknown evidence origin")


@dataclass(frozen=True, slots=True)
class Need:
    id: str
    requirement: str
    source_id: str
    locator: str
    intent: Intent


@dataclass(frozen=True, slots=True)
class Capability:
    name: str
    status: Availability


@dataclass(frozen=True, slots=True)
class Relationship:
    source_id: str
    need_id: str
    capability: str | None
    relation: Literal["supports_need", "covers", "contradicts", "unverified"]
    explanation: str


@dataclass(frozen=True, slots=True)
class Assessment:
    verdict: Verdict
    reason_codes: tuple[str, ...]
    intent: Intent
    compatibility: Literal["supported", "contradicted", "partial", "unknown"]
    supported_need_ids: tuple[str, ...]
    hypothetical_need_ids: tuple[str, ...]
    missing_need_ids: tuple[str, ...]
    unknown_need_ids: tuple[str, ...]
    source_ids: tuple[str, ...]
    relationships: tuple[Relationship, ...]
    report_lines: tuple[str, ...]


def _key(value: str) -> str:
    # Exact normalized capability equality is intentional; no semantic guesses.
    return " ".join(value.casefold().split())


def _contains_full_term(text: str, term: str) -> bool:
    normalized = _key(term)
    if not normalized:
        return False
    return re.search(
        r"(?<!\\w)" + re.escape(normalized) + r"(?!\\w)",
        _key(text),
    ) is not None


def assess(
    sources: tuple[Source, ...],
    needs: tuple[Need, ...],
    capabilities: tuple[Capability, ...],
    *,
    launched: bool,
) -> Assessment:
    """Evaluate only explicitly sourced requirements and declared capabilities."""
    by_source = {source.id: source for source in sources}
    by_need = {need.id: need for need in needs}
    by_capability = {_key(cap.name): cap for cap in capabilities}
    if (
        len(by_source) != len(sources)
        or len(by_need) != len(needs)
        or len(by_capability) != len(capabilities)
    ):
        raise EvidenceInputError("Duplicate identities")
    for declared_capability in capabilities:
        if not declared_capability.name.strip() or declared_capability.status not in (
            "available",
            "proposed",
            "missing",
            "unknown",
        ):
            raise EvidenceInputError("Invalid declared capability")
    for need in needs:
        source = by_source.get(need.source_id)
        if not need.id or not need.requirement.strip() or source is None:
            raise EvidenceInputError("Missing cited requirement or source")
        if need.intent not in ("buying", "seeking_solution", "discussion", "unknown"):
            raise EvidenceInputError("Unknown intent")
        if (
            not need.locator.strip()
            or not _contains_full_term(source.excerpt, need.locator)
            or not _contains_full_term(need.locator, need.requirement)
        ):
            raise EvidenceInputError("Requirement lacks actual source locator")
    if not needs:
        return Assessment(
            Verdict.INSUFFICIENT,
            ("NO_SOURCED_REQUIREMENTS",),
            "unknown",
            "unknown",
            (),
            (),
            (),
            (),
            tuple(by_source),
            (),
            ("No source-linked customer requirements were supplied.",),
        )

    supported: list[str] = []
    hypothetical: list[str] = []
    missing: list[str] = []
    unknown: list[str] = []
    links: list[Relationship] = []
    report: list[str] = []
    for need in needs:
        source = by_source[need.source_id]
        links.append(
            Relationship(source.id, need.id, None, "supports_need", "Exact source locator")
        )
        cap = by_capability.get(_key(need.requirement))
        if cap is None or cap.status == "unknown":
            unknown.append(need.id)
            report.append(f"{need.requirement}: unknown capability.")
        elif cap.status == "missing":
            missing.append(need.id)
            links.append(
                Relationship(
                    source.id,
                    need.id,
                    cap.name,
                    "contradicts",
                    "Founder declares missing",
                )
            )
            report.append(f"{need.requirement}: explicitly missing.")
        elif cap.status == "proposed" and not launched:
            hypothetical.append(need.id)
            links.append(
                Relationship(
                    source.id,
                    need.id,
                    cap.name,
                    "unverified",
                    "Hypothetical idea-stage coverage; proposed, not shipped",
                )
            )
            report.append(
                f"{need.requirement}: hypothetical coverage only; feature not shipped."
            )
        elif cap.status == "proposed" and launched:
            unknown.append(need.id)
            links.append(Relationship(source.id, need.id, cap.name, "unverified", "Not shipped"))
            report.append(f"{need.requirement}: proposed but not available.")
        else:
            supported.append(need.id)
            links.append(
                Relationship(
                    source.id,
                    need.id,
                    cap.name,
                    "covers",
                    "Founder-declared capability; not independently verified",
                )
            )
            report.append(f"{need.requirement}: declared compatible.")
        report.append(
            f"Source {source.id}: {source.url}; origin={source.origin}; "
            f"retrieved={source.retrieved_at.isoformat()}."
        )
    intent: Intent = "unknown"
    if any(need.intent == "buying" for need in needs):
        intent = "buying"
    elif any(need.intent == "seeking_solution" for need in needs):
        intent = "seeking_solution"
    elif any(need.intent == "discussion" for need in needs):
        intent = "discussion"
    codes: tuple[str, ...]
    compatibility: Literal["supported", "contradicted", "partial", "unknown"]
    if missing:
        verdict = Verdict.SKIP
        codes = ("EXPLICIT_MISSING_FEATURE",)
        compatibility = "contradicted"
    elif unknown:
        verdict = Verdict.RESEARCH
        codes = ("UNKNOWN_CAPABILITY",)
        compatibility = "partial" if supported or hypothetical else "unknown"
    elif hypothetical:
        verdict = Verdict.RESEARCH
        codes = ("IDEA_STAGE_HYPOTHESIS",)
        compatibility = "partial"
    elif launched and intent in ("buying", "seeking_solution"):
        verdict = Verdict.PURSUE
        codes = ("SOLUTION_INTENT_AND_DECLARED_COVERAGE",)
        compatibility = "supported"
    else:
        verdict = Verdict.RESEARCH
        codes = ("IDEA_STAGE_HYPOTHESIS",) if not launched else ("NO_CLEAR_SOLUTION_INTENT",)
        compatibility = "supported"
    if hypothetical and "IDEA_STAGE_HYPOTHESIS" not in codes:
        codes = (*codes, "IDEA_STAGE_HYPOTHESIS")
    if any(by_source[need.source_id].origin == "seeded" for need in needs):
        codes = (*codes, "INCLUDES_SEEDED_EXAMPLE")
    return Assessment(
        verdict,
        codes,
        intent,
        compatibility,
        tuple(supported),
        tuple(hypothetical),
        tuple(missing),
        tuple(unknown),
        tuple(dict.fromkeys(need.source_id for need in needs)),
        tuple(links),
        tuple(report),
    )
