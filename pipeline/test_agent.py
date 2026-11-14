"""Author feature-test drafts and locate existing regression tests without executing them."""
from __future__ import annotations

import ast
import difflib
import json
import re
import subprocess
from pathlib import Path, PurePosixPath

from pydantic import BaseModel, Field

from pipeline import config
from pipeline.agent import BASE_RULES, EventLog, run_stage
from pipeline.explore import ExploreError, load_run, record_stage, write_json
from pipeline.propose import Feature, FeaturePlan


class RegressionDiscovery(BaseModel):
    found: bool
    folders: list[str] = Field(description="Repo-relative folders containing existing tests; '.' for root")
    existing_test_files: list[str] = Field(description="Representative existing test files actually inspected")
    explanation: str


class TestFile(BaseModel):
    path: str
    content: str = Field(description="Complete executable pytest source, not pseudocode")


class Coverage(BaseModel):
    criterion: int = Field(description="One-based acceptance criterion index")
    test_functions: list[str] = Field(description="Top-level test function names covering this criterion")


class FeatureTests(BaseModel):
    feature_slug: str
    files: list[TestFile]
    coverage: list[Coverage]
    ambiguities: list[str] = Field(description="Spec ambiguities; do not invent hidden requirements")
    notes: list[str]


SYSTEM_PROMPT = "You author feature tests and discover existing regression tests.\n\n" + BASE_RULES


def tracked_files(repo: Path, commit: str) -> set[str]:
    result = subprocess.run(
        ["git", "-C", str(repo), "ls-tree", "-r", "--name-only", "-z", commit],
        capture_output=True, check=True,
    )
    return {p.decode() for p in result.stdout.split(b"\0") if p and not Path(p.decode()).name.startswith("._")}


def discovery_validator(repo: Path, tracked: set[str]):
    def validate(result: RegressionDiscovery) -> list[str]:
        errors = []
        if result.found != bool(result.folders and result.existing_test_files):
            errors.append("found must agree with the presence of folders and existing test files")
        if not result.found and (result.folders or result.existing_test_files):
            errors.append("not-found results must have empty folder and file lists")
        for name in result.existing_test_files:
            if name not in tracked or not (repo / name).is_file():
                errors.append(f"test file is not an existing file at the pinned commit: {name}")
        for folder in result.folders:
            path = repo / folder
            if not path.resolve().is_relative_to(repo.resolve()) or not path.is_dir():
                errors.append(f"invalid regression test folder: {folder}")
            elif not any(PurePosixPath(name).is_relative_to(PurePosixPath(folder))
                         for name in result.existing_test_files):
                errors.append(f"folder has no reported existing test file: {folder}")
        for name in result.existing_test_files:
            if not any(PurePosixPath(name).is_relative_to(PurePosixPath(folder)) for folder in result.folders):
                errors.append(f"existing test file has no reported parent folder: {name}")
        return errors
    return validate


def feature_validator(feature: Feature, repo: Path):
    def validate(result: FeatureTests) -> list[str]:
        errors = []
        if result.feature_slug != feature.slug:
            errors.append("feature_slug does not match the input feature")
        if result.ambiguities:
            # Preserve a blocked draft without forcing the model to invent a requirement.
            return errors
        if [f.path for f in result.files] != [feature.new_test_file]:
            errors.append(f"write exactly the planned new test file: {feature.new_test_file}")
        names = set()
        for file in result.files:
            rel = PurePosixPath(file.path)
            if (rel.is_absolute() or ".." in rel.parts or "\\" in file.path
                    or not file.path.endswith(".py") or file.path.startswith("._")
                    or not (repo / file.path).resolve().is_relative_to(repo.resolve())):
                errors.append(f"unsafe test path: {file.path}")
                continue
            if (repo / file.path).exists():
                errors.append(f"test must be new, not an edit to an existing test: {file.path}")
            if file.path in feature.source_files_to_modify + feature.source_files_to_add:
                errors.append(f"test overlaps a planned gold source file: {file.path}")
            try:
                tree = ast.parse(file.content)
            except SyntaxError as exc:
                errors.append(f"invalid Python in {file.path}: {exc}")
                continue
            for node in tree.body:
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("test_"):
                    if node.name in names:
                        errors.append(f"duplicate test function: {node.name}")
                    names.add(node.name)
                    if not any(isinstance(n, (ast.Assert, ast.With, ast.AsyncWith)) for n in ast.walk(node)):
                        errors.append(f"test has no assertion or exception context: {node.name}")
        if not names:
            errors.append("no top-level pytest test functions were generated")
        expected = set(range(1, len(feature.acceptance_criteria) + 1))
        if {c.criterion for c in result.coverage} != expected:
            errors.append("coverage must map every acceptance criterion using one-based indices")
        for item in result.coverage:
            if not item.test_functions or not set(item.test_functions) <= names:
                errors.append(f"criterion {item.criterion} must reference actual generated test functions")
        mapped = {name for c in result.coverage for name in c.test_functions}
        if names - mapped:
            errors.append(f"tests missing a criterion mapping: {sorted(names - mapped)}")
        return errors
    return validate


