# darwin

Darwin CLI — Chunk OS V1. Breaks a master plan into numbered chunks, prepares
working files for each chunk, records results, and tracks memory across the
full loop.

## Install

The system Python may be externally managed, so install inside a virtual
environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

## Full V1 Workflow

```bash
# 1. Set up workspace
darwin init

# 2. Write your plan (edit MASTER_PLAN.md with bullet tasks)
#    - Build the CLI skeleton
#    - Add the split-plan command
#    - ...

# 3. Split plan into chunks
darwin split-plan MASTER_PLAN.md

# 4. Find the next chunk to work on
darwin next-chunk

# 5. Prepare working files for that chunk
darwin prepare-chunk chunks/001-build-the-cli-skeleton

# 6. Do the work
#    - Read CLAUDE_PROMPT.md and paste it into Claude Code
#    - Read CODEX_REVIEW_PROMPT.md and paste it into your reviewer

# 7. Record the outcome
darwin record-result chunks/001-build-the-cli-skeleton --status pass --notes "all tests passed"

# 8. Run a local file review
darwin review-chunk chunks/001-build-the-cli-skeleton

# 9. Update memory and mark the chunk done in ROADMAP
darwin update-memory chunks/001-build-the-cli-skeleton

# 10. Move to the next chunk
darwin next-chunk
```

---

## Commands

### `darwin init`

Sets up the workspace in the current directory. Safe to run more than once —
never overwrites existing files.

**Folders created:** `chunks/` `memory/` `templates/` `reports/`

**Starter files created (only if missing):**
`MASTER_PLAN.md`, `ROADMAP.md`, `memory/mistakes.md`, `memory/winners.md`,
`memory/decisions.md`

---

### `darwin split-plan MASTER_PLAN.md`

Reads bullet tasks (`- ` or `* `) from the plan, creates `chunks/NNN-slug/`
folders with `TASK.md`, and regenerates `ROADMAP.md`. Existing `TASK.md` files
are never overwritten.

```bash
darwin split-plan MASTER_PLAN.md
```

---

### `darwin next-chunk`

Reads `ROADMAP.md` and prints the first unchecked `- [ ]` chunk.

```bash
darwin next-chunk
# next chunk:  001 — Build the CLI skeleton
# path:        chunks/001-build-the-cli-skeleton
# run:         darwin prepare-chunk chunks/001-build-the-cli-skeleton
```

---

### `darwin prepare-chunk <chunk_path>`

Creates all working files inside a chunk folder (only if missing):

| File | Purpose |
|---|---|
| `STEP.md` | Goal, scope, inputs, outputs, acceptance criteria |
| `CONTEXT.md` | Task summary, project state, files involved, constraints |
| `CLAUDE_PROMPT.md` | Ready-to-paste prompt for Claude |
| `CODEX_REVIEW_PROMPT.md` | Strict reviewer prompt — outputs PASS or FAIL |
| `ACCEPTANCE.md` | Human sign-off checklist |
| `TESTS.md` | Test commands: install, run, idempotency, error cases |

---

### `darwin record-result <chunk_path> --status <status> --notes <notes>`

Appends a timestamped result entry to `RESULT.md`. Never overwrites.

```bash
darwin record-result chunks/001-build-the-cli-skeleton --status pass --notes "tests green"
darwin record-result chunks/001-build-the-cli-skeleton --status fail --notes "missing output"
darwin record-result chunks/001-build-the-cli-skeleton --status blocked --notes "waiting on upstream"
```

---

### `darwin review-chunk <chunk_path>`

Checks required files, optional files, and forbidden files; writes a
timestamped verdict to `REVIEW.md`. Appends on repeated runs.

**Required:** `TASK.md` `STEP.md` `CONTEXT.md` `CLAUDE_PROMPT.md`
`CODEX_REVIEW_PROMPT.md` `ACCEPTANCE.md` `TESTS.md`

**Forbidden:** `MEMORY_UPDATE.md` `metadata.yaml`

Verdict is `PASS` only when all required files are present and no forbidden
files exist.

---

### `darwin update-memory <chunk_path>`

Reads the latest status from `RESULT.md` and verdict from `REVIEW.md`, then:

| Outcome | Actions |
|---|---|
| result=pass AND review=PASS | appends to `memory/winners.md` + `memory/decisions.md`; marks ROADMAP `[x]` |
| result=fail/blocked OR review=FAIL | appends to `memory/mistakes.md` + `memory/decisions.md`; ROADMAP unchanged |

```bash
darwin update-memory chunks/001-build-the-cli-skeleton
```

---

## Status / Doctor / Version

Quick commands to verify Darwin is healthy before starting work.

```bash
darwin version
darwin status
darwin doctor
```

### `darwin version`

