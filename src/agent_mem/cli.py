from pathlib import Path
import json
import shutil
import sys
import time
from typing import Dict, List

import click
import typer

from .config import CONFIG_FILE, get_config, save_config
from .memory import (
    get_active_context_file,
    get_fallback_memory_file,
    get_memory_dir,
    initialize_storage,
    prepare_next_prompt,
    recall_memory,
    write_active_context,
    write_session_summary,
)

app = typer.Typer()


def _echo(message: str = "", err: bool = False):
    click.secho(message, fg="bright_yellow", err=err, color=True)


def _prompt(text: str, default: str = "") -> str:
    styled = click.style(text, fg="bright_yellow")
    return click.prompt(styled, default=default, show_default=False)


def _confirm(text: str, default: bool = False) -> bool:
    styled = click.style(text, fg="bright_yellow")
    return click.confirm(styled, default=default, show_default=True)


def _project_name_from_root(project_root: Path) -> str:
    return project_root.resolve().name


def _quickstart_lines(project_root: Path | None = None) -> list[str]:
    root = project_root or _project_root()
    return [
        "agent-mem quickstart",
        f"Project root: {root}",
        "",
        "Most useful commands:",
        "  agent-mem init",
        "  agent-mem checkpoint --stdin",
        '  agent-mem recall \"current goal\"',
        "  agent-mem prepare-next",
        "  agent-mem status",
        "",
        "Important:",
        "  - Do not run `agent-mem serve` manually.",
        "  - During `init`, choose the IDE you actually use.",
        "  - Only that IDE's prompt/MCP files will be created.",
    ]


@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """CLI-first persistent memory for coding sessions."""
    if ctx.invoked_subcommand is None:
        for line in _quickstart_lines():
            _echo(line)
        raise typer.Exit()


def _rules_body(project_name: str) -> str:
    return f"""# Agent-Mem Rules

You are operating inside a repository that uses `agent-mem` for persistent coding memory.

Project name: {project_name}

## Primary Goal

Preserve accurate project context across chats while keeping the live context window small.

You must prefer saved memory over stale chat history and you must keep memory current whenever meaningful decisions are made.

## Memory Priority Order

1. If Obsidian mode is configured, the primary memory store is the vault under `Memory/Agent-Mem/`.
2. Otherwise, the primary memory store is `.agent-memory/memory.md`.
3. Old chat history is lower priority than saved memory.
4. Never invent historical decisions that do not appear in memory or the codebase.

## Start-Of-Session Requirements

At the start of every new session:

1. Resolve the repository root.
2. Resolve `project_name` from the repository root folder name unless the user explicitly overrides it.
3. Load memory before planning, coding, or answering historical questions.
4. Treat saved memory as the authoritative summary of previous sessions.

If MCP tools are available:

- call `query_memory(project_name, current_goal)`

If MCP tools are unavailable:

- read the latest Obsidian note set or `.agent-memory/memory.md` directly
- summarize what you learned before continuing

## When To Summarize

You must summarize when any of these happen:

- context becomes long or repetitive
- a milestone or subtask completes
- architecture, API, or workflow decisions change
- multiple files were edited for one logical change
- the user is about to stop or switch topics

## Required Summary Quality

Every saved summary must be factual, concise, and implementation-oriented.

It must include these sections in this order:

- Goal
- Outcome
- Key decisions
- Files changed
- Open tasks or blockers
- Next prioritized steps

## Double-Check Rules Before Saving

Before writing memory:

- verify the summary matches the actual files changed
- verify decisions are explicit, not implied guesses
- verify open tasks are still open
- remove secrets, tokens, passwords, or raw credentials
- keep wording specific enough to be useful in a later session

## Obsidian Rules

When Obsidian mode is enabled:

- prefer saving through `agent-mem summarize` or `summarize_to_obsidian`
- preserve wiki-links and note structure
- do not manually break frontmatter or note headings
- keep references usable for Graph view and backlinks

## Fallback Rules

When only `.agent-memory/memory.md` exists:

- append structured summaries
- do not overwrite prior useful context
- correct prior context only when it is clearly outdated or wrong

## Tool Preference

Preferred workflow:

1. `query_memory`
2. do work
3. `summarize_to_obsidian` or `agent-mem summarize`
4. start fresh session if context is bloated

## Response Behavior

- prefer memory-backed answers for questions about prior work
- if memory is missing, say that clearly
- suggest summarization proactively when context grows
- never claim a past decision unless you saw it in memory or code
"""


