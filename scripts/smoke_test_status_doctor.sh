#!/usr/bin/env bash
# Smoke test for Darwin Core 003: version / status / doctor.
# Run from the agent-darwin repo root with the venv active:
#   source .venv/bin/activate && bash scripts/smoke_test_status_doctor.sh

set -euo pipefail

DARWIN="darwin"
WORKSPACE="$(mktemp -d)"
trap 'rm -rf "$WORKSPACE"' EXIT

pass() { echo "  PASS: $1"; }
fail() { echo "  FAIL: $1"; exit 1; }
section() { echo; echo "=== $1 ==="; }

# darwin version
section "darwin version"
VERSION_OUT=$($DARWIN version)
echo "$VERSION_OUT" | grep -qi "version" || fail "version output missing 'version'"
echo "$VERSION_OUT" | grep -qE "[0-9]+\.[0-9]" || fail "version output missing version number"
pass "darwin version prints version"

# darwin status from temp workspace (smoke test scripts will be absent)
section "darwin status (temp workspace)"
cd "$WORKSPACE"
STATUS_OUT=$($DARWIN status)
echo "$STATUS_OUT" | grep -qi "level" || fail "status missing 'Level'"
echo "$STATUS_OUT" | grep -q "smoke_test_chunk_os.sh" || fail "status missing smoke_test_chunk_os.sh"
echo "$STATUS_OUT" | grep -q "smoke_test_mcp_tools.py" || fail "status missing smoke_test_mcp_tools.py"
echo "$STATUS_OUT" | grep -q "smoke_test_eval_harness.sh" || fail "status missing smoke_test_eval_harness.sh"
echo "$STATUS_OUT" | grep -q "smoke_test_repo_intake.sh" || fail "status missing smoke_test_repo_intake.sh"
echo "$STATUS_OUT" | grep -q "smoke_test_status_doctor.sh" || fail "status missing smoke_test_status_doctor.sh"
echo "$STATUS_OUT" | grep -qE "Darwin level: [0-9]" || fail "status missing Darwin level number"
pass "darwin status shows level and smoke test entries"

# darwin status from repo root (smoke test scripts should show [x])
section "darwin status (repo root)"
cd /home/mohit/agent-darwin
STATUS_REPO=$($DARWIN status)
echo "$STATUS_REPO" | grep -q "\[x\] scripts/smoke_test_chunk_os.sh" || fail "smoke_test_chunk_os.sh should be [x] from repo root"
echo "$STATUS_REPO" | grep -q "\[x\] scripts/smoke_test_mcp_tools.py" || fail "smoke_test_mcp_tools.py should be [x] from repo root"
echo "$STATUS_REPO" | grep -q "\[x\] scripts/smoke_test_eval_harness.sh" || fail "smoke_test_eval_harness.sh should be [x] from repo root"
echo "$STATUS_REPO" | grep -q "\[x\] scripts/smoke_test_repo_intake.sh" || fail "smoke_test_repo_intake.sh should be [x] from repo root"
echo "$STATUS_REPO" | grep -q "\[x\] scripts/smoke_test_status_doctor.sh" || fail "smoke_test_status_doctor.sh should be [x] from repo root"
pass "darwin status shows [x] for existing smoke test scripts"

# darwin doctor from temp workspace
section "darwin doctor (temp workspace)"
cd "$WORKSPACE"
DOCTOR_OUT=$($DARWIN doctor 2>&1)
echo "$DOCTOR_OUT" | grep -qiE "PASS|WARN" || fail "doctor missing PASS or WARN"
echo "$DOCTOR_OUT" | grep -qi "python" || fail "doctor missing Python check"
echo "$DOCTOR_OUT" | grep -qi "typer" || fail "doctor missing typer check"
echo "$DOCTOR_OUT" | grep -q "smoke_test_chunk_os.sh" || fail "doctor missing smoke_test_chunk_os.sh"
echo "$DOCTOR_OUT" | grep -q "smoke_test_mcp_tools.py" || fail "doctor missing smoke_test_mcp_tools.py"
echo "$DOCTOR_OUT" | grep -q "smoke_test_eval_harness.sh" || fail "doctor missing smoke_test_eval_harness.sh"
echo "$DOCTOR_OUT" | grep -q "smoke_test_repo_intake.sh" || fail "doctor missing smoke_test_repo_intake.sh"
echo "$DOCTOR_OUT" | grep -q "smoke_test_status_doctor.sh" || fail "doctor missing smoke_test_status_doctor.sh"
echo "$DOCTOR_OUT" | grep -qi "summary" || fail "doctor missing Summary line"
pass "darwin doctor shows expected output"

# doctor exits cleanly
$DARWIN doctor > /dev/null 2>&1
pass "darwin doctor exits cleanly"

# doctor does not create files
section "doctor is read-only"
FILE_COUNT=$(ls "$WORKSPACE" | wc -l | tr -d ' ')
[ "$FILE_COUNT" -eq 0 ] || fail "doctor created unexpected files in workspace: $(ls $WORKSPACE)"
pass "darwin doctor is read-only (no files created)"

# no metadata.yaml
section "no metadata.yaml"
[ -f metadata.yaml ] && fail "metadata.yaml must not exist"
pass "no metadata.yaml"

section "ALL STATUS/DOCTOR TESTS PASSED"
