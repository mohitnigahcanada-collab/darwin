"""Status, Doctor, and Version operations."""

import sys
from pathlib import Path


def _find_metadata_yaml(base: Path) -> bool:
    _skip = frozenset([".venv", "__pycache__", ".git", "node_modules", "dist", "build"])
    stack = [base]
    while stack:
        current = stack.pop()
        try:
            for item in current.iterdir():
                if item.is_dir() and item.name not in _skip:
                    stack.append(item)
                elif item.is_file() and item.name == "metadata.yaml":
                    return True
        except PermissionError:
            continue
    return False


def op_version() -> dict:
    v = "unknown"
    try:
        from importlib.metadata import version as _imv
        v = _imv("darwin")
    except Exception:
        pass
    if v == "unknown":
        try:
            from darwin import __version__ as _ver
            v = _ver
        except Exception:
            pass
    return {"version": v}


def op_status(base: Path) -> dict:
    dirs = {
        "chunks/": (base / "chunks").exists(),
        "memory/": (base / "memory").exists(),
        "evals/": (base / "evals").exists(),
        ".darwin/": (base / ".darwin").exists(),
        ".darwin/spec/": (base / ".darwin" / "spec").exists(),
        ".darwin/tools/": (base / ".darwin" / "tools").exists(),
        ".darwin/features/": (base / ".darwin" / "features").exists(),
        ".darwin/workers/": (base / ".darwin" / "workers").exists(),
        ".darwin/brain/": (base / ".darwin" / "brain").exists(),
        ".darwin/runs/": (base / ".darwin" / "runs").exists(),
        "scripts/": (base / "scripts").exists(),
    }
    files = {
        "pyproject.toml": (base / "pyproject.toml").exists(),
        "README.md": (base / "README.md").exists(),
    }
    smoke_tests = {
        "scripts/smoke_test_chunk_os.sh": (base / "scripts" / "smoke_test_chunk_os.sh").exists(),
        "scripts/smoke_test_mcp_tools.py": (base / "scripts" / "smoke_test_mcp_tools.py").exists(),
        "scripts/smoke_test_eval_harness.sh": (base / "scripts" / "smoke_test_eval_harness.sh").exists(),
        "scripts/smoke_test_repo_intake.sh": (base / "scripts" / "smoke_test_repo_intake.sh").exists(),
        "scripts/smoke_test_status_doctor.sh": (base / "scripts" / "smoke_test_status_doctor.sh").exists(),
        "scripts/smoke_test_spec_surface.sh": (base / "scripts" / "smoke_test_spec_surface.sh").exists(),
        "scripts/smoke_test_tool_registry.sh": (base / "scripts" / "smoke_test_tool_registry.sh").exists(),
        "scripts/smoke_test_fast_track_bundle.sh": (base / "scripts" / "smoke_test_fast_track_bundle.sh").exists(),
        "scripts/smoke_test_multi_brain_operator.sh": (base / "scripts" / "smoke_test_multi_brain_operator.sh").exists(),
    }
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
    }
    level_label = _level_labels.get(level, "unknown")
    return {
        "cwd": str(base.resolve()),
        "has_git": (base / ".git").exists(),
        "dirs": dirs,
        "files": files,
        "smoke_tests": smoke_tests,
        "darwin_level": level,
        "darwin_level_label": level_label,
    }


