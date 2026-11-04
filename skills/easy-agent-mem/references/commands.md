# easy-agent-mem 0.8.0 — complete client command reference

Checked on 4 November 2026 against the published PyPI 0.8.0 package. All **33 help pages** were opened successfully: the root, 18 direct commands, two command groups, and 12 grouped commands. This confirms the available command interface; it does not mean every optional integration or provider call was executed.

The companion skill teaches an agent when to recall, save, check evidence and hand off. The separately installed easy-agent-mem application supplies the broader CLI, MCP tools, watcher, graph generation and terminal dashboard documented here. Installing the skill ZIP alone does not install these application features.

## Install only the features you need

Requires Python 3.10 or newer. Run commands from the intended project folder unless a command supplies `--root`.

```sh
python3 -m pip install 'easy-agent-mem==0.8.0'
```

| Optional extra | Adds | Installation |
| --- | --- | --- |
| `mcp` | Local MCP server dependency | `python3 -m pip install 'easy-agent-mem[mcp]==0.8.0'` |
| `tui` | Interactive terminal dashboard | `python3 -m pip install 'easy-agent-mem[tui]==0.8.0'` |
| `multilang` | TypeScript/JavaScript extraction dependencies | `python3 -m pip install 'easy-agent-mem[multilang]==0.8.0'` |
| `context` | tiktoken-based context token counting | `python3 -m pip install 'easy-agent-mem[context]==0.8.0'` |
| `intelligence` | Optional code-review-graph integration dependency | `python3 -m pip install 'easy-agent-mem[intelligence]==0.8.0'` |

Combine extras when needed, for example `easy-agent-mem[mcp,tui,context]==0.8.0`. Basic save/recall and deterministic graph extraction do not require a provider API key. Generated watcher handoffs and optional graph enrichment use the selected Groq or Cerebras provider. `--dry-run` watcher modes use canned output instead of a provider call; they can still write local test output. Model availability and provider billing are separate from this package.

## All direct commands

Every command supports `--help`.

| Command | What it does | Arguments and options |
| --- | --- | --- |
| `configure-groq` | Select/save Groq configuration for generated handoffs | `--api-key TEXT` (secure prompt if omitted); `--model TEXT`. Prefer the secure prompt instead of putting secrets in shell history. |
| `configure-cerebras` | Select Cerebras while retaining existing Groq settings | `--model TEXT` (0.8.0 default: `qwen-3.8-27b`); `--use-env` uses an already-set `CEREBRAS_API_KEY` without saving the key. Otherwise prompts securely. |
| `init` | Interactive initial setup, with optional Obsidian or local fallback | No command-specific flags. It may write project instructions/configuration. |
| `setup` | Write project instruction files and MCP configurations | No command-specific flags. Review generated configuration for the actual client. |
| `setup-cursor` | Add project Cursor lifecycle hooks | No command-specific flags. Hook behavior depends on the client delivering its lifecycle events. |
| `cursor-hook EVENT` | Process a native Cursor event from standard input | Required `EVENT`; intended for hook wiring rather than ordinary manual use. |
| `setup-vscode` | Write `.vscode/mcp.json` | `--python TEXT` selects the Python executable. Review the output against the client's current native schema before use. |
| `print-mcp-json` | Print an example MCP JSON block without writing files | `--python TEXT`. Client schemas differ; this is not universal native configuration. |
| `migrate [TARGETS]...` | Import supported IDE chat history | Sources: `cursor`, `claude`, `opencode`, `antigravity`, or `all`, optionally followed by a project path. Options: `--full`, `--extract-only`, `--dry-run`, `--project-name TEXT`, `--max-sessions INTEGER` (1–100, default 20), `--max-messages INTEGER` (20–5000, default 400). |
| `summarize` | Save a summary to configured Obsidian or local fallback | Input via `--summary TEXT`, `--summary-file TEXT`, or `--stdin`; optional `--project-name TEXT`. |
| `checkpoint` | Refresh the compact handoff context | Input via `--summary TEXT`, `--summary-file TEXT`, or `--stdin`; `--project-name TEXT`; `--save-session` / `--no-save-session` (default: do not also save long-term session memory). |
| `prepare-next` | Print a starter block for the next chat | `--project-name TEXT`. This is the compact Markdown handoff path; scoped engineering handoffs have a separate command below. |
| `recall QUERY` | Search relevant saved memory | Required `QUERY`; `--project-name TEXT`; `--count INTEGER` (1–20, default 5 recent sources). |
| `test-watch` | Generate a watcher handoff immediately | `--dry-run`; `--project-name TEXT`; repeatable `--file TEXT`. Non-dry-run generation needs the selected provider's API key. |
| `watch` | Watch changes and generate handoff prompts | `--quiet-seconds INTEGER` (minimum 5, default 180); `--min-changes INTEGER` (minimum 1, default 5); `--min-diff-lines INTEGER` (minimum 1, default 400); `--once`; `--dry-run`; `--project-name TEXT`. |
| `serve` | Run the local MCP endpoint | `--force-stdio` allows an interactive terminal for debugging. Normally let the client launch it. |
| `status` | Display storage/provider status and session count | No command-specific flags. |
| `tui` | Open the interactive terminal dashboard | Requires the `tui` extra; no command-specific flags. This is a terminal interface, not a standalone web GUI. |

