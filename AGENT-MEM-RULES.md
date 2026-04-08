# Agent-Mem Rules

You are operating inside a repository that uses `agent-mem` for persistent coding memory.

Project name: agent-mem

## Primary Goal

Preserve accurate project context across chats while keeping the live context window small.

You must prefer saved memory over stale chat history and you must keep memory current whenever meaningful decisions are made.

## Memory Priority Order

1. If Obsidian mode is configured, the primary memory store is the vault under `Memory/Agent-Mem/`.
2. Otherwise, the primary memory store is `.agent-memory/memory.md`.
3. Old chat history is lower priority than saved memory.
4. Never invent historical decisions that do not appear in memory or the codebase.

## Start-Of-Session Requirements

At the start of every new session:

1. Resolve the repository root.
2. Resolve `project_name` from the repository root folder name unless the user explicitly overrides it.
3. Load memory before planning, coding, or answering historical questions.
4. Treat saved memory as the authoritative summary of previous sessions.

If MCP tools are available:

- call `query_memory(project_name, current_goal)`

If MCP tools are unavailable:

- read the latest Obsidian note set or `.agent-memory/memory.md` directly
- summarize what you learned before continuing

## When To Summarize

You must summarize when any of these happen:

- context becomes long or repetitive
- a milestone or subtask completes
- architecture, API, or workflow decisions change
- multiple files were edited for one logical change
- the user is about to stop or switch topics

## Required Summary Quality

Every saved summary must be factual, concise, and implementation-oriented.

It must include these sections in this order:

- Goal
- Outcome
- Key decisions
- Files changed
- Open tasks or blockers
- Next prioritized steps

## Double-Check Rules Before Saving

Before writing memory:

- verify the summary matches the actual files changed
- verify decisions are explicit, not implied guesses
- verify open tasks are still open
- remove secrets, tokens, passwords, or raw credentials
- keep wording specific enough to be useful in a later session

## Obsidian Rules

When Obsidian mode is enabled:

- prefer saving through `agent-mem summarize` or `summarize_to_obsidian`
- preserve wiki-links and note structure
- do not manually break frontmatter or note headings
- keep references usable for Graph view and backlinks

## Fallback Rules

When only `.agent-memory/memory.md` exists:

- append structured summaries
- do not overwrite prior useful context
- correct prior context only when it is clearly outdated or wrong

## Tool Preference

Preferred workflow:

1. `query_memory`
2. do work
3. `summarize_to_obsidian` or `agent-mem summarize`
4. start fresh session if context is bloated

## Response Behavior

- prefer memory-backed answers for questions about prior work
- if memory is missing, say that clearly
- suggest summarization proactively when context grows
- never claim a past decision unless you saw it in memory or code
