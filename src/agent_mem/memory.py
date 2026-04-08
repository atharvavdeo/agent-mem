from datetime import datetime
from pathlib import Path
import re

from .config import get_config


FALLBACK_DIR_NAME = ".agent-memory"
FALLBACK_FILE_NAME = "memory.md"
FALLBACK_ACTIVE_FILE_NAME = "active.md"
OBSIDIAN_INDEX_NAME = "Index.md"
OBSIDIAN_ACTIVE_NAME = "Active Context.md"


def is_obsidian_enabled() -> bool:
    config = get_config()
    return bool(config.get("use_obsidian") and config.get("obsidian_vault"))


def get_memory_dir(project_root: Path | None = None) -> Path:
    resolved_project_root = (project_root or Path.cwd()).resolve()
    if is_obsidian_enabled():
        vault = Path(get_config()["obsidian_vault"])
        memory_dir = vault / "Memory" / "Agent-Mem"
    else:
        memory_dir = resolved_project_root / FALLBACK_DIR_NAME

    memory_dir.mkdir(parents=True, exist_ok=True)
    return memory_dir


def get_fallback_memory_file(project_root: Path | None = None) -> Path:
    return get_memory_dir(project_root) / FALLBACK_FILE_NAME


def get_active_context_file(project_root: Path | None = None) -> Path:
    memory_dir = get_memory_dir(project_root)
    if is_obsidian_enabled():
        return memory_dir / OBSIDIAN_ACTIVE_NAME
    return memory_dir / FALLBACK_ACTIVE_FILE_NAME


def _timestamp() -> datetime:
    return datetime.now().astimezone()


def _wiki_label(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text.strip())
    return cleaned or "Unknown"


