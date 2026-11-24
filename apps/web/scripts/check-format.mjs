import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";
import * as prettier from "prettier";

const cli = fileURLToPath(
  new URL("../node_modules/prettier/bin/prettier.cjs", import.meta.url),
);
const check = spawnSync(process.execPath, [cli, "--check", "."], {
  stdio: "inherit",
});
if (check.status === 0) process.exit(0);

// A diagnostic must never turn a failed formatter check into a success.
process.exitCode = 1;
const different = spawnSync(process.execPath, [cli, "--list-different", "."], {
  encoding: "utf8",
});
const tracked = spawnSync("git", ["ls-files", "-z"], { encoding: "utf8" });
if (!different.stdout || tracked.status !== 0 || !tracked.stdout) {
  process.exit(1);
}

const allowed = new Set(tracked.stdout.split("\0"));
const files = different.stdout
  .split(/\r?\n/)
  .filter((file) => allowed.has(file))
  .slice(0, 20);
const directory = mkdtempSync(join(tmpdir(), "axiom-format-"));
try {
  for (const file of files) {
    const original = readFileSync(file, "utf8");
    const config = await prettier.resolveConfig(file);
    const formatted = await prettier.format(original, {
      ...config,
      filepath: file,
    });
    const output = join(directory, "formatted");
    writeFileSync(output, formatted, "utf8");
    console.error("Expected formatting for " + file);
    spawnSync("git", ["diff", "--no-index", "--", file, output], {
      stdio: "inherit",
    });
  }
} finally {
  rmSync(directory, { recursive: true, force: true });
}
