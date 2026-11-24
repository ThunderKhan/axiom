/** Parse source previews before any publisher content enters the UI. */
export const claimKinds = ["features", "pricing", "positioning"] as const;
export type ClaimKind = (typeof claimKinds)[number];
export type ClaimCandidate = Readonly<{ kind: ClaimKind; locator: string }>;

export type SourcePreview = Readonly<{
  source_url: string;
  source_id: string;
  title: string;
  excerpt: string;
  retrieved_at: string;
  content_digest: string;
  publisher: string;
  policy_review_id: string;
}>;

export type CompetitorPreview = Readonly<{
  source: SourcePreview;
  competitor_name: string;
  claims: readonly ClaimCandidate[];
  unknowns: readonly ClaimKind[];
}>;

export class InvalidSourcePreview extends Error {
  constructor() {
    super("The source preview did not match the requested workspace and URL.");
    this.name = "InvalidSourcePreview";
  }
}

function record(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function bounded(value: unknown, max: number): value is string {
  return typeof value === "string" && value.length <= max;
}

function kind(value: unknown): value is ClaimKind {
  return claimKinds.some((item) => item === value);
}

export function parseSourcePreview(
  raw: unknown,
  workspaceId: string,
  url: string,
): SourcePreview {
  if (
    !record(raw) ||
    raw.workspace_id !== workspaceId ||
    raw.source_url !== url ||
    raw.source_family !== "manual_url" ||
    raw.origin !== "live" ||
    raw.persisted !== false ||
    raw.independent_fact_verification !== false ||
    raw.published_at !== null ||
    !bounded(raw.source_id, 32) ||
    !/^[a-f0-9]{32}$/.test(raw.source_id) ||
    !bounded(raw.content_digest, 64) ||
    !/^[a-f0-9]{64}$/.test(raw.content_digest) ||
    !bounded(raw.title, 300) ||
    !bounded(raw.excerpt, 1500) ||
    !raw.excerpt.trim() ||
    !bounded(raw.retrieved_at, 64) ||
    !Number.isFinite(Date.parse(raw.retrieved_at)) ||
    !bounded(raw.publisher, 120) ||
    !raw.publisher.trim() ||
    !bounded(raw.policy_review_id, 120) ||
    !raw.policy_review_id.trim()
  )
    throw new InvalidSourcePreview();
  return {
    source_url: url,
    source_id: raw.source_id,
    title: raw.title,
    excerpt: raw.excerpt,
    retrieved_at: raw.retrieved_at,
    content_digest: raw.content_digest,
    publisher: raw.publisher,
    policy_review_id: raw.policy_review_id,
  };
}

export function parseCompetitorPreview(
  raw: unknown,
  workspaceId: string,
  url: string,
  name: string,
  candidates: readonly ClaimCandidate[],
): CompetitorPreview {
  if (
    !record(raw) ||
    raw.competitor_name !== name ||
    !Array.isArray(raw.claims) ||
    raw.claims.length > 8 ||
    !Array.isArray(raw.unknowns) ||
    raw.unknowns.length > 3
  )
    throw new InvalidSourcePreview();
  const source = parseSourcePreview(raw.source, workspaceId, url);
  const claims: ClaimCandidate[] = [];
  for (const value of raw.claims as unknown[]) {
    if (
      !record(value) ||
      !kind(value.kind) ||
      !bounded(value.locator, 200) ||
      !value.locator.trim() ||
      value.text !== value.locator ||
      value.source_id !== source.source_id ||
      value.status !== "publisher_claim_observed" ||
      !source.excerpt.includes(value.locator) ||
      !candidates.some(
        (item) => item.kind === value.kind && item.locator === value.locator,
      )
    )
      throw new InvalidSourcePreview();
    if (
      claims.some(
        (item) => item.kind === value.kind && item.locator === value.locator,
      )
    )
      throw new InvalidSourcePreview();
    claims.push({ kind: value.kind, locator: value.locator });
  }
  const unknowns = claimKinds.filter(
    (item) => !claims.some((claim) => claim.kind === item),
  );
  if (
    raw.unknowns.length !== unknowns.length ||
    !unknowns.every((item, index) => raw.unknowns[index] === item)
  )
    throw new InvalidSourcePreview();
  return { source, competitor_name: name, claims, unknowns };
}
