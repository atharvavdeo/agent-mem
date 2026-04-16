from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import json
import re
from typing import Any

from .config import get_config, get_groq_api_key
from .memory import initialize_storage, write_session_summary

try:
    import yaml  # type: ignore
except Exception:  # pragma: no cover - dependency guard
    yaml = None


SUPPORTED_SOURCES = ("cursor", "claude", "opencode", "antigravity")
MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024
MAX_SCAN_FILES_PER_SOURCE = 350


@dataclass
class ChatMessage:
    role: str
    content: str
    timestamp: str | None = None


@dataclass
class ChatSession:
    source: str
    session_id: str
    title: str
    origin_path: str
    workspace_hint: str | None = None
    started_at: str | None = None
    ended_at: str | None = None
    messages: list[ChatMessage] = field(default_factory=list)


@dataclass
class ExtractionReport:
    source: str
    sessions: list[ChatSession] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class MigrationResult:
    sources: list[str]
    project_root: Path
    summary: str
    sessions: list[ChatSession] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    saved_summary_path: str | None = None
    backup_path: str | None = None
    handoff_prompt: str | None = None


class ContextExtractor:
    def __init__(self, project_root: Path, max_sessions: int = 20, max_messages: int = 400):
        self.project_root = project_root.resolve()
        self.max_sessions = max_sessions
        self.max_messages = max_messages
        self.project_name = self.project_root.name.lower()

    def extract(self, source: str) -> ExtractionReport:
        normalized = source.strip().lower()
        if normalized == "claude-vscode":
            normalized = "claude"

        if normalized == "cursor":
            return self.extract_cursor()
        if normalized == "claude":
            return self.extract_claude_vscode()
        if normalized == "opencode":
            return self.extract_opencode()
        if normalized == "antigravity":
            return self.extract_antigravity()

        return ExtractionReport(
            source=normalized,
            warnings=[f"Unsupported source '{source}'. Supported sources: {', '.join(SUPPORTED_SOURCES)}."],
        )

    def extract_cursor(self) -> ExtractionReport:
        roots = [
            self.project_root / ".cursor",
            Path.home() / "Library" / "Application Support" / "Cursor" / "User" / "workspaceStorage",
        ]
        return self._extract_from_roots("cursor", roots)

    def extract_claude_vscode(self) -> ExtractionReport:
        roots = [
            self.project_root / ".claude",
            self.project_root / ".vscode",
            Path.home() / "Library" / "Application Support" / "Code" / "User" / "workspaceStorage",
        ]
        return self._extract_from_roots("claude", roots)

    def extract_opencode(self) -> ExtractionReport:
        roots = [
            self.project_root / ".opencode",
            Path.home() / ".config" / "opencode",
            Path.home() / "Library" / "Application Support" / "OpenCode",
        ]
        return self._extract_from_roots("opencode", roots)

    def extract_antigravity(self) -> ExtractionReport:
        roots = [
            self.project_root / ".antigravity",
            Path.home() / ".config" / "antigravity",
            Path.home() / "Library" / "Application Support" / "Antigravity",
        ]
        report = self._extract_from_roots("antigravity", roots)
        if not report.sessions:
            report.warnings.append(
                "No Antigravity chat transcript files found. This source is best-effort and depends on local export/storage format."
            )
        return report

    def _extract_from_roots(self, source: str, roots: list[Path]) -> ExtractionReport:
        report = ExtractionReport(source=source)
        candidate_files = self._collect_candidate_files(source, roots)
        if not candidate_files:
            report.warnings.append(
                f"No transcript candidates found for {source}."
            )
            return report

        sessions: list[ChatSession] = []
        for path in candidate_files:
            parsed = self._parse_file_to_session(source, path)
            if parsed is None:
                continue
            sessions.append(parsed)

        sessions = self._dedupe_and_rank_sessions(sessions)
        report.sessions = sessions[: self.max_sessions]
        if len(sessions) > self.max_sessions:
            report.warnings.append(
                f"Limited {source} extraction to latest {self.max_sessions} sessions."
            )

        if not report.sessions:
            report.warnings.append(
                f"Candidates found for {source}, but none contained recognizable chat messages."
            )
        return report

    def _collect_candidate_files(self, source: str, roots: list[Path]) -> list[Path]:
        patterns = ("**/*.json", "**/*.jsonl", "**/*.md", "**/*.markdown", "**/*.txt", "**/*.yaml", "**/*.yml")
        candidates: list[tuple[float, int, Path]] = []

        for root in roots:
            if not root.exists() or not root.is_dir():
                continue

            for pattern in patterns:
                try:
                    for path in root.glob(pattern):
                        if not path.is_file():
                            continue
                        try:
                            size = path.stat().st_size
                            mtime = path.stat().st_mtime
                        except OSError:
                            continue
                        if size <= 0 or size > MAX_FILE_SIZE_BYTES:
                            continue

                        score = self._candidate_score(path, source)
                        if score <= 0:
                            continue

                        candidates.append((mtime, score, path))
                except OSError:
                    continue

        candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)

        selected: list[Path] = []
        seen: set[str] = set()
        for _, _, path in candidates:
            key = str(path)
            if key in seen:
                continue
            seen.add(key)
            selected.append(path)
            if len(selected) >= MAX_SCAN_FILES_PER_SOURCE:
                break

        return selected

    def _candidate_score(self, path: Path, source: str) -> int:
        text = str(path).lower()
        name = path.name.lower()
        score = 0

        source_tokens = {
            "cursor": ("cursor",),
            "claude": ("claude", "vscode", "code"),
            "opencode": ("opencode",),
            "antigravity": ("antigravity",),
        }.get(source, (source,))

        for token in source_tokens:
            if token in text:
                score += 5

        for token in ("chat", "conversation", "history", "session", "transcript", "messages"):
            if token in text:
                score += 3

        if "workspacestorage" in text:
            score += 2
        if self.project_name and self.project_name in text:
            score += 3
        if name in {"state.json", "storage.json", "history.json"}:
            score += 1

        return score

    def _parse_file_to_session(self, source: str, path: Path) -> ChatSession | None:
        content = self._safe_read(path)
        if not content.strip():
            return None

        suffix = path.suffix.lower()
        messages: list[ChatMessage]
        if suffix in {".json", ".jsonl"}:
            messages = self._parse_json_payload(content)
        elif suffix in {".yaml", ".yml"}:
            messages = self._parse_yaml_payload(content)
        else:
            messages = self._parse_markdown_or_text(content)

        messages = [m for m in messages if m.content.strip()][: self.max_messages]
        if len(messages) < 2:
            return None

        title = self._session_title(messages)
        started_at = self._normalize_timestamp(messages[0].timestamp)
        ended_at = self._normalize_timestamp(messages[-1].timestamp)

        session_id = f"{source}-{path.stem}-{abs(hash(str(path))) % 1000000}"
        return ChatSession(
            source=source,
            session_id=session_id,
            title=title,
            origin_path=str(path),
            workspace_hint=self.project_root.name,
            started_at=started_at,
            ended_at=ended_at,
            messages=messages,
        )

    def _safe_read(self, path: Path) -> str:
        try:
            return path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            return ""

    def _parse_json_payload(self, content: str) -> list[ChatMessage]:
        messages: list[ChatMessage] = []
        if content.strip().startswith("{") or content.strip().startswith("["):
            try:
                loaded = json.loads(content)
                messages.extend(self._collect_messages_from_data(loaded))
                return messages
            except json.JSONDecodeError:
                pass

        for line in content.splitlines():
            line = line.strip()
            if not line:
                continue
            try:
                loaded = json.loads(line)
            except json.JSONDecodeError:
                continue
            messages.extend(self._collect_messages_from_data(loaded))
        return messages

    def _parse_yaml_payload(self, content: str) -> list[ChatMessage]:
        if yaml is None:
            return []
        try:
            loaded = yaml.safe_load(content)
        except Exception:
            return []
        return self._collect_messages_from_data(loaded)

    def _parse_markdown_or_text(self, content: str) -> list[ChatMessage]:
        messages: list[ChatMessage] = []
        current_role = ""
        current_lines: list[str] = []

        def flush_current():
            nonlocal current_role, current_lines
            if current_role and current_lines:
                text = "\n".join(current_lines).strip()
                if text:
                    messages.append(ChatMessage(role=current_role, content=text))
            current_role = ""
            current_lines = []

        role_line = re.compile(r"^\s*(user|assistant|system|tool)\s*[:\-]\s*(.*)$", re.IGNORECASE)
        heading_line = re.compile(r"^\s{0,3}#{1,6}\s*(user|assistant|system|tool)\s*$", re.IGNORECASE)

        for raw in content.splitlines():
            role_match = role_line.match(raw)
            if role_match:
                flush_current()
                current_role = self._normalize_role(role_match.group(1))
                current_lines = [role_match.group(2).strip()] if role_match.group(2).strip() else []
                continue

            heading_match = heading_line.match(raw)
            if heading_match:
                flush_current()
                current_role = self._normalize_role(heading_match.group(1))
                current_lines = []
                continue

            if current_role:
                current_lines.append(raw.rstrip())

        flush_current()
        return messages

    def _collect_messages_from_data(self, data: Any) -> list[ChatMessage]:
        messages: list[ChatMessage] = []

        if isinstance(data, list):
            for item in data:
                messages.extend(self._collect_messages_from_data(item))
            return messages

        if isinstance(data, dict):
            for key in ("messages", "conversation", "chat", "history", "transcript", "entries", "turns", "items"):
                value = data.get(key)
                if isinstance(value, (list, dict)):
                    messages.extend(self._collect_messages_from_data(value))

            msg = self._message_from_object(data)
            if msg is not None:
                messages.append(msg)
                return messages

            for value in data.values():
                if isinstance(value, (list, dict)):
                    messages.extend(self._collect_messages_from_data(value))

        return messages

    def _message_from_object(self, obj: dict[str, Any]) -> ChatMessage | None:
        role = self._extract_role(obj)
        content = self._extract_content(obj)
        if not role or not content:
            return None

        timestamp = obj.get("timestamp") or obj.get("time") or obj.get("createdAt") or obj.get("created_at")
        return ChatMessage(role=role, content=content, timestamp=self._normalize_timestamp(timestamp))

    def _extract_role(self, obj: dict[str, Any]) -> str:
        candidates = [
            obj.get("role"),
            obj.get("speaker"),
            obj.get("author"),
            obj.get("type"),
            obj.get("from"),
            obj.get("sender"),
        ]
        for item in candidates:
            if isinstance(item, str) and item.strip():
                normalized = self._normalize_role(item)
                if normalized in {"user", "assistant", "system", "tool"}:
                    return normalized

        # Some formats store author as nested metadata.
        author = obj.get("author")
        if isinstance(author, dict):
            for key in ("role", "name", "type"):
                value = author.get(key)
                if isinstance(value, str):
                    normalized = self._normalize_role(value)
                    if normalized in {"user", "assistant", "system", "tool"}:
                        return normalized

        return ""

    def _extract_content(self, obj: dict[str, Any]) -> str:
        for key in ("content", "text", "message", "body", "value"):
            value = obj.get(key)
            flattened = self._flatten_text(value)
            if flattened:
                return flattened

        parts = obj.get("parts")
        flattened_parts = self._flatten_text(parts)
        if flattened_parts:
            return flattened_parts

        return ""

    def _flatten_text(self, value: Any) -> str:
        if value is None:
            return ""
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, (int, float, bool)):
            return str(value)
        if isinstance(value, list):
            parts = [self._flatten_text(item) for item in value]
            return "\n".join(part for part in parts if part).strip()
        if isinstance(value, dict):
            if "text" in value and isinstance(value["text"], str):
                return value["text"].strip()
            if "content" in value:
                return self._flatten_text(value["content"])
            flattened = [self._flatten_text(item) for item in value.values()]
            return "\n".join(part for part in flattened if part).strip()
        return ""

    def _normalize_role(self, role: str) -> str:
        lowered = role.strip().lower()
        if lowered in {"assistant", "ai", "model", "bot", "claude"}:
            return "assistant"
        if lowered in {"user", "human", "me", "you"}:
            return "user"
        if lowered in {"system", "instruction"}:
            return "system"
        if lowered in {"tool", "function", "plugin"}:
            return "tool"
        return lowered

    def _normalize_timestamp(self, value: Any) -> str | None:
        if value is None:
            return None

        if isinstance(value, (int, float)):
            # Heuristic for epoch milliseconds.
            if value > 10_000_000_000:
                value = value / 1000.0
            try:
                return datetime.fromtimestamp(value, tz=timezone.utc).isoformat(timespec="seconds")
            except Exception:
                return None

        if isinstance(value, str):
            text = value.strip()
            if not text:
                return None
            # Normalize trailing Z for Python's fromisoformat.
            if text.endswith("Z"):
                text = text[:-1] + "+00:00"
            try:
                return datetime.fromisoformat(text).isoformat(timespec="seconds")
            except ValueError:
                return value.strip()

        return None

    def _session_title(self, messages: list[ChatMessage]) -> str:
        for message in messages:
            if message.role == "user" and message.content.strip():
                return self._truncate(message.content.strip().replace("\n", " "), 80)
        return f"Recovered {messages[0].role} conversation"

    def _truncate(self, value: str, limit: int) -> str:
        if len(value) <= limit:
            return value
        return value[: max(1, limit - 3)].rstrip() + "..."

    def _dedupe_and_rank_sessions(self, sessions: list[ChatSession]) -> list[ChatSession]:
        deduped: list[ChatSession] = []
        seen: set[str] = set()
        for session in sessions:
            first = session.messages[0].content if session.messages else ""
            last = session.messages[-1].content if session.messages else ""
            fingerprint = f"{session.source}|{len(session.messages)}|{first[:80]}|{last[:80]}"
            if fingerprint in seen:
                continue
            seen.add(fingerprint)
            deduped.append(session)

        return sorted(
            deduped,
            key=lambda item: (item.ended_at or "", len(item.messages)),
            reverse=True,
        )


