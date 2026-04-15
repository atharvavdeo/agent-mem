from pathlib import Path
import json
import shutil
import sys
from typing import Dict, List

import click
import typer

from .config import CONFIG_FILE, get_config, get_groq_api_key, save_config
from .graph import build_graph
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
graph_app = typer.Typer(help="Build Obsidian-friendly project knowledge notes.")
app.add_typer(graph_app, name="graph")


def _echo(message: str = "", err: bool = False):
    click.secho(message, fg="bright_yellow", err=err, color=True)


def _prompt(text: str, default: str = "") -> str:
    styled = click.style(text, fg="bright_yellow")
    return click.prompt(styled, default=default, show_default=False)


def _confirm(text: str, default: bool = False) -> bool:
    styled = click.style(text, fg="bright_yellow")
    return click.confirm(styled, default=default, show_default=True)


def _prompt_secret(text: str) -> str:
    styled = click.style(text, fg="bright_yellow")
    return click.prompt(styled, hide_input=True, show_default=False).strip()


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
        "  agent-mem configure-groq",
        "  agent-mem test-watch --dry-run",
        "  agent-mem watch --dry-run --once",
        "  agent-mem checkpoint --stdin",
        '  agent-mem recall \"current goal\"',
        "  agent-mem prepare-next",
        "  agent-mem graph build",
        "  agent-mem status",
        "",
        "Important:",
        "  - Do not run `agent-mem serve` manually.",
        "  - During `init`, choose the IDE you actually use.",
        "  - Only that IDE's prompt/MCP files will be created.",
        "  - `watch` generates a one-paste handoff prompt for your IDE chat.",
        "  - `graph build` generates Obsidian-friendly project knowledge notes.",
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

This repository uses `agent-mem` for persistent coding memory.

Project name: {project_name}

Read these rules at the start of every session. Follow them on every response. Do not silently ignore them.

## Non-Negotiable Behavior

1. Load saved memory before planning, coding, or answering questions about prior work.
2. Prefer saved memory over stale chat history.
3. Never invent historical decisions.
4. If the user pastes a watch-generated handoff prompt, pause normal work and execute the handoff immediately.

## Memory Source Of Truth

Use this priority order:

1. If Obsidian mode is configured, use the latest notes under `Memory/Agent-Mem/`.
2. Otherwise, use `.agent-memory/active.md` first and `.agent-memory/memory.md` second.
3. Old chat history is lower priority than saved memory.
4. Code on disk overrides memory if they conflict. If they conflict, say so explicitly.

## Required Start-Of-Session Workflow

At the beginning of a new session:

1. Resolve the repository root.
2. Resolve the project name from the root folder name unless the user overrides it.
3. Load memory before proposing work.
4. State the current goal only after reading memory.

If MCP tools are available:

- call `query_memory(project_name, current_goal)`

If MCP tools are unavailable:

- read the latest memory files directly
- continue only after you have incorporated them

## Required Summarization Triggers

You must summarize when:

- context is getting long or repetitive
- a milestone is complete
- multiple files were changed for one logical task
- architecture, API, workflow, or design decisions changed
- the user is about to stop
- the user pastes an `agent-mem watch` handoff prompt

## Summary Format

Every summary must use these exact sections in this exact order:

- Goal
- Outcome
- Key decisions
- Files changed
- Open tasks or blockers
- Next prioritized steps

## Summary Quality Rules

Before saving memory, verify that:

- the goal matches the actual task
- the outcome reflects what was really completed
- key decisions are explicit, not implied guesses
- file paths are concrete
- blockers are still current
- next steps are actionable
- no secrets or credentials appear anywhere

## Obsidian-Specific Requirements

When Obsidian mode is enabled:

- write summaries as dense, durable engineering notes
- preserve frontmatter, headings, and wiki-links
- make decisions and file references explicit so the notes stay useful later
- prefer high-signal summaries over long narrative chat recaps

## Forbidden Behavior

Do not:

- claim a previous decision without memory or code evidence
- skip memory loading at session start
- treat a watch prompt like a normal chat message
- write apology text into memory
- dump vague prose when a structured summary is required

## Good Behavior Example

- Read memory
- State current goal
- Do the work
- Save a structured summary
- Produce a short fresh-chat handoff when context is bloated

