import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { validateAuthConfig } from "./auth-config.ts";

const key = "sb_publishable_1234567890abcdef";

describe("M1 C1 public Supabase configuration boundary", () => {
  it("accepts exact HTTPS origin and loopback development origin", () => {
    assert.deepEqual(validateAuthConfig("https://project.supabase.co", key), {
      url: "https://project.supabase.co",
      key,
    });
    assert.equal(validateAuthConfig("http://127.0.0.1:54321", key)?.url, "http://127.0.0.1:54321");
  });
  it("treats absent and partially configured providers as unavailable", () => {
    assert.equal(validateAuthConfig(undefined, undefined), null);
    assert.equal(validateAuthConfig("https://project.supabase.co", undefined), null);
    assert.equal(validateAuthConfig(undefined, key), null);
  });
  it("rejects privileged keys, HTTP remote origins and URL injection", () => {
    for (const invalid of [
      "http://remote.example",
      "https://host.example/path",
      "https://host.example?next=/app",
      "https://host.example/#fragment",
      "https://name:pass@host.example",
      "//host.example",
      "https://host.example/",
      " https://host.example",
    ]) {
      assert.equal(validateAuthConfig(invalid, key), null, invalid);
    }
    for (const invalidKey of [
      "sb_secret_example",
      "service_role",
      "sb_publishable_short",
      "sb_publishable_too many spaces",
      "eyJhbGciOiJIUzI1NiJ9",
    ]) {
      assert.equal(validateAuthConfig("https://project.supabase.co", invalidKey), null);
    }
  });
});
