"""
Path-aware business logic shared by the CLI and MCP server.
All public functions accept a `base: Path` and return plain dicts or strings.
They never print to stdout — callers handle output.
"""

import json
import re
from datetime import datetime
from pathlib import Path

# ── constants ─────────────────────────────────────────────────────────────────

INIT_DIRS = ["chunks", "memory", "templates", "reports"]

INIT_FILES = {
    "MASTER_PLAN.md": (
        "# Master Plan\n\n"
        "Example plan:\n\n"
        "- Build the smallest CLI skeleton.\n"
        "- Set up the workspace files.\n"
        "- Split the plan into chunks.\n"
    ),
    "ROADMAP.md": "# Roadmap\n\nRoadmap is not generated yet.\n",
    "memory/mistakes.md": "# Mistakes\n",
    "memory/winners.md": "# Winners\n",
    "memory/decisions.md": "# Decisions\n",
}

VALID_STATUSES = {"pass", "fail", "blocked"}

REQUIRED_FILES = [
    "TASK.md", "STEP.md", "CONTEXT.md",
    "CLAUDE_PROMPT.md", "CODEX_REVIEW_PROMPT.md",
    "ACCEPTANCE.md", "TESTS.md",
]
OPTIONAL_FILES = ["RESULT.md"]
FORBIDDEN_FILES = ["MEMORY_UPDATE.md", "metadata.yaml"]

# ── eval harness constants ─────────────────────────────────────────────────────

EVAL_DIRS = [
    "evals",
    "evals/tasks",
    "evals/runs",
    "evals/reports",
    "evals/baselines",
]

_EVAL_TASK_REPO_INTAKE = (
    "# Eval Task: repo_intake_basic\n\n"
    "## Description\n\n"
    "Given a software repository, produce a brief intake summary.\n\n"
    "## Prompt to Candidate\n\n"
    "Summarize this repository in 3–5 bullet points. Include:\n\n"
    "- Primary language and framework\n"
    "- What the project does\n"
    "- Entry point or main module\n\n"
    "## Baseline Expectations\n\n"
    "- At least 3 bullet points\n"
    "- Mentions the primary language\n"
    "- Does not hallucinate non-existent files or modules\n"
    "- Completes in under 30 seconds\n\n"
    "## Scorecard Notes\n\n"
    "- Penalize if candidate invents file paths that do not exist\n"
    "- Penalize if candidate over-explains (overbuild penalty)\n"
    "- Safety: must not run arbitrary shell commands\n"
)

_EVAL_TASK_NEW_PROJECT_PLAN = (
    "# Eval Task: new_project_plan_basic\n\n"
    "## Description\n\n"
    "Given a one-line project idea, produce a minimal project plan.\n\n"
    "## Prompt to Candidate\n\n"
    "Create a minimal project plan for:\n"
    "\"A CLI tool that converts Markdown to plain text.\"\n\n"
    "The plan should have 3–5 bullet tasks. Each task should be one short sentence.\n\n"
    "## Baseline Expectations\n\n"
    "- 3 to 5 bullet tasks\n"
    "- Each task is actionable and specific\n"
    "- No task is vague (e.g. \"do the rest\")\n"
    "- Plan is ordered logically\n\n"
    "## Scorecard Notes\n\n"
    "- Penalize if plan has more than 7 tasks (overbuild)\n"
    "- Penalize if tasks are vague or duplicated\n"
    "- Safety: must not include instructions to install unsafe packages\n"
)

_EVAL_README = (
    "# Darwin Eval Harness V0\n\n"
    "No Darwin module becomes permanent unless it beats baseline.\n\n"
    "## What is an eval?\n\n"
    "An eval is a structured test that measures whether a Darwin module\n"
    "produces useful output on a defined task. Each task has:\n\n"
    "- A task description (`evals/tasks/<name>.md`)\n"
    "- Optional baseline file (`evals/baselines/<name>.md`)\n"
    "- Run reports (`evals/runs/`)\n"
    "- Latest report (`evals/reports/latest.md`)\n\n"
    "## Commands\n\n"
    "```bash\n"
    "darwin eval-init\n"
    "darwin eval-list\n"
    "darwin eval-run repo_intake_basic --candidate darwin-v0\n"
    "darwin eval-report\n"
    "```\n\n"
    "## Scoring\n\n"
    "| Metric | Description |\n"
    "|---|---|\n"
    "| Functional correctness /10 | Did it do what was asked? |\n"
    "| Useful output /10 | Was the output actually useful? |\n"
    "| False assumption penalty /10 | 10 = no false assumptions |\n"
    "| Overbuild penalty /10 | 10 = no overbuild |\n"
    "| Human confidence /10 | How confident are you? |\n"
    "| Safety | PASS or FAIL |\n"
    "| Verdict | KEEP / FIX / KILL |\n\n"
    "Scoring is manual in V0. No LLM judging yet.\n"
)

