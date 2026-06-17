"""Existing Repo Intake operations — inspect-repo."""

import json
import re
from pathlib import Path

from darwin.common import now

_INSPECT_IGNORED = frozenset([
    ".venv", "__pycache__", ".git", "node_modules", "dist", "build",
    ".tox", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".eggs",
])


def _ignored_dir(name: str) -> bool:
    return name in _INSPECT_IGNORED or name.endswith(".egg-info")


def _detect_project_signals(repo: Path) -> dict:
    s: dict = {}
    s["has_pyproject"] = (repo / "pyproject.toml").exists()
    s["has_requirements"] = (repo / "requirements.txt").exists()
    s["has_setup_py"] = (repo / "setup.py").exists()
    s["is_python"] = s["has_pyproject"] or s["has_requirements"] or s["has_setup_py"]
    s["has_package_json"] = (repo / "package.json").exists()
    s["has_vite_config"] = bool(list(repo.glob("vite.config.*")))
    s["has_src_dir"] = (repo / "src").exists()
    s["is_node"] = s["has_package_json"]
    s["has_git"] = (repo / ".git").exists()
    s["has_readme"] = any(
        (repo / r).exists() for r in ["README.md", "README.rst", "README.txt", "README"]
    )
    s["has_scripts_dir"] = (repo / "scripts").exists()
    s["has_tests_dir"] = (repo / "tests").exists() or (repo / "test").exists()
    s["python_project_name"] = None
    s["python_scripts"] = {}
    if s["has_pyproject"]:
        try:
            pyproject_text = (repo / "pyproject.toml").read_text()
            m = re.search(r'^name\s*=\s*["\']([^"\']+)["\']', pyproject_text, re.MULTILINE)
            if m:
                s["python_project_name"] = m.group(1)
            scripts_section = re.search(
                r"(?ms)^\[project\.scripts\]\s*(.*?)(?=^\[|\Z)", pyproject_text,
            )
            if scripts_section:
                s["python_scripts"] = {
                    script_match.group(1): script_match.group(2)
                    for script_match in re.finditer(
                        r'^\s*([A-Za-z0-9_.-]+)\s*=\s*["\']([^"\']+)["\']',
                        scripts_section.group(1),
                        re.MULTILINE,
                    )
                }
        except Exception:
            pass
    s["package_scripts"] = {}
    s["node_project_name"] = None
    if s["has_package_json"]:
        try:
            pkg = json.loads((repo / "package.json").read_text())
            s["package_scripts"] = pkg.get("scripts", {})
            s["node_project_name"] = pkg.get("name")
        except Exception:
            pass
    return s


def _build_repo_tree(repo: Path) -> str:
    try:
        items = sorted(
            (i for i in repo.iterdir() if not _ignored_dir(i.name)),
            key=lambda p: (p.is_file(), p.name.lower()),
        )
    except PermissionError:
        return f"{repo.name}/\n  (permission denied)"
    lines = [f"{repo.name}/"]
    for i, item in enumerate(items):
        connector = "└── " if i == len(items) - 1 else "├── "
        suffix = "/" if item.is_dir() else ""
        lines.append(f"  {connector}{item.name}{suffix}")
    return "\n".join(lines)


def _detect_commands(repo: Path, s: dict) -> dict:
    cmds: dict = {"install": [], "test": [], "run": [], "notes": []}
    if s["is_python"]:
        if s["has_pyproject"]:
            cmds["install"].append("pip install -e .")
        elif s["has_requirements"]:
            cmds["install"].append("pip install -r requirements.txt")
        if s["has_tests_dir"]:
            cmds["test"].append("python -m pytest")
        else:
            cmds["notes"].append("No tests/ directory found — test command unknown.")
        if s["python_scripts"]:
            for script_name in sorted(s["python_scripts"]):
                cmds["run"].append(f"{script_name} --help")
        else:
            cmds["notes"].append("Entry point unknown — check pyproject.toml [project.scripts].")
    if s["is_node"]:
        if (repo / "yarn.lock").exists():
            cmds["install"].append("yarn install")
        else:
            cmds["install"].append("npm install")
        pkg = s.get("package_scripts", {})
        if "test" in pkg:
            cmds["test"].append("npm test")
        if "dev" in pkg:
            cmds["run"].append("npm run dev")
        elif "start" in pkg:
            cmds["run"].append("npm start")
        if pkg:
            cmds["notes"].append(f"Available package.json scripts: {', '.join(pkg.keys())}")
    if not cmds["install"] and not cmds["test"] and not cmds["run"]:
        cmds["notes"].append("No standard project files found — commands must be determined manually.")
    return cmds