class ContextMigrator:
    def __init__(
        self,
        project_root: Path,
        project_name: str,
        dry_run: bool = False,
        max_sessions: int = 20,
        max_messages: int = 400,
    ):
        self.project_root = project_root.resolve()
        self.project_name = project_name
        self.dry_run = dry_run
        self.extractor = ContextExtractor(
            project_root=self.project_root,
            max_sessions=max_sessions,
            max_messages=max_messages,
        )

    def run(
        self,
        sources: list[str],
        full: bool,
        extract_only: bool,
    ) -> MigrationResult:
        normalized_sources = self._normalize_sources(sources)
        if not normalized_sources:
            raise ValueError("At least one migration source must be provided.")

        sessions: list[ChatSession] = []
        warnings: list[str] = []
        for source in normalized_sources:
            report = self.extractor.extract(source)
            sessions.extend(report.sessions)
            warnings.extend(report.warnings)

        summary = self._build_summary(normalized_sources, sessions, warnings)
        result = MigrationResult(
            sources=normalized_sources,
            project_root=self.project_root,
            sessions=sessions,
            warnings=warnings,
            summary=summary,
        )

        if self.dry_run:
            return result

        if full:
            initialize_storage(self.project_root)
            result.saved_summary_path = write_session_summary(
                self.project_name,
                summary,
                project_root=self.project_root,
            )
            result.handoff_prompt = self.generate_handoff_prompt(summary, sessions)

        if extract_only or full:
            result.backup_path = self.export_markdown_backup(
                sources=normalized_sources,
                sessions=sessions,
                summary=summary,
                handoff_prompt=result.handoff_prompt,
            )

        return result

    def _normalize_sources(self, sources: list[str]) -> list[str]:
        normalized: list[str] = []
        seen: set[str] = set()
        for source in sources:
            value = source.strip().lower()
            if value == "all":
                for item in ("cursor", "claude", "opencode"):
                    if item not in seen:
                        seen.add(item)
                        normalized.append(item)
                continue
            if value == "claude-vscode":
                value = "claude"
            if value not in SUPPORTED_SOURCES:
                continue
            if value not in seen:
                seen.add(value)
                normalized.append(value)
        return normalized

    def _build_summary(
        self,
        sources: list[str],
        sessions: list[ChatSession],
        warnings: list[str],
    ) -> str:
        total_messages = sum(len(session.messages) for session in sessions)
        files_mentioned = self._extract_file_mentions(sessions)
        decision_points = self._extract_decisions(sessions)
        blockers = self._extract_blockers(sessions)

        outcome_lines = [
            f"- Extracted {len(sessions)} session(s) and {total_messages} message(s) from: {', '.join(sources)}.",
            f"- Project root for migration: {self.project_root}",
        ]
        if warnings:
            outcome_lines.append(f"- Extraction warnings: {len(warnings)} (see migrate output).")

        decision_lines = decision_points or [
            "- Preserve only high-signal context from recovered chats.",
            "- Reuse existing agent-mem summary format for consistency.",
            "- Keep migration output portable through markdown backups.",
        ]

        files_lines = [f"- {item}" for item in files_mentioned] if files_mentioned else [
            "- No explicit file paths were detected in extracted chats.",
        ]

        blocker_lines = blockers or [
            "- Validate extracted transcripts before relying on historical decisions.",
        ]

        next_steps = [
            "- Paste the generated handoff prompt into your current IDE chat (full mode).",
            "- Start a fresh chat using the starter block produced by the IDE agent.",
            "- Re-run `agent-mem migrate --dry-run` after major sessions to verify extraction quality.",
        ]

        return (
            "## Goal\n\n"
            "- Migrate useful IDE chat context into agent-mem memory for reliable session continuity.\n\n"
            "## Outcome\n\n"
            + "\n".join(outcome_lines)
            + "\n\n## Key decisions\n\n"
            + "\n".join(decision_lines)
            + "\n\n## Files changed\n\n"
            + "\n".join(files_lines)
            + "\n\n## Open tasks or blockers\n\n"
            + "\n".join(blocker_lines)
            + "\n\n## Next prioritized steps\n\n"
            + "\n".join(next_steps)
            + "\n"
        )

    def _extract_file_mentions(self, sessions: list[ChatSession]) -> list[str]:
        pattern = re.compile(r"(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+\.[A-Za-z0-9_]+")
        found: list[str] = []
        seen: set[str] = set()
        for session in sessions:
            for message in session.messages:
                for match in pattern.findall(message.content):
                    if len(match) > 200:
                        continue
                    if match in seen:
                        continue
                    seen.add(match)
                    found.append(match)
                    if len(found) >= 12:
                        return found
        return found

    def _extract_decisions(self, sessions: list[ChatSession]) -> list[str]:
        signals = ("decide", "decision", "use", "prefer", "implement", "migrate", "keep", "avoid")
        candidates: list[str] = []
        for session in sessions:
            for message in session.messages:
                if message.role != "assistant":
                    continue
                line = self._first_nonempty_line(message.content)
                if not line:
                    continue
                lowered = line.lower()
                if any(token in lowered for token in signals):
                    candidates.append(f"- {self._truncate(line, 140)}")
        return self._dedupe_bullets(candidates, limit=6)

    def _extract_blockers(self, sessions: list[ChatSession]) -> list[str]:
        signals = ("block", "blocked", "todo", "next", "follow-up", "remaining", "pending", "error")
        candidates: list[str] = []
        for session in sessions:
            for message in session.messages:
                line = self._first_nonempty_line(message.content)
                if not line:
                    continue
                lowered = line.lower()
                if any(token in lowered for token in signals):
                    if lowered in {"is there an error", "any error", "error?", "is there error"}:
                        continue
                    if len(line) < 24 and not any(token in lowered for token in ("todo", "block", "pending")):
                        continue
                    candidates.append(f"- {self._truncate(line, 140)}")
        return self._dedupe_bullets(candidates, limit=6)

    def _dedupe_bullets(self, items: list[str], limit: int) -> list[str]:
        unique: list[str] = []
        seen: set[str] = set()
        for item in items:
            key = re.sub(r"\s+", " ", item.lower()).strip(" -:.\t")
            if not key or key in seen:
                continue
            seen.add(key)
            unique.append(item)
            if len(unique) >= limit:
                break
        return unique

    def _first_nonempty_line(self, text: str) -> str:
        for line in text.splitlines():
            stripped = line.strip(" -\t")
            if stripped:
                return stripped
        return ""

    def _truncate(self, value: str, limit: int) -> str:
        if len(value) <= limit:
            return value
        return value[: max(1, limit - 3)].rstrip() + "..."

    def generate_handoff_prompt(self, summary: str, sessions: list[ChatSession]) -> str:
        fallback_prompt = self._fallback_handoff_prompt(summary, sessions)

        api_key = get_groq_api_key()
        if not api_key:
            return fallback_prompt

        model = get_config().get("groq_model") or "llama-3.3-70b-versatile"
        try:
            from groq import Groq

            client = Groq(api_key=api_key)
            completion = client.chat.completions.create(
                model=model,
                temperature=0.2,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You generate strict migration handoff prompts for coding agents. "
                            "Return plain text only. Keep it concise, concrete, and imperative."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            "Improve this handoff prompt while keeping all required steps and structure:\n\n"
                            + fallback_prompt
                        ),
                    },
                ],
            )
            candidate = (completion.choices[0].message.content or "").strip()
            return candidate or fallback_prompt
        except Exception:
            return fallback_prompt

    def _fallback_handoff_prompt(self, summary: str, sessions: list[ChatSession]) -> str:
        latest_titles = [f"- {session.source}: {session.title}" for session in sessions[:5]]
        latest_title_block = "\n".join(latest_titles) if latest_titles else "- No named sessions recovered."

        return (
            "## Migration Handoff Prompt\n\n"
            "Paste this into your current IDE chat:\n\n"
            "```text\n"
            f"You are continuing work in project '{self.project_name}' at '{self.project_root}'.\n"
            "Treat this as a migration handoff and execute it before normal conversation.\n\n"
            "Execution protocol:\n"
            "1. Read saved memory in priority order (.agent-memory/active.md, then .agent-memory/memory.md, or Obsidian equivalent).\n"
            "2. Reconcile that memory with the migrated summary below.\n"
            "3. If migrated summary conflicts with repository files, explicitly call out the conflict and prefer repository state.\n"
            "4. Produce a fresh structured summary using exactly these sections:\n"
            "   - Goal\n"
            "   - Outcome\n"
            "   - Key decisions\n"
            "   - Files changed\n"
            "   - Open tasks or blockers\n"
            "   - Next prioritized steps\n"
            "5. Save that summary back to agent-mem memory using available tools/commands.\n"
            "6. Return output in this order:\n"
            "   A) Session sync complete (max 3 bullets)\n"
            "   B) Start fresh chat with this (compact starter block)\n"
            "Constraints:\n"
            "- Do not ask the user to restate previous context.\n"
            "- Do not skip unresolved blockers.\n"
            "- Keep the starter block under 150 words.\n\n"
            "Recent migrated sessions:\n"
            f"{latest_title_block}\n\n"
            "Migrated summary:\n"
            f"{summary.strip()}\n"
            "```\n"
        )

    def export_markdown_backup(
        self,
        sources: list[str],
        sessions: list[ChatSession],
        summary: str,
        handoff_prompt: str | None,
    ) -> str:
        backup_dir = self.project_root / ".agent-memory" / "migrations"
        backup_dir.mkdir(parents=True, exist_ok=True)

        stamp = datetime.now().astimezone().strftime("%Y-%m-%d_%H-%M")
        source_label = "-".join(sources) if sources else "unknown"
        backup_path = backup_dir / f"{stamp}-{source_label}.md"

        lines: list[str] = [
            "# agent-mem migration backup",
            "",
            f"- Generated: {datetime.now().astimezone().isoformat(timespec='seconds')}",
            f"- Project: {self.project_name}",
            f"- Project root: {self.project_root}",
            f"- Sources: {', '.join(sources)}",
            f"- Session count: {len(sessions)}",
            "",
            "## Compressed summary",
            "",
            summary.strip(),
            "",
        ]

        if handoff_prompt:
            lines.extend([
                "## Handoff prompt",
                "",
                handoff_prompt.strip(),
                "",
            ])

        lines.extend([
            "## Extracted sessions",
            "",
        ])

        if not sessions:
            lines.append("- No sessions were extracted.")
        else:
            for session in sessions:
                lines.extend([
                    f"### {session.source} :: {session.title}",
                    "",
                    f"- session_id: {session.session_id}",
                    f"- origin: {session.origin_path}",
                    f"- messages: {len(session.messages)}",
                    f"- started_at: {session.started_at or 'unknown'}",
                    f"- ended_at: {session.ended_at or 'unknown'}",
                    "",
                    "#### Transcript (truncated)",
                    "",
                ])
                for message in session.messages[:40]:
                    role = message.role.upper()
                    body = message.content.strip()
                    lines.append(f"**{role}:** {body}")
                    lines.append("")

        backup_path.write_text("\n".join(lines).strip() + "\n", encoding="utf-8")
        return str(backup_path.relative_to(self.project_root))