At the root, `agent-mem --install-completion` installs shell completion and `agent-mem --show-completion` prints it. There is no root `--version` option in this release; use `python3 -m pip show easy-agent-mem` to inspect the installed version.

### Migration modes

`migrate --full` extracts context, saves a summary, creates a handoff and writes a Markdown backup. `--extract-only` writes extracted chat backups without saving memory/handoff. Do not combine those two flags. With explicit sources and neither mode, CLI execution defaults to extract-only; interactive execution asks about full mode. `--dry-run` previews without writing migration output. `claude` here refers to the migration source supported by this release, described in the product documentation as Claude in VS Code; it is not a promise of universal native Claude Code transcript import. Antigravity import is best-effort and depends on locally available transcript/export formats.

## Graph commands and all options

`agent-mem graph` can build notes directly, and `agent-mem graph build` is the explicit equivalent. Both accept:

- `--enrich`: optional provider-generated concepts/relationships.
- `--exclude-file-pattern TEXT`: repeatable exclusion glob.
- `--compact`: shorter notes for larger projects.
- `--help`.

The deterministic graph notes cover extracted code structures and call relationships; Python support is built in, with TypeScript/JavaScript available through the `multilang` extra. Output goes under `agent-mem-output/`. Generated concept enrichment is an inference, not measured ground truth.

`agent-mem graph benchmark` compares extraction with fixture ground truth. It accepts `--fixtures-dir PATH` (default `tests/fixtures`) and `--help`. Supply a directory with the expected fixture files and `ground_truth.json`; a package install does not guarantee that your current working directory has those repository fixtures. Benchmark scores describe those fixtures, not accuracy on arbitrary projects or improved agent memory.

## Engineering commands and all options

All ten engineering commands require `--session TEXT`. They also accept `--root PATH` (default `.`), optional `--storage PATH`, and `--help`. Keep the same session handle, repository, worktree and branch when continuing private records. The `--storage` path selects the memory-store location; it does not merge unrelated projects or grant sharing.

| Command | Purpose | Additional arguments/options |
| --- | --- | --- |
| `engineering record` | Save a decision, constraint, blocker or session summary from JSON on standard input | Common options only. Required JSON fields: `kind`, `text`, `source`; optional `evidence_files`, `scope`, `status`, `agent_id`, `metadata`, `record_id`, `supersedes`. |
| `engineering check` | Check evidence files and optional change-impact context | Repeatable `--changed TEXT`. A changed/missing file prompts review; it is not proof that the remembered decision is false. |
| `engineering list` | List private session records and explicitly shared records | Common options only. |
| `engineering checkpoint` | Refresh/recover a captured checkpoint | Common options only. A checkpoint does not prove every IDE event was captured. |
| `engineering export DESTINATION` | Export readable Markdown, including to a selected vault | Required destination path. |
| `engineering context GOAL` | Retrieve whole records and freshness within a context budget | Required goal; repeatable `--changed TEXT`; `--token-budget INTEGER` (default 2048); `--legacy` / `--no-legacy` (default: include legacy context). If required context will not fit, reports an insufficient budget and exits with code 2. |
| `engineering review` | Save a finding, dismissal, fix, scoped verification or failed approach from JSON on standard input | Common options only. Required JSON fields: `kind`, `text`, `source`. Optional evidence and relationship/result fields are shown below. |
| `engineering reviews` | Show review outcomes, open findings and failed approaches | `--goal TEXT` filters task relevance. |
| `engineering share RECORD_ID` | Explicitly promote a private record to shared repository memory | Required record ID. This changes sharing; it is not needed to resume the same private session. |
| `engineering prepare-next` | Print a durable scoped handoff for a fresh chat/MCP connection | `--goal TEXT` (default `Continue this project`). |

