import {
  emptyProfileAnswers,
  type ProfileAnswers,
} from "./profile-questions.ts";
import { isWorkspaceId } from "./workspace-contract.ts";
import { validatePublicApiBaseUrl } from "./public-api.ts";

type AuthToken = (subject: string) => Promise<string>;

export type ProfileSnapshot = Readonly<{
  id: string;
  revision: number;
  answers: ProfileAnswers;
  confirmed_at: string;
}>;

export type ProfileState = Readonly<{
  draft_revision: number;
  answers: ProfileAnswers | null;
  confirmed_revision: number;
  confirmed: ProfileSnapshot | null;
}>;

export class InvalidProfileResponse extends Error {
  constructor() {
    super("Invalid profile API response.");
    this.name = "InvalidProfileResponse";
  }
}

export class ProfileApiError extends Error {
  constructor(
    readonly code: string,
    readonly status: number,
  ) {
    super("Profile request failed.");
    this.name = "ProfileApiError";
  }
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function parseAnswers(value: unknown): ProfileAnswers {
  if (!isObject(value)) throw new InvalidProfileResponse();
  const stage = value.stage;
  if (stage !== null && stage !== "idea" && stage !== "live")
    throw new InvalidProfileResponse();
  const required = Object.keys(emptyProfileAnswers).filter(
    (key) => key !== "stage",
  );
  if (
    Object.keys(value).length !== Object.keys(emptyProfileAnswers).length ||
    required.some(
      (key) => typeof value[key] !== "string" || value[key].length > 2048,
    )
  ) {
    throw new InvalidProfileResponse();
  }
  return value as ProfileAnswers;
}

export function parseProfileState(value: unknown): ProfileState {
  if (
    !isObject(value) ||
    !Number.isSafeInteger(value.draft_revision) ||
    !Number.isSafeInteger(value.confirmed_revision) ||
    (value.draft_revision as number) < 0 ||
    (value.confirmed_revision as number) < 0
  ) {
    throw new InvalidProfileResponse();
  }
  const answers = value.answers === null ? null : parseAnswers(value.answers);
  const confirmed = value.confirmed;
  let snapshot: ProfileSnapshot | null = null;
  if (confirmed !== null) {
    if (
      !isObject(confirmed) ||
      !isWorkspaceId(confirmed.id) ||
      !Number.isSafeInteger(confirmed.revision) ||
      confirmed.revision !== value.confirmed_revision ||
      typeof confirmed.confirmed_at !== "string" ||
      !Number.isFinite(Date.parse(confirmed.confirmed_at))
    ) {
      throw new InvalidProfileResponse();
    }
    snapshot = {
      id: confirmed.id,
      revision: confirmed.revision as number,
      answers: parseAnswers(confirmed.answers),
      confirmed_at: confirmed.confirmed_at,
    };
  } else if (value.confirmed_revision !== 0) {
    throw new InvalidProfileResponse();
  }
  if (
    (value.draft_revision === 0 && answers !== null) ||
    (value.draft_revision !== 0 && answers === null)
  ) {
    throw new InvalidProfileResponse();
  }
  return {
    draft_revision: value.draft_revision as number,
    answers,
    confirmed_revision: value.confirmed_revision as number,
    confirmed: snapshot,
  };
}

function errorCode(value: unknown, status: number): string {
  if (
    isObject(value) &&
    isObject(value.error) &&
    typeof value.error.code === "string" &&
    [
      "AUTH_REQUIRED",
      "AUTH_UNAVAILABLE",
      "DATABASE_UNAVAILABLE",
      "ACCOUNT_DISABLED",
      "PROVISIONING_REQUIRED",
      "VERSION_CONFLICT",
      "VALIDATION_FAILED",
      "PROFILE_INCOMPLETE",
      "NOT_FOUND",
    ].includes(value.error.code)
  ) {
    return value.error.code;
  }
  return status === 401 ? "AUTH_REQUIRED" : "UNEXPECTED_RESPONSE";
}

export function createProfileApi(
  originText: string,
  subject: string,
  getToken: AuthToken,
  fetcher: typeof fetch = fetch,
) {
  const origin = validatePublicApiBaseUrl(originText);

  async function request(
    workspaceId: string,
    path: string,
    method: "GET" | "PUT" | "POST",
    signal: AbortSignal,
    body?: object,
  ): Promise<ProfileState> {
    if (!isWorkspaceId(workspaceId) || !isWorkspaceId(subject))
      throw new ProfileApiError("NOT_FOUND", 404);
    if (!origin) throw new ProfileApiError("DATABASE_UNAVAILABLE", 503);
    if (signal.aborted) throw new ProfileApiError("CANCELLED", 0);
    let response: Response;
    try {
      const token = await getToken(subject);
      if (!token || signal.aborted)
        throw new ProfileApiError("AUTH_REQUIRED", 401);
      response = await fetcher(
        origin +
          "/api/v1/workspaces/" +
          encodeURIComponent(workspaceId) +
          "/profile" +
          path,
        {
          method,
          headers: {
            Authorization: "Bearer " + token,
            Accept: "application/json",
            ...(body ? { "Content-Type": "application/json" } : {}),
          },
          body: body ? JSON.stringify(body) : undefined,
          signal: AbortSignal.any([signal, AbortSignal.timeout(12000)]),
          cache: "no-store",
          credentials: "omit",
        },
      );
    } catch (error) {
      if (error instanceof ProfileApiError) throw error;
      if (signal.aborted) throw new ProfileApiError("CANCELLED", 0);
      // A lost response on write does not imply a failed transaction.
      throw new ProfileApiError(
        method === "GET" ? "NETWORK_FAILED" : "NETWORK_UNCERTAIN",
        0,
      );
    }
    if (!response.ok) {
      let payload: unknown;
      try {
        payload = await response.json();
      } catch {
        payload = null;
      }
      throw new ProfileApiError(
        errorCode(payload, response.status),
        response.status,
      );
    }
    let result: unknown;
    try {
      result = await response.json();
    } catch {
      throw new ProfileApiError(
        method === "GET" ? "INVALID_RESPONSE" : "NETWORK_UNCERTAIN",
        0,
      );
    }
    try {
      return parseProfileState(result);
    } catch {
      throw new ProfileApiError(
        method === "GET" ? "INVALID_RESPONSE" : "NETWORK_UNCERTAIN",
        0,
      );
    }
  }

  return {
    read: (workspaceId: string, signal: AbortSignal) =>
      request(workspaceId, "", "GET", signal),
    save: (
      workspaceId: string,
      answers: ProfileAnswers,
      expectedRevision: number,
      signal: AbortSignal,
    ) =>
      request(workspaceId, "/draft", "PUT", signal, {
        answers,
        expected_revision: expectedRevision,
      }),
    confirm: (
      workspaceId: string,
      expectedRevision: number,
      signal: AbortSignal,
    ) =>
      request(workspaceId, "/confirm", "POST", signal, {
        expected_revision: expectedRevision,
      }),
  };
}
