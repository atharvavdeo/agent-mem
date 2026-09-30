"""CLI for evidence-backed memory. Inputs are JSON data, never shell commands."""
from __future__ import annotations
import json
from pathlib import Path
import sys
import typer

from .engineering_store import EngineeringStore, redact

app = typer.Typer(help='Evidence-backed, session-scoped engineering memory.')


def emit(value: object) -> None:
    typer.echo(json.dumps(value, indent=2, ensure_ascii=False))


def store_for(root: Path, storage: Path | None) -> EngineeringStore:
    return EngineeringStore(root, storage)


def read_input() -> dict:
    raw = sys.stdin.buffer.read(2 * 1024 * 1024 + 1)
    if len(raw) > 2 * 1024 * 1024:
        raise ValueError('Input exceeds 2 MiB')
    data = json.loads(raw)
    if not isinstance(data, dict):
        raise ValueError('Expected a JSON object')
    return data


def fail(exc: Exception) -> None:
    typer.echo(redact(str(exc)), err=True)
    raise typer.Exit(1)


@app.command('record')
def record(session: str = typer.Option(...), root: Path = typer.Option(Path('.')), storage: Path | None = typer.Option(None)):
    """Store a typed record from stdin. Capture hashes for its evidence_files."""
    try:
        store = store_for(root, storage)
        data = read_input()
        if data.get('kind') not in {'decision','constraint','blocker','session_summary'}:
            raise ValueError('Use engineering review for review outcomes')
        evidence = [store.evidence(file) for file in data.get('evidence_files', [])]
        emit(store.record(session, data['kind'], data['text'], source=data['source'], scope=data.get('scope','session'),
                          status=data.get('status','observed'), agent=data.get('agent_id','user'), evidence=evidence,
                          metadata=data.get('metadata'), record_id=data.get('record_id'), supersedes=data.get('supersedes')))
    except (ValueError, KeyError, OSError) as exc:
        fail(exc)


@app.command('check')
def check(session: str = typer.Option(...), root: Path = typer.Option(Path('.')), storage: Path | None = typer.Option(None), changed: list[str] = typer.Option(None)):
    """Evaluate decisions against current files and optional change-impact graph."""
    from .freshness import check_decisions
    try:
        emit(check_decisions(store_for(root, storage), session, changed or []))
    except (ValueError, OSError) as exc:
        fail(exc)


@app.command('list')
def list_records(session: str = typer.Option(...), root: Path = typer.Option(Path('.')), storage: Path | None = typer.Option(None)):
    """Inspect this session and explicitly shared records."""
    try:
        emit(store_for(root, storage).records(session))
    except (ValueError, OSError) as exc:
        fail(exc)


@app.command('checkpoint')
def checkpoint(session: str = typer.Option(...), root: Path = typer.Option(Path('.')), storage: Path | None = typer.Option(None)):
    """Recover or refresh a captured checkpoint from the event journal."""
    try:
        emit(store_for(root, storage).save_checkpoint(session))
    except (ValueError, OSError) as exc:
        fail(exc)


@app.command('export')
def export(destination: Path, session: str = typer.Option(...), root: Path = typer.Option(Path('.')), storage: Path | None = typer.Option(None)):
    """Export records as readable Markdown, including into an Obsidian vault."""
    try:
        emit({'path': store_for(root, storage).export(session, destination)})
    except (ValueError, OSError) as exc:
        fail(exc)


@app.command('context')
def context(goal: str, session: str = typer.Option(...), root: Path = typer.Option(Path('.')), storage: Path | None = typer.Option(None), changed: list[str] = typer.Option(None), token_budget: int = typer.Option(2048), legacy: bool = typer.Option(True)):
    """Retrieve whole records, evidence freshness and bounded change-impact context."""
    from .task_context import get_task_context, serialize_packet
    try:
        packet = get_task_context(store_for(root, storage), session, goal, changed or [], token_budget, include_legacy=legacy)
        typer.echo(serialize_packet(packet))
        if packet['status'] == 'budget_insufficient':
            raise typer.Exit(2)
    except (ValueError, OSError) as exc:
        fail(exc)


@app.command('review')
def review(session: str = typer.Option(...), root: Path = typer.Option(Path('.')), storage: Path | None = typer.Option(None)):
    """Record a finding, dismissal, fix, scoped verification or failed approach from JSON."""
    from .review_memory import record_outcome
    try:
        data = read_input()
        emit(record_outcome(store_for(root, storage), session, data['kind'], data['text'], data['source'],
                            evidence_files=data.get('evidence_files'), related_id=data.get('related_id',''),
                            reason=data.get('reason',''), conditions=data.get('conditions',''), result=data.get('result',''),
                            command=data.get('command',''), status=data.get('status','observed'), scope=data.get('scope','session'),
                            external_id=data.get('external_id',''), reopens=data.get('reopens',False)))
    except (ValueError, KeyError, OSError) as exc:
        fail(exc)


@app.command('reviews')
def reviews(goal: str = '', session: str = typer.Option(...), root: Path = typer.Option(Path('.')), storage: Path | None = typer.Option(None)):
    """Inspect outcomes, unresolved findings and failed approaches with original conditions."""
    from .review_memory import review_view
    try:
        emit(review_view(store_for(root, storage), session, goal))
    except (ValueError, OSError) as exc:
        fail(exc)


@app.command('share')
def share(record_id: str, session: str = typer.Option(...), root: Path = typer.Option(Path('.')), storage: Path | None = typer.Option(None)):
    """Explicitly promote a private record into shared repository memory."""
    try:
        emit(store_for(root, storage).promote(session, record_id))
    except (ValueError, OSError) as exc:
        fail(exc)


@app.command('prepare-next')
def prepare_next(goal: str = typer.Option('Continue this project'), session: str = typer.Option(...), root: Path = typer.Option(Path('.')), storage: Path | None = typer.Option(None)):
    """Print a durable scoped handoff for a fresh chat or MCP reconnection."""
    try:
        store = store_for(root, storage)
        typer.echo('# Fresh chat handoff\n\n')
        typer.echo(f'Repository: {store.root}\nBranch: {store.identity["branch"]}\nSession ID: {session}\n')
        typer.echo('Call query_memory with this explicit session_id before continuing:')
        emit({'project_name': store.root.name, 'query': goal, 'session_id': session})
        typer.echo('Private memory remains scoped to this repository/worktree/branch. Share selected records explicitly to transfer decisions across branches.')
    except (ValueError, OSError) as exc:
        fail(exc)