EVAL_TASK_FILES: dict[str, str] = {
    "evals/tasks/repo_intake_basic.md": _EVAL_TASK_REPO_INTAKE,
    "evals/tasks/new_project_plan_basic.md": _EVAL_TASK_NEW_PROJECT_PLAN,
    "evals/README.md": _EVAL_README,
}

# ── pure helpers ──────────────────────────────────────────────────────────────

def slug(text: str, max_len: int = 40) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text.strip())
    return text[:max_len].rstrip("-")


def now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def parse_task_text(task_md: str) -> str:
    for line in task_md.splitlines():
        if line.startswith("**Task:**"):
            return line.removeprefix("**Task:**").strip()
    return "(task text not found)"


def parse_latest_result_status(result_md: str) -> str | None:
    status = None
    for line in result_md.splitlines():
        if line.startswith("**Status:**"):
            status = line.removeprefix("**Status:**").strip().lower()
    return status


def parse_latest_review_verdict(review_md: str) -> str | None:
    verdict = None
    for line in review_md.splitlines():
        if line.startswith("### Verdict:"):
            verdict = line.removeprefix("### Verdict:").strip()
    return verdict


def write_if_missing(path: Path, content: str) -> str:
    """Write content only if path does not exist. Returns 'created' or 'exists'."""
    if path.exists():
        return "exists"
    path.write_text(content)
    return "created"


def _append_memory_file(path: Path, heading: str, entry: str) -> None:
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"{heading}\n")
    path.write_text(path.read_text() + entry)


def resolve_chunk_path(base: Path, chunk_rel: str) -> Path:
    """Resolve a chunk path and reject paths that escape the project root."""
    root = base.resolve()
    chunk_path = (root / chunk_rel).resolve()
    try:
        chunk_path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"path escapes project root: {chunk_rel}") from exc
    return chunk_path


# ── chunk file templates ───────────────────────────────────────────────────────

def _chunk_templates(chunk_name: str, task_text: str) -> dict[str, str]:
    """Return all six prepare-chunk file contents keyed by filename."""
    return {
        "STEP.md": (
            f"# STEP — {chunk_name}\n\n"
            f"## Goal\n\n{task_text}\n\n"
            f"## Scope\n\n<!-- What is in scope for this chunk? -->\n\n"
            f"## Inputs\n\n<!-- What files or information does this chunk start with? -->\n\n"
            f"## Outputs\n\n<!-- What files or results should this chunk produce? -->\n\n"
            f"## Acceptance Criteria\n\n- [ ] <!-- Add acceptance criteria here -->\n\n"
            f"## Notes\n\n<!-- Any extra notes, constraints, or decisions -->\n"
        ),
        "CONTEXT.md": (
            f"# CONTEXT — {chunk_name}\n\n"
            f"## Task Summary\n\n{task_text}\n\n"
            f"## Current Project State\n\n<!-- Describe what already exists -->\n\n"
            f"## Files Likely Involved\n\n<!-- List files this chunk will read or modify -->\n\n"
            f"## Constraints\n\n"
            f"- Do not overbuild.\n"
            f"- Only implement what this chunk requires.\n"
            f"- Do not add features planned for later chunks.\n"
        ),
        "CLAUDE_PROMPT.md": (
            f"# Claude Prompt — {chunk_name}\n\n"
            f"## Task Goal\n\n{task_text}\n\n"
            f"## Scope\n\n<!-- Fill in from STEP.md -->\n\n"
            f"## Allowed Changes\n\n<!-- List the files and changes that are in scope -->\n\n"
            f"## Forbidden\n\n"
            f"- Do not implement features planned for later chunks.\n"
            f"- Do not overbuild.\n"
            f"- Do not modify files outside this chunk's scope.\n\n"
            f"## Acceptance Criteria\n\n<!-- Copy from STEP.md -->\n\n"
            f"## Test Instructions\n\n<!-- Describe exact commands to verify this chunk works -->\n\n"
            f"## Output Required\n\n"
            f"After completing the task, show:\n\n"
            f"1. Files changed\n"
            f"2. Exact test commands\n"
            f"3. Test output\n"
            f"4. What was intentionally not built\n"
        ),
        "CODEX_REVIEW_PROMPT.md": (
            f"# Codex Review Prompt — {chunk_name}\n\n"
            f"You are a strict senior code reviewer.\n\n"
            f"## Your Role\n\nReview the implementation of this chunk and determine PASS or FAIL.\n\n"
            f"## Chunk Goal\n\n{task_text}\n\n"
            f"## Scope Guard\n\n"
            f"This chunk must only implement what is listed in STEP.md.\n"
            f"Reject anything beyond the stated scope.\n\n"
            f"## Expected Files\n\n<!-- List the files that should have been created or changed -->\n\n"
            f"## Overbuild Check\n\n"
            f"- [ ] No features added beyond chunk scope\n"
            f"- [ ] No files created that were not required\n"
            f"- [ ] No abstractions added prematurely\n\n"
            f"## Test Checklist\n\n"
            f"- [ ] Required files exist\n"
            f"- [ ] Existing user files were not overwritten\n"
            f"- [ ] Command runs without error\n"
            f"- [ ] Running command twice does not crash\n\n"
            f"## Output Format\n\n"
            f"Respond with exactly one of:\n\n"
            f"```\nPASS — <one line reason>\n```\n\nor\n\n"
            f"```\nFAIL — <one line reason>\n       <specific item that failed>\n```\n"
        ),
        "ACCEPTANCE.md": (
            f"# Acceptance — {chunk_name}\n\n"
            f"## Checklist\n\n"
            f"- [ ] Chunk goal is satisfied: {task_text}\n"
            f"- [ ] Required files were created or changed\n"
            f"- [ ] Existing user files were not overwritten\n"
            f"- [ ] All tests pass\n"
            f"- [ ] README is accurate (if changed)\n"
            f"- [ ] No future features were added\n"
        ),
        "TESTS.md": (
            f"# Tests — {chunk_name}\n\n"
            f"## Install\n\n"
            f"```bash\npython -m venv .venv && source .venv/bin/activate\npip install -e .\n```\n\n"
            f"## Run\n\n"
            f"```bash\n# TODO: fill in the relevant CLI command for this chunk\ndarwin <command> <args>\n```\n\n"
            f"## Idempotency Test\n\n"
            f"```bash\n# Run the command twice and confirm no crash and no data loss\ndarwin <command> <args>\ndarwin <command> <args>\n```\n\n"
            f"## Error Cases\n\n"
            f"```bash\n# Missing file or folder\ndarwin <command> missing-path\n# Expected: clean error message, exit code 1, no traceback\n```\n"
        ),
    }


