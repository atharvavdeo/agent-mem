# Engineering memory implementation

These are release-candidate source changes (0.8.0rc1) on top of 0.7.2. The installed system package remains unchanged. Existing CLI memory, migration, watcher and graph interfaces remain available. No new custom test suite was written for implementation verification; operational runs use the actual CLI, MCP SDK, SQLite database and installed code-review-graph.

## Five approaches, in order

| Phase | Product behavior | Evidence from operational runs | Qualification boundary |
|---|---|---|---|
| 1. Cursor lifecycle | Additive/idempotent hook installer, observed response/prompt/edit capture, checkpoints at stop/end/compaction, bounded startup injection | Generated launcher installed twice preserving a third-party hook; response retry persisted once; aborted status retained; distinct same-turn edits retained | Cursor app/CLI unavailable on this host. Native launcher exercised directly; live IDE conversation not verified. Observational hooks cannot guarantee event delivery or block compaction. |
| 2. Decision freshness | Typed sourced records, SHA256 evidence, changed/missing-file warnings, explicit supersession, optional read-only impact graph | Evidence mutation flagged needs_review; unrelated mutation retained current; actual graph build read and dirty-file hash mismatch flagged stale | Unknown static-analysis coverage remains disclosed. File changes do not prove contradiction. Missing/renamed symbols remain unresolved review candidates. |
| 3. Task context | Whole-record selection, mandatory constraints/blockers, citations, stale flags, captured events, conflict warnings, tokenizer and overflow reporting | Actual context retrieval, graph fallback and zero-budget overflow inspected | Canonical JSON token count excludes MCP transport wrappers. No measured savings or model-level correctness claim. Semantic embedding backend deferred pending evidence of benefit. |
| 4. Isolation | Repository/worktree/branch/session namespaces, per-connection MCP identity, WAL transactions, atomic projections, explicit sharing, handoff handles | Linked-worktree private/shared separation; simultaneous writers compared to actual receipts; killed uncommitted writer rolled back; integrity_check returned ok; reconnection exercised | Network filesystem lock semantics and Windows execution not qualified. Legacy Markdown is intentionally shared input; use --no-legacy for strict modern retrieval. |
| 5. Review/failure memory | Findings, reasoned dismissals, proposed/executed fixes, caller-reported scoped verification, latest-result semantics, failed approaches with original conditions | Actual CLI review writes/reads and missing-evidence rejection; failed rerun superseded prior pass; original conditions retrieved | Imported test outcomes are caller-reported, never automatic proof of safety or execution. No live review service/webhook subscription configured. |

## Usage

Install the built package in your preferred environment, or use `PYTHONPATH=/absolute/path/to/agent-mem/src python3 -m agent_mem.cli` while developing. Base functionality requires no model API. Optional extras `context` and `intelligence` enable tiktoken and code-review-graph respectively. Without tiktoken, UTF-8 byte count is disclosed as a conservative upper bound, not an exact model token count.

```sh
agent-mem setup-cursor
agent-mem engineering record --session feature-a <<'JSON'
{"kind":"decision","text":"Keep project memory as sourced structured notes.","source":"design discussion","status":"accepted","evidence_files":["src/agent_mem/memory.py"],"metadata":{"topic":"memory-storage"}}
JSON
agent-mem engineering record --session feature-a <<'JSON'
{"kind":"constraint","text":"Preserve existing CLI interfaces.","source":"user requirement"}
JSON
agent-mem engineering check --session feature-a --changed src/agent_mem/memory.py
agent-mem engineering context "update memory retrieval" --session feature-a --changed src/agent_mem/memory.py --token-budget 2048
agent-mem engineering prepare-next --session feature-a
agent-mem engineering share RECORD_ID --session feature-a
agent-mem engineering export /absolute/path/to/vault/Memory/Agent-Mem/engineering.md --session feature-a
```

`record` and `review` consume a single JSON object on stdin. All engineering commands support `--root` and `--storage` for explicit repository/storage selection. Roots and evidence are canonicalized; out-of-repository evidence is rejected. `context` emits canonical JSON and exits 2 if mandatory material cannot fit; records are retained and overflow is explicit. `record` accepts decisions, constraints, blockers and session summaries. Use `review` for review outcomes so its validations cannot be skipped through the generic CLI.

```sh
agent-mem engineering review --session feature-a <<'JSON'
{"kind":"failed_approach","text":"Single global memory-loaded flag","source":"architecture review","reason":"One caller could mark another caller loaded","conditions":"Multiple simultaneous MCP callers"}
JSON
agent-mem engineering reviews --session feature-a --goal "global flag"
```

Dismissals require `related_id` of a visible finding and `reason`. Fixes require `status` proposed or executed. Verification records require a visible executed fix, `command`, `result` passed/failed/inconclusive, and `evidence_files`. Commands are stored as data and never executed. Reopened findings use `reopens: true` and the original finding ID. Duplicate imported events can carry `external_id`; changed dispositions require a new external event ID. A shared outcome cannot reference a private finding/fix.

## Storage and continuity

SQLite is authoritative; Markdown is an atomic readable projection. Default location is `.agent-memory/engineering/memory.sqlite3` in the primary checkout, shared by linked worktrees. Non-Git directories use their own `.agent-memory/engineering`. Paths and Git common-directory identity distinguish repositories; private records include branch/worktree/session, while explicit shared records are available across linked worktrees. Moving/cloning a repository changes identity; portable import/remapping is not automatic.

