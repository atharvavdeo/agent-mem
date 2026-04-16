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
- Graph dashboard summary cards with operational status and quick navigation
- Friendly `--enrich` diagnostics when Groq setup is missing/invalid
- Incremental graph parse cache for faster rebuilds on unchanged files
- Progress output for large project scans

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

## How To Use (Practical Flows)

### 1) First-Time Setup

```bash
agent-mem init
agent-mem status
agent-mem setup-vscode            # optional if you want .vscode/mcp.json generated directly
agent-mem configure-groq          # optional, enables watch handoff and graph enrich
```

### 2) Daily Memory Workflow

```bash
agent-mem checkpoint --stdin
agent-mem prepare-next
agent-mem recall "current goal"
```

### 3) Import Context From Other IDE Chats

```bash
agent-mem migrate --dry-run cursor .
agent-mem migrate --full cursor claude .
```

### 4) Generate Project Knowledge Graph

```bash
agent-mem graph build --compact
agent-mem graph build --compact --enrich
```

### 5) Automated Handoff Watcher

```bash
agent-mem watch --dry-run --once
agent-mem watch
```

### 6) MCP / IDE Integration Helpers

```bash
agent-mem print-mcp-json
agent-mem serve --force-stdio     # only for debugging MCP startup manually
```

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

### Common Recipes

```bash
# Fast baseline build
agent-mem graph build

# Large repo first pass (trim output size)
agent-mem graph build --compact

# Large repo focused pass (skip low-value paths)
agent-mem graph build --compact \
  --exclude-file-pattern "tests/*" \
  --exclude-file-pattern "**/migrations/*.py" \
  --exclude-file-pattern "**/node_modules/*"

# Semantic pass (requires Groq key)
agent-mem graph build --enrich
```

### Graph Flags

| Flag | Description |
| --- | --- |
| `--compact` | Trims long concept/function lists, keeps dashboard/report complete, and writes full lists to `agent-mem-output/Full/` |
| `--enrich` | Adds inferred concepts/relationships via Groq; deterministic graph output is still generated if enrichment fails |
| `--exclude-file-pattern` | Excludes files by glob pattern; repeatable and useful for tests/generated/vendor paths |

Flag behavior details:

- `--compact` is ideal for very large repos where full notes are noisy.
- `--enrich` does not block graph generation; if Groq is unavailable you still get deterministic notes plus actionable diagnostics.
- Multiple `--exclude-file-pattern` values are combined.
- Patterns match both full relative paths and file names.

### Generated Files

- `Index.md`: dashboard and navigation entrypoint
- `Code/*`: files, classes, functions, and imports
- `Decisions/*`: extracted decision and blocker signals
- `Sessions/recent-chats.md`: active and recent context snippets
- `Concepts.md`: concept inventory with `EXTRACTED` / `INFERRED` labels
- `Graph-Report.md`: plain-language summary with source breakdown and action suggestions

Open `agent-mem-output/Index.md` in Obsidian for full navigation and backlinks.
The dashboard includes quick navigation links, operational health status, and a direct link back to project root docs.

### Enrich Troubleshooting

If `--enrich` is requested but no inferred output is added, the CLI now prints actionable guidance.

Typical causes and fixes:

- Missing key: run `agent-mem configure-groq` or export `GROQ_API_KEY`.
- Invalid key/auth failure: reconfigure key and run `agent-mem status`.
- Missing client package: install `groq` (`pip install groq`).
- Rate limited: retry after a short delay.

### Large Project Performance

Graph builds now provide progress updates and incremental parse caching:

- Progress lines show scan stage and running cache-hit/reparse counts.
- Parsed-file cache is stored at `agent-mem-output/.graph-cache.json`.
- Unchanged Python files are reused from cache on subsequent runs.
- Use `--compact` and `--exclude-file-pattern` together for best large-repo responsiveness.

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

### Setup and Configuration

| Command | Description | Example |
| --- | --- | --- |
| `agent-mem init` | Interactive first-time setup for storage + IDE instruction files + MCP config hints | `agent-mem init` |
| `agent-mem setup` | Re-run instruction + MCP config setup for current project | `agent-mem setup` |
| `agent-mem setup-vscode` | Write `.vscode/mcp.json` with detected/selected Python interpreter | `agent-mem setup-vscode --python /path/to/python3` |
| `agent-mem print-mcp-json` | Print MCP JSON block for manual paste into IDE config | `agent-mem print-mcp-json` |
| `agent-mem configure-groq` | Save Groq API key and optional model | `agent-mem configure-groq --model llama-3.3-70b-versatile` |
| `agent-mem status` | Show storage mode, graph readiness, and Groq status | `agent-mem status` |

### Memory and Continuity

| Command | Description | Example |
| --- | --- | --- |
| `agent-mem summarize` | Save a structured session summary into memory | `agent-mem summarize --summary-file summary.md` |
| `agent-mem checkpoint` | Update compact active handoff context file | `agent-mem checkpoint --stdin` |
| `agent-mem prepare-next` | Print starter block for a fresh follow-up chat | `agent-mem prepare-next` |
| `agent-mem recall <query>` | Search saved memory for relevant context | `agent-mem recall "current blockers"` |

### Migration

| Command | Description | Example |
| --- | --- | --- |
| `agent-mem migrate` | Extract and convert IDE chat history into summaries/handoff/backups | `agent-mem migrate --full cursor claude .` |

### Graph

| Command | Description | Example |
| --- | --- | --- |
| `agent-mem graph build` | Generate knowledge graph notes and dashboard | `agent-mem graph build --compact --exclude-file-pattern "tests/*"` |

### Watch Mode and Handoff Automation

| Command | Description | Example |
| --- | --- | --- |
| `agent-mem watch` | Monitor repo activity and generate handoff prompts automatically | `agent-mem watch --once --dry-run` |
| `agent-mem test-watch` | Trigger one immediate handoff generation without waiting for file events | `agent-mem test-watch --dry-run` |

### MCP Server

| Command | Description | Example |
| --- | --- | --- |
| `agent-mem serve` | Start MCP stdio server (normally launched by IDE, not by hand) | `agent-mem serve --force-stdio` |

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
