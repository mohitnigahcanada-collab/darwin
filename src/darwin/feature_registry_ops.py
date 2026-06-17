"""Feature Registry operations — feature-init, feature-list, feature-status."""

from pathlib import Path

from darwin.common import write_if_missing

_FEATURES_MD = """\
# Darwin Feature Registry V0

## Features

| Feature | Status | Smoke Test |
|---|---|---|
| Chunk OS V1 | complete | scripts/smoke_test_chunk_os.sh |
| Chunk MCP wrapper | complete | scripts/smoke_test_mcp_tools.py |
| Eval Harness V0 | complete | scripts/smoke_test_eval_harness.sh |
| Existing Repo Intake V0 | complete | scripts/smoke_test_repo_intake.sh |
| Status / Doctor / Version | complete | scripts/smoke_test_status_doctor.sh |
| Spec Surface V0 | complete | scripts/smoke_test_spec_surface.sh |
| Tool Registry V0 | complete | scripts/smoke_test_tool_registry.sh |
| Feature Registry V0 | complete | scripts/smoke_test_fast_track_bundle.sh |
| Worker Registry V0 | complete | scripts/smoke_test_fast_track_bundle.sh |
| Batch Planner / Speed Lane V0 | complete | scripts/smoke_test_fast_track_bundle.sh |
"""

_COMMANDS_MD = """\
# Darwin Command Registry

## All Known Commands

### Chunk OS
- darwin init
- darwin split-plan
- darwin prepare-chunk
- darwin record-result
- darwin review-chunk
- darwin update-memory
- darwin next-chunk

### MCP
- darwin-mcp

### Eval Harness
- darwin eval-init
- darwin eval-list
- darwin eval-run
- darwin eval-report

### Repo Intake
- darwin inspect-repo

### Status / Doctor / Version
- darwin version
- darwin status
- darwin doctor

### Spec Surface
- darwin spec-init
- darwin spec-status

### Tool Registry
- darwin tool-init
- darwin tool-list
- darwin tool-suggest

### Feature Registry
- darwin feature-init
- darwin feature-list
- darwin feature-status

### Worker Registry
- darwin worker-init
- darwin worker-list
- darwin worker-suggest

### Batch Planner
- darwin batch-plan
"""

_COVERAGE_MD = """\
# Darwin Smoke Test Coverage

## Command Groups → Smoke Tests

| Command Group | Smoke Test |
|---|---|
| Chunk OS | scripts/smoke_test_chunk_os.sh |
| MCP tools | scripts/smoke_test_mcp_tools.py |
| Eval Harness | scripts/smoke_test_eval_harness.sh |
| Repo Intake | scripts/smoke_test_repo_intake.sh |
| Status/Doctor | scripts/smoke_test_status_doctor.sh |
| Spec Surface | scripts/smoke_test_spec_surface.sh |
| Tool Registry | scripts/smoke_test_tool_registry.sh |
| Fast Track Bundle (Feature/Worker/Batch) | scripts/smoke_test_fast_track_bundle.sh |
"""


def op_feature_init(base: Path) -> dict:
    features_dir = base / ".darwin" / "features"
    features_dir.mkdir(parents=True, exist_ok=True)
    files = {
        "FEATURES.md": _FEATURES_MD,
        "COMMANDS.md": _COMMANDS_MD,
        "COVERAGE.md": _COVERAGE_MD,
    }
    created = []
    existing = []
    for filename, content in files.items():
        status = write_if_missing(features_dir / filename, content)
        if status == "created":
            created.append(filename)
        else:
            existing.append(filename)
    return {
        "features_dir": str(features_dir),
        "created": created,
        "existing": existing,
    }


def op_feature_list(base: Path) -> dict:
    features_dir = base / ".darwin" / "features"
    if not features_dir.exists():
        return {
            "initialized": False,
            "message": "Feature registry not initialized. Run: darwin feature-init",
        }
    files = sorted(f.name for f in features_dir.iterdir() if f.is_file() and f.suffix == ".md")
    feature_count = 0
    features_path = features_dir / "FEATURES.md"
    if features_path.exists():
        for line in features_path.read_text().splitlines():
            if line.startswith("| ") and "complete" in line.lower():
                feature_count += 1
    return {
        "initialized": True,
        "features_dir": str(features_dir),
        "files": files,
        "feature_count": feature_count,
    }


def op_feature_status(base: Path) -> dict:
    features_dir = base / ".darwin" / "features"
    if not features_dir.exists():
        return {
            "initialized": False,
            "message": "Feature registry not initialized. Run: darwin feature-init",
        }
    file_names = ["FEATURES.md", "COMMANDS.md", "COVERAGE.md"]
    files = {fname: (features_dir / fname).exists() for fname in file_names}
    command_count = 0
    commands_path = features_dir / "COMMANDS.md"
    if commands_path.exists():
        for line in commands_path.read_text().splitlines():
            if line.startswith("- darwin"):
                command_count += 1
    smoke_count = 0
    coverage_path = features_dir / "COVERAGE.md"
    if coverage_path.exists():
        for line in coverage_path.read_text().splitlines():
            if "smoke_test_" in line and "|" in line:
                smoke_count += 1
    return {
        "initialized": True,
        "features_dir": str(features_dir),
        "files": files,
        "command_count": command_count,
        "smoke_test_count": smoke_count,
    }