## Bad Behavior Example

- Ignore memory
- Reconstruct history from guesswork
- Keep working in a bloated chat
- Save an unstructured paragraph instead of a proper summary
"""


def _cursor_rule_content(project_name: str) -> str:
    return f"""---
description: Enforce agent-mem memory loading, handoff handling, and structured summaries
alwaysApply: true
---

Use `AGENT-MEM-RULES.md` in the repository root as the canonical policy. Do not override it with your own assumptions.

Cursor-specific operating rules:

- Project name for this workspace is `{project_name}` unless the user explicitly says otherwise.
- At the start of every new chat, load memory before planning or coding.
- If the `agent-mem` MCP tools are visible, call `query_memory` immediately.
- If MCP tools are not visible, read the saved memory artifacts directly from the repo or Obsidian path.
- Treat `.agent-memory/active.md` as the current handoff state when local fallback mode is active.
- Before any non-trivial code edit, ground yourself in saved memory and current file state.
- If the user pastes a watch-generated handoff prompt, execute it immediately and do not treat it like an ordinary question.

Cursor execution checklist:

1. Read or query memory.
2. State the active goal.
3. Do the work.
4. Re-check whether key decisions changed.
5. Save a structured summary if anything important happened.
6. If context is bloated, generate a fresh-chat handoff.

Cursor summarization rules:

- Summarize on milestone completion.
- Summarize when context is starting to repeat.
- Summarize before ending a session with unresolved work.
- If the user pastes a handoff prompt generated by `agent-mem watch`, execute it immediately.
- Summaries must include decisions, changed files, open tasks, and next steps.
- In Obsidian mode, make the summary dense and durable: decisions, files, blockers, next actions, no fluff.

Cursor reliability rules:

- Do not trust stale chat over saved memory.
- Do not hallucinate previous decisions.
- Do not write secrets into memory.
- If memory and code conflict, report the conflict and prefer verified code state.
- If memory is missing, say that clearly instead of fabricating history.
"""


def _claude_instructions_content(project_name: str) -> str:
    return f"""# Agent Memory Instructions

Use `AGENT-MEM-RULES.md` as the canonical source of truth. Read and follow it every session.

Project name: {project_name}

Mandatory behavior at session start:

- Resolve the repository root.
- Resolve the project name from the repository root and keep it consistent.
- Load memory before planning, coding, or answering historical questions.
- Prefer saved memory over old chat history.
- If the user pastes a watch-generated handoff prompt, execute that handoff before anything else.

If MCP tools are available:

- call `query_memory` first
- call `summarize_to_obsidian` when needed

If MCP tools are unavailable:

- read the latest memory artifact directly
- prefer `.agent-memory/active.md` over older memory when fallback mode is active
- still produce the structured summary in chat if direct save tools are unavailable

Mandatory summarization triggers:

- long or repetitive context
- completed milestone
- important design or implementation decision
- multiple-file change
- session handoff or stop point
- a watch-generated handoff prompt pasted by the user

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
- in Obsidian mode, keep summaries dense, specific, and useful as future engineering notes
"""


def _simple_wrapper_content(path_hint: str) -> str:
    title = path_hint.capitalize()
    return f"""# Agent-Mem Instructions For {title}

Use `AGENT-MEM-RULES.md` in the repository root as the canonical memory policy.

Platform target: {path_hint}

Behavior requirements:

- Load memory at the start of each session.
- If the user pastes an `agent-mem watch` handoff prompt, execute it immediately.
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
        "cursor": "Cursor setup: reload the workspace. agent-mem created `.cursor/rules/agent-mem.mdc` and `.cursor/mcp.json`. Start a fresh chat. If `agent-mem watch` later copies a handoff prompt, paste it into the current Cursor chat, let Cursor summarize/save memory, then start a fresh chat with the starter block it returns.",
        "claude": "Claude / VS Code setup: reload the workspace. agent-mem created `.claude/instructions.md` and `.vscode/mcp.json`. If your Claude extension does not auto-read `.claude/instructions.md`, paste `AGENT-MEM-RULES.md` into custom instructions once. If `agent-mem watch` copies a handoff prompt, paste it into the current Claude chat, let it summarize/save memory, then start a fresh chat.",
        "antigravity": "Antigravity setup: reload the workspace. agent-mem created `.antigravity/rules.md`. If Antigravity needs MCP separately, use `agent-mem print-mcp-json`. If `agent-mem watch` copies a handoff prompt, paste it into the active chat and let the agent summarize/save memory before starting fresh.",
        "opencode": "OpenCode setup: reload the workspace. agent-mem created `.opencode/instructions.md`. If OpenCode needs MCP separately, use `agent-mem print-mcp-json` and add it in that product's MCP settings. If `agent-mem watch` copies a handoff prompt, paste it into the active chat and let the agent handle the summary/handoff.",
        "none": "No IDE files were created. You can still use `agent-mem checkpoint --stdin`, `agent-mem prepare-next`, `agent-mem recall`, and `agent-mem watch` directly from the terminal.",
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