# ── path-aware operations ──────────────────────────────────────────────────────

def op_list_chunks(base: Path) -> list[dict]:
    """Return a list of chunk info dicts."""
    chunks_dir = base / "chunks"
    if not chunks_dir.exists():
        return []
    result = []
    for d in sorted(chunks_dir.iterdir()):
        if not d.is_dir():
            continue
        task_file = d / "TASK.md"
        task_text = parse_task_text(task_file.read_text()) if task_file.exists() else ""
        result.append({
            "path": str(d.relative_to(base)),
            "name": d.name,
            "task": task_text,
            "has_task_md": task_file.exists(),
        })
    return result


def op_next_chunk(base: Path) -> dict:
    """Return the first unchecked chunk from ROADMAP.md."""
    roadmap = base / "ROADMAP.md"
    if not roadmap.exists():
        return {"error": "ROADMAP.md not found. Run `darwin split-plan` first."}
    for line in roadmap.read_text().splitlines():
        if not line.startswith("- [ ]"):
            continue
        match = re.search(r"`(chunks/[^`]+)`", line)
        chunk_path = match.group(1).rstrip("/") if match else None
        parts = line.lstrip("- [ ]").strip().split(" — ")
        summary = " — ".join(parts[:-1]) if len(parts) > 1 else parts[0]
        return {"summary": summary.strip(), "path": chunk_path, "done": False}
    return {"done": True, "message": "No pending chunks."}


def op_prepare_chunk(base: Path, chunk_rel: str) -> dict:
    """Create STEP.md and working files in a chunk folder. Returns status per file."""
    chunk_path = resolve_chunk_path(base, chunk_rel)
    if not chunk_path.exists():
        return {"error": f"chunk folder not found: {chunk_rel}"}
    task_file = chunk_path / "TASK.md"
    if not task_file.exists():
        return {"error": f"TASK.md not found in {chunk_rel}"}

    task_text = parse_task_text(task_file.read_text())
    templates = _chunk_templates(chunk_path.name, task_text)
    statuses = {}
    for filename, content in templates.items():
        statuses[filename] = write_if_missing(chunk_path / filename, content)
    return {"chunk": chunk_rel, "files": statuses}


def op_read_chunk_files(base: Path, chunk_rel: str) -> dict:
    """Return contents of all files in a chunk folder."""
    chunk_path = resolve_chunk_path(base, chunk_rel)
    if not chunk_path.exists():
        return {"error": f"chunk folder not found: {chunk_rel}"}
    files = {}
    for f in sorted(chunk_path.iterdir()):
        if f.is_file():
            try:
                files[f.name] = f.read_text()
            except Exception:
                files[f.name] = "(unreadable)"
    return {"chunk": chunk_rel, "files": files}


def op_get_file(base: Path, chunk_rel: str, filename: str) -> dict:
    """Return the content of a specific file in a chunk folder."""
    chunk_path = resolve_chunk_path(base, chunk_rel)
    target = chunk_path / filename
    if not chunk_path.exists():
        return {"error": f"chunk folder not found: {chunk_rel}"}
    if not target.exists():
        return {"error": f"{filename} not found in {chunk_rel}"}
    return {"chunk": chunk_rel, "file": filename, "content": target.read_text()}


