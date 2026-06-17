"""Spec Surface operations — spec-init, spec-status."""

import re
import sys
from pathlib import Path

from darwin.common import now
from darwin.status_ops import op_version


def _make_spec_surface_md(
    project_name: str, version: str, level: int, level_label: str, timestamp: str
) -> str:
    return (
        "# Darwin Spec Surface V0\n\n"
        f"**Project:** {project_name}\n"
        f"**Darwin version:** {version}\n"
        f"**Darwin level:** {level} — {level_label}\n"
        f"**Generated at:** {timestamp}\n\n"
        "No Darwin feature is trusted unless protected by a smoke test or eval.\n\n"
        "---\n\n"
        "## Supported Command Groups\n\n"
        "### Chunk OS\n\n"
        "- `darwin init`\n"
        "- `darwin split-plan`\n"
        "- `darwin prepare-chunk`\n"
        "- `darwin record-result`\n"
        "- `darwin review-chunk`\n"
        "- `darwin update-memory`\n"
        "- `darwin next-chunk`\n\n"
        "### MCP Entry Point\n\n"
        "- `darwin-mcp` (9 Chunk OS tools)\n\n"
        "### Eval Harness\n\n"
        "- `darwin eval-init`\n"
        "- `darwin eval-list`\n"
        "- `darwin eval-run`\n"
        "- `darwin eval-report`\n\n"
        "### Existing Repo Intake\n\n"
        '- `darwin inspect-repo <repo_path> --goal "<goal>"`\n\n'
        "### Status / Doctor / Version\n\n"
        "- `darwin version`\n"
        "- `darwin status`\n"
        "- `darwin doctor`\n\n"
        "### Spec Surface\n\n"
        "- `darwin spec-init`\n"
        "- `darwin spec-status`\n\n"
        "### Feature Registry\n\n"
        "- `darwin feature-init`\n"
        "- `darwin feature-list`\n"
        "- `darwin feature-status`\n\n"
        "### Worker Registry\n\n"
        "- `darwin worker-init`\n"
        "- `darwin worker-list`\n"
        '- `darwin worker-suggest --goal "<goal>"`\n\n'
        "### Batch Planner\n\n"
        '- `darwin batch-plan --goal "<goal>" --max-items 7`\n\n'
        "---\n\n"
        "## What Darwin Does NOT Support Yet\n\n"
        "- /new project mode\n"
        "- Prompt Darwin\n"
        "- Research Darwin\n"
        "- Context Darwin\n"
        "- Judge System\n"
        "- Production Readiness\n"
        "- Git Safety / self-upgrade\n"
        "- A2A\n"
        "- Background daemon\n"
        "- Dashboard / database\n"
    )


def _make_scenarios_md() -> str:
    return (
        "# Protected User Scenarios\n\n"
        "## 1. User initializes workspace\n\n"
        "**Command:** `darwin init`  \n"
        "**Smoke test:** `scripts/smoke_test_chunk_os.sh`\n\n"
        "## 2. User splits plan into chunks\n\n"
        "**Command:** `darwin split-plan MASTER_PLAN.md`  \n"
        "**Smoke test:** `scripts/smoke_test_chunk_os.sh`\n\n"
        "## 3. User prepares chunk\n\n"
        "**Command:** `darwin prepare-chunk chunks/NNN-name`  \n"
        "**Smoke test:** `scripts/smoke_test_chunk_os.sh`\n\n"
        "## 4. User records and reviews result\n\n"
        "**Commands:** `darwin record-result`, `darwin review-chunk`  \n"
        "**Smoke test:** `scripts/smoke_test_chunk_os.sh`\n\n"
        "## 5. User updates memory and asks next chunk\n\n"
        "**Commands:** `darwin update-memory`, `darwin next-chunk`  \n"
        "**Smoke test:** `scripts/smoke_test_chunk_os.sh`\n\n"
        "## 6. User runs eval harness\n\n"
        "**Commands:** `darwin eval-init`, `darwin eval-list`, `darwin eval-run`, `darwin eval-report`  \n"
        "**Smoke test:** `scripts/smoke_test_eval_harness.sh`\n\n"
        "## 7. User inspects existing repo\n\n"
        '**Command:** `darwin inspect-repo <repo_path> --goal "<goal>"`  \n'
        "**Smoke test:** `scripts/smoke_test_repo_intake.sh`\n\n"
        "## 8. User checks status / doctor / version\n\n"
        "**Commands:** `darwin version`, `darwin status`, `darwin doctor`  \n"
        "**Smoke test:** `scripts/smoke_test_status_doctor.sh`\n\n"
        "## 9. User views spec surface\n\n"
        "**Commands:** `darwin spec-init`, `darwin spec-status`  \n"
        "**Smoke test:** `scripts/smoke_test_spec_surface.sh`\n\n"
        "## 10. User initializes feature registry\n\n"
        "**Commands:** `darwin feature-init`, `darwin feature-list`, `darwin feature-status`  \n"
        "**Smoke test:** `scripts/smoke_test_fast_track_bundle.sh`\n\n"
        "## 11. User initializes worker registry\n\n"
        "**Commands:** `darwin worker-init`, `darwin worker-list`, `darwin worker-suggest`  \n"
        "**Smoke test:** `scripts/smoke_test_fast_track_bundle.sh`\n\n"
        "## 12. User runs batch planner\n\n"
        "**Command:** `darwin batch-plan --goal \"...\" --max-items 7`  \n"
        "**Smoke test:** `scripts/smoke_test_fast_track_bundle.sh`\n"
    )


