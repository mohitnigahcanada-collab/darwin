#!/usr/bin/env bash
# Smoke test for Darwin Repo Intake V0.
# Run from the agent-darwin repo root with the venv active:
#   source .venv/bin/activate && bash scripts/smoke_test_repo_intake.sh

set -euo pipefail

DARWIN="darwin"
WORKSPACE="$(mktemp -d)"
trap 'rm -rf "$WORKSPACE"' EXIT

pass() { echo "  PASS: $1"; }
fail() { echo "  FAIL: $1"; exit 1; }
section() { echo; echo "=== $1 ==="; }

# setup: create a minimal Python project
section "setup: create temp Python project"
REPO="$WORKSPACE/my-project"
mkdir -p "$REPO/src" "$REPO/scripts" "$REPO/tests"
cat > "$REPO/pyproject.toml" << 'EOF'
[project]
name = "my-project"
version = "0.1.0"

[project.scripts]
mycli = "my_project.cli:app"
EOF
echo "# My Project" > "$REPO/README.md"
echo "# tests" > "$REPO/tests/__init__.py"
git -C "$REPO" init -q
pass "temp Python project created"

# inspect-repo creates .darwin/
section "darwin inspect-repo"
$DARWIN inspect-repo "$REPO" --goal "improve CLI tests"
[ -d "$REPO/.darwin" ]                          || fail ".darwin/ missing"
[ -f "$REPO/.darwin/PROJECT_BRIEF.md" ]         || fail "PROJECT_BRIEF.md missing"
[ -f "$REPO/.darwin/REPO_MAP.md" ]              || fail "REPO_MAP.md missing"
[ -f "$REPO/.darwin/COMMANDS.md" ]              || fail "COMMANDS.md missing"
[ -f "$REPO/.darwin/RISK_LIST.md" ]             || fail "RISK_LIST.md missing"
[ -f "$REPO/.darwin/UNKNOWN_QUESTIONS.md" ]     || fail "UNKNOWN_QUESTIONS.md missing"
[ -f "$REPO/.darwin/MASTER_PLAN_DRAFT.md" ]     || fail "MASTER_PLAN_DRAFT.md missing"
pass "inspect-repo creates all .darwin/ files"

# verify file content
section "verify file content"
grep -q "improve CLI tests" "$REPO/.darwin/PROJECT_BRIEF.md"   || fail "PROJECT_BRIEF.md missing goal"
grep -qi "python"            "$REPO/.darwin/PROJECT_BRIEF.md"  || fail "PROJECT_BRIEF.md missing project type"
grep -q "my-project"         "$REPO/.darwin/PROJECT_BRIEF.md"  || fail "PROJECT_BRIEF.md missing project name"
grep -q "my-project"         "$REPO/.darwin/REPO_MAP.md"       || fail "REPO_MAP.md missing repo name"
grep -qi "pip install"       "$REPO/.darwin/COMMANDS.md"       || fail "COMMANDS.md missing install command"
grep -q "mycli --help"       "$REPO/.darwin/COMMANDS.md"       || fail "COMMANDS.md missing console script command"
grep -q "improve CLI tests"  "$REPO/.darwin/MASTER_PLAN_DRAFT.md" || fail "MASTER_PLAN_DRAFT.md missing goal"
pass "file content is correct"

# rerun does not overwrite user edits
section "idempotency + no-overwrite"
echo "CUSTOM NOTE: do not overwrite me" >> "$REPO/.darwin/PROJECT_BRIEF.md"
$DARWIN inspect-repo "$REPO" --goal "improve CLI tests"
grep -q "CUSTOM NOTE: do not overwrite me" "$REPO/.darwin/PROJECT_BRIEF.md" \
  || fail "inspect-repo overwrote user-edited file"
pass "inspect-repo does not overwrite existing .darwin/ files"

# missing repo path shows clean error
section "missing repo path error"
ERR_OUT=$($DARWIN inspect-repo "$WORKSPACE/nonexistent" --goal "test" 2>&1 || true)
echo "$ERR_OUT" | grep -qi "not found" \
  || fail "missing repo should show 'not found' error"
pass "missing repo path shows clean error"

# file path instead of folder shows clean error
section "file path error"
TMPFILE="$WORKSPACE/tmpfile.txt"
echo "i am a file" > "$TMPFILE"
ERR_OUT=$($DARWIN inspect-repo "$TMPFILE" --goal "test" 2>&1 || true)
echo "$ERR_OUT" | grep -qi "file" \
  || fail "file path should show error mentioning 'file'"
pass "file path shows clean error"

# no forbidden files
section "no forbidden files"
[ -f "$REPO/metadata.yaml" ] && fail "metadata.yaml must not exist"
find "$REPO" -name "metadata.yaml" | grep -q . && fail "metadata.yaml found somewhere"
pass "no forbidden files created"

section "ALL REPO INTAKE TESTS PASSED"
