# darwin

Darwin CLI workspace skeleton (Chunk 007).

## Install

The system Python may be externally managed, so install inside a virtual
environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

## Commands

### `darwin init`

Sets up the workspace in the current directory. Safe to run more than once —
never overwrites existing files.

**Folders created:**

- `chunks/`
- `memory/`
- `templates/`
- `reports/`

**Starter files created (only if they do not already exist):**

- `MASTER_PLAN.md` — short example plan
- `ROADMAP.md` — placeholder
- `memory/mistakes.md`
- `memory/winners.md`
- `memory/decisions.md`

### `darwin split-plan MASTER_PLAN.md`

Reads the given markdown file, extracts all bullet tasks (lines starting with
`- ` or `* `), creates a numbered chunk folder for each task under `chunks/`,
writes `TASK.md` in each folder, and regenerates `ROADMAP.md`.

```bash
darwin split-plan MASTER_PLAN.md
```

**What it creates:**

- `chunks/001-task-slug/TASK.md`
- `chunks/002-task-slug/TASK.md`
- …
- `ROADMAP.md` (always regenerated from the current plan)

**Idempotent:** running it twice does not crash. Existing `TASK.md` files are
never overwritten. `MASTER_PLAN.md` is never modified.

Example `ROADMAP.md` output:

```markdown
# Roadmap

## Pending Tasks

- [ ] 001 — Create project skeleton — `chunks/001-create-project-skeleton/`
- [ ] 002 — Add CLI init command — `chunks/002-add-cli-init-command/`
```

### `darwin prepare-chunk <chunk_path>`

Reads `TASK.md` from an existing chunk folder and creates `STEP.md` and
`CONTEXT.md` inside it. Safe to run more than once — existing files are never
overwritten.

```bash
darwin prepare-chunk chunks/001-create-project-skeleton
```

**What it creates inside the chunk folder (only if missing):**

| File | Purpose |
|---|---|
| `STEP.md` | Goal, scope, inputs, outputs, acceptance criteria, notes |
| `CONTEXT.md` | Task summary, project state, files involved, constraints |
| `CLAUDE_PROMPT.md` | Ready-to-paste prompt for Claude to implement the chunk |
| `CODEX_REVIEW_PROMPT.md` | Strict reviewer prompt — outputs PASS or FAIL |
| `ACCEPTANCE.md` | Human checklist to sign off the chunk |
| `TESTS.md` | Test commands: install, run, idempotency, error cases |

All files are **never overwritten** — user edits survive re-runs.

**Error cases handled cleanly:**

- Chunk folder does not exist
- `TASK.md` is missing from the folder

### `darwin record-result <chunk_path> --status <status> --notes <notes>`

Records a timestamped result entry for a chunk. Appends to `RESULT.md` if it
already exists — never erases previous entries.

```bash
darwin record-result chunks/001-create-project-skeleton --status pass --notes "all tests passed"
darwin record-result chunks/001-create-project-skeleton --status fail --notes "missing output file"
```

**Allowed statuses:** `pass`, `fail`, `blocked`

### `darwin review-chunk <chunk_path>`

Runs local file checks on a chunk and writes a timestamped checklist to
`REVIEW.md`. Appends on repeated runs — never erases previous reviews.

```bash
darwin review-chunk chunks/001-create-project-skeleton
```

**Checks performed:**

- Required files present: `TASK.md`, `STEP.md`, `CONTEXT.md`, `CLAUDE_PROMPT.md`, `CODEX_REVIEW_PROMPT.md`, `ACCEPTANCE.md`, `TESTS.md`
- Optional: `RESULT.md`
- Forbidden (must not exist): `MEMORY_UPDATE.md`, `metadata.yaml`

**Verdict:** `PASS` if all required files exist and no forbidden files are present; `FAIL` otherwise.
