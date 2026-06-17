"""Tool Registry operations — tool-init, tool-list, tool-suggest."""

import re
from pathlib import Path

from darwin.common import RISK_ORDER, parse_card_field

_TOOL_README = (
    "# Darwin Tool Registry V0\n\n"
    "This registry is a local catalog of tools, MCPs, and workers that Darwin may\n"
    "suggest for tasks. It does not install, configure, or run any tool.\n\n"
    "## Rules\n\n"
    "- Tools are only \"awake\" when explicitly selected by a user or future planner.\n"
    "- Maximum 3 MCPs active per task.\n"
    "- Maximum 1 high-risk MCP per task.\n"
    "- External/account MCPs require explicit approval before first use.\n"
    "- Secrets and full repo contents must NOT be sent to external MCPs by default.\n\n"
    "## Commands\n\n"
    "```bash\n"
    "darwin tool-init                             # create this registry (idempotent)\n"
    "darwin tool-list                             # list tools with type/risk/approval\n"
    'darwin tool-suggest --goal "<goal>"          # deterministic keyword suggestions\n'
    "```\n\n"
    "## How to use\n\n"
    "1. Run `darwin tool-suggest --goal \"<your goal>\"` to get suggestions.\n"
    "2. Review the risk and approval notes.\n"
    "3. Select tools manually before starting work.\n"
    "4. Edit any tool card freely — `darwin tool-init` never overwrites existing cards.\n"
)

_TOOL_CARD_DARWIN_CHUNK_MCP = (
    "# Tool: darwin_chunk_mcp\n\n"
    "## Type\nMCP / Internal\n\n"
    "## Status\navailable\n\n"
    "## Best for\n"
    "- Chunk OS operations (init, prepare-chunk, record-result, review-chunk, update-memory)\n"
    "- Driving the Darwin chunk loop from an MCP-capable agent\n\n"
    "## Wake when\n"
    "- Running Chunk OS operations via Claude Code or another MCP agent\n\n"
    "## Do not wake when\n"
    "- Already running from the CLI directly\n\n"
    "## Risk level\nlow\n\n"
    "## Secrets risk\nnone\n\n"
    "## Approval required\nno\n\n"
    "## Expected output\n"
    "- Chunk file creation, ROADMAP updates, memory writes\n\n"
    "## Notes\n"
    "- Already ships as `darwin-mcp`\n"
    "- Exposes 9 Chunk OS tools\n"
    "- No network, no LLM, no shell execution\n"
)

_TOOL_CARD_CONTEXT7 = (
    "# Tool: context7_docs_mcp\n\n"
    "## Type\nMCP\n\n"
    "## Status\nexternal\n\n"
    "## Best for\n"
    "- Fetching up-to-date package and framework documentation\n"
    "- Resolving API version questions before coding\n\n"
    "## Wake when\n"
    "- Goal mentions a framework, library, or API where version accuracy matters\n\n"
    "## Do not wake when\n"
    "- Working on internal logic with no external dependencies\n"
    "- Documentation is already loaded in context\n\n"
    "## Risk level\nmedium\n\n"
    "## Secrets risk\nlow\n\n"
    "## Approval required\nyes\n\n"
    "## Expected output\n"
    "- Relevant documentation excerpts for the requested library/version\n\n"
    "## Notes\n"
    "- First use requires approval\n"
    "- Do not send secrets or sensitive config to this MCP\n"
)

_TOOL_CARD_PROXIMA = (
    "# Tool: proxima_research_mcp\n\n"
    "## Type\nMCP\n\n"
    "## Status\nrisky\n\n"
    "## Best for\n"
    "- Multi-model or web research gateway\n"
    "- Comparing approaches, frameworks, or external repos at scale\n\n"
    "## Wake when\n"
    "- Goal explicitly requires broad web research or cross-model comparison\n"
    "- Proxima Doctor and Privacy Guard are confirmed active\n\n"
    "## Do not wake when\n"
    "- Proxima Doctor / Privacy Guard do not exist yet\n"
    "- Goal is local code work only\n"
    "- Secrets or sensitive repo context may be in scope\n\n"
    "## Risk level\nhigh\n\n"
    "## Secrets risk\nhigh\n\n"
    "## Approval required\nyes\n\n"
    "## Expected output\n"
    "- Research summaries, comparative analysis, external references\n\n"
    "## Notes\n"
    "- Must not send secrets, credentials, or full repo to this MCP\n"
    "- Use only after Proxima Doctor and Privacy Guard exist\n"
    "- Status: planned / not yet integrated\n"
)

