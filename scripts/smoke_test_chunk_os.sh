#!/usr/bin/env bash
# Smoke test for the full Darwin Chunk OS V1 loop.
# Run from the agent-darwin repo root with the venv active:
#   source .venv/bin/activate && bash scripts/smoke_test_chunk_os.sh

set -euo pipefail

DARWIN="darwin"
WORKSPACE="$(mktemp -d)"
trap 'rm -rf "$WORKSPACE"' EXIT

cd "$WORKSPACE"

pass() { echo "  PASS: $1"; }
fail() { echo "  FAIL: $1"; exit 1; }
section() { echo; echo "=== $1 ==="; }

# ── init ──────────────────────────────────────────────────────────────────────
section "darwin init"
$DARWIN init
[ -d chunks ] || fail "chunks/ missing"
[ -f MASTER_PLAN.md ] || fail "MASTER_PLAN.md missing"
pass "init creates workspace"

# ── split-plan ────────────────────────────────────────────────────────────────
section "darwin split-plan"
cat > MASTER_PLAN.md << 'EOF'
# Master Plan

- First task
- Second task
EOF

$DARWIN split-plan MASTER_PLAN.md
[ -d chunks/001-first-task ] || fail "chunks/001-first-task missing"
[ -f chunks/001-first-task/TASK.md ] || fail "TASK.md missing"
[ -d chunks/002-second-task ] || fail "chunks/002-second-task missing"
grep -q "001 — First task" ROADMAP.md || fail "ROADMAP.md missing chunk 001"
pass "split-plan creates chunk folders and ROADMAP"

# ── next-chunk points to 001 ──────────────────────────────────────────────────
section "next-chunk (before any pass)"
OUT=$($DARWIN next-chunk)
echo "$OUT" | grep -q "001" || fail "next-chunk should point to 001"
pass "next-chunk points to first chunk"

# ── prepare-chunk ─────────────────────────────────────────────────────────────
section "darwin prepare-chunk"
$DARWIN prepare-chunk chunks/001-first-task
[ -f chunks/001-first-task/STEP.md ] || fail "STEP.md missing"
[ -f chunks/001-first-task/CLAUDE_PROMPT.md ] || fail "CLAUDE_PROMPT.md missing"
[ -f chunks/001-first-task/ACCEPTANCE.md ] || fail "ACCEPTANCE.md missing"
pass "prepare-chunk creates all 6 files"

# ── record-result pass ────────────────────────────────────────────────────────
section "record-result pass"
$DARWIN record-result chunks/001-first-task --status pass --notes "smoke test pass"
[ -f chunks/001-first-task/RESULT.md ] || fail "RESULT.md missing"
grep -qi "PASS" chunks/001-first-task/RESULT.md || fail "RESULT.md missing PASS status"
pass "record-result creates RESULT.md"

# ── review-chunk pass ─────────────────────────────────────────────────────────
section "review-chunk pass"
REVIEW_OUT=$($DARWIN review-chunk chunks/001-first-task)
echo "$REVIEW_OUT" | grep -q "PASS" || fail "review-chunk should be PASS"
[ -f chunks/001-first-task/REVIEW.md ] || fail "REVIEW.md missing"
pass "review-chunk PASS when all files present"

# ── update-memory pass ────────────────────────────────────────────────────────
section "update-memory pass"
$DARWIN update-memory chunks/001-first-task
grep -q "first-task" memory/winners.md || fail "winners.md not updated"
grep -q "first-task" memory/decisions.md || fail "decisions.md not updated"
grep -q "\[x\]" ROADMAP.md || fail "ROADMAP.md not marked done"
grep -q "first-task" memory/mistakes.md 2>/dev/null && fail "mistakes.md should not be updated on pass"
pass "update-memory writes winners + decisions, marks ROADMAP [x]"

# ── next-chunk now points to 002 ──────────────────────────────────────────────
section "next-chunk (after 001 marked done)"
OUT=$($DARWIN next-chunk)
echo "$OUT" | grep -q "002" || fail "next-chunk should point to 002 now"
echo "$OUT" | grep -q "001" && fail "next-chunk should not point to 001 anymore"
pass "next-chunk advances to second chunk"

# ── record-result fail ────────────────────────────────────────────────────────
section "record-result fail + update-memory"
$DARWIN prepare-chunk chunks/002-second-task
$DARWIN record-result chunks/002-second-task --status fail --notes "smoke fail test"
$DARWIN review-chunk chunks/002-second-task
$DARWIN update-memory chunks/002-second-task
grep -q "second-task" memory/mistakes.md || fail "mistakes.md not updated on fail"
# ROADMAP line 002 must still be [ ] not [x]
grep "002 — Second task" ROADMAP.md | grep -q "\[ \]" || fail "002 should NOT be marked done"
pass "failed chunk updates mistakes, does NOT mark ROADMAP [x]"

# ── no forbidden files ────────────────────────────────────────────────────────
section "no forbidden files"
[ -f metadata.yaml ] && fail "metadata.yaml must not exist"
[ -f MEMORY_UPDATE.md ] && fail "MEMORY_UPDATE.md must not exist"
find . -name "metadata.yaml" | grep -q . && fail "metadata.yaml found somewhere"
pass "no forbidden files created"

# ── idempotency ───────────────────────────────────────────────────────────────
section "idempotency"
$DARWIN init
$DARWIN split-plan MASTER_PLAN.md
$DARWIN prepare-chunk chunks/001-first-task
pass "running commands twice does not crash"

section "ALL TESTS PASSED"
