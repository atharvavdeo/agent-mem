# Agent Memory Instructions

Use AGENT-MEM-RULES.md as the source of truth for memory behavior.

Project name: agent-mem

Mandatory behavior:

- Call query_memory at the start of every session.
- Call summarize_to_obsidian when context becomes long.
- Prefer memory output over old chat history.
- Never hallucinate historical decisions.