### JSON inputs

For `engineering record`, `kind` is one of `decision`, `constraint`, `blocker`, `session_summary`. Private session scope is the default. Its CLI default status is `observed`; the MCP `record_decision` tool separately defaults to `proposed`. Do not confuse those defaults or label an unaccepted proposal as an accepted decision.

```json
{
  "kind": "decision",
  "text": "Use SQLite for the single-user prototype because it must run without a database service.",
  "source": "User-confirmed architecture decision in docs/architecture.md",
  "evidence_files": ["docs/architecture.md"],
  "scope": "session",
  "status": "accepted",
  "metadata": {"topic": "prototype-storage"}
}
```

Pass the JSON through standard input, for example:

```sh
agent-mem engineering record --session my-session < decision.json
agent-mem engineering context "Resume storage implementation" --session my-session --changed docs/architecture.md --token-budget 4096
agent-mem engineering check --session my-session --changed docs/architecture.md
agent-mem engineering prepare-next --session my-session --goal "Continue storage implementation"
```

Evidence files must exist within the selected repository. Generic records cannot claim `verified` status; use scoped review verification records for actual test evidence.

`engineering review` accepts `kind`, `text`, `source`, and optional `evidence_files`, `related_id`, `reason`, `conditions`, `result`, `command`, `status`, `scope`, `external_id`, `reopens`. Recording a test command/result stores the caller's reported evidence; it does not run that command or independently validate the claim.

## Available MCP tools

The 0.8.0 server provides: `query_memory`, `summarize_to_obsidian`, `list_recent_sessions`, `session_status`, `get_task_context`, `record_decision`, `check_decisions`, `record_review_outcome`, `get_review_memory`, `share_memory_record`, and `get_session_handoff`.

Use the schemas actually exposed by the connected server. `summarize_to_obsidian` also works in local fallback mode. Private MCP reconnects need the durable session handle; a project-name label alone does not select another repository.

## What is and is not covered by the companion skill

The included skill actively guides recall, sourced decisions, evidence freshness checks and handoffs. Other commands above are available application features for clients to choose as needed. It does not automatically turn on a watcher, install hooks, import raw chat archives, run provider enrichment or share private records merely because the skill was loaded.

The setup helpers in 0.8.0 require review against the actual client's native settings; previous source review found configuration-schema/routing concerns. Their presence in `--help` is evidence that a command exists, not proof that every advertised client integration is correct. Current client behavior must be tested before claiming support.

## Exact captured help for every command

The following appendix preserves the published release's full argument, flag and default descriptions. It is generated from the 33 successful `--help` invocations, not copied from a planned future release.

### agent-mem