_TOOL_CARD_GITHUB = (
    "# Tool: github_mcp\n\n"
    "## Type\nMCP\n\n"
    "## Status\nexternal\n\n"
    "## Best for\n"
    "- Reading issues, PRs, and remote repo metadata\n"
    "- Studying external repos without cloning locally\n\n"
    "## Wake when\n"
    "- Goal mentions GitHub, PRs, issues, branch metadata, or external repo study\n\n"
    "## Do not wake when\n"
    "- Working on purely local chunks\n"
    "- No GitHub access token is configured\n\n"
    "## Risk level\nmedium\n\n"
    "## Secrets risk\nmedium\n\n"
    "## Approval required\nyes\n\n"
    "## Expected output\n"
    "- Issue/PR details, repo metadata, file trees of external repos\n\n"
    "## Notes\n"
    "- Requires GitHub token in environment\n"
    "- Do not use for pushing commits or merging PRs without explicit approval\n"
)

_TOOL_CARD_PLAYWRIGHT = (
    "# Tool: playwright_mcp\n\n"
    "## Type\nMCP\n\n"
    "## Status\nexternal\n\n"
    "## Best for\n"
    "- UI and browser flow testing\n"
    "- End-to-end form, click, and navigation tests\n\n"
    "## Wake when\n"
    "- Goal mentions UI, browser, e2e testing, form flows, or page interactions\n\n"
    "## Do not wake when\n"
    "- No browser/UI component is in scope\n"
    "- Working on backend or CLI-only tasks\n\n"
    "## Risk level\nmedium\n\n"
    "## Secrets risk\nlow\n\n"
    "## Approval required\nyes\n\n"
    "## Expected output\n"
    "- Test results, screenshots, assertion output\n\n"
    "## Notes\n"
    "- Requires Playwright browser binaries installed\n"
)

_TOOL_CARD_DEVTOOLS = (
    "# Tool: chrome_devtools_mcp\n\n"
    "## Type\nMCP\n\n"
    "## Status\nexternal\n\n"
    "## Best for\n"
    "- Live frontend console, DOM, CSS, and performance debugging\n"
    "- Inspecting runtime state of a running browser page\n\n"
    "## Wake when\n"
    "- Goal mentions console errors, DOM inspection, CSS layout, or devtools\n\n"
    "## Do not wake when\n"
    "- No browser page is running\n"
    "- Working on backend or CLI-only tasks\n\n"
    "## Risk level\nmedium\n\n"
    "## Secrets risk\nlow\n\n"
    "## Approval required\nyes\n\n"
    "## Expected output\n"
    "- Console logs, DOM snapshots, performance traces\n\n"
    "## Notes\n"
    "- Requires a running Chrome/Chromium instance with DevTools Protocol enabled\n"
)

_TOOL_CARD_SEMGREP = (
    "# Tool: semgrep_mcp\n\n"
    "## Type\nMCP\n\n"
    "## Status\nexternal\n\n"
    "## Best for\n"
    "- Security static analysis\n"
    "- Detecting unsafe patterns, injection risks, insecure defaults\n\n"
    "## Wake when\n"
    "- Goal mentions security, vulnerability scanning, or static analysis\n\n"
    "## Do not wake when\n"
    "- Security is not in scope for the current chunk\n\n"
    "## Risk level\nmedium\n\n"
    "## Secrets risk\nlow\n\n"
    "## Approval required\nyes\n\n"
    "## Expected output\n"
    "- Rule match list with file, line, and severity\n\n"
    "## Notes\n"
    "- Requires Semgrep installed locally\n"
    "- Run on local files only; do not send to external API without approval\n"
)

