import re
from datetime import datetime
from pathlib import Path

import typer

app = typer.Typer(help="Darwin CLI.", no_args_is_help=True)

INIT_DIRS = ["chunks", "memory", "templates", "reports"]

INIT_FILES = {
    "MASTER_PLAN.md": (
        "# Master Plan\n\n"
        "Example plan:\n\n"
        "- Build the smallest CLI skeleton.\n"
        "- Set up the workspace files.\n"
        "- Split the plan into chunks.\n"
    ),
    "ROADMAP.md": (
        "# Roadmap\n\n"
        "Roadmap is not generated yet.\n"
    ),
    "memory/mistakes.md": "# Mistakes\n",
    "memory/winners.md": "# Winners\n",
    "memory/decisions.md": "# Decisions\n",
}


def _slug(text: str, max_len: int = 40) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text.strip())
    return text[:max_len].rstrip("-")


@app.callback()
def main() -> None:
    """Darwin CLI."""


@app.command()
def init() -> None:
    """Create the Darwin working directories and starter files."""
    for name in INIT_DIRS:
        path = Path(name)
        path.mkdir(parents=True, exist_ok=True)
        typer.echo(f"ready:   {path}/")

    for name, content in INIT_FILES.items():
        path = Path(name)
        if path.exists():
            typer.echo(f"exists:  {path}")
            continue
        path.write_text(content)
        typer.echo(f"created: {path}")


@app.command("split-plan")
def split_plan(
    plan_file: Path = typer.Argument(..., help="Path to the master plan markdown file."),
) -> None:
    """Extract tasks, create chunk folders with TASK.md, and write ROADMAP.md."""
    if not plan_file.exists():
        typer.echo(f"error: file not found: {plan_file}", err=True)
        raise typer.Exit(1)

    lines = plan_file.read_text().splitlines()
    tasks = []
    for line in lines:
        if line.startswith("- ") or line.startswith("* "):
            task = line[2:].strip()
            if task:
                tasks.append(task)

    if not tasks:
        typer.echo("No bullet tasks found in the plan. Nothing was changed.")
        return

    typer.echo(f"Found {len(tasks)} task(s):\n")

    roadmap_lines = ["# Roadmap", "", "## Pending Tasks", ""]

    for i, task in enumerate(tasks, 1):
        num = f"{i:03d}"
        folder_name = f"{num}-{_slug(task)}"
        folder_path = Path("chunks") / folder_name
        task_file = folder_path / "TASK.md"

        folder_path.mkdir(parents=True, exist_ok=True)

        if task_file.exists():
            file_status = "exists"
        else:
            task_file.write_text(
                f"# Chunk {num}\n\n"
                f"**Task:** {task}\n"
                f"**Status:** pending\n"
            )
            file_status = "created"

        typer.echo(f"  {num} — {task}")
        typer.echo(f"       {folder_path}/ [{file_status} TASK.md]")

        roadmap_lines.append(f"- [ ] {num} — {task} — `{folder_path}/`")

    Path("ROADMAP.md").write_text("\n".join(roadmap_lines) + "\n")
    typer.echo(f"\nwritten: ROADMAP.md")
    typer.echo(f"done:    chunks/ ({len(tasks)} folder(s))")


def _parse_task_text(task_md: str) -> str:
    """Extract the task text from TASK.md content."""
    for line in task_md.splitlines():
        if line.startswith("**Task:**"):
            return line.removeprefix("**Task:**").strip()
    return "(task text not found)"


def _write_if_missing(path: Path, content: str) -> str:
    """Write content to path only if it does not exist. Returns 'created' or 'exists'."""
    if path.exists():
        return "exists"
    path.write_text(content)
    return "created"


