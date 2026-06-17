"""Brain config, status, and route operations — Multi-Brain Operator V0."""

import os
from pathlib import Path

from darwin.common import now, write_if_missing

# ── Provider definitions ───────────────────────────────────────────────────────

_PROVIDERS = {
    "groq": {
        "env_key": "GROQ_API_KEY",
        "env_model": "DARWIN_GROQ_MODEL",
        "env_base_url": "DARWIN_GROQ_BASE_URL",
        "default_model": "llama-3.1-8b-instant",
        "role": "Reflex Router / Fast Summarizer",
    },
    "openrouter": {
        "env_key": "OPENROUTER_API_KEY",
        "env_model": "DARWIN_OPENROUTER_MODEL",
        "env_base_url": "DARWIN_OPENROUTER_BASE_URL",
        "default_model": "anthropic/claude-3-haiku",
        "role": "Deep Planner / Fallback Marketplace",
    },
    "poolside": {
        "env_key": "POOLSIDE_API_KEY",
        "env_model": "DARWIN_POOLSIDE_MODEL",
        "env_base_url": "DARWIN_POOLSIDE_BASE_URL",
        "default_model": "poolside-malibu",
        "role": "Coding Brain / Engineering Planner",
    },
    "nvidia": {
        "env_key": "NVIDIA_API_KEY",
        "env_model": "DARWIN_NVIDIA_MODEL",
        "env_base_url": "DARWIN_NVIDIA_BASE_URL",
        "default_model": "nvidia/llama-3.1-nemotron-70b-instruct",
        "role": "Stable Structured Brain / Fallback",
    },
}

# ── Brain init file templates ──────────────────────────────────────────────────

_BRAIN_MD = """\
# Darwin Brain

## What Is Darwin Brain?

Darwin Brain is **optional**. The default mode is **off**.

Darwin Brain helps with:
- Planning and routing tasks to the right worker
- Summarizing repo state and goals
- Generating prompts for body workers
- Classifying risk and task type
- Judging results (with Mohit as Supreme Judge)

## What Darwin Brain Does NOT Do

- Brain does NOT execute tools.
- Brain does NOT run Claude Code.
- Brain does NOT run OpenCode.
- Brain does NOT run Codex.
- Brain does NOT commit code.
- Brain does NOT push to git.
- Brain does NOT manage external accounts.

## Brain vs Body vs Hands vs Nerves

```
Brain  = AI providers (Groq, OpenRouter, Poolside, NVIDIA) — plan and route
Body   = Workers (Claude Code, OpenCode, Codex, Mohit) — build and review
Hands  = MCP tools — later
Nerves = A2A/ACP — later
```

## Default Mode

The default brain mode is `off`. Darwin works fully offline and deterministically
with `--brain off`. No API keys are required.

## Changing Brain Mode

Pass `--brain <mode>` to commands that support it:

```bash
darwin brain-route --goal "add tests" --brain off
darwin brain-route --goal "add tests" --brain auto
darwin operate-existing /path/to/repo --goal "add tests" --brain off
darwin operate-existing /path/to/repo --goal "add tests" --brain auto
```

Valid modes: off, auto, groq, openrouter, poolside, nvidia

## Mohit Supreme Judge

Mohit is the final approval gate for all commits, releases, deploys, and
destructive actions. No brain or body worker can bypass this.
"""

_PROVIDERS_MD = """\
# Darwin Brain Providers

## Supported Providers

| Name        | Role                              | API Key Env Var        |
|-------------|-----------------------------------|------------------------|
| groq        | Reflex Router / Fast Summarizer   | GROQ_API_KEY           |
| openrouter  | Deep Planner / Fallback Market    | OPENROUTER_API_KEY     |
| poolside    | Coding Brain / Engineering Plan   | POOLSIDE_API_KEY       |
| nvidia      | Stable Structured Brain / Fallback| NVIDIA_API_KEY         |

## API Keys

**API keys must be environment variables only.** Never write keys into `.darwin/`.
Never print keys. Never commit keys.

Required environment variable names:

```
GROQ_API_KEY
OPENROUTER_API_KEY
POOLSIDE_API_KEY
NVIDIA_API_KEY
```

## Optional Configuration

Override model or base URL per provider:

```
DARWIN_GROQ_MODEL
DARWIN_OPENROUTER_MODEL
DARWIN_POOLSIDE_MODEL
DARWIN_NVIDIA_MODEL

DARWIN_GROQ_BASE_URL
DARWIN_OPENROUTER_BASE_URL
DARWIN_POOLSIDE_BASE_URL
DARWIN_NVIDIA_BASE_URL
```

## Setting Keys

```bash
export GROQ_API_KEY="your-key-here"
darwin brain-status  # confirm key present (never prints values)
```

## No Hardcoded Keys

Darwin will never store, print, or log API key values.
Run `darwin brain-status` to see which keys are configured (yes/no only).
"""