def _cursor_rule_content(project_name: str) -> str:
    return f"""---
description: Enforce agent-mem persistent memory workflow for Cursor
alwaysApply: true
---

Use `AGENT-MEM-RULES.md` in the repository root as the canonical memory policy.

Cursor-specific operating rules:

- Project name for this workspace is `{project_name}` unless the user explicitly says otherwise.
- At the start of every new chat, load memory before planning.
- If the `agent-mem` MCP tools are visible, call `query_memory` immediately.
- If MCP tools are not visible, read the saved memory artifacts directly from the repo or Obsidian path.
- Before any non-trivial code edit, ground yourself in saved memory and current file state.
- When a task spans multiple files, architecture decisions, or more than a short exchange, plan to summarize before the session ends.

Cursor execution checklist:

1. Read or query memory.
2. State the active goal.
3. Do the work.
4. Re-check whether key decisions changed.
5. Save a structured summary if anything important happened.

Cursor summarization rules:

- Summarize on milestone completion.
- Summarize when context is starting to repeat.
- Summarize before ending a session with unresolved work.
- Summaries must include decisions, changed files, open tasks, and next steps.

Cursor reliability rules:

- Do not trust stale chat over saved memory.
- Do not hallucinate previous decisions.
- Do not write secrets into memory.
- If memory and code conflict, report the conflict and prefer verified code state.
"""


def _claude_instructions_content(project_name: str) -> str:
    return f"""# Agent Memory Instructions

Use `AGENT-MEM-RULES.md` as the canonical source of truth.

Project name: {project_name}

Mandatory behavior at session start:

- Resolve the repository root.
- Resolve the project name from the repository root and keep it consistent.
- Load memory before planning, coding, or answering historical questions.
- Prefer saved memory over old chat history.

If MCP tools are available:

- call `query_memory` first
- call `summarize_to_obsidian` when needed

If MCP tools are unavailable:

- read the latest memory artifact directly
- use `agent-mem summarize` conventions when preparing a summary

Mandatory summarization triggers:

- long or repetitive context
- completed milestone
- important design or implementation decision
- multiple-file change
- session handoff or stop point

Required summary contents:

- Goal
- Outcome
- Key decisions
- Files changed
- Open tasks or blockers
- Next prioritized steps

Safety rules:

- never hallucinate historical decisions
- never write secrets into memory
- if memory conflicts with the codebase, say so explicitly
- prefer verified state over guessed state
"""


def _simple_wrapper_content(path_hint: str) -> str:
    title = path_hint.capitalize()
    return f"""# Agent-Mem Instructions For {title}

Use `AGENT-MEM-RULES.md` in the repository root as the canonical memory policy.

Platform target: {path_hint}

Behavior requirements:

- Load memory at the start of each session.
- Prefer Obsidian-backed notes or `.agent-memory/memory.md` over long chat history.
- Summarize after important changes, milestones, or context growth.
- Keep summaries structured and implementation-oriented.
- Never fabricate historical context.
- Never store secrets in memory artifacts.

Required summary sections:

- Goal
- Outcome
- Key decisions
- Files changed
- Open tasks or blockers
- Next prioritized steps

If direct MCP tools are available, use them.
If they are not, read and write the memory artifacts directly while preserving structure.
"""


