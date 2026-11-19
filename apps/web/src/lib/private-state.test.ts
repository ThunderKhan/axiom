import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { clearPrivateState } from "./private-state.ts";

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
});
