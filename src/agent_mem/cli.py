from pathlib import Path
import json
import shutil
import sys
from typing import Dict, List

import typer

from .config import CONFIG_FILE, get_config, save_config
from .memory import get_fallback_memory_file, get_memory_dir, initialize_storage, recall_memory, write_session_summary

app = typer.Typer()


def _project_name_from_root(project_root: Path) -> str:
    return project_root.resolve().name


def _rules_body(project_name: str) -> str:
    return f"""# Agent-Mem Rules

You have persistent project memory via agent-mem.

## Objective

- Keep durable project context across chats.
- Prefer stored memory over long chat history.

## Memory Source Of Truth

- Primary (default): .agent-memory/memory.md
- Optional: [vault_path]/Memory/Agent-Mem/ when Obsidian mode is configured

## Mandatory Start-Of-Session Workflow

1. Resolve project root and project name (root folder name).
2. Load latest memory before planning or coding.
3. If memory exists, treat it as authoritative project context.
4. If memory does not exist, continue normally and create or update it after meaningful progress.

## Mandatory Summarization Triggers

- Context pressure (roughly 15-20 turns)
- Major milestone completed
- Before ending session when important decisions were made

## Required Summary Structure

Use concise Markdown with these sections in order:

- Goal
- Outcome
- Key decisions (with rationale)
- Files changed (path + reason)
- Open tasks or blockers
- Next prioritized steps

## Memory Write Rules

- Append new information; do not delete prior history unless it is clearly obsolete and corrected.
- Be factual and specific; never invent decisions or changes.
- Never write secrets (tokens, API keys, passwords, private credentials).

## MCP Compatibility (Optional)

- If MCP tools are available: use query_memory, summarize_to_obsidian, list_recent_sessions.
- If MCP tools are unavailable: read and update .agent-memory/memory.md directly with the same structure.

## Project Name Rule

- Always use the repository root folder name as project_name.

Project name for this workspace: {project_name}
"""


def _cursor_rule_content(project_name: str) -> str:
    return f"""---
description: Enforce agent-mem persistent memory workflow
alwaysApply: true
---

Follow AGENT-MEM-RULES.md in the repository root.

Critical reminders:

- Resolve project_name as: {project_name}
- Read .agent-memory/memory.md before planning or coding.
- On long sessions or milestones, write a structured summary with decisions and changed files.
- Use MCP tools when available; otherwise update memory.md directly.
"""


def _claude_instructions_content(project_name: str) -> str:
    return f"""# Agent Memory Instructions

Use AGENT-MEM-RULES.md as the source of truth.

Project name: {project_name}

Mandatory behavior:

- Resolve project name from repository root and keep it consistent.
- Read memory before planning or coding.
- Summarize at milestones/context pressure and persist outcomes.
- Prefer memory content over old chat history.
- Never hallucinate historical decisions.
- Never store secrets in memory files.
"""


def _simple_wrapper_content(path_hint: str) -> str:
    return (
        "Use AGENT-MEM-RULES.md in the repository root as the authoritative instruction set for memory workflow.\n"
        f"Wrapper target: {path_hint}\n"
    )


def _write_file(path: Path, content: str) -> bool:
    if path.exists():
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def _create_instruction_files(project_root: Path) -> Dict[str, List[str]]:
    project_name = _project_name_from_root(project_root)

    files_to_write = {
        project_root / "AGENT-MEM-RULES.md": _rules_body(project_name),
        project_root / ".cursor" / "rules" / "agent-mem.mdc": _cursor_rule_content(project_name),
        project_root / ".claude" / "instructions.md": _claude_instructions_content(project_name),
        project_root / "CLAUDE.md": _claude_instructions_content(project_name),
        project_root / ".antigravity" / "rules.md": _simple_wrapper_content("antigravity"),
        project_root / ".opencode" / "instructions.md": _simple_wrapper_content("opencode"),
    }

    created: List[str] = []
    skipped: List[str] = []
    for path, content in files_to_write.items():
        if _write_file(path, content):
            created.append(str(path.relative_to(project_root)))
        else:
            skipped.append(str(path.relative_to(project_root)))

    return {"created": created, "skipped": skipped}


