"""Provenance and four-way decision fixture evaluation; no fake network claims."""

from datetime import UTC, datetime

import pytest

from app.evidence_engine import (
    Capability,
    EvidenceInputError,
    Need,
    Source,
    Verdict,
    assess,
)


def source(excerpt: str = "I need offline sync for my notes") -> Source:
    return Source(
        "hn-123",
        "https://news.ycombinator.com/item?id=123",
        excerpt,
        datetime(2026, 11, 23, tzinfo=UTC),
        "seeded",
    )


def need(intent: str = "buying") -> Need:
    return Need("need-1", "offline sync", "hn-123", "offline sync", intent)


def test_explicit_missing_feature_forces_skip_even_for_buying_intent() -> None:
    result = assess(
        (source(),),
        (need(),),
        (Capability("offline sync", "missing"),),
        launched=True,
    )
    assert result.verdict == Verdict.SKIP
    assert result.compatibility == "contradicted"
    assert result.intent == "buying"
    assert result.missing_need_ids == ("need-1",)
    assert "INCLUDES_SEEDED_EXAMPLE" in result.reason_codes


def test_declared_coverage_is_compatible_but_not_independently_verified() -> None:
    result = assess(
        (source(),),
        (need("seeking_solution"),),
        (Capability("OFFLINE  SYNC", "available"),),
        launched=True,
    )
    assert result.verdict == Verdict.PURSUE
    assert result.supported_need_ids == ("need-1",)
    assert any("not independently verified" in link.explanation for link in result.relationships)


def test_idea_stage_and_launched_product_proposal_are_not_claimed_shipped() -> None:
    scenario = assess(
        (source(),),
        (need(),),
        (Capability("offline sync", "proposed"),),
        launched=False,
    )
    assert scenario.verdict == Verdict.RESEARCH
    assert scenario.reason_codes[0] == "IDEA_STAGE_HYPOTHESIS"
    unavailable = assess(
        (source(),),
        (need(),),
        (Capability("offline sync", "proposed"),),
        launched=True,
    )
    assert unavailable.verdict == Verdict.RESEARCH
    assert unavailable.unknown_need_ids == ("need-1",)


def test_no_sourced_requirement_abstains_and_no_clear_intent_stays_research() -> None:
    assert assess((source(),), (), (), launched=True).verdict == Verdict.INSUFFICIENT
    low_intent = assess(
        (source(),),
        (need("discussion"),),
        (Capability("offline sync", "available"),),
        launched=True,
    )
    assert low_intent.verdict == Verdict.RESEARCH


def test_bad_source_or_missing_exact_locator_never_becomes_a_factual_claim() -> None:
    with pytest.raises(EvidenceInputError):
        assess((), (need(),), (), launched=True)
    with pytest.raises(EvidenceInputError):
        assess((source("unrelated excerpt"),), (need(),), (), launched=True)
    with pytest.raises(EvidenceInputError):
        assess((source(), source()), (), (), launched=True)
    with pytest.raises(EvidenceInputError):
        assess((source(),), (need("invented"),), (), launched=True)


def test_untrusted_origin_and_unaware_timestamp_are_rejected() -> None:
    with pytest.raises(EvidenceInputError):
        Source("id", "http://localhost", "some text", datetime.now(UTC), "live")
    with pytest.raises(EvidenceInputError):
        Source("id", "https://example.org", "some text", datetime(2026, 11, 23), "live")


def test_report_and_relationships_share_real_source_identity() -> None:
    result = assess(
        (source(),),
        (need(),),
        (Capability("offline sync", "available"),),
        launched=True,
    )
    assert result.source_ids == ("hn-123",)
    assert all(link.source_id == "hn-123" for link in result.relationships)
    assert "hn-123" in " ".join(result.report_lines)


def test_hypothetical_coverage_survives_other_unknown_or_missing_needs() -> None:
    example = source("I need offline sync and export")
    first = need()
    second = Need("need-2", "export", "hn-123", "export", "unknown")
    mixed = assess(
        (example,),
        (first, second),
        (Capability("offline sync", "proposed"),),
        launched=False,
    )
    assert mixed.verdict == Verdict.RESEARCH
    assert mixed.hypothetical_need_ids == ("need-1",)
    assert mixed.unknown_need_ids == ("need-2",)
    assert "IDEA_STAGE_HYPOTHESIS" in mixed.reason_codes
    assert mixed.compatibility == "partial"
    assert any(
        link.need_id == "need-1" and link.relation == "unverified"
        and "Hypothetical" in link.explanation
        for link in mixed.relationships
    )
    assert "hypothetical" in " ".join(mixed.report_lines)
    rejected = assess(
        (example,),
        (first, second),
        (Capability("offline sync", "proposed"), Capability("export", "missing")),
        launched=False,
    )
    assert rejected.verdict == Verdict.SKIP
    assert "IDEA_STAGE_HYPOTHESIS" in rejected.reason_codes


@pytest.mark.parametrize(
    "url",
    ["https://", "https://?q=1", "https://example.com:invalid",
     "https://name:pass@example.com", "https://not a host.com",
     "https://example.org\\nother", "http://example.org"],
)
def test_unusable_source_url_rejected_even_without_network_fetch(url: str) -> None:
    with pytest.raises(EvidenceInputError):
        Source("s", url, "Need work", datetime.now(UTC), "seeded")
