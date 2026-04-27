"""Optional tree-sitter-based extraction for TypeScript and JavaScript."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

_AVAILABLE = False
_TS_PARSER = None
_TSX_PARSER = None
_JS_PARSER = None
_TS_LANG = None
_TSX_LANG = None
_JS_LANG = None


def _try_init() -> bool:
    global _AVAILABLE, _TS_PARSER, _TSX_PARSER, _JS_PARSER, _TS_LANG, _TSX_LANG, _JS_LANG
    try:
        from tree_sitter import Language, Parser
        import tree_sitter_typescript as tsts
        import tree_sitter_javascript as tsjs

        _TS_LANG = Language(tsts.language_typescript())
        _TSX_LANG = Language(tsts.language_tsx())
        _JS_LANG = Language(tsjs.language())
        _TS_PARSER = Parser(_TS_LANG)
        _TSX_PARSER = Parser(_TSX_LANG)
        _JS_PARSER = Parser(_JS_LANG)
        return True
    except Exception:
        return False


_AVAILABLE = _try_init()

SUPPORTED_EXTENSIONS = {".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs"}


def is_available() -> bool:
    return _AVAILABLE


@dataclass
class TSFunctionRecord:
    name: str
    file_path: str
    line: int
    is_async: bool = False
    owner_class: str | None = None


@dataclass
class TSClassRecord:
    name: str
    file_path: str
    line: int
    methods: list[str] = field(default_factory=list)


@dataclass
class TSImportRecord:
    module: str
    file_path: str
    line: int


@dataclass
class TSFileResult:
    file_path: str
    language: str
    functions: list[TSFunctionRecord] = field(default_factory=list)
    classes: list[TSClassRecord] = field(default_factory=list)
    imports: list[TSImportRecord] = field(default_factory=list)


def parse_file(path: Path, project_root: Path) -> TSFileResult | None:
    """Parse a TS/JS file. Returns None if tree-sitter unavailable or extension unsupported."""
    if not _AVAILABLE:
        return None
    ext = path.suffix.lower()
    if ext not in SUPPORTED_EXTENSIONS:
        return None
    rel = str(path.relative_to(project_root))
    source = path.read_text(encoding="utf-8", errors="replace")
    return _parse(source, rel, ext)


def _parse(source: str, rel_path: str, ext: str) -> TSFileResult:
    if ext == ".tsx":
        parser, lang = _TSX_PARSER, _TSX_LANG
        language = "tsx"
    elif ext in (".js", ".jsx", ".mjs", ".cjs"):
        parser, lang = _JS_PARSER, _JS_LANG
        language = "javascript"
    else:
        parser, lang = _TS_PARSER, _TS_LANG
        language = "typescript"

    tree = parser.parse(source.encode("utf-8"))
    root = tree.root_node
    lines = source.splitlines()

    functions: list[TSFunctionRecord] = []
    classes: list[TSClassRecord] = []
    imports: list[TSImportRecord] = []

    _walk(root, rel_path, lines, functions, classes, imports, owner_class=None)

    return TSFileResult(file_path=rel_path, language=language, functions=functions, classes=classes, imports=imports)


def _node_text(node, lines: list[str]) -> str:
    """Extract text of a node."""
    try:
        return lines[node.start_point[0]][node.start_point[1]:node.end_point[1]]
    except IndexError:
        return ""


def _walk(node, file_path: str, lines: list[str], functions: list, classes: list, imports: list, owner_class: str | None) -> None:
    t = node.type

    if t == "import_statement":
        source_node = node.child_by_field_name("source")
        if source_node:
            module = source_node.text.decode("utf-8", errors="replace").strip("'\"")
            imports.append(TSImportRecord(module=module, file_path=file_path, line=node.start_point[0] + 1))
        return  # don't recurse into imports

    if t in ("function_declaration", "function_signature", "generator_function_declaration"):
        name_node = node.child_by_field_name("name")
        if name_node:
            is_async = any(c.type == "async" for c in node.children)
            functions.append(TSFunctionRecord(
                name=name_node.text.decode("utf-8", errors="replace"),
                file_path=file_path,
                line=node.start_point[0] + 1,
                is_async=is_async,
                owner_class=owner_class,
            ))

    elif t == "class_declaration":
        name_node = node.child_by_field_name("name")
        if name_node:
            class_name = name_node.text.decode("utf-8", errors="replace")
            body = node.child_by_field_name("body")
            methods: list[str] = []
            if body:
                for child in body.children:
                    if child.type == "method_definition":
                        mn = child.child_by_field_name("name")
                        if mn:
                            mname = mn.text.decode("utf-8", errors="replace")
                            methods.append(mname)
                            is_async = any(c.type == "async" for c in child.children)
                            functions.append(TSFunctionRecord(
                                name=mname,
                                file_path=file_path,
                                line=child.start_point[0] + 1,
                                is_async=is_async,
                                owner_class=class_name,
                            ))
            classes.append(TSClassRecord(name=class_name, file_path=file_path, line=node.start_point[0] + 1, methods=methods))
            return  # methods already processed above

    elif t == "lexical_declaration":
        # const foo = () => {} or const foo = async () => {}
        for decl in node.children:
            if decl.type == "variable_declarator":
                name_node = decl.child_by_field_name("name")
                value_node = decl.child_by_field_name("value")
                if name_node and value_node and value_node.type in ("arrow_function", "function"):
                    is_async = any(c.type == "async" for c in value_node.children)
                    functions.append(TSFunctionRecord(
                        name=name_node.text.decode("utf-8", errors="replace"),
                        file_path=file_path,
                        line=node.start_point[0] + 1,
                        is_async=is_async,
                        owner_class=owner_class,
                    ))

    for child in node.children:
        _walk(child, file_path, lines, functions, classes, imports, owner_class)
