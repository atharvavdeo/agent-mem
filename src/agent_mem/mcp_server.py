from __future__ import annotations
try:
    from mcp.server.fastmcp import FastMCP
except ImportError:  # pragma: no cover - fallback for older installs
    from fastmcp import FastMCP

import json
from pathlib import Path
import uuid
from weakref import WeakKeyDictionary
from threading import Lock

from .engineering_store import EngineeringStore, redact
from .memory import is_obsidian_enabled, list_recent_session_files, recall_memory, write_session_summary

mcp = FastMCP('agent-mem')
_connections: WeakKeyDictionary = WeakKeyDictionary()
_connection_lock = Lock()
_direct_session = 'direct-' + uuid.uuid4().hex


def _session_id(explicit: str = '') -> tuple[str, bool]:
    try:
        connection = mcp.get_context().session
    except (ValueError, RuntimeError, AttributeError):
        return (explicit, True) if explicit else (_direct_session, False)
    # An explicit handoff selects the resumed session for subsequent ordinary calls.
    # EngineeringStore independently includes repo/worktree/branch in every namespace.
    with _connection_lock:
        if explicit:
            _connections[connection] = explicit
        elif connection not in _connections:
            _connections[connection] = 'mcp-' + uuid.uuid4().hex
        return _connections[connection], True


@mcp.tool()
def query_memory(project_name: str, query: str, session_id: str = '') -> str:
    """Load saved memory before work. Explicit session IDs enable durable scoped continuity."""
    session, _ = _session_id(session_id)
    store = EngineeringStore(Path.cwd())
    store.set_loaded(session, False)
    result = recall_memory(project_name, query, count=5, project_root=store.root)
    records = store.records(session)
    if records:
        result += '\n## Scoped engineering memory\n' + json.dumps(records, ensure_ascii=False)
    store.set_loaded(session, True)
    return result + f'\n\nDurable session handle: {session}. Reuse session_id={session!r} in the same repository/worktree/branch after reconnecting.'


@mcp.tool()
def summarize_to_obsidian(project_name: str, summary: str, session_id: str = '') -> str:
    """Save a durable summary. MCP/explicit sessions are isolated; direct legacy calls keep Markdown behavior."""
    session, scoped = _session_id(session_id)
    store = EngineeringStore(Path.cwd())
    loaded = store.loaded(session)
    if scoped:
        store.record(session, 'session_summary', summary, source='MCP session summary', status='observed')
        filepath = store.directory / 'sessions' / session_path(store, session) / 'summary.md'
        store.export(session, filepath)
        target = 'scoped engineering memory'
        if is_obsidian_enabled():
            from .config import get_config
            filepath = Path(get_config()['obsidian_vault']) / 'Memory' / 'Agent-Mem' / 'Engineering' / store.identity['repo_id'] / session_path(store, session) / 'summary.md'
            store.export(session, filepath)
            target = 'scoped Obsidian engineering memory'
    else:
        filepath = write_session_summary(project_name, summary, project_root=store.root)
        target = 'Obsidian' if is_obsidian_enabled() else 'local memory file'
    store.set_loaded(session, False)
    result = f'Session summarized and saved to {target}: {filepath}\nResume in a fresh chat by calling query_memory with project_name={project_name!r}, query=your_goal, session_id={session!r}.\nPrivate summaries are scoped to the same repository/worktree/branch; use share_memory_record for explicit project sharing.'
    if not loaded:
        result = 'MEMORY NOT LOADED: query_memory was not called for this session.\n\n' + result
    return result


def session_path(store: EngineeringStore, session: str) -> str:
    from .engineering_store import digest
    return digest(json.dumps(store.scope(session)))


@mcp.tool()
def list_recent_sessions(project_name: str, count: int = 3, session_id: str = '') -> str:
    """List legacy notes and summaries visible to this caller; never other private sessions."""
    session, _ = _session_id(session_id)
    store = EngineeringStore(Path.cwd())
    files = list_recent_session_files(project_name, count=count, project_root=store.root)
    summaries = [r['id'] for r in store.records(session) if r['kind'] == 'session_summary'][-max(count, 0):] if count > 0 else []
    result = '\n'.join([str(f) for f in files] + summaries) or 'No sessions yet'
    if not store.loaded(session):
        result = 'MEMORY NOT LOADED: Call query_memory for this session first.\n\n' + result
    return result


