"""Operator Run V0 — operate-existing command."""

import os
import re
from pathlib import Path

from darwin.brain_ops import (
    _classify_task,
    _PROVIDERS,
    _provider_availability,
    op_brain_route,
)
from darwin.common import now, slug
from darwin.repo_intake_ops import (
    _build_repo_tree,
    _detect_commands,
    _detect_project_signals,
    _detect_risks,
)

# ── Run file generators ────────────────────────────────────────────────────────


def _run_summary(repo: Path, goal: str, brain: str, route: dict, run_dir: Path, run_files: list) -> str:
    worker = route.get("body_worker", "Claude Code Builder")
    route_method = route.get("route_method", "deterministic")
    return (
        f"# Run Summary\n\n"
        f"**Repo:** {repo}\n"
        f"**Goal:** {goal}\n"
        f"**Brain mode:** {brain}\n"
        f"**Route method:** {route_method}\n"
        f"**Recommended brain role:** {route.get('brain_role', 'N/A')}\n"
        f"**Recommended body worker:** {worker}\n"
        f"**Run folder:** {run_dir}\n\n"
        f"## Created Files\n\n"
        + "\n".join(f"- {f}" for f in run_files)
        + "\n\n"
        f"## Next Action\n\n"
        f"See NEXT_ACTION.md\n\n"
        f"## Warning\n\n"
        f"**No workers, tools, or APIs were executed in this run.**\n"
        f"This folder contains prompts and plans only. You must paste the prompts\n"
        f"into the appropriate body worker manually.\n"
    )


def _brain_route_md(route: dict, brain: str) -> str:
    avail = route.get("provider_availability", {})
    avail_lines = "\n".join(
        f"- {name}: {'yes' if present else 'no'}"
        for name, present in avail.items()
    )
    note = route.get("provider_note", "")
    return (
        f"# Brain Route\n\n"
        f"**Brain mode:** {brain}\n"
        f"**Route method:** {route.get('route_method', 'deterministic')}\n"
        f"**Selected provider:** {route.get('selected_provider') or 'none (offline)'}\n\n"
        f"## Provider Availability\n\n"
        + avail_lines
        + f"\n\n## Route Note\n\n{note}\n\n"
        f"## Route Decision\n\n"
        f"**Task type:** {route.get('task_type', 'build')}\n"
        f"**Risk:** {route.get('risk', 'low')}\n"
        f"**Recommended brain role:** {route.get('brain_role', 'N/A')}\n"
        f"**Recommended body worker:** {route.get('body_worker', 'Claude Code Builder')}\n\n"
        f"## Approval Gates\n\n"
        f"{route.get('approval_requirement', 'Not required for build; required before commit.')}\n"
    )


def _brain_plan_md(goal: str, route: dict) -> str:
    task_type = route.get("task_type", "build")
    worker = route.get("body_worker", "Claude Code Builder")
    risk = route.get("risk", "low")
    return (
        f"# Brain Plan\n\n"
        f"**Goal:** {goal}\n"
        f"**Task type:** {task_type}\n"
        f"**Risk level:** {risk}\n\n"
        f"## Plan\n\n"
        f"This plan was generated deterministically. No LLM was called.\n\n"
        f"1. Review REPO_MAP.md to understand the current repo structure.\n"
        f"2. Review PROJECT_BRIEF.md for project type and signals.\n"
        f"3. Check TASK_BREAKDOWN.md for suggested implementation steps.\n"
        f"4. Paste CLAUDE_BUILD_PROMPT.md into {worker}.\n"
        f"5. After {worker} finishes, run TEST_PLAN.md commands.\n"
        f"6. Paste CODEX_REVIEW_PROMPT.md into Codex Reviewer.\n"
        f"7. Get Mohit Supreme Judge approval before committing.\n\n"
        f"## Recommended Worker\n\n"
        f"{worker}\n\n"
        f"## Risk Note\n\n"
        f"Risk level is **{risk}**. "
        + ("Proceed with care. Mohit approval required." if risk == "high" else
           "Standard caution applies. Mohit approval required before commit." if risk == "medium" else
           "Low risk. Mohit approval required before commit.")
        + "\n"
    )


