"""Worker Registry operations — worker-init, worker-list, worker-suggest."""

import re
from pathlib import Path

from darwin.common import RISK_ORDER, parse_card_field, write_if_missing

_WORKER_README = """\
# Darwin Worker Registry V0

This registry catalogs workers (agents) that Darwin may suggest for tasks.
It does not configure, install, or run any worker.

## Rules

- Workers are only selected when explicitly chosen by the user or planner.
- Approval is required before a high-risk worker starts.
- Secrets and sensitive repo contents must NOT be sent to external workers.

## Commands

```bash
darwin worker-init                              # create this registry (idempotent)
darwin worker-list                              # list workers with role/risk/approval
darwin worker-suggest --goal "<goal>"           # deterministic keyword suggestions
```

## How to use

1. Run `darwin worker-suggest --goal "<your goal>"` to get suggestions.
2. Review the risk and approval notes.
3. Select a worker manually before starting work.
4. Edit any worker card freely — `darwin worker-init` never overwrites existing cards.
"""

_WORKER_CARD_CLAUDE_CODE_BUILDER = """\
# Worker: claude_code_builder

## Role
Builder

## Best for
- Focused implementation chunks with narrow, well-defined scope
- Single-file or small multi-file changes
- Running smoke tests and verifying output

## Use when
- Goal is a specific, bounded coding or debugging task
- Scope is clear and fits in one chunk

## Do not use when
- Goal requires broad research before coding
- Goal is ambiguous or open-ended
- Multiple MCPs are required simultaneously

## Allowed tools
- Read, Edit, Write, Bash (local)
- 1-2 read-only MCPs max

## Forbidden tools
- No git push
- No secrets in scope
- No external account MCPs without approval

## Risk level
medium

## Approval required
yes

## Expected output
- Code changes, test output, file edits

## Notes
- Give minimal MCPs only
- Prefer read-only MCPs unless writes are explicitly required
"""

_WORKER_CARD_CODEX_REVIEWER = """\
# Worker: codex_reviewer

## Role
Reviewer

## Best for
- Strict code review and scope guard
- Verifying tests pass and acceptance criteria are met
- Requesting the smallest possible fix

## Use when
- A chunk result needs review before being accepted

## Do not use when
- Work is still in progress (review after completion only)

## Allowed tools
- Read only
- No file writes in review-only mode

## Forbidden tools
- No file edits in review-only mode (approval needed if patching)
- No external tools
- No LLM calls

## Risk level
low

## Approval required
no

## Expected output
- PASS or FAIL verdict with specific feedback

## Notes
- Approval not required for review-only mode
- Approval yes if also patching files
"""

_WORKER_CARD_OPENCODE_PLAN = """\
# Worker: opencode_plan

## Role
Planner

## Best for
- Planning, tool routing, architecture design
- Deciding which workers and tools to use for a goal
- Breaking a complex goal into safe chunks

## Use when
- Goal requires multi-step planning before building
- Tool selection is unclear

## Do not use when
- Goal is already clear and scoped (go straight to builder)

## Allowed tools
- Read only
- No file writes

## Forbidden tools
- No edits
- No external accounts without approval
- No git push

## Risk level
medium

## Approval required
no

## Expected output
- Plan document, tool routing recommendations, chunk breakdown

## Notes
- Planning only; does not build or execute
"""

_WORKER_CARD_OPENCODE_BUILD = """\
# Worker: opencode_build

## Role
Builder (MCP-heavy)

## Best for
- MCP-heavy coding tasks requiring multiple tools in parallel
- Multi-agent execution and tool routing
- Non-interactive headless coding runs

## Use when
- Goal requires 3+ MCPs active simultaneously
- Goal is well-specified and bounded

## Do not use when
- Goal is narrow and can be done with claude_code_builder alone
- Goal is unclear or open-ended
- Any high-risk MCP would be active without approval

## Allowed tools
- As specified in permission profile
- Max 3 MCPs, max 1 high-risk

## Forbidden tools
- No git push
- No secrets in scope
- No full repo to external tools without approval

## Risk level
high

## Approval required
yes

## Expected output
- Code changes, file writes, test results (scoped to task)

## Notes
- Status: planned / not yet integrated
- Requires explicit permission profile before first run
"""

_WORKER_CARD_OPENCODE_EXPLORE = """\
# Worker: opencode_explore

## Role
Explorer

## Best for
- Repo exploration and understanding
- Finding files, symbols, and patterns in a codebase
- Answering "where is X defined" questions

## Use when
- Goal is to understand the current state of a codebase

## Do not use when
- Editing or writing files
- External tools needed

## Allowed tools
- Read, Bash (read-only), grep

## Forbidden tools
- No edits
- No external accounts

## Risk level
low

## Approval required
no

## Expected output
- File listings, symbol locations, pattern summaries

## Notes
- Read-only; safe to run without approval
"""

_WORKER_CARD_OPENCODE_SCOUT = """\
# Worker: opencode_scout

## Role
Researcher

## Best for
- Documentation research and dependency scouting
- Finding latest package versions and API docs
- Comparing frameworks or external repos

## Use when
- Goal explicitly requires up-to-date external information
- External docs or packages must be checked

## Do not use when
- Goal is purely local code work
- No external information is needed

## Allowed tools
- Read, web search (with approval)
- External MCPs require approval

## Forbidden tools
- No edits without approval
- No secrets in scope

## Risk level
medium

## Approval required
yes (for external tool use)

## Expected output
- Research summaries, doc excerpts, version comparisons

## Notes
- Status: planned / not yet integrated
- External tools require explicit approval before first use
"""