_TOOL_CARD_OSV = (
    "# Tool: osv_mcp\n\n"
    "## Type\nMCP\n\n"
    "## Status\nexternal\n\n"
    "## Best for\n"
    "- Dependency vulnerability lookup using the OSV database\n"
    "- Checking whether a package version has known CVEs\n\n"
    "## Wake when\n"
    "- Goal mentions dependency security, vulnerability, or supply chain risk\n\n"
    "## Do not wake when\n"
    "- No dependency changes are in scope\n\n"
    "## Risk level\nmedium\n\n"
    "## Secrets risk\nnone\n\n"
    "## Approval required\nyes\n\n"
    "## Expected output\n"
    "- List of known vulnerabilities for queried packages\n\n"
    "## Notes\n"
    "- Queries the public OSV.dev API\n"
    "- No secrets needed; results are public data\n"
)

_TOOL_CARD_SUPABASE = (
    "# Tool: supabase_mcp\n\n"
    "## Type\nMCP\n\n"
    "## Status\nexternal\n\n"
    "## Best for\n"
    "- Supabase project schema inspection and migration planning\n"
    "- Database query execution on a Supabase instance\n\n"
    "## Wake when\n"
    "- Goal explicitly involves a Supabase project\n\n"
    "## Do not wake when\n"
    "- Working on local-only code with no Supabase dependency\n"
    "- No Supabase service key is confirmed safe to use\n\n"
    "## Risk level\nhigh\n\n"
    "## Secrets risk\nhigh\n\n"
    "## Approval required\nyes\n\n"
    "## Expected output\n"
    "- Schema listings, migration previews, query results\n\n"
    "## Notes\n"
    "- Requires Supabase service key — handle with extreme care\n"
    "- Never log or expose service keys in output\n"
)

_TOOL_CARD_POSTGRES = (
    "# Tool: postgres_mcp\n\n"
    "## Type\nMCP\n\n"
    "## Status\nexternal\n\n"
    "## Best for\n"
    "- Local or controlled PostgreSQL database inspection and querying\n\n"
    "## Wake when\n"
    "- Goal explicitly involves a PostgreSQL database with a controlled connection\n\n"
    "## Do not wake when\n"
    "- Working on code with no database dependency\n"
    "- No safe, non-production connection string is confirmed\n\n"
    "## Risk level\nhigh\n\n"
    "## Secrets risk\nhigh\n\n"
    "## Approval required\nyes\n\n"
    "## Expected output\n"
    "- Schema listings, query results, explain plans\n\n"
    "## Notes\n"
    "- Use on local/dev databases only\n"
    "- Never run destructive queries without explicit confirmation\n"
)

_TOOL_CARD_DOCKER = (
    "# Tool: docker_mcp\n\n"
    "## Type\nMCP\n\n"
    "## Status\nexternal\n\n"
    "## Best for\n"
    "- Container and compose debugging\n"
    "- Inspecting logs, container state, and service health\n\n"
    "## Wake when\n"
    "- Goal mentions Docker, containers, compose, or container logs\n\n"
    "## Do not wake when\n"
    "- No containers are running or in scope\n\n"
    "## Risk level\nhigh\n\n"
    "## Secrets risk\nmedium\n\n"
    "## Approval required\nyes\n\n"
    "## Expected output\n"
    "- Container logs, status output, compose service state\n\n"
    "## Notes\n"
    "- Can affect running containers — approval required for any state-changing action\n"
)

_TOOL_CARD_OPENCODE = (
    "# Tool: opencode_worker\n\n"
    "## Type\nWorker\n\n"
    "## Status\nplanned\n\n"
    "## Best for\n"
    "- MCP-heavy coding tasks requiring multiple tools in parallel\n"
    "- Multi-agent execution and tool routing\n"
    "- Non-interactive headless coding runs\n\n"
    "## Wake when\n"
    "- Goal requires 3+ MCPs active simultaneously\n"
    "- Goal is well-specified and bounded\n\n"
    "## Do not wake when\n"
    "- Goal is narrow and can be done with claude_code_worker alone\n"
    "- Goal is unclear or open-ended\n"
    "- Any high-risk MCP would be active without approval\n\n"
    "## Risk level\nhigh\n\n"
    "## Secrets risk\nmedium\n\n"
    "## Approval required\nyes\n\n"
    "## Expected output\n"
    "- Code changes, file writes, test results (scoped to task)\n\n"
    "## Notes\n"
    "- Use with strict permissions: no git push, no secrets, no full repo to external tools\n"
    "- Not yet integrated; status: planned\n"
    "- Requires explicit permission profile before first run\n"
)