def _run_graph_build(
    enrich: bool,
    compact: bool,
    exclude_file_patterns: List[str] | None = None,
    project_root: Path | None = None,
):
    resolved_root = (project_root or _project_root()).resolve()
    _echo("Building project knowledge graph...")
    try:
        result = build_graph(
            project_root=resolved_root,
            enrich=enrich,
            exclude_file_patterns=exclude_file_patterns or [],
            compact=compact,
        )
    except Exception as exc:
        _echo(f"❌ Graph build failed: {exc}", err=True)
        raise typer.Exit(1)

    _echo(f"✅ Graph notes generated at: {result.output_dir}")
    _echo(f"Files written   : {len(result.files_written)}")
    _echo(f"Python files    : {result.python_files_scanned}")
    _echo(f"Classes         : {result.classes_found}")
    _echo(f"Functions       : {result.functions_found}")
    _echo(f"Imports         : {result.imports_found}")
    _echo(f"Tagged comments : {result.comments_found}")
    _echo(f"Decisions       : {result.decisions_found}")
    _echo(f"Blockers        : {result.blockers_found}")
    _echo(f"Concepts        : {result.concepts_found}")
    _echo(f"LLM requested   : {'yes' if result.enrichment_requested else 'no'}")
    _echo(f"LLM enriched    : {'yes' if result.enriched else 'no'}")
    _echo(f"Compact mode    : {'yes' if result.compact else 'no'}")
    if result.notes:
        _echo("Notes:")
        for note in result.notes:
            _echo(f"  - {note}")


@graph_app.callback(invoke_without_command=True)
def graph(
    ctx: typer.Context,
    enrich: bool = typer.Option(
        False,
        "--enrich",
        help="Enable optional LLM concept/relationship enrichment.",
    ),
    exclude_file_pattern: List[str] = typer.Option(
        [],
        "--exclude-file-pattern",
        help="Glob pattern for Python files to exclude from graph extraction. Repeat the option for multiple patterns.",
    ),
    compact: bool = typer.Option(
        False,
        "--compact",
        help="Generate compact notes for large projects with truncated function and concept lists.",
    ),
):
    """Build markdown knowledge notes for code, memory, and sessions."""
    if ctx.invoked_subcommand is None:
        _run_graph_build(enrich=enrich, compact=compact, exclude_file_patterns=exclude_file_pattern)


@graph_app.command("build")
def graph_build(
    enrich: bool = typer.Option(
        False,
        "--enrich",
        help="Enable optional LLM concept/relationship enrichment.",
    ),
    exclude_file_pattern: List[str] = typer.Option(
        [],
        "--exclude-file-pattern",
        help="Glob pattern for Python files to exclude from graph extraction. Repeat the option for multiple patterns.",
    ),
    compact: bool = typer.Option(
        False,
        "--compact",
        help="Generate compact notes for large projects with truncated function and concept lists.",
    ),
):
    """Generate the agent-mem-output knowledge notes folder."""
    _run_graph_build(enrich=enrich, compact=compact, exclude_file_patterns=exclude_file_pattern)