_SAFETY_MD = """\
# Darwin Brain Safety Rules

These rules apply to all brain API calls. Darwin enforces them automatically.

## What Darwin Brain Never Sends

- Never sends `.env` files or environment variable values
- Never sends private keys, secrets, or credentials
- Never sends full repository contents by default
- Never sends `.git/` directory contents
- Never sends `node_modules/`
- Never sends hidden files by default

## What Darwin Brain May Send

- Compact repo summary (project type, top-level structure, detected commands)
- User goal (text only)
- Detected project signals (is Python, is Node, has tests, etc.)
- Safety rules (this file)

## What Darwin Brain Never Does

- Never executes tools on your behalf
- Never performs external account actions
- Never runs git commit or git push
- Never deploys code
- Never modifies files in the target repo directly via API

## Approval Gates

Any action involving:
- git commit / push / release / deploy
- database migrations
- external accounts
- paid services
- destructive operations

...requires **Mohit Supreme Judge** approval before execution.

## Safe Mode Guarantee

`--brain off` is always available and requires no API calls.
All Darwin commands work fully offline in `--brain off` mode.
"""

_ROLES_MD = """\
# Darwin Brain Roles

## Role Definitions

### Reflex Router Brain
- Provider: Groq (fast inference)
- Use for: quick task classification, cheap summarization, routing decisions
- Not for: deep code analysis, architecture planning

### Planner Brain
- Provider: OpenRouter (marketplace access)
- Use for: deep planning, architecture decisions, multi-step routing
- Not for: low-latency reflex decisions

### Coding Brain
- Provider: Poolside Laguna (code-specialized)
- Use for: code strategy, implementation planning, engineering decisions
- Not for: general routing or administrative tasks

### Critic/Judge Brain
- Provider: NVIDIA NIM (stable, structured)
- Use for: structured output, fallback routing, review scoring
- Not for: fast reflex decisions

### Memory/Summarizer Brain
- Provider: Groq or OpenRouter (depending on depth)
- Use for: summarizing long context, compressing repo state, building prompts
- Not for: final judgment calls

### Mohit Supreme Judge
- Provider: Human (Mohit)
- Use for: final approval of all commits, releases, deploys, destructive actions
- Always required for: git push, production deploys, schema migrations, paid account actions
- Cannot be bypassed by any brain or body worker

## Provider → Role Mapping

| Provider   | Primary Role          | Secondary Role         |
|------------|----------------------|------------------------|
| Groq       | Reflex Router        | Fast Summarizer        |
| OpenRouter | Deep Planner         | Fallback Marketplace   |
| Poolside   | Coding Brain         | Engineering Planner    |
| NVIDIA NIM | Stable/Structured    | Fallback Brain         |
| Mohit      | Supreme Judge        | Final Approval         |

## Darwin Body Workers (Not Brain)

Brain plans and routes. Body executes.

| Worker              | Role                        | When Used             |
|--------------------|-----------------------------|-----------------------|
| Claude Code Builder | Build / Implement / Fix     | code/build tasks      |
| OpenCode Plan       | Planning / Architecture     | plan/design tasks     |
| OpenCode Build      | Build with tool access      | after approval        |
| OpenCode Scout      | Research / Explore          | docs/research tasks   |
| Codex Reviewer      | Review / Test / Verify      | review stage          |
| Mohit Supreme Judge | Final approval              | always, at commit     |
"""

# ── Brain init ─────────────────────────────────────────────────────────────────


def op_brain_init(base: Path) -> dict:
    """Create .darwin/brain/ with starter files. Never overwrites existing files."""
    brain_dir = base / ".darwin" / "brain"
    brain_dir.mkdir(parents=True, exist_ok=True)

    files = {
        "BRAIN.md": _BRAIN_MD,
        "PROVIDERS.md": _PROVIDERS_MD,
        "SAFETY.md": _SAFETY_MD,
        "ROLES.md": _ROLES_MD,
    }
    created = []
    existing = []
    for filename, content in files.items():
        status = write_if_missing(brain_dir / filename, content)
        if status == "created":
            created.append(filename)
        else:
            existing.append(filename)

    return {
        "brain_dir": str(brain_dir),
        "created": created,
        "existing": existing,
    }


# ── Brain status ───────────────────────────────────────────────────────────────