```text
Usage: agent-mem [OPTIONS] [COMMAND] [ARGS]...                                                                         
                                                                                                                        
 CLI-first persistent memory for coding sessions.                                                                       
                                                                                                                        
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --install-completion          Install completion for the current shell.                                              │
│ --show-completion             Show completion for the current shell, to copy it or customize the installation.       │
│ --help                        Show this message and exit.                                                            │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ configure-groq      Save Groq watch configuration for one-paste handoff generation.                                  │
│ configure-cerebras  Select Cerebras while preserving existing Groq configuration.                                    │
│ init                One-time setup - Obsidian is optional, local memory.md fallback is supported.                    │
│ setup               Set up instruction files + MCP configs for the current project.                                  │
│ setup-cursor        Install additive native Cursor lifecycle hooks in the current project.                           │
│ cursor-hook         Read a native Cursor lifecycle event from stdin and emit hook JSON.                              │
│ setup-vscode        Write .vscode/mcp.json using the currently active Python interpreter.                            │
│ print-mcp-json      Print a ready-to-paste MCP JSON block without writing any files.                                 │
│ migrate             Extract IDE chat history into agent-mem summaries, handoff prompts, and backups.                 │
│ summarize           Save a structured session summary to Obsidian or local fallback storage.                         │
│ checkpoint          Write the compact live handoff file used for the next fresh chat.                                │
│ prepare-next        Print the compact starter block for a fresh follow-up chat.                                      │
│ recall              Recall the most relevant saved memory for a task or question.                                    │
│ test-watch          Generate a watch handoff immediately without waiting for file events.                            │
│ watch               Watch the repo and generate one-paste handoff prompts for your IDE chat.                         │
│ serve               Start the optional MCP server (stdio transport).                                                 │
│ status              Show the configured vault and stored session count.                                              │
│ tui                 Open the interactive terminal UI dashboard.                                                      │
│ graph               Build Obsidian-friendly project knowledge notes.                                                 │
│ engineering         Evidence-backed, session-scoped engineering memory.                                              │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### agent-mem configure-groq

```text
Usage: agent-mem configure-groq [OPTIONS]                                                                              
                                                                                                                        
 Save Groq watch configuration for one-paste handoff generation.                                                        
                                                                                                                        
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --api-key        TEXT  Groq API key. If omitted, prompt securely.                                                    │
│ --model          TEXT  Groq model to use for watch handoff generation.                                               │
│ --help                 Show this message and exit.                                                                   │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### agent-mem configure-cerebras

```text
Usage: agent-mem configure-cerebras [OPTIONS]                                                                          
                                                                                                                        
 Select Cerebras while preserving existing Groq configuration.                                                          
                                                                                                                        
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --model          TEXT  Cerebras model ID. [default: qwen-3.8-27b]                                                    │
│ --use-env              Use CEREBRAS_API_KEY from the environment without saving it.                                  │
│ --help                 Show this message and exit.                                                                   │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### agent-mem init

```text
Usage: agent-mem init [OPTIONS]                                                                                        
                                                                                                                        
 One-time setup - Obsidian is optional, local memory.md fallback is supported.                                          
                                                                                                                        
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                          │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### agent-mem setup

```text
Usage: agent-mem setup [OPTIONS]                                                                                       
                                                                                                                        
 Set up instruction files + MCP configs for the current project.                                                        
                                                                                                                        
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                          │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### agent-mem setup-cursor

```text
Usage: agent-mem setup-cursor [OPTIONS]                                                                                
                                                                                                                        
 Install additive native Cursor lifecycle hooks in the current project.                                                 
                                                                                                                        
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                          │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### agent-mem cursor-hook

```text
Usage: agent-mem cursor-hook [OPTIONS] EVENT                                                                           
                                                                                                                        
 Read a native Cursor lifecycle event from stdin and emit hook JSON.                                                    
                                                                                                                        
╭─ Arguments ──────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *    event      TEXT  [required]                                                                                     │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                          │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### agent-mem setup-vscode

```text
Usage: agent-mem setup-vscode [OPTIONS]                                                                                
                                                                                                                        
 Write .vscode/mcp.json using the currently active Python interpreter.                                                  
                                                                                                                        
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --python        TEXT  Explicit Python executable path for MCP command                                                │
│ --help                Show this message and exit.                                                                    │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### agent-mem print-mcp-json

```text
Usage: agent-mem print-mcp-json [OPTIONS]                                                                              
                                                                                                                        
 Print a ready-to-paste MCP JSON block without writing any files.                                                       
                                                                                                                        
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --python        TEXT  Explicit Python executable path for MCP command                                                │
│ --help                Show this message and exit.                                                                    │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### agent-mem migrate

```text
Usage: agent-mem migrate [OPTIONS] [TARGETS]...                                                                        
                                                                                                                        
 Extract IDE chat history into agent-mem summaries, handoff prompts, and backups.                                       
                                                                                                                        
