#!/usr/bin/env python3
"""
Smoke test for MCP tool functions.
Tests darwin.core operations directly — no MCP client needed.
Run with:  python scripts/smoke_test_mcp_tools.py
"""

import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from darwin.core import (
    INIT_DIRS,
    INIT_FILES,
    op_get_file,
    op_list_chunks,
    op_next_chunk,
    op_prepare_chunk,
    op_read_chunk_files,
    op_record_result,
    op_review_chunk,
    op_update_memory,
    slug,
    write_if_missing,
)

PASS = 0
FAIL = 0


def ok(msg: str) -> None:
    global PASS
    PASS += 1
    print(f"  PASS: {msg}")


def fail(msg: str) -> None:
    global FAIL
    FAIL += 1
    print(f"  FAIL: {msg}", file=sys.stderr)


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def setup_workspace(base: Path) -> Path:
    """Create a minimal Darwin workspace with two chunks."""
    for d in INIT_DIRS:
        (base / d).mkdir(parents=True, exist_ok=True)
    for name, content in INIT_FILES.items():
        write_if_missing(base / name, content)

    tasks = ["First task", "Second task"]
    roadmap_lines = ["# Roadmap", "", "## Pending Tasks", ""]
    for i, task in enumerate(tasks, 1):
        num = f"{i:03d}"
        folder = base / "chunks" / f"{num}-{slug(task)}"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "TASK.md").write_text(
            f"# Chunk {num}\n\n**Task:** {task}\n**Status:** pending\n"
        )
        roadmap_lines.append(f"- [ ] {num} — {task} — `chunks/{num}-{slug(task)}/`")
    (base / "ROADMAP.md").write_text("\n".join(roadmap_lines) + "\n")
    return base