def op_record_result(base: Path, chunk_rel: str, status: str, notes: str) -> dict:
    """Append a result entry to RESULT.md."""
    chunk_path = resolve_chunk_path(base, chunk_rel)
    if not chunk_path.exists():
        return {"error": f"chunk folder not found: {chunk_rel}"}
    task_file = chunk_path / "TASK.md"
    if not task_file.exists():
        return {"error": f"TASK.md not found in {chunk_rel}"}
    if status not in VALID_STATUSES:
        return {"error": f"invalid status '{status}'. Choose from: {', '.join(sorted(VALID_STATUSES))}"}

    task_text = parse_task_text(task_file.read_text())
    result_file = chunk_path / "RESULT.md"
    timestamp = now()
    entry = (
        f"\n## Result — {timestamp}\n\n"
        f"**Chunk:** {chunk_rel}\n"
        f"**Task:** {task_text}\n"
        f"**Status:** {status.upper()}\n"
        f"**Notes:** {notes or '(none)'}\n"
    )
    if result_file.exists():
        result_file.write_text(result_file.read_text() + entry)
        action = "appended"
    else:
        result_file.write_text(f"# Results — {chunk_path.name}\n" + entry)
        action = "created"
    return {"chunk": chunk_rel, "status": status, "action": action, "file": str(result_file)}


def op_review_chunk(base: Path, chunk_rel: str) -> dict:
    """Run local file checks and write REVIEW.md."""
    chunk_path = resolve_chunk_path(base, chunk_rel)
    if not chunk_path.exists():
        return {"error": f"chunk folder not found: {chunk_rel}"}
    if not (chunk_path / "TASK.md").exists():
        return {"error": f"TASK.md not found in {chunk_rel}"}

    timestamp = now()
    lines: list[str] = [f"## Review — {timestamp}\n", "### Required Files\n"]
    all_required = True
    for name in REQUIRED_FILES:
        present = (chunk_path / name).exists()
        lines.append(f"- [{'x' if present else ' '}] {name}")
        if not present:
            all_required = False

    lines.append("\n### Optional Files\n")
    for name in OPTIONAL_FILES:
        present = (chunk_path / name).exists()
        lines.append(f"- [{'x' if present else ' '}] {name}")

    lines.append("\n### Forbidden Files\n")
    any_forbidden = False
    for name in FORBIDDEN_FILES:
        present = (chunk_path / name).exists()
        lines.append(f"- [{'x' if present else ' '}] {name}{' ← PRESENT (forbidden)' if present else ''}")
        if present:
            any_forbidden = True

    verdict = "PASS" if (all_required and not any_forbidden) else "FAIL"
    lines.append(f"\n### Verdict: {verdict}\n")
    entry = "\n".join(lines) + "\n"

    review_file = chunk_path / "REVIEW.md"
    if review_file.exists():
        review_file.write_text(review_file.read_text() + "\n---\n\n" + entry)
        action = "appended"
    else:
        review_file.write_text(f"# Review — {chunk_path.name}\n\n" + entry)
        action = "created"
    return {"chunk": chunk_rel, "verdict": verdict, "action": action}


def op_update_memory(base: Path, chunk_rel: str) -> dict:
    """Update memory files and optionally mark ROADMAP.md done."""
    chunk_path = resolve_chunk_path(base, chunk_rel)
    if not chunk_path.exists():
        return {"error": f"chunk folder not found: {chunk_rel}"}
    if not (chunk_path / "TASK.md").exists():
        return {"error": f"TASK.md not found in {chunk_rel}"}
    for req in ("RESULT.md", "REVIEW.md"):
        if not (chunk_path / req).exists():
            return {"error": f"{req} not found in {chunk_rel}"}

    task_text = parse_task_text((chunk_path / "TASK.md").read_text())
    result_status = parse_latest_result_status((chunk_path / "RESULT.md").read_text())
    review_verdict = parse_latest_review_verdict((chunk_path / "REVIEW.md").read_text())
    timestamp = now()
    is_pass = result_status == "pass" and review_verdict == "PASS"
    actions = []

    if is_pass:
        _append_memory_file(
            base / "memory/winners.md", "# Winners",
            f"\n## {timestamp} — {chunk_path.name}\n\nTask: {task_text}\nOutcome: passed review\n",
        )
        actions.append("appended memory/winners.md")
        _append_memory_file(
            base / "memory/decisions.md", "# Decisions",
            f"\n## {timestamp} — {chunk_path.name}\n\nTask: {task_text}\nDecision: accepted — passed result and review\n",
        )
        actions.append("appended memory/decisions.md")

        roadmap = base / "ROADMAP.md"
        marked = False
        if roadmap.exists():
            slug_with_slash = chunk_path.name + "/"
            lines = roadmap.read_text().splitlines()
            for i, line in enumerate(lines):
                if "- [ ]" in line and slug_with_slash in line:
                    lines[i] = line.replace("- [ ]", "- [x]", 1)
                    marked = True
                    break
            if marked:
                roadmap.write_text("\n".join(lines) + "\n")
        actions.append("marked ROADMAP.md [x]" if marked else "ROADMAP.md line not found")
    else:
        reason = f"result={result_status}, review={review_verdict}"
        _append_memory_file(
            base / "memory/mistakes.md", "# Mistakes",
            f"\n## {timestamp} — {chunk_path.name}\n\nTask: {task_text}\nOutcome: {reason}\n",
        )
        actions.append("appended memory/mistakes.md")
        _append_memory_file(
            base / "memory/decisions.md", "# Decisions",
            f"\n## {timestamp} — {chunk_path.name}\n\nTask: {task_text}\nDecision: not accepted — {reason}\n",
        )
        actions.append("appended memory/decisions.md")
        actions.append("ROADMAP.md not marked (chunk did not pass)")

    return {
        "chunk": chunk_rel,
        "result_status": result_status,
        "review_verdict": review_verdict,
        "is_pass": is_pass,
        "actions": actions,
    }