╭─ Arguments ──────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│   targets      [TARGETS]...  Sources followed optionally by a project path. Example: agent-mem migrate cursor claude │
│                              .                                                                                       │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --full                                             Extract + save summary to memory + generate handoff + write       │
│                                                    markdown backup.                                                  │
│ --extract-only                                     Extract chats and write markdown backup only (no memory write or  │
│                                                    handoff save).                                                    │
│ --dry-run                                          Run safely without writing memory or backup files.                │
│ --project-name        TEXT                         Override inferred project name for memory summary writes.         │
│ --max-sessions        INTEGER RANGE [1<=x<=100]    Maximum sessions to keep after extraction per source.             │
│                                                    [default: 20]                                                     │
│ --max-messages        INTEGER RANGE [20<=x<=5000]  Maximum messages retained per extracted session. [default: 400]   │
│ --help                                             Show this message and exit.                                       │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### agent-mem summarize

```text
Usage: agent-mem summarize [OPTIONS]                                                                                   
                                                                                                                        
 Save a structured session summary to Obsidian or local fallback storage.                                               
                                                                                                                        
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --summary             TEXT  Inline summary text to save.                                                             │
│ --summary-file        TEXT  Path to a markdown/text file containing the summary.                                     │
│ --stdin                     Read summary text from stdin.                                                            │
│ --project-name        TEXT  Override the inferred project name.                                                      │
│ --help                      Show this message and exit.                                                              │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### agent-mem checkpoint

```text
Usage: agent-mem checkpoint [OPTIONS]                                                                                  
                                                                                                                        
 Write the compact live handoff file used for the next fresh chat.                                                      
                                                                                                                        
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --summary                              TEXT  Inline checkpoint summary text.                                         │
│ --summary-file                         TEXT  Path to a markdown/text file containing the checkpoint summary.         │
│ --stdin                                      Read checkpoint summary text from stdin.                                │
│ --project-name                         TEXT  Override the inferred project name.                                     │
│ --save-session    --no-save-session          Also persist the checkpoint into long-term session memory.              │
│                                              [default: no-save-session]                                              │
│ --help                                       Show this message and exit.                                             │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### agent-mem prepare-next

```text
Usage: agent-mem prepare-next [OPTIONS]                                                                                
                                                                                                                        
 Print the compact starter block for a fresh follow-up chat.                                                            
                                                                                                                        
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --project-name        TEXT  Override the inferred project name.                                                      │
│ --help                      Show this message and exit.                                                              │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### agent-mem recall

```text
Usage: agent-mem recall [OPTIONS] QUERY                                                                                
                                                                                                                        
 Recall the most relevant saved memory for a task or question.                                                          
                                                                                                                        
╭─ Arguments ──────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *    query      TEXT  Short query describing the context you want recalled. [required]                               │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --project-name        TEXT                      Override the inferred project name.                                  │
│ --count               INTEGER RANGE [1<=x<=20]  Number of recent memory sources to inspect. [default: 5]             │
│ --help                                          Show this message and exit.                                          │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### agent-mem test-watch

```text
Usage: agent-mem test-watch [OPTIONS]                                                                                  
                                                                                                                        
 Generate a watch handoff immediately without waiting for file events.                                                  
                                                                                                                        
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --dry-run                   Generate a local canned handoff instead of calling the selected provider.                │
│ --project-name        TEXT  Override the inferred project name.                                                      │
│ --file                TEXT  File path to include in the test handoff. Repeatable.                                    │
│ --help                      Show this message and exit.                                                              │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### agent-mem watch

```text
Usage: agent-mem watch [OPTIONS]                                                                                       
                                                                                                                        
 Watch the repo and generate one-paste handoff prompts for your IDE chat.                                               
                                                                                                                        
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --quiet-seconds         INTEGER RANGE [x>=5]  Required quiet time after file activity before generating a handoff.   │
│                                               [default: 180]                                                         │
│ --min-changes           INTEGER RANGE [x>=1]  Minimum number of changed files before a handoff triggers.             │
│                                               [default: 5]                                                           │
│ --min-diff-lines        INTEGER RANGE [x>=1]  Minimum git diff line count before a handoff triggers. [default: 400]  │
│ --once                                        Exit after the first automatic checkpoint is saved.                    │
│ --dry-run                                     Skip the provider call and generate a canned handoff prompt for        │
│                                               testing.                                                               │
│ --project-name          TEXT                  Override the inferred project name.                                    │
│ --help                                        Show this message and exit.                                            │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### agent-mem serve