def _project_brief_md(repo: Path, goal: str, signals: dict, timestamp: str) -> str:
    type_lines = []
    if signals.get("is_python"):
        parts = [f for f, k in [("pyproject.toml", "has_pyproject"), ("requirements.txt", "has_requirements"), ("setup.py", "has_setup_py")] if signals.get(k)]
        type_lines.append(f"- Python ({', '.join(parts)})")
    if signals.get("is_node"):
        type_lines.append("- Node.js (package.json)")
    if signals.get("has_git"):
        type_lines.append("- Git repository")
    if signals.get("has_readme"):
        type_lines.append("- README present")
    if signals.get("has_tests_dir"):
        type_lines.append("- tests/ directory")
    if not type_lines:
        type_lines.append("- Unknown (no standard project markers found)")
    project_name = signals.get("python_project_name") or signals.get("node_project_name") or repo.name
    return (
        f"# Project Brief\n\n"
        f"**Repo path:** {repo}\n"
        f"**Goal:** {goal}\n"
        f"**Scanned at:** {timestamp}\n\n"
        f"## Project Type\n\n"
        + "\n".join(type_lines) + "\n\n"
        f"## Project Name\n\n{project_name}\n\n"
        f"## Goal\n\n{goal}\n"
    )


def _repo_map_md(repo: Path, tree: str, signals: dict) -> str:
    important = []
    for fname, desc in [
        ("pyproject.toml", "Python project config"),
        ("requirements.txt", "Python dependencies"),
        ("package.json", "Node.js project config"),
        ("README.md", "Project documentation"),
        (".env.example", "Environment variable template"),
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


def _body_worker_plan_md(goal: str, route: dict) -> str:
    recommended = route.get("body_worker", "Claude Code Builder")
    task_type = route.get("task_type", "build")
    return (
        f"# Body Worker Plan\n\n"
        f"**Goal:** {goal}\n"
        f"**Recommended first worker:** {recommended}\n\n"
        f"## Worker Roles\n\n"
        f"### Claude Code Builder\n"
        f"- Builds, implements, and fixes code\n"
        f"- Reads existing code and writes targeted changes\n"
        f"- Does not commit without approval\n"
        f"- Best for: code/build/fix/implement tasks\n\n"
        f"### OpenCode Plan\n"
        f"- Plans and architectures solutions\n"
        f"- Suggests tools and MCPs (but does not use them yet)\n"
        f"- Outputs TOOL_PLAN and RISK_REPORT\n"
        f"- Best for: plan/design/architecture tasks\n\n"
        f"### OpenCode Build\n"
        f"- Builds with tool access (MCP-aware)\n"
        f"- Only activates with Mohit approval after OpenCode Plan\n"
        f"- Best for: mcp-heavy or tool-requiring tasks\n\n"
        f"### OpenCode Scout\n"
        f"- Researches frameworks, packages, documentation\n"
        f"- Explores codebase without modifying files\n"
        f"- Best for: research/explore/scout tasks\n\n"
        f"### Codex Reviewer\n"
        f"- Senior code review (correctness, scope, tests)\n"
        f"- Does not commit\n"
        f"- Outputs PASS/FAIL verdict\n"
        f"- Best for: review/verify/test tasks\n\n"
        f"### Mohit Supreme Judge\n"
        f"- Final approval for all commits, releases, deploys\n"
        f"- Cannot be bypassed\n"
        f"- Required for: git push, production deploy, schema migration, paid accounts\n\n"
        f"## This Run\n\n"
        f"**Task type:** {task_type}\n\n"
        f"**Who acts first:** {recommended}\n\n"
        f"**Who reviews:** Codex Reviewer\n\n"
        f"**Who approves:** Mohit Supreme Judge (before any commit)\n"
    )


def _tool_policy_md(goal: str) -> str:
    return (
        f"# Tool Policy\n\n"
        f"**Goal:** {goal}\n\n"
        f"## This Run\n\n"
        f"**Tools were NOT executed in this run.**\n"
        f"This folder contains plans and prompts only.\n\n"
        f"## MCP Tools (Hands) — Later\n\n"
        f"MCP tools are Darwin Hands. They are not active in this chunk.\n\n"
        f"When MCP tools are enabled in a future chunk:\n"
        f"- Maximum 3 MCPs active at once\n"
        f"- Maximum 1 risky MCP at a time\n"
        f"- Mohit approval required for any risky MCP\n\n"
        f"## Recommended MCP Categories (for planning only)\n\n"
        f"Based on goal type, these categories may be relevant later:\n"
        f"- File read/write MCPs (safe)\n"
        f"- Search/research MCPs (low risk)\n"
        f"- Browser MCPs (medium risk — requires approval)\n"
        f"- Git MCPs (high risk — requires Mohit approval)\n"
        f"- External account MCPs (high risk — requires Mohit approval)\n\n"
        f"## Hard Rules\n\n"
        f"- No secrets or API keys via tools\n"
        f"- No external account actions\n"
        f"- No git push via tools\n"
        f"- No paid service actions without Mohit approval\n"
    )


def _task_breakdown_md(goal: str, signals: dict, cmds: dict) -> str:
    gl = goal.lower()
    project_name = signals.get("python_project_name") or signals.get("node_project_name") or "unknown"
    test_cmd = ""
    if cmds.get("test"):
        test_cmd = cmds["test"][0]
    elif signals.get("is_python"):
        test_cmd = "python -m pytest"
    elif signals.get("is_node"):
        test_cmd = "npm test"
    else:
        test_cmd = "(determine test command manually)"

    steps = [
        f"1. **Inspect repo** — read REPO_MAP.md and PROJECT_BRIEF.md to understand current state",
        f"2. **Identify target files** — locate the files most likely to change for this goal",
        f"3. **Implement smallest safe change** — make only what is needed for: {goal}",
        f"4. **Run tests** — `{test_cmd}` (or see TEST_PLAN.md)",
        f"5. **Review with Codex** — paste CODEX_REVIEW_PROMPT.md into Codex Reviewer",
        f"6. **Fix if needed** — apply Codex feedback (smallest safe fix only)",
        f"7. **Commit only after Mohit approval** — never commit without Supreme Judge sign-off",
    ]
    return (
        f"# Task Breakdown\n\n"
        f"**Goal:** {goal}\n"
        f"**Project:** {project_name}\n\n"
        f"## Steps\n\n"
        + "\n".join(steps) + "\n\n"
        f"## Scope Constraints\n\n"
        f"- Work only on files directly needed for the goal\n"
        f"- Do not refactor unrelated code\n"
        f"- Do not change tests unless the goal requires it\n"
        f"- Do not add new dependencies unless required\n"
        f"- Do not commit — wait for Mohit approval\n"
    )


def _claude_build_prompt_md(repo: Path, goal: str, signals: dict, cmds: dict, risks: list) -> str:
    project_name = signals.get("python_project_name") or signals.get("node_project_name") or repo.name
    test_cmd = cmds.get("test", ["(see TEST_PLAN.md)"])[0] if cmds.get("test") else "(see TEST_PLAN.md)"
    install_cmd = cmds.get("install", ["(see PROJECT_BRIEF.md)"])[0] if cmds.get("install") else "(see PROJECT_BRIEF.md)"
    risk_lines = "\n".join(f"- {r}" for r in risks[:5])

    type_hint = "Python" if signals.get("is_python") else "Node.js" if signals.get("is_node") else "unknown"

    return (
        f"# Claude Code Build Prompt\n\n"
        f"*Copy and paste this entire prompt into Claude Code.*\n\n"
        f"---\n\n"
        f"## Project\n\n"
        f"- **Path:** `{repo}`\n"
        f"- **Name:** {project_name}\n"
        f"- **Type:** {type_hint}\n"
        f"- **Install:** `{install_cmd}`\n"
        f"- **Test:** `{test_cmd}`\n\n"
        f"## Goal\n\n"
        f"{goal}\n\n"
        f"## Task Breakdown\n\n"
        f"1. Understand the current repo structure (read key files before changing anything)\n"
        f"2. Identify the exact files that need to change for this goal\n"
        f"3. Implement the smallest safe change that achieves the goal\n"
        f"4. Run the test suite and confirm it passes\n"
        f"5. Describe what you changed and why\n\n"
        f"## Known Risks\n\n"
        + risk_lines + "\n\n"
        f"## Strict Scope\n\n"
        f"- Only change files directly needed for the goal above\n"
        f"- Do not refactor unrelated code\n"
        f"- Do not change tests unless required by the goal\n"
        f"- Do not add new dependencies unless required\n"
        f"- Do not add error handling for impossible scenarios\n"
        f"- Do not add comments unless the WHY is non-obvious\n\n"
        f"## Forbidden\n\n"
        f"- Do NOT commit\n"
        f"- Do NOT push to git\n"
        f"- Do NOT modify `.env` or secrets files\n"
        f"- Do NOT add features beyond what the goal requires\n\n"
        f"## Acceptance Criteria\n\n"
        f"- Goal is achieved: {goal}\n"
        f"- Tests pass: `{test_cmd}`\n"
        f"- No unrelated files changed\n"
        f"- No new dependencies added (unless required)\n\n"
        f"## Output Format\n\n"
        f"After completing the task:\n"
        f"1. List every file you changed\n"
        f"2. Explain what you changed and why\n"
        f"3. Show the test output\n"
        f"4. Note anything you are uncertain about\n\n"
        f"---\n\n"
        f"*Generated by Darwin Operator Run. Do not commit without Mohit approval.*\n"
    )


def _opencode_plan_prompt_md(repo: Path, goal: str, signals: dict) -> str:
    project_name = signals.get("python_project_name") or signals.get("node_project_name") or repo.name
    return (
        f"# OpenCode Plan Prompt\n\n"
        f"*Copy and paste this entire prompt into OpenCode in planning mode.*\n\n"
        f"---\n\n"
        f"## Project\n\n"
        f"- **Path:** `{repo}`\n"
        f"- **Name:** {project_name}\n\n"
        f"## Goal\n\n"
        f"{goal}\n\n"
        f"## Your Task (Planning Only)\n\n"
        f"You are in **planning mode only**. Do not edit files or run tools yet.\n\n"
        f"1. Read the project structure and identify relevant files\n"
        f"2. Suggest a tool plan (which tools/MCPs might be needed)\n"
        f"3. Identify risks and unknowns\n"
        f"4. Propose a step-by-step implementation plan\n"
        f"5. Output a TOOL_PLAN and RISK_REPORT\n\n"
        f"## Output Format\n\n"
        f"### TOOL_PLAN\n"
        f"List any tools or MCPs you recommend, with:\n"
        f"- Tool name\n"
        f"- Why needed\n"
        f"- Risk level (low/medium/high)\n\n"
        f"### RISK_REPORT\n"
        f"List risks:\n"
        f"- What could go wrong\n"
        f"- How to mitigate it\n\n"
        f"## Constraints\n\n"
        f"- No file edits in this step\n"
        f"- No dangerous shell commands\n"
        f"- No secrets or API keys\n"
        f"- No commits or git push\n"
        f"- Max 3 MCPs recommended\n"
        f"- Any risky tool requires explicit Mohit approval note\n\n"
        f"---\n\n"
        f"*Generated by Darwin Operator Run. Await Mohit approval before implementation.*\n"
    )


def _codex_review_prompt_md(repo: Path, goal: str, signals: dict, cmds: dict) -> str:
    test_cmd = cmds.get("test", ["(see TEST_PLAN.md)"])[0] if cmds.get("test") else "(see TEST_PLAN.md)"
    project_name = signals.get("python_project_name") or signals.get("node_project_name") or repo.name
    return (
        f"# Codex Review Prompt\n\n"
        f"*Copy and paste this entire prompt into Codex Reviewer.*\n\n"
        f"---\n\n"
        f"## Project\n\n"
        f"- **Path:** `{repo}`\n"
        f"- **Name:** {project_name}\n"
        f"- **Test command:** `{test_cmd}`\n\n"
        f"## Goal That Was Implemented\n\n"
        f"{goal}\n\n"
        f"## Your Task (Senior Code Review)\n\n"
        f"You are a strict senior reviewer. Your job:\n\n"
        f"1. **Check scope** — was anything changed beyond what the goal required?\n"
        f"2. **Run tests** — `{test_cmd}` — do they pass?\n"
        f"3. **Check correctness** — are there logic errors, edge cases, or regressions?\n"
        f"4. **Check style** — does the new code match the existing project style?\n"
        f"5. **Check safety** — any security issues? Any hardcoded secrets?\n\n"
        f"## Output Format\n\n"
        f"### Verdict: PASS or FAIL\n\n"
        f"If PASS:\n"
        f"- Confirm tests pass\n"
        f"- Confirm scope is correct\n"
        f"- Note anything to watch\n\n"
        f"If FAIL:\n"
        f"- List specific issues (one per bullet)\n"
        f"- Suggest the smallest fix for each issue\n"
        f"- Do not suggest unrelated changes\n\n"
        f"## Constraints\n\n"
        f"- Do NOT commit\n"
        f"- Do NOT push to git\n"
        f"- Only suggest fixes for issues found — no scope creep\n"
        f"- If unsure, flag as warning rather than blocking\n\n"
        f"---\n\n"
        f"*Generated by Darwin Operator Run. Mohit reviews verdict before commit.*\n"
    )


def _acceptance_checklist_md(goal: str, cmds: dict) -> str:
    test_cmd = cmds.get("test", ["(see TEST_PLAN.md)"])[0] if cmds.get("test") else "(see TEST_PLAN.md)"
    return (
        f"# Acceptance Checklist\n\n"
        f"**Goal:** {goal}\n\n"
        f"## Before Committing\n\n"
        f"- [ ] Goal achieved: {goal}\n"
        f"- [ ] Tests pass: `{test_cmd}`\n"
        f"- [ ] No unrelated files changed\n"
        f"- [ ] No new dependencies added (unless required)\n"
        f"- [ ] Codex review verdict: PASS\n"
        f"- [ ] Mohit Supreme Judge has approved\n\n"
        f"## After Committing (separately)\n\n"
        f"- [ ] Run full smoke tests\n"
        f"- [ ] Update ROADMAP.md if applicable\n"
        f"- [ ] Update CHANGELOG if applicable\n"
    )


def _test_plan_md(repo: Path, goal: str, signals: dict, cmds: dict) -> str:
    lines = [
        f"# Test Plan\n",
        f"**Goal:** {goal}\n",
        f"## Detected Test Commands\n",
    ]
    if signals.get("is_python"):
        lines.append("### Python\n")
        lines.append("```bash")
        lines.append("python -m compileall src")
        if cmds.get("test"):
            lines.extend(cmds["test"])
        elif signals.get("has_tests_dir"):
            lines.append("python -m pytest")
        else:
            lines.append("# No tests/ directory found — add tests or check manually")
        lines.append("```\n")
    if signals.get("is_node"):
        lines.append("### Node.js\n")
        lines.append("```bash")
        if cmds.get("test"):
            lines.extend(cmds["test"])
        else:
            lines.append("npm test")
        lines.append("```\n")

    is_darwin = _is_darwin_repo(repo)
    if is_darwin:
        lines.append("### Darwin Repo — Run All Smoke Tests\n")
        lines.append("```bash")
        smoke_dir = repo / "scripts"
        if smoke_dir.exists():
            for sh in sorted(smoke_dir.glob("smoke_test_*.sh")):
                lines.append(f"bash scripts/{sh.name}")
            for py in sorted(smoke_dir.glob("smoke_test_*.py")):
                lines.append(f"python scripts/{py.name}")
        else:
            lines.append("# No scripts/ directory found")
        lines.append("```\n")

    if not signals.get("is_python") and not signals.get("is_node") and not is_darwin:
        lines.append("### Manual Checks\n")
        lines.append("No standard project type detected. Verify manually:\n")
        lines.append("- Does the code run without errors?")
        lines.append("- Does it achieve the goal?")
        lines.append("- Are there any regressions?\n")

    lines.append("\n## After Tests\n")
    lines.append("- [ ] All tests pass")
    lines.append("- [ ] No new failures introduced")
    lines.append("- [ ] Paste CODEX_REVIEW_PROMPT.md into Codex Reviewer")

    return "\n".join(lines) + "\n"


def _is_darwin_repo(repo: Path) -> bool:
    return (
        (repo / "src" / "darwin").exists()
        or any(repo.glob("scripts/smoke_test_*.sh"))
    )


def _risks_md(risks: list, goal: str) -> str:
    lines = [
        f"# Risks\n",
        f"**Goal:** {goal}\n",
        f"## Detected Risks\n",
    ]
    lines.extend(f"- [ ] {r}" for r in risks)
    lines.append("\n## Always-On Risks\n")
    lines += [
        "- [ ] Changes may introduce regressions in untested code paths",
        "- [ ] Dependencies may have incompatible versions",
        "- [ ] Committing without Mohit approval",
    ]
    lines.append("\n*Risks detected by static scan — review before coding.*")
    return "\n".join(lines) + "\n"


def _next_action_md(goal: str, route: dict) -> str:
    worker = route.get("body_worker", "Claude Code Builder")
    task_type = route.get("task_type", "build")

    if "Mohit" in worker:
        return (
            f"# Next Action\n\n"
            f"**STOP — Mohit Supreme Judge approval required.**\n\n"
            f"This goal has been classified as high-risk or destructive:\n"
            f"> {goal}\n\n"
            f"Do not proceed until Mohit reviews and approves.\n"
        )

    if "Claude Code" in worker or task_type == "build":
        prompt_file = "CLAUDE_BUILD_PROMPT.md"
        worker_label = "Claude Code"
    elif "OpenCode Plan" in worker or task_type == "planning":
        prompt_file = "OPENCODE_PLAN_PROMPT.md"
        worker_label = "OpenCode (planning mode)"
    elif "Codex" in worker or task_type == "review":
        prompt_file = "CODEX_REVIEW_PROMPT.md"
        worker_label = "Codex Reviewer"
    else:
        prompt_file = "CLAUDE_BUILD_PROMPT.md"
        worker_label = "Claude Code"

    return (
        f"# Next Action\n\n"
        f"**Goal:** {goal}\n\n"
        f"## Step 1 — Paste the build prompt into {worker_label}\n\n"
        f"Open `{prompt_file}` and paste the entire contents into {worker_label}.\n\n"
        f"After {worker_label} finishes:\n"
        f"1. Review what was changed\n"
        f"2. Run TEST_PLAN.md commands to verify\n"
        f"3. Paste CODEX_REVIEW_PROMPT.md into Codex Reviewer\n"
        f"4. Review Codex verdict\n"
        f"5. Get Mohit Supreme Judge approval\n"
        f"6. Only then commit\n\n"
        f"## Files to Use\n\n"
        f"- `{prompt_file}` — paste into {worker_label}\n"
        f"- `CODEX_REVIEW_PROMPT.md` — paste into Codex after build\n"
        f"- `TEST_PLAN.md` — run these tests\n"
        f"- `ACCEPTANCE_CHECKLIST.md` — check before committing\n"
    )


def _trace_md(cmd: str, brain: str, run_dir: Path, run_files: list, timestamp: str) -> str:
    return (
        f"# Trace\n\n"
        f"**Command:** `{cmd}`\n"
        f"**Timestamp:** {timestamp}\n"
        f"**Brain mode:** {brain}\n"
        f"**Run folder:** {run_dir}\n\n"
        f"## Created Files\n\n"
        + "\n".join(f"- {f}" for f in run_files)
        + "\n\n"
        f"## What Was NOT Done\n\n"
        f"- No body workers executed\n"
        f"- No tools executed\n"
        f"- No API keys used or stored\n"
        f"- No files outside `.darwin/runs/` were modified\n"
        f"- No commits or git push\n"
        f"- No external account actions\n\n"
        f"*API key values are never recorded in trace logs.*\n"
    )


# ── Run folder creation ────────────────────────────────────────────────────────


def _make_run_dir(runs_dir: Path, goal_slug: str) -> Path:
    """Create next numbered run folder. Returns the created path."""
    n = 1
    while True:
        candidate = runs_dir / f"{n:03d}-{goal_slug}"
        if not candidate.exists():
            candidate.mkdir(parents=True)
            return candidate
        n += 1


def op_operate_existing(repo_path: Path, goal: str, brain: str = "off") -> dict:
    """Create a Darwin operator run packet for an existing repo. No workers/tools executed."""
    brain = brain.lower().strip()
    valid_modes = {"off", "auto", "groq", "openrouter", "poolside", "nvidia"}
    if brain not in valid_modes:
        return {"error": f"invalid brain mode '{brain}'. Valid: {', '.join(sorted(valid_modes))}"}

    repo = repo_path.resolve() if not repo_path.is_absolute() else repo_path
    if not repo.exists():
        return {"error": f"repo path not found: {repo_path}"}
    if not repo.is_dir():
        return {"error": f"repo path is a file, not a folder: {repo_path}"}

    timestamp = now()
    goal_slug = slug(goal, max_len=40)

    # Gather repo signals (reuse repo_intake_ops)
    signals = _detect_project_signals(repo)
    tree = _build_repo_tree(repo)
    cmds = _detect_commands(repo, signals)
    risks = _detect_risks(repo, signals)

    # Route
    route = op_brain_route(goal, brain=brain)

    # Create run folder inside target repo
    runs_dir = repo / ".darwin" / "runs"
    runs_dir.mkdir(parents=True, exist_ok=True)
    run_dir = _make_run_dir(runs_dir, goal_slug)

    run_files = [
        "RUN_SUMMARY.md",
        "BRAIN_ROUTE.md",
        "BRAIN_PLAN.md",
        "PROJECT_BRIEF.md",
        "REPO_MAP.md",
        "BODY_WORKER_PLAN.md",
        "TOOL_POLICY.md",
        "TASK_BREAKDOWN.md",
        "CLAUDE_BUILD_PROMPT.md",
        "OPENCODE_PLAN_PROMPT.md",
        "CODEX_REVIEW_PROMPT.md",
        "ACCEPTANCE_CHECKLIST.md",
        "TEST_PLAN.md",
        "RISKS.md",
        "NEXT_ACTION.md",
        "TRACE.md",
    ]

    cmd_str = f"darwin operate-existing {repo_path} --goal \"{goal}\" --brain {brain}"

    content_map = {
        "BRAIN_ROUTE.md": _brain_route_md(route, brain),
        "BRAIN_PLAN.md": _brain_plan_md(goal, route),
        "PROJECT_BRIEF.md": _project_brief_md(repo, goal, signals, timestamp),
        "REPO_MAP.md": _repo_map_md(repo, tree, signals),
        "BODY_WORKER_PLAN.md": _body_worker_plan_md(goal, route),
        "TOOL_POLICY.md": _tool_policy_md(goal),
        "TASK_BREAKDOWN.md": _task_breakdown_md(goal, signals, cmds),
        "CLAUDE_BUILD_PROMPT.md": _claude_build_prompt_md(repo, goal, signals, cmds, risks),
        "OPENCODE_PLAN_PROMPT.md": _opencode_plan_prompt_md(repo, goal, signals),
        "CODEX_REVIEW_PROMPT.md": _codex_review_prompt_md(repo, goal, signals, cmds),
        "ACCEPTANCE_CHECKLIST.md": _acceptance_checklist_md(goal, cmds),
        "TEST_PLAN.md": _test_plan_md(repo, goal, signals, cmds),
        "RISKS.md": _risks_md(risks, goal),
        "NEXT_ACTION.md": _next_action_md(goal, route),
        "TRACE.md": _trace_md(cmd_str, brain, run_dir, run_files, timestamp),
    }

    # Write all files except RUN_SUMMARY (needs file list first)
    created = []
    for fname in run_files:
        if fname == "RUN_SUMMARY.md":
            continue
        (run_dir / fname).write_text(content_map[fname])
        created.append(fname)

    # Write RUN_SUMMARY last (includes file list)
    summary_content = _run_summary(repo, goal, brain, route, run_dir, run_files)
    (run_dir / "RUN_SUMMARY.md").write_text(summary_content)
    created.insert(0, "RUN_SUMMARY.md")

    return {
        "repo": str(repo),
        "goal": goal,
        "brain": brain,
        "run_dir": str(run_dir),
        "created": run_files,
        "route": route,
    }