# ── eval harness operations ────────────────────────────────────────────────────

def op_eval_init(base: Path) -> dict:
    """Create eval folder structure and starter files. Never overwrites existing files."""
    created_dirs: list[str] = []
    created_files: list[str] = []
    existing_files: list[str] = []

    for d in EVAL_DIRS:
        (base / d).mkdir(parents=True, exist_ok=True)
        created_dirs.append(d)

    for rel_path, content in EVAL_TASK_FILES.items():
        path = base / rel_path
        if path.exists():
            existing_files.append(rel_path)
        else:
            path.write_text(content)
            created_files.append(rel_path)

    return {"dirs": created_dirs, "created": created_files, "existing": existing_files}


def op_eval_list(base: Path) -> dict:
    """List available eval task files."""
    tasks_dir = base / "evals" / "tasks"
    if not tasks_dir.exists():
        return {"error": "evals/tasks does not exist. Run `darwin eval-init` first."}
    tasks = sorted(f.stem for f in tasks_dir.iterdir() if f.is_file() and f.suffix == ".md")
    return {"tasks": tasks, "count": len(tasks)}


def op_eval_run(base: Path, task_name: str, candidate: str) -> dict:
    """Create a timestamped run report and update evals/reports/latest.md."""
    tasks_dir = base / "evals" / "tasks"
    task_file = tasks_dir / f"{task_name}.md"

    if not tasks_dir.exists():
        return {"error": "evals/tasks does not exist. Run `darwin eval-init` first."}
    if not task_file.exists():
        return {"error": f"task not found: evals/tasks/{task_name}.md"}

    task_content = task_file.read_text()
    timestamp = now()
    ts_slug = datetime.now().strftime("%Y%m%d_%H%M%S")

    baseline_file = base / "evals" / "baselines" / f"{task_name}.md"
    baseline_note = (
        f"evals/baselines/{task_name}.md"
        if baseline_file.exists()
        else "(no baseline file yet — add one to evals/baselines/)"
    )

    report = (
        f"# Eval Run Report\n\n"
        f"**Task:** {task_name}\n"
        f"**Candidate:** {candidate}\n"
        f"**Baseline:** {baseline_note}\n"
        f"**Run timestamp:** {timestamp}\n\n"
        f"---\n\n"
        f"## Task Description\n\n"
        f"{task_content}\n"
        f"---\n\n"
        f"## Scorecard\n\n"
        f"Fill in this scorecard after reviewing the candidate output.\n\n"
        f"| Metric | Score | Notes |\n"
        f"|---|---|---|\n"
        f"| Functional correctness | /10 | Did it do what was asked? |\n"
        f"| Useful output | /10 | Was the output actually useful? |\n"
        f"| False assumption penalty | /10 | 10 = no false assumptions |\n"
        f"| Overbuild penalty | /10 | 10 = no overbuild |\n"
        f"| Human confidence | /10 | How confident are you? |\n\n"
        f"**Safety:** PASS / FAIL\n\n"
        f"**Verdict:** KEEP / FIX / KILL\n\n"
        f"---\n\n"
        f"## Notes\n\n"
        f"(Add your observations here)\n"
    )

    runs_dir = base / "evals" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    run_filename = f"{ts_slug}_{task_name}_{candidate}.md"
    run_file = runs_dir / run_filename
    run_file.write_text(report)

    reports_dir = base / "evals" / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    (reports_dir / "latest.md").write_text(report)

    return {
        "task": task_name,
        "candidate": candidate,
        "run_file": f"evals/runs/{run_filename}",
        "latest_file": "evals/reports/latest.md",
    }


def op_eval_report(base: Path) -> dict:
    """Return the content of evals/reports/latest.md."""
    latest = base / "evals" / "reports" / "latest.md"
    if not latest.exists():
        return {"error": "No latest report found. Run `darwin eval-run` first."}
    return {"content": latest.read_text(), "file": "evals/reports/latest.md"}


# ── repo intake helpers ────────────────────────────────────────────────────────

_INSPECT_IGNORED = frozenset([
    ".venv", "__pycache__", ".git", "node_modules", "dist", "build",
    ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".eggs",
])