```text
Usage: agent-mem serve [OPTIONS]                                                                                       
                                                                                                                        
 Start the optional MCP server (stdio transport).                                                                       
                                                                                                                        
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --force-stdio          Run even in an interactive terminal. Intended only for debugging MCP startup.                 │
│ --help                 Show this message and exit.                                                                   │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### agent-mem status

```text
Usage: agent-mem status [OPTIONS]                                                                                      
                                                                                                                        
 Show the configured vault and stored session count.                                                                    
                                                                                                                        
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                          │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### agent-mem tui

```text
Usage: agent-mem tui [OPTIONS]                                                                                         
                                                                                                                        
 Open the interactive terminal UI dashboard.                                                                            
                                                                                                                        
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                          │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### agent-mem graph

```text
Usage: agent-mem graph [OPTIONS] [COMMAND] [ARGS]...                                                                   
                                                                                                                        
 Build Obsidian-friendly project knowledge notes.                                                                       
                                                                                                                        
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --enrich                            Enable optional LLM concept/relationship enrichment.                             │
│ --exclude-file-pattern        TEXT  Glob pattern for Python files to exclude from graph extraction. Repeat the       │
│                                     option for multiple patterns.                                                    │
│ --compact                           Generate compact notes for large projects with truncated function and concept    │
│                                     lists.                                                                           │
│ --help                              Show this message and exit.                                                      │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ build      Generate the agent-mem-output knowledge notes folder.                                                     │
│ benchmark  Measure detection accuracy against known fixture files.                                                   │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### agent-mem graph build

```text
Usage: agent-mem graph build [OPTIONS]                                                                                 
                                                                                                                        
 Generate the agent-mem-output knowledge notes folder.                                                                  
                                                                                                                        
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --enrich                            Enable optional LLM concept/relationship enrichment.                             │
│ --exclude-file-pattern        TEXT  Glob pattern for Python files to exclude from graph extraction. Repeat the       │
│                                     option for multiple patterns.                                                    │
│ --compact                           Generate compact notes for large projects with truncated function and concept    │
│                                     lists.                                                                           │
│ --help                              Show this message and exit.                                                      │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### agent-mem graph benchmark

```text
Usage: agent-mem graph benchmark [OPTIONS]                                                                             
                                                                                                                        
 Measure detection accuracy against known fixture files.                                                                
                                                                                                                        
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --fixtures-dir        PATH  Directory containing fixture .py files and ground_truth.json [default: tests/fixtures]   │
│ --help                      Show this message and exit.                                                              │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### agent-mem engineering

```text
Usage: agent-mem engineering [OPTIONS] COMMAND [ARGS]...                                                               
                                                                                                                        
 Evidence-backed, session-scoped engineering memory.                                                                    
                                                                                                                        
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                                                          │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ record        Store a typed record from stdin. Capture hashes for its evidence_files.                                │
│ check         Evaluate decisions against current files and optional change-impact graph.                             │
│ list          Inspect this session and explicitly shared records.                                                    │
│ checkpoint    Recover or refresh a captured checkpoint from the event journal.                                       │
│ export        Export records as readable Markdown, including into an Obsidian vault.                                 │
│ context       Retrieve whole records, evidence freshness and bounded change-impact context.                          │
│ review        Record a finding, dismissal, fix, scoped verification or failed approach from JSON.                    │
│ reviews       Inspect outcomes, unresolved findings and failed approaches with original conditions.                  │
│ share         Explicitly promote a private record into shared repository memory.                                     │
│ prepare-next  Print a durable scoped handoff for a fresh chat or MCP reconnection.                                   │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### agent-mem engineering record

```text
Usage: agent-mem engineering record [OPTIONS]                                                                          
                                                                                                                        
 Store a typed record from stdin. Capture hashes for its evidence_files.                                                
                                                                                                                        
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *  --session        TEXT  [required]                                                                                 │
│    --root           PATH  [default: .]                                                                               │
│    --storage        PATH                                                                                             │
│    --help                 Show this message and exit.                                                                │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### agent-mem engineering check

