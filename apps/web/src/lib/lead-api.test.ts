import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { createLeadApi, LeadApiError } from "./lead-api.ts";
import { InvalidLeadResponse } from "./lead-contract.ts";

const subject = "11111111-1111-4111-8111-111111111111";
const workspace = "22222222-2222-4222-8222-222222222222";
const leadId = "33333333-3333-4333-8333-333333333333";
const token = "unit-test-not-a-real-jwt";
const signal = new AbortController().signal;
const lead = {
  id: leadId,
  workspace_id: workspace,
  title: "Manual opportunity",
  source_url: "https://example.org/notes",
  source_excerpt: "Manual citation",
  source_origin: "user_provided",
  stage: "spotted",
  note: "",
  follow_up_at: null,
  follow_up_done: false,
  unsent_draft: "",
  version: 1,
  created_at: "2026-11-23T11:00:00Z",
  updated_at: "2026-11-23T11:00:00Z",
};
const payload = {
  title: lead.title,
  source_url: lead.source_url,
  source_excerpt: lead.source_excerpt,
};

describe("authenticated CRM API client", () => {
  it("never places credentials in URLs, stores no fake source and sends one POST", async () => {
    const requests: Array<{ url: string; options: RequestInit | undefined }> =
      [];
    const fetcher = async (
      url: string | URL | Request,
      options?: RequestInit,
    ): Promise<Response> => {
      requests.push({ url: String(url), options });
      if (options?.method === "POST")
        return Response.json(
          { ...lead, already_exists: false },
          { status: 201 },
        );
      return Response.json({ items: [lead] });
    };
    const api = createLeadApi(
      "https://api.example.test",
      subject,
      async (expected) => {
        assert.equal(expected, subject);
        return token;
      },
      fetcher,
    );
    assert.equal((await api.list(workspace, signal)).length, 1);
    assert.equal(
      (await api.create(workspace, payload, "initialKey123", signal)).id,
      leadId,
    );
    assert.equal(requests.length, 2);
    assert(
      requests.every((item) =>
        item.url.includes("/workspaces/" + workspace + "/leads"),
      ),
    );
    assert(requests.every((item) => !item.url.includes(token)));
    assert(requests.every((item) => item.options?.credentials === "omit"));
    assert(requests.every((item) => item.options?.cache === "no-store"));
    assert(
      requests.every(
        (item) =>
          (item.options?.headers as Record<string, string>).Authorization ===
          "Bearer " + token,
      ),
    );
    assert.equal(
      (requests[1].options?.headers as Record<string, string>)[
        "Idempotency-Key"
      ],
      "initialKey123",
    );
    assert.deepEqual(JSON.parse(String(requests[1].options?.body)), payload);
  });

  it("sends optimistic revisions and never invents an outreach send operation", async () => {
    const requests: Array<{ url: string; options: RequestInit | undefined }> =
      [];
    const api = createLeadApi(
      "https://api.example.test",
      subject,
      async () => token,
      async (url, options) => {
        requests.push({ url: String(url), options });
        if (options?.method === "PATCH")
          return Response.json({ ...lead, version: 2, stage: "qualified" });
        return new Response(null, { status: 204 });
      },
    );
    assert.equal(
      (
        await api.update(
          workspace,
          leadId,
          { expected_version: 1, stage: "qualified" },
          signal,
        )
      ).version,
      2,
    );
    await api.archive(workspace, leadId, 2, signal);
    assert.equal(requests[0].options?.method, "PATCH");
    assert.equal(requests[1].options?.method, "DELETE");
    assert.equal(
      requests[1].url,
      "https://api.example.test/api/v1/workspaces/" +
        workspace +
        "/leads/" +
        leadId +
        "?expected_version=2",
    );
  });

  it("does not retry a possibly committed or malformed successful POST", async () => {
    let count = 0;
    const api = createLeadApi(
      "https://api.example.test",
      subject,
      async () => token,
      async () => {
        count++;
        return Response.json(
          { ...lead, workspace_id: subject },
          { status: 201 },
        );
      },
    );
    await assert.rejects(
      api.create(workspace, payload, "initialKey123", signal),
      (error: unknown) =>
        error instanceof LeadApiError && error.code === "NETWORK_UNCERTAIN",
    );
    assert.equal(count, 1);
    const offline = createLeadApi(
      "https://api.example.test",
      subject,
      async () => token,
      async () => {
        throw new Error("private-network details");
      },
    );
    await assert.rejects(
      offline.create(workspace, payload, "initialKey123", signal),
      (error: unknown) =>
        error instanceof LeadApiError &&
        error.code === "NETWORK_UNCERTAIN" &&
        !error.message.includes("details"),
    );
  });

  it("denies cross-workspace records, malformed IDs and missing auth", async () => {
    const mismatched = createLeadApi(
      "https://api.example.test",
      subject,
      async () => token,
      async () =>
        Response.json({ items: [{ ...lead, workspace_id: subject }] }),
    );
    await assert.rejects(
      mismatched.list(workspace, signal),
      InvalidLeadResponse,
    );
    await assert.rejects(
      mismatched.read("../other", leadId, signal),
      InvalidLeadResponse,
    );
    let fetchCount = 0;
    const withoutToken = createLeadApi(
      "https://api.example.test",
      subject,
      async () => {
        throw new LeadApiError("AUTH_REQUIRED", 401);
      },
      async () => {
        fetchCount++;
        return Response.json(lead);
      },
    );
    await assert.rejects(
      withoutToken.read(workspace, leadId, signal),
      (error: unknown) => error instanceof LeadApiError && error.status === 401,
    );
    assert.equal(fetchCount, 0);
  });

  it("preserves HTTP failures without leaking bodies or accepting forged codes", async () => {
    for (const [status, code] of [
      [401, "AUTH_REQUIRED"],
      [404, "NOT_FOUND"],
      [409, "LEAD_ALREADY_SAVED"],
      [503, "DATABASE_UNAVAILABLE"],
    ] as const) {
      const api = createLeadApi(
        "https://api.example.test",
        subject,
        async () => token,
        async () =>
          Response.json({ error: { code, debug: "private" } }, { status }),
      );
      await assert.rejects(
        api.read(workspace, leadId, signal),
        (error: unknown) =>
          error instanceof LeadApiError &&
          error.status === status &&
          error.code === code &&
          !error.message.includes("private"),
      );
    }
  });
});
