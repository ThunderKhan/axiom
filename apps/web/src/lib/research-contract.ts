import { isWorkspaceId } from "./workspace-contract.ts";
import {
  InvalidSourcePreview,
  parseFeedPreview,
  type FeedItem,
} from "./source-preview-contract.ts";

export type ResearchRequest = Readonly<{
  profile_version_id: string;
  url: string;
  query: string;
  limit: number;
}>;

export type ResearchRun = Readonly<{
  run_id: string;
  profile_version_id: string;
  profile_revision: number;
  feed_url: string;
  query: string;
  publisher: string;
  policy_review_id: string;
  retrieved_at: string;
  items: readonly (FeedItem & { signal_id: string })[];
}>;

function record(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

export function parseResearchRun(
  raw: unknown,
  workspaceId: string,
  expected: ResearchRequest | string,
): ResearchRun {
  if (
    !record(raw) ||
    raw.workspace_id !== workspaceId ||
    !isWorkspaceId(raw.run_id) ||
    raw.status !== "completed" ||
    !Number.isSafeInteger(raw.profile_revision) ||
    (raw.profile_revision as number) < 1 ||
    !record(raw.result)
  )
    throw new InvalidSourcePreview();
  const result = raw.result;
  if (
    !isWorkspaceId(result.profile_version_id) ||
    typeof result.feed_url !== "string" ||
    typeof result.query !== "string" ||
    [...result.query].length > 120 ||
    (typeof expected === "string"
      ? raw.run_id !== expected
      : result.profile_version_id !== expected.profile_version_id ||
        result.feed_url !== expected.url ||
        result.query !== expected.query) ||
    !Array.isArray(result.items)
  )
    throw new InvalidSourcePreview();

  const preview = parseFeedPreview(
    { ...result, workspace_id: workspaceId, persisted: false },
    workspaceId,
    result.feed_url,
    typeof expected === "string" ? 20 : expected.limit,
  );
  const rawItems: unknown[] = result.items;
  const ids = new Set<string>();
  const items = preview.items.map((item, index) => {
    const original = rawItems[index];
    if (
      !record(original) ||
      !isWorkspaceId(original.signal_id) ||
      original.intent !== "unknown" ||
      ids.has(original.signal_id)
    )
      throw new InvalidSourcePreview();
    ids.add(original.signal_id);
    return { ...item, signal_id: original.signal_id };
  });
  return {
    run_id: raw.run_id,
    profile_version_id: result.profile_version_id,
    profile_revision: raw.profile_revision as number,
    feed_url: preview.feed_url,
    query: result.query,
    publisher: preview.publisher,
    policy_review_id: preview.policy_review_id,
    retrieved_at: preview.retrieved_at,
    items,
  };
}
