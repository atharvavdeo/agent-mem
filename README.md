# agent-mem

CLI-first persistent memory for AI coding sessions.

`agent-mem` saves structured session summaries either directly into an Obsidian vault as normal Markdown notes or into a local fallback store inside the project. It is designed to reduce context bloat, preserve decisions, and make recall usable even when IDE or MCP automation is unreliable.

## Install

```bash
pip install easy-agent-mem
```

Optional MCP support:

```bash
pip install "easy-agent-mem[mcp]"
```

## What It Does

- connects to an Obsidian vault during setup
- writes Obsidian-friendly `.md` notes directly into the vault
- creates graph-friendly wiki-links and YAML frontmatter
- keeps a local `.agent-memory/memory.md` fallback when Obsidian is not configured
- provides CLI commands to save and recall context without depending on IDE prompt rules

## Quick Start

```bash
agent-mem init
```

During `init`:

- if you provide an Obsidian vault path, notes are written to:
  - `<vault>/Memory/Agent-Mem/`
- if you skip the vault path, memory is stored locally in:
  - `.agent-memory/memory.md`

After setup:

```bash
agent-mem summarize --summary "## Goal

Ship the release.

## Key decisions
- Use Obsidian as primary storage.

## Open tasks
- Publish 0.4.0"
```

Then recall it later:

```bash
agent-mem recall "release status"
```

## Obsidian Mode

When connected to Obsidian, `agent-mem` writes real Markdown notes directly into your vault. You do not need a plugin. Obsidian sees the notes automatically because they live inside the vault folder.

Current layout:

```text
<vault>/
  Memory/
    Agent-Mem/
      Index.md
      project-name-YYYY-MM-DD_HH-MM-session.md
```

Session notes include:

- YAML frontmatter
- wiki-links like `[[project-name]]`
- file links like `[[File - src/agent_mem/memory.py]]`
- task links like `[[Task - publish 0.4.0]]`

## Commands

```bash
agent-mem init
agent-mem summarize --summary "..."
agent-mem summarize --summary-file session.md
cat summary.md | agent-mem summarize --stdin
agent-mem recall "auth decisions"
agent-mem status
agent-mem setup-vscode
agent-mem print-mcp-json
agent-mem serve
```

## IDE Usage

The core product works without MCP.

Recommended flow:

1. run `agent-mem init`
2. add `AGENT-MEM-RULES.md` to your IDE custom instructions
3. use `agent-mem summarize` to save milestones
4. use `agent-mem recall` to reload context

If you want MCP integration, install the optional extra and use:

```bash
agent-mem setup-vscode
```

## Status

`agent-mem` is intentionally simple:

- Obsidian is just a Markdown vault
- the CLI writes notes directly
- fallback mode stays fully usable without Obsidian

The design goal is reliable context preservation first, deeper automation second.

## Links

- PyPI: [https://pypi.org/project/easy-agent-mem/](https://pypi.org/project/easy-agent-mem/)
- Source: [https://github.com/atharvavdeo/agent-mem](https://github.com/atharvavdeo/agent-mem)

## License

MIT
