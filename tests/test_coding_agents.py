"""Coding scaffold tests use temporary Git repos and mocked providers only."""
import asyncio
import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from pipeline import coding_common, haiku_agent, reference_agent
from pipeline.agent import StageResult
from pipeline.coding_common import CompatibilityEvidence, ImplementationDraft, SourceChange
from pipeline.explore import ExploreError
from pipeline.propose import Feature, FeaturePlan


class CodingTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.run = self.root / "runs/fixture"
        self.repo = self.run / "repo"
        (self.repo / "tests").mkdir(parents=True)
        (self.repo / "module.py").write_text("def value():\n    return 1\n")
        (self.repo / "tests/test_existing.py").write_text("def test_existing():\n    assert True\n")
        self.git("init", "-q")
        self.git("add", ".")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-qm", "base")
        self.commit = self.git("rev-parse", "HEAD").strip()
        self.feature = Feature(
            slug="sample-feature", category="sample", title="Sample", problem="Missing option",
            public_interface=["value(extra=False)"], behavior=["Returns two when extra is true"],
            interaction_rules=[], edge_cases_and_errors=[], backward_compatibility=["Default returns one"],
            examples=[], acceptance_criteria=["Preserve default", "Support new option"], builds_on=[],
            extension_point="module.py", source_files_to_modify=["module.py"], source_files_to_add=[],
            regression_test_files=["tests/test_existing.py"], new_test_file="tests/test_feature.py",
            novelty_rationale="fixture", difficulty_rationale="fixture", estimated_gold_lines=40,
        )
        (self.run / "run.json").write_text(json.dumps({"run_id": "fixture", "commit_sha": self.commit}))
        self.save_plan()
        (self.root / "implementation_agent_rules.md").write_text("Preserve existing behavior. RULE_SENTINEL")
        self.patches = [patch.object(coding_common.config, "ROOT", self.root),
                        patch.object(coding_common.config, "RUNS_DIR", self.root / "runs")]
        for item in self.patches:
            item.start()
            self.addCleanup(item.stop)

    def git(self, *args):
        return subprocess.check_output(["git", "-C", str(self.repo), *args], text=True, stderr=subprocess.PIPE)

    def save_plan(self):
        (self.run / "features.json").write_text(FeaturePlan(
            variation_strategy="fixture", features=[self.feature]).model_dump_json())

    def job(self, role="haiku"):
        return coding_common.prepare_job("fixture", "sample-feature", role, "test/model")

    def draft(self):
        return ImplementationDraft(feature_slug="sample-feature", summary="Add opt-in behavior",
            changes=[SourceChange(path="module.py", content="def value(extra=False):\n    return 2 if extra else 1\n")],
            compatibility_notes=["Default unchanged"], blockers=[])

    def test_preparation_is_independent_and_uses_pinned_commit(self):
        # An uncommitted change and private authoring artifacts must never leak to either agent.
        (self.repo / "module.py").write_text("DIRTY SOURCE\n")
        (self.run / "feature_tests").mkdir()
        (self.run / "feature_tests/secret.py").write_text("hidden test fixture")
        first, second = self.job(), self.job("reference")
        self.assertNotEqual(first.workspace, second.workspace)
        self.assertEqual((first.repo / "module.py").read_text(), "def value():\n    return 1\n")
        self.assertEqual((first.repo / "module.py").read_text(), (second.repo / "module.py").read_text())
        self.assertFalse((first.workspace / "feature_tests").exists())
        self.assertIn("RULE_SENTINEL", first.system_prompt)
        self.assertFalse(json.loads((first.workspace / "result.json").read_text())["accepted"])

    def test_patch_is_scoped_and_never_marked_validated(self):
        job = self.job()
        coding_common.save_draft(job, self.draft())
        result = json.loads((job.workspace / "result.json").read_text())
        self.assertEqual(result["status"], "awaiting_validation")
        self.assertFalse(result["accepted"])
        self.assertEqual(result["compatibility"]["regression_tests"], "not_run")
        self.assertIn("extra=False", (job.repo / "module.py").read_text())
        self.assertNotIn("extra=False", (self.repo / "module.py").read_text())
        self.assertEqual(self.git("status", "--porcelain"), "")

    def test_rejects_test_config_traversal_and_invalid_source(self):
        job = self.job()
        for path in ("tests/test_existing.py", "../module.py", "pyproject.toml", "conftest.py", ".git/config"):
            value = self.draft()
            value.changes[0].path = path
            self.assertTrue(coding_common.validate_draft(job, value), path)
        value = self.draft()
        value.changes[0].content = "def broken(:\n"
        self.assertTrue(coding_common.validate_draft(job, value))

    def test_blocks_incompatible_proposal_without_applying_changes(self):
        job = self.job()
        value = self.draft()
        value.changes = []
        value.blockers = ["Proposal requires changing an existing default"]
        coding_common.save_draft(job, value)
        self.assertFalse((job.workspace / "patch.diff").exists())
        result = json.loads((job.workspace / "result.json").read_text())
        self.assertEqual(result["status"], "blocked")
        self.assertFalse(result["accepted"])

    def test_workspace_tampering_is_rejected(self):
        job = self.job()
        (job.repo / "tests/test_existing.py").write_text("# weakened test\n")
        with self.assertRaises(ExploreError):
            coding_common.save_draft(job, self.draft())
        self.assertFalse((job.workspace / "patch.diff").exists())
        result = json.loads((job.workspace / "result.json").read_text())
        self.assertEqual(result["status"], "invalid")
        self.assertFalse(result["accepted"])

    def test_new_source_and_no_final_newline_in_base_patch(self):
        (self.repo / "module.py").write_text("VALUE = 1")
        self.git("add", ".")
        self.git("-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-qm", "no newline")
        self.commit = self.git("rev-parse", "HEAD").strip()
        (self.run / "run.json").write_text(json.dumps({"commit_sha": self.commit}))
        self.feature.source_files_to_add = ["extra.py"]
        self.save_plan()
        job = self.job()
        value = self.draft()
        value.changes.append(SourceChange(path="extra.py", content="VALUE = 2\n"))
        coding_common.save_draft(job, value)
        self.assertTrue((job.repo / "extra.py").is_file())
        self.assertIn("No newline", (job.workspace / "patch.diff").read_text())

    def test_acceptance_requires_all_execution_gates(self):
        self.assertFalse(CompatibilityEvidence().accepted)
        evidence = CompatibilityEvidence(base_suite="passed", feature_tests="passed", regression_tests="failed",
            full_suite="passed", feature_count=3, regression_count=5, evidence_paths=["actual-log.json"])
        self.assertFalse(evidence.accepted)
        evidence.regression_tests = "passed"
        self.assertTrue(evidence.accepted)
        evidence.regression_count = 0
        self.assertFalse(evidence.accepted)

    def test_prepare_only_does_not_call_either_provider(self):
        async def prepare():
            one = await haiku_agent.implement_feature("fixture", "sample-feature")
            two = await reference_agent.create_reference("fixture", "sample-feature")
            return one, two
        with patch.object(haiku_agent, "run_stage", side_effect=AssertionError("paid SDK call")), \
             patch.object(reference_agent, "run_reference_session", side_effect=AssertionError("paid HTTP call")):
            paths = asyncio.run(prepare())
        for path in paths:
            self.assertEqual(json.loads((path / "result.json").read_text())["status"], "prepared")

    def test_haiku_sdk_receives_model_rules_and_validation(self):
        async def fake_stage(stage, workspace, prompt, system, log, **kwargs):
            self.assertEqual(kwargs["model"], haiku_agent.config.HAIKU_IMPLEMENTATION_MODEL)
            self.assertEqual(kwargs["tools"], ["Read", "Glob", "Grep"])
            self.assertIn("RULE_SENTINEL", system)
            self.assertFalse(kwargs["validator"](self.draft()))
            return StageResult(stage=stage, status="ok", data=self.draft(), usage={"total_cost_usd": 0.1})
        with patch.object(haiku_agent, "run_stage", fake_stage):
            output = asyncio.run(haiku_agent.implement_feature("fixture", "sample-feature", execute=True))
        self.assertEqual(json.loads((output / "result.json").read_text())["status"], "awaiting_validation")

    def test_reference_tools_cannot_read_host_or_other_candidates(self):
        job = self.job("reference")
        for name in ("../rules.md", ".git/config", "../../haiku/attempt_1/draft.json"):
            with self.assertRaises(ValueError):
                reference_agent.read_tool(job, "read_file", {"path": name, "start_line": 1, "end_line": 3})
        read = reference_agent.read_tool(job, "read_file", {"path": "module.py", "start_line": 1, "end_line": 2})
        self.assertIn("return 1", read["content"])

    def test_reference_tool_loop_and_usage_with_mocked_openrouter(self):
        job = self.job("reference")
        requests = []
        def handler(request):
            payload = json.loads(request.content)
            self.assertNotIn("parallel_tool_calls", payload)
            self.assertTrue(payload["provider"]["require_parameters"])
            requests.append(payload)
            if len(requests) == 1:
                function = {"name": "read_file", "arguments": json.dumps(
                    {"path": "module.py", "start_line": 1, "end_line": 2})}
            else:
                self.assertIn("return 1", payload["messages"][-1]["content"])
                function = {"name": "submit_implementation", "arguments": self.draft().model_dump_json()}
            return httpx.Response(200, json={"id": f"response-{len(requests)}", "model": "actual/model",
                "usage": {"cost": 0.01, "prompt_tokens": 10, "completion_tokens": 20},
                "choices": [{"finish_reason": "tool_calls", "message": {"role": "assistant", "content": None,
                    "tool_calls": [{"id": str(len(requests)), "type": "function", "function": function}]}}]})
        async def run():
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                return await reference_agent.run_reference_session(job, client, "fixture-secret-key")
        value = asyncio.run(run())
        self.assertEqual(value.feature_slug, self.feature.slug)
        self.assertEqual(len(requests), 2)
        self.assertEqual(json.loads((job.workspace / "usage.json").read_text())["reported_cost_usd"], 0.02)
        for path in job.workspace.glob("*.json"):
            if not path.name.startswith("._"):
                self.assertNotIn("fixture-secret-key", path.read_text())

    def test_reference_http_error_preserves_reason_and_redacts_credentials(self):
        job = self.job("reference")
        async def run():
            def handler(request):
                return httpx.Response(404, json={"error": {"code": 404,
                    "message": "No endpoints support parameters; key fixture-secret-key Bearer other-key sk-test-123",
                    "metadata": {"raw": "fixture-secret-key"}}})
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                return await reference_agent.run_reference_session(job, client, "fixture-secret-key")
        with self.assertRaisesRegex(ExploreError, "No endpoints support parameters") as caught:
            asyncio.run(run())
        details = (job.workspace / "error_1.json").read_text()
        for secret in ("fixture-secret-key", "other-key", "sk-test-123"):
            self.assertNotIn(secret, str(caught.exception))
            self.assertNotIn(secret, details)
        self.assertNotIn("metadata", details)
        self.assertIn("404", details)

    def test_reference_stops_on_truncation_unknown_cost_and_budget(self):
        async def run(job, finish, usage):
            def handler(request):
                return httpx.Response(200, json={"usage": usage, "choices": [{"finish_reason": finish,
                    "message": {"role": "assistant", "tool_calls": [{"id": "1", "type": "function", "function": {
                        "name": "list_files", "arguments": '{"pattern":"*.py"}'}}]}}]})
            async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
                return await reference_agent.run_reference_session(job, client, "fixture-key")
        for finish, usage in (("length", {"cost": 0.01}), ("tool_calls", {}),
                              ("tool_calls", {"cost": 999.0})):
            with self.subTest(finish=finish, usage=usage), self.assertRaises(ExploreError):
                asyncio.run(run(self.job("reference"), finish, usage))


if __name__ == "__main__":
    unittest.main()
