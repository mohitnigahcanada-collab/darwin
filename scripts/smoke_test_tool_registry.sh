#!/usr/bin/env bash
# Smoke test for Darwin Core 005: tool-init / tool-list / tool-suggest.
# Run from the agent-darwin repo root with the venv active:
#   source .venv/bin/activate && bash scripts/smoke_test_tool_registry.sh

set -euo pipefail

DARWIN="darwin"
WORKSPACE="$(mktemp -d)"
trap 'rm -rf "$WORKSPACE"' EXIT

pass() { echo "  PASS: $1"; }
fail() { echo "  FAIL: $1"; exit 1; }
section() { echo; echo "=== $1 ==="; }

# tool-list before init prints clean error
section "tool-list before init"
cd "$WORKSPACE"
ERR_OUT=$($DARWIN tool-list 2>&1 || true)
echo "$ERR_OUT" | grep -qi "tool-init" || fail "tool-list before init should mention tool-init"
pass "tool-list before init gives clean message"

# tool-init creates .darwin/tools/
section "darwin tool-init"
$DARWIN tool-init
[ -d .darwin/tools ]                           || fail ".darwin/tools/ missing"
[ -f .darwin/tools/README.md ]                 || fail "README.md missing"
[ -f .darwin/tools/darwin_chunk_mcp.md ]       || fail "darwin_chunk_mcp.md missing"
[ -f .darwin/tools/context7_docs_mcp.md ]      || fail "context7_docs_mcp.md missing"
[ -f .darwin/tools/proxima_research_mcp.md ]   || fail "proxima_research_mcp.md missing"
[ -f .darwin/tools/github_mcp.md ]             || fail "github_mcp.md missing"
[ -f .darwin/tools/playwright_mcp.md ]         || fail "playwright_mcp.md missing"
[ -f .darwin/tools/chrome_devtools_mcp.md ]    || fail "chrome_devtools_mcp.md missing"
[ -f .darwin/tools/semgrep_mcp.md ]            || fail "semgrep_mcp.md missing"
[ -f .darwin/tools/osv_mcp.md ]                || fail "osv_mcp.md missing"
[ -f .darwin/tools/supabase_mcp.md ]           || fail "supabase_mcp.md missing"
[ -f .darwin/tools/postgres_mcp.md ]           || fail "postgres_mcp.md missing"
[ -f .darwin/tools/docker_mcp.md ]             || fail "docker_mcp.md missing"
[ -f .darwin/tools/opencode_worker.md ]        || fail "opencode_worker.md missing"
[ -f .darwin/tools/claude_code_worker.md ]     || fail "claude_code_worker.md missing"
[ -f .darwin/tools/codex_reviewer.md ]         || fail "codex_reviewer.md missing"
pass "tool-init creates all expected tool cards"

# tool-list shows tools
section "darwin tool-list"
LIST_OUT=$($DARWIN tool-list)
echo "$LIST_OUT" | grep -q "darwin_chunk_mcp"  || fail "tool-list missing darwin_chunk_mcp"
echo "$LIST_OUT" | grep -q "context7_docs_mcp" || fail "tool-list missing context7_docs_mcp"
echo "$LIST_OUT" | grep -q "opencode_worker"   || fail "tool-list missing opencode_worker"
echo "$LIST_OUT" | grep -q "codex_reviewer"    || fail "tool-list missing codex_reviewer"
echo "$LIST_OUT" | grep -q "Risk"              || fail "tool-list missing Risk field"
echo "$LIST_OUT" | grep -q "Approval"          || fail "tool-list missing Approval field"
pass "tool-list shows expected tools and fields"

# tool-suggest for React docs goal
section "darwin tool-suggest: React docs + build UI"
SUGGEST_OUT=$($DARWIN tool-suggest --goal "research latest React docs and build UI")
echo "$SUGGEST_OUT" | grep -q "context7_docs_mcp"  || fail "suggest missing context7_docs_mcp"
echo "$SUGGEST_OUT" | grep -qE "proxima_research_mcp|github_mcp" \
  || fail "suggest missing proxima_research_mcp or github_mcp"
echo "$SUGGEST_OUT" | grep -q "claude_code_worker" || fail "suggest missing claude_code_worker"
echo "$SUGGEST_OUT" | grep -qi "suggestion only"   || fail "suggest missing disclaimer"
pass "tool-suggest recommends expected tools for React/docs/build goal"

# idempotency: user edits survive rerun
section "tool-init idempotency and no-overwrite"
echo "CUSTOM USER NOTE: my edit" >> .darwin/tools/darwin_chunk_mcp.md
$DARWIN tool-init
grep -q "CUSTOM USER NOTE: my edit" .darwin/tools/darwin_chunk_mcp.md \
  || fail "tool-init overwrote user-edited darwin_chunk_mcp.md"
INIT_OUT=$($DARWIN tool-init)
echo "$INIT_OUT" | grep -q "exists:" || fail "second run should show 'exists:' for all files"
pass "tool-init does not overwrite existing cards"

# darwin status mentions tools
section "darwin status mentions .darwin/tools/"
STATUS_OUT=$($DARWIN status)
echo "$STATUS_OUT" | grep -q "tools" || fail "darwin status does not mention .darwin/tools/"
pass "darwin status mentions tool registry"

# darwin doctor exits cleanly
section "darwin doctor exits cleanly"
$DARWIN doctor > /dev/null 2>&1
pass "darwin doctor exits cleanly"

# doctor mentions tool registry smoke test
section "darwin doctor mentions tool registry smoke test"
DOCTOR_OUT=$($DARWIN doctor 2>&1)
echo "$DOCTOR_OUT" | grep -q "smoke_test_tool_registry.sh" \
  || fail "doctor missing smoke_test_tool_registry.sh"
pass "darwin doctor mentions smoke_test_tool_registry.sh"

# tool-suggest for security goal
section "darwin tool-suggest: security/vulnerability goal"
SEC_OUT=$($DARWIN tool-suggest --goal "scan for security vulnerabilities in dependencies")
echo "$SEC_OUT" | grep -qE "semgrep_mcp|osv_mcp" || fail "suggest missing semgrep/osv for security goal"
pass "tool-suggest recommends security tools for vulnerability goal"

# tool-suggest for database goal
section "darwin tool-suggest: database goal"
DB_OUT=$($DARWIN tool-suggest --goal "inspect the database schema and run migrations")
echo "$DB_OUT" | grep -qE "supabase_mcp|postgres_mcp" || fail "suggest missing db tool for database goal"
pass "tool-suggest recommends DB tools for database goal"

# tool-suggest for OpenCode / MCP-heavy phrasing
section "darwin tool-suggest: OpenCode / MCP-heavy goal"
OPENCODE_OUT=$($DARWIN tool-suggest --goal "MCP-heavy multi-tool coding task")
echo "$OPENCODE_OUT" | grep -q "opencode_worker" || fail "suggest missing opencode_worker for MCP-heavy goal"
pass "tool-suggest recommends OpenCode worker for MCP-heavy goal"

# no metadata.yaml
section "no metadata.yaml"
[ -f metadata.yaml ] && fail "metadata.yaml must not exist"
find . -name "metadata.yaml" | grep -q . && fail "metadata.yaml found in workspace"
pass "no metadata.yaml"

section "ALL TOOL REGISTRY TESTS PASSED"
