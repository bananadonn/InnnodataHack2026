#!/usr/bin/env python3
"""validate_submission.py — self-check that your WHOLE submission is complete, BEFORE you send it.

`check_structure.py` and `selfcheck.sh` validate individual task packages. This checks the **submission as a
whole** — the things `SUBMISSION.md` asks for are present and loadable, nothing leaks secrets, and your
`pipeline_run.json` telemetry is well-formed and matches your packages.

It does NOT grade you and reveals nothing about how we score — it only answers "is this submission complete,
well-formed, and safe to send?". Passing it is necessary, not sufficient (we still evaluate against the brief).

Checks (ERROR = blocking, must fix; warn = advisory, please look):
  1. ZIP name — `TeamName_Track1.zip` (only when you pass a .zip).
  2. No secrets — no API keys / tokens anywhere in the submission.
  3. Task packages — at least one (you must deliver 5 distinct); each passes `check_structure.py`.
  4. pipeline_run.json — present, valid JSON, one row per task, required fields present + numeric,
     and its instance_ids match the packages you shipped.
  5. Pipeline code + README — runnable pipeline with run instructions is present.
  6. Variation writeup — a writeup / README explaining your variation strategy is present.

Usage:
    harness/validate_submission.py path/to/submission_dir
    harness/validate_submission.py TeamName_Track1.zip
Exit 0 if there are no ERRORs, 1 otherwise.
"""
from __future__ import annotations
import json, os, re, sys, zipfile, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import check_structure  # reuse the per-package structure lint  # noqa: E402

# pipeline_run.json row schema (SUBMISSION.md §3b). instance_id/model are strings; the rest numeric.
TELEMETRY_NUM_FIELDS = ["wall_seconds", "model_calls", "attempts",
                        "n_input_tokens", "n_output_tokens", "n_cache_tokens"]

# Secret shapes — provider keys + generic bearer/long tokens. We never print the match, only where it is.
SECRET_RE = re.compile(
    r"(sk-ant-[A-Za-z0-9_\-]{8,}|sk-[A-Za-z0-9]{20,}|xai-[A-Za-z0-9]{20,}|"
    r"sk-or-[A-Za-z0-9_\-]{8,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{20,}|"
    r"Bearer\s+[A-Za-z0-9._\-]{20,})")
# `NAME_API_KEY = "value"` / `NAME_TOKEN: value` with a real-looking value (not a placeholder).
ENVKEY_RE = re.compile(r"(?i)\b([A-Z0-9_]*(?:API_KEY|SECRET|TOKEN|ACCESS_KEY))\b\s*[:=]\s*['\"]?([^\s'\"]{16,})")
PLACEHOLDER = re.compile(r"(?i)^(x{3,}|\.{3}|<[^>]+>|your[_-]?key|changeme|placeholder|\$\{?[A-Z_]+\}?|example|none|null|redacted|\*+)")

# files worth scanning for secrets / reading as text
TEXT_EXT = {".py", ".js", ".ts", ".tsx", ".jsx", ".sh", ".bash", ".zsh", ".json", ".jsonl", ".toml",
            ".yaml", ".yml", ".ini", ".cfg", ".env", ".txt", ".md", ".csv", ".tsv", ".html", ".xml",
            ".java", ".rb", ".go", ".rs", ".c", ".h", ".cpp", ".hpp", ".cc"}
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv", ".mypy_cache", ".pytest_cache"}
CODE_EXT = {".py", ".js", ".ts", ".tsx", ".jsx", ".sh", ".rb", ".go", ".rs", ".java"}
README_RE = re.compile(r"(?i)readme")
WRITEUP_RE = re.compile(r"(?i)(writeup|write-up|variation|approach|strategy|design|report)")
MAX_SCAN_BYTES = 2_000_000  # don't read huge blobs for secrets


def _iter_files(root):
    for dp, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        for f in files:
            yield os.path.join(dp, f)


