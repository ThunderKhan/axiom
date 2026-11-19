import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { validatePublicApiBaseUrl } from "./public-api.ts";

describe("public API origin contract", () => {
  it("accepts exact loopback HTTP and production HTTPS origins", () => {
    assert.equal(
      validatePublicApiBaseUrl("http://127.0.0.1:8000"),
      "http://127.0.0.1:8000",
    );
    assert.equal(
      validatePublicApiBaseUrl("https://api.example.test"),
      "https://api.example.test",
    );
  });

  it("permits a standalone frontend with no configured API", () => {
    assert.equal(validatePublicApiBaseUrl(undefined), "");
  });

  it("rejects invalid, credentialed, and non-loopback HTTP origins", () => {
    for (const invalid of [
      "http://remote.example:8000",
      "***api.example.test",
      "https://api.example.test/path",
      "https://api.example.test?key=secret",
      "https://api.example.test/#fragment",
      "http://127.0.0.1:8000/",
      " http://127.0.0.1:8000",
      "not-a-url",
    ]) {
      assert.throws(() => validatePublicApiBaseUrl(invalid), Error, invalid);
    }
  });
});
