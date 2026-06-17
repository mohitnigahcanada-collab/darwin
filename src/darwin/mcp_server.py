"""
Darwin Chunk OS — MCP server.

Start with:  darwin-mcp
             python -m darwin.mcp_server
"""

import sys
from pathlib import Path

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    FastMCP = None  # type: ignore[assignment,misc]

from darwin.core import (
    op_get_file,
    op_list_chunks,
    op_next_chunk,
    op_prepare_chunk,
    op_read_chunk_files,
    op_record_result,
    op_review_chunk,
    op_update_memory,
)

if FastMCP is not None:
    mcp = FastMCP("darwin-chunk-os")

    @mcp.tool()
    def list_chunks(project_path: str = ".") -> list[dict]:
        """List all chunk folders in the project."""
        return op_list_chunks(Path(project_path).resolve())

    @mcp.tool()
    def next_chunk(project_path: str = ".") -> dict:
        """Return the first unchecked chunk from ROADMAP.md."""
        return op_next_chunk(Path(project_path).resolve())

    @mcp.tool()
    def prepare_chunk(project_path: str, chunk_path: str) -> dict:
        """Create STEP.md, CONTEXT.md, CLAUDE_PROMPT.md, and other working files."""
        return op_prepare_chunk(Path(project_path).resolve(), chunk_path)

    @mcp.tool()
    def read_chunk_files(project_path: str, chunk_path: str) -> dict:
        """Return the contents of all files in a chunk folder."""
        return op_read_chunk_files(Path(project_path).resolve(), chunk_path)

    @mcp.tool()
    def get_builder_prompt(project_path: str, chunk_path: str) -> dict:
        """Return the contents of CLAUDE_PROMPT.md for a chunk."""
        return op_get_file(Path(project_path).resolve(), chunk_path, "CLAUDE_PROMPT.md")

    @mcp.tool()
    def get_review_prompt(project_path: str, chunk_path: str) -> dict:
        """Return the contents of CODEX_REVIEW_PROMPT.md for a chunk."""
        return op_get_file(Path(project_path).resolve(), chunk_path, "CODEX_REVIEW_PROMPT.md")

    @mcp.tool()
    def record_result(
        project_path: str,
        chunk_path: str,
        status: str,
        notes: str = "",
    ) -> dict:
        """Record a pass/fail/blocked result for a chunk."""
        return op_record_result(Path(project_path).resolve(), chunk_path, status, notes)

    @mcp.tool()
    def review_chunk(project_path: str, chunk_path: str) -> dict:
        """Run local file checks on a chunk and write REVIEW.md."""
        return op_review_chunk(Path(project_path).resolve(), chunk_path)

    @mcp.tool()
    def update_memory(project_path: str, chunk_path: str) -> dict:
        """Update memory files and mark ROADMAP.md done if chunk passed."""
        return op_update_memory(Path(project_path).resolve(), chunk_path)


def main() -> None:
    if FastMCP is None:
        print(
            "Error: MCP SDK not installed.\n"
            "Install it with:  pip install 'mcp[cli]'\n"
            "Or:               pip install darwin[mcp]",
            file=sys.stderr,
        )
        sys.exit(1)
    mcp.run()


if __name__ == "__main__":
    main()
