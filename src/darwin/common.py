"""Shared constants and pure helpers used across Darwin modules."""
import re
from datetime import datetime
from pathlib import Path

# ── Chunk OS constants ─────────────────────────────────────────────────────────

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

# ── Shared risk ordering (used by registries) ──────────────────────────────────

RISK_ORDER = {"low": 0, "medium": 1, "high": 2}

# ── Pure helpers ───────────────────────────────────────────────────────────────


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


def parse_card_field(text: str, heading: str) -> str:
    """Return first non-empty non-heading line after `## heading` in a card file."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if line.strip() == f"## {heading}":
            for j in range(i + 1, len(lines)):
                stripped = lines[j].strip()
                if stripped and not stripped.startswith("#"):
                    return stripped
    return "unknown"