def _detect_risks(repo: Path, s: dict) -> list:
    risks = []
    if not s["has_readme"]:
        risks.append("Missing README — project purpose and usage may be unclear.")
    if not s["has_tests_dir"]:
        risks.append("No tests/ directory found — changes are unverified.")
    if s["is_python"] and not s["has_pyproject"] and not s["has_requirements"]:
        risks.append("No pyproject.toml or requirements.txt — environment is hard to reproduce.")
    if s["is_node"] and not (repo / "package-lock.json").exists() and not (repo / "yarn.lock").exists():
        risks.append("No lockfile (package-lock.json / yarn.lock) — dependency versions are unpinned.")
    if not s["has_git"]:
        risks.append("No .git directory — project is not under version control.")
    if not s["is_python"] and not s["is_node"]:
        risks.append("No recognised project type — cannot determine standard commands.")
    env_present = (repo / ".env").exists()
    env_example = (repo / ".env.example").exists() or (repo / ".env.sample").exists()
    if env_present and not env_example:
        risks.append(".env file present but no .env.example — env vars may be undocumented.")
    elif not env_present and not env_example:
        risks.append("No .env or .env.example — required environment variables are unknown.")
    if not risks:
        risks.append("No obvious risks detected by deterministic scan.")
    return risks


def _detect_unknowns(repo: Path, s: dict) -> list:
    unknowns = []
    has_ci = (repo / ".github").exists() or (repo / ".gitlab-ci.yml").exists() or (repo / "Makefile").exists()
    if not has_ci:
        unknowns.append("CI/CD pipeline is unknown — no .github/, .gitlab-ci.yml, or Makefile found.")
    if s["is_python"] and not s["python_project_name"]:
        unknowns.append("Python project name could not be parsed from pyproject.toml.")
    if s["is_node"] and not s["node_project_name"]:
        unknowns.append("Node.js project name could not be parsed from package.json.")
    if not (repo / "Dockerfile").exists() and not (repo / "docker-compose.yml").exists():
        unknowns.append("Deployment method is unclear — no Dockerfile or docker-compose.yml.")
    if not unknowns:
        unknowns.append("No additional unknowns detected by deterministic scan.")
    return unknowns


def _make_project_brief(repo: Path, goal: str, s: dict, timestamp: str) -> str:
    type_lines = []
    if s["is_python"]:
        details = [f for f, k in [("pyproject.toml", "has_pyproject"), ("requirements.txt", "has_requirements"), ("setup.py", "has_setup_py")] if s[k]]
        type_lines.append(f"- Python ({', '.join(details)})")
    if s["is_node"]:
        details = ["package.json"]
        if s["has_vite_config"]:
            details.append("vite.config")
        type_lines.append(f"- Node.js ({', '.join(details)})")
    if s["has_git"]:
        type_lines.append("- Git repository")
    if s["has_readme"]:
        type_lines.append("- README present")
    if s["has_scripts_dir"]:
        type_lines.append("- scripts/ directory")
    if s["has_tests_dir"]:
        type_lines.append("- tests/ directory")
    if not type_lines:
        type_lines.append("- Unknown (no standard project markers found)")
    project_name = s.get("python_project_name") or s.get("node_project_name") or repo.name
    parts = []
    if s["is_python"]:
        parts.append(f'Python project "{project_name}"')
    elif s["is_node"]:
        parts.append(f'Node.js project "{project_name}"')
    else:
        parts.append(f'Project "{repo.name}"')
    if s["has_git"]:
        parts.append("under git version control")
    if s["has_tests_dir"]:
        parts.append("with a test suite")
    if s["has_scripts_dir"]:
        parts.append("and a scripts/ directory")
    summary = ", ".join(parts) + "."
    return (
        "# Project Brief\n\n"
        f"**Repo path:** {repo}\n"
        f"**User goal:** {goal}\n"
        f"**Scanned at:** {timestamp}\n\n"
        "## Project Type\n\n"
        + "\n".join(type_lines)
        + f"\n\n## Project Name\n\n{project_name}\n\n"
        f"## Summary\n\n{summary}\n\n"
        f"## User Goal\n\n{goal}\n"
    )


def _make_repo_map(repo: Path, tree: str, s: dict) -> str:
    important = []
    for fname, desc in [
        ("pyproject.toml", "Python project config"),
        ("requirements.txt", "Python dependencies"),
        ("setup.py", "Python setup script"),
        ("package.json", "Node.js project config"),
        ("README.md", "Project documentation"),
        ("README.rst", "Project documentation"),
        (".env.example", "Environment variable template"),
        ("Dockerfile", "Container build file"),
        ("Makefile", "Build/task commands"),
    ]:
        if (repo / fname).exists():
            important.append(f"- `{fname}` — {desc}")
    lines = [
        "# Repo Map\n",
        "Top-level structure (noisy folders excluded):\n",
        f"```\n{tree}\n```\n",
    ]
    if important:
        lines.append("## Important Files\n")
        lines.extend(important)
        lines.append("")
    return "\n".join(lines)


def _make_commands_md(cmds: dict) -> str:
    parts = ["# Commands\n"]
    if cmds["install"]:
        parts += ["## Install\n", "```bash"] + cmds["install"] + ["```\n"]
    if cmds["test"]:
        parts += ["## Test\n", "```bash"] + cmds["test"] + ["```\n"]
    if cmds["run"]:
        parts += ["## Run\n", "```bash"] + cmds["run"] + ["```\n"]
    if cmds["notes"]:
        parts.append("## Notes\n")
        parts.extend(f"- {n}" for n in cmds["notes"])
        parts.append("")
    if not cmds["install"] and not cmds["test"] and not cmds["run"]:
        parts.append("No commands detected. Fill in manually.\n")
    parts.append("*Commands detected by static scan — verify before running.*")
    return "\n".join(parts) + "\n"


