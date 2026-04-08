try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover - fallback for older installs
    from fastmcp import FastMCP

from pathlib import Path

from .memory import (
    get_fallback_memory_file,
    is_obsidian_enabled,
    list_recent_session_files,
    write_session_summary,
)

mcp = FastMCP("agent-mem")


def _score_line(line: str, query: str) -> int:
    line_lower = line.lower()
    query_lower = query.lower().strip()
    if not query_lower:
        return 0

    score = 0
    for word in query_lower.split():
        if word and word in line_lower:
            score += 2
    if query_lower in line_lower:
        score += 5
    return score


def _scored_excerpt(content: str, query: str, limit: int = 12) -> list[str]:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    scored = sorted(
        ((line, _score_line(line, query)) for line in lines),
        key=lambda item: item[1],
        reverse=True,
    )
    matches = [line for line, score in scored if score > 0][:limit]
    if matches:
        return matches
    return [content[:800].strip()] if content.strip() else []

@mcp.tool()
def query_memory(project_name: str, query: str) -> str:
    """MUST be called at the start of every new session.

    Use the project root folder name for project_name and a short goal-focused query.
    Works in both modes:
    - Obsidian mode: reads recent notes from <vault>/Memory/Agent-Mem
    - Fallback mode: reads local .agent-memory/memory.md
    """
    project_root = Path.cwd().resolve()
    files = list_recent_session_files(project_name, count=5, project_root=project_root)

    if not files:
        return "No memory yet for this project. Start by chatting, then save a session summary."

    mode = "Obsidian" if is_obsidian_enabled() else "Local memory.md"
    result = [f"## Latest Memory ({mode})"]
    for file_path in files:
        content = file_path.read_text(encoding="utf-8")
        matches = _scored_excerpt(content, query, limit=12)

        result.append(f"### {file_path.name}")
        if matches:
            result.extend(matches)
        result.append("")

    return "\n".join(result)[:6000]

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