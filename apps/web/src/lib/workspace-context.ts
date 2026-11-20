import { isWorkspaceId, type Workspace } from "./workspace-contract.ts";

export const WORKSPACE_PREFERENCE_PREFIX = "axiom:workspace:";

/** Subject is trusted only after Next.js verifies provider claims. */
export function workspacePreferenceKey(subject: string): string {
  if (!isWorkspaceId(subject)) throw new Error("Verified user ID required.");
  return WORKSPACE_PREFERENCE_PREFIX + subject;
}

type Preferences = Pick<Storage, "getItem" | "setItem" | "removeItem">;

/** The browser storage getter itself may throw under restrictive policies. */
export function availablePreferenceStorage(
  acquire: () => Preferences,
): Preferences | null {
  try {
    return acquire();
  } catch {
    return null;
  }
}

export function readWorkspacePreference(
  storage: Preferences | null,
  subject: string,
): string | null {
  try {
    if (!storage) return null;
    const key = workspacePreferenceKey(subject);
    const value = storage.getItem(key);
    if (value !== null && !isWorkspaceId(value)) {
      storage.removeItem(key);
      return null;
    }
    return value;
  } catch {
    return null; // Private storage can be blocked; never weaken API authorization.
  }
}

export function saveWorkspacePreference(
  storage: Preferences | null,
  subject: string,
  workspaceId: string | null,
): void {
  try {
    if (!storage) return;
    const key = workspacePreferenceKey(subject);
    if (workspaceId === null) storage.removeItem(key);
    else if (isWorkspaceId(workspaceId)) storage.setItem(key, workspaceId);
  } catch {
    // Session-only preference; loss of storage cannot grant access.
  }
}

export function chooseRequestedWorkspace(
  rawPathId: unknown,
  savedId: string | null,
): string | null {
  // A supplied URL never becomes authority. The candidate is fetched from FastAPI.
  if (rawPathId !== null && rawPathId !== undefined) {
    return isWorkspaceId(rawPathId) ? rawPathId : null;
  }
  return isWorkspaceId(savedId) ? savedId : null;
}

export function mergeOwnedWorkspaces(
  workspaces: readonly Workspace[],
  item: Workspace,
): Workspace[] {
  return [item, ...workspaces.filter((existing) => existing.id !== item.id)];
}

export type CreateAttempt = Readonly<{
  subject: string;
  name: string;
  key: string;
  startedAt: number;
}>;

export function makeCreateAttempt(
  subject: string,
  name: string,
  now: number,
  generateKey: () => string,
): CreateAttempt {
  if (!isWorkspaceId(subject)) throw new Error("Verified user ID required.");
  const key = generateKey();
  if (!/^[A-Za-z0-9][A-Za-z0-9_-]{7,127}$/.test(key)) {
    throw new Error("Invalid creation key.");
  }
  return { subject, name, key, startedAt: now };
}

/** No deployment-verified delivery bound: no automatic retry is permitted. */
export function allowAutomaticCreateRetry(
  attempt: CreateAttempt,
  subject: string,
  now: number,
  verifiedMaxDeliveryMs?: number,
): boolean {
  if (
    attempt.subject !== subject ||
    !Number.isFinite(now) ||
    now < attempt.startedAt ||
    verifiedMaxDeliveryMs === undefined ||
    !Number.isFinite(verifiedMaxDeliveryMs) ||
    verifiedMaxDeliveryMs <= 0
  )
    return false;
  // Conservative bound, with delivery and clock-safety margin. Deployment
  // verification must establish the maximum client/proxy/network delay first.
  const deadline = 24 * 60 * 60 * 1000 - 2 * verifiedMaxDeliveryMs;
  return deadline > 0 && now - attempt.startedAt < deadline;
}

/** Pending creates require owner-authorized list inspection after interruption. */
export type UncertainCreation = Readonly<{
  kind: "uncertain";
  name: string;
  inspected: boolean;
}>;

export function uncertainCreationState(
  attempt: CreateAttempt | null,
  subject: string,
  inspected: boolean,
): UncertainCreation | null {
  return attempt?.subject === subject
    ? { kind: "uncertain", name: attempt.name, inspected }
    : null;
}

export class RequestGeneration {
  private value = 0;

  next(): number {
    this.value += 1;
    return this.value;
  }

  current(expected: number): boolean {
    return this.value === expected;
  }
}
