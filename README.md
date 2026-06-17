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

## Smoke Test

```bash
source .venv/bin/activate
bash scripts/smoke_test_chunk_os.sh
```

Runs a full V1 loop in a temp directory and verifies all acceptance criteria.
