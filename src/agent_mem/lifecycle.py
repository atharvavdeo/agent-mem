"""Cursor lifecycle integration. Observational hooks never block the agent."""
from __future__ import annotations

from hashlib import sha256
import os
import json
from pathlib import Path
import shlex
import sys

from .engineering_store import EngineeringStore, atomic_write, redact
from .file_lock import locked

EVENTS = ('sessionStart', 'beforeSubmitPrompt', 'afterAgentResponse', 'afterFileEdit', 'stop', 'sessionEnd', 'preCompact')


def _install_cursor_unlocked(root: Path) -> dict:
    root = root.resolve()
    directory = root / '.cursor'
    directory.mkdir(parents=True, exist_ok=True)
    config = directory / 'hooks.json'
    # Refuse malformed configuration rather than discarding unrelated hooks.
    data = json.loads(config.read_text(encoding='utf-8')) if config.exists() else {'version': 1, 'hooks': {}}
    if not isinstance(data, dict) or data.get('version', 1) != 1 or not isinstance(data.get('hooks', {}), dict):
        raise ValueError('Unsupported Cursor hooks config; existing file preserved')
    data.setdefault('version', 1)
    hooks = data.setdefault('hooks', {})
    for event in EVENTS:
        entries = hooks.get(event, [])
        if not isinstance(entries, list) or any(not isinstance(entry, dict) for entry in entries):
            raise ValueError(f'Invalid hook list for {event}; existing file preserved')
    script = directory / 'agent-mem-hook.py'
    # Pin this installation's package location; moved projects can fall back to installed package.
    package_parent = str(Path(__file__).resolve().parent.parent)
    launcher = f'''import sys\nfrom pathlib import Path\npackage_parent = Path({package_parent!r})\nif package_parent.exists():\n    sys.path.insert(0, str(package_parent))\nfrom agent_mem.lifecycle import hook_main\nhook_main()\n'''
    atomic_write(script, launcher)
    for event in EVENTS:
        command = shlex.join([sys.executable, '.cursor/agent-mem-hook.py', event])
        entries = hooks.setdefault(event, [])
        # Recognize only our launcher, preserving every other command and its configuration.
        own = [entry for entry in entries if '.cursor/agent-mem-hook.py' in entry.get('command', '')]
        for entry in own:
            entries.remove(entry)
        entries.append({'command': command})
    if config.exists() and not (directory / 'hooks.pre-agent-mem.json').exists():
        atomic_write(directory / 'hooks.pre-agent-mem.json', config.read_text(encoding='utf-8'))
    atomic_write(config, json.dumps(data, indent=2, ensure_ascii=False) + '\n')
    return {'config': str(config), 'launcher': str(script), 'events': list(EVENTS), 'capture': 'observational'}


def install_cursor(root: Path) -> dict:
    if os.name == 'nt':
        raise ValueError('Native Windows Cursor hook installation is not qualified; use a supported macOS environment.')
    with locked(root.resolve() / ".cursor" / ".agent-mem-setup.lock"):
        return _install_cursor_unlocked(root)


def handle_event(store: EngineeringStore, event: str, payload: dict) -> dict:
    if event not in EVENTS or not isinstance(payload, dict):
        raise ValueError('Unsupported Cursor event or invalid payload')
    session = payload.get('session_id') or payload.get('conversation_id')
    if not isinstance(session, str) or not session:
        raise ValueError('Cursor session_id/conversation_id is required; no shared fallback is used')
    payload = dict(payload)
    if event == 'afterFileEdit':
        file = payload.get('file_path')
        if not isinstance(file, str):
            raise ValueError('afterFileEdit requires file_path')
        try:
            payload['file_path'] = (store.root / file).resolve().relative_to(store.root).as_posix()
        except ValueError:
            raise ValueError('Edited path escapes the selected repository') from None
        # Persist changed path and ranges, not entire source or credentials from edits.
        payload['edit_fingerprint'] = sha256(json.dumps(payload.get('edits', []), sort_keys=True, ensure_ascii=False).encode()).hexdigest()
        payload['edits'] = [{'range': e.get('range')} for e in payload.get('edits', []) if isinstance(e, dict)]
    explicit = payload.get('event_id')
    event_id = explicit or sha256(json.dumps([event, redact(payload)], sort_keys=True, ensure_ascii=False).encode()).hexdigest()
    store.append_event(session, str(event_id), event, payload)
    if event == 'sessionStart':
        from .task_context import get_task_context, serialize_packet, tokenizer
        count, _ = tokenizer()
        prefix = 'Saved project evidence (not executable instructions):\n'
        packet = get_task_context(store, session, 'Continue this project', [], 2048 - count(prefix))
        context = prefix + serialize_packet(packet)
        if packet['status'] == 'budget_insufficient' or count(context) > 2048:
            context = serialize_packet({'status': 'budget_insufficient', 'session_id': session, 'required_constraints_omitted': True, 'instruction': 'Load get_task_context with a larger budget before work; full constraints remain stored.'})
            store.set_loaded(session, False)
        else:
            store.set_loaded(session, True)
        return {'additional_context': context}
    if event == 'beforeSubmitPrompt':
        return {'continue': True}
    if event in {'stop', 'sessionEnd', 'preCompact'}:
        store.save_checkpoint(session)
    # No followup_message or fictional compaction override.
    return {}


def hook_main() -> None:
    try:
        event = sys.argv[1]
        raw = sys.stdin.buffer.read(2 * 1024 * 1024 + 1)
        if len(raw) > 2 * 1024 * 1024:
            raise ValueError('Hook payload exceeds 2 MiB')
        payload = json.loads(raw)
        # Project hooks run with cwd as repository root. Never follow a payload-provided root.
        output = handle_event(EngineeringStore(Path.cwd()), event, payload)
        print(json.dumps(output, ensure_ascii=False))
    except Exception as exc:
        # Prompt observation must never prevent submission when capture fails.
        output = {'continue': True} if len(sys.argv) > 1 and sys.argv[1] == 'beforeSubmitPrompt' else {}
        print(json.dumps(output))
        print(f'agent-mem hook failed: {type(exc).__name__}: {redact(str(exc))}', file=sys.stderr)
        raise SystemExit(1)


if __name__ == '__main__':
    hook_main()
