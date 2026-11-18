"""Offline tests for the main-only, non-destructive GitHub label sync."""
from __future__ import annotations

import os
import pathlib
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))
from ci import sync_labels


class LabelSyncTests(unittest.TestCase):
    def test_catalog_has_valid_unique_label_definitions(self):
        labels = sync_labels.load_catalog()
        self.assertGreaterEqual(len(labels), 20)
        self.assertEqual(len({x["name"] for x in labels}), len(labels))
        self.assertIn("type:bug", {x["name"] for x in labels})
        self.assertIn("status:needs-triage", {x["name"] for x in labels})

    def test_never_writes_from_feature_branch(self):
        env = {
            "GH_TOKEN": "dummy-test-token",
            "GITHUB_REPOSITORY": "ThunderKhan/axiom",
            "GITHUB_REF": "refs/heads/chore/other",
        }
        with patch.dict(os.environ, env, clear=True), patch.object(
            sync_labels, "request_json"
        ) as api:
            with self.assertRaisesRegex(RuntimeError, "only from main"):
                sync_labels.sync()
            api.assert_not_called()

    def test_all_existing_matching_labels_are_noop(self):
        labels = sync_labels.load_catalog()
        env = {
            "GH_TOKEN": "dummy-test-token",
            "GITHUB_REPOSITORY": "ThunderKhan/axiom",
            "GITHUB_REF": "refs/heads/main",
        }
        with patch.dict(os.environ, env, clear=True), patch.object(
            sync_labels, "request_json", return_value=labels
        ) as api:
            sync_labels.sync()
            self.assertEqual(api.call_count, 1)
            self.assertEqual(api.call_args.args[0], "GET")

    def test_missing_labels_are_created_without_delete(self):
        labels = sync_labels.load_catalog()
        base = "/repos/ThunderKhan/axiom/labels"
        env = {
            "GH_TOKEN": "dummy-test-token",
            "GITHUB_REPOSITORY": "ThunderKhan/axiom",
            "GITHUB_REF": "refs/heads/main",
        }
        seen = []

        def fake_request(method, path, token, payload=None):
            seen.append((method, path, payload))
            return [] if method == "GET" else payload

        with patch.dict(os.environ, env, clear=True), patch.object(
            sync_labels, "request_json", side_effect=fake_request
        ):
            sync_labels.sync()
        self.assertEqual(seen[0], ("GET", base + "?per_page=100&page=1", None))
        self.assertEqual(
            seen[1:],
            [("POST", base, spec) for spec in labels],
        )
        self.assertFalse(any(method == "DELETE" for method, _, _ in seen))

    def test_existing_case_variant_is_updated_without_creation_or_rename(self):
        labels = sync_labels.load_catalog()
        desired = labels[0]
        other = {"name": "unrelated:preserve", "color": "cccccc", "description": "Unrelated"}
        existing = [dict(desired, name=desired["name"].upper(), color="ffffff"), other]
        env = {
            "GH_TOKEN": "dummy-test-token",
            "GITHUB_REPOSITORY": "ThunderKhan/axiom",
            "GITHUB_REF": "refs/heads/main",
        }
        seen = []

        def fake_request(method, path, token, payload=None):
            seen.append((method, path, payload))
            return existing if method == "GET" else payload

        with patch.dict(os.environ, env, clear=True), patch.object(
            sync_labels, "request_json", side_effect=fake_request
        ):
            sync_labels.sync()
        updated = [x for x in seen if x[0] == "PATCH"]
        self.assertEqual(updated, [
            ("PATCH", "/repos/ThunderKhan/axiom/labels/" + desired["name"].upper().replace(":", "%3A"),
             {"color": desired["color"], "description": desired["description"]})
        ])
        self.assertNotIn("name", updated[0][2])
        self.assertFalse(any(
            method == "POST" and payload["name"] == desired["name"]
            for method, _, payload in seen
        ))
        self.assertFalse(any("unrelated:preserve" in path and method != "GET"
                             for method, path, _ in seen))

    def test_catalog_rejects_casefold_duplicate_names(self):
        labels = sync_labels.load_catalog()
        with patch.object(sync_labels, "LABELS_FILE") as fake_file:
            import json
            fake_file.read_text.return_value = json.dumps(
                labels + [dict(labels[0], name=labels[0]["name"].upper())]
            )
            with self.assertRaisesRegex(ValueError, "duplicate label"):
                sync_labels.load_catalog()


if __name__ == "__main__":
    unittest.main()
