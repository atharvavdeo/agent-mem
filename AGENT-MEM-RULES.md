# Agent-Mem Rules

This repository uses `agent-mem` for persistent coding memory.

Project name: agent-mem

Read these rules at the start of every session. Follow them on every response. Do not silently ignore them.

## Non-Negotiable Behavior

1. Load saved memory before planning, coding, or answering questions about prior work.
2. Prefer saved memory over stale chat history.
3. Never invent historical decisions.
4. If the user pastes a watch-generated handoff prompt, pause normal work and execute the handoff immediately.

## Memory Source Of Truth

Use this priority order:

1. If Obsidian mode is configured, use the latest notes under `Memory/Agent-Mem/`.
2. Otherwise, use `.agent-memory/active.md` first and `.agent-memory/memory.md` second.
3. Old chat history is lower priority than saved memory.
4. Code on disk overrides memory if they conflict. If they conflict, say so explicitly.

## Required Start-Of-Session Workflow

At the beginning of a new session:

1. Resolve the repository root.
2. Resolve the project name from the root folder name unless the user overrides it.
3. Load memory before proposing work.
4. State the current goal only after reading memory.

If MCP tools are available:

- call `query_memory(project_name, current_goal)`

If MCP tools are unavailable:

- read the latest memory files directly
- continue only after you have incorporated them

## Required Summarization Triggers

You must summarize when:

- context is getting long or repetitive
- a milestone is complete
- multiple files were changed for one logical task
- architecture, API, workflow, or design decisions changed
- the user is about to stop
- the user pastes an `agent-mem watch` handoff prompt

## Summary Format

Every summary must use these exact sections in this exact order:

- Goal
- Outcome
- Key decisions
- Files changed
- Open tasks or blockers
- Next prioritized steps

## Summary Quality Rules

Before saving memory, verify that:

- the goal matches the actual task
- the outcome reflects what was really completed
- key decisions are explicit, not implied guesses
- file paths are concrete
- blockers are still current
- next steps are actionable
- no secrets or credentials appear anywhere

## Obsidian-Specific Requirements

When Obsidian mode is enabled:

- write summaries as dense, durable engineering notes
- preserve frontmatter, headings, and wiki-links
- make decisions and file references explicit so the notes stay useful later
- prefer high-signal summaries over long narrative chat recaps

## Forbidden Behavior

Do not:

- claim a previous decision without memory or code evidence
- skip memory loading at session start
- treat a watch prompt like a normal chat message
- write apology text into memory
- dump vague prose when a structured summary is required

## Good Behavior Example

- Read memory
- State current goal
- Do the work
- Save a structured summary
- Produce a short fresh-chat handoff when context is bloated

## Bad Behavior Example

- Ignore memory
- Reconstruct history from guesswork
- Keep working in a bloated chat
- Save an unstructured paragraph instead of a proper summary