def save_feature(output: Path, result: FeatureTests) -> None:
    output.mkdir(parents=True, exist_ok=True)
    write_json(output / "draft.json", result.model_dump())
    if result.ambiguities:
        return
    patch = []
    for file in result.files:
        destination = output / "files" / file.path
        destination.parent.mkdir(parents=True, exist_ok=True)
        content = file.content if file.content.endswith("\n") else file.content + "\n"
        destination.write_text(content, encoding="utf-8")
        patch.append(f"diff --git a/{file.path} b/{file.path}\nnew file mode 100644\n")
        patch.extend(difflib.unified_diff([], content.splitlines(keepends=True),
                                        fromfile="/dev/null", tofile=f"b/{file.path}"))
    (output / "test_patch.diff").write_text("".join(patch), encoding="utf-8")


async def create_tests(run_id: str) -> Path:
    workspace, meta = load_run(run_id)
    plan_path = workspace / "features.json"
    if not plan_path.is_file():
        raise ExploreError(f"run {run_id} has no features.json; run propose first")
    try:
        plan = FeaturePlan.model_validate_json(plan_path.read_text(encoding="utf-8"))
        rules = (config.ROOT / "test_agent_rules.md").read_text(encoding="utf-8")
    except (ValueError, OSError) as exc:
        raise ExploreError(f"cannot load feature plan or test-agent rules: {exc}") from exc
    if not plan.features or len({f.slug for f in plan.features}) != len(plan.features):
        raise ExploreError("feature plan must contain features with distinct slugs")
    if any(not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)+", f.slug) for f in plan.features):
        raise ExploreError("feature plan contains an invalid slug")
    repo = workspace / "repo"
    try:
        tracked = tracked_files(repo, meta["commit_sha"])
        actual = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    except (subprocess.CalledProcessError, KeyError, TypeError) as exc:
        raise ExploreError(f"cannot inspect pinned repository: {exc}") from exc
    if actual != meta["commit_sha"]:
        raise ExploreError("repository HEAD does not match the run's pinned commit")
    # A fresh attempt preserves all previous drafts, failures and usage evidence.
    root = workspace / "feature_tests"
    root.mkdir(exist_ok=True)
    attempt = 1
    while (root / f"attempt_{attempt}").exists():
        attempt += 1
    output = root / f"attempt_{attempt}"
    output.mkdir()
    (output / "rules.md").write_text(rules, encoding="utf-8")
    write_json(output / "features_input.json", plan.model_dump())
    feature_text = ""
    for filename in ("feature.md", "features.md"):
        path = workspace / filename
        if path.is_file():
            text = path.read_text(encoding="utf-8")
            (output / filename).write_text(text, encoding="utf-8")
            feature_text += f"\n{filename}:\n{text}\n"
    log = EventLog(workspace / "events.jsonl")
    prefix = f"test-agent:{attempt}"
    instructions = (
        "\n\nApplication-provided authoring rules:\n" + rules +
        "\n\nCURRENT SCOPE: create new pytest test source for each proposed feature and locate the "
        "existing regression-test folders/files. Do not run tests, select final PASS_TO_PASS IDs, "
        "or build a Harbor package yet. There is no gold implementation or final instruction.md "
        "available at this stage. Report validation as pending; never invent collected test IDs "
        "or passing results. Output source as structured data; the application saves the files."
    )
    discovery = await run_stage(
        prefix + ":regression-discovery", workspace,
        "Inspect ./repo to find its existing regression tests. Read representative tests and test "
        "configuration. Return found=true with repo-relative folders and inspected file paths, "
        "or found=false with empty lists and an explanation. These are existing tests, not new "
        "feature tests. Do not claim they passed.\n" + instructions,
        SYSTEM_PROMPT, log, model=config.TEST_MODEL,
        max_budget_usd=config.TEST_DISCOVERY_MAX_BUDGET_USD,
        schema=RegressionDiscovery, validator=discovery_validator(repo, tracked),
    )
    record_stage(meta, workspace, discovery)
    if discovery.status != "ok":
        write_json(output / "summary.json", {
            "status": "discovery_failed", "features": [], "regression": None,
            "error": discovery.error, "validation": "not_run",
        })
        (output / "report.md").write_text(
            "# Test agent report\n\nRegression discovery failed; found/not-found is unknown.\n\n"
            f"{discovery.status}: {discovery.error}\n\nNo feature tests were generated.\n",
            encoding="utf-8",
        )
        raise ExploreError(f"regression discovery failed ({discovery.status}): {discovery.error}")
    write_json(output / "regression_tests.json", discovery.data.model_dump())
    rows = []
    for feature in plan.features:
        res = await run_stage(
            prefix + ":" + feature.slug, workspace,
            "Create concrete pytest tests for this feature. Read the relevant source and existing "
            "tests for conventions, but do not modify them. Use exactly the planned new_test_file; "
            "use top-level test_* functions. Map every acceptance criterion (one-based index) to "
            "actual generated test function names. Every test must have a criterion mapping. "
            "Cover specified behavior and interactions with concrete assertions, including errors "
            "where specified. If a required behavior is ambiguous, return ambiguities instead of "
            "inventing a requirement. The feature JSON gives the structured proposal; if the "
            "Markdown disagrees, report that ambiguity.\n" + instructions +
            "\n\nFeature:\n" + feature.model_dump_json(indent=2) +
            "\n\nExisting regression tests:\n" + discovery.data.model_dump_json(indent=2) +
            "\n\nFeature document:\n" + feature_text,
            SYSTEM_PROMPT, log, model=config.TEST_MODEL, max_budget_usd=config.TEST_MAX_BUDGET_USD,
            schema=FeatureTests, validator=feature_validator(feature, repo),
        )
        record_stage(meta, workspace, res)
        status = res.status
        if res.status == "ok":
            save_feature(output / feature.slug, res.data)
            status = "blocked" if res.data.ambiguities else "drafted"
        rows.append({"slug": feature.slug, "status": status, "error": res.error,
                     "ambiguities": res.data.ambiguities if res.data else [],
                     "validation": "not_run"})
        write_json(output / "summary.json", {"features": rows, "regression": discovery.data.model_dump()})
    lines = ["# Test agent report", "", f"Run: `{run_id}`; attempt: {attempt}", "",
             f"Existing regression tests found: **{'yes' if discovery.data.found else 'no'}**", ""]
    lines += [f"- Folder: `repo/{p}`" for p in discovery.data.folders]
    lines += [f"- Existing file: `repo/{p}`" for p in discovery.data.existing_test_files]
    lines += ["", discovery.data.explanation, "", "## Feature test drafts", ""]
    for row in rows:
        lines.append(f"- `{row['slug']}`: {row['status']}")
        lines.extend(f"  - Ambiguity: {a}" for a in row["ambiguities"])
        if row["error"]:
            lines.append(f"  - Error: {row['error']}")
    lines += ["", "Drafts only. Python syntax, paths and criterion mappings were checked. Test collection, "
              "base health, nop/oracle, mutation checks and Harbor packaging have not run. Existing "
              "test paths were checked against the pinned Git tree; behavioral coverage still needs review.", ""]
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")
    print(f"Existing regression tests found: {'yes' if discovery.data.found else 'no'}")
    for folder in discovery.data.folders:
        print(f"Regression test folder: {repo / folder}")
    print(f"Test agent report: {output / 'report.md'}")
    if any(row["status"] != "drafted" for row in rows):
        raise ExploreError(f"some feature drafts failed or are blocked; see {output / 'report.md'}")
    return output