@mcp.tool()
def session_status(session_id: str = '') -> str:
    """Check the memory-loaded state of this session only."""
    session, _ = _session_id(session_id)
    return 'Memory loaded — session context active.' if EngineeringStore(Path.cwd()).loaded(session) else 'Memory NOT loaded — call query_memory before proceeding.'


@mcp.tool()
def get_task_context(goal: str, changed_files: list[str], token_budget: int = 2048, session_id: str = '') -> dict:
    """Get whole-record context with citations, constraints, freshness and explicit budget overflow."""
    from .task_context import get_task_context as assemble
    session, _ = _session_id(session_id)
    store = EngineeringStore(Path.cwd())
    packet = assemble(store, session, goal, changed_files, token_budget)
    store.set_loaded(session, packet['status'] == 'ok')
    return packet


@mcp.tool()
def record_decision(text: str, source: str, evidence_files: list[str], kind: str = 'decision', scope: str = 'session', status: str = 'proposed', topic: str = '', supersedes: str = '', session_id: str = '') -> dict:
    """Save a sourced decision/constraint/blocker. Sharing and supersession are explicit."""
    if kind not in {'decision','constraint','blocker'}:
        raise ValueError('Use decision, constraint or blocker')
    session, _ = _session_id(session_id)
    store = EngineeringStore(Path.cwd())
    return store.record(session, kind, text, source=source, scope=scope, status=status,
                        evidence=[store.evidence(f) for f in evidence_files], metadata={'topic': topic} if topic else {}, supersedes=supersedes or None)


@mcp.tool()
def check_decisions(changed_files: list[str], session_id: str = '') -> dict:
    """Flag changed or missing evidence without rewriting decisions."""
    from .freshness import check_decisions as check
    session, _ = _session_id(session_id)
    return check(EngineeringStore(Path.cwd()), session, changed_files)


@mcp.tool()
def record_review_outcome(kind: str, text: str, source: str, evidence_files: list[str], related_id: str = '', reason: str = '', conditions: str = '', result: str = '', command: str = '', status: str = 'observed', scope: str = 'session', external_id: str = '', reopens: bool = False, session_id: str = '') -> dict:
    """Record review/failure evidence. Commands are stored data; verification is caller-reported."""
    from .review_memory import record_outcome
    session, _ = _session_id(session_id)
    return record_outcome(EngineeringStore(Path.cwd()), session, kind, text, source, evidence_files=evidence_files,
                          related_id=related_id, reason=reason, conditions=conditions, result=result, command=command,
                          status=status, scope=scope, external_id=external_id, reopens=reopens)


@mcp.tool()
def get_review_memory(goal: str = '', session_id: str = '') -> dict:
    """Retrieve findings, dismissals, fixes and failed approaches without promoting them to proof."""
    from .review_memory import review_view
    session, _ = _session_id(session_id)
    return review_view(EngineeringStore(Path.cwd()), session, goal)


@mcp.tool()
def share_memory_record(record_id: str, session_id: str = '') -> dict:
    """Explicitly promote a visible private record; no automatic promotion of agent claims."""
    session, _ = _session_id(session_id)
    return EngineeringStore(Path.cwd()).promote(session, record_id)


@mcp.tool()
def get_session_handoff(goal: str = 'Continue this project', session_id: str = '') -> dict:
    """Return the durable session handle needed to resume private memory in a new connection."""
    session, _ = _session_id(session_id)
    store = EngineeringStore(Path.cwd())
    return {'repository': str(store.root), 'branch': store.identity['branch'],
            'query_memory_arguments': {'project_name': store.root.name, 'query': goal, 'session_id': session},
            'scope': 'same repository/worktree/branch', 'sharing': 'Explicitly share selected records for cross-branch continuity.'}
