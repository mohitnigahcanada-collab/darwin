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
- `ROADMAP.md` — placeholder
- `memory/mistakes.md`
- `memory/winners.md`
- `memory/decisions.md`

### `darwin split-plan MASTER_PLAN.md`

Reads the given markdown file, extracts all bullet tasks (lines starting with
`- ` or `* `), prints them numbered to the terminal, and writes `ROADMAP.md`.

```bash
darwin split-plan MASTER_PLAN.md
```

`ROADMAP.md` is always regenerated from the current plan. `MASTER_PLAN.md` is
never modified.

Example `ROADMAP.md` output:

```markdown
# Roadmap

## Pending Tasks

- [ ] 001 — Build the CLI skeleton
- [ ] 002 — Set up workspace files
```