Default MCP calls use per-connection identities. `query_memory`, `summarize_to_obsidian`, and `get_session_handoff` expose a durable session handle. To reconnect in the same worktree/branch, pass the returned `session_id` to query_memory. This selects the resumed session for subsequent ordinary calls on that connection. CLI `engineering prepare-next --session ID` prints the equivalent handoff. Shared decisions can be created with `scope: shared` or explicitly promoted using `engineering share` / `share_memory_record`. Raw observations and private summaries are never automatically promoted.

MCP/explicit-session summaries export under paths derived from the full scope tuple. In Obsidian mode they export under `Memory/Agent-Mem/Engineering/<repository>/<scope>/`; legacy direct Python summarize calls keep the original memory.md behavior. Legacy Markdown writes now use process locks and atomic replacement; Obsidian note names include microseconds to prevent same-minute overwrites. Existing Markdown is read without destructive migration and labeled unanchored. Disable legacy input using CLI `--no-legacy` when strict modern isolation is desired.

Legacy active-context projections retain prose-only decision, blocker and next-step sections. Explicit `Files changed` entries take precedence over path inference, preserving absolute paths and spaces through saved context and handoffs.

## Native hook behavior

`setup-cursor` installs sessionStart, beforeSubmitPrompt, afterAgentResponse, afterFileEdit, stop, sessionEnd and preCompact in `.cursor/hooks.json`. It preserves unrelated hooks and unknown configuration keys, backs up the original config, refuses malformed input, and serializes installers. The generated launcher pins this installation's interpreter/package path; reinstall hooks after moving or changing the Python environment.

Session IDs come from session_id/conversation_id; there is no shared unknown-session fallback. Edit content is hashed for identity but not persisted; only paths/ranges and the fingerprint are stored. Capture completeness is always observational/unknown. preCompact checkpoints previously collected data, without claiming to modify compaction. Optional transcript_path is not read. Cloud agents may lack startup/end hooks.

Startup injection uses the counted canonical serialization plus its prefix. If required context exceeds the startup bound, Cursor receives an explicit overflow warning and instructions to load full context through MCP with a larger budget. It is not marked loaded. The hook never emits a followup_message or fabricates completion.

## Graph and retrieval boundaries

The adapter reads schemas 9 through 13 through SQLite URI mode=ro and never initializes or migrates graph storage. It validates required core columns and rejects graphs anchored to a different repository root. It uses installed code-review-graph's read-only path resolver, includes installed version, commit anchor and live file hashes, bounds traversals/time/results, and reports unindexed files, truncation, unknown/partial coverage and stale graphs. Schema 11 and later also preserve target-resolution labels; observed unresolved call targets make coverage partial. Incomplete build markers make coverage partial and suppress derived flows; the warning distinguishes an interrupted build from pending postprocessing. Explicitly build/update graphs using code-review-graph; agent-mem retrieval does not silently do so.

Graph dependency overlap is a reason to review an assumption, not a verdict that the decision is wrong. Conflicting decision texts are surfaced only when they share an explicit metadata.topic; users resolve them through append-only supersession. Historical findings and failed approaches remain available with their qualifiers. Later verification failures replace earlier passes as the current reported result while retaining both records. Reopening chains follow the latest related finding and its disposition, so dismissing a reopened finding updates the original chain view.

## Errors found and handled

| Error | Fix/result |
|---|---|
| CLI imported removed CONFIG_FILE | Resolve config path through _config_file(); source CLI starts again. |
| MCP startup text on stdout | Send startup diagnostics to stderr; actual MCP SDK initialize/list/call succeeded. |
| Distinct file edits mistaken for retries | Hash original edits before persisting sanitized ranges; direct launcher events retain both edits. |
| Historical passing verification outlived later failure | Select latest verification for latest executed fix. |
| Scoped exports collided across branches | Hash full repository/worktree/branch/session scope. |
| Private memory lacked reconnect route | Return durable handles and provide CLI/MCP handoff APIs. |
| Token accounting differed from emitted context | Declare canonical representation, emit it on CLI/hooks, budget hook prefix and disclose transport exclusion. |
| Package build timed out reading OneDrive-generated egg-info | Preserve those artifacts and rebuild identical current sources in a clean local staging directory; logs retain the original failure. |
| Deprecated license metadata | Use SPDX license string/license-files with setuptools>=77. |
| Python 3.10 lacked declared TOML parser | Add conditional tomli dependency. |

Operational logs are under verification/runs/implementation. Logs use isolated copies of actual source and synthetic lifecycle/review inputs; they are not evidence of real PR outcomes. Existing extraction benchmark results establish only its fixture extraction behavior. The earlier five_approaches contract runner is preserved as a planning artifact and was not expanded or used to manufacture feature passes.

## Release-candidate supported configuration

Supported engineering storage is a local filesystem on one host. SQLite WAL does
not support mounted network filesystems or concurrent access across hosts. Live
SQLite files must not be cloud-synchronized. For hosted/synchronized code, set
`AGENT_MEM_STORAGE_DIR` to an absolute unsynchronized local directory and provide
that environment to every CLI, MCP server, and Cursor process. Explicit CLI
`--storage` takes precedence over the environment. No automatic data migration
occurs; existing repository identity/session scopes continue to apply.

Successful prompt capture now returns `continue: true`, as required by the Cursor
hook schema. Capture errors also emit that response while reporting failure on
stderr and a nonzero exit, so prompt observation remains fail-open. Windows hook
installation is rejected before files are written because POSIX shell quoting
is not qualified there. Hook commands/launchers remain local-installation bound;
regenerate them per environment and do not claim cloud portability.

References: [Cursor hooks](https://cursor.com/docs/hooks),
[SQLite WAL](https://sqlite.org/wal.html),
[Python shell quoting](https://docs.python.org/3/library/shlex.html).