def op_brain_status(base: Path) -> dict:
    """Read brain config status. Never prints API key values."""
    brain_dir = base / ".darwin" / "brain"
    brain_present = brain_dir.exists()

    provider_status = {}
    for name, info in _PROVIDERS.items():
        key_var = info["env_key"]
        key_present = bool(os.environ.get(key_var, "").strip())
        model_var = info["env_model"]
        model_val = os.environ.get(model_var, "").strip()
        base_url_var = info["env_base_url"]
        base_url_present = bool(os.environ.get(base_url_var, "").strip())
        provider_status[name] = {
            "key_env_var": key_var,
            "key_present": key_present,
            "model_env_var": model_var,
            "model_configured": model_val if model_val else None,
            "base_url_env_var": base_url_var,
            "base_url_present": base_url_present,
            "role": info["role"],
        }

    files_present = {}
    for fname in ["BRAIN.md", "PROVIDERS.md", "SAFETY.md", "ROLES.md"]:
        files_present[fname] = (brain_dir / fname).exists()

    any_key = any(p["key_present"] for p in provider_status.values())

    return {
        "brain_dir": str(brain_dir),
        "brain_dir_present": brain_present,
        "files": files_present,
        "providers": provider_status,
        "any_key_present": any_key,
    }


# ── Deterministic routing helpers ──────────────────────────────────────────────

_BUILD_KEYWORDS = frozenset([
    "add", "build", "create", "implement", "feature", "fix", "code",
    "develop", "write", "change", "update", "modify", "patch", "install",
    "command", "module", "function", "class", "endpoint", "api",
])

_REVIEW_KEYWORDS = frozenset([
    "review", "test", "verify", "check", "scope", "audit", "inspect",
    "validate", "assess", "qa", "quality",
])

_PLAN_KEYWORDS = frozenset([
    "plan", "architecture", "design", "route", "routing", "strategy",
    "approach", "structure", "organize", "layout", "diagram",
])

_RESEARCH_KEYWORDS = frozenset([
    "doc", "docs", "documentation", "research", "latest", "framework",
    "package", "library", "learn", "explore", "scout", "investigate",
    "compare", "survey",
])

_MCP_KEYWORDS = frozenset([
    "mcp", "multi-tool", "browser", "tool routing", "tool plan",
    "tool policy", "external tool",
])

_DESTRUCTIVE_KEYWORDS = frozenset([
    "commit", "release", "deploy", "database", "db", "migration",
    "secrets", "external account", "paid account", "destructive",
    "delete", "drop", "reset", "purge", "remove", "wipe", "push",
    "publish", "production", "prod",
])

_HIGH_RISK_KEYWORDS = frozenset([
    "all files", "everything", "overwrite", "bulk", "mass", "nuke",
    "force", "bypass", "skip", "ignore", "disable",
])


def _classify_task(goal: str) -> dict:
    gl = goal.lower()
    words = set(gl.replace("-", " ").replace("_", " ").split())

    is_destructive = bool(words & _DESTRUCTIVE_KEYWORDS)
    is_high_risk = bool(words & _HIGH_RISK_KEYWORDS)
    is_mcp = bool(words & _MCP_KEYWORDS)
    is_research = bool(words & _RESEARCH_KEYWORDS)
    is_plan = bool(words & _PLAN_KEYWORDS)
    is_review = bool(words & _REVIEW_KEYWORDS)
    is_build = bool(words & _BUILD_KEYWORDS)

    if is_destructive:
        task_type = "destructive"
        risk = "high"
        brain_role = "Mohit Supreme Judge"
        body_worker = "Mohit Supreme Judge"
        approval = "required — Mohit must approve before any action"
    elif is_high_risk:
        task_type = "high-risk"
        risk = "high"
        brain_role = "Critic/Judge Brain (NVIDIA)"
        body_worker = "Mohit Supreme Judge"
        approval = "required — Mohit must approve before any action"
    elif is_mcp:
        task_type = "mcp-heavy"
        risk = "medium"
        brain_role = "Planner Brain (OpenRouter)"
        body_worker = "OpenCode Plan → OpenCode Build (with approval)"
        approval = "required before OpenCode Build"
    elif is_research:
        task_type = "research"
        risk = "low"
        brain_role = "Memory/Summarizer Brain (Groq or OpenRouter)"
        body_worker = "OpenCode Scout"
        approval = "not required for research; required before any code change"
    elif is_plan:
        task_type = "planning"
        risk = "low"
        brain_role = "Planner Brain (OpenRouter)"
        body_worker = "OpenCode Plan"
        approval = "not required for planning output; required before implementation"
    elif is_review:
        task_type = "review"
        risk = "low"
        brain_role = "Critic/Judge Brain (NVIDIA)"
        body_worker = "Codex Reviewer"
        approval = "not required for review output"
    elif is_build:
        task_type = "build"
        risk = "low"
        brain_role = "Coding Brain (Poolside) or Reflex Router (Groq)"
        body_worker = "Claude Code Builder"
        approval = "not required for build; required before commit"
    else:
        task_type = "unclear"
        risk = "medium"
        brain_role = "Planner Brain (OpenRouter)"
        body_worker = "ask Mohit"
        approval = "required — task is unclear, ask Mohit before proceeding"

    return {
        "task_type": task_type,
        "risk": risk,
        "brain_role": brain_role,
        "body_worker": body_worker,
        "approval": approval,
    }


