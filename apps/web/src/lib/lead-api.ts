import {
  parseManualAssessment,
  type EvidenceAssessment,
  type ManualNeed,
} from "./evidence-contract.ts";
import {
  InvalidLeadResponse,
  parseCreatedLead,
  parseLead,
  parseLeadEvents,
  parseLeadList,
  type Lead,
  type LeadEvent,
  type LeadStage,
} from "./lead-contract.ts";
import { validatePublicApiBaseUrl } from "./public-api.ts";
import {
  parseSavedComparison,
  type SavedComparison,
  type ScenarioRequest,
} from "./scenario-contract.ts";
import {
  parseCompetitorPreview,
  parseSourcePreview,
  type ClaimCandidate,
  type CompetitorPreview,
  type SourcePreview,
} from "./source-preview-contract.ts";
import { isWorkspaceId } from "./workspace-contract.ts";

type AuthToken = (subject: string) => Promise<string>;
type Method = "GET" | "POST" | "PATCH" | "DELETE";

export type NewLead = Readonly<{
  title: string;
  source_url: string;
  source_excerpt: string;
}>;

export type LeadEdit = Readonly<{
  expected_version: number;
  stage?: LeadStage;
  note?: string;
  follow_up_at?: string | null;
  follow_up_done?: boolean;
  unsent_draft?: string;
}>;

export class LeadApiError extends Error {
  readonly status: number;
  readonly code: string;

  constructor(code: string, status: number) {
    super("The private lead request could not be completed.");
    this.name = "LeadApiError";
    this.code = code;
    this.status = status;
  }
}

const allowedCodes = new Set([
  "AUTH_REQUIRED",
  "AUTH_UNAVAILABLE",
  "ACCOUNT_DISABLED",
  "NOT_FOUND",
  "VALIDATION_FAILED",
  "VERSION_CONFLICT",
  "IDEMPOTENCY_CONFLICT",
  "LEAD_ALREADY_SAVED",
  "PROFILE_INCOMPLETE",
  "DATABASE_UNAVAILABLE",
  "SOURCE_BLOCKED",
  "SOURCE_RATE_LIMITED",
  "SOURCE_UNAVAILABLE",
]);

function serverCode(raw: unknown, status: number): string {
  if (
    raw !== null &&
    typeof raw === "object" &&
    "error" in raw &&
    raw.error !== null &&
    typeof raw.error === "object" &&
    "code" in raw.error &&
    typeof raw.error.code === "string" &&
    allowedCodes.has(raw.error.code)
  )
    return raw.error.code;
  return status === 401 ? "AUTH_REQUIRED" : "UNEXPECTED_RESPONSE";
}

