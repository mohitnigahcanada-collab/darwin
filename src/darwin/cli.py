from pathlib import Path

import typer

from darwin.core import (
    FORBIDDEN_FILES,
    INIT_DIRS,
    INIT_FILES,
    OPTIONAL_FILES,
    REQUIRED_FILES,
    VALID_STATUSES,
    _chunk_templates,
    now,
    op_update_memory,
    parse_task_text,
    slug,
    write_if_missing,
)

app = typer.Typer(help="Darwin CLI.", no_args_is_help=True)


@app.callback()
def main() -> None:
    """Darwin CLI."""


def _check_chunk(chunk_path: Path) -> None:
    if not chunk_path.exists():
        typer.echo(f"error: chunk folder not found: {chunk_path}", err=True)
        raise typer.Exit(1)
    if not (chunk_path / "TASK.md").exists():
        typer.echo(f"error: TASK.md not found in {chunk_path}", err=True)
        raise typer.Exit(1)


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

    tasks = [
        line[2:].strip()
        for line in plan_file.read_text().splitlines()
        if (line.startswith("- ") or line.startswith("* ")) and line[2:].strip()
    ]
    if not tasks:
        typer.echo("No bullet tasks found in the plan. Nothing was changed.")
        return

    typer.echo(f"Found {len(tasks)} task(s):\n")
    roadmap_lines = ["# Roadmap", "", "## Pending Tasks", ""]

    for i, task in enumerate(tasks, 1):
        num = f"{i:03d}"
        folder_name = f"{num}-{slug(task)}"
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


@app.command("prepare-chunk")
def prepare_chunk(
    chunk_path: Path = typer.Argument(..., help="Path to the chunk folder."),
) -> None:
    """Create STEP.md, CONTEXT.md, CLAUDE_PROMPT.md, CODEX_REVIEW_PROMPT.md, ACCEPTANCE.md, and TESTS.md."""
    _check_chunk(chunk_path)
    task_text = parse_task_text((chunk_path / "TASK.md").read_text())
    templates = _chunk_templates(chunk_path.name, task_text)
    for filename, content in templates.items():
        status = write_if_missing(chunk_path / filename, content)
        typer.echo(f"{status + ':':<9} {chunk_path / filename}")


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

    task_text = parse_task_text((chunk_path / "TASK.md").read_text())
    result_file = chunk_path / "RESULT.md"
    entry = (
        f"\n## Result — {now()}\n\n"
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
        typer.echo(f"appended: {review_file}")
    else:
        review_file.write_text(f"# Review — {chunk_path.name}\n\n" + entry)
        typer.echo(f"created:  {review_file}")
    typer.echo(f"verdict:  {verdict}")


@app.command("update-memory")
def update_memory(
    chunk_path: Path = typer.Argument(..., help="Path to the chunk folder."),
) -> None:
    """Append memory entries from a chunk result and mark ROADMAP.md if passing."""
    _check_chunk(chunk_path)
    for req in ("RESULT.md", "REVIEW.md"):
        if not (chunk_path / req).exists():
            typer.echo(f"error: {req} not found in {chunk_path}", err=True)
            raise typer.Exit(1)

    result = op_update_memory(Path("."), str(chunk_path))
    if "error" in result:
        typer.echo(f"error: {result['error']}", err=True)
        raise typer.Exit(1)

    typer.echo(f"chunk:   {chunk_path}")
    typer.echo(f"result:  {result['result_status']}  |  review: {result['review_verdict']}")
    for action in result["actions"]:
        typer.echo(f"{'marked:' if 'ROADMAP' in action and '[x]' in action else 'appended:' if 'appended' in action else 'note:    '} {action}")


@app.command("next-chunk")
def next_chunk() -> None:
    """Print the first unchecked chunk from ROADMAP.md."""
    roadmap = Path("ROADMAP.md")
    if not roadmap.exists():
        typer.echo("error: ROADMAP.md not found. Run `darwin split-plan` first.", err=True)
        raise typer.Exit(1)
    import re
    for line in roadmap.read_text().splitlines():
        if not line.startswith("- [ ]"):
            continue
        match = re.search(r"`(chunks/[^`]+)`", line)
        chunk_path = match.group(1).rstrip("/") if match else None
        parts = line.lstrip("- [ ]").strip().split(" — ")
        summary = " — ".join(parts[:-1]) if len(parts) > 1 else parts[0]
        typer.echo(f"next chunk:  {summary.strip()}")
        if chunk_path:
            typer.echo(f"path:        {chunk_path}")
            typer.echo(f"run:         darwin prepare-chunk {chunk_path}")
        return
    typer.echo("No pending chunks. All tasks are done or ROADMAP.md has no unchecked items.")


if __name__ == "__main__":
    app()
