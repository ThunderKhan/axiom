import assert from "node:assert/strict";
import { describe, it } from "node:test";
import {
  allowAutomaticCreateRetry,
  availablePreferenceStorage,
  chooseRequestedWorkspace,
  makeCreateAttempt,
  mergeOwnedWorkspaces,
  readWorkspacePreference,
  RequestGeneration,
  saveWorkspacePreference,
  uncertainCreationState,
  workspacePreferenceKey,
} from "./workspace-context.ts";
import type { Workspace } from "./workspace-contract.ts";

const a = "11111111-1111-4111-8111-111111111111";
const b = "22222222-2222-4222-8222-222222222222";
const one = "33333333-3333-4333-8333-333333333333";
const two = "44444444-4444-4444-8444-444444444444";

function mockStorage() {
  const records = new Map<string, string>();
  return {
    records,
    getItem(key: string) {
      return records.get(key) ?? null;
    },
    setItem(key: string, value: string) {
      records.set(key, value);
    },
    removeItem(key: string) {
      records.delete(key);
    },
  };
}

function workspace(id: string): Workspace {
  return {
    id,
    name: id,
    created_at: "2026-11-19T10:00:00Z",
    updated_at: "2026-11-19T10:00:00Z",
    version: 1,
  };
}

describe("H2/H3 per-subject preferences and async context", () => {
  it("namespaces preferences and refuses invalid stored values", () => {
    const storage = mockStorage();
    assert.notEqual(workspacePreferenceKey(a), workspacePreferenceKey(b));
    saveWorkspacePreference(storage, a, one);
    saveWorkspacePreference(storage, b, two);
    assert.equal(readWorkspacePreference(storage, a), one);
    assert.equal(readWorkspacePreference(storage, b), two);
    storage.setItem(workspacePreferenceKey(a), "../../foreign");
    assert.equal(readWorkspacePreference(storage, a), null);
    assert.equal(readWorkspacePreference(storage, b), two);
    assert.equal(chooseRequestedWorkspace("not-a-uuid", one), null);
    assert.equal(chooseRequestedWorkspace(two, one), two);
    assert.equal(chooseRequestedWorkspace(null, one), one);
    saveWorkspacePreference(storage, b, null);
    assert.equal(readWorkspacePreference(storage, b), null);
    assert.throws(() => workspacePreferenceKey("unverified"));
  });

  it("does not promote storage failures into authorization", () => {
    const blocked = {
      getItem() {
        throw new Error("SecurityError");
      },
      setItem() {
        throw new Error("SecurityError");
      },
      removeItem() {
        throw new Error("SecurityError");
      },
    };
    assert.equal(readWorkspacePreference(blocked, a), null);
    assert.doesNotThrow(() => saveWorkspacePreference(blocked, a, one));
  });

  it("continues without persistence when acquiring browser storage throws", () => {
    const unavailable = availablePreferenceStorage(() => {
      throw new Error("SecurityError");
    });
    assert.equal(unavailable, null);
    assert.equal(readWorkspacePreference(unavailable, a), null);
    assert.doesNotThrow(() => saveWorkspacePreference(unavailable, a, one));
    const storage = mockStorage();
    assert.equal(
      availablePreferenceStorage(() => storage),
      storage,
    );
  });

  it("keeps an interrupted write blocked until an authorized list is inspected", () => {
    const attempt = makeCreateAttempt(a, "Project", 1000, () => one);
    assert.deepEqual(uncertainCreationState(attempt, a, false), {
      kind: "uncertain",
      name: "Project",
      inspected: false,
    });
    assert.deepEqual(uncertainCreationState(attempt, a, true), {
      kind: "uncertain",
      name: "Project",
      inspected: true,
    });
    assert.equal(uncertainCreationState(attempt, b, true), null);
    assert.equal(uncertainCreationState(null, a, true), null);
  });

  it("select and switch preserve only the newest context", () => {
    const current = new RequestGeneration();
    const aSequence = current.next();
    assert.equal(current.current(aSequence), true);
    const bSequence = current.next();
    assert.equal(current.current(aSequence), false);
    assert.equal(current.current(bSequence), true);
    current.next(); // Logout/account change invalidates every pending response.
    assert.equal(current.current(bSequence), false);
    assert.deepEqual(
      mergeOwnedWorkspaces(
        [workspace(one), workspace(two)],
        workspace(two),
      ).map((x) => x.id),
      [two, one],
    );
  });

  it("binds create keys and payload to the originating user, never auto-retries without a bound", () => {
    const attempt = makeCreateAttempt(a, "Project", 1000, () => one);
    assert.equal(attempt.name, "Project");
    assert.equal(attempt.key, one);
    assert.equal(allowAutomaticCreateRetry(attempt, a, 1100), false);
    assert.equal(allowAutomaticCreateRetry(attempt, b, 1100, 1000), false);
    assert.equal(allowAutomaticCreateRetry(attempt, a, 1100, 1000), true);
    assert.equal(
      allowAutomaticCreateRetry(attempt, a, 1000 + 24 * 60 * 60 * 1000, 1000),
      false,
    );
    assert.equal(allowAutomaticCreateRetry(attempt, a, 900, 1000), false);
    assert.equal(allowAutomaticCreateRetry(attempt, a, 1100, Infinity), false);
    assert.throws(() => makeCreateAttempt(a, "Project", 0, () => "!"));
    assert.throws(() => makeCreateAttempt("foreign", "Project", 0, () => one));
  });
});
