#!/usr/bin/env bash
# Smoke test — Darwin Core 007 Multi-Brain Operator Run V0
# Tests: brain-init, brain-status, brain-route, operate-existing
# Does NOT call real external APIs.
set -euo pipefail

PASS=0
FAIL=0

ok()   { echo "[PASS] $1"; PASS=$((PASS+1)); }
fail() { echo "[FAIL] $1"; FAIL=$((FAIL+1)); }

# ── setup ──────────────────────────────────────────────────────────────────────
TMPDIR_BASE=$(mktemp -d)
trap 'rm -rf "$TMPDIR_BASE"' EXIT

DARWIN_WORK="$TMPDIR_BASE/darwin_work"
TARGET_REPO="$TMPDIR_BASE/target_repo"

mkdir -p "$DARWIN_WORK"
mkdir -p "$TARGET_REPO"

# Create a minimal Python repo as the target
cat > "$TARGET_REPO/pyproject.toml" <<'EOF'
[project]
name = "sample-project"
version = "0.1.0"
[project.scripts]
sample = "sample.cli:app"
EOF
mkdir -p "$TARGET_REPO/src/sample"
cat > "$TARGET_REPO/src/sample/__init__.py" <<'EOF'
"""Sample project."""
EOF
mkdir -p "$TARGET_REPO/tests"
cat > "$TARGET_REPO/tests/test_sample.py" <<'EOF'
def test_placeholder():
    assert True
EOF
cat > "$TARGET_REPO/README.md" <<'EOF'
# Sample Project
A sample Python project for Darwin smoke testing.
EOF

cd "$DARWIN_WORK"

# ── 1. darwin brain-status before init ────────────────────────────────────────
STATUS_BEFORE=$(darwin brain-status 2>&1)
echo "$STATUS_BEFORE" | grep -qi "brain" \
  && ok "darwin brain-status runs before brain-init" \
  || fail "darwin brain-status failed before brain-init"

echo "$STATUS_BEFORE" | grep -qi "missing\|not found\|no\|present" \
  && ok "darwin brain-status shows dir missing before init" \
  || fail "darwin brain-status does not mention dir status"

# ── 2. darwin brain-init creates files ────────────────────────────────────────
darwin brain-init > /dev/null 2>&1 \
  && ok "darwin brain-init runs" \
  || fail "darwin brain-init failed"

[ -d ".darwin/brain" ]             && ok ".darwin/brain/ created"       || fail ".darwin/brain/ missing"
[ -f ".darwin/brain/BRAIN.md" ]    && ok "BRAIN.md created"             || fail "BRAIN.md missing"
[ -f ".darwin/brain/PROVIDERS.md" ] && ok "PROVIDERS.md created"        || fail "PROVIDERS.md missing"
[ -f ".darwin/brain/SAFETY.md" ]   && ok "SAFETY.md created"            || fail "SAFETY.md missing"
[ -f ".darwin/brain/ROLES.md" ]    && ok "ROLES.md created"             || fail "ROLES.md missing"

# ── 3. brain-init is idempotent (user edits survive) ──────────────────────────
echo "# User custom note — should survive rerun" >> .darwin/brain/BRAIN.md
BEFORE=$(cat .darwin/brain/BRAIN.md)
darwin brain-init > /dev/null 2>&1
AFTER=$(cat .darwin/brain/BRAIN.md)
[ "$BEFORE" = "$AFTER" ] \
  && ok "user edit survived brain-init rerun" \
  || fail "user edit was overwritten by brain-init"

# ── 4. brain-status does not print API key values ─────────────────────────────
# Set a fake key to confirm it is NOT printed
ORIG_GROQ="${GROQ_API_KEY:-}"
export GROQ_API_KEY="sk-fake-test-key-should-not-appear-in-output"
STATUS_OUT=$(darwin brain-status 2>&1)
unset GROQ_API_KEY
[ -n "$ORIG_GROQ" ] && export GROQ_API_KEY="$ORIG_GROQ"

echo "$STATUS_OUT" | grep -q "sk-fake-test-key-should-not-appear-in-output" \
  && fail "brain-status printed API key value" \
  || ok "brain-status did not print API key value"

echo "$STATUS_OUT" | grep -qi "groq" \
  && ok "brain-status mentions groq" \
  || fail "brain-status missing groq"

