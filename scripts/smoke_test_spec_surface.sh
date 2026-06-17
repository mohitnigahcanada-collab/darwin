#!/usr/bin/env bash
# Smoke test for Darwin Core 004: spec-init / spec-status.
# Run from the agent-darwin repo root with the venv active:
#   source .venv/bin/activate && bash scripts/smoke_test_spec_surface.sh

set -euo pipefail

DARWIN="darwin"
WORKSPACE="$(mktemp -d)"
trap 'rm -rf "$WORKSPACE"' EXIT

pass() { echo "  PASS: $1"; }
fail() { echo "  FAIL: $1"; exit 1; }
section() { echo; echo "=== $1 ==="; }

# spec-init creates .darwin/spec/ files
section "darwin spec-init"
cd "$WORKSPACE"
$DARWIN spec-init
[ -d .darwin/spec ]                       || fail ".darwin/spec/ missing"
[ -f .darwin/spec/SPEC_SURFACE.md ]       || fail "SPEC_SURFACE.md missing"
[ -f .darwin/spec/SCENARIOS.md ]          || fail "SCENARIOS.md missing"
[ -f .darwin/spec/PROTECTED_COMMANDS.md ] || fail "PROTECTED_COMMANDS.md missing"
pass "spec-init creates all spec files"

# spec-status shows expected output
section "darwin spec-status"
SPEC_OUT=$($DARWIN spec-status)
echo "$SPEC_OUT" | grep -q "SPEC_SURFACE.md"       || fail "spec-status missing SPEC_SURFACE.md"
echo "$SPEC_OUT" | grep -q "SCENARIOS.md"           || fail "spec-status missing SCENARIOS.md"
echo "$SPEC_OUT" | grep -q "PROTECTED_COMMANDS.md"  || fail "spec-status missing PROTECTED_COMMANDS.md"
echo "$SPEC_OUT" | grep -qiE "Protected commands: [0-9]+" || fail "spec-status missing protected count"
pass "spec-status shows expected output"

# idempotency: user edits survive rerun
section "spec-init idempotency and no-overwrite"
echo "CUSTOM NOTE: do not overwrite me" >> .darwin/spec/SPEC_SURFACE.md
$DARWIN spec-init
grep -q "CUSTOM NOTE: do not overwrite me" .darwin/spec/SPEC_SURFACE.md \
  || fail "spec-init overwrote user-edited SPEC_SURFACE.md"
pass "spec-init does not overwrite existing files"

# darwin status mentions spec
section "darwin status mentions spec"
STATUS_OUT=$($DARWIN status)
echo "$STATUS_OUT" | grep -q "spec" || fail "darwin status does not mention spec"
echo "$STATUS_OUT" | grep -q "smoke_test_spec_surface.sh" || fail "darwin status missing smoke_test_spec_surface.sh"
echo "$STATUS_OUT" | grep -q "Darwin level: 4" || fail "Spec Surface must not advance Darwin beyond Level 4"
pass "darwin status mentions spec surface and smoke test"

# darwin doctor exits cleanly
section "darwin doctor exits cleanly"
$DARWIN doctor > /dev/null 2>&1
pass "darwin doctor exits cleanly"

# doctor mentions spec surface smoke test
section "darwin doctor mentions spec surface smoke test"
DOCTOR_OUT=$($DARWIN doctor 2>&1)
echo "$DOCTOR_OUT" | grep -q "smoke_test_spec_surface.sh" || fail "doctor missing smoke_test_spec_surface.sh"
pass "darwin doctor mentions smoke_test_spec_surface.sh"

# spec-status exits 1 before init in a fresh workspace
section "spec-status exits 1 when spec not initialized"
FRESH="$(mktemp -d)"
trap 'rm -rf "$WORKSPACE" "$FRESH"' EXIT
cd "$FRESH"
ERR_OUT=$($DARWIN spec-status 2>&1 || true)
echo "$ERR_OUT" | grep -qi "spec-init" || fail "spec-status error message should mention spec-init"
pass "spec-status exits 1 and mentions spec-init when not initialized"

# no metadata.yaml
section "no metadata.yaml"
cd "$WORKSPACE"
[ -f metadata.yaml ] && fail "metadata.yaml must not exist"
find . -name "metadata.yaml" | grep -q . && fail "metadata.yaml found in workspace"
pass "no metadata.yaml"

section "ALL SPEC SURFACE TESTS PASSED"