def _provider_availability() -> dict:
    avail = {}
    for name, info in _PROVIDERS.items():
        avail[name] = bool(os.environ.get(info["env_key"], "").strip())
    return avail


def op_brain_route(goal: str, brain: str = "off", repo_path: str | None = None) -> dict:
    """Route a goal to brain role and body worker. Read-only, no file creation."""
    brain = brain.lower().strip()
    valid_modes = {"off", "auto", "groq", "openrouter", "poolside", "nvidia"}
    if brain not in valid_modes:
        return {"error": f"invalid brain mode '{brain}'. Valid: {', '.join(sorted(valid_modes))}"}

    avail = _provider_availability()
    classification = _classify_task(goal)

    route_method = "deterministic"
    provider_note = ""
    selected_provider = None

    if brain == "off":
        route_method = "deterministic (brain=off)"
        provider_note = "Brain is off. All routing is local and deterministic. No API calls."
    elif brain == "auto":
        any_key = any(avail.values())
        if not any_key:
            route_method = "deterministic (auto fallback — no API keys present)"
            provider_note = (
                "brain=auto selected but no API key found in environment. "
                "Using deterministic local route. Set GROQ_API_KEY, OPENROUTER_API_KEY, "
                "POOLSIDE_API_KEY, or NVIDIA_API_KEY to enable provider routing."
            )
        else:
            first_avail = next((p for p in ["groq", "openrouter", "poolside", "nvidia"] if avail[p]), None)
            selected_provider = first_avail
            route_method = f"deterministic (auto selected {first_avail} — API call skipped in V0)"
            provider_note = (
                f"brain=auto found key for '{first_avail}'. "
                f"Provider call is not implemented in V0. Deterministic route used."
            )
    else:
        if not avail.get(brain):
            route_method = f"deterministic (key missing for {brain})"
            provider_note = (
                f"Warning: --brain {brain} selected but {_PROVIDERS[brain]['env_key']} not set. "
                "Falling back to deterministic local route."
            )
        else:
            selected_provider = brain
            route_method = f"deterministic (provider {brain} available — API call skipped in V0)"
            provider_note = (
                f"brain={brain} and key is present. "
                "Provider call is not implemented in V0. Deterministic route used."
            )

    next_step = _build_next_step(classification, brain)

    return {
        "goal": goal,
        "brain_mode": brain,
        "route_method": route_method,
        "provider_note": provider_note,
        "selected_provider": selected_provider,
        "provider_availability": avail,
        "task_type": classification["task_type"],
        "risk": classification["risk"],
        "brain_role": classification["brain_role"],
        "body_worker": classification["body_worker"],
        "approval_requirement": classification["approval"],
        "next_step": next_step,
    }


def _build_next_step(classification: dict, brain: str) -> str:
    worker = classification["body_worker"]
    task_type = classification["task_type"]
    if classification["risk"] == "high":
        return "Stop and ask Mohit before proceeding. This task requires Supreme Judge approval."
    if task_type == "build":
        return (
            "Run `darwin operate-existing <repo> --goal \"<goal>\" --brain off` to generate "
            "a Claude Code build prompt. Paste CLAUDE_BUILD_PROMPT.md into Claude Code."
        )
    if task_type == "review":
        return (
            "Run `darwin operate-existing <repo> --goal \"<goal>\" --brain off` to generate "
            "a Codex review prompt. Paste CODEX_REVIEW_PROMPT.md into Codex."
        )
    if task_type == "planning":
        return (
            "Run `darwin operate-existing <repo> --goal \"<goal>\" --brain off` to generate "
            "an OpenCode plan prompt. Paste OPENCODE_PLAN_PROMPT.md into OpenCode."
        )
    if task_type == "research":
        return (
            "Run `darwin operate-existing <repo> --goal \"<goal>\" --brain off` to generate "
            "an OpenCode Scout prompt."
        )
    return (
        f"Recommended worker: {worker}. "
        "Run `darwin operate-existing <repo> --goal \"<goal>\" --brain off` to generate prompts."
    )
