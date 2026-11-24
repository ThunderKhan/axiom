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
  return typeof value === "string" && Array.from(value).length <= max;
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
    !bounded(raw.title, 180) ||
    !bounded(raw.excerpt, 500) ||
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
  const returnedUnknowns: unknown[] = raw.unknowns;
  if (
    returnedUnknowns.length !== unknowns.length ||
    !unknowns.every((item, index) => returnedUnknowns[index] === item)
  )
    throw new InvalidSourcePreview();
  return { source, competitor_name: name, claims, unknowns };
}

export type FeedItem = Readonly<{
  source_id: string;
  source_url: string;
  title: string;
  excerpt: string;
  published_at: string | null;
}>;

export type FeedPreview = Readonly<{
  feed_url: string;
  publisher: string;
  policy_review_id: string;
  retrieved_at: string;
  items: readonly FeedItem[];
}>;

function isSafeArticleUrl(value: unknown): value is string {
  if (!bounded(value, 2048) || !/^[!-~]+$/.test(value) || value.includes("\\"))
    return false;
  try {
    const url = new URL(value);
    return (
      url.protocol === "https:" &&
      !url.username &&
      !url.password &&
      !url.search &&
      !url.hash &&
      (!url.port || url.port === "443") &&
      /^[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,63}$/.test(url.hostname) &&
      !/\.(local|localhost|internal|test|invalid)$/.test(url.hostname)
    );
  } catch {
    return false;
  }
}

export function parseFeedPreview(
  raw: unknown,
  workspaceId: string,
  url: string,
  limit: number,
): FeedPreview {
  if (
    !record(raw) ||
    raw.workspace_id !== workspaceId ||
    raw.feed_url !== url ||
    raw.source_family !== "rss_atom" ||
    raw.origin !== "live" ||
    raw.persisted !== false ||
    raw.independent_fact_verification !== false ||
    raw.query_method !== "literal_all_terms" ||
    !bounded(raw.feed_content_digest, 64) ||
    !/^[a-f0-9]{64}$/.test(raw.feed_content_digest) ||
    !bounded(raw.retrieved_at, 64) ||
    !Number.isFinite(Date.parse(raw.retrieved_at)) ||
    !bounded(raw.publisher, 120) ||
    !raw.publisher.trim() ||
    !bounded(raw.policy_review_id, 120) ||
    !raw.policy_review_id.trim() ||
    !Array.isArray(raw.items) ||
    raw.items.length > limit
  )
    throw new InvalidSourcePreview();
  const seen = new Set<string>();
  const ids = new Set<string>();
  const items = raw.items.map((item: unknown) => {
    if (
      !record(item) ||
      !bounded(item.source_id, 32) ||
      !/^[a-f0-9]{32}$/.test(item.source_id) ||
      !isSafeArticleUrl(item.source_url) ||
      seen.has(item.source_url) ||
      ids.has(item.source_id) ||
      !bounded(item.title, 180) ||
      !item.title.trim() ||
      !bounded(item.excerpt, 500) ||
      !item.excerpt.trim() ||
      (item.published_at !== null &&
        (!bounded(item.published_at, 64) ||
          !Number.isFinite(Date.parse(item.published_at))))
    )
      throw new InvalidSourcePreview();
    seen.add(item.source_url);
    ids.add(item.source_id);
    return {
      source_id: item.source_id,
      source_url: item.source_url,
      title: item.title,
      excerpt: item.excerpt,
      published_at: item.published_at,
    };
  });
  return {
    feed_url: url,
    publisher: raw.publisher,
    policy_review_id: raw.policy_review_id,
    retrieved_at: raw.retrieved_at,
    items,
  };
}