_TOOL_CARD_CLAUDE_CODE = (
    "# Tool: claude_code_worker\n\n"
    "## Type\nWorker\n\n"
    "## Status\navailable\n\n"
    "## Best for\n"
    "- Focused coding chunks with narrow, well-defined scope\n"
    "- Single-file or small multi-file changes\n"
    "- Running smoke tests and verifying output\n\n"
    "## Wake when\n"
    "- Goal is a specific, bounded coding or debugging task\n\n"
    "## Do not wake when\n"
    "- Goal requires broad research before coding\n"
    "- Goal is ambiguous\n\n"
    "## Risk level\nmedium\n\n"
    "## Secrets risk\nlow\n\n"
    "## Approval required\nyes\n\n"
    "## Expected output\n"
    "- Code changes, test output, file edits\n\n"
    "## Notes\n"
    "- Give minimal MCPs only (1-2 max)\n"
    "- Prefer read-only MCPs unless writes are explicitly required\n"
)

_TOOL_CARD_CODEX_REVIEWER = (
    "# Tool: codex_reviewer\n\n"
    "## Type\nReviewer\n\n"
    "## Status\navailable\n\n"
    "## Best for\n"
    "- Strict code review and scope guard\n"
    "- Verifying tests pass and acceptance criteria are met\n"
    "- Requesting the smallest possible fix\n\n"
    "## Wake when\n"
    "- A chunk result needs review before being accepted\n\n"
    "## Do not wake when\n"
    "- Work is still in progress (review after completion only)\n\n"
    "## Risk level\nlow\n\n"
    "## Secrets risk\nnone\n\n"
    "## Approval required\nno\n\n"
    "## Expected output\n"
    "- PASS or FAIL verdict with specific feedback\n\n"
    "## Notes\n"
    "- Approval not required for review-only mode\n"
    "- Approval yes if also patching files\n"
    "- Outputs CODEX_REVIEW_PROMPT.md format\n"
)

_TOOL_CARDS: dict[str, str] = {
    "README.md": _TOOL_README,
    "darwin_chunk_mcp.md": _TOOL_CARD_DARWIN_CHUNK_MCP,
    "context7_docs_mcp.md": _TOOL_CARD_CONTEXT7,
    "proxima_research_mcp.md": _TOOL_CARD_PROXIMA,
    "github_mcp.md": _TOOL_CARD_GITHUB,
    "playwright_mcp.md": _TOOL_CARD_PLAYWRIGHT,
    "chrome_devtools_mcp.md": _TOOL_CARD_DEVTOOLS,
    "semgrep_mcp.md": _TOOL_CARD_SEMGREP,
    "osv_mcp.md": _TOOL_CARD_OSV,
    "supabase_mcp.md": _TOOL_CARD_SUPABASE,
    "postgres_mcp.md": _TOOL_CARD_POSTGRES,
    "docker_mcp.md": _TOOL_CARD_DOCKER,
    "opencode_worker.md": _TOOL_CARD_OPENCODE,
    "claude_code_worker.md": _TOOL_CARD_CLAUDE_CODE,
    "codex_reviewer.md": _TOOL_CARD_CODEX_REVIEWER,
}