def _upsert_mcp_config(config_path: Path) -> str:
    config_path.parent.mkdir(parents=True, exist_ok=True)

    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            if not isinstance(config, dict):
                config = {}
        except json.JSONDecodeError:
            config = {}
    else:
        config = {}

    servers = config.get("mcpServers")
    if not isinstance(servers, dict):
        servers = {}

    resolved_command = shutil.which("agent-mem") or "agent-mem"
    servers["agent-mem"] = {
        "command": resolved_command,
        "args": ["serve"],
    }
    config["mcpServers"] = servers

    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return str(config_path)


def _create_local_mcp_configs(project_root: Path) -> List[str]:
    return [
        _upsert_mcp_config(project_root / ".vscode" / "mcp.json"),
        _upsert_mcp_config(project_root / ".cursor" / "mcp.json"),
    ]


def _upsert_vscode_mcp_with_python(config_path: Path, python_executable: str) -> str:
    config_path.parent.mkdir(parents=True, exist_ok=True)

    if config_path.exists():
        try:
            config = json.loads(config_path.read_text(encoding="utf-8"))
            if not isinstance(config, dict):
                config = {}
        except json.JSONDecodeError:
            config = {}
    else:
        config = {}

    servers = config.get("mcpServers")
    if not isinstance(servers, dict):
        servers = {}

    servers["agent-mem"] = {
        "command": python_executable,
        "args": ["-m", "agent_mem.cli", "serve"],
    }
    config["mcpServers"] = servers

    config_path.write_text(json.dumps(config, indent=2) + "\n", encoding="utf-8")
    return str(config_path)


def _detect_preferred_python(project_root: Path) -> str:
    # Prefer repo-local virtual env for predictable MCP startup.
    local_venv_python = project_root / ".venv" / "bin" / "python"
    if local_venv_python.exists():
        return str(local_venv_python)

    virtual_env = Path(sys.prefix)
    if (virtual_env / "bin" / "python").exists():
        return str(virtual_env / "bin" / "python")

    return sys.executable


def _resolve_python_for_mcp(project_root: Path, python_option: str) -> str:
    if python_option.strip():
        explicit_python = Path(python_option.strip()).expanduser().resolve()
        if not explicit_python.exists():
            typer.echo(f"❌ Python path not found: {explicit_python}", err=True)
            raise typer.Exit(1)
        return str(explicit_python)

    return _detect_preferred_python(project_root)


def _build_mcp_json_with_python(python_executable: str) -> dict:
    return {
        "mcpServers": {
            "agent-mem": {
                "command": python_executable,
                "args": ["-m", "agent_mem.cli", "serve"],
            }
        }
    }


def _project_root() -> Path:
    return Path.cwd().resolve()


def _read_summary_input(summary: str, summary_file: str, stdin: bool) -> str:
    if summary.strip():
        return summary.strip()
    if summary_file.strip():
        summary_path = Path(summary_file.strip()).expanduser().resolve()
        if not summary_path.exists():
            typer.echo(f"❌ Summary file not found: {summary_path}", err=True)
            raise typer.Exit(1)
        return summary_path.read_text(encoding="utf-8").strip()
    if stdin:
        data = sys.stdin.read().strip()
        if data:
            return data

    typer.echo("❌ Provide summary text with --summary, --summary-file, or --stdin.", err=True)
    raise typer.Exit(1)


