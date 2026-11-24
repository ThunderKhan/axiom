import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { createLeadApi, LeadApiError } from "./lead-api.ts";
import { InvalidLeadResponse } from "./lead-contract.ts";
import { InvalidSourcePreview } from "./source-preview-contract.ts";

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
          Response.json(
            { error: { code, debug: "secret-contract-value-8374" } },
            { status },
          ),
      );
      await assert.rejects(
        api.read(workspace, leadId, signal),
        (error: unknown) =>
          error instanceof LeadApiError &&
          error.status === status &&
          error.code === code &&
          !error.message.includes("secret-contract-value-8374"),
      );
    }
  });
});

describe("reviewed source preview", () => {
  const source = {
    workspace_id: workspace,
    source_url: lead.source_url,
    source_id: "a".repeat(32),
    source_family: "manual_url",
    title: "Product",
    excerpt: "Offline export is offered.",
    origin: "live",
    retrieved_at: "2026-11-24T06:00:00Z",
    content_digest: "b".repeat(64),
    publisher: "Fixture publisher",
    policy_review_id: "fixture-only",
    published_at: null,
    persisted: false,
    independent_fact_verification: false,
  };

  it("uses the authenticated source route and rejects forged provenance", async () => {
    let response: unknown = source;
    const api = createLeadApi(
      "https://api.example.test",
      subject,
      async () => token,
      async (url, options) => {
        assert.equal(
          String(url),
          "https://api.example.test/api/v1/workspaces/" +
            workspace +
            "/research/public-url/preview",
        );
        assert.equal(options?.method, "POST");
        assert.deepEqual(JSON.parse(String(options?.body)), {
          url: lead.source_url,
        });
        assert.equal(options?.cache, "no-store");
        return Response.json(response);
      },
    );
    assert.equal(
      (await api.previewSource(workspace, lead.source_url, signal)).excerpt,
      source.excerpt,
    );
    response = { ...source, excerpt: "😀" + "x".repeat(499) };
    const unicode = await api.previewSource(workspace, lead.source_url, signal);
    assert.equal(Array.from(unicode.excerpt).length, 500);
    for (const changes of [
      { workspace_id: subject },
      { origin: "seeded" },
      { persisted: true },
      { source_url: "https://example.org/other" },
    ]) {
      response = { ...source, ...changes };
      await assert.rejects(
        api.previewSource(workspace, lead.source_url, signal),
        InvalidSourcePreview,
      );
    }
  });

  it("accepts only requested, observed claims and explicit unknowns", async () => {
    const candidates = [{ kind: "features", locator: "Offline" }] as const;
    const claim = {
      ...candidates[0],
      text: "Offline",
      source_id: source.source_id,
      status: "publisher_claim_observed",
    };
    let response: unknown = {
      competitor_name: "Product",
      source,
      claims: [claim],
      unknowns: ["pricing", "positioning"],
    };
    const api = createLeadApi(
      "https://api.example.test",
      subject,
      async () => token,
      async (_url, options) => {
        assert.equal(JSON.parse(String(options?.body)).confirmed, true);
        return Response.json(response);
      },
    );
    const preview = () =>
      api.previewCompetitor(
        workspace,
        lead.source_url,
        "Product",
        candidates,
        signal,
      );
    assert.deepEqual((await preview()).unknowns, ["pricing", "positioning"]);
    response = {
      competitor_name: "Product",
      source,
      claims: [{ ...claim, text: "Free forever" }],
      unknowns: ["pricing", "positioning"],
    };
    await assert.rejects(preview, InvalidSourcePreview);
  });
});

describe("reviewed feed browser contract", () => {
  it("uses an authenticated bounded feed request and rejects unsafe entries", async () => {
    const url = "https://example.org/feed.xml";
    const item = {
      source_id: "a".repeat(32),
      source_url: "https://example.org/post",
      title: "Offline sync",
      excerpt: "Offline sync is useful.",
      published_at: null,
    };
    const response = {
      workspace_id: workspace,
      feed_url: url,
      source_family: "rss_atom",
      origin: "live",
      persisted: false,
      independent_fact_verification: false,
      query_method: "literal_all_terms",
      feed_content_digest: "b".repeat(64),
      publisher: "Fixture publisher",
      policy_review_id: "fixture",
      retrieved_at: lead.created_at,
      items: [item],
    };
    let body: unknown = response;
    const api = createLeadApi(
      "https://api.example.test",
      subject,
      async () => token,
      async (requested, options) => {
        assert.equal(
          String(requested),
          "https://api.example.test/api/v1/workspaces/" +
            workspace +
            "/research/feed/preview",
        );
        assert.equal(options?.method, "POST");
        assert.equal(options?.credentials, "omit");
        assert.deepEqual(JSON.parse(String(options?.body)), {
          url,
          query: "offline",
          limit: 10,
        });
        return Response.json(body);
      },
    );
    const preview = await api.previewFeed(workspace, url, "offline", signal);
    assert.equal(preview.items.length, 1);
    for (const bad of [
      { ...response, workspace_id: leadId },
      { ...response, origin: "seeded" },
      { ...response, persisted: true },
      { ...response, items: [item, item] },
      {
        ...response,
        items: [
          item,
          {
            ...item,
            source_id: "c".repeat(32),
            source_url: "https://example.org:443/post",
          },
        ],
      },
      {
        ...response,
        items: [{ ...item, source_url: "https:example.org/post" }],
      },
      {
        ...response,
        items: [{ ...item, source_url: "https://127.0.0.1/private" }],
      },
      {
        ...response,
        items: [{ ...item, source_url: "javascript:alert(1)" }],
      },
    ]) {
      body = bad;
      await assert.rejects(
        api.previewFeed(workspace, url, "offline", signal),
        InvalidSourcePreview,
      );
    }
  });
});
