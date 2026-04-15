from __future__ import annotations

import ast
from dataclasses import dataclass, field
from datetime import datetime
import fnmatch
import io
from pathlib import Path
import re
import tokenize
from typing import Any

from .config import get_config, get_groq_api_key
from .memory import (
    get_active_context_file,
    get_fallback_memory_file,
    get_handoff_outbox_file,
    is_obsidian_enabled,
    list_recent_session_files,
)

OUTPUT_DIR_NAME = "agent-mem-output"
COMPACT_FUNCTION_LIMIT = 60
COMPACT_CONCEPT_LIMIT = 24
COMPACT_FUNCTION_DETAIL_LIMIT = 24

COMMENT_TAGS = ("NOTE", "TODO", "RATIONALE", "DECISION", "BLOCKER")
DECISION_TAGS = {"DECISION", "RATIONALE", "NOTE"}
BLOCKER_TAGS = {"BLOCKER", "TODO"}

CONCEPT_SOURCE_EXTRACTED = "EXTRACTED"
CONCEPT_SOURCE_INFERRED = "INFERRED"
CONCEPT_SOURCE_BOTH = "EXTRACTED+INFERRED"

GENERIC_CONCEPT_TERMS = {
    "file",
    "files",
    "function",
    "functions",
    "class",
    "classes",
    "import",
    "imports",
    "render",
    "get",
    "set",
    "run",
    "read",
    "write",
    "build",
    "project",
    "python",
    "config",
    "module",
}

IGNORED_PARTS = {
    ".git",
    ".agent-memory",
    ".cursor",
    ".claude",
    ".antigravity",
    ".opencode",
    ".vscode",
    ".venv",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    "build",
    "dist",
    "node_modules",
    OUTPUT_DIR_NAME,
}


@dataclass
class ImportRecord:
    kind: str
    module: str
    imported: str
    alias: str
    line: int


@dataclass
class MethodRecord:
    name: str
    qualified_name: str
    args: str
    docstring: str
    line: int
    is_async: bool


@dataclass
class ClassRecord:
    name: str
    qualified_name: str
    file_path: str
    line: int
    docstring: str
    methods: list[MethodRecord] = field(default_factory=list)


@dataclass
class FunctionRecord:
    name: str
    qualified_name: str
    file_path: str
    line: int
    args: str
    docstring: str
    is_async: bool
    owner_class: str | None = None


@dataclass
class CommentRecord:
    tag: str
    text: str
    file_path: str
    line: int


@dataclass
class FileRecord:
    file_path: str
    module_docstring: str
    imports: list[ImportRecord] = field(default_factory=list)
    classes: list[ClassRecord] = field(default_factory=list)
    functions: list[FunctionRecord] = field(default_factory=list)
    comments: list[CommentRecord] = field(default_factory=list)


@dataclass
class ChatSnippet:
    source_label: str
    source_path: str
    updated_at: str
    excerpt: str


@dataclass
class BuildResult:
    output_dir: Path
    files_written: list[str]
    python_files_scanned: int
    classes_found: int
    functions_found: int
    imports_found: int
    comments_found: int
    decisions_found: int
    blockers_found: int
    concepts_found: int
    enrichment_requested: bool
    enriched: bool
    compact: bool
    notes: list[str] = field(default_factory=list)


def _now() -> datetime:
    return datetime.now().astimezone()


def _iso_now() -> str:
    return _now().isoformat(timespec="seconds")


def _project_name(project_root: Path) -> str:
    return project_root.resolve().name


