"""Frozen-evidence comparison; no alternative can become a verified product fact."""

from dataclasses import replace
from datetime import UTC, datetime, timedelta, timezone

import pytest

from app.counterfactual import (
    FeatureAssumption,
    FrozenEvidence,
    Scenario,
    ScenarioInputError,
    compare_scenarios,
)
from app.evidence_engine import Capability, Need, Source, Verdict

NOW = datetime(2026, 11, 24, 8, 0, tzinfo=UTC)


def snapshot() -> FrozenEvidence:
    source = Source(
        id="source-1",
        url="https://example.org/customer-feedback",
        excerpt="Offline sync and data export are needed.",
        retrieved_at=NOW,
        origin="user_provided",
    )
    return FrozenEvidence(
        profile_revision=3,
        launched=True,
        sources=(source,),
        needs=(
            Need("need-1", "offline sync", source.id, "Offline sync", "seeking_solution"),
            Need("need-2", "data export", source.id, "data export", "buying"),
        ),
        capabilities=(
            Capability("offline sync", "missing"),
            Capability("data export", "available"),
        ),
    )


def alternatives() -> tuple[Scenario, ...]:
    return (
        Scenario(
            name="Offline-first",
            features=(FeatureAssumption("offline sync", "add"),),
            pricing="A qualitative starter tier",
            positioning="Offline-first students",
        ),
        Scenario(
            name="Narrower workflow",
            features=(FeatureAssumption("data export", "remove"),),
            positioning="Local note-taking only",
        ),
    )


def test_two_alternatives_use_same_evidence_and_never_modify_baseline() -> None:
    frozen = snapshot()
    result = compare_scenarios(frozen, alternatives())
    assert result.baseline_verdict == Verdict.SKIP
    assert [item.state for item in result.baseline_requirements] == [
        "missing",
        "declared_supported",
    ]
    first, second = result.scenarios
    assert first.baseline_fingerprint == second.baseline_fingerprint == frozen.fingerprint
    assert first.projected_verdict == Verdict.RESEARCH
    assert first.requirements[0].state == "hypothetical"
    assert first.requirements[1].state == "declared_supported"
    assert [(item.need_id, item.before, item.after) for item in first.changes] == [
        ("need-1", "missing", "hypothetical")
    ]
    assert second.projected_verdict == Verdict.SKIP
    assert second.requirements[1].state == "missing"
    assert first.requirements[0].source_id == result.baseline_requirements[0].source_id
    assert frozen.capabilities[0].status == "missing"
    assert compare_scenarios(frozen, alternatives()) == result


def test_snapshot_identity_includes_exact_evidence_and_profile_version() -> None:
    original = snapshot()
    assert replace(original, profile_revision=4).fingerprint != original.fingerprint
    source = original.sources[0]
    edited = replace(source, excerpt="Offline sync and data export are needed. Edited.")
    assert replace(original, sources=(edited,)).fingerprint != original.fingerprint
    later = replace(source, retrieved_at=NOW + timedelta(seconds=1))
    assert replace(original, sources=(later,)).fingerprint != original.fingerprint
    same_instant = replace(
        source, retrieved_at=NOW.astimezone(timezone(timedelta(hours=5, minutes=30)))
    )
    assert replace(original, sources=(same_instant,)).fingerprint == original.fingerprint


def test_unsupported_pricing_positioning_and_uncited_features_are_not_coverage() -> None:
    scenario = Scenario(
        name="Premium",
        features=(FeatureAssumption("video calls", "add"),),
        pricing="Higher monthly price",
        positioning="Enterprise",
    )
    result = compare_scenarios(snapshot(), (scenario, alternatives()[0])).scenarios[0]
    assert result.changes == ()
    assert any("no matching cited requirement" in item for item in result.unsupported_assumptions)
    assert any("Pricing assumption" in item for item in result.unsupported_assumptions)
    assert any("Positioning assumption" in item for item in result.unsupported_assumptions)
    assert any("No predicted revenue" in item for item in result.limitations)


def test_untouched_proposed_live_capability_remains_unknown() -> None:
    original = snapshot()
    frozen = replace(
        original,
        capabilities=(
            Capability("offline sync", "proposed"),
            Capability("data export", "available"),
        ),
    )
    other = Scenario(
        name="Different feature",
        features=(FeatureAssumption("video calls", "add"),),
        positioning="Students",
    )
    result = compare_scenarios(frozen, (other, alternatives()[0]))
    assert result.baseline_requirements[0].state == "unknown"
    assert result.scenarios[0].requirements[0].state == "unknown"
    assert result.scenarios[1].requirements[0].state == "hypothetical"


def test_user_provided_baseline_cannot_claim_verified_pursue() -> None:
    frozen = replace(
        snapshot(),
        capabilities=(
            Capability("offline sync", "available"),
            Capability("data export", "available"),
        ),
    )
    result = compare_scenarios(frozen, alternatives())
    assert result.baseline_verdict == Verdict.RESEARCH
    assert result.scenarios[0].projected_verdict != Verdict.PURSUE


def test_ambiguous_assumptions_and_duplicate_scenario_names_are_rejected() -> None:
    with pytest.raises(ScenarioInputError):
        Scenario(
            name="Conflicting",
            features=(
                FeatureAssumption("Offline sync", "add"),
                FeatureAssumption(" offline  sync ", "remove"),
            ),
            pricing="Low cost",
        )
    with pytest.raises(ScenarioInputError):
        Scenario(name="Only features", features=(FeatureAssumption("offline sync", "add"),))
    with pytest.raises(ScenarioInputError):
        compare_scenarios(snapshot(), alternatives()[:1])
    duplicate = replace(alternatives()[0], name=" offline-first ")
    with pytest.raises(ScenarioInputError):
        compare_scenarios(snapshot(), (alternatives()[0], duplicate))
    with pytest.raises(ScenarioInputError):
        replace(snapshot(), profile_revision=0)