@app.command("configure-groq")
def configure_groq(
    api_key: str = typer.Option("", "--api-key", help="Groq API key. If omitted, prompt securely."),
    model: str = typer.Option("", "--model", help="Groq model to use for watch handoff generation."),
):
    """Save Groq watch configuration for one-paste handoff generation."""
    config = get_config()
    resolved_key = api_key.strip() or _prompt_secret("Groq API key")
    if not resolved_key:
        _echo("❌ Groq API key is required.", err=True)
        raise typer.Exit(1)

    config["groq_api_key"] = resolved_key
    if model.strip():
        config["groq_model"] = model.strip()
    save_config(config)

    _echo(f"✅ Groq API key saved to {CONFIG_FILE}")
    _echo(f"Groq model      : {get_config().get('groq_model')}")
    _echo("You can now run: agent-mem watch --once --dry-run")


@app.command()
def init():
    """One-time setup - Obsidian is optional, local memory.md fallback is supported."""
    _echo("agent-mem setup (Obsidian path is optional)")
    vault = _prompt("Full path to your Obsidian vault (press Enter to skip and use local memory.md)", default="")

    existing = get_config()
    config = {
        "use_obsidian": False,
        "obsidian_vault": None,
        "groq_api_key": existing.get("groq_api_key"),
        "groq_model": existing.get("groq_model"),
    }
    if vault.strip():
        vault_path = Path(vault).expanduser().resolve()
        if vault_path.exists():
            config["use_obsidian"] = True
            config["obsidian_vault"] = str(vault_path)
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
    if get_groq_api_key():
        _echo("Watch mode      : Ready")
        _echo(f"Groq model      : {get_config().get('groq_model')}")
        _echo("Run this when you want automatic handoff generation:")
        _echo("  agent-mem watch --dry-run --once")
        _echo("Then remove --dry-run for real clipboard handoff prompts.")
    else:
        _echo("Watch mode      : Not configured yet")
        _echo("To enable one-paste handoff prompts:")
        _echo("  1. export GROQ_API_KEY=...   # temporary")
        _echo("  2. or run: agent-mem configure-groq")

    _echo("Terminal-only test:")
    _echo("  1. agent-mem checkpoint --stdin")
    _echo("  2. agent-mem prepare-next")
    _echo('  3. agent-mem recall "current goal"')
    _echo("  4. agent-mem graph build")
    if written_paths:
        _echo("You do not need to run `agent-mem serve` manually. Your IDE will launch it from the generated MCP config.")

    if _confirm("Generate initial graph notes now? (agent-mem-output/)", default=False):
        _run_graph_build(enrich=False, project_root=project_root)


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


@app.command("test-watch")
def test_watch(
    dry_run: bool = typer.Option(False, "--dry-run", help="Generate a local canned handoff instead of calling Groq."),
    project_name: str = typer.Option("", "--project-name", help="Override the inferred project name."),
    files: List[str] = typer.Option([], "--file", help="File path to include in the test handoff. Repeatable."),
):
    """Generate a watch handoff immediately without waiting for file events."""
    project_root = _project_root()
    effective_project_name = project_name.strip() or _project_name_from_root(project_root)
    initialize_storage(project_root)

    if not dry_run and not get_groq_api_key():
        _echo("❌ Groq is not configured.", err=True)
        _echo("Set GROQ_API_KEY in your shell or run: agent-mem configure-groq", err=True)
        _echo("If you just want to test formatting and delivery, run: agent-mem test-watch --dry-run", err=True)
        raise typer.Exit(1)

    from .watcher import (
        WatchResult,
        build_trigger,
        copy_to_clipboard,
        generate_dry_run_prompt,
        generate_handoff_prompt,
        render_alert,
        write_handoff_outbox,
    )

    changed_files = [item.strip() for item in files if item.strip()]
    trigger = build_trigger(
        project_root=project_root,
        project_name=effective_project_name,
        changed_files=changed_files,
        quiet_seconds=0,
    )
    try:
        prompt = generate_dry_run_prompt(trigger) if dry_run else generate_handoff_prompt(trigger)
        outbox_path = write_handoff_outbox(project_root, prompt)
        result = WatchResult(prompt=prompt, clipboard_ok=copy_to_clipboard(prompt), outbox_path=outbox_path)
    except RuntimeError as exc:
        _echo(f"❌ {exc}", err=True)
        raise typer.Exit(1)

    _echo(render_alert(result, dry_run=dry_run))
    _echo("")
    _echo(prompt)


