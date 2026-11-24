import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { createLeadApi } from "./lead-api.ts";
import type { Lead } from "./lead-contract.ts";
import {
  InvalidEvidenceResponse,
  parseManualAssessment,
} from "./evidence-contract.ts";

const workspace = "22222222-2222-4222-8222-222222222222";
const leadId = "33333333-3333-4333-8333-333333333333";
const lead: Lead = {
  id: leadId,
  workspace_id: workspace,
  title: "Manual example",
  source_url: "https://example.org/post",
  source_excerpt: "I need offline sync for my notes",
  source_origin: "user_provided",
  stage: "spotted",
  note: "",
  follow_up_at: null,
  follow_up_done: false,
  unsent_draft: "",
  version: 2,
  created_at: "2026-11-24T06:00:00Z",
  updated_at: "2026-11-24T06:00:00Z",
};

const report = {
  workspace_id: workspace,
  lead_id: leadId,
  lead_version: lead.version,
  confirmed_profile_revision: 1,
  source_url: lead.source_url,
  source_origin: "user_provided",
  source_recorded_at: lead.created_at,
  live_source_verified: false,
  persisted_assessment: false,
  verdict: "research_further",
  intent: "buying",
  compatibility: "supported",
  reason_codes: ["SOLUTION_INTENT_AND_DECLARED_COVERAGE", "USER_PROVIDED_SOURCE_UNVERIFIED"],
  supported_need_ids: ["need-1"],
  hypothetical_need_ids: [],
  missing_need_ids: [],
  unknown_need_ids: [],
  relationships: [
    {
      source_id: leadId,
      need_id: "need-1",
      capability: "offline sync",
      relation: "covers",
      explanation: "Declared capability, not independently verified",
    },
  ],
  report_lines: ["Founder provided citation, not retrieved."],
};

describe("manual source report boundary", () => {
  it("parses owner-matched, explicitly unverified relationship and report", () => {
    const safe = parseManualAssessment(report, workspace, lead);
    assert.equal(safe.verdict, "research_further");
    assert.equal(safe.relationships[0].source_id, leadId);
    assert.deepEqual(safe.report_lines, report.report_lines);
  });

  it("rejects forged live evidence, foreign IDs, fake pursue and stale records", () => {
    for (const mutated of [
      { ...report, workspace_id: "11111111-1111-4111-8111-111111111111" },
      { ...report, lead_id: "11111111-1111-4111-8111-111111111111" },
      { ...report, source_origin: "live" },
      { ...report, live_source_verified: true },
      { ...report, persisted_assessment: true },
      { ...report, verdict: "pursue" },
      { ...report, lead_version: 1 },
      { ...report, source_recorded_at: "2026-11-24T07:00:00Z" },
      { ...report, source_url: "https://other.example.org" },
      { ...report, reason_codes: ["SOLUTION_INTENT_AND_DECLARED_COVERAGE"] },
      { ...report, relationships: [{ ...report.relationships[0], source_id: workspace }] },
      { ...report, supported_need_ids: ["need-999"] },
    ]) {
      assert.throws(
        () => parseManualAssessment(mutated, workspace, lead),
        InvalidEvidenceResponse,
      );
    }
  });

  it("uses existing verified bearer client with no cookies or URL token", async () => {
    const subject = "11111111-1111-4111-8111-111111111111";
    const token = "ephemeral-unit-token";
    let calls = 0;
    const api = createLeadApi(
      "https://api.example.test",
      subject,
      async (expected) => {
        assert.equal(expected, subject);
        return token;
      },
      async (url, options) => {
        calls++;
        assert.equal(
          String(url),
          "https://api.example.test/api/v1/workspaces/" +
            workspace + "/leads/" + leadId + "/assessment",
        );
        assert.equal(options?.method, "POST");
        assert.equal(options?.credentials, "omit");
        assert.equal(options?.cache, "no-store");
        assert.equal(
          (options?.headers as Record<string, string>).Authorization,
          "Bearer " + token,
        );
        assert(!String(url).includes(token));
        assert.deepEqual(JSON.parse(String(options?.body)), {
          needs: [
            {
              requirement: "offline sync",
              locator: "offline sync",
              intent: "buying",
            },
          ],
        });
        return Response.json(report);
      },
    );
    const outcome = await api.assess(
      workspace,
      lead,
      [{ requirement: "offline sync", locator: "offline sync", intent: "buying" }],
      new AbortController().signal,
    );
    assert.equal(outcome.verdict, "research_further");
    assert.equal(calls, 1);
  });
});
