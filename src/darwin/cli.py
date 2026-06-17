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
    op_batch_plan,
    op_brain_init,
    op_brain_route,
    op_brain_status,
    op_doctor,
    op_eval_init,
    op_eval_list,
    op_eval_report,
    op_eval_run,
    op_feature_init,
    op_feature_list,
    op_feature_status,
    op_inspect_repo,
    op_operate_existing,
    op_spec_init,
    op_spec_status,
    op_status,
    op_tool_init,
    op_tool_list,
    op_tool_suggest,
    op_update_memory,
    op_version,
    op_worker_init,
    op_worker_list,
    op_worker_suggest,
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


@app.command("inspect-repo")
def inspect_repo(
    repo_path: Path = typer.Argument(..., help="Path to the repo to inspect."),
    goal: str = typer.Option(..., help="Your goal for this project."),
) -> None:
    """Inspect a repo and create a .darwin/ understanding pack."""
    result = op_inspect_repo(repo_path.resolve(), goal)
    if "error" in result:
        typer.echo(f"error: {result['error']}", err=True)
        raise typer.Exit(1)
    typer.echo(f"repo:   {result['repo']}")
    typer.echo(f"output: {result['darwin_dir']}/")
    for f in result["created"]:
        typer.echo(f"created: .darwin/{f}")
    for f in result["existing"]:
        typer.echo(f"exists:  .darwin/{f}")


@app.command("spec-init")
def spec_init() -> None:
    """Create .darwin/spec/ with contract files. Never overwrites existing files."""
    result = op_spec_init(Path("."))
    typer.echo(f"spec dir: {result['spec_dir']}/")
    for f in result["created"]:
        typer.echo(f"created: .darwin/spec/{f}")
    for f in result["existing"]:
        typer.echo(f"exists:  .darwin/spec/{f}")


@app.command("spec-status")
def spec_status() -> None:
    """Show spec surface status (.darwin/spec/)."""
    result = op_spec_status(Path("."))
    if not result["initialized"]:
        typer.echo(result["message"])
        raise typer.Exit(1)
    typer.echo("Spec Surface")
    typer.echo("=" * 12)
    typer.echo(f"spec dir: {result['spec_dir']}/")
    typer.echo("")
    typer.echo("Files:")
    for fname, present in result["files"].items():
        typer.echo(f"  [{'x' if present else ' '}] .darwin/spec/{fname}")
    typer.echo("")
    typer.echo(f"Protected commands: {result['protected_command_count']}")


@app.command("tool-init")
def tool_init() -> None:
    """Create .darwin/tools/ with tool cards. Never overwrites existing cards."""
    result = op_tool_init(Path("."))
    typer.echo(f"tools dir: {result['tools_dir']}/")
    for f in result["created"]:
        typer.echo(f"created: .darwin/tools/{f}")
    for f in result["existing"]:
        typer.echo(f"exists:  .darwin/tools/{f}")


@app.command("tool-list")
def tool_list() -> None:
    """List tool cards in .darwin/tools/ with type, risk, and approval."""
    result = op_tool_list(Path("."))
    if not result["initialized"]:
        typer.echo(result["message"])
        raise typer.Exit(1)
    typer.echo("Tool Registry")
    typer.echo("=" * 13)
    typer.echo(f"Tools in {result['tools_dir']}/ ({result['count']}):")
    typer.echo("")
    for t in result["tools"]:
        typer.echo(f"  {t['filename']}")
        typer.echo(f"    Type:     {t['type']}")
        typer.echo(f"    Risk:     {t['risk']}")
        typer.echo(f"    Approval: {t['approval']}")


@app.command("tool-suggest")
def tool_suggest(
    goal: str = typer.Option(..., help="Your goal or task description."),
) -> None:
    """Suggest tools for a goal using deterministic keyword matching."""
    result = op_tool_suggest(Path("."), goal)
    typer.echo("Tool Suggestions")
    typer.echo("=" * 16)
    typer.echo(f"Goal: {result['goal']}")
    typer.echo("")
    if not result["matches"]:
        typer.echo("No tools matched this goal.")
    else:
        typer.echo(f"Recommended tools ({result['total_matched']}):")
        typer.echo("")
        for m in result["matches"]:
            kw_str = ", ".join(m["matched_keywords"])
            typer.echo(f"  {m['tool']}")
            typer.echo(f"    Matched:  {kw_str}")
            typer.echo(f"    Risk:     {m['risk']}")
            typer.echo(f"    Approval: {m['approval']}")
        typer.echo("")
    if result["warning"]:
        typer.echo(f"Warning: {result['warning']}")
        typer.echo("")
    typer.echo(result["disclaimer"])


