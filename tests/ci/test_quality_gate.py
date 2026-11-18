from __future__ import annotations

import pathlib
import sys
import tempfile
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

from ci.quality_gate import (
    QualityError, check_application_config, check_document_links, validate_command,
)


class QualityGateTests(unittest.TestCase):
    def test_documentation_only_is_explicit(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual([], check_application_config(pathlib.Path(folder), []))

    def test_app_code_without_real_commands_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            path = root / "apps/web/page.tsx"
            path.parent.mkdir(parents=True)
            path.write_text("export default function Page() { return null; }")
            with self.assertRaisesRegex(QualityError, "ci/quality.toml is missing"):
                check_application_config(root, [path])

    def test_placeholder_and_no_test_bypass_are_rejected(self):
        for value in (["echo", "passed"], ["npm", "test", "--passWithNoTests"], []):
            with self.subTest(value=value), self.assertRaises(QualityError):
                validate_command(value, "test")

    def test_missing_local_markdown_link_fails(self):
        with tempfile.TemporaryDirectory() as folder:
            root = pathlib.Path(folder)
            for name in ("AGENTS.md", "ENGINEERING.md", "docs/01-INDEX.md"):
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("# present\n")
            index = root / "docs/01-INDEX.md"
            index.write_text("[broken](missing.md)\n")
            with self.assertRaisesRegex(QualityError, "Broken Markdown link"):
                check_document_links(root, [index])


if __name__ == "__main__":
    unittest.main()
