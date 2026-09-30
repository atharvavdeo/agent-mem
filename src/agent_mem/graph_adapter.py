"""Bounded, read-only code-review-graph schema 9 through 13 adapter."""
from __future__ import annotations
from hashlib import sha256
from contextlib import closing
from importlib.metadata import PackageNotFoundError, version
import json
from pathlib import Path
import sqlite3
import time

from .engineering_store import git


def graph_context(root: Path, changed_files: list[str], max_nodes: int = 100, depth: int = 2) -> dict:
    result = {'backend': 'code-review-graph', 'status': 'unavailable', 'coverage': 'unknown', 'nodes': [], 'edges': [], 'flows': [], 'warnings': []}
    root = root.resolve()
    absolute = []
    for file in changed_files:
        path = (root / file).resolve()
        if not path.is_relative_to(root):
            raise ValueError('Changed file escapes repository')
        absolute.append(str(path))
    try:
        result['version'] = version('code-review-graph')
        from code_review_graph.incremental import get_db_path
        path = get_db_path(root, read_only=True)
        if not path.is_file():
            legacy = root / '.code-review-graph.db'
            if legacy.is_file():
                path = legacy
            else:
                result['warnings'].append('No graph database. Build it explicitly with code-review-graph build.')
                return result
        with closing(sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=0.1)) as db:
            db.row_factory = sqlite3.Row
            db.execute('PRAGMA query_only=ON')
            deadline = time.monotonic() + 3
            db.set_progress_handler(lambda: int(time.monotonic() > deadline), 1000)
            # Keep build markers, nodes and derived data on one read snapshot
            # if an upstream graph rebuild runs concurrently.
            db.execute('BEGIN')
            metadata = dict(db.execute('SELECT key,value FROM metadata'))
            schema = int(metadata.get('schema_version', 0))
            result['schema_version'] = schema
            result['metadata'] = metadata
            # v10-v13 add symbol lookup, target resolution and FTS columns;
            # the nodes/edges/flows queried here retain their existing shape.
            if schema not in {9, 10, 11, 12, 13}:
                result['warnings'].append('Unsupported graph schema; graph left unchanged.')
                return result
            required = {
                'nodes': {'id', 'kind', 'name', 'qualified_name', 'file_path', 'file_hash'},
                'edges': {'id', 'kind', 'source_qualified', 'target_qualified'},
            }
            for table, columns in required.items():
                actual = {row['name'] for row in db.execute(f'PRAGMA table_info({table})')}
                if not columns <= actual:
                    result['warnings'].append(f'Incomplete graph schema: missing {table} columns; graph left unchanged.')
                    return result
            indexed_root = metadata.get('repo_root')
            if indexed_root and Path(indexed_root).resolve() != root:
                result['warnings'].append('Graph belongs to a different repository root; select or build a graph for this checkout.')
                return result
            result['status'] = 'available'
            # A read-only graph cannot prove full parser coverage; report uncertainty explicitly.
            result['coverage'] = 'unknown'
            result['warnings'].append('Graph coverage is unknown; static edges may be unresolved or inferred.')
            build_state = metadata.get('build_state', '')
            if build_state:
                result['build_state'] = build_state
            if build_state in {'in-progress', 'postprocess-pending'}:
                result['coverage'] = 'partial'
                repair = 'build' if build_state == 'in-progress' else 'postprocess'
                result['warnings'].append(f'Graph build is {build_state}; run code-review-graph {repair} explicitly. Derived flows are omitted.')
            head = git(root, 'rev-parse', 'HEAD')
            result['head_matches_build'] = bool(head and metadata.get('git_head_sha') == head)
            if head and not result['head_matches_build']:
                result['status'] = 'stale'
                result['warnings'].append('Graph commit anchor does not match current HEAD.')
            for key, value in metadata.items():
                pending = value not in {'', '0', '[]', '{}'}
                if key == 'cpp_identity_pending' and pending:
                    try:
                        state = json.loads(value)
                        if isinstance(state, dict) and isinstance(state.get('files'), list):
                            pending = bool(state['files'])
                    except (TypeError, ValueError):
                        pass
                if ('fail' in key or 'pending' in key) and pending:
                    result['coverage'] = 'partial'
                    result['warnings'].append('Graph reports pending/failed parsing: ' + key)
            if not absolute:
                return result
            placeholders = ','.join('?' for _ in absolute)
            rows = db.execute(f'SELECT * FROM nodes WHERE file_path IN ({placeholders}) LIMIT ?', (*absolute, max_nodes + 1)).fetchall()
            nodes = {r['qualified_name']: dict(r) for r in rows[:max_nodes]}
            omitted = len(rows) > max_nodes
            result['unindexed_files'] = [f for f in changed_files if str((root / f).resolve()) not in {r['file_path'] for r in rows}]
            if result['unindexed_files']:
                result['coverage'] = 'partial'
                result['warnings'].append('Some changed files are unindexed; empty impact is not proof of no impact.')
            frontier = list(nodes)
            edges = {}
            for _ in range(min(max(depth, 0), 4)):
                if not frontier:
                    break
                marks = ','.join('?' for _ in frontier)
                query = f"SELECT * FROM edges WHERE kind IN ('CALLS','IMPORTS_FROM','INHERITS','IMPLEMENTS','TESTED_BY','DEPENDS_ON') AND (source_qualified IN ({marks}) OR target_qualified IN ({marks})) LIMIT ?"
                relationships = db.execute(query, (*frontier, *frontier, 201)).fetchall()
                omitted |= len(relationships) > 200
                next_names = set()
                for row in relationships[:200]:
                    edges[row['id']] = dict(row)
                    next_names.update((row['source_qualified'], row['target_qualified']))
                next_names.difference_update(nodes)
                if not next_names:
                    break
                names = sorted(next_names)[:max_nodes]
                more = db.execute('SELECT * FROM nodes WHERE qualified_name IN (' + ','.join('?' for _ in names) + ') LIMIT ?', (*names, max_nodes + 1)).fetchall()
                frontier = []
                for row in more:
                    if len(nodes) >= max_nodes:
                        omitted = True
                        break
                    nodes[row['qualified_name']] = dict(row)
                    frontier.append(row['qualified_name'])
            for node in nodes.values():
                file = Path(node['file_path']).resolve()
                if not file.is_relative_to(root):
                    continue
                indexed = node.get('file_hash')
                live = sha256(file.read_bytes()).hexdigest() if file.is_file() else None
                node['hash_matches'] = bool(indexed and live == indexed)
                if not node['hash_matches']:
                    result['status'] = 'stale'
                node['file_path'] = file.relative_to(root).as_posix()
                node['qualified_name'] = node['qualified_name'].replace(str(root) + '/', '')
                result['nodes'].append({k: node.get(k) for k in ('id','kind','name','qualified_name','file_path','line_start','line_end','is_test','hash_matches')})
            result['edges'] = [{k: (v.replace(str(root) + '/', '') if isinstance(v, str) else v) for k, v in edge.items() if k in {'kind','source_qualified','target_qualified','confidence','confidence_tier','target_resolution'}} for edge in list(edges.values())[:200]]
            if any(edge.get('target_resolution') == 'unresolved' for edge in result['edges']):
                result['coverage'] = 'partial'
                result['warnings'].append('Some call targets are unresolved; graph impact coverage is partial.')
            if nodes:
                ids = [n['id'] for n in nodes.values()]
                tables = {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if {'flows', 'flow_memberships'} <= tables and build_state not in {'in-progress', 'postprocess-pending'}:
                    flow_rows = db.execute('SELECT DISTINCT f.* FROM flows f JOIN flow_memberships m ON f.id=m.flow_id WHERE m.node_id IN (' + ','.join('?' for _ in ids) + ') LIMIT 21', ids).fetchall()
                    result['flows'] = [{k: (v.replace(str(root) + '/', '') if isinstance(v, str) else v) for k, v in dict(r).items()} for r in flow_rows[:20]]
                    omitted |= len(flow_rows) > 20
            result['truncated'] = omitted
            if omitted:
                result['warnings'].append('Graph context truncated at bounded traversal limits.')
            if result['status'] == 'stale':
                result['warnings'].append('Graph evidence is stale; refresh graph explicitly before relying on it.')
    except (ImportError, PackageNotFoundError, sqlite3.Error, ValueError, OSError) as exc:
        result['status'] = 'unavailable'
        result['warnings'].append(f'Graph unavailable: {type(exc).__name__}')
    return result