```text
Usage: agent-mem engineering check [OPTIONS]                                                                           
                                                                                                                        
 Evaluate decisions against current files and optional change-impact graph.                                             
                                                                                                                        
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *  --session        TEXT  [required]                                                                                 │
│    --root           PATH  [default: .]                                                                               │
│    --storage        PATH                                                                                             │
│    --changed        TEXT                                                                                             │
│    --help                 Show this message and exit.                                                                │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### agent-mem engineering list

```text
Usage: agent-mem engineering list [OPTIONS]                                                                            
                                                                                                                        
 Inspect this session and explicitly shared records.                                                                    
                                                                                                                        
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *  --session        TEXT  [required]                                                                                 │
│    --root           PATH  [default: .]                                                                               │
│    --storage        PATH                                                                                             │
│    --help                 Show this message and exit.                                                                │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### agent-mem engineering checkpoint

```text
Usage: agent-mem engineering checkpoint [OPTIONS]                                                                      
                                                                                                                        
 Recover or refresh a captured checkpoint from the event journal.                                                       
                                                                                                                        
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *  --session        TEXT  [required]                                                                                 │
│    --root           PATH  [default: .]                                                                               │
│    --storage        PATH                                                                                             │
│    --help                 Show this message and exit.                                                                │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### agent-mem engineering export

```text
Usage: agent-mem engineering export [OPTIONS] DESTINATION                                                              
                                                                                                                        
 Export records as readable Markdown, including into an Obsidian vault.                                                 
                                                                                                                        
╭─ Arguments ──────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *    destination      PATH  [required]                                                                               │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *  --session        TEXT  [required]                                                                                 │
│    --root           PATH  [default: .]                                                                               │
│    --storage        PATH                                                                                             │
│    --help                 Show this message and exit.                                                                │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### agent-mem engineering context

```text
Usage: agent-mem engineering context [OPTIONS] GOAL                                                                    
                                                                                                                        
 Retrieve whole records, evidence freshness and bounded change-impact context.                                          
                                                                                                                        
╭─ Arguments ──────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *    goal      TEXT  [required]                                                                                      │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *  --session                        TEXT     [required]                                                              │
│    --root                           PATH     [default: .]                                                            │
│    --storage                        PATH                                                                             │
│    --changed                        TEXT                                                                             │
│    --token-budget                   INTEGER  [default: 2048]                                                         │
│    --legacy          --no-legacy             [default: legacy]                                                       │
│    --help                                    Show this message and exit.                                             │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### agent-mem engineering review

```text
Usage: agent-mem engineering review [OPTIONS]                                                                          
                                                                                                                        
 Record a finding, dismissal, fix, scoped verification or failed approach from JSON.                                    
                                                                                                                        
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *  --session        TEXT  [required]                                                                                 │
│    --root           PATH  [default: .]                                                                               │
│    --storage        PATH                                                                                             │
│    --help                 Show this message and exit.                                                                │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### agent-mem engineering reviews

```text
Usage: agent-mem engineering reviews [OPTIONS]                                                                         
                                                                                                                        
 Inspect outcomes, unresolved findings and failed approaches with original conditions.                                  
                                                                                                                        
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│    --goal           TEXT                                                                                             │
│ *  --session        TEXT  [required]                                                                                 │
│    --root           PATH  [default: .]                                                                               │
│    --storage        PATH                                                                                             │
│    --help                 Show this message and exit.                                                                │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### agent-mem engineering share

```text
Usage: agent-mem engineering share [OPTIONS] RECORD_ID                                                                 
                                                                                                                        
 Explicitly promote a private record into shared repository memory.                                                     
                                                                                                                        