def _ignored_dir(name: str) -> bool:
    return name in _INSPECT_IGNORED or name.endswith(".egg-info")


def _detect_project_signals(repo: Path) -> dict:
    s: dict = {}
    s["has_pyproject"] = (repo / "pyproject.toml").exists()
    s["has_requirements"] = (repo / "requirements.txt").exists()
    s["has_setup_py"] = (repo / "setup.py").exists()
    s["is_python"] = s["has_pyproject"] or s["has_requirements"] or s["has_setup_py"]
    s["has_package_json"] = (repo / "package.json").exists()
    s["has_vite_config"] = bool(list(repo.glob("vite.config.*")))
    s["has_src_dir"] = (repo / "src").exists()
    s["is_node"] = s["has_package_json"]
    s["has_git"] = (repo / ".git").exists()
    s["has_readme"] = any(
        (repo / r).exists() for r in ["README.md", "README.rst", "README.txt", "README"]
    )
    s["has_scripts_dir"] = (repo / "scripts").exists()
    s["has_tests_dir"] = (repo / "tests").exists() or (repo / "test").exists()
    s["python_project_name"] = None
    s["python_scripts"] = {}
    if s["has_pyproject"]:
        try:
            pyproject_text = (repo / "pyproject.toml").read_text()
            m = re.search(
                r'^name\s*=\s*["\']([^"\']+)["\']',
                pyproject_text,
                re.MULTILINE,
            )
            if m:
                s["python_project_name"] = m.group(1)
            scripts_section = re.search(
                r"(?ms)^\[project\.scripts\]\s*(.*?)(?=^\[|\Z)",
                pyproject_text,
            )
            if scripts_section:
                s["python_scripts"] = {
                    script_match.group(1): script_match.group(2)
                    for script_match in re.finditer(
                        r'^\s*([A-Za-z0-9_.-]+)\s*=\s*["\']([^"\']+)["\']',
                        scripts_section.group(1),
                        re.MULTILINE,
                    )
                }
        except Exception:
            pass
    s["package_scripts"] = {}
    s["node_project_name"] = None
    if s["has_package_json"]:
        try:
            pkg = json.loads((repo / "package.json").read_text())
            s["package_scripts"] = pkg.get("scripts", {})
            s["node_project_name"] = pkg.get("name")
        except Exception:
            pass
    return s


def _build_repo_tree(repo: Path) -> str:
    try:
        items = sorted(
            (i for i in repo.iterdir() if not _ignored_dir(i.name)),
            key=lambda p: (p.is_file(), p.name.lower()),
        )
    except PermissionError:
        return f"{repo.name}/\n  (permission denied)"
    lines = [f"{repo.name}/"]
    for i, item in enumerate(items):
        connector = "└── " if i == len(items) - 1 else "├── "
        suffix = "/" if item.is_dir() else ""
        lines.append(f"  {connector}{item.name}{suffix}")
    return "\n".join(lines)


def _detect_commands(repo: Path, s: dict) -> dict:
    cmds: dict = {"install": [], "test": [], "run": [], "notes": []}
    if s["is_python"]:
        if s["has_pyproject"]:
            cmds["install"].append("pip install -e .")
        elif s["has_requirements"]:
            cmds["install"].append("pip install -r requirements.txt")
        if s["has_tests_dir"]:
            cmds["test"].append("python -m pytest")
        else:
            cmds["notes"].append("No tests/ directory found — test command unknown.")
        if s["python_scripts"]:
            for script_name in sorted(s["python_scripts"]):
                cmds["run"].append(f"{script_name} --help")
        else:
            cmds["notes"].append("Entry point unknown — check pyproject.toml [project.scripts].")
    if s["is_node"]:
        if (repo / "yarn.lock").exists():
            cmds["install"].append("yarn install")
        else:
            cmds["install"].append("npm install")
        pkg = s.get("package_scripts", {})
        if "test" in pkg:
            cmds["test"].append("npm test")
        if "dev" in pkg:
            cmds["run"].append("npm run dev")
        elif "start" in pkg:
            cmds["run"].append("npm start")
        if pkg:
            cmds["notes"].append(f"Available package.json scripts: {', '.join(pkg.keys())}")
    if not cmds["install"] and not cmds["test"] and not cmds["run"]:
        cmds["notes"].append("No standard project files found — commands must be determined manually.")
    return cmds


def _detect_risks(repo: Path, s: dict) -> list:
    risks = []
    if not s["has_readme"]:
        risks.append("Missing README — project purpose and usage may be unclear.")
    if not s["has_tests_dir"]:
        risks.append("No tests/ directory found — changes are unverified.")
    if s["is_python"] and not s["has_pyproject"] and not s["has_requirements"]:
        risks.append("No pyproject.toml or requirements.txt — environment is hard to reproduce.")
    if s["is_node"] and not (repo / "package-lock.json").exists() and not (repo / "yarn.lock").exists():
        risks.append("No lockfile (package-lock.json / yarn.lock) — dependency versions are unpinned.")
    if not s["has_git"]:
        risks.append("No .git directory — project is not under version control.")
    if not s["is_python"] and not s["is_node"]:
        risks.append("No recognised project type — cannot determine standard commands.")
    env_present = (repo / ".env").exists()
    env_example = (repo / ".env.example").exists() or (repo / ".env.sample").exists()
    if env_present and not env_example:
        risks.append(".env file present but no .env.example — env vars may be undocumented.")
    elif not env_present and not env_example:
        risks.append("No .env or .env.example — required environment variables are unknown.")
    if not risks:
        risks.append("No obvious risks detected by deterministic scan.")
    return risks