with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    setup_workspace(base)

    # ── list_chunks ───────────────────────────────────────────────────────────
    section("list_chunks")
    chunks = op_list_chunks(base)
    if len(chunks) == 2:
        ok(f"returns {len(chunks)} chunks")
    else:
        fail(f"expected 2 chunks, got {len(chunks)}")
    if chunks[0]["task"] == "First task":
        ok("first chunk has correct task text")
    else:
        fail(f"first chunk task: {chunks[0].get('task')}")

    # ── next_chunk ────────────────────────────────────────────────────────────
    section("next_chunk (before any pass)")
    result = op_next_chunk(base)
    if "error" not in result and "001" in (result.get("path") or ""):
        ok("next_chunk returns first chunk")
    else:
        fail(f"unexpected result: {result}")

    # ── prepare_chunk ─────────────────────────────────────────────────────────
    section("prepare_chunk")
    chunk_rel = f"chunks/001-{slug('First task')}"
    result = op_prepare_chunk(base, chunk_rel)
    if "error" in result:
        fail(f"prepare_chunk error: {result['error']}")
    else:
        created = [k for k, v in result["files"].items() if v == "created"]
        if len(created) == 6:
            ok(f"created {len(created)} files: {', '.join(created)}")
        else:
            fail(f"expected 6 created files, got {len(created)}: {created}")

    # ── read_chunk_files ──────────────────────────────────────────────────────
    section("read_chunk_files")
    result = op_read_chunk_files(base, chunk_rel)
    if "error" in result:
        fail(f"read_chunk_files error: {result['error']}")
    else:
        files = result["files"]
        if "TASK.md" in files and "STEP.md" in files:
            ok(f"returned {len(files)} files including TASK.md and STEP.md")
        else:
            fail(f"missing expected files, got: {list(files.keys())}")

    # ── get_builder_prompt ────────────────────────────────────────────────────
    section("get_builder_prompt")
    result = op_get_file(base, chunk_rel, "CLAUDE_PROMPT.md")
    if "error" in result:
        fail(f"get_builder_prompt error: {result['error']}")
    elif "Claude Prompt" in result.get("content", ""):
        ok("CLAUDE_PROMPT.md content returned")
    else:
        fail("CLAUDE_PROMPT.md content missing expected header")

    # ── get_review_prompt ─────────────────────────────────────────────────────
    section("get_review_prompt")
    result = op_get_file(base, chunk_rel, "CODEX_REVIEW_PROMPT.md")
    if "error" in result:
        fail(f"get_review_prompt error: {result['error']}")
    elif "PASS" in result.get("content", "") or "Codex Review" in result.get("content", ""):
        ok("CODEX_REVIEW_PROMPT.md content returned")
    else:
        fail("CODEX_REVIEW_PROMPT.md content missing expected text")

    # ── record_result ─────────────────────────────────────────────────────────
    section("record_result")
    result = op_record_result(base, chunk_rel, "pass", "smoke test pass")
    if result.get("action") == "created":
        ok("RESULT.md created on first call")
    else:
        fail(f"unexpected action: {result}")
    result2 = op_record_result(base, chunk_rel, "pass", "second entry")
    if result2.get("action") == "appended":
        ok("RESULT.md appended on second call")
    else:
        fail(f"expected appended, got: {result2}")
    bad = op_record_result(base, chunk_rel, "invalid", "x")
    if "error" in bad:
        ok("invalid status returns error dict")
    else:
        fail("invalid status should return error")

    # ── review_chunk ──────────────────────────────────────────────────────────
    section("review_chunk")
    result = op_review_chunk(base, chunk_rel)
    if result.get("verdict") == "PASS":
        ok("review_chunk returns PASS when all files present")
    else:
        fail(f"expected PASS, got: {result}")
    result2 = op_review_chunk(base, chunk_rel)
    if result2.get("action") == "appended":
        ok("REVIEW.md appended on second call")
    else:
        fail(f"expected appended, got: {result2}")

    # ── update_memory (pass) ──────────────────────────────────────────────────
    section("update_memory (pass)")
    result = op_update_memory(base, chunk_rel)
    if result.get("is_pass"):
        ok("update_memory detects pass correctly")
    else:
        fail(f"expected is_pass=True, got: {result}")
    if (base / "memory/winners.md").read_text().__contains__("first-task"):
        ok("winners.md updated")
    else:
        fail("winners.md not updated")
    if (base / "ROADMAP.md").read_text().__contains__("[x]"):
        ok("ROADMAP.md marked [x]")
    else:
        fail("ROADMAP.md not marked")

    # ── next_chunk advances after pass ────────────────────────────────────────
    section("next_chunk (after 001 marked done)")
    result = op_next_chunk(base)
    if "002" in (result.get("path") or ""):
        ok("next_chunk advances to chunk 002")
    else:
        fail(f"expected 002, got: {result}")

    # ── update_memory (fail) ──────────────────────────────────────────────────
    section("update_memory (fail)")
    chunk2_rel = f"chunks/002-{slug('Second task')}"
    op_prepare_chunk(base, chunk2_rel)
    op_record_result(base, chunk2_rel, "fail", "smoke fail test")
    op_review_chunk(base, chunk2_rel)
    result = op_update_memory(base, chunk2_rel)
    if not result.get("is_pass"):
        ok("update_memory detects fail correctly")
    else:
        fail("expected is_pass=False")
    if (base / "memory/mistakes.md").read_text().__contains__("second-task"):
        ok("mistakes.md updated")
    else:
        fail("mistakes.md not updated")
    roadmap_text = (base / "ROADMAP.md").read_text()
    chunk2_line = next((l for l in roadmap_text.splitlines() if "second-task" in l), "")
    if "- [ ]" in chunk2_line:
        ok("failed chunk not marked [x] in ROADMAP.md")
    else:
        fail(f"roadmap line unexpected: {chunk2_line!r}")

    # ── no forbidden files ────────────────────────────────────────────────────
    section("no forbidden files")
    for name in ("metadata.yaml", "MEMORY_UPDATE.md"):
        if not (base / name).exists():
            ok(f"{name} not created")
        else:
            fail(f"{name} should not exist")

    # ── path safety ──────────────────────────────────────────────────────────
    section("path safety")
    for label, fn in (
        ("prepare_chunk", lambda: op_prepare_chunk(base, "../outside")),
        ("read_chunk_files", lambda: op_read_chunk_files(base, "../outside")),
        ("get_builder_prompt", lambda: op_get_file(base, "../outside", "CLAUDE_PROMPT.md")),
    ):
        try:
            fn()
        except ValueError:
            ok(f"{label} rejects path escape")
        else:
            fail(f"{label} should reject path escape")

    # ── error handling ────────────────────────────────────────────────────────
    section("error handling")
    r = op_prepare_chunk(base, "chunks/999-nope")
    if "error" in r:
        ok("missing chunk folder returns error")
    else:
        fail(f"expected error: {r}")
    r = op_review_chunk(base, "chunks/999-nope")
    if "error" in r:
        ok("review missing chunk returns error")
    else:
        fail(f"expected error: {r}")
    r = op_next_chunk(Path("/tmp/empty-nonexistent-dir-xyz"))
    if "error" in r:
        ok("next_chunk missing ROADMAP returns error")
    else:
        fail(f"expected error: {r}")


print(f"\n{'='*40}")
print(f"Results: {PASS} passed, {FAIL} failed")
if FAIL:
    print("SOME TESTS FAILED", file=sys.stderr)
    sys.exit(1)
else:
    print("ALL TESTS PASSED")
