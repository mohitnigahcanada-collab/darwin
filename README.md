# darwin

Smallest CLI skeleton (Chunk 001).

## Install

The system Python may be externally managed, so install inside a virtual
environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e .
```

## Run

```bash
darwin --help
darwin init
```

`darwin init` sets up the workspace in the current directory. It is safe to run
more than once.

It creates these folders:

- `chunks/`
- `memory/`
- `templates/`
- `reports/`