export function createLeadApi(
  rawOrigin: string,
  subject: string,
  getToken: AuthToken,
  fetcher: typeof fetch = fetch,
) {
  const origin = validatePublicApiBaseUrl(rawOrigin);

  function pathFor(workspaceId: string, leadId?: string): string {
    if (!isWorkspaceId(workspaceId) || (leadId && !isWorkspaceId(leadId)))
      throw new InvalidLeadResponse();
    return (
      "/api/v1/workspaces/" +
      encodeURIComponent(workspaceId) +
      "/leads" +
      (leadId ? "/" + encodeURIComponent(leadId) : "")
    );
  }

  async function send(
    path: string,
    method: Method,
    signal: AbortSignal,
    body?: unknown,
    key?: string,
  ): Promise<unknown> {
    if (!origin) throw new LeadApiError("DATABASE_UNAVAILABLE", 503);
    if (signal.aborted) throw new LeadApiError("CANCELLED", 0);
    let response: Response;
    try {
      const token = await getToken(subject);
      if (!token || signal.aborted)
        throw new LeadApiError("AUTH_REQUIRED", 401);
      const headers: Record<string, string> = {
        Authorization: "Bearer " + token,
        Accept: "application/json",
      };
      if (body !== undefined) headers["Content-Type"] = "application/json";
      if (key) headers["Idempotency-Key"] = key;
      response = await fetcher(origin + path, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
        cache: "no-store",
        credentials: "omit",
        signal: AbortSignal.any([signal, AbortSignal.timeout(12000)]),
      });
    } catch (error) {
      if (error instanceof LeadApiError) throw error;
      if (signal.aborted) throw new LeadApiError("CANCELLED", 0);
      throw new LeadApiError(
        method === "GET" ? "NETWORK_FAILED" : "NETWORK_UNCERTAIN",
        0,
      );
    }
    if (response.status === 204 && method === "DELETE") return null;
    let data: unknown = null;
    try {
      const text = await response.text();
      if (text.length > 1_000_000) throw new InvalidLeadResponse();
      data = JSON.parse(text) as unknown;
    } catch {
      if (response.ok) {
        if (method !== "GET") throw new LeadApiError("NETWORK_UNCERTAIN", 0);
        throw new InvalidLeadResponse();
      }
      // The HTTP status remains authoritative when an error is malformed.
    }
    if (!response.ok) {
      throw new LeadApiError(
        serverCode(data, response.status),
        response.status,
      );
    }
    return data;
  }

  function sourcePath(workspaceId: string): string {
    if (!isWorkspaceId(workspaceId)) throw new InvalidLeadResponse();
    return "/api/v1/workspaces/" + encodeURIComponent(workspaceId);
  }

  return {
    async previewSource(
      workspaceId: string,
      url: string,
      signal: AbortSignal,
    ): Promise<SourcePreview> {
      return parseSourcePreview(
        await send(
          sourcePath(workspaceId) + "/research/public-url/preview",
          "POST",
          signal,
          { url },
        ),
        workspaceId,
        url,
      );
    },
    async previewCompetitor(
      workspaceId: string,
      url: string,
      name: string,
      candidates: readonly ClaimCandidate[],
      signal: AbortSignal,
    ): Promise<CompetitorPreview> {
      return parseCompetitorPreview(
        await send(
          sourcePath(workspaceId) + "/competitors/preview",
          "POST",
          signal,
          { url, name, confirmed: true, candidates },
        ),
        workspaceId,
        url,
        name,
        candidates,
      );
    },
    async list(workspaceId: string, signal: AbortSignal): Promise<Lead[]> {
      return parseLeadList(
        await send(pathFor(workspaceId) + "?limit=100", "GET", signal),
        workspaceId,
      );
    },
    async read(
      workspaceId: string,
      leadId: string,
      signal: AbortSignal,
    ): Promise<Lead> {
      const item = parseLead(
        await send(pathFor(workspaceId, leadId), "GET", signal),
        workspaceId,
      );
      if (item.id !== leadId) throw new InvalidLeadResponse();
      return item;
    },
    async create(
      workspaceId: string,
      payload: NewLead,
      key: string,
      signal: AbortSignal,
    ): Promise<Lead & { already_exists: boolean }> {
      if (!/^[A-Za-z0-9][A-Za-z0-9_-]{7,127}$/.test(key))
        throw new InvalidLeadResponse();
      const response = await send(
        pathFor(workspaceId),
        "POST",
        signal,
        payload,
        key,
      );
      try {
        return parseCreatedLead(response, workspaceId);
      } catch (error) {
        if (error instanceof InvalidLeadResponse)
          throw new LeadApiError("NETWORK_UNCERTAIN", 0);
        throw error;
      }
    },
    async update(
      workspaceId: string,
      leadId: string,
      payload: LeadEdit,
      signal: AbortSignal,
    ): Promise<Lead> {
      const response = await send(
        pathFor(workspaceId, leadId),
        "PATCH",
        signal,
        payload,
      );
      try {
        const item = parseLead(response, workspaceId);
        if (item.id !== leadId) throw new InvalidLeadResponse();
        return item;
      } catch (error) {
        if (error instanceof InvalidLeadResponse)
          throw new LeadApiError("NETWORK_UNCERTAIN", 0);
        throw error;
      }
    },
    async archive(
      workspaceId: string,
      leadId: string,
      expectedVersion: number,
      signal: AbortSignal,
    ): Promise<void> {
      if (!Number.isSafeInteger(expectedVersion) || expectedVersion < 1)
        throw new InvalidLeadResponse();
      await send(
        pathFor(workspaceId, leadId) +
          "?expected_version=" +
          String(expectedVersion),
        "DELETE",
        signal,
      );
    },
    /** Read-only computation; never fetches a website or writes a snapshot. */
    async assess(
      workspaceId: string,
      lead: Lead,
      needs: readonly ManualNeed[],
      signal: AbortSignal,
    ): Promise<EvidenceAssessment> {
      if (lead.workspace_id !== workspaceId || needs.length > 8)
        throw new InvalidLeadResponse();
      const payload = { needs };
      return parseManualAssessment(
        await send(
          pathFor(workspaceId, lead.id) + "/assessment",
          "POST",
          signal,
          payload,
        ),
        workspaceId,
        lead,
      );
    },
    async saveComparison(
      workspaceId: string,
      lead: Lead,
      payload: ScenarioRequest,
      key: string,
      signal: AbortSignal,
    ): Promise<SavedComparison> {
      if (
        lead.workspace_id !== workspaceId ||
        lead.version !== payload.expected_lead_version ||
        !/^[A-Za-z0-9][A-Za-z0-9_-]{7,127}$/.test(key)
      )
        throw new InvalidLeadResponse();
      const response = await send(
        pathFor(workspaceId, lead.id) + "/scenario-comparisons",
        "POST",
        signal,
        payload,
        key,
      );
      try {
        return parseSavedComparison(response, workspaceId, lead, payload);
      } catch {
        throw new LeadApiError("NETWORK_UNCERTAIN", 0);
      }
    },
    async listComparisons(
      workspaceId: string,
      lead: Lead,
      signal: AbortSignal,
    ): Promise<SavedComparison[]> {
      if (lead.workspace_id !== workspaceId) throw new InvalidLeadResponse();
      const raw = await send(
        pathFor(workspaceId, lead.id) + "/scenario-comparisons?limit=5",
        "GET",
        signal,
      );
      if (
        raw === null ||
        typeof raw !== "object" ||
        !("items" in raw) ||
        !Array.isArray(raw.items) ||
        raw.items.length > 5
      )
        throw new InvalidLeadResponse();
      return raw.items.map((item: unknown) =>
        parseSavedComparison(item, workspaceId, lead),
      );
    },
    async history(
      workspaceId: string,
      leadId: string,
      signal: AbortSignal,
    ): Promise<LeadEvent[]> {
      return parseLeadEvents(
        await send(pathFor(workspaceId, leadId) + "/activity", "GET", signal),
      );
    },
  };
}