def _task_packages(root):
    """Every dir that directly contains a task.toml (a package). Nested dupes under ready_ship/package dropped."""
    hits = []
    for dp, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
        if "task.toml" in files:
            if not any(seg.lower() in {"ready_ship", "ready_shipped", "package"} for seg in dp.split(os.sep)):
                hits.append(dp)
    return sorted(hits)


def _read_text(fp):
    try:
        if os.path.getsize(fp) > MAX_SCAN_BYTES:
            return None
        with open(fp, encoding="utf-8", errors="replace") as fh:
            return fh.read()
    except Exception:
        return None


def _scan_secrets(root):
    """Return list of 'relpath:reason' for files that look like they contain a secret. Never returns the secret."""
    hits = []
    for fp in _iter_files(root):
        ext = os.path.splitext(fp)[1].lower()
        if ext not in TEXT_EXT and os.path.basename(fp) != ".env":
            continue
        txt = _read_text(fp)
        if not txt:
            continue
        rel = os.path.relpath(fp, root)
        if SECRET_RE.search(txt):
            hits.append(f"{rel}: contains an API-key/token-shaped string")
            continue
        for m in ENVKEY_RE.finditer(txt):
            val = m.group(2)
            if not PLACEHOLDER.match(val):
                hits.append(f"{rel}: looks like a real value assigned to {m.group(1)}")
                break
    return hits


def _check_telemetry(root, pkg_iids):
    """Validate pipeline_run.json. Returns (errs, warns)."""
    errs, warns = [], []
    cands = [fp for fp in _iter_files(root) if os.path.basename(fp) == "pipeline_run.json"]
    if not cands:
        errs.append("pipeline_run.json not found (SUBMISSION.md §3b — required for efficiency measurement)")
        return errs, warns
    if len(cands) > 1:
        warns.append(f"multiple pipeline_run.json found; using {os.path.relpath(cands[0], root)}")
    fp = cands[0]
    try:
        data = json.load(open(fp))
    except Exception as e:
        errs.append(f"pipeline_run.json is not valid JSON: {e}")
        return errs, warns
    tasks = data.get("tasks") if isinstance(data, dict) else None
    if not isinstance(tasks, list) or not tasks:
        errs.append("pipeline_run.json must be an object with a non-empty 'tasks' array")
        return errs, warns
    tele_iids = set()
    for i, row in enumerate(tasks):
        if not isinstance(row, dict):
            errs.append(f"pipeline_run.json tasks[{i}] is not an object"); continue
        iid = row.get("instance_id")
        if not iid or not isinstance(iid, str):
            errs.append(f"pipeline_run.json tasks[{i}] missing a string 'instance_id'")
        else:
            tele_iids.add(iid)
        for fld in TELEMETRY_NUM_FIELDS:
            v = row.get(fld)
            if v is None:
                warns.append(f"telemetry[{iid or i}] missing '{fld}' (efficiency for this task can't be measured)")
            elif isinstance(v, bool) or not isinstance(v, (int, float)):
                warns.append(f"telemetry[{iid or i}].{fld} is not numeric ({v!r})")
    # cross-check telemetry rows vs shipped packages
    if pkg_iids:
        no_row = sorted(pkg_iids - tele_iids)
        no_pkg = sorted(tele_iids - pkg_iids)
        if no_row:
            warns.append(f"{len(no_row)} shipped package(s) have no telemetry row: {no_row[:5]}"
                         f"{'…' if len(no_row) > 5 else ''}")
        if no_pkg:
            warns.append(f"{len(no_pkg)} telemetry row(s) reference no shipped package: {no_pkg[:5]}"
                         f"{'…' if len(no_pkg) > 5 else ''}")
    return errs, warns


def _safe_extract(zpath, dest):
    """Extract a zip, refusing path-traversal (zip-slip) members."""
    with zipfile.ZipFile(zpath) as z:
        for m in z.namelist():
            tgt = os.path.realpath(os.path.join(dest, m))
            if not (tgt == os.path.realpath(dest) or tgt.startswith(os.path.realpath(dest) + os.sep)):
                raise ValueError(f"unsafe path in zip: {m}")
        z.extractall(dest)


