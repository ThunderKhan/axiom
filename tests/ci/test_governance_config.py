"""Validate repository governance YAML/JSON using the actual checked-out files."""
from __future__ import annotations

import json
from pathlib import Path
import unittest

import yaml

ROOT = Path(__file__).resolve().parents[2]
GITHUB = ROOT / ".github"


def read_yaml(path: Path):
    with path.open(encoding="utf-8") as handle:
        # BaseLoader preserves GitHub Actions' "on" key as a string, avoiding
        # the YAML 1.1 boolean conversion in PyYAML's default safe loader.
        return yaml.load(handle, Loader=yaml.BaseLoader)


class GovernanceConfigTests(unittest.TestCase):
    def test_coderabbit_safe_review_configuration(self):
        config = read_yaml(ROOT / ".coderabbit.yaml")
        reviews = config["reviews"]
        self.assertEqual(reviews["auto_review"]["enabled"], "true")
        self.assertEqual(reviews["auto_review"]["drafts"], "false")
        self.assertEqual(reviews["auto_approvals"]["enabled"], "false")
        self.assertEqual(reviews["auto_apply_labels"], "false")
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
                self.assertTrue(set(form.get("labels", [])).issubset(names))
                ids = [field.get("id") for field in form["body"] if field.get("id")]
                self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(read_yaml(GITHUB / "ISSUE_TEMPLATE/config.yml")["blank_issues_enabled"], "false")

    def test_label_sync_is_explicit_and_main_only(self):
        workflow = read_yaml(GITHUB / "workflows/sync-labels.yml")
        self.assertEqual(set(workflow["on"]), {"workflow_dispatch"})
        self.assertEqual(workflow["permissions"]["contents"], "read")
        self.assertEqual(workflow["permissions"]["issues"], "write")
        job = workflow["jobs"]["sync-labels"]
        self.assertIn("refs/heads/main", job["if"])
        self.assertTrue(any("ci/sync_labels.py" in step.get("run", "")
                            for step in job["steps"]))
        self.assertNotIn("pull_request_target", workflow["on"])

    def test_governance_check_never_needs_write_permissions(self):
        workflow = read_yaml(GITHUB / "workflows/governance.yml")
        self.assertEqual(workflow["permissions"], {"contents": "read"})
        self.assertIn("pull_request", workflow["on"])
        self.assertNotIn("pull_request_target", workflow["on"])

    def test_templates_and_maintainer_guides_exist(self):
        for relative in (".github/PULL_REQUEST_TEMPLATE.md",
                         ".github/CODEOWNERS", "CONTRIBUTING.md", "SECURITY.md",
                         "docs/01-INDEX.md"):
            with self.subTest(path=relative):
                self.assertTrue((ROOT / relative).is_file())


if __name__ == "__main__":
    unittest.main()
