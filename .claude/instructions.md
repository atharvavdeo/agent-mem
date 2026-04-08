# Agent Memory Instructions

Use `AGENT-MEM-RULES.md` as the canonical source of truth. Read and follow it every session.

Project name: agent-mem

Mandatory behavior at session start:

- Resolve the repository root.
- Resolve the project name from the repository root and keep it consistent.
- Load memory before planning, coding, or answering historical questions.
- Prefer saved memory over old chat history.
- If the user pastes a watch-generated handoff prompt, execute that handoff before anything else.

If MCP tools are available:

- call `query_memory` first
- call `summarize_to_obsidian` when needed

If MCP tools are unavailable:

- read the latest memory artifact directly
- prefer `.agent-memory/active.md` over older memory when fallback mode is active
- still produce the structured summary in chat if direct save tools are unavailable

Mandatory summarization triggers:

- long or repetitive context
- completed milestone
- important design or implementation decision
- multiple-file change
- session handoff or stop point
- a watch-generated handoff prompt pasted by the user

Required summary contents:

- Goal
- Outcome
- Key decisions
- Files changed
- Open tasks or blockers
- Next prioritized steps

Safety rules:

- never hallucinate historical decisions
- never write secrets into memory
- if memory conflicts with the codebase, say so explicitly
- prefer verified state over guessed state
- in Obsidian mode, keep summaries dense, specific, and useful as future engineering notes
