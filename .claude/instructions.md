# Agent Memory Instructions

Use `AGENT-MEM-RULES.md` as the canonical source of truth.

Project name: agent-mem

Mandatory behavior at session start:

- Resolve the repository root.
- Resolve the project name from the repository root and keep it consistent.
- Load memory before planning, coding, or answering historical questions.
- Prefer saved memory over old chat history.

If MCP tools are available:

- call `query_memory` first
- call `summarize_to_obsidian` when needed

If MCP tools are unavailable:

- read the latest memory artifact directly
- use `agent-mem summarize` conventions when preparing a summary

Mandatory summarization triggers:

- long or repetitive context
- completed milestone
- important design or implementation decision
- multiple-file change
- session handoff or stop point

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