def _clean_line(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _is_noise_item(value: str) -> bool:
    cleaned = _clean_line(value)
    if not cleaned:
        return True

    lowered = cleaned.lower()
    if cleaned.startswith("#"):
        return True
    if lowered in {"none", "none recorded", "n/a", "unknown"}:
        return True
    if lowered.startswith("none ") or lowered.startswith("no "):
        return True
    if lowered in {"open tasks or blockers", "key decisions", "active decisions"}:
        return True
    return False


def _shorten(text: str, max_len: int = 180) -> str:
    single = _clean_line(text)
    if len(single) <= max_len:
        return single
    return single[: max_len - 3].rstrip() + "..."


def _wiki_label(prefix: str, value: str) -> str:
    clean_value = _clean_line(value)
    return f"{prefix} - {clean_value}" if clean_value else f"{prefix} - Unknown"


def _frontmatter(title: str, type_name: str, project_name: str) -> str:
    generated_at = _iso_now()
    return (
        "---\n"
        f"title: \"{title}\"\n"
        f"type: \"{type_name}\"\n"
        f"project: \"{project_name}\"\n"
        f"generated_at: \"{generated_at}\"\n"
        "generator: \"agent-mem graph build\"\n"
        "tags:\n"
        "  - agent-mem\n"
        "  - knowledge-graph\n"
        "---\n\n"
    )


def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _write_markdown(path: Path, title: str, type_name: str, project_name: str, body: str) -> None:
    _ensure_parent(path)
    path.write_text(_frontmatter(title, type_name, project_name) + body.rstrip() + "\n", encoding="utf-8")


def _path_has_ignored_part(path: Path) -> bool:
    return any(part in IGNORED_PARTS for part in path.parts)


def _matches_exclude_pattern(relative_path: Path, exclude_patterns: list[str]) -> bool:
    relative_text = relative_path.as_posix()
    for pattern in exclude_patterns:
        clean_pattern = pattern.strip()
        if not clean_pattern:
            continue
        if fnmatch.fnmatch(relative_text, clean_pattern):
            return True
        if fnmatch.fnmatch(relative_path.name, clean_pattern):
            return True
    return False


def _collect_python_files(project_root: Path, exclude_patterns: list[str] | None = None) -> list[Path]:
    patterns = exclude_patterns or []
    files: list[Path] = []
    for path in project_root.rglob("*.py"):
        relative = path.relative_to(project_root)
        if _path_has_ignored_part(relative):
            continue
        if _matches_exclude_pattern(relative, patterns):
            continue
        files.append(path)
    return sorted(files)


def _format_args(node: ast.arguments) -> str:
    parts: list[str] = []

    posonly = [arg.arg for arg in node.posonlyargs]
    normal = [arg.arg for arg in node.args]
    kwonly = [arg.arg for arg in node.kwonlyargs]

    if posonly:
        parts.extend(posonly)
        parts.append("/")

    parts.extend(normal)

    if node.vararg:
        parts.append(f"*{node.vararg.arg}")
    elif kwonly:
        parts.append("*")

    parts.extend(kwonly)

    if node.kwarg:
        parts.append(f"**{node.kwarg.arg}")

    return ", ".join(parts)


def _extract_comments(source: str, file_path: str) -> list[CommentRecord]:
    comments: list[CommentRecord] = []
    reader = io.StringIO(source).readline
    for token in tokenize.generate_tokens(reader):
        if token.type != tokenize.COMMENT:
            continue
        raw = token.string.lstrip("#").strip()
        if not raw:
            continue
        upper = raw.upper()
        for tag in COMMENT_TAGS:
            if tag in upper:
                comments.append(
                    CommentRecord(
                        tag=tag,
                        text=raw,
                        file_path=file_path,
                        line=token.start[0],
                    )
                )
                break
    return comments


class _PythonStructureCollector(ast.NodeVisitor):
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.imports: list[ImportRecord] = []
        self.classes: list[ClassRecord] = []
        self.functions: list[FunctionRecord] = []
        self._class_stack: list[str] = []

    def visit_Import(self, node: ast.Import) -> Any:
        for alias in node.names:
            self.imports.append(
                ImportRecord(
                    kind="import",
                    module=alias.name,
                    imported="",
                    alias=alias.asname or "",
                    line=node.lineno,
                )
            )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> Any:
        module = ("." * node.level) + (node.module or "")
        for alias in node.names:
            self.imports.append(
                ImportRecord(
                    kind="from",
                    module=module,
                    imported=alias.name,
                    alias=alias.asname or "",
                    line=node.lineno,
                )
            )
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> Any:
        parent = ".".join(self._class_stack)
        qualified_name = f"{parent}.{node.name}" if parent else node.name

        methods: list[MethodRecord] = []
        for child in node.body:
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                method_name = f"{qualified_name}.{child.name}"
                methods.append(
                    MethodRecord(
                        name=child.name,
                        qualified_name=method_name,
                        args=_format_args(child.args),
                        docstring=ast.get_docstring(child) or "",
                        line=child.lineno,
                        is_async=isinstance(child, ast.AsyncFunctionDef),
                    )
                )

        self.classes.append(
            ClassRecord(
                name=node.name,
                qualified_name=qualified_name,
                file_path=self.file_path,
                line=node.lineno,
                docstring=ast.get_docstring(node) or "",
                methods=methods,
            )
        )

        self._class_stack.append(node.name)
        self.generic_visit(node)
        self._class_stack.pop()

    def _record_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        owner_class = ".".join(self._class_stack) if self._class_stack else None
        qualified_name = f"{owner_class}.{node.name}" if owner_class else node.name
        self.functions.append(
            FunctionRecord(
                name=node.name,
                qualified_name=qualified_name,
                file_path=self.file_path,
                line=node.lineno,
                args=_format_args(node.args),
                docstring=ast.get_docstring(node) or "",
                is_async=isinstance(node, ast.AsyncFunctionDef),
                owner_class=owner_class,
            )
        )

    def visit_FunctionDef(self, node: ast.FunctionDef) -> Any:
        self._record_function(node)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> Any:
        self._record_function(node)
        self.generic_visit(node)


def _parse_python_file(path: Path, project_root: Path) -> FileRecord:
    source = path.read_text(encoding="utf-8", errors="ignore")
    relative_path = str(path.relative_to(project_root))

    tree = ast.parse(source)
    collector = _PythonStructureCollector(relative_path)
    collector.visit(tree)

    return FileRecord(
        file_path=relative_path,
        module_docstring=ast.get_docstring(tree) or "",
        imports=collector.imports,
        classes=collector.classes,
        functions=collector.functions,
        comments=_extract_comments(source, relative_path),
    )


def _extract_section_items(text: str, headings: tuple[str, ...]) -> list[str]:
    escaped = [re.escape(item) for item in headings]
    heading_group = "|".join(escaped)
    pattern = rf"(?ims)^#+\s*(?:{heading_group})\s*$\n(.*?)(?=^\s*#|\Z)"

    items: list[str] = []
    for match in re.finditer(pattern, text):
        block = match.group(1)
        for line in block.splitlines():
            stripped = line.strip()
            if stripped.startswith(("-", "*")):
                value = stripped[1:].strip()
                if value:
                    items.append(value)
    return items


def _extract_sentences_with_tags(text: str, tags: tuple[str, ...]) -> list[str]:
    tags_upper = {tag.upper() for tag in tags}
    results: list[str] = []
    for line in text.splitlines():
        clean = line.strip()
        if not clean or clean.startswith("#"):
            continue
        upper = clean.upper()
        if any(tag in upper for tag in tags_upper):
            results.append(clean.lstrip("-*").strip())
    return results


def _safe_read(path: Path, limit: int = 5000) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")[:limit]


def _collect_chat_sources(project_root: Path, project_name: str) -> list[tuple[Path, str]]:
    sources: list[tuple[Path, str]] = []
    seen: set[Path] = set()

    active_file = get_active_context_file(project_root)
    if active_file.exists():
        seen.add(active_file.resolve())
        sources.append((active_file, "active-context"))

    for session_file in list_recent_session_files(project_name, count=8, project_root=project_root):
        resolved = session_file.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        sources.append((session_file, "session-memory"))

    fallback_file = get_fallback_memory_file(project_root)
    if fallback_file.exists() and fallback_file.resolve() not in seen:
        seen.add(fallback_file.resolve())
        sources.append((fallback_file, "fallback-memory"))

    handoff_path = get_handoff_outbox_file(project_root)
    if handoff_path.exists() and handoff_path.resolve() not in seen:
        seen.add(handoff_path.resolve())
        sources.append((handoff_path, "handoff-outbox"))

    return sources


def _append_back_to_index(lines: list[str]) -> None:
    lines.extend(["", "---", "", "Back to Index: [[Index]]"])


def _build_symbol_catalog(records: list[FileRecord]) -> tuple[list[str], list[str]]:
    classes = sorted({cls.qualified_name for record in records for cls in record.classes})
    functions = sorted({fn.qualified_name for record in records for fn in record.functions})
    return classes, functions


def _infer_related_symbol_links(
    text: str,
    class_symbols: list[str],
    function_symbols: list[str],
    max_links: int = 3,
) -> list[str]:
    haystack = _clean_line(text).lower()
    if not haystack:
        return []

    links: list[str] = []
    seen: set[str] = set()

    def _maybe_add(link: str) -> None:
        if link in seen:
            return
        seen.add(link)
        links.append(link)

    for symbol in function_symbols:
        short = symbol.split(".")[-1].lower()
        if len(short) < 4:
            continue
        if re.search(rf"\\b{re.escape(short)}\\b", haystack):
            _maybe_add(f"[[Function - {symbol}]]")
            if len(links) >= max_links:
                return links

    for symbol in class_symbols:
        short = symbol.split(".")[-1].lower()
        if len(short) < 4:
            continue
        if re.search(rf"\\b{re.escape(short)}\\b", haystack):
            _maybe_add(f"[[Class - {symbol}]]")
            if len(links) >= max_links:
                return links

    return links


def _render_recent_chats(chat_snippets: list[ChatSnippet]) -> str:
    lines: list[str] = [
        "# Recent Chats",
        "",
        "This section captures recent saved context snippets to help reconstruct session continuity.",
        "",
        "Recent context collected from active memory and recent session artifacts.",
        "",
        "| Source | Updated | Excerpt |",
        "| --- | --- | --- |",
    ]

    if not chat_snippets:
        lines.append("| None | n/a | No saved chats were found. |")
    else:
        for snippet in chat_snippets:
            source_link = f"[[Chat Source - {snippet.source_label}]]"
            excerpt = snippet.excerpt.replace("|", "\\|")
            lines.append(f"| {source_link} | {snippet.updated_at} | {excerpt} |")

    _append_back_to_index(lines)

    return "\n".join(lines)


def _render_files(records: list[FileRecord]) -> str:
    lines: list[str] = [
        "# Python Files",
        "",
        "This table summarizes file-level structure discovered from static Python parsing.",
        "",
        "| File | Classes | Functions | Imports | Tagged Comments |",
        "| --- | ---: | ---: | ---: | ---: |",
    ]

    if not records:
        lines.append("| None | 0 | 0 | 0 | 0 |")

    for record in records:
        lines.append(
            f"| [[File - {record.file_path}]] | {len(record.classes)} | {len(record.functions)} | {len(record.imports)} | {len(record.comments)} |"
        )

    lines.extend(["", "## Module Docstrings", ""])
    docstring_count = 0
    for record in records:
        if not record.module_docstring:
            continue
        docstring_count += 1
        lines.append(f"- [[File - {record.file_path}]]: {_shorten(record.module_docstring, 240)}")

    if docstring_count == 0:
        lines.append("- No module docstrings were found.")

    _append_back_to_index(lines)

    return "\n".join(lines)


def _render_classes(records: list[FileRecord]) -> str:
    classes: list[ClassRecord] = []
    for record in records:
        classes.extend(record.classes)

    classes.sort(key=lambda item: (item.file_path, item.line))

    lines: list[str] = [
        "# Classes",
        "",
        "This note lists class definitions and links them to methods and source files.",
        "",
    ]
    if not classes:
        lines.append("No classes were detected in scanned Python files.")
        _append_back_to_index(lines)
        return "\n".join(lines)

    lines.extend(["| Class | File | Methods |", "| --- | --- | ---: |"])
    for cls in classes:
        lines.append(
            f"| [[Class - {cls.qualified_name}]] | [[File - {cls.file_path}]]:{cls.line} | {len(cls.methods)} |"
        )

    lines.extend(["", "## Details", ""])
    for cls in classes:
        lines.append(f"### [[Class - {cls.qualified_name}]]")
        lines.append("")
        lines.append(f"- File: [[File - {cls.file_path}]]:{cls.line}")
        if cls.docstring:
            lines.append(f"- Docstring: {_shorten(cls.docstring, 320)}")
        if not cls.methods:
            lines.append("- Methods: none")
            lines.append("")
            continue

        lines.append("- Methods:")
        for method in cls.methods:
            async_prefix = "async " if method.is_async else ""
            lines.append(
                f"  - [[Function - {method.qualified_name}]]: {async_prefix}{method.name}({method.args})"
            )
        lines.append("")

    _append_back_to_index(lines)

    return "\n".join(lines)


def _render_functions(
    records: list[FileRecord],
    compact: bool = False,
    compact_limit: int = COMPACT_FUNCTION_LIMIT,
    compact_detail_limit: int = COMPACT_FUNCTION_DETAIL_LIMIT,
    full_list_note_path: str = "agent-mem-output/Full/functions-full.md",
) -> str:
    functions: list[FunctionRecord] = []
    for record in records:
        functions.extend(record.functions)

    functions.sort(key=lambda item: (item.file_path, item.line))

    lines: list[str] = [
        "# Functions",
        "",
        "This table captures function-level structure, ownership, and signatures.",
        "",
    ]

    if not functions:
        lines.append("| None | n/a | n/a |")
        _append_back_to_index(lines)
        return "\n".join(lines)

    total_functions = len(functions)
    shown_functions = functions
    if compact and total_functions > compact_limit:
        shown_functions = functions[:compact_limit]
        lines.extend(
            [
                f"> Compact mode: showing first {compact_limit} of {total_functions} functions.",
                f"> See full list in {full_list_note_path}.",
                "",
            ]
        )

    lines.extend([
        "| Function | File | Owner |",
        "| --- | --- | --- |",
    ])

    for fn in shown_functions:
        owner = f"[[Class - {fn.owner_class}]]" if fn.owner_class else "module"
        lines.append(
            f"| [[Function - {fn.qualified_name}]] | [[File - {fn.file_path}]]:{fn.line} | {owner} |"
        )

    lines.extend(["", "## Details", ""])
    detail_items = shown_functions
    if compact and len(detail_items) > compact_detail_limit:
        detail_items = detail_items[:compact_detail_limit]

    for fn in detail_items:
        async_prefix = "async " if fn.is_async else ""
        lines.append(f"### [[Function - {fn.qualified_name}]]")
        lines.append("")
        lines.append(f"- Signature: `{async_prefix}{fn.name}({fn.args})`")
        lines.append(f"- File: [[File - {fn.file_path}]]:{fn.line}")
        if fn.owner_class:
            lines.append(f"- Owner: [[Class - {fn.owner_class}]]")
        if fn.docstring:
            lines.append(f"- Docstring: {_shorten(fn.docstring, 320)}")
        lines.append("")

    if compact and total_functions > compact_limit:
        lines.append(
            f"- Detail section truncated in compact mode. See full list in {full_list_note_path}."
        )

    _append_back_to_index(lines)

    return "\n".join(lines)


def _render_imports(records: list[FileRecord]) -> str:
    rows: list[tuple[str, ImportRecord]] = []
    for record in records:
        for import_record in record.imports:
            rows.append((record.file_path, import_record))

    rows.sort(key=lambda item: (item[0], item[1].line, item[1].module, item[1].imported))

    lines: list[str] = [
        "# Imports",
        "",
        "This table shows import statements to help map dependency flow across files.",
        "",
        "| File | Statement |",
        "| --- | --- |",
    ]

    if not rows:
        lines.append("| None | No imports found. |")
        return "\n".join(lines)

    for file_path, record in rows:
        if record.kind == "import":
            statement = f"import {record.module}"
            if record.alias:
                statement += f" as {record.alias}"
        else:
            statement = f"from {record.module} import {record.imported}"
            if record.alias:
                statement += f" as {record.alias}"
        lines.append(f"| [[File - {file_path}]]:{record.line} | `{statement}` |")

    _append_back_to_index(lines)

    return "\n".join(lines)


def _render_decisions(
    decisions: list[str],
    comment_records: list[CommentRecord],
    class_symbols: list[str],
    function_symbols: list[str],
) -> str:
    lines: list[str] = ["# Key Decisions", ""]
    lines.extend(
        [
            "Decision candidates are collected from session memory and tagged source comments.",
            "",
        ]
    )

    if not decisions and not comment_records:
        lines.append("No decision signals were found.")
        _append_back_to_index(lines)
        return "\n".join(lines)

    if decisions:
        lines.append("## From Memory and Sessions")
        lines.append("")
        for item in decisions:
            label = _wiki_label("Decision", _shorten(item, 80))
            related = _infer_related_symbol_links(item, class_symbols, function_symbols)
            related_text = f" (Related: {', '.join(related)})" if related else ""
            lines.append(f"- [[{label}]]: {_shorten(item, 260)}{related_text}")
        lines.append("")

    tagged = [record for record in comment_records if record.tag in DECISION_TAGS]
    if tagged:
        lines.append("## From Code Comments")
        lines.append("")
        for record in tagged:
            label = _wiki_label("Decision", _shorten(record.text, 80))
            related = _infer_related_symbol_links(record.text, class_symbols, function_symbols)
            related_text = f" (Related: {', '.join(related)})" if related else ""
            lines.append(
                f"- [[{label}]]: {_shorten(record.text, 240)} ([[File - {record.file_path}]]:{record.line}){related_text}"
            )

    _append_back_to_index(lines)

    return "\n".join(lines)


def _render_blockers(
    blockers: list[str],
    comment_records: list[CommentRecord],
    class_symbols: list[str],
    function_symbols: list[str],
) -> str:
    lines: list[str] = ["# Open Blockers", ""]
    lines.extend(
        [
            "Potential blockers are synthesized from memory artifacts and tagged code comments.",
            "",
        ]
    )

    if not blockers and not comment_records:
        lines.append("No open blockers were detected.")
        _append_back_to_index(lines)
        return "\n".join(lines)

    if blockers:
        lines.append("## From Memory and Sessions")
        lines.append("")
        for item in blockers:
            label = _wiki_label("Blocker", _shorten(item, 80))
            related = _infer_related_symbol_links(item, class_symbols, function_symbols)
            related_text = f" (Related: {', '.join(related)})" if related else ""
            lines.append(f"- [[{label}]]: {_shorten(item, 260)}{related_text}")
        lines.append("")

    tagged = [record for record in comment_records if record.tag in BLOCKER_TAGS]
    if tagged:
        lines.append("## From Code Comments")
        lines.append("")
        for record in tagged:
            label = _wiki_label("Blocker", _shorten(record.text, 80))
            related = _infer_related_symbol_links(record.text, class_symbols, function_symbols)
            related_text = f" (Related: {', '.join(related)})" if related else ""
            lines.append(
                f"- [[{label}]]: {_shorten(record.text, 240)} ([[File - {record.file_path}]]:{record.line}){related_text}"
            )

    _append_back_to_index(lines)

    return "\n".join(lines)


def _split_identifier_words(value: str) -> list[str]:
    normalized = re.sub(r"[^A-Za-z0-9_]", " ", value)
    words: list[str] = []
    for part in normalized.split():
        split = re.sub(r"([a-z0-9])([A-Z])", r"\1 \2", part)
        words.extend(item.lower() for item in split.split("_") if item)
    return words


def _collect_concepts(
    records: list[FileRecord],
    memory_items: list[str],
    decision_items: list[str],
    blocker_items: list[str],
) -> list[tuple[str, int]]:
    raw_score: dict[str, int] = {}

    def bump(term: str, amount: int = 1) -> None:
        clean = term.strip().lower()
        if not clean or len(clean) < 3:
            return
        if clean in {"self", "none", "true", "false", "from", "import"}:
            return
        raw_score[clean] = raw_score.get(clean, 0) + amount

    for record in records:
        for cls in record.classes:
            bump(cls.name, 3)
            for word in _split_identifier_words(cls.name):
                bump(word, 1)
        for fn in record.functions:
            bump(fn.name, 2)
            for word in _split_identifier_words(fn.name):
                bump(word, 1)
        for imp in record.imports:
            bump(imp.module.split(".")[0], 1)

    for line in memory_items + decision_items + blocker_items:
        for word in _split_identifier_words(line):
            bump(word, 1)

    ranked: list[tuple[str, int, int]] = []
    for term, score in raw_score.items():
        adjusted = score
        if term in GENERIC_CONCEPT_TERMS:
            adjusted = max(1, int(round(score * 0.28)))
        if term.startswith("_"):
            adjusted = max(1, int(round(adjusted * 0.7)))
        ranked.append((term, adjusted, score))

    ranked.sort(key=lambda item: (item[1], item[2], item[0]), reverse=True)
    return [(term, adjusted) for term, adjusted, _ in ranked[:40]]


def _concept_label_counts(concept_sources: dict[str, str]) -> tuple[int, int]:
    extracted_count = 0
    inferred_count = 0
    for label in concept_sources.values():
        if CONCEPT_SOURCE_EXTRACTED in label:
            extracted_count += 1
        if CONCEPT_SOURCE_INFERRED in label:
            inferred_count += 1
    return extracted_count, inferred_count


def _parse_confidence_item(item: str, default_confidence: int = 70) -> tuple[str, int]:
    text = _clean_line(item)
    if not text:
        return "", default_confidence

    confidence = default_confidence
    match = re.search(r"confidence\s*[:=]\s*(\d{1,3})", text, flags=re.IGNORECASE)
    if not match:
        match = re.search(r"\|\s*(\d{1,3})\s*$", text)
    if match:
        confidence = max(0, min(100, int(match.group(1))))
        text = text[: match.start()] + text[match.end() :]

    cleaned = _clean_line(text).strip("|;:,- ")
    return cleaned, confidence


def _parse_inferred_items(items: list[str], default_confidence: int = 70) -> list[tuple[str, int]]:
    deduped: dict[str, tuple[str, int]] = {}
    for item in items:
        label, confidence = _parse_confidence_item(item, default_confidence=default_confidence)
        if _is_noise_item(label):
            continue

        key = label.lower()
        existing = deduped.get(key)
        if existing is None or confidence > existing[1]:
            deduped[key] = (label, confidence)

    return list(deduped.values())


def _merge_llm_concepts(
    concepts: list[tuple[str, int]],
    concept_sources: dict[str, str],
    concept_confidence: dict[str, int],
    llm_concepts: list[tuple[str, int]],
) -> list[tuple[str, int]]:
    merged_scores: dict[str, int] = {term: value for term, value in concepts}

    for concept, confidence in llm_concepts:
        normalized = _clean_line(concept).lower()
        if _is_noise_item(normalized):
            continue

        if normalized in merged_scores:
            merged_scores[normalized] += 1
            if concept_sources.get(normalized) == CONCEPT_SOURCE_EXTRACTED:
                concept_sources[normalized] = CONCEPT_SOURCE_BOTH
            concept_confidence[normalized] = max(concept_confidence.get(normalized, 0), confidence)
        else:
            merged_scores[normalized] = 2
            concept_sources[normalized] = CONCEPT_SOURCE_INFERRED
            concept_confidence[normalized] = confidence

    merged = sorted(merged_scores.items(), key=lambda item: (item[1], item[0]), reverse=True)
    return merged


def _render_concepts(
    concepts: list[tuple[str, int]],
    concept_sources: dict[str, str],
    concept_confidence: dict[str, int],
    llm_relationships: list[tuple[str, int]],
    enriched: bool,
    compact: bool = False,
    compact_limit: int = COMPACT_CONCEPT_LIMIT,
    full_list_note_path: str = "agent-mem-output/Full/concepts-full.md",
) -> str:
    lines: list[str] = [
        "# Concepts",
        "",
        "This note combines deterministic and optional inferred concepts used for navigation and planning.",
        "",
    ]

    shown_concepts = concepts
    total_concepts = len(concepts)
    if compact and total_concepts > compact_limit:
        shown_concepts = concepts[:compact_limit]
        lines.extend(
            [
                f"> Compact mode: showing first {compact_limit} of {total_concepts} concepts.",
                f"> See full list in {full_list_note_path}.",
                "",
            ]
        )

    lines.extend([
        "| Concept | Score | Source | Confidence |",
        "| --- | ---: | --- | ---: |",
    ])

    if not shown_concepts:
        lines.append("| none | 0 | n/a | n/a |")
    else:
        for term, value in shown_concepts:
            source = concept_sources.get(term, CONCEPT_SOURCE_EXTRACTED)
            confidence = concept_confidence.get(term)
            confidence_text = str(confidence) if confidence is not None else "n/a"
            lines.append(f"| [[Concept - {term}]] | {value} | {source} | {confidence_text} |")

    lines.extend(["", "## Relationships", ""])
    lines.append(
        "- [[Relation - EXTRACTED]]: Deterministic structural links were extracted from AST, tagged comments, and saved memory artifacts."
    )

    if enriched:
        if llm_relationships:
            for relation, confidence in llm_relationships:
                lines.append(f"- [[Relation - INFERRED]] (confidence: {confidence}%): {_shorten(relation, 260)}")
        else:
            lines.append(
                "- [[Relation - INFERRED]]: Enrichment was requested, but no inferred relationships were produced in this run."
            )
    else:
        lines.append("- [[Relation - INFERRED]]: Not generated (run with `--enrich`).")

    _append_back_to_index(lines)

    return "\n".join(lines)


def _render_graph_report(
    project_name: str,
    records: list[FileRecord],
    decisions: list[str],
    blockers: list[str],
    concepts: list[tuple[str, int]],
    concept_sources: dict[str, str],
    concept_confidence: dict[str, int],
    llm_relationships: list[tuple[str, int]],
    enrichment_requested: bool,
    enriched: bool,
    compact: bool,
    notes: list[str],
) -> str:
    class_count = sum(len(record.classes) for record in records)
    function_count = sum(len(record.functions) for record in records)
    import_count = sum(len(record.imports) for record in records)
    comment_count = sum(len(record.comments) for record in records)
    extracted_count, inferred_count = _concept_label_counts(concept_sources)
    inferred_concept_confidences = [
        concept_confidence[term]
        for term in concept_confidence
        if CONCEPT_SOURCE_INFERRED in concept_sources.get(term, "")
    ]
    inferred_relationship_confidences = [confidence for _, confidence in llm_relationships]

    top_concepts = ", ".join(term for term, _ in concepts[:8]) or "none"

    lines: list[str] = [
        "# Graph Report",
        "",
        f"Project `{project_name}` was scanned and converted into Obsidian-ready notes.",
        "",
        "## Summary",
        "",
        f"- Python files scanned: {len(records)}",
        f"- Classes found: {class_count}",
        f"- Functions found: {function_count}",
        f"- Imports found: {import_count}",
        f"- Tagged comments found: {comment_count}",
        f"- Decision signals: {len(decisions)}",
        f"- Blocker signals: {len(blockers)}",
        f"- Top concepts: {top_concepts}",
        f"- LLM enrichment requested: {'yes' if enrichment_requested else 'no'}",
        f"- LLM enrichment applied: {'yes' if enriched else 'no'}",
        f"- Compact mode: {'yes' if compact else 'no'}",
        f"- Concepts labeled EXTRACTED: {extracted_count}",
        f"- Concepts labeled INFERRED: {inferred_count}",
        f"- Inferred concept avg confidence: {round(sum(inferred_concept_confidences) / len(inferred_concept_confidences), 1) if inferred_concept_confidences else 'n/a'}",
        f"- Inferred relationships: {len(llm_relationships) if enriched else 0}",
        f"- Inferred relationship avg confidence: {round(sum(inferred_relationship_confidences) / len(inferred_relationship_confidences), 1) if inferred_relationship_confidences else 'n/a'}",
        "",
        "## Label Definitions",
        "",
        "- `EXTRACTED`: Deterministic signal from code AST, imports, comments, and saved memory artifacts.",
        "- `INFERRED`: Optional semantic signal added by `--enrich`.",
        "",
        "## Navigation",
        "",
        "- [[Index]]",
        "- [[Code/files]]",
        "- [[Code/classes]]",
        "- [[Code/functions]]",
        "- [[Code/imports]]",
        "- [[Decisions/key-decisions]]",
        "- [[Decisions/open-blockers]]",
        "- [[Sessions/recent-chats]]",
        "- [[Concepts]]",
        "",
    ]

    if notes:
        lines.append("## Notes")
        lines.append("")
        for note in notes:
            lines.append(f"- {note}")

    _append_back_to_index(lines)

    return "\n".join(lines)


def _render_index(
    project_name: str,
    records: list[FileRecord],
    decisions: list[str],
    blockers: list[str],
    concepts: list[tuple[str, int]],
    compact: bool,
    file_count_written: int,
) -> str:
    total_classes = sum(len(record.classes) for record in records)
    total_functions = sum(len(record.functions) for record in records)
    total_imports = sum(len(record.imports) for record in records)
    generated_at = _now().strftime("%Y-%m-%d %H:%M:%S %Z")
    top_concepts = concepts[:10]
    decision_status = "Healthy" if decisions else "No explicit decision signals"
    blocker_status = "Attention needed" if blockers else "Healthy"
    concept_status = "Healthy" if concepts else "Low coverage"
    compact_status = "Enabled" if compact else "Disabled"

    lines: list[str] = [
        "# Agent-Mem Knowledge Graph Dashboard",
        "",
        f"Executive control panel for `{project_name}` with code intelligence, memory signals, and action-ready navigation.",
        "",
        "> [!summary] Executive Snapshot",
        f"> - Generated: {generated_at}",
        f"> - Notes generated: {file_count_written}",
        f"> - Engineering footprint: {len(records)} files, {total_classes} classes, {total_functions} functions",
        f"> - Memory posture: {len(decisions)} decisions, {len(blockers)} blockers",
        f"> - Compact mode: {compact_status}",
        "",
        "## KPI Summary",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
        f"| Python Files | {len(records)} |",
        f"| Classes | {total_classes} |",
        f"| Functions | {total_functions} |",
        f"| Imports | {total_imports} |",
        f"| Decisions | {len(decisions)} |",
        f"| Blockers | {len(blockers)} |",
        f"| Concepts | {len(concepts)} |",
        "",
        "## Operational Health",
        "",
        "| Domain | Status | Owner View |",
        "| --- | --- | --- |",
        f"| Decisions | {decision_status} | [[Decisions/key-decisions]] |",
        f"| Blockers | {blocker_status} | [[Decisions/open-blockers]] |",
        f"| Concepts | {concept_status} | [[Concepts]] |",
        "| Graph Report | Ready | [[Graph-Report]] |",
        "",
        "## Strategic Navigation",
        "",
        "### Engineering Assets",
        "",
        "- [[Code/files]]",
        "- [[Code/classes]]",
        "- [[Code/functions]]",
        "- [[Code/imports]]",
        "",
        "### Decision Intelligence",
        "",
        "- [[Decisions/key-decisions]]",
        "- [[Decisions/open-blockers]]",
        "- [[Sessions/recent-chats]]",
        "- [[Concepts]]",
        "- [[Graph-Report]]",
        "",
        "## Priority Concepts",
        "",
        "Highest-signal concepts extracted from code and memory artifacts.",
        "",
        "| Rank | Concept | Score |",
        "| ---: | --- | ---: |",
    ]

    if top_concepts:
        for idx, (term, score) in enumerate(top_concepts, start=1):
            lines.append(f"| {idx} | [[Concept - {term}]] | {score} |")
    else:
        lines.append("| 1 | No concepts extracted yet | 0 |")

    lines.extend(
        [
            "",
            "## Executive Actions",
            "",
        ]
    )

    if blockers:
        lines.append("- Prioritize [[Decisions/open-blockers]] to reduce near-term delivery risk.")
    else:
        lines.append("- No active blocker signal detected. Continue against current implementation priorities.")

    if not decisions:
        lines.append("- Add explicit DECISION/RATIONALE notes in code or memory to strengthen traceability.")
    else:
        lines.append("- Keep [[Decisions/key-decisions]] current as architecture and tradeoffs evolve.")

    lines.extend(
        [
            "- Rebuild this dashboard after substantial changes: `agent-mem graph build`.",
            "",
            "## Reporting Cadence",
            "",
            f"Last refresh: {generated_at}.",
            "Refresh this dashboard with `agent-mem graph build` or `agent-mem graph build --compact`.",
        ]
    )

    return "\n".join(lines)


def _enrich_with_groq(
    project_name: str,
    records: list[FileRecord],
    concepts: list[tuple[str, int]],
) -> tuple[list[tuple[str, int]], list[tuple[str, int]], list[str]]:
    api_key = get_groq_api_key()
    if not api_key:
        return [], [], ["LLM enrichment skipped because GROQ_API_KEY is not configured."]

    try:
        from groq import Groq
    except Exception:
        return [], [], ["LLM enrichment skipped because the Groq client is not available."]

    model = get_config().get("groq_model") or "llama-3.3-70b-versatile"
    client = Groq(api_key=api_key)

    seed_classes = [cls.qualified_name for record in records for cls in record.classes[:3]][:12]
    seed_functions = [fn.qualified_name for record in records for fn in record.functions[:3]][:20]
    seed_concepts = [term for term, _ in concepts[:20]]

    prompt = (
        f"Project: {project_name}\n"
        "Infer higher-level concepts and relationships from deterministic code extraction.\n"
        "Return markdown with exactly these headings and bullet lists:\n"
        "## Concepts\n"
        "## Relationships\n"
        "No extra headings.\n"
        "Every bullet MUST include confidence 0-100 using this exact suffix: '| confidence=<int>'.\n"
        "Example: - authentication handoff | confidence=82\n\n"
        f"Classes:\n- " + "\n- ".join(seed_classes) + "\n\n"
        f"Functions:\n- " + "\n- ".join(seed_functions) + "\n\n"
        f"Deterministic concepts:\n- " + "\n- ".join(seed_concepts)
    )

    try:
        completion = client.chat.completions.create(
            model=model,
            temperature=0.1,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You provide concise engineering concept inference. "
                        "Return only the requested headings and bullet lists."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
        )
    except Exception as exc:
        return [], [], [f"LLM enrichment skipped after Groq error: {exc}"]

    content = (completion.choices[0].message.content or "").strip()
    parsed_concepts = _parse_inferred_items(_extract_section_items(content, ("Concepts",)), default_confidence=70)
    parsed_relationships = _parse_inferred_items(
        _extract_section_items(content, ("Relationships",)),
        default_confidence=65,
    )
    if not parsed_concepts and not parsed_relationships:
        return [], [], ["LLM enrichment produced no structured bullets; deterministic output was kept."]

    return parsed_concepts[:20], parsed_relationships[:20], ["LLM enrichment added inferred concepts and relationships."]


def build_graph(
    project_root: Path | None = None,
    enrich: bool = False,
    exclude_file_patterns: list[str] | None = None,
    compact: bool = False,
) -> BuildResult:
    root = (project_root or Path.cwd()).resolve()
    project_name = _project_name(root)
    normalized_excludes = [pattern.strip() for pattern in (exclude_file_patterns or []) if pattern.strip()]

    output_dir = root / OUTPUT_DIR_NAME
    code_dir = output_dir / "Code"
    decisions_dir = output_dir / "Decisions"
    sessions_dir = output_dir / "Sessions"
    full_dir = output_dir / "Full"

    code_dir.mkdir(parents=True, exist_ok=True)
    decisions_dir.mkdir(parents=True, exist_ok=True)
    sessions_dir.mkdir(parents=True, exist_ok=True)
    if compact:
        full_dir.mkdir(parents=True, exist_ok=True)

    python_files = _collect_python_files(root, exclude_patterns=normalized_excludes)
    records: list[FileRecord] = []
    notes: list[str] = []

    if normalized_excludes:
        notes.append("Excluded file patterns: " + ", ".join(normalized_excludes))

    for path in python_files:
        try:
            records.append(_parse_python_file(path, root))
        except SyntaxError as exc:
            notes.append(f"Skipped {path.relative_to(root)} due to syntax error: {exc}")

    all_comments: list[CommentRecord] = [
        comment
        for record in records
        for comment in record.comments
    ]

    chat_sources = _collect_chat_sources(root, project_name)
    chat_snippets: list[ChatSnippet] = []
    memory_blobs: list[str] = []

    for source_path, label in chat_sources:
        text = _safe_read(source_path, limit=7000)
        if not text.strip():
            continue
        memory_blobs.append(text)
        modified_at = datetime.fromtimestamp(source_path.stat().st_mtime).astimezone().strftime("%Y-%m-%d %H:%M")
        chat_snippets.append(
            ChatSnippet(
                source_label=f"{label}:{source_path.name}",
                source_path=str(source_path),
                updated_at=modified_at,
                excerpt=_shorten(text, 220),
            )
        )

    decision_items: list[str] = []
    blocker_items: list[str] = []

    for blob in memory_blobs:
        decision_items.extend(_extract_section_items(blob, ("Key decisions", "Key Decisions")))
        blocker_items.extend(
            _extract_section_items(blob, ("Open tasks or blockers", "Open Tasks or Blockers", "Blockers"))
        )
        decision_items.extend(_extract_sentences_with_tags(blob, ("DECISION", "RATIONALE")))
        blocker_items.extend(_extract_sentences_with_tags(blob, ("BLOCKER", "TODO")))

    for comment in all_comments:
        if comment.tag in DECISION_TAGS:
            decision_items.append(comment.text)
        if comment.tag in BLOCKER_TAGS:
            blocker_items.append(comment.text)

    def _dedupe(items: list[str], limit: int = 120) -> list[str]:
        seen: set[str] = set()
        result: list[str] = []
        for item in items:
            clean = _clean_line(item)
            if _is_noise_item(clean):
                continue
            key = clean.lower()
            if key in seen:
                continue
            seen.add(key)
            result.append(clean)
            if len(result) >= limit:
                break
        return result

    deduped_decisions = _dedupe(decision_items, limit=120)
    deduped_blockers = _dedupe(blocker_items, limit=120)
    class_symbols, function_symbols = _build_symbol_catalog(records)

    concepts = _collect_concepts(records, memory_blobs, deduped_decisions, deduped_blockers)
    concept_sources: dict[str, str] = {term: CONCEPT_SOURCE_EXTRACTED for term, _ in concepts}
    concept_confidence: dict[str, int] = {}
    enrichment_requested = enrich
    enrichment_applied = False

    llm_relationships: list[tuple[str, int]] = []
    if enrich:
        llm_concepts, llm_relationships, enrich_notes = _enrich_with_groq(project_name, records, concepts)
        notes.extend(enrich_notes)
        if llm_concepts or llm_relationships:
            enrichment_applied = True
        if llm_concepts:
            concepts = _merge_llm_concepts(concepts, concept_sources, concept_confidence, llm_concepts)
    elif is_obsidian_enabled():
        notes.append("Deterministic mode completed. Re-run with --enrich to add optional inferred relationships.")

    concepts = sorted(concepts, key=lambda item: (item[1], item[0]), reverse=True)
    concept_sources = {term: concept_sources.get(term, CONCEPT_SOURCE_EXTRACTED) for term, _ in concepts}

    files_to_write = 10 + (2 if compact else 0)
    body_index = _render_index(
        project_name,
        records,
        deduped_decisions,
        deduped_blockers,
        concepts,
        compact=compact,
        file_count_written=files_to_write,
    )
    body_files = _render_files(records)
    body_classes = _render_classes(records)
    body_functions = _render_functions(records, compact=compact)
    body_imports = _render_imports(records)
    body_decisions = _render_decisions(deduped_decisions, all_comments, class_symbols, function_symbols)
    body_blockers = _render_blockers(deduped_blockers, all_comments, class_symbols, function_symbols)
    body_sessions = _render_recent_chats(chat_snippets)
    body_concepts = _render_concepts(
        concepts,
        concept_sources,
        concept_confidence,
        llm_relationships,
        enriched=enrichment_requested,
        compact=compact,
    )
    body_report = _render_graph_report(
        project_name,
        records,
        deduped_decisions,
        deduped_blockers,
        concepts,
        concept_sources,
        concept_confidence,
        llm_relationships,
        enrichment_requested=enrichment_requested,
        enriched=enrichment_applied,
        compact=compact,
        notes=notes,
    )

    targets = {
        output_dir / "Index.md": ("Index", "agent-mem-graph-index", body_index),
        code_dir / "files.md": ("Code Files", "agent-mem-graph-code-files", body_files),
        code_dir / "classes.md": ("Code Classes", "agent-mem-graph-code-classes", body_classes),
        code_dir / "functions.md": ("Code Functions", "agent-mem-graph-code-functions", body_functions),
        code_dir / "imports.md": ("Code Imports", "agent-mem-graph-code-imports", body_imports),
        decisions_dir / "key-decisions.md": ("Key Decisions", "agent-mem-graph-decisions", body_decisions),
        decisions_dir / "open-blockers.md": ("Open Blockers", "agent-mem-graph-blockers", body_blockers),
        sessions_dir / "recent-chats.md": ("Recent Chats", "agent-mem-graph-recent-chats", body_sessions),
        output_dir / "Concepts.md": ("Concepts", "agent-mem-graph-concepts", body_concepts),
        output_dir / "Graph-Report.md": ("Graph Report", "agent-mem-graph-report", body_report),
    }

    if compact:
        body_functions_full = _render_functions(
            records,
            compact=False,
            full_list_note_path="agent-mem-output/Full/functions-full.md",
        )
        body_concepts_full = _render_concepts(
            concepts,
            concept_sources,
            concept_confidence,
            llm_relationships,
            enriched=enrichment_requested,
            compact=False,
            full_list_note_path="agent-mem-output/Full/concepts-full.md",
        )
        targets[full_dir / "functions-full.md"] = (
            "Functions Full",
            "agent-mem-graph-functions-full",
            body_functions_full,
        )
        targets[full_dir / "concepts-full.md"] = (
            "Concepts Full",
            "agent-mem-graph-concepts-full",
            body_concepts_full,
        )

    files_written: list[str] = []
    for path, (title, type_name, body) in targets.items():
        _write_markdown(path, title, type_name, project_name, body)
        files_written.append(str(path.relative_to(root)))

    return BuildResult(
        output_dir=output_dir,
        files_written=files_written,
        python_files_scanned=len(records),
        classes_found=sum(len(record.classes) for record in records),
        functions_found=sum(len(record.functions) for record in records),
        imports_found=sum(len(record.imports) for record in records),
        comments_found=len(all_comments),
        decisions_found=len(deduped_decisions),
        blockers_found=len(deduped_blockers),
        concepts_found=len(concepts),
        enrichment_requested=enrichment_requested,
        enriched=enrichment_applied,
        compact=compact,
        notes=notes,
    )

    concepts = sorted(concepts, key=lambda item: (item[1], item[0]), reverse=True)
    concept_sources = {term: concept_sources.get(term, CONCEPT_SOURCE_EXTRACTED) for term, _ in concepts}

    files_to_write = 10 + (2 if compact else 0)
    body_index = _render_index(
        project_name,
        records,
        deduped_decisions,
        deduped_blockers,
        concepts,
        compact=compact,
        file_count_written=files_to_write,
    )
    body_files = _render_files(records)
    body_classes = _render_classes(records)
    body_functions = _render_functions(records, compact=compact)
    body_imports = _render_imports(records)
    body_decisions = _render_decisions(deduped_decisions, all_comments, class_symbols, function_symbols)
    body_blockers = _render_blockers(deduped_blockers, all_comments, class_symbols, function_symbols)
    body_sessions = _render_recent_chats(chat_snippets)
    body_concepts = _render_concepts(
        concepts,
        concept_sources,
        concept_confidence,
        llm_relationships,
        enriched=enrichment_requested,
        compact=compact,
    )
    body_report = _render_graph_report(
        project_name,
        records,
        deduped_decisions,
        deduped_blockers,
        concepts,
        concept_sources,
        concept_confidence,
        llm_relationships,
        enrichment_requested=enrichment_requested,
        enriched=enrichment_applied,
        compact=compact,
        notes=notes,
    )

    targets = {
        output_dir / "Index.md": ("Index", "agent-mem-graph-index", body_index),
        code_dir / "files.md": ("Code Files", "agent-mem-graph-code-files", body_files),
        code_dir / "classes.md": ("Code Classes", "agent-mem-graph-code-classes", body_classes),
        code_dir / "functions.md": ("Code Functions", "agent-mem-graph-code-functions", body_functions),
        code_dir / "imports.md": ("Code Imports", "agent-mem-graph-code-imports", body_imports),
        decisions_dir / "key-decisions.md": ("Key Decisions", "agent-mem-graph-decisions", body_decisions),
        decisions_dir / "open-blockers.md": ("Open Blockers", "agent-mem-graph-blockers", body_blockers),
        sessions_dir / "recent-chats.md": ("Recent Chats", "agent-mem-graph-recent-chats", body_sessions),
        output_dir / "Concepts.md": ("Concepts", "agent-mem-graph-concepts", body_concepts),
        output_dir / "Graph-Report.md": ("Graph Report", "agent-mem-graph-report", body_report),
    }

    if compact:
        body_functions_full = _render_functions(
            records,
            compact=False,
            full_list_note_path="agent-mem-output/Full/functions-full.md",
        )
        body_concepts_full = _render_concepts(
            concepts,
            concept_sources,
            concept_confidence,
            llm_relationships,
            enriched=enrichment_requested,
            compact=False,
            full_list_note_path="agent-mem-output/Full/concepts-full.md",
        )
        targets[full_dir / "functions-full.md"] = (
            "Functions Full",
            "agent-mem-graph-functions-full",
            body_functions_full,
        )
        targets[full_dir / "concepts-full.md"] = (
            "Concepts Full",
            "agent-mem-graph-concepts-full",
            body_concepts_full,
        )

    files_written: list[str] = []
    for path, (title, type_name, body) in targets.items():
        _write_markdown(path, title, type_name, project_name, body)
        files_written.append(str(path.relative_to(root)))

    return BuildResult(
        output_dir=output_dir,
        files_written=files_written,
        python_files_scanned=len(records),
        classes_found=sum(len(record.classes) for record in records),
        functions_found=sum(len(record.functions) for record in records),
        imports_found=sum(len(record.imports) for record in records),
        comments_found=len(all_comments),
        decisions_found=len(deduped_decisions),
        blockers_found=len(deduped_blockers),
        concepts_found=len(concepts),
        enrichment_requested=enrichment_requested,
        enriched=enrichment_applied,
        compact=compact,
        notes=notes,
    )
