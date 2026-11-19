import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { clearPrivateState, clearPrivateStateSafely } from "./private-state.ts";

describe("M1 H3 private-state cleanup contract", () => {
  it("clears private user/workspace keys while preserving unrelated preferences", () => {
    const data = new Map([
      ["axiom:workspace:user-a", "first"],
      ["axiom:workspace:user-b", "second"],
      ["axiom:private:user-a:query", "sensitive"],
      ["color-scheme", "light"],
    ]);
    const store = {
      get length() {
        return data.size;
      },
      key(index: number) {
        return [...data.keys()][index] ?? null;
      },
      removeItem(key: string) {
        data.delete(key);
      },
    };
    clearPrivateState(store);
    assert.deepEqual([...data.entries()], [["color-scheme", "light"]]);
    clearPrivateState(store);
    assert.deepEqual([...data.entries()], [["color-scheme", "light"]]);
  });
  it("continues cleaning session storage when localStorage throws SecurityError", () => {
    const privateData = new Map([["axiom:private:user-b:query", "sensitive"]]);
    const session = {
      get length() {
        return privateData.size;
      },
      key(index: number) {
        return [...privateData.keys()][index] ?? null;
      },
      removeItem(key: string) {
        privateData.delete(key);
      },
    };
    const errors: number[] = [];
    clearPrivateStateSafely(
      [
        () => {
          throw new Error("denied");
        },
        () => session,
      ],
      (index) => errors.push(index),
    );
    assert.deepEqual(errors, [0]);
    assert.equal(privateData.size, 0);
  });

  it("reports both inaccessible stores without propagating or logging data", () => {
    const failures: number[] = [];
    clearPrivateStateSafely(
      [
        () => {
          throw new Error("sensitive");
        },
        () => {
          throw new Error("sensitive");
        },
      ],
      (index) => failures.push(index),
    );
    assert.deepEqual(failures, [0, 1]);
  });
});
