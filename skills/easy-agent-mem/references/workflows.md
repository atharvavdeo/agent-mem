# Tool examples for easy-agent-mem 0.8.0

These are input examples, not captured execution results. Use actual project names, source paths, tool schemas and returned session handles.

## Remember an accepted decision

For a user who explicitly asks to remember the decision documented in `docs/architecture.md`:

```json
{
  "text": "Use SQLite for the prototype because the initial deployment is single-user and must run without a database service.",
  "source": "User-confirmed architecture decision in docs/architecture.md",
  "evidence_files": ["docs/architecture.md"],
  "kind": "decision",
  "scope": "session",
  "status": "accepted",
  "topic": "prototype-storage",
  "session_id": "HANDLE_FROM_QUERY_MEMORY"
}
```

Call `query_memory` first. `record_decision` returns the stored record; report its actual ID. Do not add invented test results to its text.

## Retrieve task context

```json
{
  "goal": "Resume the prototype storage implementation",
  "changed_files": ["docs/architecture.md"],
  "token_budget": 4096,
  "session_id": "HANDLE_FROM_QUERY_MEMORY"
}
```

Send this to `get_task_context`. Cite returned records and files. Explain `current`, `unanchored`, `superseded`, or `needs_review` labels as applicable. A current evidence hash means the cited file matches its captured contents. It does not mean tests passed.

## Review freshness

After an intentional edit to `docs/architecture.md`, call:

```json
{
  "changed_files": ["docs/architecture.md"],
  "session_id": "HANDLE_FROM_QUERY_MEMORY"
}
```

Send this to `check_decisions`. Inspect changed evidence before recommending a new decision. Keep supersession separate from the freshness signal.

## Continue in a fresh connection

Save the summary, then call `get_session_handoff` using the same handle. Preserve the returned `query_memory_arguments` in the handoff. In the fresh chat, call `query_memory` with those arguments in the same repository/worktree/branch. A new arbitrary handle will not restore another private session.
