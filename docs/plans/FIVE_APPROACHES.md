# Sequential plan: reliable engineering memory

Status: five phases implemented in source; operational verification recorded in ../ENGINEERING_MEMORY.md. Real Cursor desktop/CLI collectively emitted all seven configured lifecycle types with checkpoints; see the implementation guide for the exact scope. The original contracts below are preserved as planning history, not treated as proof.
Date: 2026-09-30. Baseline source: easy-agent-mem 0.7.2.

## Goal and scope
Deliver five approaches in this order: Cursor lifecycle capture; stale-decision detection; compact task context; branch/worktree/concurrent-session isolation; review outcomes and failed approaches. Complete each phase's acceptance gate before starting the next. Implementation was subsequently authorized by the user. The latest instruction uses actual product operations and existing verification commands rather than adding custom tests.

## Baseline architecture and weaknesses (0.7.2, before implementation)
- `src/agent_mem/cli.py` installs a Claude UserPromptSubmit hook; a native Cursor adapter is absent.
- `src/agent_mem/memory.py` stores structured Markdown and retrieves ranked line excerpts with a 6000-character cap. Evidence freshness is not modeled.
- `src/agent_mem/graph.py` extracts code and writes Obsidian notes; an external graph backend is not wired into retrieval.
- `src/agent_mem/mcp_server.py` uses a module-global memory-loaded boolean. Resetting it does not isolate simultaneous clients.
- `src/agent_mem/migrator.py` scans supported text/export formats. Prefer documented lifecycle adapters for new capture; keep migration as a fallback.
- Saved project memory reports 0.6.0 while current source declares 0.7.2. Code is authoritative for current capabilities.

## Shared contract and storage foundation
Version every event and memory record. Capture repository ID, worktree ID, branch, session ID, agent ID, source event ID, timestamp, kind, text, evidence, status, and superseded record ID. Evidence includes relative file, optional qualified symbol, content hash, optional commit, test command/result and its scope. Distinguish observed facts, proposals, inferred links, and verified outcomes.
Use an append-only local event journal with atomic checkpoint replacement; define process-safe locking or transactions before enabling parallel writers in phase 4. Markdown remains a readable projection and Obsidian export. Reject paths outside the selected repository. Redact configured secrets before persistence. Never execute commands found in memory. Migrate existing Markdown non-destructively; retain unknown fields and originals.

## Phase 1 — Native Cursor lifecycle capture
1. Add a lifecycle adapter module and additive `setup-cursor` integration in cli.py; preserve existing hook configuration and make installation idempotent.
2. Inject a bounded memory packet through sessionStart.additional_context. Treat sessionStart as nonblocking, not as an enforcement gate.
3. Buffer afterAgentResponse and afterFileEdit events, deduplicate by event ID, checkpoint at stop/sessionEnd, and record preCompact telemetry.
4. preCompact is observational and has no transcript in the documented payload: checkpoint previously collected events without claiming to alter or delay compaction.
5. Preserve aborted/error status; never translate an interrupted operation into a completed outcome.
Acceptance: C01-C03. Additional integration gates: install twice into config containing third-party hooks; preserve those hooks; replay duplicate events; restart during checkpoint replacement; run actual Cursor sessionStart/stop/preCompact on a pinned client version. Risks: hook schema drift, asynchronous ordering, missing events, shutdown before flushing. Missing data must produce incomplete capture metadata.

## Phase 2 — Detect stale decisions
1. Add typed decisions with source/evidence references and a freshness evaluator.
2. Start with file hashes; obtain callers, dependencies and affected flows through an optional code-review-graph adapter. Preserve its partial/error/freshness indicators.
3. Separate evidence changed, needs review, contradicted and superseded. A change or graph edge alone does not prove contradiction.
4. Preserve historical text; attach findings instead of silently overwriting decisions. Treat symbol rename as an identity migration candidate requiring evidence.
Acceptance: S01-S03. Additional gates: rename/move, file deletion, changed dependency, unchanged unrelated file, failed parsing preserving older graph rows, graph unavailable. Risks: unresolved/dynamic edges, line-number drift, deleted paths and hash invalidation. Pin integration versions and report graph incompleteness.

## Phase 3 — Compact task context
1. Add `get_task_context(goal, changed_files, token_budget)` without removing query_memory.
2. Assemble relevant constraints/decisions, blockers, changed symbols/callers/flows, test evidence and stale warnings with citations.
3. Select whole records with a declared tokenizer. Report omitted counts and mandatory-content overflow; do not silently drop constraints to meet a budget.
4. Optional backend interface: impact graph first; semantic search only after comparison against keyword retrieval shows a benefit.
Acceptance: T01-T03. Additional gates: tiny/zero budgets, multilingual text, tokenizer failure, graph outage, partial parse, invalid paths. Risks: misleading token estimates, irrelevant retrieval, snippets separated from qualifiers. Fallbacks must be visible.