@app.command()
def watch(
    quiet_seconds: int = typer.Option(180, "--quiet-seconds", min=5, help="Required quiet time after file activity before generating a handoff."),
    min_changes: int = typer.Option(5, "--min-changes", min=1, help="Minimum number of changed files before a handoff triggers."),
    min_diff_lines: int = typer.Option(400, "--min-diff-lines", min=1, help="Minimum git diff line count before a handoff triggers."),
    once: bool = typer.Option(False, "--once", help="Exit after the first automatic checkpoint is saved."),
    dry_run: bool = typer.Option(False, "--dry-run", help="Skip the Groq call and generate a canned handoff prompt for testing."),
    project_name: str = typer.Option("", "--project-name", help="Override the inferred project name."),
):
    """Watch the repo and generate one-paste handoff prompts for your IDE chat."""
    project_root = _project_root()
    effective_project_name = project_name.strip() or _project_name_from_root(project_root)
    initialize_storage(project_root)

    if not dry_run and not get_groq_api_key():
        _echo("❌ Groq is not configured.", err=True)
        _echo("Set GROQ_API_KEY in your shell or run: agent-mem configure-groq", err=True)
        _echo("If you just want to test the watcher flow, run: agent-mem watch --dry-run --once", err=True)
        raise typer.Exit(1)

    from .watcher import render_alert, run_watch_loop

    def _emit(message: str):
        _echo(message)

    def _handle_result(result):
        _echo("")
        _echo(render_alert(result, dry_run=dry_run))
        _echo("")
        _echo(result.prompt)
        _echo("")
        _echo("Next step: paste the prompt into your current IDE chat, let the agent summarize/save memory, then start a fresh chat with the starter block it returns.")

    try:
        run_watch_loop(
            project_root,
            effective_project_name,
            quiet_seconds=quiet_seconds,
            min_changes=min_changes,
            min_diff_lines=min_diff_lines,
            once=once,
            dry_run=dry_run,
            on_result=_handle_result,
            emit=_emit,
        )
    except KeyboardInterrupt:
        _echo("\nStopped watch mode.")
    except RuntimeError as exc:
        _echo(f"❌ {exc}", err=True)
        raise typer.Exit(1)


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
    groq_key = get_groq_api_key()
    groq_configured = "yes" if groq_key else "no"
    groq_source = "env/config" if groq_key else "missing"
    groq_model = config.get("groq_model")

    if config.get("use_obsidian") and vault:
        memory_dir = Path(vault) / "Memory" / "Agent-Mem"
        count = len(list(memory_dir.glob("*-session.md"))) if memory_dir.exists() else 0
        index_path = memory_dir / "Index.md"
        active_path = get_active_context_file(project_root)
        graph_dir = project_root / "agent-mem-output"
        graph_ready = graph_dir.exists()
        graph_docs = len(list(graph_dir.rglob("*.md"))) if graph_ready else 0
        _echo("Storage mode   : Obsidian")
        _echo(f"Obsidian vault : {vault}")
        _echo(f"Memory folder  : {memory_dir}")
        _echo(f"Index note     : {index_path}")
        _echo(f"Active context : {active_path}")
        _echo(f"Session notes  : {count} stored")
        _echo(f"Graph output   : {'yes' if graph_ready else 'no'}")
        _echo(f"Graph docs     : {graph_docs}")
        _echo("Graph command  : agent-mem graph build")
        _echo(f"Groq ready     : {groq_configured} ({groq_source})")
        _echo(f"Groq model     : {groq_model}")
        return

    fallback_file = project_root / ".agent-memory" / "memory.md"
    active_path = get_active_context_file(project_root)
    graph_dir = project_root / "agent-mem-output"
    graph_ready = graph_dir.exists()
    graph_docs = len(list(graph_dir.rglob("*.md"))) if graph_ready else 0
    _echo("Storage mode   : Local fallback")
    _echo(f"Memory file    : {fallback_file}")
    _echo(f"Active context : {active_path}")
    _echo(f"Memory exists  : {'yes' if fallback_file.exists() else 'no'}")
    _echo(f"Graph output   : {'yes' if graph_ready else 'no'}")
    _echo(f"Graph docs     : {graph_docs}")
    _echo("Graph command  : agent-mem graph build")
    _echo(f"Groq ready     : {groq_configured} ({groq_source})")
    _echo(f"Groq model     : {groq_model}")


if __name__ == "__main__":
    app()
