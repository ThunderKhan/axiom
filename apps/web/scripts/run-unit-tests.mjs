import { spawnSync } from "node:child_process";
import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";

const root = fileURLToPath(new URL("../", import.meta.url));
const junit = process.argv.includes("--junit");

if (junit) {
  mkdirSync(new URL("../test-results/", import.meta.url), { recursive: true });
}

const args = ["--experimental-strip-types", "--test"];

if (junit) {
  args.push(
    "--test-reporter=spec",
    "--test-reporter=junit",
    "--test-reporter-destination=stdout",
    "--test-reporter-destination=test-results/junit.xml",
  );
}

args.push("src/lib/foundation.test.ts");

const result = spawnSync(process.execPath, args, {
  cwd: root,
  stdio: "inherit",
});

// Missing tests, signals and failed assertions must never become success.
process.exit(result.status ?? 1);
