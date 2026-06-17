"""Chunk OS business logic — prepare, record, review, update-memory."""

import re
from pathlib import Path

from darwin.common import (
    FORBIDDEN_FILES,
    INIT_DIRS,
    INIT_FILES,
    OPTIONAL_FILES,
    REQUIRED_FILES,
    VALID_STATUSES,
    _append_memory_file,
    now,
    parse_latest_result_status,
    parse_latest_review_verdict,
    parse_task_text,
    resolve_chunk_path,
    write_if_missing,
)


def op_init(base: Path) -> dict:
    """Create Darwin workspace directories and starter files without overwriting."""
    ready = []
    for name in INIT_DIRS:
        path = base / name
        path.mkdir(parents=True, exist_ok=True)
        ready.append(name)

    created = []
    existing = []
    for name, content in INIT_FILES.items():
        path = base / name
        if path.exists():
            existing.append(name)
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        created.append(name)

    return {
        "ready": ready,
        "created": created,
        "existing": existing,
    }


def op_split_plan(base: Path, plan_file: Path) -> dict:
    """Create chunk TASK.md files and ROADMAP.md from bullet tasks."""
    plan_path = plan_file if plan_file.is_absolute() else base / plan_file
    if not plan_path.exists():
        return {"error": f"file not found: {plan_file}"}

    tasks = [
        line[2:].strip()
        for line in plan_path.read_text().splitlines()
        if (line.startswith("- ") or line.startswith("* ")) and line[2:].strip()
    ]
    if not tasks:
        return {"tasks": [], "created": [], "existing": [], "roadmap": None}

    roadmap_lines = ["# Roadmap", "", "## Pending Tasks", ""]
    created = []
    existing = []
    task_results = []
    for i, task in enumerate(tasks, 1):
        num = f"{i:03d}"
        folder_name = f"{num}-{slug(task)}"
        folder_path = base / "chunks" / folder_name
        task_file = folder_path / "TASK.md"
        folder_path.mkdir(parents=True, exist_ok=True)

        if task_file.exists():
            file_status = "exists"
            existing.append(str(task_file.relative_to(base)))
        else:
            task_file.write_text(
                f"# Chunk {num}\n\n"
                f"**Task:** {task}\n"
                f"**Status:** pending\n"
            )
            file_status = "created"
            created.append(str(task_file.relative_to(base)))

        rel_folder = folder_path.relative_to(base)
        task_results.append({
            "number": num,
            "task": task,
            "path": str(rel_folder),
            "task_file_status": file_status,
        })
        roadmap_lines.append(f"- [ ] {num} — {task} — `{rel_folder}/`")

    roadmap_path = base / "ROADMAP.md"
    roadmap_path.write_text("\n".join(roadmap_lines) + "\n")
    return {
        "tasks": task_results,
        "created": created,
        "existing": existing,
        "roadmap": str(roadmap_path.relative_to(base)),
    }


def _chunk_templates(chunk_name: str, task_text: str) -> dict[str, str]:
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


def op_list_chunks(base: Path) -> list[dict]:
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
    chunk_path = resolve_chunk_path(base, chunk_rel)
    target = chunk_path / filename
    if not chunk_path.exists():
        return {"error": f"chunk folder not found: {chunk_rel}"}
    if not target.exists():
        return {"error": f"{filename} not found in {chunk_rel}"}
    return {"chunk": chunk_rel, "file": filename, "content": target.read_text()}


def op_record_result(base: Path, chunk_rel: str, status: str, notes: str) -> dict:
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