@app.command("eval-init")
def eval_init() -> None:
    """Create eval folder structure and starter task files."""
    result = op_eval_init(Path("."))
    for d in result["dirs"]:
        typer.echo(f"ready:   {d}/")
    for f in result["created"]:
        typer.echo(f"created: {f}")
    for f in result["existing"]:
        typer.echo(f"exists:  {f}")


@app.command("eval-list")
def eval_list() -> None:
    """List available eval task files in evals/tasks/."""
    result = op_eval_list(Path("."))
    if "error" in result:
        typer.echo(f"error: {result['error']}", err=True)
        raise typer.Exit(1)
    if not result["tasks"]:
        typer.echo("No eval tasks found in evals/tasks/.")
        return
    typer.echo(f"Eval tasks ({result['count']}):")
    for task in result["tasks"]:
        typer.echo(f"  {task}")


@app.command("eval-run")
def eval_run(
    task_name: str = typer.Argument(..., help="Eval task name (without .md)."),
    candidate: str = typer.Option(..., help="Candidate name being evaluated."),
) -> None:
    """Create a timestamped run report for an eval task."""
    result = op_eval_run(Path("."), task_name, candidate)
    if "error" in result:
        typer.echo(f"error: {result['error']}", err=True)
        raise typer.Exit(1)
    typer.echo(f"task:      {result['task']}")
    typer.echo(f"candidate: {result['candidate']}")
    typer.echo(f"run:       {result['run_file']}")
    typer.echo(f"latest:    {result['latest_file']}")


@app.command("eval-report")
def eval_report() -> None:
    """Print evals/reports/latest.md."""
    result = op_eval_report(Path("."))
    if "error" in result:
        typer.echo(f"error: {result['error']}", err=True)
        raise typer.Exit(1)
    typer.echo(result["content"])


@app.command("version")
def version_cmd() -> None:
    """Print Darwin version."""
    result = op_version()
    typer.echo(f"darwin version {result['version']}")


@app.command("status")
def status() -> None:
    """Show workspace and Darwin level summary."""
    r = op_status(Path("."))
    typer.echo("Darwin Status")
    typer.echo("=" * 13)
    typer.echo(f"CWD: {r['cwd']}")
    typer.echo(f"git: {'yes (.git found)' if r['has_git'] else 'not found'}")
    typer.echo("")
    typer.echo("Project files:")
    for name, present in r["files"].items():
        typer.echo(f"  [{'x' if present else ' '}] {name}")
    typer.echo("")
    typer.echo("Workspace directories:")
    for name, present in r["dirs"].items():
        typer.echo(f"  [{'x' if present else ' '}] {name}")
    typer.echo("")
    typer.echo("Smoke tests:")
    for name, present in r["smoke_tests"].items():
        typer.echo(f"  [{'x' if present else ' '}] {name}")
    typer.echo("")
    typer.echo(f"Darwin level: {r['darwin_level']} — {r['darwin_level_label']}")


@app.command("doctor")
def doctor() -> None:
    """Run read-only health checks. Does not run smoke tests."""
    checks = op_doctor(Path("."))
    typer.echo("Darwin Doctor")
    typer.echo("=" * 13)
    for c in checks:
        detail = f" — {c['detail']}" if c["detail"] else ""
        typer.echo(f"[{c['status']:<4}] {c['check']}{detail}")
    typer.echo("")
    n_pass = sum(1 for c in checks if c["status"] == "PASS")
    n_warn = sum(1 for c in checks if c["status"] == "WARN")
    n_fail = sum(1 for c in checks if c["status"] == "FAIL")
    typer.echo(f"Summary: {n_pass} PASS, {n_warn} WARN, {n_fail} FAIL")


@app.command("feature-init")
def feature_init() -> None:
    """Create .darwin/features/ with feature/command/coverage registry files."""
    result = op_feature_init(Path("."))
    typer.echo(f"features dir: {result['features_dir']}/")
    for f in result["created"]:
        typer.echo(f"created: .darwin/features/{f}")
    for f in result["existing"]:
        typer.echo(f"exists:  .darwin/features/{f}")