def _make_protected_commands_md() -> str:
    rows = [
        ("darwin init", "scripts/smoke_test_chunk_os.sh"),
        ("darwin split-plan", "scripts/smoke_test_chunk_os.sh"),
        ("darwin prepare-chunk", "scripts/smoke_test_chunk_os.sh"),
        ("darwin record-result", "scripts/smoke_test_chunk_os.sh"),
        ("darwin review-chunk", "scripts/smoke_test_chunk_os.sh"),
        ("darwin update-memory", "scripts/smoke_test_chunk_os.sh"),
        ("darwin next-chunk", "scripts/smoke_test_chunk_os.sh"),
        ("darwin eval-init", "scripts/smoke_test_eval_harness.sh"),
        ("darwin eval-list", "scripts/smoke_test_eval_harness.sh"),
        ("darwin eval-run", "scripts/smoke_test_eval_harness.sh"),
        ("darwin eval-report", "scripts/smoke_test_eval_harness.sh"),
        ("darwin inspect-repo", "scripts/smoke_test_repo_intake.sh"),
        ("darwin version", "scripts/smoke_test_status_doctor.sh"),
        ("darwin status", "scripts/smoke_test_status_doctor.sh"),
        ("darwin doctor", "scripts/smoke_test_status_doctor.sh"),
        ("darwin spec-init", "scripts/smoke_test_spec_surface.sh"),
        ("darwin spec-status", "scripts/smoke_test_spec_surface.sh"),
        ("darwin tool-init", "scripts/smoke_test_tool_registry.sh"),
        ("darwin tool-list", "scripts/smoke_test_tool_registry.sh"),
        ("darwin tool-suggest", "scripts/smoke_test_tool_registry.sh"),
        ("darwin feature-init", "scripts/smoke_test_fast_track_bundle.sh"),
        ("darwin feature-list", "scripts/smoke_test_fast_track_bundle.sh"),
        ("darwin feature-status", "scripts/smoke_test_fast_track_bundle.sh"),
        ("darwin worker-init", "scripts/smoke_test_fast_track_bundle.sh"),
        ("darwin worker-list", "scripts/smoke_test_fast_track_bundle.sh"),
        ("darwin worker-suggest", "scripts/smoke_test_fast_track_bundle.sh"),
        ("darwin batch-plan", "scripts/smoke_test_fast_track_bundle.sh"),
        ("darwin-mcp", "scripts/smoke_test_mcp_tools.py"),
        ("python scripts/smoke_test_mcp_tools.py", "scripts/smoke_test_mcp_tools.py"),
    ]
    header = "# Protected Commands\n\n| Command | Smoke Test |\n|---|---|\n"
    rows_str = "".join(f"| `{cmd}` | `{test}` |\n" for cmd, test in rows)
    return header + rows_str


def op_spec_init(base: Path) -> dict:
    spec_dir = base / ".darwin" / "spec"
    spec_dir.mkdir(parents=True, exist_ok=True)
    project_name = "unknown"
    pyproject = base / "pyproject.toml"
    if pyproject.exists():
        try:
            m = re.search(
                r'^name\s*=\s*["\']([^"\']+)["\']', pyproject.read_text(), re.MULTILINE
            )
            if m:
                project_name = m.group(1)
        except Exception:
            pass
    version = op_version()["version"]
    _core = sys.modules.get("darwin.core")
    level = 0
    if _core and hasattr(_core, "op_prepare_chunk"):
        level = 1
    try:
        import darwin.mcp_server  # noqa: F401
        level = max(level, 2)
    except ImportError:
        pass
    if _core and hasattr(_core, "op_eval_init"):
        level = max(level, 3)
    if _core and hasattr(_core, "op_inspect_repo"):
        level = max(level, 4)
    _level_labels = {
        0: "none",
        1: "Chunk OS V1",
        2: "Chunk MCP",
        3: "Eval Harness V0",
        4: "Existing Repo Intake V0",
        5: "Spec Surface V0",
    }
    level_label = _level_labels.get(level, "unknown")
    timestamp = now()
    spec_files = {
        "SPEC_SURFACE.md": _make_spec_surface_md(project_name, version, level, level_label, timestamp),
        "SCENARIOS.md": _make_scenarios_md(),
        "PROTECTED_COMMANDS.md": _make_protected_commands_md(),
    }
    created = []
    existing = []
    for filename, content in spec_files.items():
        path = spec_dir / filename
        if path.exists():
            existing.append(filename)
        else:
            path.write_text(content)
            created.append(filename)
    return {"spec_dir": str(spec_dir), "created": created, "existing": existing}


def op_spec_status(base: Path) -> dict:
    spec_dir = base / ".darwin" / "spec"
    if not spec_dir.exists():
        return {
            "initialized": False,
            "message": "Spec not initialized. Run `darwin spec-init` to create .darwin/spec/.",
        }
    file_names = ["SPEC_SURFACE.md", "SCENARIOS.md", "PROTECTED_COMMANDS.md"]
    files = {fname: (spec_dir / fname).exists() for fname in file_names}
    protected_count = 0
    pc_path = spec_dir / "PROTECTED_COMMANDS.md"
    if pc_path.exists():
        for line in pc_path.read_text().splitlines():
            if line.startswith("| `darwin") or line.startswith("| `python"):
                protected_count += 1
    return {
        "initialized": True,
        "spec_dir": str(spec_dir),
        "files": files,
        "protected_command_count": protected_count,
    }