def _ide_setup_instructions(target: str) -> str:
    instructions = {
        "cursor": "Cursor setup: reload the workspace. agent-mem created `.cursor/rules/agent-mem.mdc` and `.cursor/mcp.json`. Start a fresh chat; Cursor should load both automatically.",
        "claude": "Claude / VS Code setup: reload the workspace. agent-mem created `.claude/instructions.md` and `.vscode/mcp.json`. If your Claude extension does not auto-read `.claude/instructions.md`, paste `AGENT-MEM-RULES.md` into your custom instructions once.",
        "antigravity": "Antigravity setup: reload the workspace. agent-mem created `.antigravity/rules.md`. If Antigravity supports MCP via VS Code settings in your setup, add the generated `.vscode/mcp.json` only if needed.",
        "opencode": "OpenCode setup: reload the workspace. agent-mem created `.opencode/instructions.md`. If OpenCode needs MCP separately, use `agent-mem print-mcp-json` and add it in that product's MCP settings.",
        "none": "No IDE files were created. You can still use `agent-mem checkpoint --stdin`, `agent-mem prepare-next`, and `agent-mem recall` directly from the terminal.",
    }
    return instructions[target]


def _write_file(path: Path, content: str) -> bool:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def _create_instruction_files(project_root: Path, target: str) -> Dict[str, List[str]]:
    project_name = _project_name_from_root(project_root)

    files_to_write = {project_root / "AGENT-MEM-RULES.md": _rules_body(project_name)}
    if target == "cursor":
        files_to_write[project_root / ".cursor" / "rules" / "agent-mem.mdc"] = _cursor_rule_content(project_name)
    elif target == "claude":
        files_to_write[project_root / ".claude" / "instructions.md"] = _claude_instructions_content(project_name)
    elif target == "antigravity":
        files_to_write[project_root / ".antigravity" / "rules.md"] = _simple_wrapper_content("antigravity")
    elif target == "opencode":
        files_to_write[project_root / ".opencode" / "instructions.md"] = _simple_wrapper_content("opencode")

    created: List[str] = []
    updated: List[str] = []
    for path, content in files_to_write.items():
        existed = path.exists()
        if _write_file(path, content):
            if existed:
                updated.append(str(path.relative_to(project_root)))
            else:
                created.append(str(path.relative_to(project_root)))

    return {"created": created, "updated": updated}


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


def _create_local_mcp_configs(project_root: Path, target: str) -> List[str]:
    if target == "cursor":
        return [_upsert_mcp_config(project_root / ".cursor" / "mcp.json")]
    if target == "claude":
        return [_upsert_mcp_config(project_root / ".vscode" / "mcp.json")]
    return []


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
            _echo(f"❌ Python path not found: {explicit_python}", err=True)
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


def _prompt_ide_target(default: str = "cursor") -> str:
    valid = {"cursor", "claude", "antigravity", "opencode", "none"}
    while True:
        value = _prompt(
            "Which IDE do you want to set up? [cursor/claude/antigravity/opencode/none]",
            default=default,
        ).strip().lower()
        if value in valid:
            return value
        _echo("❌ Choose one of: cursor, claude, antigravity, opencode, none", err=True)


def _read_summary_input(summary: str, summary_file: str, stdin: bool) -> str:
    if summary.strip():
        return summary.strip()
    if summary_file.strip():
        summary_path = Path(summary_file.strip()).expanduser().resolve()
        if not summary_path.exists():
            _echo(f"❌ Summary file not found: {summary_path}", err=True)
            raise typer.Exit(1)
        return summary_path.read_text(encoding="utf-8").strip()
    if stdin:
        data = sys.stdin.read().strip()
        if data:
            return data

    _echo("❌ Provide summary text with --summary, --summary-file, or --stdin.", err=True)
    raise typer.Exit(1)


def _watch_ignore(path: Path) -> bool:
    ignored_parts = {
        ".git",
        ".agent-memory",
        ".cursor",
        ".claude",
        ".antigravity",
        ".opencode",
        ".vscode",
        "dist",
        "build",
        "__pycache__",
        ".pytest_cache",
        ".mypy_cache",
    }
    return any(part in ignored_parts for part in path.parts)


