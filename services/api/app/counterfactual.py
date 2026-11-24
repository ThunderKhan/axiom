"""Deterministic, non-predictive comparisons on one immutable evidence snapshot."""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from datetime import UTC
from typing import Literal

from app.evidence_engine import Assessment, Capability, Need, Source, Verdict, assess

Coverage = Literal["declared_supported", "hypothetical", "missing", "unknown"]
FeatureAction = Literal["add", "remove"]


class ScenarioInputError(ValueError):
    """Reject ambiguous or unsupported comparison inputs."""


def _key(value: str) -> str:
    return " ".join(value.casefold().split())


def _valid_text(value: str, maximum: int) -> bool:
    return (
        bool(value.strip())
        and len(value) <= maximum
        and all(ord(ch) >= 32 and ord(ch) != 127 for ch in value)
        and not any(0xD800 <= ord(ch) <= 0xDFFF for ch in value)
    )


@dataclass(frozen=True, slots=True)
class FrozenEvidence:
    """Value object only; storage must bind it to an authorized workspace."""

    profile_revision: int
    launched: bool
    sources: tuple[Source, ...]
    needs: tuple[Need, ...]
    capabilities: tuple[Capability, ...]

    def __post_init__(self) -> None:
        if (
            type(self.profile_revision) is not int
            or self.profile_revision < 1
            or type(self.launched) is not bool
            or not isinstance(self.sources, tuple)
            or not isinstance(self.needs, tuple)
            or not isinstance(self.capabilities, tuple)
            or not 1 <= len(self.sources) <= 8
            or len(self.needs) > 8
            or len(self.capabilities) > 64
        ):
            raise ScenarioInputError("Invalid or oversized evidence snapshot")
        assess(self.sources, self.needs, self.capabilities, launched=self.launched)

    @property
    def fingerprint(self) -> str:
        # All evidence, explicit claims and profile revision participate in identity.
        source_data = []
        for source in self.sources:
            value = asdict(source)
            value["retrieved_at"] = source.retrieved_at.astimezone(UTC).isoformat()
            source_data.append(value)
        payload = {
            "schema_version": 1,
            "profile_revision": self.profile_revision,
            "launched": self.launched,
            "sources": source_data,
            "needs": [asdict(need) for need in self.needs],
            "capabilities": [asdict(capability) for capability in self.capabilities],
        }
        canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
        return hashlib.sha256(canonical.encode("ascii")).hexdigest()


@dataclass(frozen=True, slots=True)
class FeatureAssumption:
    name: str
    action: FeatureAction

    def __post_init__(self) -> None:
        if not _valid_text(self.name, 120) or self.action not in ("add", "remove"):
            raise ScenarioInputError("Invalid feature assumption")


@dataclass(frozen=True, slots=True)
class Scenario:
    name: str
    features: tuple[FeatureAssumption, ...]
    pricing: str | None = None
    positioning: str | None = None

    def __post_init__(self) -> None:
        if (
            not _valid_text(self.name, 80)
            or not isinstance(self.features, tuple)
            or not 1 <= len(self.features) <= 8
            or (self.pricing is None and self.positioning is None)
            or (self.pricing is not None and not _valid_text(self.pricing, 300))
            or (self.positioning is not None and not _valid_text(self.positioning, 300))
        ):
            raise ScenarioInputError("Use a name, feature changes and a qualitative assumption")
        if len({_key(feature.name) for feature in self.features}) != len(self.features):
            raise ScenarioInputError("Duplicate or conflicting feature assumptions")


@dataclass(frozen=True, slots=True)
class RequirementCoverage:
    need_id: str
    source_id: str
    requirement: str
    state: Coverage


