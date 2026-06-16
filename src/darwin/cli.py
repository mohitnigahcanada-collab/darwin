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
    """Extract tasks from a plan file and write ROADMAP.md."""
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
        label = f"{num} — {task}"
        typer.echo(f"  {label}")
        roadmap_lines.append(f"- [ ] {label}")

    Path("ROADMAP.md").write_text("\n".join(roadmap_lines) + "\n")
    typer.echo(f"\nwritten: ROADMAP.md ({len(tasks)} task(s))")


if __name__ == "__main__":
    app()