@app.command("prepare-chunk")
def prepare_chunk(
    chunk_path: Path = typer.Argument(..., help="Path to the chunk folder, e.g. chunks/001-example-task"),
) -> None:
    """Create STEP.md, CONTEXT.md, CLAUDE_PROMPT.md, CODEX_REVIEW_PROMPT.md, ACCEPTANCE.md, and TESTS.md."""
    if not chunk_path.exists():
        typer.echo(f"error: chunk folder not found: {chunk_path}", err=True)
        raise typer.Exit(1)

    task_file = chunk_path / "TASK.md"
    if not task_file.exists():
        typer.echo(f"error: TASK.md not found in {chunk_path}", err=True)
        raise typer.Exit(1)

    task_text = _parse_task_text(task_file.read_text())
    chunk_name = chunk_path.name

    files: list[tuple[Path, str]] = [
        (
            chunk_path / "STEP.md",
            f"# STEP — {chunk_name}\n\n"
            f"## Goal\n\n"
            f"{task_text}\n\n"
            f"## Scope\n\n"
            f"<!-- What is in scope for this chunk? -->\n\n"
            f"## Inputs\n\n"
            f"<!-- What files or information does this chunk start with? -->\n\n"
            f"## Outputs\n\n"
            f"<!-- What files or results should this chunk produce? -->\n\n"
            f"## Acceptance Criteria\n\n"
            f"- [ ] <!-- Add acceptance criteria here -->\n\n"
            f"## Notes\n\n"
            f"<!-- Any extra notes, constraints, or decisions -->\n",
        ),
        (
            chunk_path / "CONTEXT.md",
            f"# CONTEXT — {chunk_name}\n\n"
            f"## Task Summary\n\n"
            f"{task_text}\n\n"
            f"## Current Project State\n\n"
            f"<!-- Describe what already exists in the project that is relevant -->\n\n"
            f"## Files Likely Involved\n\n"
            f"<!-- List files this chunk will read or modify -->\n\n"
            f"## Constraints\n\n"
            f"- Do not overbuild.\n"
            f"- Only implement what this chunk requires.\n"
            f"- Do not add features planned for later chunks.\n",
        ),
        (
            chunk_path / "CLAUDE_PROMPT.md",
            f"# Claude Prompt — {chunk_name}\n\n"
            f"## Task Goal\n\n"
            f"{task_text}\n\n"
            f"## Scope\n\n"
            f"<!-- Fill in from STEP.md -->\n\n"
            f"## Allowed Changes\n\n"
            f"<!-- List the files and changes that are in scope -->\n\n"
            f"## Forbidden\n\n"
            f"- Do not implement features planned for later chunks.\n"
            f"- Do not overbuild.\n"
            f"- Do not modify files outside this chunk's scope.\n\n"
            f"## Acceptance Criteria\n\n"
            f"<!-- Copy from STEP.md -->\n\n"
            f"## Test Instructions\n\n"
            f"<!-- Describe exact commands to verify this chunk works -->\n\n"
            f"## Output Required\n\n"
            f"After completing the task, show:\n\n"
            f"1. Files changed\n"
            f"2. Exact test commands\n"
            f"3. Test output\n"
            f"4. What was intentionally not built\n",
        ),
        (
            chunk_path / "CODEX_REVIEW_PROMPT.md",
            f"# Codex Review Prompt — {chunk_name}\n\n"
            f"You are a strict senior code reviewer.\n\n"
            f"## Your Role\n\n"
            f"Review the implementation of this chunk and determine PASS or FAIL.\n\n"
            f"## Chunk Goal\n\n"
            f"{task_text}\n\n"
            f"## Scope Guard\n\n"
            f"This chunk must only implement what is listed in STEP.md.\n"
            f"Reject anything beyond the stated scope.\n\n"
            f"## Expected Files\n\n"
            f"<!-- List the files that should have been created or changed -->\n\n"
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
            f"```\n"
            f"PASS — <one line reason>\n"
            f"```\n\n"
            f"or\n\n"
            f"```\n"
            f"FAIL — <one line reason>\n"
            f"       <specific item that failed>\n"
            f"```\n",
        ),
        (
            chunk_path / "ACCEPTANCE.md",
            f"# Acceptance — {chunk_name}\n\n"
            f"## Checklist\n\n"
            f"- [ ] Chunk goal is satisfied: {task_text}\n"
            f"- [ ] Required files were created or changed\n"
            f"- [ ] Existing user files were not overwritten\n"
            f"- [ ] All tests pass\n"
            f"- [ ] README is accurate (if changed)\n"
            f"- [ ] No future features were added\n",
        ),
        (
            chunk_path / "TESTS.md",
            f"# Tests — {chunk_name}\n\n"
            f"## Install\n\n"
            f"```bash\n"
            f"python -m venv .venv && source .venv/bin/activate\n"
            f"pip install -e .\n"
            f"```\n\n"
            f"## Run\n\n"
            f"```bash\n"
            f"# TODO: fill in the relevant CLI command for this chunk\n"
            f"darwin <command> <args>\n"
            f"```\n\n"
            f"## Idempotency Test\n\n"
            f"```bash\n"
            f"# Run the command twice and confirm no crash and no data loss\n"
            f"darwin <command> <args>\n"
            f"darwin <command> <args>\n"
            f"```\n\n"
            f"## Error Cases\n\n"
            f"```bash\n"
            f"# Missing file or folder\n"
            f"darwin <command> missing-path\n"
            f"# Expected: clean error message, exit code 1, no traceback\n"
            f"```\n",
        ),
    ]

    for path, content in files:
        status = _write_if_missing(path, content)
        typer.echo(f"{status + ':':<9} {path}")


