"""Evidence change flags do not rewrite historical decisions or prove contradiction."""
from __future__ import annotations
from hashlib import sha256
from pathlib import Path
from .engineering_store import EngineeringStore
from .graph_adapter import graph_context


def evaluate(store: EngineeringStore, record: dict, changed_files: list[str] | None = None, graph: dict | None = None) -> dict:
    observations = []
    evidence = record.get('evidence', [])
    for item in evidence:
        path = (store.root / item['file']).resolve()
        if not path.is_relative_to(store.root):
            observations.append({'file': item['file'], 'status': 'invalid_path'})
        elif not path.is_file():
            observations.append({'file': item['file'], 'status': 'missing', 'rename_candidate': 'unresolved'})
        else:
            current = sha256(path.read_bytes()).hexdigest()
            observations.append({'file': item['file'], 'status': 'unchanged' if current == item['content_hash'] else 'changed', 'current_hash': current, 'recorded_hash': item['content_hash']})
    graph = graph if graph is not None else graph_context(store.root, changed_files or [])
    affected = {node['file_path'] for node in graph.get('nodes', [])}
    dependency_overlap = bool(changed_files and affected & {i['file'] for i in evidence})
    changed = any(o['status'] != 'unchanged' for o in observations)
    status = 'needs_review' if changed or dependency_overlap else 'current' if evidence else 'unanchored'
    if record.get('status') == 'superseded':
        status = 'superseded'
    return {'record_id': record['id'], 'status': status, 'historical_text': record['text'], 'evidence': observations,
            'dependency_review': dependency_overlap, 'graph_status': graph['status'], 'coverage': graph['coverage'],
            'warnings': graph.get('warnings', []), 'meaning': 'File/dependency changes require review; they do not prove contradiction.'}


def check_decisions(store: EngineeringStore, session: str, changed_files: list[str] | None = None) -> dict:
    graph = graph_context(store.root, changed_files or [])
    records = store.records(session)
    superseded = {r.get('supersedes') for r in records if r.get('supersedes')}
    decisions = []
    for record in records:
        if record['kind'] in {'decision','constraint','blocker','finding','fix','failed_approach'}:
            if record['id'] in superseded:
                record = {**record, 'status': 'superseded'}
            decisions.append(evaluate(store, record, changed_files, graph))
    return {'decisions': decisions, 'graph': graph}