@app.command()
def init():
    """One-time setup - Obsidian is optional, local memory.md fallback is supported."""
    typer.echo("agent-mem setup (Obsidian path is optional)")
    vault = typer.prompt(
        "Full path to your Obsidian vault (press Enter to skip and use local memory.md)",
        default="",
    )

    config = {"use_obsidian": False, "obsidian_vault": None}
    if vault.strip():
        vault_path = Path(vault).expanduser().resolve()
        if vault_path.exists():
            config = {"use_obsidian": True, "obsidian_vault": str(vault_path)}
            typer.echo(f"✅ Using Obsidian vault: {vault_path}")
        else:
            typer.echo("⚠️ Path does not exist. Falling back to local memory.md", err=True)
    else:
        typer.echo("✅ Using simple local memory.md fallback in project folder")

    save_config(config)
    typer.echo(f"✅ Config saved to {CONFIG_FILE}")

    project_root = _project_root()
    created_storage = initialize_storage(project_root)
    memory_dir = get_memory_dir(project_root)
    typer.echo(f"Project root for setup: {project_root}")
    typer.echo(f"Memory storage   : {memory_dir}")
    if created_storage:
        typer.echo("✅ Created storage files:")
        for path in created_storage:
            typer.echo(f"  - {path}")
    if config.get("use_obsidian"):
        typer.echo("Obsidian mode    : Connected")
        typer.echo("Notes written here will appear in Obsidian automatically because they are plain Markdown inside your vault.")
    else:
        typer.echo("Obsidian mode    : Disabled (local fallback active)")

    if typer.confirm(
        "Create automatic instruction files for Cursor/Claude/Antigravity/OpenCode? (recommended)",
        default=True,
    ):
        result = _create_instruction_files(project_root)
        if result["created"]:
            typer.echo("✅ Created instruction files:")
            for relative_path in result["created"]:
                typer.echo(f"  - {relative_path}")
        if result["skipped"]:
            typer.echo("ℹ️ Existing files kept unchanged:")
            for relative_path in result["skipped"]:
                typer.echo(f"  - {relative_path}")
        typer.echo("Restart your IDE chat (or reload rules) to apply instruction changes.")

    if typer.confirm(
        "Create/update local MCP config files (.vscode/mcp.json and .cursor/mcp.json)? (optional)",
        default=False,
    ):
        written_paths = _create_local_mcp_configs(project_root)
        typer.echo("✅ MCP config updated:")
        for config_path in written_paths:
            typer.echo(f"  - {config_path}")

    typer.echo("\nSetup complete!")
    typer.echo("Recommended next steps:")
    typer.echo("  1. Add AGENT-MEM-RULES.md to your IDE custom instructions")
    typer.echo('  2. Save a session with: agent-mem summarize --summary "..."')
    typer.echo('  3. Recall context with: agent-mem recall "current goal"')
    typer.echo('Optional MCP mode: pip install "easy-agent-mem[mcp]" && agent-mem serve')


@app.command()
def setup():
    """Set up instruction files + MCP configs for the current project."""
    project_root = _project_root()

    result = _create_instruction_files(project_root)
    written_paths = _create_local_mcp_configs(project_root)

    typer.echo(f"Project root: {project_root}")
    if result["created"]:
        typer.echo("✅ Created instruction files:")
        for relative_path in result["created"]:
            typer.echo(f"  - {relative_path}")
    if result["skipped"]:
        typer.echo("ℹ️ Existing files kept unchanged:")
        for relative_path in result["skipped"]:
            typer.echo(f"  - {relative_path}")

    typer.echo("✅ MCP config updated:")
    for config_path in written_paths:
        typer.echo(f"  - {config_path}")


@app.command("setup-vscode")
def setup_vscode(
    python: str = typer.Option(
        "",
        "--python",
        help="Explicit Python executable path for MCP command",
    ),
):
    """Write .vscode/mcp.json using the currently active Python interpreter."""
    project_root = _project_root()
    config_path = project_root / ".vscode" / "mcp.json"
    selected_python = _resolve_python_for_mcp(project_root, python)

    written = _upsert_vscode_mcp_with_python(config_path, selected_python)

    typer.echo("✅ VS Code MCP config written")
    typer.echo(f"Path: {written}")
    typer.echo("Server command uses:")
    typer.echo(f"  {selected_python} -m agent_mem.cli serve")


