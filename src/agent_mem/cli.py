import typer
from .config import CONFIG_FILE, get_config, save_config
from pathlib import Path
import json
import shutil
import sys
from typing import Dict, List

from .memory import get_fallback_memory_file

app = typer.Typer()


def _project_name_from_root(project_root: Path) -> str:
    return project_root.resolve().name


def _rules_body(project_name: str) -> str:
    return f"""You have persistent project memory via agent-mem.

Primary memory source:
- Local-first file: .agent-memory/memory.md
- Optional Obsidian target when configured: <vault>/Memory/Agent-Mem/

Start-of-session rule (mandatory):
- Before planning or coding, read the latest project memory.
- If .agent-memory/memory.md exists, treat it as the source of truth.
- If no memory exists yet, proceed normally and create memory after meaningful progress.

Context management rule:
- Do not depend on long chat history for old decisions.
- Prefer memory content (and recent summaries) over earlier conversation context.

When context grows long (~15-20 turns):
- Announce that you are summarizing the session for memory.
- Save a concise Markdown summary containing:
    - Goal and outcome
    - Key decisions and why
    - Files changed and purpose
    - Open tasks/blockers
    - Next prioritized steps

Summary quality rules:
- Keep summaries short, factual, and actionable.
- Never invent prior decisions; only record what happened.
- Do not store secrets, tokens, passwords, or private keys in memory files.

MCP compatibility (optional):
- If agent-mem MCP tools are available, use query_memory / summarize_to_obsidian / list_recent_sessions.
- If MCP tools are unavailable, read and update .agent-memory/memory.md directly using the same structure.

Project naming:
- Use the repository root folder name as project_name for memory operations.

Project name for this workspace: {project_name}
"""


def _cursor_rule_content(project_name: str) -> str:
    return f"""---
description: Enforce agent-mem persistent memory workflow
alwaysApply: true
---

Follow AGENT-MEM-RULES.md in the repository root.

Critical reminders:

- Read .agent-memory/memory.md before planning or coding.
- Summarize long sessions with key decisions, changed files, blockers, and next steps.
- If MCP tools are available, use query_memory and summarize_to_obsidian.
"""


def _claude_instructions_content(project_name: str) -> str:
    return f"""# Agent Memory Instructions

Use AGENT-MEM-RULES.md as the source of truth.

Project name: {project_name}

Mandatory behavior:

- Read memory before planning or coding.
- Summarize when context becomes long and persist outcomes.
- Prefer memory content over old chat history.
- Never hallucinate historical decisions.
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


def _ensure_local_memory_initialized(project_root: Path):
    fallback_file = get_fallback_memory_file(project_root)
    if fallback_file.exists():
        return
    fallback_file.parent.mkdir(parents=True, exist_ok=True)
    fallback_file.write_text("# Agent Memory\n\n", encoding="utf-8")


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
        _ensure_local_memory_initialized(Path.cwd().resolve())

    save_config(config)
    typer.echo(f"✅ Config saved to {CONFIG_FILE}")

    project_root = Path.cwd().resolve()
    typer.echo(f"Project root for setup: {project_root}")

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
    typer.echo("Next: add AGENT-MEM-RULES.md to your IDE custom instructions.")
    typer.echo('Optional MCP mode: pip install "agent-mem[mcp]" && agent-mem serve')


@app.command()
def setup():
    """Set up instruction files + MCP configs for the current project."""
    project_root = Path.cwd().resolve()

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
    project_root = Path.cwd().resolve()
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
    project_root = Path.cwd().resolve()
    selected_python = _resolve_python_for_mcp(project_root, python)
    block = _build_mcp_json_with_python(selected_python)

    typer.echo(json.dumps(block, indent=2))


@app.command()
def serve():
    """Start the optional MCP server (stdio transport)."""
    try:
        from .mcp_server import mcp
    except ImportError:
        typer.echo(
            '❌ MCP dependencies are not installed. Install with: pip install "agent-mem[mcp]"',
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
    project_root = Path.cwd().resolve()
    vault = config.get("obsidian_vault")

    if config.get("use_obsidian") and vault:
        memory_dir = Path(vault) / "Memory" / "Agent-Mem"
        count = len(list(memory_dir.glob("*.md"))) if memory_dir.exists() else 0
        typer.echo("Storage mode   : Obsidian")
        typer.echo(f"Obsidian vault : {vault}")
        typer.echo(f"Memory notes   : {count} sessions stored")
        return

    fallback_file = project_root / ".agent-memory" / "memory.md"
    typer.echo("Storage mode   : Local fallback")
    typer.echo(f"Memory file    : {fallback_file}")
    typer.echo(f"Memory exists  : {'yes' if fallback_file.exists() else 'no'}")


if __name__ == "__main__":
    app()