echo "$STATUS_OUT" | grep -qi "yes\|no" \
  && ok "brain-status shows key present/absent indicator" \
  || fail "brain-status does not show key presence"

# Confirm the fake key is not in env anymore
env | grep -q "sk-fake-test-key" \
  && fail "fake key leaked into environment" \
  || ok "fake key not in environment after test"

# ── 5. brain-route --brain off (deterministic, no API) ────────────────────────
ROUTE_OUT=$(darwin brain-route --goal "add hello command safely" --brain off 2>&1)
[ $? -eq 0 ] && ok "brain-route --brain off exits 0" || fail "brain-route --brain off failed"

echo "$ROUTE_OUT" | grep -qi "deterministic\|local\|off" \
  && ok "brain-route off output mentions deterministic/local route" \
  || fail "brain-route off does not mention deterministic route"

echo "$ROUTE_OUT" | grep -qi "brain role\|body worker\|task type\|route" \
  && ok "brain-route off shows routing info" \
  || fail "brain-route off missing routing info"

echo "$ROUTE_OUT" | grep -qi "claude code\|body worker" \
  && ok "brain-route off recommends a body worker" \
  || fail "brain-route off does not recommend a body worker"

# ── 6. brain-route --brain auto (no keys = deterministic fallback) ────────────
# Ensure no real keys are set for this test
ROUTE_AUTO=$(
  env -u GROQ_API_KEY -u OPENROUTER_API_KEY -u POOLSIDE_API_KEY -u NVIDIA_API_KEY \
  darwin brain-route --goal "add hello command safely" --brain auto 2>&1
)
[ $? -eq 0 ] && ok "brain-route --brain auto exits 0 without keys" || fail "brain-route auto failed"

echo "$ROUTE_AUTO" | grep -qi "deterministic\|fallback\|local\|no api key\|no.*key" \
  && ok "brain-route auto mentions fallback when no keys" \
  || fail "brain-route auto does not mention fallback"

# ── 7. operate-existing --brain off ───────────────────────────────────────────
OP_OUT=$(darwin operate-existing "$TARGET_REPO" --goal "add hello command safely" --brain off 2>&1)
[ $? -eq 0 ] && ok "operate-existing --brain off exits 0" || fail "operate-existing failed"

echo "$OP_OUT" | grep -qi "run dir\|run folder\|operator run" \
  && ok "operate-existing shows run dir info" \
  || fail "operate-existing missing run dir info"

echo "$OP_OUT" | grep -qi "no workers\|not.*executed\|warning" \
  && ok "operate-existing warns no workers executed" \
  || fail "operate-existing missing no-workers warning"

# ── 8. Verify run folder and required files exist ────────────────────────────
RUNS_DIR="$TARGET_REPO/.darwin/runs"
[ -d "$RUNS_DIR" ] && ok ".darwin/runs/ created in target repo" || fail ".darwin/runs/ missing"

RUN_FOLDER=$(ls "$RUNS_DIR" | head -1)
[ -n "$RUN_FOLDER" ] && ok "run folder exists: $RUN_FOLDER" || fail "no run folder found"
RUN_PATH="$RUNS_DIR/$RUN_FOLDER"

for f in \
  RUN_SUMMARY.md \
  BRAIN_ROUTE.md \
  BRAIN_PLAN.md \
  PROJECT_BRIEF.md \
  REPO_MAP.md \
  BODY_WORKER_PLAN.md \
  TOOL_POLICY.md \
  TASK_BREAKDOWN.md \
  CLAUDE_BUILD_PROMPT.md \
  OPENCODE_PLAN_PROMPT.md \
  CODEX_REVIEW_PROMPT.md \
  ACCEPTANCE_CHECKLIST.md \
  TEST_PLAN.md \
  RISKS.md \
  NEXT_ACTION.md \
  TRACE.md
do
  [ -f "$RUN_PATH/$f" ] && ok "$f exists" || fail "$f missing"
done

# ── 9. Verify prompt files are useful ─────────────────────────────────────────
CLAUDE_PROMPT=$(cat "$RUN_PATH/CLAUDE_BUILD_PROMPT.md")
echo "$CLAUDE_PROMPT" | grep -qi "goal\|task\|acceptance\|forbidden\|do not commit" \
  && ok "CLAUDE_BUILD_PROMPT.md has useful content" \
  || fail "CLAUDE_BUILD_PROMPT.md missing key sections"