def _slug(text: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return cleaned or "session"


def _extract_file_links(summary: str) -> list[str]:
    matches = re.findall(r"(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+\.[A-Za-z0-9_]+", summary)
    seen: set[str] = set()
    links: list[str] = []
    for match in matches:
        if "/" not in match and "." not in match:
            continue
        label = _wiki_label(f"File - {match}")
        if label not in seen:
            seen.add(label)
            links.append(label)
    return links[:12]


def _extract_section_items(summary: str, heading: str) -> list[str]:
    pattern = rf"(?ims)^#+\s*{re.escape(heading)}\s*$\n(.*?)(?=^\s*#|\Z)"
    match = re.search(pattern, summary)
    if not match:
        return []

    items: list[str] = []
    for line in match.group(1).splitlines():
        stripped = line.strip()
        if stripped.startswith(("-", "*")):
            item = stripped[1:].strip()
            if item:
                items.append(item)
    return items[:10]


def _session_note_name(project_name: str, moment: datetime) -> str:
    return f"{_slug(project_name)}-{moment.strftime('%Y-%m-%d_%H-%M')}-session.md"


def _collect_active_sections(summary: str) -> dict[str, list[str] | str]:
    goal_items = _extract_section_items(summary, "Goal")
    next_steps = _extract_section_items(summary, "Next prioritized steps")
    decisions = _extract_section_items(summary, "Key decisions")
    blockers = _extract_section_items(summary, "Open tasks or blockers")
    files = [label.removeprefix("File - ") for label in _extract_file_links(summary)]

    goal = ""
    if goal_items:
        goal = goal_items[0]
    else:
        goal_match = re.search(r"(?ims)^#+\s*Goal\s*$\n(.*?)(?=^\s*#|\Z)", summary)
        if goal_match:
            goal = " ".join(line.strip() for line in goal_match.group(1).splitlines() if line.strip())

    return {
        "goal": goal.strip() or "Continue the current implementation task.",
        "decisions": decisions[:6],
        "files": files[:10],
        "blockers": blockers[:6],
        "next_steps": next_steps[:6],
    }


def _obsidian_frontmatter(project_name: str, moment: datetime) -> str:
    title = f"Session - {project_name} - {moment.strftime('%Y-%m-%d %H:%M')}"
    created = moment.isoformat(timespec="seconds")
    return (
        "---\n"
        f'title: "{title}"\n'
        f'project: "{project_name}"\n'
        'type: "agent-session"\n'
        f'created: "{created}"\n'
        "tags:\n"
        "  - agent-mem\n"
        "  - coding-session\n"
        "  - memory\n"
        "---\n"
    )


def _obsidian_note(project_name: str, summary: str, moment: datetime) -> str:
    project_link = _wiki_label(project_name)
    decision_links = [_wiki_label(f"Decision - {item}") for item in _extract_section_items(summary, "Key decisions")]
    task_links = [_wiki_label(f"Task - {item}") for item in _extract_section_items(summary, "Open tasks")]
    file_links = _extract_file_links(summary)

    related_links = [f"[[{project_link}]]"]
    related_links.extend(f"[[{label}]]" for label in decision_links)
    related_links.extend(f"[[{label}]]" for label in task_links)
    related_links.extend(f"[[{label}]]" for label in file_links)

    unique_related: list[str] = []
    seen: set[str] = set()
    for link in related_links:
        if link not in seen:
            seen.add(link)
            unique_related.append(link)

    related_block = "\n".join(f"- {link}" for link in unique_related) or "- [[Unknown]]"

    return (
        f"{_obsidian_frontmatter(project_name, moment)}\n"
        f"# Session: [[{project_link}]]\n\n"
        "## Related\n\n"
        f"{related_block}\n\n"
        "## Summary\n\n"
        f"{summary.strip()}\n\n"
        "---\n"
        "**Auto-generated by agent-mem • Obsidian mode**\n"
    )


def _active_context_frontmatter(project_name: str, moment: datetime) -> str:
    updated = moment.isoformat(timespec="seconds")
    return (
        "---\n"
        f'title: "Active Context - {project_name}"\n'
        f'project: "{project_name}"\n'
        'type: "agent-active-context"\n'
        f'updated: "{updated}"\n'
        "tags:\n"
        "  - agent-mem\n"
        "  - active-context\n"
        "---\n"
    )


def _active_context_body(project_name: str, summary: str, moment: datetime) -> str:
    sections = _collect_active_sections(summary)
    project_link = _wiki_label(project_name)

    def _render_bullets(items: list[str]) -> str:
        if not items:
            return "- None recorded"
        return "\n".join(f"- {item}" for item in items)

    file_lines = _render_bullets([f"[[File - {item}]]" for item in sections["files"]])
    decision_lines = _render_bullets([f"[[Decision - {_wiki_label(item)}]]" for item in sections["decisions"]])
    blocker_lines = _render_bullets([f"[[Task - {_wiki_label(item)}]]" for item in sections["blockers"]])
    next_step_lines = _render_bullets(sections["next_steps"])

    return (
        f"{_active_context_frontmatter(project_name, moment)}\n"
        f"# Active Context: [[{project_link}]]\n\n"
        f"Last updated: {moment.strftime('%Y-%m-%d %H:%M %Z')}\n\n"
        "## Current Goal\n\n"
        f"{sections['goal']}\n\n"
        "## Active Decisions\n\n"
        f"{decision_lines}\n\n"
        "## Active Files\n\n"
        f"{file_lines}\n\n"
        "## Open Tasks or Blockers\n\n"
        f"{blocker_lines}\n\n"
        "## Next Prioritized Steps\n\n"
        f"{next_step_lines}\n"
    )


def _fallback_active_context_body(project_name: str, summary: str, moment: datetime) -> str:
    sections = _collect_active_sections(summary)

    def _render_bullets(items: list[str]) -> str:
        if not items:
            return "- None recorded"
        return "\n".join(f"- {item}" for item in items)

    return (
        "# Active Context\n\n"
        f"Project: {project_name}\n"
        f"Last updated: {moment.strftime('%Y-%m-%d %H:%M %Z')}\n\n"
        "## Current Goal\n\n"
        f"{sections['goal']}\n\n"
        "## Active Decisions\n\n"
        f"{_render_bullets(sections['decisions'])}\n\n"
        "## Active Files\n\n"
        f"{_render_bullets(sections['files'])}\n\n"
        "## Open Tasks or Blockers\n\n"
        f"{_render_bullets(sections['blockers'])}\n\n"
        "## Next Prioritized Steps\n\n"
        f"{_render_bullets(sections['next_steps'])}\n"
    )


def _obsidian_index_path(project_root: Path | None = None) -> Path:
    return get_memory_dir(project_root) / OBSIDIAN_INDEX_NAME


def _update_obsidian_index(project_name: str, session_note_name: str, project_root: Path | None = None):
    index_path = _obsidian_index_path(project_root)
    project_link = _wiki_label(project_name)
    content = (
        "# Agent-Mem Index\n\n"
        f"## Project\n\n- [[{project_link}]]\n\n"
        f"## Active Context\n\n- [[{OBSIDIAN_ACTIVE_NAME.removesuffix('.md')}]]\n\n"
        "## Recent Sessions\n\n"
    )

    existing_links: list[str] = []
    if index_path.exists():
        existing_links = [
            line.strip()[2:]
            for line in index_path.read_text(encoding="utf-8").splitlines()
            if line.strip().startswith("- [[") and line.strip().endswith("]]")
        ]

    new_session_link = f"[[{session_note_name.removesuffix('.md')}]]"
    ordered_links = [new_session_link]
    for link in existing_links:
        if link != new_session_link and link != f"[[{project_link}]]":
            ordered_links.append(link)

    content += "\n".join(f"- {link}" for link in ordered_links[:25]) + "\n"
    index_path.write_text(content, encoding="utf-8")


def initialize_storage(project_root: Path | None = None) -> list[Path]:
    created: list[Path] = []
    resolved_project_root = (project_root or Path.cwd()).resolve()
    project_name = resolved_project_root.name
    memory_dir = get_memory_dir(resolved_project_root)

    if is_obsidian_enabled():
        index_path = _obsidian_index_path(resolved_project_root)
        if not index_path.exists():
            index_path.write_text("# Agent-Mem Index\n\n## Recent Sessions\n\n", encoding="utf-8")
            created.append(index_path)
        active_context_path = get_active_context_file(resolved_project_root)
        if not active_context_path.exists():
            active_context_path.write_text(
                _active_context_body(
                    project_name,
                    "## Goal\n\nInitialize active context.\n\n## Outcome\n\nStorage created.\n\n## Key decisions\n\n- Active context will be updated by checkpoint, summarize, and watch.\n\n## Files changed\n\n- None yet.\n\n## Open tasks or blockers\n\n- Save the first real checkpoint.\n\n## Next prioritized steps\n\n- Run agent-mem checkpoint or agent-mem summarize after meaningful work.",
                    _timestamp(),
                ),
                encoding="utf-8",
            )
            created.append(active_context_path)
        return created

    fallback_file = get_fallback_memory_file(resolved_project_root)
    if not fallback_file.exists():
        fallback_file.write_text("# Agent Memory\n\n", encoding="utf-8")
        created.append(fallback_file)
    active_context_path = get_active_context_file(resolved_project_root)
    if not active_context_path.exists():
        active_context_path.write_text(
            f"# Active Context\n\nProject: {project_name}\nLast updated: never\n\n## Current Goal\n\nInitialize active context.\n\n## Active Decisions\n\n- Active context will be updated by checkpoint, summarize, and watch.\n\n## Active Files\n\n- None recorded\n\n## Open Tasks or Blockers\n\n- Save the first real checkpoint.\n\n## Next Prioritized Steps\n\n- Run agent-mem checkpoint or agent-mem summarize after meaningful work.\n",
            encoding="utf-8",
        )
        created.append(active_context_path)
    return created


def write_active_context(project_name: str, summary: str, project_root: Path | None = None) -> str:
    resolved_project_root = (project_root or Path.cwd()).resolve()
    filepath = get_active_context_file(resolved_project_root)
    moment = _timestamp()

    if is_obsidian_enabled():
        content = _active_context_body(project_name, summary, moment)
        filepath.write_text(content, encoding="utf-8")
        vault = Path(get_config()["obsidian_vault"])
        return str(filepath.relative_to(vault))

    content = _fallback_active_context_body(project_name, summary, moment)
    filepath.write_text(content, encoding="utf-8")
    return str(filepath.relative_to(resolved_project_root))


def read_active_context(project_root: Path | None = None) -> str:
    filepath = get_active_context_file(project_root)
    if not filepath.exists():
        return ""
    return filepath.read_text(encoding="utf-8").strip()


def prepare_next_prompt(project_name: str, project_root: Path | None = None) -> str:
    resolved_project_root = (project_root or Path.cwd()).resolve()
    active_context = read_active_context(resolved_project_root)
    if not active_context:
        return (
            "No active context exists yet.\n\n"
            f"Project: {project_name}\n"
            "Recommended next step: run `agent-mem checkpoint` or `agent-mem summarize` first."
        )

    return (
        "# Fresh Chat Starter\n\n"
        "Use the following saved active context before planning new work.\n\n"
        f"{active_context}\n\n"
        "## Instruction\n\n"
        "Continue from this state. Prefer these saved decisions over stale chat history, and update active context again after the next meaningful milestone.\n"
    )


def _score_line(line: str, query: str) -> int:
    line_lower = line.lower()
    query_lower = query.lower().strip()
    if not query_lower:
        return 0

    score = 0
    for word in query_lower.split():
        if word and word in line_lower:
            score += 2
    if query_lower in line_lower:
        score += 5
    return score


def _scored_excerpt(content: str, query: str, limit: int = 12) -> list[str]:
    lines = [line.strip() for line in content.splitlines() if line.strip()]
    scored = sorted(
        ((line, _score_line(line, query)) for line in lines),
        key=lambda item: item[1],
        reverse=True,
    )
    matches = [line for line, score in scored if score > 0][:limit]
    if matches:
        return matches
    return [content[:800].strip()] if content.strip() else []


def _session_block(project_name: str, summary: str) -> str:
    timestamp = _timestamp().strftime("%Y-%m-%d %H:%M")
    return f"""## Session Summary - {timestamp}

Project: {project_name}

{summary}

---
**Auto-generated by agent-mem**
"""


def write_session_summary(project_name: str, summary: str, project_root: Path | None = None) -> str:
    resolved_project_root = (project_root or Path.cwd()).resolve()
    memory_dir = get_memory_dir(resolved_project_root)
    moment = _timestamp()
    write_active_context(project_name, summary, resolved_project_root)

    if is_obsidian_enabled():
        session_name = _session_note_name(project_name, moment)
        filepath = memory_dir / session_name
        content = _obsidian_note(project_name, summary, moment)
        filepath.write_text(content, encoding="utf-8")
        _update_obsidian_index(project_name, session_name, resolved_project_root)
        vault = Path(get_config()["obsidian_vault"])
        return str(filepath.relative_to(vault))

    filepath = get_fallback_memory_file(resolved_project_root)
    entry = _session_block(project_name, summary).strip() + "\n"
    if filepath.exists():
        filepath.write_text(filepath.read_text(encoding="utf-8") + "\n" + entry, encoding="utf-8")
    else:
        filepath.write_text("# Agent Memory\n\n" + entry, encoding="utf-8")
    return str(filepath.relative_to(resolved_project_root))


def list_recent_session_files(
    project_name: str,
    count: int = 3,
    project_root: Path | None = None,
) -> list[Path]:
    resolved_project_root = (project_root or Path.cwd()).resolve()
    if is_obsidian_enabled():
        memory_dir = get_memory_dir(resolved_project_root)
        files = sorted(
            memory_dir.glob(f"{project_name}*.md"),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )
        return files[:count]

    fallback_file = get_fallback_memory_file(resolved_project_root)
    return [fallback_file] if fallback_file.exists() else []


def recall_memory(
    project_name: str,
    query: str,
    count: int = 5,
    project_root: Path | None = None,
) -> str:
    resolved_project_root = (project_root or Path.cwd()).resolve()
    active_context = read_active_context(resolved_project_root)
    files = list_recent_session_files(project_name, count=count, project_root=resolved_project_root)

    if not active_context and not files:
        return "No memory yet for this project. Start by saving a session summary."

    mode = "Obsidian" if is_obsidian_enabled() else "Local memory.md"
    result = [f"## Latest Memory ({mode})"]
    if active_context:
        matches = _scored_excerpt(active_context, query, limit=12)
        result.append(f"### {get_active_context_file(resolved_project_root).name}")
        result.extend(matches or [active_context[:800].strip()])
        result.append("")
    for file_path in files:
        content = file_path.read_text(encoding="utf-8")
        matches = _scored_excerpt(content, query, limit=12)
        result.append(f"### {file_path.name}")
        if matches:
            result.extend(matches)
        result.append("")

    return "\n".join(result)[:6000]
