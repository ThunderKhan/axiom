import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  parseResearchRun,
  parseSignalAssessment,
} from "./research-contract.ts";

const workspace = "11111111-1111-4111-8111-111111111111";
const profile = "22222222-2222-4222-8222-222222222222";
const runId = "33333333-3333-4333-8333-333333333333";
const signal = "44444444-4444-4444-8444-444444444444";
const timestamp = "2026-11-24T12:00:00Z";
const request = {
  profile_version_id: profile,
  url: "https://example.org/feed.xml",
  query: "offline",
  limit: 10,
};
const item = {
  signal_id: signal,
  source_id: "a".repeat(32),
  source_url: "https://example.org/article",
  title: "Offline tools",
  excerpt: "Offline tools are available.",
  published_at: null,
  intent: "unknown",
};
const response = {
  run_id: runId,
  workspace_id: workspace,
  profile_revision: 1,
  status: "completed",
  result: {
    profile_version_id: profile,
    feed_url: request.url,
    query: request.query,
    publisher: "Fixture",
    policy_review_id: "fixture-review",
    retrieved_at: timestamp,
    source_family: "rss_atom",
    origin: "live",
    independent_fact_verification: false,
    query_method: "literal_all_terms",
    feed_content_digest: "b".repeat(64),
    items: [item],
  },
};

describe("durable research response integrity", () => {
  it("matches the requested profile, run, source and signal", () => {
    const parsed = parseResearchRun(response, workspace, request);
    assert.equal(parsed.items[0].signal_id, signal);
    assert.deepEqual(parseResearchRun(response, workspace, runId), parsed);
    assert.throws(() => parseResearchRun(response, profile, request));
    assert.throws(() => parseResearchRun(response, workspace, signal));
    assert.throws(() =>
      parseResearchRun(response, workspace, { ...request, query: "different" }),
    );
  });

  it("rejects invented demand, duplicate signals and unsafe citation URLs", () => {
    for (const items of [
      [{ ...item, intent: "buying" }],
      [item, { ...item, source_id: "c".repeat(32) }],
      [{ ...item, source_url: "javascript:alert(1)" }],
    ])
      assert.throws(() =>
        parseResearchRun(
          { ...response, result: { ...response.result, items } },
          workspace,
          request,
        ),
      );
  });

  it("validates evidence against the selected immutable run and signal", () => {
    const run = parseResearchRun(response, workspace, request);
    const report = {
      workspace_id: workspace,
      run_id: runId,
      signal_id: signal,
      profile_revision: 1,
      profile_version_id: profile,
      source_url: item.source_url,
      source_excerpt: item.excerpt,
      source_origin: "live",
      policy_review_id: "fixture-review",
      retrieved_at: timestamp,
      article_independently_verified: false,
      persisted_assessment: false,
      assessment: {
        verdict: "research_further",
        intent: "unknown",
        compatibility: "supported",
        report_lines: ["Founder-declared capability."],
        source_ids: [signal],
      },
    };
    assert.equal(
      parseSignalAssessment(report, workspace, run, run.items[0]).verdict,
      "research_further",
    );
    for (const invalid of [
      { ...report, profile_revision: 2 },
      { ...report, source_excerpt: "Fabricated" },
      { ...report, article_independently_verified: true },
      { ...report, assessment: { ...report.assessment, verdict: "pursue" } },
    ])
      assert.throws(() =>
        parseSignalAssessment(invalid, workspace, run, run.items[0]),
      );
  });
});