def op_doctor(base: Path) -> list:
    checks: list = []

    def _chk(name: str, status: str, detail: str = "") -> None:
        checks.append({"check": name, "status": status, "detail": detail})

    vi = sys.version_info
    py_str = f"{vi.major}.{vi.minor}.{vi.micro}"
    if vi >= (3, 9):
        _chk(f"Python {py_str}", "PASS", ">= 3.9")
    else:
        _chk(f"Python {py_str}", "FAIL", "3.9+ required")

    try:
        import darwin as _d  # noqa: F401
        _chk("darwin package importable", "PASS")
    except ImportError as exc:
        _chk("darwin package importable", "FAIL", str(exc))

    try:
        import typer as _t  # noqa: F401
        _chk("typer importable", "PASS")
    except ImportError as exc:
        _chk("typer importable", "FAIL", str(exc))

    try:
        from importlib.metadata import entry_points as _eps
        names = [ep.name for ep in _eps(group="console_scripts")]
        if "darwin" in names:
            _chk("darwin CLI entry point", "PASS")
        else:
            _chk("darwin CLI entry point", "WARN", "not in metadata — run: pip install -e .")
    except Exception as exc:
        _chk("darwin CLI entry point", "WARN", str(exc))

    try:
        from mcp.server.fastmcp import FastMCP as _F  # noqa: F401
        _chk("MCP SDK (optional)", "PASS", "mcp[cli] installed")
    except ImportError:
        _chk("MCP SDK (optional)", "WARN", "not installed — run: pip install darwin[mcp]")

    for script in [
        "scripts/smoke_test_chunk_os.sh",
        "scripts/smoke_test_mcp_tools.py",
        "scripts/smoke_test_eval_harness.sh",
        "scripts/smoke_test_repo_intake.sh",
        "scripts/smoke_test_status_doctor.sh",
        "scripts/smoke_test_spec_surface.sh",
        "scripts/smoke_test_tool_registry.sh",
        "scripts/smoke_test_fast_track_bundle.sh",
        "scripts/smoke_test_multi_brain_operator.sh",
    ]:
        if (base / script).exists():
            _chk(script, "PASS", "found")
        else:
            _chk(script, "WARN", "not found in current directory")

    _core = sys.modules.get("darwin.core")
    for op_name, label in [
        ("op_prepare_chunk", "Chunk OS"),
        ("op_eval_init", "Eval Harness"),
        ("op_inspect_repo", "Repo Intake"),
        ("op_spec_init", "Spec Surface"),
        ("op_tool_init", "Tool Registry"),
        ("op_tool_list", "Tool Registry"),
        ("op_tool_suggest", "Tool Registry"),
        ("op_feature_init", "Feature Registry"),
        ("op_feature_list", "Feature Registry"),
        ("op_feature_status", "Feature Registry"),
        ("op_worker_init", "Worker Registry"),
        ("op_worker_list", "Worker Registry"),
        ("op_worker_suggest", "Worker Registry"),
        ("op_batch_plan", "Batch Planner"),
        ("op_brain_init", "Multi-Brain Operator"),
        ("op_brain_status", "Multi-Brain Operator"),
        ("op_brain_route", "Multi-Brain Operator"),
        ("op_operate_existing", "Multi-Brain Operator"),
    ]:
        if _core and hasattr(_core, op_name):
            _chk(f"{op_name} ({label})", "PASS")
        else:
            _chk(f"{op_name} ({label})", "FAIL", "not found in darwin.core")

    darwin_dir = base / ".darwin"
    spec_dir = base / ".darwin" / "spec"
    if darwin_dir.exists() and not spec_dir.exists():
        _chk(".darwin/spec/", "WARN", "not found — run: darwin spec-init")
    elif spec_dir.exists():
        _chk(".darwin/spec/", "PASS", "found")

    tools_dir = base / ".darwin" / "tools"
    if darwin_dir.exists() and not tools_dir.exists():
        _chk(".darwin/tools/", "WARN", "not found — run: darwin tool-init")
    elif tools_dir.exists():
        _chk(".darwin/tools/", "PASS", "found")

    features_dir = base / ".darwin" / "features"
    if darwin_dir.exists() and not features_dir.exists():
        _chk(".darwin/features/", "WARN", "not found — run: darwin feature-init")
    elif features_dir.exists():
        _chk(".darwin/features/", "PASS", "found")

    workers_dir = base / ".darwin" / "workers"
    if darwin_dir.exists() and not workers_dir.exists():
        _chk(".darwin/workers/", "WARN", "not found — run: darwin worker-init")
    elif workers_dir.exists():
        _chk(".darwin/workers/", "PASS", "found")

    brain_dir = base / ".darwin" / "brain"
    if darwin_dir.exists() and not brain_dir.exists():
        _chk(".darwin/brain/", "WARN", "not found — run: darwin brain-init")
    elif brain_dir.exists():
        _chk(".darwin/brain/", "PASS", "found")

    if _find_metadata_yaml(base):
        _chk("No metadata.yaml", "FAIL", "metadata.yaml found — remove it")
    else:
        _chk("No metadata.yaml", "PASS")

    return checks