@app.command("print-mcp-json")
def print_mcp_json(
    python: str = typer.Option(
        "",
        "--python",
        help="Explicit Python executable path for MCP command",
    ),
):
    """Print a ready-to-paste MCP JSON block without writing any files."""
    project_root = _project_root()
    selected_python = _resolve_python_for_mcp(project_root, python)
    block = _build_mcp_json_with_python(selected_python)

    typer.echo(json.dumps(block, indent=2))


@app.command()
def summarize(
    summary: str = typer.Option("", "--summary", help="Inline summary text to save."),
    summary_file: str = typer.Option("", "--summary-file", help="Path to a markdown/text file containing the summary."),
    stdin: bool = typer.Option(False, "--stdin", help="Read summary text from stdin."),
    project_name: str = typer.Option("", "--project-name", help="Override the inferred project name."),
):
    """Save a structured session summary to Obsidian or local fallback storage."""
    project_root = _project_root()
    effective_project_name = project_name.strip() or _project_name_from_root(project_root)
    summary_text = _read_summary_input(summary, summary_file, stdin)

    saved_path = write_session_summary(effective_project_name, summary_text, project_root=project_root)
    mode = "Obsidian" if get_config().get("use_obsidian") else "local fallback"

    typer.echo(f"✅ Summary saved to {mode}: {saved_path}")


@app.command()
def recall(
    query: str = typer.Argument(..., help="Short query describing the context you want recalled."),
    project_name: str = typer.Option("", "--project-name", help="Override the inferred project name."),
    count: int = typer.Option(5, "--count", min=1, max=20, help="Number of recent memory sources to inspect."),
):
    """Recall the most relevant saved memory for a task or question."""
    project_root = _project_root()
    effective_project_name = project_name.strip() or _project_name_from_root(project_root)
    typer.echo(recall_memory(effective_project_name, query, count=count, project_root=project_root))


@app.command()
def serve():
    """Start the optional MCP server (stdio transport)."""
    try:
        from .mcp_server import mcp
    except ImportError:
        typer.echo(
            '❌ MCP dependencies are not installed. Install with: pip install "easy-agent-mem[mcp]"',
            err=True,
        )
        raise typer.Exit(1)

    config = get_config()
    if config.get("use_obsidian") and not config.get("obsidian_vault"):
        typer.echo("❌ Obsidian mode selected but no vault path found. Re-run agent-mem init.", err=True)
        raise typer.Exit(1)

    typer.echo("agent-mem MCP server started (stdio transport)")
    typer.echo("Tip: run 'agent-mem print-mcp-json' if you need a config block.")
    mcp.run()


@app.command()
def status():
    """Show the configured vault and stored session count."""
    config = get_config()
    project_root = _project_root()
    vault = config.get("obsidian_vault")

    if config.get("use_obsidian") and vault:
        memory_dir = Path(vault) / "Memory" / "Agent-Mem"
        count = len(list(memory_dir.glob("*-session.md"))) if memory_dir.exists() else 0
        index_path = memory_dir / "Index.md"
        typer.echo("Storage mode   : Obsidian")
        typer.echo(f"Obsidian vault : {vault}")
        typer.echo(f"Memory folder  : {memory_dir}")
        typer.echo(f"Index note     : {index_path}")
        typer.echo(f"Session notes  : {count} stored")
        return

    fallback_file = project_root / ".agent-memory" / "memory.md"
    typer.echo("Storage mode   : Local fallback")
    typer.echo(f"Memory file    : {fallback_file}")
    typer.echo(f"Memory exists  : {'yes' if fallback_file.exists() else 'no'}")


if __name__ == "__main__":
    app()