def _make_risk_list(risks: list) -> str:
    lines = ["# Risk List\n"] + [f"- [ ] {r}" for r in risks]
    lines += ["", "*Risks detected by deterministic scan — review before coding.*"]
    return "\n".join(lines) + "\n"


def _make_unknowns_md(unknowns: list) -> str:
    lines = [
        "# Unknown Questions\n",
        "## What Darwin Could Not Determine\n",
    ] + [f"- {u}" for u in unknowns] + [
        "",
        "## Questions to Answer Before Coding\n",
        "1. Are there environment variables required to run this project?",
        "2. Is there a CI/CD pipeline and what does it run?",
        "3. Are there external services or APIs this project depends on?",
        "4. What is the deployment target (local, cloud, container)?",
        "",
        "## Safe Assumptions\n",
        "- Tests should pass before merging any change.",
        "- Existing user files must not be deleted or overwritten.",
        "- New code should follow the existing project style.",
    ]
    return "\n".join(lines) + "\n"


def _make_master_plan_draft(goal: str, s: dict) -> str:
    gl = goal.lower()
    bullets = ["- Understand current state of the codebase"]
    if any(w in gl for w in ["test", "testing", "spec", "coverage"]):
        if s["is_python"] and not s["has_tests_dir"]:
            bullets.append("- Set up tests/ directory and configure pytest")
        bullets += [
            "- Identify which modules or commands lack test coverage",
            "- Add unit tests for each untested module",
            "- Add integration or smoke tests for key workflows",
            "- Run the test suite and confirm all tests pass",
        ]
    elif any(w in gl for w in ["refactor", "clean", "simplify"]):
        bullets += [
            "- Identify duplicated or overly complex code",
            "- Plan the refactor to avoid breaking existing behaviour",
            "- Apply the refactor in small reviewable chunks",
            "- Confirm existing tests still pass after each chunk",
        ]
    elif any(w in gl for w in ["doc", "documentation", "readme"]):
        bullets += [
            "- Audit existing documentation for gaps",
            "- Write or update README with accurate usage instructions",
            "- Add documentation to public functions or modules",
            "- Review and update any example outputs",
        ]
    elif any(w in gl for w in ["fix", "bug", "error", "issue", "broken"]):
        bullets += [
            "- Reproduce the issue with a minimal test case",
            "- Identify the root cause in the codebase",
            "- Implement the fix",
            "- Add a regression test to prevent recurrence",
        ]
    elif any(w in gl for w in ["add", "build", "create", "implement", "feature"]):
        bullets += [
            "- Define the exact scope of the new feature",
            "- Identify files that will need to change",
            "- Implement the feature in small chunks",
            "- Add tests for the new feature",
            "- Update documentation",
        ]
    else:
        bullets += [
            f"- Identify what changes are needed to achieve: {goal}",
            "- Implement changes in small reviewable chunks",
            "- Add or update tests for any modified code",
            "- Update documentation if needed",
        ]
    return (
        "# Master Plan Draft\n\n"
        f"**Goal:** {goal}\n\n"
        "*Generated by deterministic scan. Review and edit before running `darwin split-plan`.*\n\n"
        "## Tasks\n\n"
        + "\n".join(bullets) + "\n"
    )


def op_inspect_repo(repo: Path, goal: str) -> dict:
    if not repo.exists():
        return {"error": f"repo path not found: {repo}"}
    if not repo.is_dir():
        return {"error": f"repo path is a file, not a folder: {repo}"}
    signals = _detect_project_signals(repo)
    tree = _build_repo_tree(repo)
    cmds = _detect_commands(repo, signals)
    risks = _detect_risks(repo, signals)
    unknowns = _detect_unknowns(repo, signals)
    timestamp = now()
    darwin_dir = repo / ".darwin"
    darwin_dir.mkdir(exist_ok=True)
    files = {
        "PROJECT_BRIEF.md": _make_project_brief(repo, goal, signals, timestamp),
        "REPO_MAP.md": _make_repo_map(repo, tree, signals),
        "COMMANDS.md": _make_commands_md(cmds),
        "RISK_LIST.md": _make_risk_list(risks),
        "UNKNOWN_QUESTIONS.md": _make_unknowns_md(unknowns),
        "MASTER_PLAN_DRAFT.md": _make_master_plan_draft(goal, signals),
    }
    created = []
    existing = []
    for filename, content in files.items():
        path = darwin_dir / filename
        if path.exists():
            existing.append(filename)
        else:
            path.write_text(content)
            created.append(filename)
    return {
        "repo": str(repo),
        "darwin_dir": str(darwin_dir),
        "created": created,
        "existing": existing,
    }
