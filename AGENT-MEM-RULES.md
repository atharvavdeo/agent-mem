# Agent-Mem Rules

You have persistent project memory via agent-mem.

## Objective

- Keep durable project context across chats.
- Prefer stored memory over long chat history.

## Memory Source Of Truth

- Primary (default): .agent-memory/memory.md
- Optional: [vault_path]/Memory/Agent-Mem/ when Obsidian mode is configured

## Mandatory Start-Of-Session Workflow

1. Resolve project root and project name (root folder name).
2. Load latest memory before planning or coding.
3. If memory exists, treat it as authoritative project context.
4. If memory does not exist, continue normally and create or update it after meaningful progress.

## Mandatory Summarization Triggers

- Context pressure (roughly 15-20 turns)
- Major milestone completed
- Before ending session when important decisions were made

## Required Summary Structure

Use concise Markdown with these sections in order:

- Goal
- Outcome
- Key decisions (with rationale)
- Files changed (path + reason)
- Open tasks or blockers
- Next prioritized steps

## Memory Write Rules

- Append new information; do not delete prior history unless it is clearly obsolete and corrected.
- Be factual and specific; never invent decisions or changes.
- Never write secrets (tokens, API keys, passwords, private credentials).

## MCP Compatibility (Optional)

- If MCP tools are available: use query_memory, summarize_to_obsidian, list_recent_sessions.
- If MCP tools are unavailable: read and update .agent-memory/memory.md directly with the same structure.

## Project Name Rule

- Always use the repository root folder name as project_name.

Project name for this workspace: agent-mem