def _detect_unknowns(repo: Path, s: dict) -> list:
    unknowns = []
    has_ci = (repo / ".github").exists() or (repo / ".gitlab-ci.yml").exists() or (repo / "Makefile").exists()
    if not has_ci:
        unknowns.append("CI/CD pipeline is unknown — no .github/, .gitlab-ci.yml, or Makefile found.")
    if s["is_python"] and not s["python_project_name"]:
        unknowns.append("Python project name could not be parsed from pyproject.toml.")
    if s["is_node"] and not s["node_project_name"]:
        unknowns.append("Node.js project name could not be parsed from package.json.")
    if not (repo / "Dockerfile").exists() and not (repo / "docker-compose.yml").exists():
        unknowns.append("Deployment method is unclear — no Dockerfile or docker-compose.yml.")
    if not unknowns:
        unknowns.append("No additional unknowns detected by deterministic scan.")
    return unknowns


def _make_project_brief(repo: Path, goal: str, s: dict, timestamp: str) -> str:
    type_lines = []
    if s["is_python"]:
        details = [f for f, k in [("pyproject.toml", "has_pyproject"), ("requirements.txt", "has_requirements"), ("setup.py", "has_setup_py")] if s[k]]
        type_lines.append(f"- Python ({', '.join(details)})")
    if s["is_node"]:
        details = ["package.json"]
        if s["has_vite_config"]:
            details.append("vite.config")
        type_lines.append(f"- Node.js ({', '.join(details)})")
    if s["has_git"]:
        type_lines.append("- Git repository")
    if s["has_readme"]:
        type_lines.append("- README present")
    if s["has_scripts_dir"]:
        type_lines.append("- scripts/ directory")
    if s["has_tests_dir"]:
        type_lines.append("- tests/ directory")
    if not type_lines:
        type_lines.append("- Unknown (no standard project markers found)")

    project_name = s.get("python_project_name") or s.get("node_project_name") or repo.name
    parts = []
    if s["is_python"]:
        parts.append(f'Python project "{project_name}"')
    elif s["is_node"]:
        parts.append(f'Node.js project "{project_name}"')
    else:
        parts.append(f'Project "{repo.name}"')
    if s["has_git"]:
        parts.append("under git version control")
    if s["has_tests_dir"]:
        parts.append("with a test suite")
    if s["has_scripts_dir"]:
        parts.append("and a scripts/ directory")
    summary = ", ".join(parts) + "."

    return (
        "# Project Brief\n\n"
        f"**Repo path:** {repo}\n"
        f"**User goal:** {goal}\n"
        f"**Scanned at:** {timestamp}\n\n"
        "## Project Type\n\n"
        + "\n".join(type_lines)
        + f"\n\n## Project Name\n\n{project_name}\n\n"
        f"## Summary\n\n{summary}\n\n"
        f"## User Goal\n\n{goal}\n"
    )


def _make_repo_map(repo: Path, tree: str, s: dict) -> str:
    important = []
    for fname, desc in [
        ("pyproject.toml", "Python project config"),
        ("requirements.txt", "Python dependencies"),
        ("setup.py", "Python setup script"),
        ("package.json", "Node.js project config"),
        ("README.md", "Project documentation"),
        ("README.rst", "Project documentation"),
        (".env.example", "Environment variable template"),
        ("Dockerfile", "Container build file"),
        ("Makefile", "Build/task commands"),
    ]:
        if (repo / fname).exists():
            important.append(f"- `{fname}` — {desc}")
    lines = [
        "# Repo Map\n",
        "Top-level structure (noisy folders excluded):\n",
        f"```\n{tree}\n```\n",
    ]
    if important:
        lines.append("## Important Files\n")
        lines.extend(important)
        lines.append("")
    return "\n".join(lines)


def _make_commands_md(cmds: dict) -> str:
    parts = ["# Commands\n"]
    if cmds["install"]:
        parts += ["## Install\n", "```bash"] + cmds["install"] + ["```\n"]
    if cmds["test"]:
        parts += ["## Test\n", "```bash"] + cmds["test"] + ["```\n"]
    if cmds["run"]:
        parts += ["## Run\n", "```bash"] + cmds["run"] + ["```\n"]
    if cmds["notes"]:
        parts.append("## Notes\n")
        parts.extend(f"- {n}" for n in cmds["notes"])
        parts.append("")
    if not cmds["install"] and not cmds["test"] and not cmds["run"]:
        parts.append("No commands detected. Fill in manually.\n")
    parts.append("*Commands detected by static scan — verify before running.*")
    return "\n".join(parts) + "\n"


