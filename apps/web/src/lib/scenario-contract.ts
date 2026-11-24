import type { Lead } from "./lead-contract.ts";
import type { ManualNeed } from "./evidence-contract.ts";
import { isWorkspaceId } from "./workspace-contract.ts";

export type ScenarioAssumption = Readonly<{
  name: string;
  features: readonly { name: string; action: "add" | "remove" }[];
  pricing: string | null;
  positioning: string | null;
}>;

export type ScenarioRequest = Readonly<{
  needs: readonly ManualNeed[];
  expected_lead_version: number;
  expected_profile_revision: number;
  scenarios: readonly ScenarioAssumption[];
}>;

type Coverage = {
  requirement: string;
  need_id: string;
  state: string;
};

type Alternative = {
  name: string;
  projected_verdict: string;
  assumptions: ScenarioAssumption;
  requirements: Coverage[];
  unsupported_assumptions: string[];
  limitations: string[];
};

export type SavedComparison = {
  id: string;
  lead_version: number;
  confirmed_profile_revision: number;
  created_at: string;
  source_excerpt: string;
  comparison: {
    baseline_fingerprint: string;
    baseline_verdict: string;
    baseline_requirements: Coverage[];
    scenarios: Alternative[];
  };
};

export class InvalidScenarioResponse extends Error {
  constructor() {
    super("Saved comparison did not match the authorized evidence.");
    this.name = "InvalidScenarioResponse";
  }
}

function record(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function positive(value: unknown): value is number {
  return typeof value === "number" && Number.isSafeInteger(value) && value > 0;
}

function bounded(value: unknown, maximum: number): value is string {
  return typeof value === "string" && Array.from(value).length <= maximum;
}

function texts(value: unknown): value is string[] {
  return (
    Array.isArray(value) &&
    value.length <= 20 &&
    value.every((item: unknown) => bounded(item, 400))
  );
}

function coverage(raw: unknown, leadId: string): Coverage[] {
  if (!Array.isArray(raw) || raw.length > 8) throw new InvalidScenarioResponse();
  const result = raw.map((item: unknown) => {
    if (
      !record(item) ||
      item.source_id !== leadId ||
      !bounded(item.need_id, 8) ||
      !/^need-[1-8]$/.test(item.need_id) ||
      !bounded(item.requirement, 120) ||
      !bounded(item.state, 24) ||
      !["declared_supported", "hypothetical", "missing", "unknown"].includes(
        item.state,
      )
    )
      throw new InvalidScenarioResponse();
    return {
      need_id: item.need_id,
      requirement: item.requirement,
      state: item.state,
    };
  });
  if (new Set(result.map((item) => item.need_id)).size !== result.length)
    throw new InvalidScenarioResponse();
  return result;
}

function parseAssumptions(raw: unknown, name: string): ScenarioAssumption {
  if (
    !record(raw) ||
    raw.name !== name ||
    !Array.isArray(raw.features) ||
    raw.features.length < 1 ||
    raw.features.length > 8 ||
    (raw.pricing !== null && !bounded(raw.pricing, 300)) ||
    (raw.positioning !== null && !bounded(raw.positioning, 300)) ||
    (raw.pricing === null && raw.positioning === null)
  )
    throw new InvalidScenarioResponse();
  const features = raw.features.map((item: unknown) => {
    if (
      !record(item) ||
      !bounded(item.name, 120) ||
      !item.name.trim() ||
      (item.action !== "add" && item.action !== "remove")
    )
      throw new InvalidScenarioResponse();
    return { name: item.name, action: item.action } as const;
  });
  return { name, features, pricing: raw.pricing, positioning: raw.positioning };
}

export function parseSavedComparison(
  raw: unknown,
  workspaceId: string,
  lead: Lead,
  request?: ScenarioRequest,
): SavedComparison {
  if (
    !record(raw) ||
    !isWorkspaceId(raw.id) ||
    raw.workspace_id !== workspaceId ||
    raw.lead_id !== lead.id ||
    raw.source_origin !== "user_provided" ||
    raw.live_source_verified !== false ||
    raw.persisted_comparison !== true ||
    raw.source_url !== lead.source_url ||
    raw.source_excerpt !== lead.source_excerpt ||
    !positive(raw.lead_version) ||
    raw.lead_version > lead.version ||
    !positive(raw.confirmed_profile_revision) ||
    !bounded(raw.created_at, 64) ||
    !Number.isFinite(Date.parse(raw.created_at)) ||
    !bounded(raw.source_recorded_at, 64) ||
    Date.parse(raw.source_recorded_at) !== Date.parse(lead.created_at) ||
    !record(raw.comparison)
  )
    throw new InvalidScenarioResponse();
  const data = raw.comparison;
  if (
    !bounded(data.baseline_fingerprint, 64) ||
    !/^[a-f0-9]{64}$/.test(data.baseline_fingerprint) ||
    !bounded(data.baseline_verdict, 24) ||
    !["research_further", "skip", "insufficient_evidence"].includes(
      data.baseline_verdict,
    ) ||
    !Array.isArray(data.scenarios) ||
    data.scenarios.length < 2 ||
    data.scenarios.length > 8
  )
    throw new InvalidScenarioResponse();
  const baseline = coverage(data.baseline_requirements, lead.id);
  const fingerprint = data.baseline_fingerprint;
  const scenarios = data.scenarios.map((item: unknown) => {
    if (
      !record(item) ||
      item.baseline_fingerprint !== fingerprint ||
      !bounded(item.name, 80) ||
      !item.name.trim() ||
      !bounded(item.projected_verdict, 24) ||
      !["pursue", "research_further", "skip", "insufficient_evidence"].includes(
        item.projected_verdict,
      ) ||
      !texts(item.unsupported_assumptions) ||
      !texts(item.limitations) ||
      item.limitations.length === 0
    )
      throw new InvalidScenarioResponse();
    const requirements = coverage(item.requirements, lead.id);
    if (
      requirements.length !== baseline.length ||
      requirements.some(
        (need, index) =>
          need.need_id !== baseline[index].need_id ||
          need.requirement !== baseline[index].requirement,
      )
    )
      throw new InvalidScenarioResponse();
    return {
      name: item.name,
      projected_verdict: item.projected_verdict,
      assumptions: parseAssumptions(item.assumptions, item.name),
      requirements,
      unsupported_assumptions: item.unsupported_assumptions,
      limitations: item.limitations,
    };
  });
  if (
    new Set(scenarios.map((item) => item.name.trim().toLowerCase())).size !==
    scenarios.length
  )
    throw new InvalidScenarioResponse();
  if (
    request &&
    (raw.lead_version !== request.expected_lead_version ||
      raw.confirmed_profile_revision !== request.expected_profile_revision ||
      request.scenarios.length !== scenarios.length ||
      request.scenarios.some((item, index) => {
        const saved = scenarios[index].assumptions;
        return (
          item.name !== saved.name ||
          item.pricing !== saved.pricing ||
          item.positioning !== saved.positioning ||
          item.features.length !== saved.features.length ||
          item.features.some(
            (feature, i) =>
              feature.name !== saved.features[i].name ||
              feature.action !== saved.features[i].action,
          )
        );
      }))
  )
    throw new InvalidScenarioResponse();
  return {
    id: raw.id,
    lead_version: raw.lead_version,
    confirmed_profile_revision: raw.confirmed_profile_revision,
    created_at: raw.created_at,
    source_excerpt: raw.source_excerpt,
    comparison: {
      baseline_fingerprint: fingerprint,
      baseline_verdict: data.baseline_verdict,
      baseline_requirements: baseline,
      scenarios,
    },
  };
}
