# agent-mem

![easy-agent-mem header](https://raw.githubusercontent.com/atharvavdeo/agent-mem/main/assets/repo-header.png)

![PyPI version](https://img.shields.io/pypi/v/easy-agent-mem)
![Python version](https://img.shields.io/pypi/pyversions/easy-agent-mem)
![License](https://img.shields.io/pypi/l/easy-agent-mem)
![GitHub stars](https://img.shields.io/github/stars/atharvavdeo/agent-mem?style=social)
![GitHub forks](https://img.shields.io/github/forks/atharvavdeo/agent-mem?style=social)
![GitHub issues](https://img.shields.io/github/issues/atharvavdeo/agent-mem)
![PyPI downloads](https://img.shields.io/pypi/dm/easy-agent-mem)
![Last commit](https://img.shields.io/github/last-commit/atharvavdeo/agent-mem)

Automatic context compression and persistent memory for AI coding agents.

`agent-mem` helps you keep long coding sessions coherent by capturing decisions, session context, and code signals in structured memory notes. It also generates Obsidian-friendly project graph docs so you can navigate architecture, decisions, blockers, and recent context quickly.

---

## Why Use agent-mem

- Preserve critical context between chats and sessions
- Reduce token waste from repeating project history
- Keep technical decisions and blockers traceable
- Generate a searchable Obsidian-native knowledge graph from code + memory

---

## Core Features

- Smart `watch` mode with file + git + idle detection
- One-paste handoff prompts (Groq-powered, optional)
- Cross-IDE context migration (`agent-mem migrate`) for Cursor, Claude (VS Code), and OpenCode
- Obsidian-first storage with wiki-links and YAML frontmatter
- Local fallback mode (`.agent-memory/`) when Obsidian is not configured
- `graph` command to build project knowledge docs from code + memory + chat context

---

## Installation

```bash
pip install easy-agent-mem
```

---

## Quick Start

```bash
agent-mem init
agent-mem configure-groq      # optional for enrich/watch handoff generation
agent-mem migrate --dry-run cursor .
agent-mem watch               # start automatic handoff mode
```

After initialization, use `agent-mem status` to verify storage mode, graph output readiness, and Groq configuration status.

---

## Knowledge Graph (`agent-mem graph`)

Generate Obsidian-native docs into `agent-mem-output/`:

```bash
agent-mem graph build
```

Use optional flags:

```bash
agent-mem graph build --compact
agent-mem graph build --enrich
agent-mem graph build --compact --enrich
agent-mem graph build --exclude-file-pattern "tests/*" --exclude-file-pattern "**/migrations/*.py"
```

### Graph Flags

| Flag | Description |
| --- | --- |
| `--compact` | Trims long concept/function lists and writes full lists to `agent-mem-output/Full/` |
| `--enrich` | Adds inferred concepts/relationships via Groq when available |
| `--exclude-file-pattern` | Excludes files by glob pattern; repeatable |

### Generated Files

- `Index.md`: dashboard and navigation entrypoint
- `Code/*`: files, classes, functions, and imports
- `Decisions/*`: extracted decision and blocker signals
- `Sessions/recent-chats.md`: active and recent context snippets
- `Concepts.md`: concept inventory with `EXTRACTED` / `INFERRED` labels
- `Graph-Report.md`: plain-language summary with source breakdown and action suggestions

Open `agent-mem-output/Index.md` in Obsidian for full navigation and backlinks.
The dashboard includes quick navigation links, operational health status, and a direct link back to project root docs.

---

## Daily Workflow

```bash
agent-mem watch
agent-mem migrate --extract-only cursor .
agent-mem checkpoint --stdin
agent-mem prepare-next
agent-mem recall "current goal"
agent-mem graph build --compact
```

Use this flow to maintain continuity during active implementation and produce graph notes when you need a wider project snapshot.

---

## Migration (`agent-mem migrate`)

Bring context from other IDE chat stores into your current project memory.

### What It Does

- Extracts recognizable chat sessions from Cursor, Claude (VS Code), and OpenCode
- Compresses extracted context into agent-mem structured summary format
- In `--full` mode, saves summary to memory and generates a one-paste handoff prompt
- Writes portable markdown backups under `.agent-memory/migrations/`
- Supports safe simulation with `--dry-run`

### Source Notes

- `cursor`: best support on macOS and local `.cursor` storage
- `claude`: scans `.claude`, `.vscode`, and VS Code workspace storage paths
- `opencode`: scans local `.opencode` and common OpenCode config paths
- `antigravity`: best-effort extraction only (depends on local transcript format)

### Examples

```bash
agent-mem migrate
agent-mem migrate cursor .
agent-mem migrate --extract-only cursor claude .
agent-mem migrate --full cursor claude .
agent-mem migrate --dry-run cursor .
agent-mem migrate --full cursor .
agent-mem migrate --dry-run --full cursor claude opencode .
```

### Modes

- `--extract-only`: extract + backup only (default for direct CLI usage)
- `--full`: extract + save summary to memory + generate handoff + backup
- `--dry-run`: no file writes, prints preview summary/handoff output

### Recommended Workflow

```bash
# 1) Preview what will be extracted
agent-mem migrate --dry-run cursor .

# 2) Persist memory + handoff prompt for actual continuation
agent-mem migrate --full cursor .

# 3) Paste the generated handoff prompt into your active IDE chat
#    and let the agent write a fresh structured summary.
```

### Output Artifacts

- Memory summary:
  - Obsidian mode: `Memory/Agent-Mem/<project>-<timestamp>-session.md`
  - Fallback mode: `.agent-memory/memory.md`
- Handoff outbox: `.agent-memory/outbox/latest-handoff.md`
- Migration backup: `.agent-memory/migrations/<timestamp>-<sources>.md`

---

## Commands Overview

| Command | Description |
| --- | --- |
| `agent-mem init` | Configure storage mode and IDE instructions |
| `agent-mem configure-groq` | Set Groq API key and model configuration |
| `agent-mem migrate` | Extract IDE chat history and convert it into memory/handoff artifacts |
| `agent-mem watch` | Run automatic handoff watcher |
| `agent-mem graph build` | Build knowledge graph notes |
| `agent-mem summarize` | Save manual structured summary |
| `agent-mem checkpoint` | Update compact active handoff context |
| `agent-mem prepare-next` | Print starter block for a fresh chat |
| `agent-mem recall <query>` | Search saved memory |
| `agent-mem status` | Show storage, graph, and Groq configuration |

---

## Storage Modes

### Obsidian Mode

If Obsidian is configured, notes are written under:

- `Memory/Agent-Mem/` for session and active context notes
- `agent-mem-output/` for graph notes

### Local Fallback Mode

If Obsidian is unavailable, memory is written to:

- `.agent-memory/active.md`
- `.agent-memory/memory.md`

---

## Troubleshooting

- If `--enrich` does not apply inferred content, run `agent-mem status` and verify Groq key/model configuration.
- If graph output is too large, use `--compact`.
- For large repos, exclude low-value paths with repeatable `--exclude-file-pattern` options.

---

## Project Links

- PyPI: [easy-agent-mem](https://pypi.org/project/easy-agent-mem/)
- GitHub: [atharvavdeo/agent-mem](https://github.com/atharvavdeo/agent-mem)

---

## License

MIT
