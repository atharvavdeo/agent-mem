![easy-agent-mem header](https://raw.githubusercontent.com/atharvavdeo/agent-mem/main/assets/repo-header.png)

# agent-mem

CLI-first persistent memory and one-paste handoff control for AI coding sessions.

`agent-mem` keeps coding context outside the live chat window and helps you compress bloated chats before they become useless.

It does three things:

- stores durable memory locally or in Obsidian
- gives the next chat a compact active handoff
- watches for meaningful work and generates a one-paste prompt that tells your IDE agent to summarize, save memory, and start fresh

## Why This Exists

Long coding chats drift. Important decisions get buried, context windows bloat, and new sessions start cold.

`agent-mem` fixes that with a local, inspectable memory layer:

- **Obsidian-first** when you want graph view, backlinks, and durable notes
- **project-local fallback** when you want zero extra setup
- **CLI-first** so the product works even without MCP or IDE-specific integrations
- **one-paste watch mode** so you can shrink context without manually designing handoff prompts

## Core Features

- direct Obsidian vault connection during `init`
- Obsidian-friendly session notes with:
  - YAML frontmatter
  - wiki-links
  - `Index.md` updates
- local fallback in `.agent-memory/memory.md`
- one common rules file plus one selected IDE wrapper
- CLI commands to:
  - initialize storage
  - save structured summaries
  - recall relevant memory
  - prepare the next fresh chat
  - watch file activity and generate handoff prompts
  - test the handoff flow without waiting for file events
- optional MCP support for IDEs that expose tools reliably
- generated instruction files tailored only for the IDE you choose:
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

### 1. Initialize the project and choose your IDE

```bash
agent-mem init
```

During setup you can:

- connect an Obsidian vault
- or skip it and use local fallback storage
- choose only the IDE you actually use

`init` will create:

- `AGENT-MEM-RULES.md`
- local memory storage
- one IDE-specific wrapper/config, not all of them

### 2. Configure Groq for one-paste watch mode

```bash
agent-mem configure-groq
```

Or set it in the shell:

```bash
export GROQ_API_KEY=...
```

### 3. Test the handoff flow immediately

```bash
agent-mem test-watch --dry-run
```

This does not wait for file events. It generates a sample handoff prompt, writes it to the outbox, and tries to copy it to your clipboard.

### 4. Run the real watch loop

```bash
agent-mem watch
```

When enough work accumulates and the repo goes quiet, `agent-mem` will:

- inspect the current work
- call Groq for a compact structured digest
- build one ready-to-paste prompt for your IDE chat
- copy it to the clipboard when possible
- write it to `.agent-memory/outbox/latest-handoff.md`
- print a loud terminal alert

### 5. Paste the handoff into your IDE chat

Paste the prompt into the current chat. Your IDE agent should then:

1. summarize the current work with the required sections
2. save memory if the tools are available
3. produce a short fresh-chat starter block
4. tell you to start a new chat

That is the core one-paste loop.

### 6. Save or update memory manually when needed

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

### 7. Recall memory later

```bash
agent-mem recall "release status"
```

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
- extracted sections for:
  - goal
  - outcome
  - key decisions
  - files changed
  - open tasks or blockers
  - next prioritized steps

### Local Fallback Mode

If you skip Obsidian, memory is stored in:

```text
.agent-memory/active.md
.agent-memory/memory.md
.agent-memory/outbox/latest-handoff.md
```

This keeps the product usable even in plain local repos without extra tools.

- `active.md` is the compact live handoff state
- `memory.md` is the longer session log
- `outbox/latest-handoff.md` is the latest watch-generated prompt

## Commands

```bash
agent-mem init
agent-mem configure-groq
agent-mem test-watch --dry-run
agent-mem summarize --summary "..."
agent-mem summarize --summary-file session.md
cat summary.md | agent-mem summarize --stdin
cat summary.md | agent-mem checkpoint --stdin
agent-mem recall "auth decisions"
agent-mem prepare-next
agent-mem watch
agent-mem watch --dry-run --once
agent-mem status
agent-mem setup
agent-mem setup-vscode
agent-mem print-mcp-json
agent-mem serve
```

## IDE Integration

`agent-mem` works best when the IDE is instructed to treat saved memory as the source of truth and to treat watch-generated prompts as urgent handoff requests.

The repo generates:

- one common rules file: `AGENT-MEM-RULES.md`
- one IDE-specific wrapper/config for the IDE you selected during `init`

Recommended IDE workflow:

1. run `agent-mem init`
2. reload the IDE workspace
3. run `agent-mem configure-groq`
4. run `agent-mem test-watch --dry-run`
5. when ready, run `agent-mem watch`
6. paste the copied handoff prompt into the active IDE chat when watch fires
7. let the IDE summarize/save memory and give you a fresh-chat starter
8. start a new chat

Optional MCP workflow:

```bash
agent-mem setup-vscode
```

Do not run `agent-mem serve` manually. The IDE should launch it from the generated MCP config.

## Watch Mode

`agent-mem watch` is a local file watcher plus handoff generator.

It:

- watches file changes locally
- waits until work settles
- inspects git diff stats and active memory
- calls Groq for a tight structured digest
- renders one ready-to-paste IDE prompt
- copies it to the clipboard if possible
- writes the same prompt to the outbox file
- tells you to compress the chat now

Useful options:

```bash
agent-mem test-watch --dry-run
agent-mem watch --dry-run --once
agent-mem watch --quiet-seconds 180 --min-changes 5 --min-diff-lines 400
agent-mem watch --once
```

This is not a replacement for a good IDE-side summary. It is the control loop that tells your IDE when to summarize and how to hand off cleanly.

## Release Notes

### 0.5.0

- Groq-backed one-paste watch mode
- `configure-groq`
- `test-watch`
- tighter IDE rule files
- stronger handoff contract for context compression
- improved Obsidian note structure for denser engineering summaries

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
