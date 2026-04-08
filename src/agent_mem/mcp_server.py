try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover - fallback for older installs
    from fastmcp import FastMCP

from pathlib import Path

from .memory import get_fallback_memory_file, is_obsidian_enabled, list_recent_session_files, recall_memory, write_session_summary

mcp = FastMCP("agent-mem")

@mcp.tool()
def query_memory(project_name: str, query: str) -> str:
    """MUST be called at the start of every new session.

    Use the project root folder name for project_name and a short goal-focused query.
    Works in both modes:
    - Obsidian mode: reads recent notes from <vault>/Memory/Agent-Mem
    - Fallback mode: reads local .agent-memory/memory.md
    """
    project_root = Path.cwd().resolve()
    return recall_memory(project_name, query, count=5, project_root=project_root)

@mcp.tool()
def summarize_to_obsidian(project_name: str, summary: str) -> str:
    """Call when context is getting long (about 15-20 turns).

    Provide a structured markdown summary with decisions, file changes, open tasks,
    blockers, and next steps. After saving, suggest starting a fresh chat.

    This tool writes to Obsidian when configured, otherwise to local .agent-memory/memory.md.
    """
    project_root = Path.cwd().resolve()
    filepath = write_session_summary(project_name, summary, project_root=project_root)
    target = "Obsidian" if is_obsidian_enabled() else "local memory file"

    return (
        f"✅ Session summarized and saved to {target}: {filepath}\n"
        "You can now start a fresh chat. Future chats will use query_memory first."
    )


@mcp.tool()
def list_recent_sessions(project_name: str, count: int = 3) -> str:
    """List recent memory notes for quick historical overviews.

    Useful when users ask about prior work before requesting deep details.
    In fallback mode, returns the local memory.md file when available.
    """
    project_root = Path.cwd().resolve()
    files = list_recent_session_files(project_name, count=count, project_root=project_root)
    if not files:
        return "No sessions yet"
    if is_obsidian_enabled():
        return "\n".join(file_path.name for file_path in files)

    fallback = get_fallback_memory_file(project_root)
    return str(fallback.relative_to(project_root)) if fallback.exists() else "No sessions yet"