Prints the installed Darwin version from package metadata.

```
darwin version 0.2.0
```

### `darwin status`

Read-only. Shows the current workspace layout and the installed Darwin feature level. Useful when switching between projects.

```bash
darwin status
# Darwin Status
# =============
# CWD: /path/to/project
# git: yes (.git found)
#
# Project files:
#   [x] pyproject.toml
#   [x] README.md
#
# Workspace directories:
#   [x] chunks/
#   [x] memory/
#   [ ] evals/
#   [ ] .darwin/
#   [x] scripts/
#
# Smoke tests:
#   [x] scripts/smoke_test_chunk_os.sh
#   [x] scripts/smoke_test_mcp_tools.py
#   [x] scripts/smoke_test_eval_harness.sh
#   [x] scripts/smoke_test_repo_intake.sh
#   [x] scripts/smoke_test_status_doctor.sh
#
# Darwin level: 4 — Existing Repo Intake V0
```

### `darwin doctor`

Read-only. Checks Python version, package imports, entry point registration, optional MCP SDK, smoke test file presence, and absence of forbidden files. Does **not** run smoke tests. Prints `PASS`, `WARN`, or `FAIL` per check.

```bash
darwin doctor
# Darwin Doctor
# =============
# [PASS] Python 3.11.x >= 3.9
# [PASS] darwin package importable
# [PASS] typer importable
# [PASS] darwin CLI entry point
# [WARN] MCP SDK (optional) — not installed — run: pip install darwin[mcp]
# [WARN] scripts/smoke_test_chunk_os.sh — not found in current directory
# ...
# Summary: 9 PASS, 5 WARN, 0 FAIL
```