def _snapshot_project_files(project_root: Path) -> Dict[str, float]:
    snapshot: Dict[str, float] = {}
    for path in project_root.rglob("*"):
        if not path.is_file():
            continue
        if _watch_ignore(path.relative_to(project_root)):
            continue
        snapshot[str(path.relative_to(project_root))] = path.stat().st_mtime
    return snapshot


def _diff_snapshots(previous: Dict[str, float], current: Dict[str, float]) -> List[str]:
    changed: set[str] = set()
    previous_keys = set(previous)
    current_keys = set(current)

    for key in previous_keys ^ current_keys:
        changed.add(key)

    for key in previous_keys & current_keys:
        if previous[key] != current[key]:
            changed.add(key)

    return sorted(changed)


def _auto_summary(changed_files: List[str], project_name: str) -> str:
    bullet_files = "\n".join(f"- {path}" for path in changed_files[:25]) or "- No files detected"
    extra_note = ""
    if len(changed_files) > 25:
        extra_note = f"\nAdditional changed files not shown: {len(changed_files) - 25}"

    return f"""## Goal

Automatic checkpoint created by `agent-mem watch`.

## Outcome

Saved an automated memory checkpoint after file activity settled.

## Key decisions

- Automatic watch-based checkpoint captured current work-in-progress state for {project_name}.

## Files changed

{bullet_files}{extra_note}

## Open tasks or blockers

- Review the changed files and replace this automated checkpoint with a richer manual summary if architectural decisions were made.

## Next prioritized steps

- Continue the current task.
- Run `agent-mem summarize` manually after the next meaningful milestone for a higher-quality summary.
"""


@app.command()
def init():
    """One-time setup - Obsidian is optional, local memory.md fallback is supported."""
    _echo("agent-mem setup (Obsidian path is optional)")
    vault = _prompt("Full path to your Obsidian vault (press Enter to skip and use local memory.md)", default="")

    config = {"use_obsidian": False, "obsidian_vault": None}
    if vault.strip():
        vault_path = Path(vault).expanduser().resolve()
        if vault_path.exists():
            config = {"use_obsidian": True, "obsidian_vault": str(vault_path)}
            _echo(f"✅ Using Obsidian vault: {vault_path}")
        else:
            _echo("⚠️ Path does not exist. Falling back to local memory.md", err=True)
    else:
        _echo("✅ Using simple local memory.md fallback in project folder")

    ide_target = _prompt_ide_target()

    save_config(config)
    _echo(f"✅ Config saved to {CONFIG_FILE}")

    project_root = _project_root()
    created_storage = initialize_storage(project_root)
    memory_dir = get_memory_dir(project_root)
    _echo(f"Project root for setup: {project_root}")
    _echo(f"Memory storage   : {memory_dir}")
    if created_storage:
        _echo("✅ Created storage files:")
        for path in created_storage:
            _echo(f"  - {path}")
    if config.get("use_obsidian"):
        _echo("Obsidian mode    : Connected")
        _echo("Notes written here will appear in Obsidian automatically because they are plain Markdown inside your vault.")
    else:
        _echo("Obsidian mode    : Disabled (local fallback active)")

    result = _create_instruction_files(project_root, ide_target)
    if result["created"]:
        _echo("✅ Created instruction files:")
        for relative_path in result["created"]:
            _echo(f"  - {relative_path}")
    if result["updated"]:
        _echo("✅ Updated instruction files:")
        for relative_path in result["updated"]:
            _echo(f"  - {relative_path}")
    _echo("Restart your IDE chat (or reload rules) to apply instruction changes.")

    written_paths = _create_local_mcp_configs(project_root, ide_target)
    if written_paths:
        _echo("✅ MCP config updated:")
        for config_path in written_paths:
            _echo(f"  - {config_path}")

    _echo("\nSetup complete!")
    _echo(_ide_setup_instructions(ide_target))
    _echo("Terminal-only test:")
    _echo("  1. agent-mem checkpoint --stdin")
    _echo("  2. agent-mem prepare-next")
    _echo('  3. agent-mem recall "current goal"')
    if written_paths:
        _echo("You do not need to run `agent-mem serve` manually. Your IDE will launch it from the generated MCP config.")


