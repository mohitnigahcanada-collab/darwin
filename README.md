# darwin

Darwin CLI workspace skeleton (Chunk 003).

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
- `ROADMAP.md` — placeholder (roadmap not generated yet)
- `memory/mistakes.md`
- `memory/winners.md`
- `memory/decisions.md`

### `darwin split-plan MASTER_PLAN.md`

Reads the given markdown file, extracts all bullet tasks (lines starting with
`- ` or `* `), prints them numbered to the terminal, and writes `ROADMAP.md`.

```bash
darwin split-plan MASTER_PLAN.md
```

Example output:

```
Found 3 task(s):

  001 — Build the smallest CLI skeleton
  002 — Set up the workspace files
  003 — Add the split-plan command

written: ROADMAP.md (3 task(s))
```

`ROADMAP.md` is always overwritten by this command (it is regenerated from
the plan). `MASTER_PLAN.md` is never modified.
