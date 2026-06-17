#!/usr/bin/env bash
# Smoke test for Darwin Eval Harness V0.
# Run from the agent-darwin repo root with the venv active:
#   source .venv/bin/activate && bash scripts/smoke_test_eval_harness.sh

set -euo pipefail

DARWIN="darwin"
WORKSPACE="$(mktemp -d)"
trap 'rm -rf "$WORKSPACE"' EXIT

cd "$WORKSPACE"

pass() { echo "  PASS: $1"; }
fail() { echo "  FAIL: $1"; exit 1; }
section() { echo; echo "=== $1 ==="; }

# eval-init creates structure
section "darwin eval-init"
$DARWIN eval-init
[ -d evals ]              || fail "evals/ missing"
[ -d evals/tasks ]        || fail "evals/tasks/ missing"
[ -d evals/runs ]         || fail "evals/runs/ missing"
[ -d evals/reports ]      || fail "evals/reports/ missing"
[ -d evals/baselines ]    || fail "evals/baselines/ missing"
[ -f evals/tasks/repo_intake_basic.md ]       || fail "repo_intake_basic.md missing"
[ -f evals/tasks/new_project_plan_basic.md ]  || fail "new_project_plan_basic.md missing"
[ -f evals/README.md ]    || fail "evals/README.md missing"
pass "eval-init creates full eval structure"

# eval-init does not overwrite user edits
section "eval-init idempotency + no-overwrite"
echo "CUSTOM NOTE: do not overwrite me" >> evals/tasks/repo_intake_basic.md
$DARWIN eval-init
grep -q "CUSTOM NOTE: do not overwrite me" evals/tasks/repo_intake_basic.md \
  || fail "eval-init overwrote user-edited task file"
pass "eval-init does not overwrite existing files"

# eval-list shows tasks
section "darwin eval-list"
LIST_OUT=$($DARWIN eval-list)
echo "$LIST_OUT" | grep -q "repo_intake_basic"      || fail "eval-list missing repo_intake_basic"
echo "$LIST_OUT" | grep -q "new_project_plan_basic" || fail "eval-list missing new_project_plan_basic"
pass "eval-list shows available tasks"

# eval-list clean error when evals/tasks missing
section "eval-list clean error"
mkdir -p no_evals_workspace
cd no_evals_workspace
ERR_OUT=$($DARWIN eval-list 2>&1 || true)
echo "$ERR_OUT" | grep -qi "eval-init" \
  || fail "eval-list should hint to run eval-init when tasks dir missing"
cd "$WORKSPACE"
pass "eval-list shows clean error when evals/tasks missing"

# eval-run creates reports
section "darwin eval-run"
$DARWIN eval-run repo_intake_basic --candidate darwin-v0
RUN_COUNT=$(ls evals/runs/ | wc -l | tr -d ' ')
[ "$RUN_COUNT" -ge 1 ]                              || fail "no run file in evals/runs/"
[ -f evals/reports/latest.md ]                      || fail "evals/reports/latest.md missing"
grep -q "repo_intake_basic" evals/reports/latest.md || fail "latest.md missing task name"
grep -q "darwin-v0"         evals/reports/latest.md || fail "latest.md missing candidate name"
grep -q "KEEP / FIX / KILL" evals/reports/latest.md || fail "latest.md missing verdict placeholder"
grep -q "PASS / FAIL"       evals/reports/latest.md || fail "latest.md missing safety placeholder"
pass "eval-run creates run report and updates latest.md"

# eval-run run file is timestamped
section "eval-run timestamped file"
RUN_FILE=$(ls evals/runs/)
echo "$RUN_FILE" | grep -q "repo_intake_basic" || fail "run filename missing task name"
echo "$RUN_FILE" | grep -q "darwin-v0"         || fail "run filename missing candidate"
pass "eval-run filename includes task and candidate"

# eval-report prints latest
section "darwin eval-report"
REPORT_OUT=$($DARWIN eval-report)
echo "$REPORT_OUT" | grep -q "repo_intake_basic" || fail "eval-report should print task name"
echo "$REPORT_OUT" | grep -q "darwin-v0"         || fail "eval-report should print candidate name"
pass "eval-report prints latest report"

# eval-report clean error when no latest report exists
section "eval-report clean error"
mkdir -p no_report_workspace/evals/reports
cd no_report_workspace
ERR_OUT=$($DARWIN eval-report 2>&1 || true)
echo "$ERR_OUT" | grep -qi "eval-run" \
  || fail "eval-report should hint to run eval-run when no latest report"
cd "$WORKSPACE"
pass "eval-report shows clean error when no latest report"

# no forbidden files
section "no forbidden files"
[ -f metadata.yaml ] && fail "metadata.yaml must not exist"
find . -name "metadata.yaml" | grep -q . && fail "metadata.yaml found somewhere"
pass "no forbidden files created"

section "ALL EVAL HARNESS TESTS PASSED"
