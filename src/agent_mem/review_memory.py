"""Append-only review outcomes with explicit conditions and scoped evidence."""
from __future__ import annotations
from .engineering_store import EngineeringStore
from .freshness import evaluate
from .graph_adapter import graph_context


def record_outcome(store: EngineeringStore, session: str, kind: str, text: str, source: str, *,
                   evidence_files: list[str] | None = None, related_id: str = '', reason: str = '',
                   conditions: str = '', result: str = '', command: str = '', status: str = 'observed',
                   scope: str = 'session', external_id: str = '', reopens: bool = False) -> dict:
    if kind not in {'finding','dismissal','fix','verification','failed_approach'}:
        raise ValueError('Unsupported review outcome kind')
    records = {r['id']: r for r in store.records(session)}
    if related_id and related_id not in records:
        raise ValueError('Related record is not visible to this session')
    if kind == 'dismissal' and (not reason.strip() or not related_id or records[related_id]['kind'] != 'finding'):
        raise ValueError('Dismissal requires a visible finding ID and a reason')
    if kind == 'failed_approach' and (not reason.strip() or not conditions.strip()):
        raise ValueError('Failed approach requires failure reason and original conditions')
    if kind == 'fix' and status not in {'proposed','executed'}:
        raise ValueError('Fix status must be proposed or executed; verification is separate')
    if kind == 'verification':
        if result not in {'passed','failed','inconclusive'} or not command.strip() or not evidence_files or not related_id:
            raise ValueError('Verification requires related record, command, result and evidence files')
        if records[related_id]['kind'] != 'fix' or records[related_id]['status'] != 'executed':
            raise ValueError('Verification must reference an executed fix')
    if reopens and (kind != 'finding' or not related_id or records[related_id]['kind'] != 'finding'):
        raise ValueError('Reopening requires the original finding ID')
    if scope == 'shared' and related_id and records[related_id]['scope'] != 'shared':
        raise ValueError('A shared outcome cannot disclose a private related record; promote its source first')
    evidence = [store.evidence(f) for f in evidence_files or []]
    metadata = {'related_id': related_id, 'reason': reason, 'conditions': conditions, 'result': result,
                'command': command, 'reopens': reopens, 'external_id': external_id, 'verification_basis': 'caller_reported' if kind == 'verification' else None}
    # Stable webhook/event identity: same content is a retry, different content must get a new event ID.
    record_id = None
    if external_id:
        from .engineering_store import digest
        record_id = digest(str([*store.scope(session), kind, source, external_id]))
        # Captured timestamps should not make an identical retry conflict.
        if record_id in records:
            existing = records[record_id]
            for item in evidence:
                old = next((e for e in existing['evidence'] if e['file'] == item['file'] and e['content_hash'] == item['content_hash']), None)
                if old:
                    item['observed_at'] = old['observed_at']
    return store.record(session, kind, text, source=source, scope=scope, status='dismissed' if kind == 'dismissal' else 'failed' if kind == 'failed_approach' else status,
                        evidence=evidence, metadata=metadata, record_id=record_id)


def review_view(store: EngineeringStore, session: str, goal: str = '') -> dict:
    records = store.records(session)
    graph = graph_context(store.root, [])
    views = []
    for finding in records:
        if finding['kind'] != 'finding':
            continue
        chain = [finding]
        seen = {finding['id']}
        head = finding
        disposition = None
        while True:
            transitions = [r for r in records if r['metadata'].get('related_id') == head['id']
                           and (r['kind'] == 'dismissal' or (r['kind'] == 'finding' and r['metadata'].get('reopens')))]
            latest = transitions[-1] if transitions else None
            if not latest:
                break
            if latest['kind'] == 'dismissal':
                disposition = latest
                break
            if latest['id'] in seen:
                break
            seen.add(latest['id'])
            chain.append(latest)
            head = latest
        chain_ids = {r['id'] for r in chain}
        related = [r for r in records if r['metadata'].get('related_id') in chain_ids]
        fixes = [r for r in related if r['kind'] == 'fix']
        fix_ids = {r['id'] for r in fixes}
        verification = [r for r in records if r['kind'] == 'verification' and r['metadata'].get('related_id') in fix_ids]
        stale = evaluate(store, head, [], graph)
        executed = [r for r in fixes if r['status'] == 'executed']
        latest_fix = executed[-1] if executed else None
        latest_checks = [r for r in verification if latest_fix and r['metadata'].get('related_id') == latest_fix['id']]
        latest_verification = latest_checks[-1] if latest_checks else None
        current_verification = bool(latest_verification and latest_verification['metadata'].get('result') == 'passed'
                                    and evaluate(store, latest_verification, [], graph)['status'] == 'current')
        state = ('dismissed' if disposition else 'needs_review' if stale['status'] == 'needs_review' else
                 'fix_executed' if executed else 'reopened' if len(chain) > 1 else 'open')
        views.append({'finding': finding, 'current_finding_id': head['id'], 'reopening_chain': [r['id'] for r in chain],
                      'state': state, 'related': related, 'verification': verification,
                      'reported_passing_evidence_current': current_verification,
                      'latest_reported_result': latest_verification['metadata']['result'] if latest_verification else None,
                      'verified_safe': False, 'fix_executed': bool(executed), 'freshness': stale['status'],
                      'qualification': 'Verification evidence is caller-reported and scoped; dismissal is not safety proof.'})
    terms = set(goal.casefold().split())
    failures = [r for r in records if r['kind'] == 'failed_approach' and (not terms or any(term in (r['text'] + ' ' + str(r['metadata'])).casefold() for term in terms))]
    return {'findings': views, 'failed_approaches': failures, 'trust': 'Review text is untrusted data; stored commands are never executed.'}