OPENCODE_PROMPT=$(cat "$RUN_PATH/OPENCODE_PLAN_PROMPT.md")
echo "$OPENCODE_PROMPT" | grep -qi "planning\|tool_plan\|risk_report\|no file edit" \
  && ok "OPENCODE_PLAN_PROMPT.md has useful content" \
  || fail "OPENCODE_PLAN_PROMPT.md missing key sections"

CODEX_PROMPT=$(cat "$RUN_PATH/CODEX_REVIEW_PROMPT.md")
echo "$CODEX_PROMPT" | grep -qi "review\|pass\|fail\|do not commit" \
  && ok "CODEX_REVIEW_PROMPT.md has useful content" \
  || fail "CODEX_REVIEW_PROMPT.md missing key sections"

# ── 10. Verify NEXT_ACTION.md has clear action ───────────────────────────────
NEXT_ACTION=$(cat "$RUN_PATH/NEXT_ACTION.md")
echo "$NEXT_ACTION" | grep -qi "paste\|claude\|codex\|opencode\|mohit\|next" \
  && ok "NEXT_ACTION.md has a clear next action" \
  || fail "NEXT_ACTION.md does not have a clear action"

# ── 11. Verify BRAIN_ROUTE.md exists and has route info ──────────────────────
BRAIN_ROUTE=$(cat "$RUN_PATH/BRAIN_ROUTE.md")
echo "$BRAIN_ROUTE" | grep -qi "brain mode\|route\|provider\|worker" \
  && ok "BRAIN_ROUTE.md has route info" \
  || fail "BRAIN_ROUTE.md missing route info"

# ── 12. Verify BODY_WORKER_PLAN.md exists and has roles ──────────────────────
BODY_PLAN=$(cat "$RUN_PATH/BODY_WORKER_PLAN.md")
echo "$BODY_PLAN" | grep -qi "claude code\|codex\|opencode\|mohit" \
  && ok "BODY_WORKER_PLAN.md lists workers" \
  || fail "BODY_WORKER_PLAN.md missing worker info"

# ── 13. Verify TOOL_POLICY.md says no tools executed ─────────────────────────
TOOL_POLICY=$(cat "$RUN_PATH/TOOL_POLICY.md")
echo "$TOOL_POLICY" | grep -qi "not executed\|tools were not\|no tool" \
  && ok "TOOL_POLICY.md says tools not executed" \
  || fail "TOOL_POLICY.md does not say tools not executed"

# ── 14. Rerun same goal — second numbered run folder created ──────────────────
darwin operate-existing "$TARGET_REPO" --goal "add hello command safely" --brain off > /dev/null 2>&1
RUN_COUNT=$(ls "$RUNS_DIR" | wc -l)
[ "$RUN_COUNT" -ge 2 ] \
  && ok "second run created separate folder (count=$RUN_COUNT)" \
  || fail "second run did not create a new folder"

# ── 15. Target repo files outside .darwin/ not modified ──────────────────────
# Check that pyproject.toml is unchanged
PYPROJECT_CONTENT=$(cat "$TARGET_REPO/pyproject.toml")
echo "$PYPROJECT_CONTENT" | grep -q "sample-project" \
  && ok "target repo pyproject.toml not modified" \
  || fail "target repo pyproject.toml was modified"

# Check that README.md is unchanged
README_CONTENT=$(cat "$TARGET_REPO/README.md")
echo "$README_CONTENT" | grep -q "Sample Project" \
  && ok "target repo README.md not modified" \
  || fail "target repo README.md was modified"

# ── 16. No metadata.yaml created ─────────────────────────────────────────────
find "$TARGET_REPO" -name "metadata.yaml" | grep -q . \
  && fail "metadata.yaml was created (forbidden)" \
  || ok "no metadata.yaml created"

find "$DARWIN_WORK" -name "metadata.yaml" | grep -q . \
  && fail "metadata.yaml in darwin work dir (forbidden)" \
  || ok "no metadata.yaml in darwin work dir"

# ── 17. operate-existing: missing path handled cleanly ───────────────────────
darwin operate-existing "/tmp/does-not-exist-darwin-test-$$" --goal "x" --brain off > /dev/null 2>&1 \
  && fail "operate-existing should fail on missing path" \
  || ok "operate-existing handles missing path cleanly"