VALID_STATUSES = {"pass", "fail", "blocked"}

REQUIRED_FILES = [
    "TASK.md",
    "STEP.md",
    "CONTEXT.md",
    "CLAUDE_PROMPT.md",
    "CODEX_REVIEW_PROMPT.md",
    "ACCEPTANCE.md",
    "TESTS.md",
]
OPTIONAL_FILES = ["RESULT.md"]
FORBIDDEN_FILES = ["MEMORY_UPDATE.md", "metadata.yaml"]


def _check_chunk(chunk_path: Path) -> None:
    """Raise a clean error if chunk folder or TASK.md is missing."""
    if not chunk_path.exists():
        typer.echo(f"error: chunk folder not found: {chunk_path}", err=True)
        raise typer.Exit(1)
    if not (chunk_path / "TASK.md").exists():
        typer.echo(f"error: TASK.md not found in {chunk_path}", err=True)
        raise typer.Exit(1)


def _now() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@app.command("record-result")
def record_result(
    chunk_path: Path = typer.Argument(..., help="Path to the chunk folder."),
    status: str = typer.Option(..., help="Result status: pass, fail, or blocked."),
    notes: str = typer.Option("", help="Notes about the result."),
) -> None:
    """Record a result entry (pass/fail/blocked) for a chunk."""
    _check_chunk(chunk_path)

    if status not in VALID_STATUSES:
        typer.echo(
            f"error: invalid status '{status}'. Choose from: {', '.join(sorted(VALID_STATUSES))}",
            err=True,
        )
        raise typer.Exit(1)

    task_text = _parse_task_text((chunk_path / "TASK.md").read_text())
    result_file = chunk_path / "RESULT.md"
    timestamp = _now()

    entry = (
        f"\n## Result — {timestamp}\n\n"
        f"**Chunk:** {chunk_path}\n"
        f"**Task:** {task_text}\n"
        f"**Status:** {status.upper()}\n"
        f"**Notes:** {notes or '(none)'}\n"
    )

    if result_file.exists():
        result_file.write_text(result_file.read_text() + entry)
        typer.echo(f"appended: {result_file}")
    else:
        result_file.write_text(f"# Results — {chunk_path.name}\n" + entry)
        typer.echo(f"created:  {result_file}")


@app.command("review-chunk")
def review_chunk(
    chunk_path: Path = typer.Argument(..., help="Path to the chunk folder."),
) -> None:
    """Run local file checks on a chunk and write REVIEW.md."""
    _check_chunk(chunk_path)

    timestamp = _now()
    lines: list[str] = []

    lines.append(f"## Review — {timestamp}\n")
    lines.append("### Required Files\n")
    all_required_present = True
    for name in REQUIRED_FILES:
        present = (chunk_path / name).exists()
        mark = "x" if present else " "
        lines.append(f"- [{mark}] {name}")
        if not present:
            all_required_present = False

    lines.append("\n### Optional Files\n")
    for name in OPTIONAL_FILES:
        present = (chunk_path / name).exists()
        mark = "x" if present else " "
        lines.append(f"- [{mark}] {name}")

    lines.append("\n### Forbidden Files\n")
    any_forbidden_present = False
    for name in FORBIDDEN_FILES:
        present = (chunk_path / name).exists()
        mark = "x" if present else " "
        lines.append(f"- [{mark}] {name} {'← PRESENT (forbidden)' if present else ''}")
        if present:
            any_forbidden_present = True

    verdict = "PASS" if (all_required_present and not any_forbidden_present) else "FAIL"
    lines.append(f"\n### Verdict: {verdict}\n")

    entry = "\n".join(lines) + "\n"
    review_file = chunk_path / "REVIEW.md"

    if review_file.exists():
        review_file.write_text(review_file.read_text() + "\n---\n\n" + entry)
        typer.echo(f"appended: {review_file}")
    else:
        review_file.write_text(f"# Review — {chunk_path.name}\n\n" + entry)
        typer.echo(f"created:  {review_file}")

    typer.echo(f"verdict:  {verdict}")


if __name__ == "__main__":
    app()
