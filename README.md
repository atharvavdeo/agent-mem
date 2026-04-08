# agent-mem

agent-mem is a lightweight, local-first persistent memory layer for AI coding agents in IDEs like VS Code and Cursor.

It helps you keep project context stable across chats by:

- creating a strong instruction file (`AGENT-MEM-RULES.md`)
- maintaining a clean memory source (`.agent-memory/memory.md`)
- optionally using Obsidian (`<vault>/Memory/Agent-Mem/`)

## Quick Start

```bash
pip install atharva-agent-mem

agent-mem init
# Follow prompts (Obsidian optional)

# Then add the generated AGENT-MEM-RULES.md content to your IDE custom instructions
```

## How It Works

1. Run `agent-mem init` in your project root.
2. agent-mem creates instruction files and initializes local memory fallback.
3. Your agent reads project memory first before planning or coding.
4. As chat context grows, your agent appends concise session summaries.

This keeps memory durable without relying on long chat history.

## What `agent-mem init` Creates

- `AGENT-MEM-RULES.md` (main rule file)
- `.cursor/rules/agent-mem.mdc`
- `.claude/instructions.md`
- `CLAUDE.md`
- `.antigravity/rules.md`
- `.opencode/instructions.md`

Optional local MCP config files can also be generated:

- `.vscode/mcp.json`
- `.cursor/mcp.json`

## Storage Modes

- Local-first (default): `<project-root>/.agent-memory/memory.md`
- Optional Obsidian: `<vault>/Memory/Agent-Mem/`

If Obsidian path is missing or invalid, agent-mem automatically uses local fallback.

## CLI Commands

- `agent-mem init`: interactive setup (recommended)
- `agent-mem setup`: create instruction files and local MCP configs
- `agent-mem status`: show active storage mode and memory location
- `agent-mem print-mcp-json`: print MCP JSON block for manual config
- `agent-mem setup-vscode`: write `.vscode/mcp.json` with selected Python path
- `agent-mem serve`: run optional MCP server (requires MCP extra)

## Optional MCP Mode

MCP is optional for v0.3.0. Base usage does not require it.

```bash
pip install "atharva-agent-mem[mcp]"
agent-mem serve
```

Example MCP config:

```json
{
  "mcpServers": {
    "agent-mem": {
      "command": "agent-mem",
      "args": ["serve"]
    }
  }
}
```

## Development Build Check

```bash
pip install build twine
python -m build
twine check dist/*
```

## License

MIT