@app.command("feature-list")
def feature_list() -> None:
    """List feature registry files in .darwin/features/."""
    result = op_feature_list(Path("."))
    if not result["initialized"]:
        typer.echo(result["message"])
        raise typer.Exit(1)
    typer.echo("Feature Registry")
    typer.echo("=" * 16)
    typer.echo(f"Features dir: {result['features_dir']}/")
    typer.echo(f"Files: {', '.join(result['files'])}")
    typer.echo(f"Complete features: {result['feature_count']}")


@app.command("feature-status")
def feature_status() -> None:
    """Show feature registry status (.darwin/features/)."""
    result = op_feature_status(Path("."))
    if not result["initialized"]:
        typer.echo(result["message"])
        raise typer.Exit(1)
    typer.echo("Feature Registry Status")
    typer.echo("=" * 23)
    typer.echo(f"features dir: {result['features_dir']}/")
    typer.echo("")
    typer.echo("Files:")
    for fname, present in result["files"].items():
        typer.echo(f"  [{'x' if present else ' '}] .darwin/features/{fname}")
    typer.echo("")
    typer.echo(f"Known commands: {result['command_count']}")
    typer.echo(f"Smoke test coverage entries: {result['smoke_test_count']}")


@app.command("worker-init")
def worker_init() -> None:
    """Create .darwin/workers/ with worker cards. Never overwrites existing cards."""
    result = op_worker_init(Path("."))
    typer.echo(f"workers dir: {result['workers_dir']}/")
    for f in result["created"]:
        typer.echo(f"created: .darwin/workers/{f}")
    for f in result["existing"]:
        typer.echo(f"exists:  .darwin/workers/{f}")


@app.command("worker-list")
def worker_list() -> None:
    """List worker cards in .darwin/workers/ with role, risk, and approval."""
    result = op_worker_list(Path("."))
    if not result["initialized"]:
        typer.echo(result["message"])
        raise typer.Exit(1)
    typer.echo("Worker Registry")
    typer.echo("=" * 15)
    typer.echo(f"Workers in {result['workers_dir']}/ ({result['count']}):")
    typer.echo("")
    for w in result["workers"]:
        typer.echo(f"  {w['filename']}")
        typer.echo(f"    Role:     {w['role']}")
        typer.echo(f"    Risk:     {w['risk']}")
        typer.echo(f"    Approval: {w['approval']}")


@app.command("worker-suggest")
def worker_suggest(
    goal: str = typer.Option(..., help="Your goal or task description."),
) -> None:
    """Suggest workers for a goal using deterministic keyword matching."""
    result = op_worker_suggest(Path("."), goal)
    typer.echo("Worker Suggestions")
    typer.echo("=" * 18)
    typer.echo(f"Goal: {result['goal']}")
    typer.echo("")
    if not result["matches"]:
        typer.echo("No workers matched this goal.")
    else:
        typer.echo(f"Recommended workers ({result['total_matched']}):")
        typer.echo("")
        for m in result["matches"]:
            kw_str = ", ".join(m["matched_keywords"])
            typer.echo(f"  {m['worker']}")
            typer.echo(f"    Matched:  {kw_str}")
            typer.echo(f"    Risk:     {m['risk']}")
            typer.echo(f"    Approval: {m['approval']}")
        typer.echo("")
    typer.echo(result["disclaimer"])


@app.command("batch-plan")
def batch_plan(
    goal: str = typer.Option(..., help="Your goal for batch planning."),
    max_items: int = typer.Option(7, help="Maximum items in the batch (1-7)."),
) -> None:
    """Plan a safe batch size for a goal. Read-only, deterministic, no execution."""
    result = op_batch_plan(goal, max_items)
    typer.echo("Batch Planner / Speed Lane")
    typer.echo("=" * 26)
    typer.echo(f"Goal:             {result['goal']}")
    typer.echo(f"Max items:        {result['max_items']}")
    typer.echo(f"Risk:             {result['risk_classification']}")
    typer.echo(f"Recommended size: {result['recommended_batch_size']}")
    typer.echo(f"Suggested mode:   {result['suggested_mode']}")
    typer.echo(f"Why:              {result['why']}")
    typer.echo("")
    typer.echo("Stop conditions:")
    for c in result["stop_conditions"]:
        typer.echo(f"  - {c}")
    typer.echo("")
    typer.echo(f"Fallback plan:    {result['fallback_plan']}")
    typer.echo("")
    typer.echo(f"Note: {result['disclaimer']}")


