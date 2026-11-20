import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  createWorkspaceApi,
  isUncertainCreateFailure,
  WorkspaceApiError,
} from "./workspace-api.ts";
import { InvalidWorkspaceResponse } from "./workspace-contract.ts";

const a = "11111111-1111-4111-8111-111111111111";
const id = "22222222-2222-4222-8222-222222222222";
const token = "synthetic-not-real-token";
const workspace = {
  id,
  name: "First",
  created_at: "2026-11-19T10:00:00Z",
  updated_at: "2026-11-19T10:00:00Z",
  version: 1,
};
const controller = new AbortController();

describe("FastAPI-only authenticated workspace client", () => {
  it("bootstraps, pages and validates actual request headers without credentials in URL", async () => {
    const requests: Array<{ url: string; init?: RequestInit }> = [];
    const fetcher = async (
      url: string | URL | Request,
      init?: RequestInit,
    ): Promise<Response> => {
      requests.push({ url: String(url), init });
      if (String(url).endsWith("/me/bootstrap")) {
        return Response.json(
          {
            user: { id: a, status: "active", created_at: workspace.created_at },
            created: true,
          },
          { status: 201 },
        );
      }
      if (String(url).includes("cursor=")) {
        return Response.json({ items: [], next_cursor: null });
      }
      return Response.json({
        items: [workspace],
        next_cursor: "opaque-cursor",
      });
    };
    const api = createWorkspaceApi(
      "https://api.example.test",
      a,
      async (expected) => {
        assert.equal(expected, a);
        return token;
      },
      fetcher,
    );
    await api.bootstrap(controller.signal);
    assert.equal((await api.list(controller.signal)).length, 1);
    assert.equal(requests.length, 3);
    assert(requests.every((req) => !req.url.includes(token)));
    assert(
      requests.every(
        (req) =>
          req.init?.headers &&
          (req.init.headers as Record<string, string>).Authorization ===
            "Bearer " + token,
      ),
    );
    assert(requests.every((req) => req.init?.credentials === "omit"));
    assert(requests.every((req) => req.init?.cache === "no-store"));
  });

  it("uses one original idempotency key for the request, and never invents a retry", async () => {
    const requests: RequestInit[] = [];
    const fetcher = async (
      _url: string | URL | Request,
      init?: RequestInit,
    ): Promise<Response> => {
      requests.push(init ?? {});
      return Response.json(workspace, { status: 201 });
    };
    const api = createWorkspaceApi(
      "https://api.example.test",
      a,
      async () => token,
      fetcher,
    );
    assert.deepEqual(
      await api.create("First", "originalKey189", controller.signal),
      workspace,
    );
    assert.equal(requests.length, 1);
    assert.equal(
      (requests[0].headers as Record<string, string>)["Idempotency-Key"],
      "originalKey189",
    );
    assert.equal(requests[0].body, JSON.stringify({ name: "First" }));
    assert.equal(
      "owner_user_id" in JSON.parse(String(requests[0].body)),
      false,
    );
  });

  it("classifies network loss after a POST as uncertain and does not resubmit", async () => {
    let count = 0;
    const api = createWorkspaceApi(
      "https://api.example.test",
      a,
      async () => token,
      async (): Promise<Response> => {
        count++;
        throw new Error("sensitive credentials must not escape");
      },
    );
    await assert.rejects(
      api.create("First", "originalKey189", controller.signal),
      (error: unknown) =>
        error instanceof WorkspaceApiError &&
        error.code === "NETWORK_UNCERTAIN" &&
        isUncertainCreateFailure(error) &&
        !error.message.includes("credentials"),
    );
    assert.equal(count, 1);
  });

  it("denies malformed responses and maps 401/403/404/409/422/503 safely", async () => {
    for (const [status, code] of [
      [401, "AUTH_REQUIRED"],
      [403, "ACCOUNT_DISABLED"],
      [404, "NOT_FOUND"],
      [409, "PROVISIONING_REQUIRED"],
      [422, "VALIDATION_FAILED"],
      [503, "DATABASE_UNAVAILABLE"],
    ] as const) {
      const api = createWorkspaceApi(
        "https://api.example.test",
        a,
        async () => token,
        async () => Response.json({ error: { code } }, { status }),
      );
      await assert.rejects(
        api.read(id, controller.signal),
        (error: unknown) =>
          error instanceof WorkspaceApiError &&
          error.status === status &&
          error.code === code,
      );
    }
    const api = createWorkspaceApi(
      "https://api.example.test",
      a,
      async () => token,
      async () => Response.json({ id: "injected", name: "Fake" }),
    );
    await assert.rejects(
      api.read(id, controller.signal),
      InvalidWorkspaceResponse,
    );
  });

  it("treats committed-but-malformed POST replies and server failures as uncertain", async () => {
    const invalidResponse = createWorkspaceApi(
      "https://api.example.test",
      a,
      async () => token,
      async () => Response.json({ id: "invalid" }, { status: 201 }),
    );
    await assert.rejects(
      invalidResponse.create("First", "originalKey189", controller.signal),
      (error: unknown) =>
        error instanceof WorkspaceApiError &&
        error.code === "NETWORK_UNCERTAIN" &&
        isUncertainCreateFailure(error),
    );
    const emptyResponse = createWorkspaceApi(
      "https://api.example.test",
      a,
      async () => token,
      async () => new Response("", { status: 201 }),
    );
    await assert.rejects(
      emptyResponse.create("First", "originalKey189", controller.signal),
      (error: unknown) =>
        error instanceof WorkspaceApiError && isUncertainCreateFailure(error),
    );
    const brokenServer = createWorkspaceApi(
      "https://api.example.test",
      a,
      async () => token,
      async () =>
        Response.json(
          { error: { code: "UNEXPECTED_RESPONSE" } },
          { status: 500 },
        ),
    );
    await assert.rejects(
      brokenServer.create("First", "originalKey189", controller.signal),
      (error: unknown) =>
        error instanceof WorkspaceApiError &&
        error.status === 500 &&
        isUncertainCreateFailure(error),
    );
    const mismatchedRead = createWorkspaceApi(
      "https://api.example.test",
      a,
      async () => token,
      async () => Response.json({ ...workspace, id: a }),
    );
    await assert.rejects(
      mismatchedRead.read(id, controller.signal),
      InvalidWorkspaceResponse,
    );
  });

  it("keeps 401 authorization failures when error bodies are empty", async () => {
    const api = createWorkspaceApi(
      "https://api.example.test",
      a,
      async () => token,
      async () => new Response("", { status: 401 }),
    );
    await assert.rejects(
      api.create("First", "originalKey189", controller.signal),
      (error: unknown) =>
        error instanceof WorkspaceApiError &&
        error.status === 401 &&
        error.code === "AUTH_REQUIRED" &&
        !isUncertainCreateFailure(error),
    );
    await assert.rejects(
      api.bootstrap(controller.signal),
      (error: unknown) =>
        error instanceof WorkspaceApiError &&
        error.status === 401 &&
        error.code === "AUTH_REQUIRED",
    );
  });

  it("accepts uppercase deep-link UUIDs but rejects a different workspace", async () => {
    const api = createWorkspaceApi(
      "https://api.example.test",
      a,
      async () => token,
      async () => Response.json(workspace),
    );
    assert.equal((await api.read(id.toUpperCase(), controller.signal)).id, id);
    await assert.rejects(api.read(a, controller.signal), InvalidWorkspaceResponse);
  });

  it("refuses to send when the session or public API origin is not usable", async () => {
    const noApi = createWorkspaceApi("", a, async () => token);
    await assert.rejects(noApi.list(controller.signal), WorkspaceApiError);
    let fetches = 0;
    const wrong = createWorkspaceApi(
      "https://api.example.test",
      a,
      async () => {
        throw new WorkspaceApiError("AUTH_REQUIRED", 401);
      },
      async () => {
        fetches++;
        return Response.json(workspace);
      },
    );
    await assert.rejects(wrong.read(id, controller.signal), WorkspaceApiError);
    assert.equal(fetches, 0);
  });
});
