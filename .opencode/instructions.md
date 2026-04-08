# Agent-Mem Instructions For Opencode

Use `AGENT-MEM-RULES.md` in the repository root as the canonical memory policy.

Platform target: opencode

Behavior requirements:

- Load memory at the start of each session.
- If the user pastes an `agent-mem watch` handoff prompt, execute it immediately.
- Prefer Obsidian-backed notes or `.agent-memory/active.md` and `.agent-memory/memory.md` over long chat history.
- Summarize after important changes, milestones, or context growth.
- Keep summaries structured and implementation-oriented.
- Never fabricate historical context.
- Never store secrets in memory artifacts.

Required summary sections:

- Goal
- Outcome
- Key decisions
- Files changed
- Open tasks or blockers
- Next prioritized steps

If direct MCP tools are available, use them.
If they are not, read and write the memory artifacts directly while preserving structure.