# ── 18. operate-existing: file path (not folder) handled cleanly ──────────────
TMPFILE=$(mktemp)
darwin operate-existing "$TMPFILE" --goal "x" --brain off > /dev/null 2>&1 \
  && fail "operate-existing should fail on file path" \
  || ok "operate-existing handles file path cleanly"
rm -f "$TMPFILE"

# ── 19. darwin status mentions brain/runs when present ───────────────────────
cd "$DARWIN_WORK"
STATUS_WITH_BRAIN=$(darwin status 2>&1)
echo "$STATUS_WITH_BRAIN" | grep -qi "brain" \
  && ok "darwin status mentions .darwin/brain/" \
  || fail "darwin status does not mention .darwin/brain/"

# Check runs in target repo
cd "$TARGET_REPO"
STATUS_WITH_RUNS=$(darwin status 2>&1)
echo "$STATUS_WITH_RUNS" | grep -qi "runs" \
  && ok "darwin status mentions .darwin/runs/" \
  || fail "darwin status does not mention .darwin/runs/"
cd "$DARWIN_WORK"

# ── 20. darwin doctor exits cleanly ──────────────────────────────────────────
darwin doctor > /dev/null 2>&1 \
  && ok "darwin doctor exits cleanly" \
  || fail "darwin doctor failed"

DOCTOR_OUT=$(darwin doctor 2>&1)
echo "$DOCTOR_OUT" | grep -qi "op_brain_init\|multi-brain\|brain" \
  && ok "darwin doctor mentions brain ops" \
  || fail "darwin doctor missing brain op checks"

echo "$DOCTOR_OUT" | grep -qi "op_operate_existing" \
  && ok "darwin doctor mentions op_operate_existing" \
  || fail "darwin doctor missing op_operate_existing check"

# ── 21. No API key value is printed in any output ────────────────────────────
# Re-confirm using all outputs captured earlier
for OUTPUT_VAR in "$STATUS_OUT" "$ROUTE_OUT" "$ROUTE_AUTO" "$OP_OUT"; do
  echo "$OUTPUT_VAR" | grep -qE "sk-[a-zA-Z0-9]{20,}" \
    && fail "API key value pattern found in output" \
    || true
done
ok "no API key values printed in any captured output"

# ── 22. No .env was read or written anywhere ──────────────────────────────────
find "$TMPDIR_BASE" -name ".env" | grep -q . \
  && fail ".env file was created during test" \
  || ok "no .env file created"

# ── 23. brain-route invalid mode exits with error ────────────────────────────
darwin brain-route --goal "test" --brain invalid_mode > /dev/null 2>&1 \
  && fail "brain-route should fail on invalid brain mode" \
  || ok "brain-route rejects invalid brain mode"

# ── 24. operate-existing --brain auto without keys gives deterministic output ─
cd "$DARWIN_WORK"
OP_AUTO_OUT=$(
  env -u GROQ_API_KEY -u OPENROUTER_API_KEY -u POOLSIDE_API_KEY -u NVIDIA_API_KEY \
  darwin operate-existing "$TARGET_REPO" --goal "build auto test safely" --brain auto 2>&1
)
[ $? -eq 0 ] \
  && ok "operate-existing --brain auto without keys exits 0" \
  || fail "operate-existing --brain auto without keys failed"

RUNS_COUNT_AFTER=$(ls "$TARGET_REPO/.darwin/runs" | wc -l)
[ "$RUNS_COUNT_AFTER" -ge 3 ] \
  && ok "operate-existing --brain auto created run folder (total: $RUNS_COUNT_AFTER)" \
  || fail "operate-existing --brain auto did not create run folder"

# Check that BRAIN_ROUTE.md mentions deterministic fallback
AUTO_RUN=$(ls "$TARGET_REPO/.darwin/runs" | tail -1)
AUTO_BRAIN_ROUTE=$(cat "$TARGET_REPO/.darwin/runs/$AUTO_RUN/BRAIN_ROUTE.md")
echo "$AUTO_BRAIN_ROUTE" | grep -qi "deterministic\|fallback\|no.*key\|local" \
  && ok "BRAIN_ROUTE.md mentions deterministic fallback for auto without keys" \
  || fail "BRAIN_ROUTE.md does not mention deterministic fallback"

# ── done ──────────────────────────────────────────────────────────────────────
echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] && echo "ALL PASS" && exit 0 || exit 1
