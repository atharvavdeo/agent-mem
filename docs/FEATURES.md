# Features in 0.8.0

Version 0.8.0 is a source update; it has not been published as a package or GitHub release.

| Feature | Behavior | Entry point |
|---|---|---|
| Native Cursor lifecycle | Capture prompt, response and edit observations; checkpoint on stop, session end and compaction | `agent-mem setup-cursor` |
| Sourced decisions | Store decisions, constraints and blockers with source and file-hash evidence | `agent-mem engineering record` |
| Evidence freshness | Flag changed/missing evidence and bounded optional graph impact; changes prompt review rather than proving contradiction | `agent-mem engineering check` |
| Task context | Retrieve whole cited records, mandatory constraints/blockers, stale flags and explicit overflow | `agent-mem engineering context` |
| Scoped continuity | Isolate repository/worktree/branch/session records and resume using durable handles | `agent-mem engineering prepare-next`; MCP `query_memory` |
| Explicit sharing | Promote selected private records for other linked worktrees | `agent-mem engineering share` |
| Review memory | Preserve findings, reasoned dismissals, executed fixes and caller-reported verification; later outcomes supersede earlier results | `agent-mem engineering review`; `reviews` |
| Failed approaches | Retrieve previous failures with their original conditions | `agent-mem engineering reviews` |
| Local storage | Route CLI, hooks and MCP to the same unsynchronized local database | `AGENT_MEM_STORAGE_DIR`; CLI `--storage` |
| Graph integration | Read code-review-graph schemas 9–13 without altering its database; disclose freshness and partial coverage | Engineering `check`/`context`, optional `intelligence` extra |
| Provider support | Groq default with native SDK; optional Cerebras adapter, environment credentials and actionable errors | `configure-groq`; `configure-cerebras --use-env` |
| Existing workflows | File/Git/idle watcher, IDE-history migration, graph extraction, benchmark, TUI and Markdown/Obsidian summaries | `watch`, `migrate`, `graph`, `tui`, `summarize` |

## Verification and limits

Local installed-package CLI, MCP reconnect, native hooks, graph operations and
existing extraction benchmark passed on Python 3.10 and 3.13. The previous runtime
candidate passed six CI jobs on Linux, macOS and Windows. Actual Groq handoff,
graph enrichment and migration generation passed with openai/gpt-oss-120b.
Real Cursor desktop 3.22.12 and CLI 2026.09.28-64d2043 collectively emitted all seven
configured events with durable checkpoints; not each event independently on both.
Cerebras authentication/model discovery worked, but generation returned HTTP402
and remains optional and deferred. No automatic provider/model substitution occurs.

Supported engineering storage is an unsynchronized local filesystem on one host.
Mounted-network, multi-host and live cloud-synchronized SQLite WAL are excluded.
Native Windows Cursor hook installation is rejected before mutation. Regenerate
hooks when changing machines or Python installations. Cloud-agent portability,
Windows crash/concurrency durability, production load and model-level retrieval
quality are not qualified. Imported verification is caller-reported evidence, not
a command executor or proof of safety. No performance or token-savings claim is made.

See [engineering memory usage and architecture](ENGINEERING_MEMORY.md) and
[0.8.0 change notes](releases/v0.8.0.md).