@app.command("brain-init")
def brain_init() -> None:
    """Create .darwin/brain/ with brain config files. Never overwrites existing files."""
    result = op_brain_init(Path("."))
    typer.echo(f"brain dir: {result['brain_dir']}/")
    for f in result["created"]:
        typer.echo(f"created: .darwin/brain/{f}")
    for f in result["existing"]:
        typer.echo(f"exists:  .darwin/brain/{f}")


@app.command("brain-status")
def brain_status() -> None:
    """Show brain config status. Never prints API key values."""
    result = op_brain_status(Path("."))
    typer.echo("Darwin Brain Status")
    typer.echo("=" * 19)
    typer.echo(f"brain dir: {'present' if result['brain_dir_present'] else 'missing (run: darwin brain-init)'}")
    typer.echo("")
    typer.echo("Brain files:")
    for fname, present in result["files"].items():
        typer.echo(f"  [{'x' if present else ' '}] .darwin/brain/{fname}")
    typer.echo("")
    typer.echo("Provider API keys (present = yes/no only — values never shown):")
    for name, info in result["providers"].items():
        key_status = "yes" if info["key_present"] else "no"
        model_note = f"  model: {info['model_configured']}" if info["model_configured"] else ""
        typer.echo(f"  {name:<12} key: {key_status:<4}  ({info['key_env_var']}){model_note}")
    typer.echo("")
    if result["any_key_present"]:
        typer.echo("At least one API key is configured.")
    else:
        typer.echo("No API keys configured. Brain mode 'off' will be used.")
    typer.echo("")
    typer.echo("Reminder: API keys are environment variables only. Never stored in .darwin/.")


@app.command("brain-route")
def brain_route(
    goal: str = typer.Option(..., help="Your goal or task description."),
    repo_path: str = typer.Option(None, "--repo-path", help="Optional repo path for context."),
    brain: str = typer.Option("off", "--brain", help="Brain mode: off, auto, groq, openrouter, poolside, nvidia."),
) -> None:
    """Route a goal to brain role and body worker. Read-only, no files created."""
    result = op_brain_route(goal, brain=brain, repo_path=repo_path)
    if "error" in result:
        typer.echo(f"error: {result['error']}", err=True)
        raise typer.Exit(1)
    typer.echo("Darwin Brain Route")
    typer.echo("=" * 18)
    typer.echo(f"Goal:              {result['goal']}")
    typer.echo(f"Brain mode:        {result['brain_mode']}")
    typer.echo(f"Route method:      {result['route_method']}")
    typer.echo("")
    typer.echo("Provider availability:")
    for name, present in result["provider_availability"].items():
        typer.echo(f"  {name:<12} {'yes' if present else 'no'}")
    typer.echo("")
    typer.echo(f"Task type:         {result['task_type']}")
    typer.echo(f"Risk level:        {result['risk']}")
    typer.echo(f"Brain role:        {result['brain_role']}")
    typer.echo(f"Body worker:       {result['body_worker']}")
    typer.echo(f"Approval:          {result['approval_requirement']}")
    typer.echo("")
    if result["provider_note"]:
        typer.echo(f"Note: {result['provider_note']}")
        typer.echo("")
    typer.echo(f"Next step: {result['next_step']}")


@app.command("operate-existing")
def operate_existing(
    repo_path: Path = typer.Argument(..., help="Path to the target repo."),
    goal: str = typer.Option(..., help="Your goal for this operator run."),
    brain: str = typer.Option("off", "--brain", help="Brain mode: off, auto, groq, openrouter, poolside, nvidia."),
) -> None:
    """Create a Darwin operator run packet for an existing repo. No workers or tools are executed."""
    result = op_operate_existing(repo_path, goal, brain=brain)
    if "error" in result:
        typer.echo(f"error: {result['error']}", err=True)
        raise typer.Exit(1)
    typer.echo("Darwin Operator Run")
    typer.echo("=" * 19)
    typer.echo(f"Repo:    {result['repo']}")
    typer.echo(f"Goal:    {result['goal']}")
    typer.echo(f"Brain:   {result['brain']}")
    typer.echo(f"Run dir: {result['run_dir']}/")
    typer.echo("")
    typer.echo("Created files:")
    for f in result["created"]:
        typer.echo(f"  {f}")
    typer.echo("")
    typer.echo(f"Route:   {result['route']['route_method']}")
    typer.echo(f"Worker:  {result['route']['body_worker']}")
    typer.echo("")
    typer.echo("Warning: No workers, tools, or APIs were executed.")
    typer.echo("Next:    See NEXT_ACTION.md in the run folder.")


if __name__ == "__main__":
    app()
