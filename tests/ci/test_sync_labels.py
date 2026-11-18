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
        env = {
            "GH_TOKEN": "dummy-test-token",
            "GITHUB_REPOSITORY": "ThunderKhan/axiom",
            "GITHUB_REF": "refs/heads/main",
        }
        seen = []

        def fake_request(method, path, token, payload=None):
            seen.append((method, path))
            return [] if method == "GET" else payload

        with patch.dict(os.environ, env, clear=True), patch.object(
            sync_labels, "request_json", side_effect=fake_request
        ):
            sync_labels.sync()
        self.assertEqual(sum(m == "POST" for m, _ in seen), len(labels))
        self.assertEqual(sum(m == "DELETE" for m, _ in seen), 0)


if __name__ == "__main__":
    unittest.main()