_TOOL_KEYWORD_MAP: dict[str, dict] = {
    "darwin_chunk_mcp": {
        "keywords": {"chunk", "roadmap", "prepare", "result", "memory"},
        "risk": "low",
        "approval": "no",
    },
    "context7_docs_mcp": {
        "keywords": {
            "docs", "documentation", "api", "framework", "package",
            "library", "version", "react", "vite", "stripe",
        },
        "risk": "medium",
        "approval": "yes",
    },
    "proxima_research_mcp": {
        "keywords": {
            "research", "papers", "competitors", "market",
            "compare", "latest", "repos",
        },
        "risk": "high",
        "approval": "yes",
    },
    "github_mcp": {
        "keywords": {
            "github", "pr", "issue", "branch", "repository",
            "repos", "compare", "competitors",
        },
        "risk": "medium",
        "approval": "yes",
    },
    "playwright_mcp": {
        "keywords": {"ui", "browser", "click", "form", "page", "frontend", "e2e"},
        "risk": "medium",
        "approval": "yes",
    },
    "chrome_devtools_mcp": {
        "keywords": {"console", "dom", "css", "layout", "performance", "devtools"},
        "risk": "medium",
        "approval": "yes",
    },
    "semgrep_mcp": {
        "keywords": {"security", "vulnerability", "static", "unsafe"},
        "risk": "medium",
        "approval": "yes",
    },
    "osv_mcp": {
        "keywords": {"vulnerability", "cve", "dependency", "supply"},
        "risk": "medium",
        "approval": "yes",
    },
    "supabase_mcp": {
        "keywords": {"supabase", "database", "sql", "schema", "migration"},
        "risk": "high",
        "approval": "yes",
    },
    "postgres_mcp": {
        "keywords": {"postgres", "postgresql", "database", "sql", "schema"},
        "risk": "high",
        "approval": "yes",
    },
    "docker_mcp": {
        "keywords": {"docker", "container", "compose"},
        "risk": "high",
        "approval": "yes",
    },
    "opencode_worker": {
        "keywords": {"opencode", "mcp heavy", "multi tool", "tool routing", "routing"},
        "risk": "high",
        "approval": "yes",
    },
    "claude_code_worker": {
        "keywords": {"build", "implement", "code", "fix"},
        "risk": "medium",
        "approval": "yes",
    },
    "codex_reviewer": {
        "keywords": {"review", "test", "verify", "judge", "scope"},
        "risk": "low",
        "approval": "no",
    },
}


def op_tool_init(base: Path) -> dict:
    tools_dir = base / ".darwin" / "tools"
    tools_dir.mkdir(parents=True, exist_ok=True)
    created = []
    existing = []
    for filename, content in _TOOL_CARDS.items():
        path = tools_dir / filename
        if path.exists():
            existing.append(filename)
        else:
            path.write_text(content)
            created.append(filename)
    return {"tools_dir": str(tools_dir), "created": created, "existing": existing}


def op_tool_list(base: Path) -> dict:
    tools_dir = base / ".darwin" / "tools"
    if not tools_dir.exists():
        return {
            "initialized": False,
            "message": "Tool registry not initialized. Run: darwin tool-init",
        }
    tools = []
    for path in sorted(tools_dir.glob("*.md")):
        if path.name == "README.md":
            continue
        try:
            text = path.read_text()
        except Exception:
            text = ""
        tools.append({
            "filename": path.name,
            "name": path.stem,
            "type": parse_card_field(text, "Type"),
            "risk": parse_card_field(text, "Risk level"),
            "approval": parse_card_field(text, "Approval required"),
        })
    return {
        "initialized": True,
        "tools_dir": str(tools_dir),
        "tools": tools,
        "count": len(tools),
    }


def op_tool_suggest(base: Path, goal: str) -> dict:
    goal_lower = goal.lower()
    normalized_goal = re.sub(r"[^a-z0-9]+", " ", goal_lower)
    goal_words = set(re.findall(r"[a-z0-9]+", goal_lower))
    matches: list[dict] = []
    for tool_name, info in _TOOL_KEYWORD_MAP.items():
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
            "tool": tool_name,
            "matched_keywords": hit_words,
            "risk": info["risk"],
            "approval": info["approval"],
        })
    matches.sort(key=lambda m: (RISK_ORDER.get(m["risk"], 9), m["tool"]))
    warning = None
    if len(matches) > 3:
        warning = "Too many tools matched; planner should narrow this before execution."
    matches = matches[:5]
    return {
        "goal": goal,
        "matches": matches,
        "total_matched": len(matches),
        "warning": warning,
        "disclaimer": "This is a suggestion only. It does not enable or run tools.",
    }
