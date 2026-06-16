# darwin

Darwin CLI workspace skeleton (Chunk 005).

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

**What it creates (only if missing):**

- `chunks/001-.../STEP.md` — goal, scope, inputs, outputs, acceptance criteria, notes
- `chunks/001-.../CONTEXT.md` — task summary, project state, files involved, constraints

**Error cases handled cleanly:**

- Chunk folder does not exist
- `TASK.md` is missing from the folder