def validate(root, zip_name=None):
    errs, warns = [], []

    # 1. ZIP name
    if zip_name is not None and not re.fullmatch(r".+_Track1\.zip", zip_name):
        warns.append(f"ZIP is '{zip_name}', expected 'TeamName_Track1.zip' (SUBMISSION.md)")

    # 2. secrets
    for h in _scan_secrets(root):
        errs.append(f"possible secret — {h}  (remove all API keys/tokens before submitting)")

    # 3. task packages + per-package structure
    pkgs = _task_packages(root)
    pkg_iids = {os.path.basename(p) for p in pkgs}
    if not pkgs:
        errs.append("no task packages found (a folder with task.toml) — nothing to grade")
    else:
        if len(pkgs) < 5:
            warns.append(f"only {len(pkgs)} task package(s) found; the brief asks for 5 distinct tasks")
        bad = 0
        for p in pkgs:
            pe, _pw = check_structure.check(p)
            if pe:
                bad += 1
                errs.append(f"package '{os.path.basename(p)}' fails check_structure ({len(pe)} error(s)) — "
                            f"run: harness/check_structure.py {os.path.relpath(p, root)}")
        if not bad:
            print(f"  ✓ {len(pkgs)} task package(s) pass check_structure")

    # 4. telemetry
    te, tw = _check_telemetry(root, pkg_iids)
    errs += te; warns += tw
    if not te:
        print("  ✓ pipeline_run.json present and well-formed")

    # 5. pipeline code + README
    files = list(_iter_files(root))
    readmes = [f for f in files if README_RE.search(os.path.basename(f))]
    # pipeline code = a code file that is NOT inside a task package's tests/solution/environment
    pkg_prefixes = tuple(os.path.join(p, "") for p in pkgs)
    code = [f for f in files if os.path.splitext(f)[1].lower() in CODE_EXT and not f.startswith(pkg_prefixes)]
    if not readmes:
        warns.append("no README found — SUBMISSION.md §1 requires pipeline run instructions")
    if not code:
        warns.append("no pipeline source found outside the task packages — did you include your pipeline code?")

    # 6. variation writeup
    writeup = [f for f in files if WRITEUP_RE.search(os.path.basename(f))]
    if not writeup:
        # a README may double as the writeup; only warn if neither clearly present
        if not readmes:
            warns.append("no variation writeup found (SUBMISSION.md §4 — 1–2 pages on your variation strategy)")
        else:
            warns.append("no file named like a writeup found; make sure a README/writeup covers the "
                         "variation strategy (SUBMISSION.md §4)")

    return errs, warns


def main(argv):
    if len(argv) != 2:
        print("usage: validate_submission.py <submission_dir | TeamName_Track1.zip>", file=sys.stderr)
        return 2
    target = argv[1]
    tmp = None
    zip_name = None
    try:
        if os.path.isdir(target):
            root = target
        elif zipfile.is_zipfile(target):
            zip_name = os.path.basename(target)
            tmp = tempfile.mkdtemp(prefix="submission_")
            try:
                _safe_extract(target, tmp)
            except Exception as e:
                print(f"✗ cannot extract {zip_name}: {e}", file=sys.stderr); return 1
            # if the zip contains a single top dir, descend into it
            entries = [os.path.join(tmp, e) for e in os.listdir(tmp)]
            root = entries[0] if len(entries) == 1 and os.path.isdir(entries[0]) else tmp
        else:
            print(f"✗ {target} is neither a directory nor a zip", file=sys.stderr); return 2

        print(f"# submission check: {target}")
        errs, warns = validate(root, zip_name)
        for e in errs:
            print(f"  ERROR  {e}")
        for w in warns:
            print(f"  warn   {w}")
        print()
        if errs:
            print(f"✗ SUBMISSION INCOMPLETE — {len(errs)} error(s), {len(warns)} warning(s). Fix the ERRORs and re-run.")
            return 1
        print(f"✓ SUBMISSION COMPLETE — 0 errors"
              + (f", {len(warns)} warning(s) to review." if warns else ". Ready to send."))
        return 0
    finally:
        if tmp:
            import shutil
            shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