@app.command()
def setup():
    """Set up instruction files + MCP configs for the current project."""
    project_root = _project_root()
    ide_target = _prompt_ide_target()

    result = _create_instruction_files(project_root, ide_target)
    written_paths = _create_local_mcp_configs(project_root, ide_target)

    _echo(f"Project root: {project_root}")
    if result["created"]:
        _echo("✅ Created instruction files:")
        for relative_path in result["created"]:
            _echo(f"  - {relative_path}")
    if result["updated"]:
        _echo("✅ Updated instruction files:")
        for relative_path in result["updated"]:
            _echo(f"  - {relative_path}")

    if written_paths:
        _echo("✅ MCP config updated:")
        for config_path in written_paths:
            _echo(f"  - {config_path}")
    _echo(_ide_setup_instructions(ide_target))


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

    _echo("✅ VS Code MCP config written")
    _echo(f"Path: {written}")
    _echo("Server command uses:")
    _echo(f"  {selected_python} -m agent_mem.cli serve")


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

    _echo(json.dumps(block, indent=2))


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
    active_path = get_active_context_file(project_root)
    mode = "Obsidian" if get_config().get("use_obsidian") else "local fallback"

    _echo(f"✅ Summary saved to {mode}: {saved_path}")
    _echo(f"✅ Active context refreshed: {active_path}")


@app.command()
def checkpoint(
    summary: str = typer.Option("", "--summary", help="Inline checkpoint summary text."),
    summary_file: str = typer.Option("", "--summary-file", help="Path to a markdown/text file containing the checkpoint summary."),
    stdin: bool = typer.Option(False, "--stdin", help="Read checkpoint summary text from stdin."),
    project_name: str = typer.Option("", "--project-name", help="Override the inferred project name."),
    save_session: bool = typer.Option(
        False,
        "--save-session/--no-save-session",
        help="Also persist the checkpoint into long-term session memory.",
    ),
):
    """Write the compact live handoff file used for the next fresh chat."""
    project_root = _project_root()
    effective_project_name = project_name.strip() or _project_name_from_root(project_root)
    summary_text = _read_summary_input(summary, summary_file, stdin)

    active_path = write_active_context(effective_project_name, summary_text, project_root=project_root)
    _echo(f"✅ Active context saved: {active_path}")

    if save_session:
        session_path = write_session_summary(effective_project_name, summary_text, project_root=project_root)
        _echo(f"✅ Session memory also saved: {session_path}")


@app.command("prepare-next")
def prepare_next(
    project_name: str = typer.Option("", "--project-name", help="Override the inferred project name."),
):
    """Print the compact starter block for a fresh follow-up chat."""
    project_root = _project_root()
    effective_project_name = project_name.strip() or _project_name_from_root(project_root)
    _echo(prepare_next_prompt(effective_project_name, project_root=project_root))


@app.command()
def recall(
    query: str = typer.Argument(..., help="Short query describing the context you want recalled."),
    project_name: str = typer.Option("", "--project-name", help="Override the inferred project name."),
    count: int = typer.Option(5, "--count", min=1, max=20, help="Number of recent memory sources to inspect."),
):
    """Recall the most relevant saved memory for a task or question."""
    project_root = _project_root()
    effective_project_name = project_name.strip() or _project_name_from_root(project_root)
    _echo(recall_memory(effective_project_name, query, count=count, project_root=project_root))


