"""Validate repository governance YAML/JSON using the actual checked-out files."""
from __future__ import annotations

import json
import re
from pathlib import Path
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]
GITHUB = ROOT / ".github"


def read_yaml(path: Path):
    with path.open(encoding="utf-8") as handle:
        # Quote the GitHub Actions top-level event key before SafeLoader.
        # Other YAML booleans must remain typed, so "false" is NOT False.
        raw = re.sub(r"^on:", '"on":', handle.read(), flags=re.MULTILINE)
        return yaml.safe_load(raw)


class GovernanceConfigTests(unittest.TestCase):
    def test_coderabbit_safe_review_configuration(self):
        config = read_yaml(ROOT / ".coderabbit.yaml")
        reviews = config["reviews"]
        self.assertIs(reviews["auto_review"]["enabled"], True)
        self.assertIs(reviews["auto_review"]["drafts"], False)
        self.assertIs(reviews["auto_approvals"]["enabled"], False)
        self.assertIs(reviews["auto_apply_labels"], False)
        self.assertTrue(reviews["path_instructions"])
        self.assertTrue(reviews["labeling_instructions"])
        labels = json.loads((GITHUB / "labels.json").read_text(encoding="utf-8"))
        label_names = {item["name"] for item in labels}
        self.assertTrue(all(entry["label"] in label_names
                            for entry in reviews["labeling_instructions"]))

    def test_issue_forms_are_valid_and_labels_defined(self):
        catalog = json.loads((GITHUB / "labels.json").read_text(encoding="utf-8"))
        names = {label["name"] for label in catalog}
        self.assertEqual(len(names), len(catalog))
        forms = sorted((GITHUB / "ISSUE_TEMPLATE").glob("[0-9][0-9]-*.yml"))
        self.assertGreaterEqual(len(forms), 3)
        for path in forms:
            with self.subTest(path=path.name):
                form = read_yaml(path)
                self.assertTrue(form.get("name") and form.get("description"))
                self.assertTrue(form.get("body"))
                self.assertTrue(
                    any(item.get("type") in {"input", "textarea", "dropdown", "checkboxes"}
                        for item in form["body"]),
                    "Issue form must contain an input field, not only markdown",
                )
                self.assertTrue(set(form.get("labels", [])).issubset(names))
                ids = [field.get("id") for field in form["body"] if field.get("id")]
                self.assertEqual(len(ids), len(set(ids)))
        self.assertIs(read_yaml(GITHUB / "ISSUE_TEMPLATE/config.yml")["blank_issues_enabled"], False)

    def test_label_sync_is_main_only_and_minimally_privileged(self):
        workflow = read_yaml(GITHUB / "workflows/sync-labels.yml")
        self.assertEqual(set(workflow["on"]), {"push", "workflow_dispatch"})
        self.assertEqual(workflow["on"]["push"]["branches"], ["main"])
        self.assertEqual(workflow["on"]["push"]["paths"], [".github/labels.json"])
        self.assertEqual(
            workflow["permissions"], {"contents": "read", "issues": "write"}
        )
        self.assertEqual(workflow["concurrency"]["cancel-in-progress"], False)
        job = workflow["jobs"]["sync-labels"]
        self.assertNotIn("permissions", job, "Job override cannot broaden scopes")
        guard = str(job["if"]).strip()
        if guard.startswith("${{") and guard.endswith("}}"):
            guard = guard[3:-2].strip()
        self.assertEqual(guard, "github.ref == 'refs/heads/main'")
        self.assertTrue(any("ci/sync_labels.py" in step.get("run", "")
                            for step in job["steps"]))
        self.assertNotIn("pull_request_target", workflow["on"])
        self.assertNotIn("pull_request", workflow["on"])

    def test_governance_check_never_needs_write_permissions(self):
        workflow = read_yaml(GITHUB / "workflows/governance.yml")
        self.assertEqual(workflow["permissions"], {"contents": "read"})
        for name, job in workflow["jobs"].items():
            self.assertNotIn("permissions", job, f"{name} overrides permissions")
        self.assertIn("pull_request", workflow["on"])
        self.assertNotIn("pull_request_target", workflow["on"])

    def test_boolean_literals_are_not_accepted_as_quoted_strings(self):
        original = read_yaml(ROOT / ".coderabbit.yaml")
        self.assertIs(original["reviews"]["auto_review"]["drafts"], False)
        self.assertIs(
            read_yaml(GITHUB / "ISSUE_TEMPLATE/config.yml")["blank_issues_enabled"],
            False,
        )

    def test_templates_and_maintainer_guides_exist(self):
        for relative in (".github/PULL_REQUEST_TEMPLATE.md",
                         ".github/CODEOWNERS", "CONTRIBUTING.md", "SECURITY.md",
                         "docs/01-INDEX.md"):
            with self.subTest(path=relative):
                self.assertTrue((ROOT / relative).is_file())


if __name__ == "__main__":
    unittest.main()