@dataclass(frozen=True, slots=True)
class CoverageChange:
    need_id: str
    before: Coverage
    after: Coverage


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    name: str
    baseline_fingerprint: str
    assumptions: Scenario
    projected_verdict: Verdict
    requirements: tuple[RequirementCoverage, ...]
    changes: tuple[CoverageChange, ...]
    unsupported_assumptions: tuple[str, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Comparison:
    baseline_fingerprint: str
    baseline_verdict: Verdict
    baseline_requirements: tuple[RequirementCoverage, ...]
    scenarios: tuple[ScenarioResult, ...]


def _coverage(snapshot: FrozenEvidence, outcome: Assessment) -> tuple[RequirementCoverage, ...]:
    supported = set(outcome.supported_need_ids)
    hypothetical = set(outcome.hypothetical_need_ids)
    missing = set(outcome.missing_need_ids)
    result: list[RequirementCoverage] = []
    for need in snapshot.needs:
        state: Coverage = "unknown"
        if need.id in supported:
            state = "declared_supported"
        elif need.id in hypothetical:
            state = "hypothetical"
        elif need.id in missing:
            state = "missing"
        result.append(RequirementCoverage(need.id, need.source_id, need.requirement, state))
    return tuple(result)


def _project(
    snapshot: FrozenEvidence,
    scenario: Scenario,
    baseline: tuple[RequirementCoverage, ...],
    fingerprint: str,
) -> ScenarioResult:
    # A proposed capability of a launched product is unknown in the baseline.
    # Preserve that state in the hypothetical evaluation unless explicitly changed.
    capabilities = {
        _key(cap.name): Capability(
            cap.name,
            "unknown" if snapshot.launched and cap.status == "proposed" else cap.status,
        )
        for cap in snapshot.capabilities
    }
    cited = {_key(need.requirement) for need in snapshot.needs}
    unsupported: list[str] = []
    for feature in scenario.features:
        key = _key(feature.name)
        if key not in cited:
            unsupported.append(f"{feature.name}: no matching cited requirement.")
            continue
        current = capabilities.get(key)
        if feature.action == "add":
            if current is not None and current.status == "available":
                unsupported.append(f"{feature.name}: already declared available; no change.")
                continue
            capabilities[key] = Capability(feature.name, "proposed")
        else:
            capabilities[key] = Capability(feature.name, "missing")
    # Qualitative pricing/positioning cannot change requirement coverage without
    # separately sourced evidence; no demand or commercial forecast is produced.
    if scenario.pricing is not None:
        unsupported.append("Pricing assumption: no evidenced pricing-response model.")
    if scenario.positioning is not None:
        unsupported.append("Positioning assumption: no evidenced market-response model.")

    # Evaluate the alternative as hypothetical, never as a launched factual product.
    projected = assess(
        snapshot.sources, snapshot.needs, tuple(capabilities.values()), launched=False
    )
    after = _coverage(snapshot, projected)
    changes = tuple(
        CoverageChange(before.need_id, before.state, changed.state)
        for before, changed in zip(baseline, after, strict=True)
        if before.state != changed.state
    )
    return ScenarioResult(
        name=scenario.name,
        baseline_fingerprint=fingerprint,
        assumptions=scenario,
        projected_verdict=projected.verdict,
        requirements=after,
        changes=changes,
        unsupported_assumptions=tuple(unsupported),
        limitations=(
            "All changed capabilities are hypothetical; no confirmed profile is modified.",
            "Pricing and positioning are exploratory; they do not alter evidenced coverage.",
            "No predicted revenue, conversion, market share or causal effect.",
        ),
    )


def compare_scenarios(snapshot: FrozenEvidence, scenarios: tuple[Scenario, ...]) -> Comparison:
    """Recompute at least two alternatives on exactly the same source and need values."""
    if (
        not isinstance(scenarios, tuple)
        or not 2 <= len(scenarios) <= 8
        or len({_key(scenario.name) for scenario in scenarios}) != len(scenarios)
    ):
        raise ScenarioInputError("Two to eight uniquely named alternatives are required")
    baseline = assess(
        snapshot.sources, snapshot.needs, snapshot.capabilities, launched=snapshot.launched
    )
    coverage = _coverage(snapshot, baseline)
    fingerprint = snapshot.fingerprint
    verdict = baseline.verdict
    if verdict == Verdict.PURSUE and any(
        source.origin in ("seeded", "user_provided") and source.id in baseline.source_ids
        for source in snapshot.sources
    ):
        verdict = Verdict.RESEARCH
    return Comparison(
        baseline_fingerprint=fingerprint,
        baseline_verdict=verdict,
        baseline_requirements=coverage,
        scenarios=tuple(_project(snapshot, item, coverage, fingerprint) for item in scenarios),
    )
