#!/usr/bin/env bash
# Smoke test — Darwin Core 006 Fast Track Infrastructure Bundle V0
# Tests: module split, feature registry, worker registry, batch planner
set -euo pipefail

PASS=0
FAIL=0

ok()   { echo "[PASS] $1"; PASS=$((PASS+1)); }
fail() { echo "[FAIL] $1"; FAIL=$((FAIL+1)); }

# ── setup ──────────────────────────────────────────────────────────────────────
TMPDIR_BASE=$(mktemp -d)
trap 'rm -rf "$TMPDIR_BASE"' EXIT
cd "$TMPDIR_BASE"

# ── 1. module split — existing commands still work ─────────────────────────────
darwin version > /dev/null 2>&1 && ok "darwin version (module split)" || fail "darwin version broken"
darwin status  > /dev/null 2>&1 && ok "darwin status (module split)"  || fail "darwin status broken"
darwin doctor  > /dev/null 2>&1 && ok "darwin doctor (module split)"  || fail "darwin doctor broken"

darwin init > /dev/null 2>&1 && ok "darwin init (module split)" || fail "darwin init broken"

cat > MASTER_PLAN.md <<'EOF'
- Build the smoke test checker
- Verify idempotency
EOF
darwin split-plan MASTER_PLAN.md > /dev/null 2>&1 && ok "darwin split-plan (module split)" || fail "darwin split-plan broken"

CHUNK=$(ls chunks/ | head -1)
darwin prepare-chunk "chunks/$CHUNK" > /dev/null 2>&1 && ok "darwin prepare-chunk (module split)" || fail "darwin prepare-chunk broken"

# ── 2. darwin status mentions features and workers ─────────────────────────────
STATUS_OUT=$(darwin status 2>&1)
echo "$STATUS_OUT" | grep -q "features" && ok "darwin status mentions features" || fail "darwin status does not mention features"
echo "$STATUS_OUT" | grep -q "workers"  && ok "darwin status mentions workers"  || fail "darwin status does not mention workers"

# ── 3. feature-init creates files ─────────────────────────────────────────────
darwin feature-init > /dev/null 2>&1 && ok "darwin feature-init runs" || fail "darwin feature-init failed"
[ -d ".darwin/features" ]           && ok ".darwin/features/ created"          || fail ".darwin/features/ missing"
[ -f ".darwin/features/FEATURES.md" ] && ok "FEATURES.md created"            || fail "FEATURES.md missing"
[ -f ".darwin/features/COMMANDS.md" ] && ok "COMMANDS.md created"             || fail "COMMANDS.md missing"
[ -f ".darwin/features/COVERAGE.md" ] && ok "COVERAGE.md created"             || fail "COVERAGE.md missing"

# ── 4. feature-init is idempotent (user edit survives) ────────────────────────
echo "# User custom note" >> .darwin/features/FEATURES.md
BEFORE=$(cat .darwin/features/FEATURES.md)
darwin feature-init > /dev/null 2>&1
AFTER=$(cat .darwin/features/FEATURES.md)
[ "$BEFORE" = "$AFTER" ] && ok "user edit survived feature-init rerun" || fail "user edit was overwritten by feature-init"

# ── 5. feature-list works ─────────────────────────────────────────────────────
darwin feature-list 2>&1 | grep -q "Feature Registry" && ok "darwin feature-list runs" || fail "darwin feature-list failed"

# ── 6. feature-status works ───────────────────────────────────────────────────
darwin feature-status 2>&1 | grep -q "Feature Registry Status" && ok "darwin feature-status runs" || fail "darwin feature-status failed"

# ── 7. feature-list and feature-status are read-only ─────────────────────────
MTIME_BEFORE=$(stat -c %Y .darwin/features/FEATURES.md 2>/dev/null || stat -f %m .darwin/features/FEATURES.md)
darwin feature-list > /dev/null 2>&1
darwin feature-status > /dev/null 2>&1
MTIME_AFTER=$(stat -c %Y .darwin/features/FEATURES.md 2>/dev/null || stat -f %m .darwin/features/FEATURES.md)
[ "$MTIME_BEFORE" = "$MTIME_AFTER" ] && ok "feature-list/status did not mutate files" || fail "feature-list/status mutated files"

# ── 8. worker-init creates files ──────────────────────────────────────────────
darwin worker-init > /dev/null 2>&1 && ok "darwin worker-init runs" || fail "darwin worker-init failed"
[ -d ".darwin/workers" ]                           && ok ".darwin/workers/ created"               || fail ".darwin/workers/ missing"
[ -f ".darwin/workers/claude_code_builder.md" ]   && ok "claude_code_builder.md created"         || fail "claude_code_builder.md missing"
[ -f ".darwin/workers/codex_reviewer.md" ]        && ok "codex_reviewer.md created"              || fail "codex_reviewer.md missing"
[ -f ".darwin/workers/opencode_plan.md" ]         && ok "opencode_plan.md created"               || fail "opencode_plan.md missing"
[ -f ".darwin/workers/opencode_build.md" ]        && ok "opencode_build.md created"              || fail "opencode_build.md missing"
[ -f ".darwin/workers/opencode_explore.md" ]      && ok "opencode_explore.md created"            || fail "opencode_explore.md missing"
[ -f ".darwin/workers/opencode_scout.md" ]        && ok "opencode_scout.md created"              || fail "opencode_scout.md missing"
[ -f ".darwin/workers/mohit_supreme_judge.md" ]   && ok "mohit_supreme_judge.md created"         || fail "mohit_supreme_judge.md missing"

