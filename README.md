![easy-agent-mem header](assets/repo-header.png)

# agent-mem

CLI-first persistent memory for AI coding sessions.

`agent-mem` keeps coding context outside the live chat window. It saves structured summaries directly into an Obsidian vault when one is configured, or into a local fallback store inside the project when Obsidian is not available.

That gives you a simple workflow:

- save progress as memory
- reopen memory later with a focused query
- keep chat context smaller
- stop repeating the same project decisions across sessions

## Why This Exists

Long coding chats drift. Important decisions get buried, context windows bloat, and new sessions start cold.

`agent-mem` fixes that with a local, inspectable memory layer:

- **Obsidian-first** when you want graph view, backlinks, and durable notes
- **project-local fallback** when you want zero extra setup
- **CLI-first** so the product works even without MCP or IDE-specific integrations

## Core Features

- direct Obsidian vault connection during `init`
- Obsidian-friendly session notes with:
  - YAML frontmatter
  - wiki-links
  - `Index.md` updates
- local fallback in `.agent-memory/memory.md`
- CLI commands to:
  - initialize storage
  - save structured summaries
  - recall relevant memory
  - watch file activity and create automatic checkpoints
- optional MCP support for IDEs that expose tools reliably
- generated instruction files tailored for:
  - Cursor
  - Claude / VS Code
  - Antigravity
  - OpenCode

## Installation

```bash
pip install easy-agent-mem
```

Optional MCP support:

```bash
pip install "easy-agent-mem[mcp]"
```

## Quick Start

### 1. Initialize the project

```bash
agent-mem init
```

During setup you can:

- connect an Obsidian vault
- or skip it and use local fallback storage

### 2. Save a session summary

```bash
agent-mem summarize --summary "## Goal

Ship the release.

## Outcome

Prepared the package for publication.

## Key decisions
- Use Obsidian as primary storage.

## Files changed
- src/agent_mem/memory.py

## Open tasks or blockers
- Publish 0.4.2

## Next prioritized steps
- Verify the built wheel."
```

### 3. Recall memory later

```bash
agent-mem recall "release status"
```

### 4. Run automatic checkpointing

```bash
agent-mem watch
```

This monitors file activity in the current repo and writes an automated checkpoint once activity settles.

## Storage Modes

### Obsidian Mode

If you provide a vault path during `agent-mem init`, notes are written directly into:

```text
<vault>/Memory/Agent-Mem/
```

Current layout:

```text
<vault>/
  Memory/
    Agent-Mem/
      Index.md
      project-name-YYYY-MM-DD_HH-MM-session.md
```

Session notes are normal Markdown files, so Obsidian picks them up automatically.

They include:

- YAML frontmatter
- wiki-links like `[[project-name]]`
- file links like `[[File - src/agent_mem/cli.py]]`
- task links like `[[Task - ship release]]`

### Local Fallback Mode

If you skip Obsidian, memory is stored in:

```text
.agent-memory/memory.md
```

This keeps the product usable even in plain local repos without extra tools.

## Commands

```bash
agent-mem init
agent-mem summarize --summary "..."
agent-mem summarize --summary-file session.md
cat summary.md | agent-mem summarize --stdin
agent-mem recall "auth decisions"
agent-mem watch
agent-mem status
agent-mem setup
agent-mem setup-vscode
agent-mem print-mcp-json
agent-mem serve
```

## IDE Integration

`agent-mem` works best when the IDE is instructed to treat saved memory as the source of truth.

The repo can generate instruction files automatically for:

- `AGENT-MEM-RULES.md`
- `.cursor/rules/agent-mem.mdc`
- `.claude/instructions.md`
- `CLAUDE.md`
- `.antigravity/rules.md`
- `.opencode/instructions.md`

Recommended IDE workflow:

1. run `agent-mem init`
2. add the generated instructions to your IDE
3. use `agent-mem summarize` after milestones
4. use `agent-mem recall` at the start of new sessions

Optional MCP workflow:

```bash
agent-mem setup-vscode
agent-mem serve
```

## Automated Checkpoints

`agent-mem watch` is a lightweight file-activity watcher.

It:

- polls the repo for file changes
- waits for a quiet period
- writes an automatic checkpoint summary after enough changes accumulate

Useful options:

```bash
agent-mem watch --interval 2 --quiet-seconds 20 --min-changes 3
agent-mem watch --once
```

This is not a replacement for a high-quality manual summary. It is a safety net to avoid losing context between work bursts.

## Release Notes

### 0.4.1

- added tailored IDE-specific instruction files for Cursor, Claude, Antigravity, and OpenCode
- strengthened generated rules with explicit summarization checks and anti-hallucination guidance
- aligned the instruction-file generator with the checked-in templates

### 0.4.0

- introduced Obsidian-first storage with direct vault note writing
- added YAML frontmatter, wiki-links, and `Index.md`
- added CLI-first `summarize` and `recall`
- kept local fallback mode intact

## Project Links

- PyPI: [easy-agent-mem](https://pypi.org/project/easy-agent-mem/)
- Source: [github.com/atharvavdeo/agent-mem](https://github.com/atharvavdeo/agent-mem)

## License

MIT
