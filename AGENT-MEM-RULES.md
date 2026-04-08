You have persistent project memory via agent-mem.

Primary memory source:
- Local-first file: .agent-memory/memory.md
- Optional Obsidian target when configured: <vault>/Memory/Agent-Mem/

Start-of-session rule (mandatory):
- Before planning or coding, read the latest project memory.
- If .agent-memory/memory.md exists, treat it as the source of truth.
- If no memory exists yet, proceed normally and create memory after meaningful progress.

Context management rule:
- Do not depend on long chat history for old decisions.
- Prefer memory content (and recent summaries) over earlier conversation context.

When context grows long (~15-20 turns):
- Announce that you are summarizing the session for memory.
- Save a concise Markdown summary containing:
  - Goal and outcome
  - Key decisions and why
  - Files changed and purpose
  - Open tasks/blockers
  - Next prioritized steps

Summary quality rules:
- Keep summaries short, factual, and actionable.
- Never invent prior decisions; only record what happened.
- Do not store secrets, tokens, passwords, or private keys in memory files.

MCP compatibility (optional):
- If agent-mem MCP tools are available, use query_memory / summarize_to_obsidian / list_recent_sessions.
- If MCP tools are unavailable, read and update .agent-memory/memory.md directly using the same structure.

Project naming:
- Use the repository root folder name as project_name for memory operations.

Project name for this workspace: agent-mem