_WORKER_CARD_MOHIT_SUPREME_JUDGE = """\
# Worker: mohit_supreme_judge

## Role
Judge

## Best for
- Final product and direction approval
- High-risk decisions that affect production or external accounts
- Commit, release, and external account approval

## Use when
- A decision is irreversible or high-stakes
- A commit or release requires sign-off
- Paid/external account access is required

## Do not use when
- Decision is low-risk and reversible
- Work is still in progress

## Allowed tools
- All (judge has final authority)

## Forbidden tools
- None (but judge must approve any dangerous action explicitly)

## Risk level
high

## Approval required
yes — Mohit must approve explicitly

## Expected output
- Explicit APPROVE or REJECT decision with reason

## Notes
- This is a human-in-the-loop gate, not an automated worker
- No action proceeds without explicit judge approval
"""

_WORKER_CARDS: dict[str, str] = {
    "README.md": _WORKER_README,
    "claude_code_builder.md": _WORKER_CARD_CLAUDE_CODE_BUILDER,
    "codex_reviewer.md": _WORKER_CARD_CODEX_REVIEWER,
    "opencode_plan.md": _WORKER_CARD_OPENCODE_PLAN,
    "opencode_build.md": _WORKER_CARD_OPENCODE_BUILD,
    "opencode_explore.md": _WORKER_CARD_OPENCODE_EXPLORE,
    "opencode_scout.md": _WORKER_CARD_OPENCODE_SCOUT,
    "mohit_supreme_judge.md": _WORKER_CARD_MOHIT_SUPREME_JUDGE,
}

_WORKER_KEYWORD_MAP: dict[str, dict] = {
    "claude_code_builder": {
        "keywords": {"build", "implement", "code", "fix", "create"},
        "risk": "medium",
        "approval": "yes",
    },
    "codex_reviewer": {
        "keywords": {"review", "test", "verify", "scope", "bug"},
        "risk": "low",
        "approval": "no",
    },
    "opencode_plan": {
        "keywords": {"plan", "architecture", "design", "routing", "route"},
        "risk": "medium",
        "approval": "no",
    },
    "opencode_build": {
        "keywords": {"opencode", "mcp", "multi-tool", "routing"},
        "risk": "high",
        "approval": "yes",
    },
    "opencode_explore": {
        "keywords": {"inspect", "explore", "find", "search", "repo"},
        "risk": "low",
        "approval": "no",
    },
    "opencode_scout": {
        "keywords": {"docs", "research", "latest", "framework", "package"},
        "risk": "medium",
        "approval": "yes",
    },
    "mohit_supreme_judge": {
        "keywords": {"commit", "release", "dangerous", "external", "paid", "high risk", "approve"},
        "risk": "high",
        "approval": "yes",
    },
}


def op_worker_init(base: Path) -> dict:
    workers_dir = base / ".darwin" / "workers"
    workers_dir.mkdir(parents=True, exist_ok=True)
    created = []
    existing = []
    for filename, content in _WORKER_CARDS.items():
        status = write_if_missing(workers_dir / filename, content)
        if status == "created":
            created.append(filename)
        else:
            existing.append(filename)
    return {"workers_dir": str(workers_dir), "created": created, "existing": existing}


def op_worker_list(base: Path) -> dict:
    workers_dir = base / ".darwin" / "workers"
    if not workers_dir.exists():
        return {
            "initialized": False,
            "message": "Worker registry not initialized. Run: darwin worker-init",
        }
    workers = []
    for path in sorted(workers_dir.glob("*.md")):
        if path.name == "README.md":
            continue
        try:
            text = path.read_text()
        except Exception:
            text = ""
        workers.append({
            "filename": path.name,
            "name": path.stem,
            "role": parse_card_field(text, "Role"),
            "risk": parse_card_field(text, "Risk level"),
            "approval": parse_card_field(text, "Approval required"),
        })
    return {
        "initialized": True,
        "workers_dir": str(workers_dir),
        "workers": workers,
        "count": len(workers),
    }


def op_worker_suggest(base: Path, goal: str) -> dict:
    goal_lower = goal.lower()
    normalized_goal = re.sub(r"[^a-z0-9]+", " ", goal_lower)
    goal_words = set(re.findall(r"[a-z0-9]+", goal_lower))
    matches: list[dict] = []
    for worker_name, info in _WORKER_KEYWORD_MAP.items():
        hit_words = sorted(info["keywords"] & goal_words)
        if not hit_words:
            phrase_hits = [
                kw for kw in info["keywords"]
                if " " in kw and kw in normalized_goal
            ]
            if not phrase_hits:
                continue
            hit_words = phrase_hits
        matches.append({
            "worker": worker_name,
            "matched_keywords": hit_words,
            "risk": info["risk"],
            "approval": info["approval"],
        })
    matches.sort(key=lambda m: (RISK_ORDER.get(m["risk"], 9), m["worker"]))
    return {
        "goal": goal,
        "matches": matches,
        "total_matched": len(matches),
        "disclaimer": "This is a suggestion only. It does not configure or run workers.",
    }
