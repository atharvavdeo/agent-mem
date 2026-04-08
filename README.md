# agent-mem

**Persistent memory layer for AI coding agents** (Cursor, VS Code + Claude Code, etc.)

Tired of repeating context every time you start a new chat?
`agent-mem` automatically maintains a clean project memory file so your agent always knows what happened before - without bloating the context window.

## Features

- Simple local fallback: `.agent-memory/memory.md`
- Optional Obsidian vault support (with full graph view, backlinks, Canvas)
- Auto-generates strong agent instruction rules
- Zero extra models or API keys needed
- Works with any MCP-compatible IDE (Cursor, VS Code, etc.)
- Extremely lightweight

## Installation

```bash
pip install easy-agent-mem
```

## Quick Start

```bash
# 1. One-time setup
agent-mem init

# 2. (Recommended) Add the generated rules to your IDE
#    - Cursor: Settings -> Custom Instructions
#    - VS Code: Create CLAUDE.md or .claude/instructions.md in project root
```

During `init` you can:

- Provide an Obsidian vault path (optional)
- Or just press Enter to use the simple local `.agent-memory/memory.md` fallback

## How It Works

1. `agent-mem init` creates:
   - `AGENT-MEM-RULES.md` (strong instructions for the agent)
   - `.agent-memory/memory.md` (or Obsidian notes)

2. Add the rules from `AGENT-MEM-RULES.md` to your IDE's custom instructions.

3. From then on, your agent will:
   - Read memory first in every new chat
   - Summarize sessions when context gets long
   - Keep a clean, persistent project history

## Example Usage in Chat

Tell your agent:
> "Summarize this session for memory"

It will create a clean summary and append it to memory. Then start a fresh chat - the agent will automatically load the latest memory.

## Commands

```bash
agent-mem init          # Setup (Obsidian optional)
agent-mem status        # Show current config
agent-mem --help        # Full help
```

## Project Links

- PyPI: [https://pypi.org/project/easy-agent-mem/](https://pypi.org/project/easy-agent-mem/)
- Source: [https://github.com/atharvavdeo/agent-mem](https://github.com/atharvavdeo/agent-mem)

## License

MIT
