import re
from pathlib import Path

import typer

app = typer.Typer(help="Darwin CLI.", no_args_is_help=True)

INIT_DIRS = ["chunks", "memory", "templates", "reports"]

INIT_FILES = {
    "MASTER_PLAN.md": (
        "# Master Plan\n\n"
        "Example plan:\n\n"
        "- Build the smallest CLI skeleton.\n"
        "- Set up the workspace files.\n"
        "- Split the plan into chunks.\n"
    ),
    "ROADMAP.md": (
        "# Roadmap\n\n"
        "Roadmap is not generated yet.\n"
    ),
    "memory/mistakes.md": "# Mistakes\n",
    "memory/winners.md": "# Winners\n",
    "memory/decisions.md": "# Decisions\n",
}


def _slug(text: str, max_len: int = 40) -> str:
    text = text.lower()
    text = re.sub(r"[^a-z0-9\s-]", "", text)
    text = re.sub(r"\s+", "-", text.strip())
    return text[:max_len].rstrip("-")


@app.callback()
def main() -> None:
    """Darwin CLI."""


@app.command()
def init() -> None:
    """Create the Darwin working directories and starter files."""
    for name in INIT_DIRS:
        path = Path(name)
        path.mkdir(parents=True, exist_ok=True)
        typer.echo(f"ready:   {path}/")

    for name, content in INIT_FILES.items():
        path = Path(name)
        if path.exists():
            typer.echo(f"exists:  {path}")
            continue
        path.write_text(content)
        typer.echo(f"created: {path}")


@app.command("split-plan")
def split_plan(
    plan_file: Path = typer.Argument(..., help="Path to the master plan markdown file."),
) -> None:
    """Extract tasks, create chunk folders with TASK.md, and write ROADMAP.md."""
    if not plan_file.exists():
        typer.echo(f"error: file not found: {plan_file}", err=True)
        raise typer.Exit(1)

    lines = plan_file.read_text().splitlines()
    tasks = []
    for line in lines:
        if line.startswith("- ") or line.startswith("* "):
            task = line[2:].strip()
            if task:
                tasks.append(task)

    if not tasks:
        typer.echo("No bullet tasks found in the plan. Nothing was changed.")
        return

    typer.echo(f"Found {len(tasks)} task(s):\n")

    roadmap_lines = ["# Roadmap", "", "## Pending Tasks", ""]

    for i, task in enumerate(tasks, 1):
        num = f"{i:03d}"
        folder_name = f"{num}-{_slug(task)}"
        folder_path = Path("chunks") / folder_name
        task_file = folder_path / "TASK.md"

        folder_path.mkdir(parents=True, exist_ok=True)

        if task_file.exists():
            file_status = "exists"
        else:
            task_file.write_text(
                f"# Chunk {num}\n\n"
                f"**Task:** {task}\n"
                f"**Status:** pending\n"
            )
            file_status = "created"

        typer.echo(f"  {num} — {task}")
        typer.echo(f"       {folder_path}/ [{file_status} TASK.md]")

        roadmap_lines.append(f"- [ ] {num} — {task} — `{folder_path}/`")

    Path("ROADMAP.md").write_text("\n".join(roadmap_lines) + "\n")
    typer.echo(f"\nwritten: ROADMAP.md")
    typer.echo(f"done:    chunks/ ({len(tasks)} folder(s))")


if __name__ == "__main__":
    app()
