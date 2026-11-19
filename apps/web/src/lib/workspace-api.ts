import {
  InvalidWorkspaceResponse,
  parseBootstrap,
  parseWorkspace,
  parseWorkspaceList,
  type Workspace,
} from "./workspace-contract.ts";
import { validatePublicApiBaseUrl } from "./public-api.ts";

type AuthToken = (subject: string) => Promise<string>;
type HttpMethod = "GET" | "POST";

const knownCodes = new Set([
  "AUTH_REQUIRED",
  "ACCOUNT_DISABLED",
  "PROVISIONING_REQUIRED",
  "NOT_FOUND",
  "IDEMPOTENCY_CONFLICT",
  "VERSION_CONFLICT",
  "VALIDATION_FAILED",
  "DATABASE_UNAVAILABLE",
  "AUTH_UNAVAILABLE",
]);

export class WorkspaceApiError extends Error {
  readonly code: string;
  readonly status: number;

  constructor(code: string, status: number) {
    super("Workspace request could not be completed.");
    this.name = "WorkspaceApiError";
    this.code = code;
    this.status = status;
  }
}

export function isUncertainCreateFailure(error: unknown): boolean {
  return (
    error instanceof WorkspaceApiError &&
    ["NETWORK_UNCERTAIN", "DATABASE_UNAVAILABLE", "AUTH_UNAVAILABLE"].includes(
      error.code,
    )
  );
}

function readErrorCode(body: unknown, status: number): string {
  if (
    typeof body === "object" &&
    body !== null &&
    "error" in body &&
    typeof body.error === "object" &&
    body.error !== null &&
    "code" in body.error &&
    typeof body.error.code === "string" &&
    knownCodes.has(body.error.code)
  )
    return body.error.code;
  return status === 401 ? "AUTH_REQUIRED" : "UNEXPECTED_RESPONSE";
}

/** M1 workspace data can only travel through the reviewed FastAPI HTTP API. */
export function createWorkspaceApi(
  rawOrigin: string,
  subject: string,
  getToken: AuthToken,
  fetcher: typeof fetch = fetch,
) {
  const origin = validatePublicApiBaseUrl(rawOrigin);
  async function request(
    path: string,
    method: HttpMethod,
    signal: AbortSignal,
    body?: Record<string, string>,
    idempotencyKey?: string,
  ): Promise<unknown> {
    if (!origin) throw new WorkspaceApiError("DATABASE_UNAVAILABLE", 503);
    if (signal.aborted) throw new WorkspaceApiError("CANCELLED", 0);
    let response: Response;
    try {
      const token = await getToken(subject);
      if (!token || signal.aborted)
        throw new WorkspaceApiError("AUTH_REQUIRED", 401);
      const headers: Record<string, string> = {
        Authorization: "Bearer " + token,
        Accept: "application/json",
      };
      if (body !== undefined) headers["Content-Type"] = "application/json";
      if (idempotencyKey) headers["Idempotency-Key"] = idempotencyKey;
      response = await fetcher(origin + path, {
        method,
        headers,
        body: body === undefined ? undefined : JSON.stringify(body),
        signal: AbortSignal.any([signal, AbortSignal.timeout(12000)]),
        cache: "no-store",
        credentials: "omit",
      });
    } catch (error) {
      if (error instanceof WorkspaceApiError) throw error;
      if (signal.aborted) throw new WorkspaceApiError("CANCELLED", 0);
      // POST may have committed even if transport failed. Never auto-resubmit.
      throw new WorkspaceApiError(
        method === "POST" ? "NETWORK_UNCERTAIN" : "NETWORK_FAILED",
        0,
      );
    }
    let payload: unknown;
    try {
      payload = await response.json();
    } catch {
      throw new InvalidWorkspaceResponse();
    }
    if (!response.ok)
      throw new WorkspaceApiError(
        readErrorCode(payload, response.status),
        response.status,
      );
    return payload;
  }

  return {
    async bootstrap(signal: AbortSignal): Promise<void> {
      const value = await request("/api/v1/me/bootstrap", "POST", signal, {});
      parseBootstrap(value, subject);
    },
    async list(signal: AbortSignal): Promise<Workspace[]> {
      const result: Workspace[] = [];
      const seen = new Set<string>();
      const cursors = new Set<string>();
      let cursor: string | null = null;
      // Hard ceiling prevents a malicious/broken API from causing unbounded traffic.
      for (let page = 0; page < 100; page += 1) {
        const path =
          "/api/v1/workspaces?limit=100" +
          (cursor === null ? "" : "&cursor=" + encodeURIComponent(cursor));
        const response = parseWorkspaceList(await request(path, "GET", signal));
        for (const item of response.items) {
          if (seen.has(item.id)) throw new InvalidWorkspaceResponse();
          seen.add(item.id);
          result.push(item);
        }
        if (response.next_cursor === null) return result;
        if (cursors.has(response.next_cursor))
          throw new InvalidWorkspaceResponse();
        cursors.add(response.next_cursor);
        cursor = response.next_cursor;
      }
      throw new InvalidWorkspaceResponse();
    },
    async read(id: string, signal: AbortSignal): Promise<Workspace> {
      return parseWorkspace(
        await request(
          "/api/v1/workspaces/" + encodeURIComponent(id),
          "GET",
          signal,
        ),
      );
    },
    async create(
      name: string,
      key: string,
      signal: AbortSignal,
    ): Promise<Workspace> {
      return parseWorkspace(
        await request("/api/v1/workspaces", "POST", signal, { name }, key),
      );
    },
  };
}