def _make_risk_list(risks: list) -> str:
    lines = ["# Risk List\n"] + [f"- [ ] {r}" for r in risks]
    lines += ["", "*Risks detected by deterministic scan — review before coding.*"]
    return "\n".join(lines) + "\n"


def _make_unknowns_md(unknowns: list) -> str:
    lines = [
        "# Unknown Questions\n",
        "## What Darwin Could Not Determine\n",
    ] + [f"- {u}" for u in unknowns] + [
        "",
        "## Questions to Answer Before Coding\n",
        "1. Are there environment variables required to run this project?",
        "2. Is there a CI/CD pipeline and what does it run?",
        "3. Are there external services or APIs this project depends on?",
        "4. What is the deployment target (local, cloud, container)?",
        "",
        "## Safe Assumptions\n",
        "- Tests should pass before merging any change.",
        "- Existing user files must not be deleted or overwritten.",
        "- New code should follow the existing project style.",
    ]
    return "\n".join(lines) + "\n"


def _make_master_plan_draft(goal: str, s: dict) -> str:
    gl = goal.lower()
    bullets = ["- Understand current state of the codebase"]
    if any(w in gl for w in ["test", "testing", "spec", "coverage"]):
        if s["is_python"] and not s["has_tests_dir"]:
            bullets.append("- Set up tests/ directory and configure pytest")
        bullets += [
            "- Identify which modules or commands lack test coverage",
            "- Add unit tests for each untested module",
            "- Add integration or smoke tests for key workflows",
            "- Run the test suite and confirm all tests pass",
        ]
    elif any(w in gl for w in ["refactor", "clean", "simplify"]):
        bullets += [
            "- Identify duplicated or overly complex code",
            "- Plan the refactor to avoid breaking existing behaviour",
            "- Apply the refactor in small reviewable chunks",
            "- Confirm existing tests still pass after each chunk",
        ]
    elif any(w in gl for w in ["doc", "documentation", "readme"]):
        bullets += [
            "- Audit existing documentation for gaps",
            "- Write or update README with accurate usage instructions",
            "- Add documentation to public functions or modules",
            "- Review and update any example outputs",
        ]
    elif any(w in gl for w in ["fix", "bug", "error", "issue", "broken"]):
        bullets += [
            "- Reproduce the issue with a minimal test case",
            "- Identify the root cause in the codebase",
            "- Implement the fix",
            "- Add a regression test to prevent recurrence",
        ]
    elif any(w in gl for w in ["add", "build", "create", "implement", "feature"]):
        bullets += [
            "- Define the exact scope of the new feature",
            "- Identify files that will need to change",
            "- Implement the feature in small chunks",
            "- Add tests for the new feature",
            "- Update documentation",
        ]
    else:
        bullets += [
            f"- Identify what changes are needed to achieve: {goal}",
            "- Implement changes in small reviewable chunks",
            "- Add or update tests for any modified code",
            "- Update documentation if needed",
        ]
    return (
        "# Master Plan Draft\n\n"
        f"**Goal:** {goal}\n\n"
        "*Generated by deterministic scan. Review and edit before running `darwin split-plan`.*\n\n"
        "## Tasks\n\n"
        + "\n".join(bullets) + "\n"
    )


# ── repo intake operation ──────────────────────────────────────────────────────

def op_inspect_repo(repo: Path, goal: str) -> dict:
    """Inspect a repo and create a .darwin/ understanding pack."""
    if not repo.exists():
        return {"error": f"repo path not found: {repo}"}
    if not repo.is_dir():
        return {"error": f"repo path is a file, not a folder: {repo}"}

    signals = _detect_project_signals(repo)
    tree = _build_repo_tree(repo)
    cmds = _detect_commands(repo, signals)
    risks = _detect_risks(repo, signals)
    unknowns = _detect_unknowns(repo, signals)
    timestamp = now()

    darwin_dir = repo / ".darwin"
    darwin_dir.mkdir(exist_ok=True)

    files = {
        "PROJECT_BRIEF.md": _make_project_brief(repo, goal, signals, timestamp),
        "REPO_MAP.md": _make_repo_map(repo, tree, signals),
        "COMMANDS.md": _make_commands_md(cmds),
        "RISK_LIST.md": _make_risk_list(risks),
        "UNKNOWN_QUESTIONS.md": _make_unknowns_md(unknowns),
        "MASTER_PLAN_DRAFT.md": _make_master_plan_draft(goal, signals),
    }

    created = []
    existing = []
    for filename, content in files.items():
        path = darwin_dir / filename
        if path.exists():
            existing.append(filename)
        else:
            path.write_text(content)
            created.append(filename)

    return {
        "repo": str(repo),
        "darwin_dir": str(darwin_dir),
        "created": created,
        "existing": existing,
    }