@app.command()
def watch(
    interval: float = typer.Option(2.0, "--interval", min=0.5, help="Polling interval in seconds."),
    quiet_seconds: int = typer.Option(20, "--quiet-seconds", min=1, help="Required quiet time before a checkpoint is saved."),
    min_changes: int = typer.Option(3, "--min-changes", min=1, help="Minimum number of changed files before saving an automatic checkpoint."),
    once: bool = typer.Option(False, "--once", help="Exit after the first automatic checkpoint is saved."),
    project_name: str = typer.Option("", "--project-name", help="Override the inferred project name."),
):
    """Watch the repo for file activity and save automatic checkpoint summaries."""
    project_root = _project_root()
    effective_project_name = project_name.strip() or _project_name_from_root(project_root)

    initialize_storage(project_root)
    baseline = _snapshot_project_files(project_root)
    pending_changes: set[str] = set()
    last_change_at: float | None = None

    _echo(f"Watching {project_root}")
    _echo(f"Project name     : {effective_project_name}")
    _echo(f"Polling interval : {interval}s")
    _echo(f"Quiet threshold  : {quiet_seconds}s")
    _echo(f"Min changes      : {min_changes}")
    _echo("Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(interval)
            current = _snapshot_project_files(project_root)
            changed = _diff_snapshots(baseline, current)
            baseline = current

            if changed:
                pending_changes.update(changed)
                last_change_at = time.time()
                _echo(f"Detected {len(changed)} changed files. Pending total: {len(pending_changes)}")
                continue

            if not pending_changes or last_change_at is None:
                continue

            if (time.time() - last_change_at) < quiet_seconds:
                continue

            if len(pending_changes) < min_changes:
                continue

            summary = _auto_summary(sorted(pending_changes), effective_project_name)
            saved_path = write_session_summary(effective_project_name, summary, project_root=project_root)
            active_path = get_active_context_file(project_root)
            _echo(f"✅ Automatic checkpoint saved: {saved_path}")
            _echo(f"✅ Active context refreshed: {active_path}")
            pending_changes.clear()
            last_change_at = None

            if once:
                return
    except KeyboardInterrupt:
        _echo("\nStopped watch mode.")


@app.command()
def serve(
    force_stdio: bool = typer.Option(
        False,
        "--force-stdio",
        help="Run even in an interactive terminal. Intended only for debugging MCP startup.",
    ),
):
    """Start the optional MCP server (stdio transport)."""
    if not force_stdio and (sys.stdin.isatty() or sys.stdout.isatty()):
        _echo("`agent-mem serve` is an MCP stdio endpoint for IDEs, not a normal terminal command.", err=True)
        _echo("Do not run it manually from a shell prompt.", err=True)
        _echo("", err=True)
        _echo("Use one of these instead:", err=True)
        _echo("  - agent-mem status", err=True)
        _echo("  - agent-mem checkpoint --stdin", err=True)
        _echo("  - agent-mem prepare-next", err=True)
        _echo("", err=True)
        _echo("If you are configuring VS Code or Cursor, keep the generated MCP config and let the IDE launch `serve` automatically.", err=True)
        _echo("If you really need to debug MCP startup in a terminal, run: agent-mem serve --force-stdio", err=True)
        raise typer.Exit(1)

    try:
        from .mcp_server import mcp
    except ImportError:
        _echo(
            '❌ MCP dependencies are not installed. Install with: pip install "easy-agent-mem[mcp]"',
            err=True,
        )
        raise typer.Exit(1)

    config = get_config()
    if config.get("use_obsidian") and not config.get("obsidian_vault"):
        _echo("❌ Obsidian mode selected but no vault path found. Re-run agent-mem init.", err=True)
        raise typer.Exit(1)

    _echo("agent-mem MCP server started (stdio transport)")
    _echo("Tip: run 'agent-mem print-mcp-json' if you need a config block.")
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
        active_path = get_active_context_file(project_root)
        _echo("Storage mode   : Obsidian")
        _echo(f"Obsidian vault : {vault}")
        _echo(f"Memory folder  : {memory_dir}")
        _echo(f"Index note     : {index_path}")
        _echo(f"Active context : {active_path}")
        _echo(f"Session notes  : {count} stored")
        return

    fallback_file = project_root / ".agent-memory" / "memory.md"
    active_path = get_active_context_file(project_root)
    _echo("Storage mode   : Local fallback")
    _echo(f"Memory file    : {fallback_file}")
    _echo(f"Active context : {active_path}")
    _echo(f"Memory exists  : {'yes' if fallback_file.exists() else 'no'}")


if __name__ == "__main__":
    app()
