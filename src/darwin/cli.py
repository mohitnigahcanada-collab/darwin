from pathlib import Path

import typer

app = typer.Typer(help="Darwin CLI.", no_args_is_help=True)

# Directories created by `darwin init`.
INIT_DIRS = ["chunks", "memory", "templates", "reports"]

@app.callback()
def main() -> None:
    """Darwin CLI."""


@app.command()
def init() -> None:
    """Create the Darwin working directories."""
    for name in INIT_DIRS:
        path = Path(name)
        path.mkdir(parents=True, exist_ok=True)
        typer.echo(f"ready: {path}/")


if __name__ == "__main__":
    app()
