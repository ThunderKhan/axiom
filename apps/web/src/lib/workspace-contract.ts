/** Only these M1.5 DTO fields may enter the authenticated workspace UI. */
export type Workspace = Readonly<{
  id: string;
  name: string;
  created_at: string;
  updated_at: string;
  version: number;
}>;

export type WorkspaceList = Readonly<{
  items: readonly Workspace[];
  next_cursor: string | null;
}>;

export class InvalidWorkspaceResponse extends Error {
  constructor() {
    super("Invalid workspace API response.");
    this.name = "InvalidWorkspaceResponse";
  }
}

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

export function isWorkspaceId(value: unknown): value is string {
  return (
    typeof value === "string" &&
    /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
      value,
    )
  );
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

export function parseWorkspace(value: unknown): Workspace {
  if (
    !record(value) ||
    !isWorkspaceId(value.id) ||
    typeof value.name !== "string" ||
    value.name.length < 1 ||
    value.name.length > 120 ||
    !timestamp(value.created_at) ||
    !timestamp(value.updated_at) ||
    !Number.isSafeInteger(value.version) ||
    (value.version as number) < 1
  ) {
    throw new InvalidWorkspaceResponse();
  }
  return {
    id: value.id,
    name: value.name,
    created_at: value.created_at,
    updated_at: value.updated_at,
    version: value.version as number,
  };
}

export function parseWorkspaceList(value: unknown): WorkspaceList {
  if (
    !record(value) ||
    !Array.isArray(value.items) ||
    value.items.length > 100 ||
    !(
      value.next_cursor === null ||
      (typeof value.next_cursor === "string" &&
        value.next_cursor.length > 0 &&
        value.next_cursor.length <= 512)
    )
  ) {
    throw new InvalidWorkspaceResponse();
  }
  const items = value.items.map(parseWorkspace);
  if (new Set(items.map((item) => item.id)).size !== items.length) {
    throw new InvalidWorkspaceResponse();
  }
  return { items, next_cursor: value.next_cursor };
}

export function parseBootstrap(value: unknown, subject: string): void {
  if (
    !record(value) ||
    !record(value.user) ||
    value.user.id !== subject ||
    value.user.status !== "active" ||
    !timestamp(value.user.created_at) ||
    typeof value.created !== "boolean"
  ) {
    throw new InvalidWorkspaceResponse();
  }
}

/** Client feedback only; FastAPI is the authoritative name validator. */
export function canonicalWorkspaceName(value: string): string {
  const name = value.trim();
  if (
    name.length === 0 ||
    [...name].length > 120 ||
    /[\u0000-\u001f\u007f-\u009f\uD800-\uDFFF]/u.test(name)
  ) {
    throw new Error(
      "Use a name of 1–120 characters without control characters.",
    );
  }
  return name;
}
