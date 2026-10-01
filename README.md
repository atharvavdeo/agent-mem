# agent-mem

![easy-agent-mem header](https://raw.githubusercontent.com/atharvavdeo/agent-mem/main/assets/repo-header.png)

[![GitHub release](https://img.shields.io/github/v/release/atharvavdeo/agent-mem)](https://github.com/atharvavdeo/agent-mem/releases/latest)
[![PyPI version](https://img.shields.io/pypi/v/easy-agent-mem?cacheSeconds=0)](https://pypi.org/project/easy-agent-mem/)
[![Python version](https://img.shields.io/pypi/pyversions/easy-agent-mem)](https://pypi.org/project/easy-agent-mem/)
[![License](https://img.shields.io/pypi/l/easy-agent-mem)](https://github.com/atharvavdeo/agent-mem/blob/main/LICENSE)
[![GitHub stars](https://img.shields.io/github/stars/atharvavdeo/agent-mem?style=social)](https://github.com/atharvavdeo/agent-mem/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/atharvavdeo/agent-mem?style=social)](https://github.com/atharvavdeo/agent-mem/network/members)
[![GitHub issues](https://img.shields.io/github/issues/atharvavdeo/agent-mem)](https://github.com/atharvavdeo/agent-mem/issues)
[![PyPI downloads](https://img.shields.io/pypi/dm/easy-agent-mem)](https://pypi.org/project/easy-agent-mem/)
[![Last commit](https://img.shields.io/github/last-commit/atharvavdeo/agent-mem)](https://github.com/atharvavdeo/agent-mem/commits/main)
[![MCP compatible](https://img.shields.io/badge/MCP-compatible-7c3aed)](https://github.com/atharvavdeo/agent-mem)
[![parser: tree-sitter](https://img.shields.io/badge/parser-tree--sitter-orange)](https://tree-sitter.github.io/tree-sitter/)
[![languages](https://img.shields.io/badge/languages-Python%20%7C%20TypeScript%20%7C%20JavaScript-blue)](https://github.com/atharvavdeo/agent-mem)
[![extraction F1](https://img.shields.io/badge/extraction%20F1-1.00-brightgreen)](https://github.com/atharvavdeo/agent-mem)
[![TUI](https://img.shields.io/badge/TUI-Textual-1d4ed8)](https://github.com/Textualize/textual)

Automatic context compression and persistent memory for AI coding agents.

`agent-mem` saves coding decisions, constraints and session context so you can continue work across chats. Search previous decisions, check whether their supporting files have changed, and carry relevant context into your next session.

---

## Why Use agent-mem

- Preserve critical context between chats and sessions
- Reduce token waste from repeating project history
- Keep technical decisions and blockers traceable
- Generate a searchable Obsidian-native knowledge graph from code + memory

---

## Core Features

- Save decisions, constraints and blockers with their sources and supporting files
- Check saved decisions for changed or missing evidence
- Retrieve relevant context with citations and a token budget
- Keep memory separate across repositories, branches, worktrees and sessions
- Resume sessions with durable handoffs and explicitly share selected records
- Track review findings, fixes, verification results and failed approaches
- Export structured memory to Markdown or Obsidian
- Smart `watch` mode with file + git + idle detection
- One-paste handoff prompts (Groq-powered, optional)
- Cross-IDE context migration (`agent-mem migrate`) for Cursor, Claude (VS Code), and OpenCode
- Obsidian-first storage with wiki-links and YAML frontmatter
- Local fallback mode (`.agent-memory/`) when Obsidian is not configured
- `graph` command builds project knowledge docs from code + memory + chat context
- **Call graph extraction** — tracks which functions call which across the codebase
- **Multi-language extraction** — Python (AST) + TypeScript/JavaScript (tree-sitter, optional)
- **MCP session gate** — warns agents that skip `query_memory` before summarizing
- **Claude Code enforcement hook** — `UserPromptSubmit` hook auto-injects memory context every prompt
- **Benchmark command** — `graph benchmark` measures extraction Precision/Recall/F1 against ground truth
- **Terminal UI** — `agent-mem tui` opens an interactive status/memory/benchmark dashboard
- Incremental graph parse cache for faster rebuilds on unchanged files

---

## Installation

```bash
pip install easy-agent-mem

# Install 0.8.0 from GitHub
pip install "git+https://github.com/atharvavdeo/agent-mem.git@v0.8.0"
```

Optional extras:

```bash
pip install 'easy-agent-mem[tui]'       # terminal UI (agent-mem tui)
pip install 'easy-agent-mem[multilang]' # TypeScript/JavaScript extraction via tree-sitter
pip install 'easy-agent-mem[mcp]'       # MCP server support
pip install 'easy-agent-mem[context] @ git+https://github.com/atharvavdeo/agent-mem.git@v0.8.0' # token counting
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

### 2) Import Context From Other IDE Chats

```bash
agent-mem migrate --dry-run cursor .
agent-mem migrate --full cursor claude .
```

### 3) Generate Project Knowledge Graph

```bash
agent-mem graph build --compact
agent-mem graph build --compact --enrich
```

### 4) Automated Handoff Watcher

```bash
agent-mem watch --dry-run --once
agent-mem watch
```

### 5) MCP / IDE Integration Helpers

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

### Graph Flags

| Flag | Description |
| --- | --- |
| `--compact` | Trims long concept/function lists, keeps dashboard/report complete, and writes full lists to `agent-mem-output/Full/` |
| `--enrich` | Adds inferred concepts/relationships via Groq; deterministic graph output is still generated if enrichment fails |
| `--exclude-file-pattern` | Excludes files by glob pattern; repeatable and useful for tests/generated/vendor paths |

---

## Migration (`agent-mem migrate`)

Bring context from other IDE chat stores into your current project memory.

### What It Does

- Extracts recognizable chat sessions from Cursor, Claude (VS Code), and OpenCode
- Compresses extracted context into agent-mem structured summary format
- In `--full` mode, saves summary to memory and generates a one-paste handoff prompt
- Writes portable markdown backups under `.agent-memory/migrations/`
- Supports safe simulation with `--dry-run`

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

---

## Commands Overview

### Setup and Configuration

| Command | Description | Example |
| --- | --- | --- |
| `agent-mem init` | Interactive first-time setup for storage + IDE instruction files + MCP config hints | `agent-mem init` |
| `agent-mem setup` | Re-run instruction + MCP config setup for current project | `agent-mem setup` |
| `agent-mem setup-vscode` | Write `.vscode/mcp.json` with detected/selected Python interpreter | `agent-mem setup-vscode --python /path/to/python3` |
| `agent-mem print-mcp-json` | Print MCP JSON block for manual paste into IDE config | `agent-mem print-mcp-json` |
| `agent-mem configure-groq` | Save Groq API key and optional model | `agent-mem configure-groq --model openai/gpt-oss-120b` |
| `agent-mem status` | Show storage mode, graph readiness, and Groq status | `agent-mem status` |

### Memory and Continuity

| Command | Description | Example |
| --- | --- | --- |
| `agent-mem summarize` | Save a structured session summary into memory | `agent-mem summarize --summary-file summary.md` |
| `agent-mem checkpoint` | Update compact active handoff context file | `agent-mem checkpoint --stdin` |
| `agent-mem prepare-next` | Print starter block for a fresh follow-up chat | `agent-mem prepare-next` |
| `agent-mem recall <query>` | Search saved memory for relevant context | `agent-mem recall "current blockers"` |
| `agent-mem engineering record` | Save a decision, constraint or blocker from JSON | `agent-mem engineering record --session feature-a < decision.json` |
| `agent-mem engineering list` | List private and explicitly shared records | `agent-mem engineering list --session feature-a` |
| `agent-mem engineering check` | Find decisions affected by changed files | `agent-mem engineering check --session feature-a --changed src/app.py` |
| `agent-mem engineering context` | Retrieve relevant context with citations and a token budget | `agent-mem engineering context "update storage" --session feature-a --token-budget 2048` |
| `agent-mem engineering checkpoint` | Save the current session checkpoint | `agent-mem engineering checkpoint --session feature-a` |
| `agent-mem engineering prepare-next` | Resume a saved session in a new chat | `agent-mem engineering prepare-next --session feature-a` |
| `agent-mem engineering share` | Share a selected record across linked worktrees | `agent-mem engineering share RECORD_ID --session feature-a` |
| `agent-mem engineering export` | Export session memory to Markdown | `agent-mem engineering export memory.md --session feature-a` |
| `agent-mem engineering review` | Record a finding, dismissal, fix, verification or failed approach | `agent-mem engineering review --session feature-a < review.json` |
| `agent-mem engineering reviews` | Retrieve review history and failed approaches | `agent-mem engineering reviews --session feature-a --goal "storage"` |

### Migration

| Command | Description | Example |
| --- | --- | --- |
| `agent-mem migrate` | Extract and convert IDE chat history into summaries/handoff/backups | `agent-mem migrate --full cursor claude .` |

### Graph

| Command | Description | Example |
| --- | --- | --- |
| `agent-mem graph build` | Generate knowledge graph notes and dashboard | `agent-mem graph build --compact --exclude-file-pattern "tests/*"` |
| `agent-mem graph benchmark` | Measure extraction Precision/Recall/F1 against fixture ground truth | `agent-mem graph benchmark --fixtures-dir tests/fixtures` |

### Terminal UI

| Command | Description | Example |
| --- | --- | --- |
| `agent-mem tui` | Open interactive terminal dashboard (Status / Memory / Benchmark tabs) | `agent-mem tui` |

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
- `.agent-memory/engineering/` for structured session records

Set `AGENT_MEM_STORAGE_DIR` to use a different local directory for structured memory.

---

## What's Fixed in 0.8.0

| Change | Use case |
| --- | --- |
| Separate MCP connection state | Keep simultaneous agent sessions independent |
| Durable session handles | Reconnect to the same saved session after restarting |
| Evidence freshness checks | Review decisions when their supporting files change |
| Latest review-result tracking | Show a newer failure instead of an outdated passing result |
| Scoped session exports | Keep exports from different branches and sessions separate |
| Atomic memory writes | Preserve saved context across interrupted writes |
| Improved path handling | Preserve file paths containing spaces in summaries and handoffs |
| Credential redaction | Remove configured secrets from stored context |

---

## Project Links

- PyPI: [easy-agent-mem](https://pypi.org/project/easy-agent-mem/)
- GitHub: [atharvavdeo/agent-mem](https://github.com/atharvavdeo/agent-mem)

---

## License

MIT
