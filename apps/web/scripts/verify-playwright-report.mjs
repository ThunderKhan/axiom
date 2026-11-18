import { existsSync, readdirSync } from "node:fs";
import { fileURLToPath } from "node:url";

const report = fileURLToPath(new URL("../playwright-report/", import.meta.url));
const index = fileURLToPath(new URL("../playwright-report/index.html", import.meta.url));
const attachments = fileURLToPath(new URL("../playwright-report/data/", import.meta.url));

if (!existsSync(index) || !existsSync(attachments)) {
  console.error("Playwright HTML report or attachments are missing");
  process.exitCode = 1;
} else {
  const traces = readdirSync(attachments, { withFileTypes: true }).filter(
    (entry) => entry.isFile() && entry.name.endsWith(".zip"),
  );
  if (traces.length === 0) {
    console.error("Playwright HTML report contains no trace archives");
    process.exitCode = 1;
  } else {
    console.log(`Verified ${traces.length} trace archive(s) in ${report}`);
  }
}
