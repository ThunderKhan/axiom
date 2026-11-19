import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  canonicalWorkspaceName,
  InvalidWorkspaceResponse,
  isWorkspaceId,
  parseBootstrap,
  parseWorkspace,
  parseWorkspaceList,
} from "./workspace-contract.ts";

const owner = "11111111-1111-4111-8111-111111111111";
const id = "22222222-2222-4222-8222-222222222222";
const workspace = {
  id,
  name: "Product A",
  created_at: "2026-11-19T10:00:00Z",
  updated_at: "2026-11-19T10:00:00+00:00",
  version: 1,
};

describe("M1.6 workspace DTO and name boundary", () => {
  it("accepts the approved typed workspace shape", () => {
    assert.deepEqual(parseWorkspace(workspace), workspace);
    const unicode = { ...workspace, name: "😃".repeat(120) };
    assert.deepEqual(parseWorkspace(unicode), unicode);
    assert.deepEqual(
      parseWorkspaceList({ items: [workspace], next_cursor: null }),
      {
        items: [workspace],
        next_cursor: null,
      },
    );
    parseBootstrap(
      {
        user: { id: owner, status: "active", created_at: workspace.created_at },
        created: true,
      },
      owner,
    );
  });

  it("fails closed on malformed or identity-mismatched data", () => {
    for (const data of [
      null,
      [],
      { ...workspace, id: "not-uuid" },
      { ...workspace, name: null },
      { ...workspace, version: 0 },
      { ...workspace, version: 1.2 },
      { ...workspace, created_at: "yesterday" },
    ]) {
      assert.throws(() => parseWorkspace(data), InvalidWorkspaceResponse);
    }
    for (const data of [
      { items: [workspace, workspace], next_cursor: null },
      { items: [workspace], next_cursor: 17 },
      { items: null, next_cursor: null },
    ]) {
      assert.throws(() => parseWorkspaceList(data), InvalidWorkspaceResponse);
    }
    assert.throws(
      () =>
        parseBootstrap(
          {
            user: { id, status: "active", created_at: workspace.created_at },
            created: false,
          },
          owner,
        ),
      InvalidWorkspaceResponse,
    );
    assert.equal(isWorkspaceId("../../../admin"), false);
  });

  it("trims names but rejects unsafe and oversized names", () => {
    assert.equal(canonicalWorkspaceName("  Café 👋  "), "Café 👋");
    for (const value of [
      "",
      "  ",
      "a".repeat(121),
      "x\u0000y",
      "x\u0007y",
      "\ud800",
    ]) {
      assert.throws(() => canonicalWorkspaceName(value));
    }
    assert.equal(canonicalWorkspaceName("😃".repeat(120)), "😃".repeat(120));
  });
});
