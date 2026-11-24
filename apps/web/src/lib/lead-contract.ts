import { isWorkspaceId } from "./workspace-contract.ts";

export const leadStages = [
  "spotted",
  "qualified",
  "contacted",
  "closed_lost",
] as const;

export type LeadStage = (typeof leadStages)[number];

export type Lead = Readonly<{
  id: string;
  workspace_id: string;
  title: string;
  source_url: string;
  source_excerpt: string;
  source_origin: "user_provided" | "live";
  research_run_id?: string;
  research_signal_id?: string;
  stage: LeadStage;
  note: string;
  follow_up_at: string | null;
  follow_up_done: boolean;
  unsent_draft: string;
  version: number;
  created_at: string;
  updated_at: string;
}>;

export type LeadEvent = Readonly<{
  id: string;
  actor_id: string;
  event_type: "created" | "updated" | "archived";
  changed_fields: readonly string[];
  created_at: string;
}>;

export class InvalidLeadResponse extends Error {
  constructor() {
    super("Invalid or mismatched CRM response.");
    this.name = "InvalidLeadResponse";
  }
}

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function timestamp(value: unknown): value is string {
  return (
    typeof value === "string" &&
    /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|[+-]\d{2}:\d{2})$/.test(
      value,
    ) &&
    Number.isFinite(Date.parse(value))
  );
}

export function isLeadStage(value: unknown): value is LeadStage {
  return leadStages.some((stage) => stage === value);
}

export function parseLead(value: unknown, workspaceId: string): Lead {
  if (
    !record(value) ||
    !isWorkspaceId(value.id) ||
    value.workspace_id !== workspaceId ||
    typeof value.title !== "string" ||
    [...value.title].length < 1 ||
    [...value.title].length > 180 ||
    typeof value.source_url !== "string" ||
    value.source_url.length > 2048 ||
    !value.source_url.startsWith("https://") ||
    typeof value.source_excerpt !== "string" ||
    [...value.source_excerpt].length < 1 ||
    [...value.source_excerpt].length > 500 ||
    (value.source_origin !== "user_provided" &&
      value.source_origin !== "live") ||
    (value.source_origin === "live" &&
      (!isWorkspaceId(value.research_run_id) ||
        !isWorkspaceId(value.research_signal_id))) ||
    (value.source_origin === "user_provided" &&
      (value.research_run_id != null || value.research_signal_id != null)) ||
    !isLeadStage(value.stage) ||
    typeof value.note !== "string" ||
    [...value.note].length > 2000 ||
    (value.follow_up_at !== null && !timestamp(value.follow_up_at)) ||
    typeof value.follow_up_done !== "boolean" ||
    (value.follow_up_done && value.follow_up_at === null) ||
    typeof value.unsent_draft !== "string" ||
    [...value.unsent_draft].length > 4000 ||
    !Number.isSafeInteger(value.version) ||
    (value.version as number) < 1 ||
    !timestamp(value.created_at) ||
    !timestamp(value.updated_at)
  ) {
    throw new InvalidLeadResponse();
  }
  return {
    id: value.id,
    workspace_id: workspaceId,
    title: value.title,
    source_url: value.source_url,
    source_excerpt: value.source_excerpt,
    source_origin: value.source_origin,
    ...(value.source_origin === "live"
      ? {
          research_run_id: value.research_run_id as string,
          research_signal_id: value.research_signal_id as string,
        }
      : {}),
    stage: value.stage,
    note: value.note,
    follow_up_at: value.follow_up_at,
    follow_up_done: value.follow_up_done,
    unsent_draft: value.unsent_draft,
    version: value.version as number,
    created_at: value.created_at,
    updated_at: value.updated_at,
  };
}

export function parseLeadList(value: unknown, workspaceId: string): Lead[] {
  if (!record(value) || !Array.isArray(value.items) || value.items.length > 100)
    throw new InvalidLeadResponse();
  const leads = value.items.map((item: unknown) =>
    parseLead(item, workspaceId),
  );
  if (new Set(leads.map((lead) => lead.id)).size !== leads.length)
    throw new InvalidLeadResponse();
  return leads;
}

export function parseCreatedLead(
  value: unknown,
  workspaceId: string,
): Lead & { already_exists: boolean } {
  const lead = parseLead(value, workspaceId);
  if (!record(value) || typeof value.already_exists !== "boolean")
    throw new InvalidLeadResponse();
  return { ...lead, already_exists: value.already_exists };
}

export function parseLeadEvents(value: unknown): LeadEvent[] {
  if (!record(value) || !Array.isArray(value.items) || value.items.length > 100)
    throw new InvalidLeadResponse();
  return value.items.map((raw: unknown) => {
    if (
      !record(raw) ||
      !isWorkspaceId(raw.id) ||
      !isWorkspaceId(raw.actor_id) ||
      !["created", "updated", "archived"].includes(String(raw.event_type)) ||
      !Array.isArray(raw.changed_fields) ||
      !raw.changed_fields.every(
        (field: unknown) => typeof field === "string" && field.length <= 64,
      ) ||
      !timestamp(raw.created_at)
    ) {
      throw new InvalidLeadResponse();
    }
    return {
      id: raw.id,
      actor_id: raw.actor_id,
      event_type: raw.event_type as LeadEvent["event_type"],
      changed_fields: raw.changed_fields as string[],
      created_at: raw.created_at,
    };
  });
}

/** Server-side Pydantic remains authoritative. This only protects client edits. */
export function normalizeLeadText(value: string, limit: number): string {
  if ([...value].length > limit || /[\u0000\uD800-\uDFFF]/u.test(value))
    throw new Error("The input contains too much text or invalid characters.");
  return value;
}

/** An unchanged browser-local wall time must retain the original absolute instant. */
export function resolveFollowUpInstant(
  original: string | null,
  initialLocal: string,
  editedLocal: string,
): string | null {
  if (!editedLocal) return null;
  if (original && editedLocal === initialLocal) return original;
  const chosen = new Date(editedLocal);
  if (!Number.isFinite(chosen.getTime()))
    throw new Error("Enter a valid local follow-up date and time.");
  return chosen.toISOString();
}
