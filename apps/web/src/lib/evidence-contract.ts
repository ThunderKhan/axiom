import type { Lead } from "./lead-contract.ts";

export type ManualNeed = Readonly<{
  requirement: string;
  locator: string;
  intent: "buying" | "seeking_solution" | "discussion" | "unknown";
}>;

export type EvidenceAssessment = Readonly<{
  verdict: "research_further" | "skip" | "insufficient_evidence";
  intent: ManualNeed["intent"];
  compatibility: "supported" | "contradicted" | "partial" | "unknown";
  reason_codes: readonly string[];
  report_lines: readonly string[];
  relationships: ReadonlyArray<{
    source_id: string;
    need_id: string;
    capability: string | null;
    relation: "supports_need" | "covers" | "contradicts" | "unverified";
    explanation: string;
  }>;
}>;

export class InvalidEvidenceResponse extends Error {
  constructor() {
    super(
      "Evidence report did not match the verified workspace and saved lead.",
    );
    this.name = "InvalidEvidenceResponse";
  }
}

function record(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function strings(
  value: unknown,
  max: number,
  maxLength: number,
): value is string[] {
  return (
    Array.isArray(value) &&
    value.length <= max &&
    value.every((item) => typeof item === "string" && item.length <= maxLength)
  );
}

function needIds(value: unknown): value is string[] {
  return (
    strings(value, 8, 8) && value.every((item) => /^need-[1-8]$/.test(item))
  );
}

/** Parse network data as untrusted; user-entered evidence must never be rebranded live. */
export function parseManualAssessment(
  raw: unknown,
  workspaceId: string,
  lead: Lead,
): EvidenceAssessment {
  if (
    !record(raw) ||
    raw.workspace_id !== workspaceId ||
    raw.lead_id !== lead.id ||
    raw.lead_version !== lead.version ||
    !Number.isSafeInteger(raw.confirmed_profile_revision) ||
    (raw.confirmed_profile_revision as number) < 1 ||
    raw.source_url !== lead.source_url ||
    raw.source_origin !== "user_provided" ||
    raw.live_source_verified !== false ||
    raw.persisted_assessment !== false ||
    typeof raw.source_recorded_at !== "string" ||
    !Number.isFinite(Date.parse(raw.source_recorded_at)) ||
    Date.parse(raw.source_recorded_at) !== Date.parse(lead.created_at) ||
    !["research_further", "skip", "insufficient_evidence"].includes(
      String(raw.verdict),
    ) ||
    !["buying", "seeking_solution", "discussion", "unknown"].includes(
      String(raw.intent),
    ) ||
    !["supported", "contradicted", "partial", "unknown"].includes(
      String(raw.compatibility),
    ) ||
    !strings(raw.reason_codes, 20, 80) ||
    !raw.reason_codes.includes("USER_PROVIDED_SOURCE_UNVERIFIED") ||
    !strings(raw.report_lines, 40, 2500) ||
    !needIds(raw.supported_need_ids) ||
    !needIds(raw.hypothetical_need_ids) ||
    !needIds(raw.missing_need_ids) ||
    !needIds(raw.unknown_need_ids) ||
    !Array.isArray(raw.relationships) ||
    raw.relationships.length > 24
  ) {
    throw new InvalidEvidenceResponse();
  }
  const linked = raw.relationships.map((item: unknown) => {
    if (
      !record(item) ||
      item.source_id !== lead.id ||
      typeof item.need_id !== "string" ||
      !/^need-[1-8]$/.test(item.need_id) ||
      (item.capability !== null &&
        (typeof item.capability !== "string" ||
          item.capability.length > 120)) ||
      !["supports_need", "covers", "contradicts", "unverified"].includes(
        String(item.relation),
      ) ||
      typeof item.explanation !== "string" ||
      item.explanation.length > 300
    ) {
      throw new InvalidEvidenceResponse();
    }
    return {
      source_id: lead.id,
      need_id: item.need_id,
      capability: item.capability as string | null,
      relation:
        item.relation as EvidenceAssessment["relationships"][number]["relation"],
      explanation: item.explanation,
    };
  });
  return {
    verdict: raw.verdict as EvidenceAssessment["verdict"],
    intent: raw.intent as EvidenceAssessment["intent"],
    compatibility: raw.compatibility as EvidenceAssessment["compatibility"],
    reason_codes: raw.reason_codes,
    report_lines: raw.report_lines,
    relationships: linked,
  };
}
