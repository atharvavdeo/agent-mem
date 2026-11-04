# Requirements and setup

Requires Python 3.10+, easy-agent-mem 0.8.0 or later exposing the required tools, and an agent connected to the local agent-mem MCP server. Obsidian is optional. Agensi distributes this skill's instructions; it neither hosts nor installs the local memory server.

If setup is requested, use the user's normal Python environment or an isolated environment. The published dependency is:

```sh
python3 -m pip install 'easy-agent-mem[mcp]==0.8.0'
```

The executable is `agent-mem`. Launch the MCP process through the agent's native MCP settings using the actual installed executable path, arguments `serve`, `--force-stdio`, and the intended repository as the process working directory. Client configuration formats differ; use the current client's documented settings. Existing 0.8.0 setup helpers must not be assumed to generate correct native configuration for every client. Preserve existing settings and diagnose malformed JSON rather than replacing it.

`agent-mem status` reports configured storage. `agent-mem print-mcp-json` can help inspect a configuration example, but its format is not universal. Run interactive `agent-mem init` only when initialization is requested, because it can write project instructions and configuration. Review those changes with the user.

Verify that the connected server exposes `query_memory`, `record_decision`, `get_task_context`, `check_decisions`, `summarize_to_obsidian` and `get_session_handoff`. A missing advanced tool can mean an older installation. Report the version/tool mismatch and use only tools actually available. Do not manufacture MCP results or silently replace scoped memory with an unrelated Markdown file.

An explicit Obsidian vault configuration enables export into the user's chosen vault. Obtain the intended vault path from the user or approved local configuration; never select an arbitrary vault. Basic local save/recall does not require Groq, Cerebras, an embedding service, or their API keys. Optional LLM enrichment and other product features are outside this skill's default workflow.

## Access and storage

- The agent needs the connected local MCP server. Terminal access is needed for installation or diagnostics, not necessarily for every connected MCP call.
- The server reads relevant project evidence and writes local `.agent-memory/**` state, including SQLite and Markdown projections. Writes also occur in the selected Obsidian vault when configured.
- Restrict evidence reads to files relevant to the task. Do not inspect `.env`, credentials or private chat stores for a memory demo.
- Network access is needed to install dependencies and use the Agensi connector. The local core memory operations do not require a separate remote model service. The coding agent/model provider's normal data handling still applies; do not claim that the entire conversation never leaves the computer.

## Troubleshooting

- Wrong project recalled: check the server process working directory before further writes.
- Missing private records: reuse the durable handle in the same repository/worktree/branch. Do not automatically promote records to shared scope.
- Changed evidence: inspect the source file; the warning is a change signal, not a contradiction detector.
- No graph backend: ordinary saved-memory retrieval can still work. Report unavailable graph context.
- Reconnect after server changes and inspect the actual exposed tool schemas again.

Documentation: https://github.com/atharvavdeo/agent-mem
