import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  InvalidLeadResponse,
  isLeadStage,
  normalizeLeadText,
  parseCreatedLead,
  parseLead,
  parseLeadEvents,
  parseLeadList,
  resolveFollowUpInstant,
} from "./lead-contract.ts";

const workspace = "11111111-1111-4111-8111-111111111111";
const leadId = "22222222-2222-4222-8222-222222222222";
const other = "33333333-3333-4333-8333-333333333333";
const saved = {
  id: leadId,
  workspace_id: workspace,
  title: "Need offline support",
  source_url: "https://example.org/customer/123",
  source_excerpt: "A customer requested offline support.",
  source_origin: "user_provided",
  stage: "spotted",
  note: "",
  follow_up_at: null,
  follow_up_done: false,
  unsent_draft: "",
  version: 1,
  created_at: "2026-11-23T11:20:00Z",
  updated_at: "2026-11-23T11:20:00Z",
};

describe("CRM response and provenance integrity", () => {
  it("accepts valid owner-scoped manual lead and event metadata", () => {
    assert.deepEqual(parseLead(saved, workspace), saved);
    assert.deepEqual(parseLeadList({ items: [saved] }, workspace), [saved]);
    assert.deepEqual(
      parseCreatedLead({ ...saved, already_exists: false }, workspace),
      { ...saved, already_exists: false },
    );
    assert.equal(isLeadStage("contacted"), true);
    assert.equal(isLeadStage("sent"), false);
    assert.deepEqual(
      parseLeadEvents({
        items: [
          {
            id: other,
            actor_id: workspace,
            event_type: "updated",
            changed_fields: ["stage", "note"],
            created_at: saved.updated_at,
          },
        ],
      }).map((event) => event.changed_fields),
      [["stage", "note"]],
    );
  });

  it("denies workspace mismatch, fake verification and unsafe origin claims", () => {
    for (const data of [
      { ...saved, workspace_id: other },
      { ...saved, id: "../system" },
      { ...saved, source_origin: "live_verified" },
      { ...saved, source_url: "javascript:alert(1)" },
      { ...saved, stage: "sent" },
      { ...saved, version: 0 },
      { ...saved, follow_up_done: true },
      { ...saved, updated_at: "yesterday" },
      { ...saved, title: "a".repeat(181) },
      { ...saved, unsent_draft: "a".repeat(4001) },
    ])
      assert.throws(() => parseLead(data, workspace), InvalidLeadResponse);
    assert.throws(
      () => parseLeadList({ items: [saved, saved] }, workspace),
      InvalidLeadResponse,
    );
    assert.throws(
      () => parseCreatedLead({ ...saved, already_exists: "yes" }, workspace),
      InvalidLeadResponse,
    );
  });

  it("denies forged event history and invalid response collections", () => {
    for (const data of [
      {
        items: [
          {
            id: other,
            actor_id: workspace,
            event_type: "sent",
            changed_fields: [],
            created_at: saved.created_at,
          },
        ],
      },
      {
        items: [
          {
            id: other,
            actor_id: workspace,
            event_type: "created",
            changed_fields: "all",
            created_at: saved.created_at,
          },
        ],
      },
      { items: null },
      { items: new Array(101).fill(saved) },
    ])
      assert.throws(() => parseLeadEvents(data), InvalidLeadResponse);
  });

  it("uses Python-compatible Unicode codepoint limits for all private text", () => {
    const emoji = "🛰️";
    const singleCodepoint = "🛰";
    const valid = {
      ...saved,
      title: singleCodepoint.repeat(180),
      source_excerpt: singleCodepoint.repeat(500),
      note: singleCodepoint.repeat(2000),
      unsent_draft: singleCodepoint.repeat(4000),
    };
    assert.deepEqual(parseLead(valid, workspace), valid);
    assert.equal(normalizeLeadText(singleCodepoint.repeat(500), 500),
      singleCodepoint.repeat(500));
    assert.throws(
      () => parseLead({ ...saved, title: singleCodepoint.repeat(181) }, workspace),
      InvalidLeadResponse,
    );
    assert.throws(
      () => normalizeLeadText(emoji.repeat(501), 500),
    );
  });

  it("preserves seconds and DST offset for a follow-up whose local field did not change", () => {
    const secondHour = "2026-11-01T06:30:45Z";
    assert.equal(
      resolveFollowUpInstant(secondHour, "2026-11-01T01:30", "2026-11-01T01:30"),
      secondHour,
    );
    assert.equal(resolveFollowUpInstant(secondHour, "2026-11-01T01:30", ""), null);
    assert.equal(
      resolveFollowUpInstant(null, "", "2026-11-02T11:45"),
      new Date("2026-11-02T11:45").toISOString(),
    );
    assert.throws(() => resolveFollowUpInstant(null, "", "not-a-date"));
  });

  it("keeps client changes within server limits", () => {
    assert.equal(normalizeLeadText("Research note", 2000), "Research note");
    assert.throws(() => normalizeLeadText("x".repeat(2001), 2000));
    assert.throws(() => normalizeLeadText("x\u0000", 2000));
  });
});
