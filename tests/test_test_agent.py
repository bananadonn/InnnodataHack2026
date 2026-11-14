"""Offline tests for test authoring boundaries; no model calls or repository test execution."""
import asyncio
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from pipeline import test_agent
from pipeline.agent import StageResult
from pipeline.explore import ExploreError
from pipeline.propose import Feature, FeaturePlan


def feature():
    return Feature(
        slug="sample-feature", category="sample", title="Sample", problem="Missing behavior",
        public_interface=["sample()"], behavior=["Returns one"], interaction_rules=[],
        edge_cases_and_errors=[], backward_compatibility=[], examples=[],
        acceptance_criteria=["Returns one", "Returns an integer"], builds_on=[],
        extension_point="module.py", source_files_to_modify=["module.py"], source_files_to_add=[],
        regression_test_files=["tests/test_existing.py"], new_test_file="tests/test_feature.py",
        novelty_rationale="fixture", difficulty_rationale="fixture", estimated_gold_lines=40,
    )


def draft():
    return test_agent.FeatureTests(
        feature_slug="sample-feature",
        files=[test_agent.TestFile(path="tests/test_feature.py", content=(
            "def test_value():\n    assert 1 == 1\n\ndef test_type():\n    assert isinstance(1, int)\n"))],
        coverage=[test_agent.Coverage(criterion=1, test_functions=["test_value"]),
                  test_agent.Coverage(criterion=2, test_functions=["test_type"])],
        ambiguities=[], notes=[],
    )


class TestAuthoring(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.repo = self.root / "repo"
        (self.repo / "tests").mkdir(parents=True)
        (self.repo / "tests/test_existing.py").write_text("def test_old():\n    assert True\n")
        self.validate = test_agent.feature_validator(feature(), self.repo)

    def test_rejects_coverage_gaps_and_invented_test_names(self):
        value = draft()
        value.coverage.pop()
        self.assertTrue(self.validate(value))
        value = draft()
        value.coverage[0].test_functions = ["test_nonexistent"]
        self.assertTrue(self.validate(value))

    def test_rejects_overwrites_traversal_and_invalid_python(self):
        for name in ("tests/test_existing.py", "../escape.py", "/tmp/escape.py", "module.py"):
            value = draft()
            value.files[0].path = name
            self.assertTrue(self.validate(value), name)
        value = draft()
        value.files[0].content = "def test_broken(:"
        self.assertTrue(self.validate(value))

    def test_ambiguous_spec_is_saved_without_materializing_test_code(self):
        value = draft()
        value.ambiguities = ["Error message unspecified"]
        value.files[0].path = "../escape.py"
        self.assertFalse(self.validate(value))
        output = self.root / "blocked"
        test_agent.save_feature(output, value)
        self.assertTrue((output / "draft.json").exists())
        self.assertFalse((output / "files").exists())
        self.assertFalse((output / "test_patch.diff").exists())

    def test_generated_patch_applies_without_changing_existing_tests(self):
        value = draft()
        self.assertFalse(self.validate(value))
        output = self.root / "output"
        test_agent.save_feature(output, value)
        result = subprocess.run(["git", "apply", "--check", str(output / "test_patch.diff")],
                                cwd=self.repo, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.repo / "tests/test_feature.py").exists())

    def test_discovery_checks_reported_paths_against_pinned_tree(self):
        validate = test_agent.discovery_validator(self.repo, {"tests/test_existing.py"})
        found = test_agent.RegressionDiscovery(found=True, folders=["tests"],
                                              existing_test_files=["tests/test_existing.py"], explanation="Read tests")
        self.assertFalse(validate(found))
        found.existing_test_files = ["tests/invented.py"]
        self.assertTrue(validate(found))
        missing = test_agent.RegressionDiscovery(found=False, folders=[], existing_test_files=[],
                                                explanation="No tests found")
        self.assertFalse(validate(missing))

    def test_offline_pipeline_reads_rules_and_preserves_attempts(self):
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        subprocess.run(["git", "-C", str(self.repo), "add", "."], check=True)
        subprocess.run(["git", "-C", str(self.repo), "-c", "user.name=Test", "-c",
                        "user.email=test@example.com", "commit", "-qm", "fixture"], check=True)
        commit = subprocess.check_output(["git", "-C", str(self.repo), "rev-parse", "HEAD"], text=True).strip()
        (self.root / "run.json").write_text(json.dumps({"run_id": "fixture", "commit_sha": commit}))
        (self.root / "features.json").write_text(FeaturePlan(variation_strategy="fixture", features=[feature()]).model_dump_json())
        (self.root / "features.md").write_text("Feature specification fixture")
        (self.root / "test_agent_rules.md").write_text("AUTHORING RULE SENTINEL")
        calls = []

        async def fake_stage(stage, workspace, prompt, system_prompt, log, **kwargs):
            self.assertIn("AUTHORING RULE SENTINEL", prompt)
            self.assertIn("Do not run tests", prompt)
            if stage.endswith("regression-discovery"):
                data = test_agent.RegressionDiscovery(found=True, folders=["tests"],
                    existing_test_files=["tests/test_existing.py"], explanation="Inspected existing tests")
            else:
                self.assertIn("Feature specification fixture", prompt)
                data = draft()
            self.assertFalse(kwargs["validator"](data))
            calls.append(stage)
            return StageResult(stage=stage, status="ok", data=data)

        with patch.object(test_agent.config, "ROOT", self.root), \
             patch.object(test_agent.config, "RUNS_DIR", self.root.parent), \
             patch.object(test_agent, "run_stage", fake_stage):
            first = asyncio.run(test_agent.create_tests(self.root.name))
            second = asyncio.run(test_agent.create_tests(self.root.name))
        self.assertNotEqual(first, second)
        self.assertTrue((first / "report.md").exists())
        self.assertTrue((second / "sample-feature/files/tests/test_feature.py").exists())
        self.assertEqual(len(calls), 4)
        self.assertFalse((self.repo / "tests/test_feature.py").exists())
        self.assertIn("not_run", (second / "summary.json").read_text())
        self.assertNotIn("._", "\n".join(test_agent.tracked_files(self.repo, commit)))


if __name__ == "__main__":
    unittest.main()