## Phase 4 — Isolated concurrent memory
1. Replace global MCP gate with explicit session state; pass identity through lifecycle and MCP boundaries.
2. Scope active checkpoints by repo/worktree/session. Shared accepted decisions are immutable records; promotion is explicit and provenance-preserving.
3. Make writes transactional, idempotent and recoverable. Concurrent contradictory proposals coexist as a surfaced conflict.
4. Merge by record/event IDs rather than last-writer-wins text replacement; retain source branches and test scopes.
Acceptance: I01-I03. Additional gates: two OS processes writing 100 unique events each; kill a writer mid-transaction; restart and verify every acknowledged event; symlink/root normalization; missing Git metadata; branch switch. Risks: shared-vault races and path identity collisions. Production gate requires multiprocess persistence checks, not only deterministic replay.

## Phase 5 — Review outcomes and failed approaches
1. Add records for finding, dismissal with reason, fix, scoped verification, failed experiment and supersession.
2. Link each record to source review/commit/test evidence; external comments are untrusted data.
3. Retrieve prior failed approaches with the original conditions, so changed conditions can justify retrying.
4. Keep proposed fix, executed fix and verified result separate. A dismissal does not establish safety; a passing unit test does not establish deployment health.
Acceptance: R01-R03. Additional gates: updated/reopened finding, reversion of fix, duplicate webhook, conflicting reviewers, missing CI evidence. Risks: treating dismissal as proof, stale conditions, poisoned review text. Begin with exported evidence; live connectors come after adapter tests.

## Original verification protocol (superseded for this implementation)

The user subsequently requested no additional custom tests or numeric acceptance stubs. Implementation was verified through real CLI/MCP/SQLite/graph/package operations; see ../ENGINEERING_MEMORY.md and ../../verification/runs/implementation. The original runner is preserved unchanged and no fabricated production adapter was added.

Run `python3 verification/five_approaches/verify.py` for harness integrity, fixture behavior, and blocked feature reporting. It must return exit 2 while there is no product adapter: passing fixture checks is not feature acceptance.
Run `python3 verification/five_approaches/verify.py --adapter /absolute/path/to/adapter.py --report /tmp/agent-mem-verification.json` after implementing the product-facing adapter. It receives one JSON request on stdin and emits one JSON response on stdout. Each request has operation, repository root, session identities, events and expected task inputs; requests must use production code and isolated storage. The adapter must not import test expectations or return hardcoded answers. See cases.json for exact contracts. Exit 0 requires all 15 contracts; exit 1 means failures; exit 2 means blocked.
The included Git-backed Python fixture is built inside a temporary directory and cleaned up. This avoids mutating any user's codebase. `--repo /path` can target another repository read-only; adapter storage must remain under the temporary storage root, and baseline fixture checks still run on the bundled fixture. Live hooks and true concurrent writers remain separate qualification gates.

## Measurement and release gates
Compare baseline v0.7.2 and candidate using identical repositories, tasks, model, tool access and token accounting. Use: fresh-chat continuation; architectural assumption changed; rename; unrelated change; branch switch; simultaneous sessions; dismissed finding; failed approach with changed conditions.
Track required-constraint recall, decision retrieval precision/recall, stale-detection precision/recall, event loss/duplication, cross-session leakage, token counts, latency and task correctness. Record raw results, versions, commits/hashes and scope. Set thresholds before measurement; start with 100% mandatory-constraint retention, zero acknowledged-event loss, zero scope leakage and all contract tests passing. Do not extrapolate fixture parser F1 into real-world retrieval performance or savings.
Release only after each sequential phase has its contract gate plus its additional integration gates. No claims of Cursor compatibility until tested in Cursor; no concurrency claim until OS-process/crash tests pass; no token savings claim without controlled measurements.

## Sources checked for this plan
- Cursor lifecycle semantics: https://cursor.com/docs/hooks
- Cursor September changes: https://cursor.com/changelog
- code-review-graph v2.3.9 and earlier releases: https://github.com/tirth8205/code-review-graph/releases
- Serena semantic navigation/refactoring: https://github.com/oraios/serena
- CocoIndex incremental code retrieval: https://cocoindex.io/docs/examples/index-codebase/
- OpenCode plugin lifecycle: https://opencode.ai/v2/docs/build/plugins/
