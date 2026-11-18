"""Regression tests for CodeRabbit findings on Axiom's CI quality contract."""
from __future__ import annotations

import contextlib
import io
import pathlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[2]))

import ci.quality_gate as gate


class QualityRegressionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = pathlib.Path(temp.name)
        for name in gate.REQUIRED:
            self.write(name, "# required\n")
        self.original_workflow = (
            gate.ROOT / ".github/workflows/quality.yml"
        ).read_text(encoding="utf-8")
        self.write(".github/workflows/quality.yml", self.original_workflow)

    def write(self, path, data):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(data, encoding="utf-8")
        return target

    def check_workflow_mutation(self, mutated, message):
        self.write(".github/workflows/quality.yml", mutated)
        with self.assertRaisesRegex(gate.QualityError, message):
            gate.check_workflow(self.root)

    def make_package(self, manifest="package.json", lockfile="pnpm-lock.yaml",
                     test_file="src/page.test.ts"):
        root = self.root / "apps" / "web"
        root.mkdir(parents=True, exist_ok=True)
        manifests = {
            "package.json": '{"name":"ci-fixture","version":"1.0.0","private":true}\n',
            "pyproject.toml": '[project]\nname = "ci-fixture"\nversion = "0.0.1"\n',
            "go.mod": 'module example.com/ci-fixture\n\ngo 1.23\n',
        }
        self.write(f"apps/web/{manifest}", manifests.get(manifest, "{}\n"))
        locks = {"pnpm-lock.yaml": "lockfileVersion: '9.0'\n",
                 "uv.lock": "version = 1\n", "go.sum": ""}
        self.write(f"apps/web/{lockfile}", locks.get(lockfile, "lockfile\n"))
        self.write(f"apps/web/{test_file}", "it('works', () => {});\n")
        self.write("apps/web/src/app.ts", "export const hello = true;\n")
        config = [
            "version = 1", "", "[packages.web]",
            'directory = "apps/web"',
            f'manifest = "{manifest}"',
            f'lockfile = "{lockfile}"',
            f'test_files = ["{test_file}"]',
        ]
        for step in gate.CHECKS:
            config.append(f'{step} = ["tool", "{step}"]')
        if manifest != "go.mod":
            config.append('test_report = "build/junit.xml"')
        self.write("ci/quality.toml", "\n".join(config) + "\n")
        return root

    def make_runnable_python_package(self, test_method):
        self.make_package(
            manifest="pyproject.toml",
            lockfile="uv.lock",
            test_file="tests/test_sample.py",
        )
        source = self.write("apps/web/src/module.py", "def f(): return 1\n")
        self.write(
            "apps/web/tests/test_sample.py",
            "import unittest\n"
            "class SampleTest(unittest.TestCase):\n"
            f"    def test_regression(self): {test_method}\n",
        )
        runner = '''
import pathlib
import sys
import unittest
import xml.etree.ElementTree as ET
suite = unittest.defaultTestLoader.discover("tests", pattern="test_*.py")
result = unittest.TextTestRunner(verbosity=1).run(suite)
root = ET.Element("testsuite", tests=str(result.testsRun))
case = ET.SubElement(root, "testcase", name="test_regression")
if result.skipped:
    ET.SubElement(case, "skipped")
if result.failures:
    ET.SubElement(case, "failure").text = result.failures[0][1]
if result.errors:
    ET.SubElement(case, "error").text = result.errors[0][1]
pathlib.Path("build").mkdir(exist_ok=True)
ET.ElementTree(root).write("build/junit.xml", encoding="utf-8")
pathlib.Path("test-ran.marker").write_text(str(result.wasSuccessful()))
sys.exit(0 if result.wasSuccessful() else 1)
'''
        self.write("apps/web/run-tests.py", runner)
        config_file = self.root / "ci/quality.toml"
        config = config_file.read_text(encoding="utf-8")
        for step in gate.CHECKS:
            actual = (f'{step} = ["{sys.executable}", "-m", "compileall", "-q", "."]'
                      if step != "test"
                      else f'{step} = ["{sys.executable}", "run-tests.py"]')
            config = config.replace(f'{step} = ["tool", "{step}"]', actual)
        config_file.write_text(config, encoding="utf-8")
        return source

    def run_python_fixture_through_main(self, source):
        with patch.object(gate, "ROOT", self.root), patch.object(
            gate, "tracked", return_value=[source]
        ), patch.object(sys, "argv", ["ci/quality_gate.py", "application"]):
            with contextlib.redirect_stderr(io.StringIO()):
                return gate.main()

    def test_default_workflow_is_valid(self):
        gate.check_workflow(self.root)

    def test_mts_and_cts_trigger_required_application_config(self):
        for ext in (".mts", ".cts"):
            with self.subTest(ext=ext):
                path = self.write(f"apps/web/worker{ext}", "export const work = 1;\n")
                with self.assertRaisesRegex(gate.QualityError, "quality.toml is missing"):
                    gate.check_application_config(self.root, [path])

    def test_fence_length_and_literal_example_links(self):
        doc = self.write("docs/example.md", (
            "Before.\n\n"
            "Excerpt:\n\n"
            "````markdown\n"
            "[fake](no-such-file.md)\n"
            "```\n"
            "````\n\n"
            "[real](01-INDEX.md)\n"
        ))
        self.assertEqual(1, gate.check_document_links(self.root, [doc]))
        self.write("docs/example.md", "[actual broken](no-such-file.md)\n")
        with self.assertRaisesRegex(gate.QualityError, "Broken Markdown link"):
            gate.check_document_links(self.root, [doc])

    def test_unclosed_long_fence_fails(self):
        doc = self.write("docs/open.md", "````python\nprint('broken')\n```\n")
        with self.assertRaisesRegex(gate.QualityError, "Unbalanced Markdown"):
            gate.check_document_links(self.root, [doc])

    def test_duplicate_workflow_keys_fail(self):
        self.check_workflow_mutation(
            self.original_workflow + "\npermissions:\n  contents: read\n",
            "Duplicate workflow YAML key",
        )

    def test_required_jobs_cannot_override_read_only_permissions(self):
        for spec in ('    permissions: {}\n', '    permissions:\n      contents: write\n'):
            with self.subTest(spec=spec):
                self.check_workflow_mutation(
                    self.original_workflow.replace("  repository:\n", "  repository:\n" + spec),
                    "read-only contents access",
                )

    def test_required_events_cannot_disappear(self):
        self.check_workflow_mutation(
            self.original_workflow.replace("  workflow_dispatch:\n", ""),
            "manual dispatch",
        )

    def test_filtering_required_events_fails(self):
        examples = (
            self.original_workflow.replace(
                "  pull_request:\n", "  pull_request:\n    paths: ['docs/**']\n"
            ),
            self.original_workflow.replace(
                "    branches: [main]\n", "    branches: [main]\n    paths-ignore: ['src/**']\n"
            ),
        )
        for example in examples:
            with self.subTest():
                self.check_workflow_mutation(example, "must not filter|without path")

    def test_required_job_and_step_cannot_be_disabled(self):
        self.check_workflow_mutation(
            self.original_workflow.replace("  application:\n", "  application:\n    if: false\n"),
            "must not have a conditional",
        )
        self.check_workflow_mutation(
            self.original_workflow.replace("      - name: Check documentation",
                "      - if: false\n        name: Check documentation"),
            "conditionally skip",
        )

    def test_secret_expression_rejected(self):
        # This is only a synthetic policy test; no actual credential is provided.
        self.check_workflow_mutation(
            self.original_workflow.replace(
                "permissions:\n  contents: read\n",
                "permissions:\n  contents: read\nenv:\n  TOKEN: ${{ secrets.DEPLOY_TOKEN }}\n"
            ),
            "secret references",
        )

    def test_executable_basename_bypass_rejected(self):
        for command in (["/usr/bin/true"], ["/bin/echo", "ok"], ["C:\\bin\\true"]):
            with self.subTest(command=command), self.assertRaises(gate.QualityError):
                gate.validate_command(command, "lint")

    def test_manifest_cannot_alias_lockfile(self):
        self.make_package(lockfile="package.json")
        with self.assertRaisesRegex(gate.QualityError, "distinct files"):
            gate.check_application_config(
                self.root, [self.root / "apps/web/src/app.ts"]
            )

    def test_lockfile_must_match_real_package_ecosystem(self):
        self.make_package(lockfile="test-placeholder.lock")
        with self.assertRaisesRegex(gate.QualityError, "lockfile role"):
            gate.check_application_config(
                self.root, [self.root / "apps/web/src/app.ts"]
            )

    def test_production_go_file_is_not_a_test(self):
        self.make_package(manifest="go.mod", lockfile="go.sum", test_file="main.go")
        with self.assertRaisesRegex(gate.QualityError, "not an ecosystem test file"):
            gate.check_application_config(
                self.root, [self.root / "apps/web/main.go"]
            )

    def test_go_success_without_executed_tests_is_rejected(self):
        self.make_package(manifest="go.mod", lockfile="go.sum", test_file="main_test.go")
        config_file = self.root / "ci/quality.toml"
        config_file.write_text(
            config_file.read_text().replace(
                'test = ["tool", "test"]',
                'test = ["go", "test", "-json", "./..."]'
            ), encoding="utf-8",
        )
        source = self.root / "apps/web/main_test.go"
        fake = subprocess.CompletedProcess(
            args=["go", "test", "-json", "./..."],
            returncode=0,
            stdout='{"Action":"output","Package":"example","Output":"[no test files]"}\n',
            stderr="",
        )
        with patch.object(gate.subprocess, "run", return_value=fake):
            with self.assertRaisesRegex(gate.QualityError, "zero successfully executed tests"):
                gate.run_application(self.root, [source])

    def test_go_all_skipped_tests_are_not_success_evidence(self):
        self.make_package(manifest="go.mod", lockfile="go.sum", test_file="main_test.go")
        config_file = self.root / "ci/quality.toml"
        config_file.write_text(
            config_file.read_text().replace(
                'test = ["tool", "test"]',
                'test = ["go", "test", "-json", "./..."]'
            ), encoding="utf-8",
        )
        source = self.root / "apps/web/main_test.go"
        fake = subprocess.CompletedProcess(
            args=["go", "test", "-json", "./..."],
            returncode=0,
            stdout='{"Action":"run","Package":"example","Test":"TestSkipped"}\n'
                   '{"Action":"skip","Package":"example","Test":"TestSkipped"}\n',
            stderr="",
        )
        with patch.object(gate.subprocess, "run", return_value=fake):
            with self.assertRaisesRegex(gate.QualityError, "zero successfully executed tests"):
                gate.run_application(self.root, [source])

    def test_go_success_with_actual_test_events_is_accepted(self):
        self.make_package(manifest="go.mod", lockfile="go.sum", test_file="main_test.go")
        config_file = self.root / "ci/quality.toml"
        config_file.write_text(
            config_file.read_text().replace(
                'test = ["tool", "test"]',
                'test = ["go", "test", "-json", "./..."]'
            ), encoding="utf-8",
        )
        source = self.root / "apps/web/main_test.go"
        fake = subprocess.CompletedProcess(
            args=["go", "test", "-json", "./..."],
            returncode=0,
            stdout='{"Action":"run","Package":"example","Test":"TestReal"}\n'
                   '{"Action":"pass","Package":"example","Test":"TestReal"}\n',
            stderr="",
        )
        with patch.object(gate.subprocess, "run", return_value=fake):
            gate.run_application(self.root, [source])

    def test_full_application_mode_checks_exact_failing_and_passing_test(self):
        source = self.make_runnable_python_package("self.fail('expected')")
        self.assertEqual(1, self.run_python_fixture_through_main(source))
        marker = self.root / "apps/web/test-ran.marker"
        self.assertEqual("False", marker.read_text(encoding="utf-8"))
        # A harmless install failure cannot satisfy this regression: the
        # marker proves the actual unittest suite ran and failed.
        report = self.root / "apps/web/build/junit.xml"
        self.assertTrue(report.is_file())
        self.write(
            "apps/web/tests/test_sample.py",
            "import unittest\n"
            "class SampleTest(unittest.TestCase):\n"
            "    def test_regression(self): self.assertEqual(2, 2)\n",
        )
        marker.unlink()
        self.assertEqual(0, self.run_python_fixture_through_main(source))
        self.assertEqual("True", marker.read_text(encoding="utf-8"))

    def test_non_go_all_skipped_suite_fails_even_with_zero_exit(self):
        source = self.make_runnable_python_package("self.skipTest('not executed')")
        self.assertEqual(1, self.run_python_fixture_through_main(source))
        report = self.root / "apps/web/build/junit.xml"
        self.assertTrue(report.is_file())
        with self.assertRaisesRegex(gate.QualityError, "zero successfully executed"):
            gate.check_junit_test_evidence(report, "web")

    def test_report_from_previous_run_cannot_satisfy_new_run(self):
        source = self.make_runnable_python_package("self.assertTrue(True)")
        report = self.root / "apps/web/build/junit.xml"
        report.parent.mkdir(exist_ok=True)
        report.write_text('<testsuite><testcase name="stale"/></testsuite>')
        # All checks appear to return successfully, but no current test
        # command has created a report; stale evidence must be removed.
        with patch.object(gate.subprocess, "run", return_value=subprocess.CompletedProcess([], 0)):
            with self.assertRaisesRegex(gate.QualityError, "missing or oversized"):
                gate.run_application(self.root, [source])

    def test_junit_rejects_malformed_xml_and_empty_reports(self):
        report = self.write("apps/web/build/junit.xml", "<testsuite>broken")
        with self.assertRaisesRegex(gate.QualityError, "invalid JUnit"):
            gate.check_junit_test_evidence(report, "web")
        report.write_text('<testsuite tests="0"></testsuite>')
        with self.assertRaisesRegex(gate.QualityError, "zero successfully executed"):
            gate.check_junit_test_evidence(report, "web")


if __name__ == "__main__":
    unittest.main()