# ── 9. worker-init is idempotent (user edit survives) ─────────────────────────
echo "# My custom note" >> .darwin/workers/claude_code_builder.md
BEFORE=$(cat .darwin/workers/claude_code_builder.md)
darwin worker-init > /dev/null 2>&1
AFTER=$(cat .darwin/workers/claude_code_builder.md)
[ "$BEFORE" = "$AFTER" ] && ok "user edit survived worker-init rerun" || fail "user edit was overwritten by worker-init"

# ── 10. worker-list works ─────────────────────────────────────────────────────
darwin worker-list 2>&1 | grep -q "Worker Registry" && ok "darwin worker-list runs" || fail "darwin worker-list failed"

# ── 11. worker-suggest works ──────────────────────────────────────────────────
darwin worker-suggest --goal "build a new feature" 2>&1 | grep -q "Worker Suggestions" && ok "darwin worker-suggest runs" || fail "darwin worker-suggest failed"
darwin worker-suggest --goal "use OpenCode for MCP-heavy tool routing" 2>&1 | grep -q "opencode" && ok "worker-suggest matches opencode for MCP routing" || fail "worker-suggest did not match opencode"

# ── 12. worker-list is read-only ──────────────────────────────────────────────
MTIME_BEFORE=$(stat -c %Y .darwin/workers/claude_code_builder.md 2>/dev/null || stat -f %m .darwin/workers/claude_code_builder.md)
darwin worker-list > /dev/null 2>&1
darwin worker-suggest --goal "review code" > /dev/null 2>&1
MTIME_AFTER=$(stat -c %Y .darwin/workers/claude_code_builder.md 2>/dev/null || stat -f %m .darwin/workers/claude_code_builder.md)
[ "$MTIME_BEFORE" = "$MTIME_AFTER" ] && ok "worker-list/suggest did not mutate files" || fail "worker-list/suggest mutated files"

# ── 13. batch-plan works ──────────────────────────────────────────────────────
darwin batch-plan --goal "build 5 safe registry improvements" --max-items 7 2>&1 | grep -q "Batch Planner" && ok "darwin batch-plan runs" || fail "darwin batch-plan failed"

# batch-plan: high-risk goal → single mode
BP_OUT=$(darwin batch-plan --goal "deploy to production database" --max-items 7 2>&1)
echo "$BP_OUT" | grep -q "single" && ok "batch-plan: production goal → single mode" || fail "batch-plan: production goal did not get single mode"

# batch-plan: safe local goal → speed batch
BP_OUT=$(darwin batch-plan --goal "build 5 safe registry docs and smoke tests" --max-items 7 2>&1)
echo "$BP_OUT" | grep -qE "speed-batch-5|max-batch-7" && ok "batch-plan: local goal → speed batch mode" || fail "batch-plan: local goal did not get speed batch"

# batch-plan is read-only — no files created
ls .darwin/ | grep -v "features\|workers\|spec\|tools" | grep -v "PROJECT_BRIEF\|REPO_MAP\|COMMANDS\|RISK_LIST\|UNKNOWN\|MASTER_PLAN" > /dev/null 2>&1 || true
darwin batch-plan --goal "plan something" --max-items 5 > /dev/null 2>&1
ok "batch-plan did not crash on basic goal"

# ── 14. darwin doctor exits cleanly ───────────────────────────────────────────
darwin doctor > /dev/null 2>&1 && ok "darwin doctor exits cleanly" || fail "darwin doctor crashed"

# ── 15. darwin level stays Level 4 ───────────────────────────────────────────
STATUS_OUT=$(darwin status 2>&1)
echo "$STATUS_OUT" | grep -q "Darwin level: 4" && ok "Darwin level stays Level 4" || fail "Darwin level changed (expected 4)"

# ── 16. no metadata.yaml was created ─────────────────────────────────────────
! find . -name "metadata.yaml" | grep -q "metadata.yaml" && ok "no metadata.yaml created" || fail "metadata.yaml found — forbidden"

# ── summary ───────────────────────────────────────────────────────────────────
echo ""
echo "Results: $PASS passed, $FAIL failed"
[ "$FAIL" -eq 0 ] && echo "smoke_test_fast_track_bundle: PASS" && exit 0 || echo "smoke_test_fast_track_bundle: FAIL" && exit 1