`WARN` means non-critical (e.g. MCP not installed, running from a directory that isn't the repo root). `FAIL` means something is broken.

---

## Tool Registry V0

A local deterministic catalog of tools, MCPs, and workers that Darwin may suggest for a task. Does not install, configure, or run any tool.

```bash
darwin tool-init                             # create .darwin/tools/ (idempotent)
darwin tool-list                             # list all cards with type/risk/approval
darwin tool-suggest --goal "build React UI"  # keyword-based suggestions
```

### What it does

- `tool-init` creates one Markdown card per tool under `.darwin/tools/`. Cards describe type, risk level, when to wake a tool, and whether approval is required. Never overwrites existing cards — user edits survive reruns.
- `tool-list` reads all cards and prints a table of name / type / risk / approval.
- `tool-suggest` matches your goal against a built-in keyword map and returns up to 5 suggestions with risk and approval notes. Fully deterministic — no LLM, no network.

### What it does NOT do

- Does not install any MCP server.
- Does not configure OpenCode or any agent.
- Does not run any tool.
- Does not call any network or LLM API.

### Registered tools

| Card | Type | Risk |
|---|---|---|
| `darwin_chunk_mcp.md` | MCP / Internal | low |
| `context7_docs_mcp.md` | MCP | medium |
| `proxima_research_mcp.md` | MCP | high |
| `github_mcp.md` | MCP | medium |
| `playwright_mcp.md` | MCP | medium |
| `chrome_devtools_mcp.md` | MCP | medium |
| `semgrep_mcp.md` | MCP | medium |
| `osv_mcp.md` | MCP | medium |
| `supabase_mcp.md` | MCP | high |
| `postgres_mcp.md` | MCP | high |
| `docker_mcp.md` | MCP | high |
| `opencode_worker.md` | Worker | high |
| `claude_code_worker.md` | Worker | medium |
| `codex_reviewer.md` | Reviewer | low |

`darwin doctor` warns if `.darwin/` exists without a `.darwin/tools/` directory.

---

## Spec Surface V0

A read-only contract document describing exactly what Darwin supports, which scenarios are protected, and which commands have smoke test coverage. Run once per repo.

```bash
darwin spec-init    # create .darwin/spec/ (idempotent, never overwrites)
darwin spec-status  # show spec file presence and protected command count
```

### Files created under `.darwin/spec/`

| File | Contents |
|---|---|
| `SPEC_SURFACE.md` | Project name, Darwin level, supported command groups, unsupported features |
| `SCENARIOS.md` | Each protected user scenario with its smoke test reference |
| `PROTECTED_COMMANDS.md` | Every Darwin command mapped to its covering smoke test |

User edits to these files survive a rerun of `spec-init`.

`darwin doctor` warns (but does not fail) if `.darwin/` exists without a `.darwin/spec/` directory.

---

## Existing Repo Intake V0

Inspect an existing project and let Darwin build a `.darwin/` understanding pack
before any coding starts. No LLM calls — deterministic file scanning only.

```bash
darwin inspect-repo . --goal "improve CLI tests"
darwin inspect-repo /path/to/project --goal "add authentication"
```

### Output files

| File | Contents |
|---|---|
| `.darwin/PROJECT_BRIEF.md` | Repo path, user goal, detected project type, summary, timestamp |
| `.darwin/REPO_MAP.md` | Top-level file tree (noisy dirs excluded) and important files |
| `.darwin/COMMANDS.md` | Detected install / test / run commands with caveats |
| `.darwin/RISK_LIST.md` | Missing README, missing tests, no lockfile, etc. |
| `.darwin/UNKNOWN_QUESTIONS.md` | What Darwin could not determine; questions to answer before coding |
| `.darwin/MASTER_PLAN_DRAFT.md` | Chunkable bullet plan based on goal and repo scan |

All files are written only if they do not already exist — user edits survive a
rerun. Safe to run more than once.

### Detected signals

- Python: `pyproject.toml`, `requirements.txt`, `setup.py`
- Node / Vite: `package.json`, `vite.config.*`
- Git, README, `scripts/`, `tests/` directories
- `package.json` scripts block (install, test, dev/start)
- Python project name and `[project.scripts]` console entry points from `pyproject.toml`

---

## Darwin Eval Harness V0

No Darwin module becomes permanent unless it beats baseline.

The eval harness gives you a structured way to score any Darwin module against
a defined task before you trust it in production. V0 is intentionally simple:
manual scoring, no LLM judging, no network calls.

### Setup

```bash
darwin eval-init
```

Creates `evals/` with task definitions, run history, reports, and baselines
directories. Safe to rerun — existing task files are never overwritten.

### Commands

```bash
# Initialise eval structure (idempotent)
darwin eval-init

# List available eval tasks
darwin eval-list

# Run an eval and generate a scorecard template
darwin eval-run repo_intake_basic --candidate darwin-v0

# Print the latest eval report
darwin eval-report
```

### Scorecard fields

Each run produces a scorecard with these fields to fill in manually:

| Metric | Description |
|---|---|
| Functional correctness `/10` | Did it do what was asked? |
| Useful output `/10` | Was the output actually useful? |
| False assumption penalty `/10` | 10 = no false assumptions |
| Overbuild penalty `/10` | 10 = no overbuild |
| Human confidence `/10` | How confident are you in this result? |
| Safety | PASS or FAIL |
| Verdict | KEEP / FIX / KILL |

### Eval file layout

```
evals/
  tasks/          ← task definitions (edit freely)
  runs/           ← timestamped run reports
  reports/        ← latest.md always points to most recent run
  baselines/      ← optional baseline files per task
  README.md
```

---

## Smoke Tests

```bash
source .venv/bin/activate
bash scripts/smoke_test_chunk_os.sh        # full CLI loop
bash scripts/smoke_test_repo_intake.sh     # repo intake
bash scripts/smoke_test_eval_harness.sh    # eval harness
bash scripts/smoke_test_status_doctor.sh   # version / status / doctor
bash scripts/smoke_test_spec_surface.sh    # spec-init / spec-status
bash scripts/smoke_test_tool_registry.sh   # tool-init / tool-list / tool-suggest
python scripts/smoke_test_mcp_tools.py     # MCP tool functions
```

---

## Using Chunk OS through MCP

Darwin exposes all Chunk OS operations as MCP tools so Claude Code and other
MCP-capable agents can drive the full loop without a shell.

### Install

```bash
pip install "darwin[mcp]"
```

### Start the server

```bash
darwin-mcp
# or
python -m darwin.mcp_server
```

### Add to Claude Code

```json
{
  "mcpServers": {
    "darwin": {
      "command": "darwin-mcp"
    }
  }
}
```

### Available MCP tools

| Tool | Description |
|---|---|
| `list_chunks(project_path)` | List all chunk folders |
| `next_chunk(project_path)` | First unchecked chunk from ROADMAP.md |
| `prepare_chunk(project_path, chunk_path)` | Create STEP.md, CLAUDE_PROMPT.md, etc. |
| `read_chunk_files(project_path, chunk_path)` | Return all file contents in a chunk |
| `get_builder_prompt(project_path, chunk_path)` | Return CLAUDE_PROMPT.md content |
| `get_review_prompt(project_path, chunk_path)` | Return CODEX_REVIEW_PROMPT.md content |
| `record_result(project_path, chunk_path, status, notes)` | Record pass/fail/blocked |
| `review_chunk(project_path, chunk_path)` | Run local file checks, write REVIEW.md |
| `update_memory(project_path, chunk_path)` | Update memory files, mark ROADMAP done |

All tools are read/write local file operations only — no network calls, no LLM
API calls, no shell execution. Chunk paths must stay inside the supplied
project path; `..` path escapes are rejected.