╭─ Arguments ──────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *    record_id      TEXT  [required]                                                                                 │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│ *  --session        TEXT  [required]                                                                                 │
│    --root           PATH  [default: .]                                                                               │
│    --storage        PATH                                                                                             │
│    --help                 Show this message and exit.                                                                │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

### agent-mem engineering prepare-next

```text
Usage: agent-mem engineering prepare-next [OPTIONS]                                                                    
                                                                                                                        
 Print a durable scoped handoff for a fresh chat or MCP reconnection.                                                   
                                                                                                                        
╭─ Options ────────────────────────────────────────────────────────────────────────────────────────────────────────────╮
│    --goal           TEXT  [default: Continue this project]                                                           │
│ *  --session        TEXT  [required]                                                                                 │
│    --root           PATH  [default: .]                                                                               │
│    --storage        PATH                                                                                             │
│    --help                 Show this message and exit.                                                                │
╰──────────────────────────────────────────────────────────────────────────────────────────────────────────────────────╯
```

## Exact MCP tool parameters (0.8.0)

These are the registered Python tool signatures in the installed 0.8.0 server. Empty `session_id` defaults to a connection session. Reuse an explicit returned handle for private reconnects. Pass only fields supported by the currently connected tool schema.

### `query_memory`

Load saved memory before work. Explicit session IDs enable durable scoped continuity.

```python
query_memory(project_name: 'str', query: 'str', session_id: 'str' = '') -> 'str'
```

### `summarize_to_obsidian`

Save a durable summary. MCP/explicit sessions are isolated; direct legacy calls keep Markdown behavior.

```python
summarize_to_obsidian(project_name: 'str', summary: 'str', session_id: 'str' = '') -> 'str'
```

### `list_recent_sessions`

List legacy notes and summaries visible to this caller; never other private sessions.

```python
list_recent_sessions(project_name: 'str', count: 'int' = 3, session_id: 'str' = '') -> 'str'
```

### `session_status`

Check the memory-loaded state of this session only.

```python
session_status(session_id: 'str' = '') -> 'str'
```

### `get_task_context`

Get whole-record context with citations, constraints, freshness and explicit budget overflow.

```python
get_task_context(goal: 'str', changed_files: 'list[str]', token_budget: 'int' = 2048, session_id: 'str' = '') -> 'dict'
```

### `record_decision`

Save a sourced decision/constraint/blocker. Sharing and supersession are explicit.

```python
record_decision(text: 'str', source: 'str', evidence_files: 'list[str]', kind: 'str' = 'decision', scope: 'str' = 'session', status: 'str' = 'proposed', topic: 'str' = '', supersedes: 'str' = '', session_id: 'str' = '') -> 'dict'
```

### `check_decisions`

Flag changed or missing evidence without rewriting decisions.

```python
check_decisions(changed_files: 'list[str]', session_id: 'str' = '') -> 'dict'
```

### `record_review_outcome`

Record review/failure evidence. Commands are stored data; verification is caller-reported.

```python
record_review_outcome(kind: 'str', text: 'str', source: 'str', evidence_files: 'list[str]', related_id: 'str' = '', reason: 'str' = '', conditions: 'str' = '', result: 'str' = '', command: 'str' = '', status: 'str' = 'observed', scope: 'str' = 'session', external_id: 'str' = '', reopens: 'bool' = False, session_id: 'str' = '') -> 'dict'
```

### `get_review_memory`

Retrieve findings, dismissals, fixes and failed approaches without promoting them to proof.

```python
get_review_memory(goal: 'str' = '', session_id: 'str' = '') -> 'dict'
```

### `share_memory_record`

Explicitly promote a visible private record; no automatic promotion of agent claims.

```python
share_memory_record(record_id: 'str', session_id: 'str' = '') -> 'dict'
```

### `get_session_handoff`

Return the durable session handle needed to resume private memory in a new connection.

```python
get_session_handoff(goal: 'str' = 'Continue this project', session_id: 'str' = '') -> 'dict'
```

