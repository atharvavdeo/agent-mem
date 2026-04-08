from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
import re
import subprocess
import time
from typing import Callable

from .config import get_config, get_groq_api_key
from .memory import get_active_context_file, get_fallback_memory_file, get_handoff_outbox_file


DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"

IGNORED_PARTS = {
    ".git",
    ".agent-memory",
    ".cursor",
    ".claude",
    ".antigravity",
    ".opencode",
    ".vscode",
    "dist",
    "build",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".venv",
    "node_modules",
}


@dataclass
class WatchTrigger:
    project_root: Path
    project_name: str
    changed_files: list[str]
    quiet_seconds: int
    diff_lines: int
    diff_stat: str
    diff_excerpt: str
    active_context: str
    recent_memory: str


@dataclass
class WatchResult:
    prompt: str
    clipboard_ok: bool
    outbox_path: Path


@dataclass
class HandoffDigest:
    current_task: str
    key_decisions: list[str]
    changed_files: list[str]
    blockers: list[str]
    next_step: str
    context_window_risk: str


@dataclass
class WatchState:
    pending_changes: set[str] = field(default_factory=set)
    last_change_at: float | None = None


def _is_ignored(relative_path: Path) -> bool:
    return any(part in IGNORED_PARTS for part in relative_path.parts)


def _safe_read(path: Path, limit: int = 4000) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")[:limit].strip()


def _run_git(project_root: Path, args: list[str]) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=project_root,
            text=True,
            capture_output=True,
            timeout=15,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None


def git_diff_stat(project_root: Path) -> tuple[int, str]:
    proc = _run_git(project_root, ["diff", "--numstat"])
    if proc is None or proc.returncode != 0:
        return 0, "git diff unavailable"

    total_lines = 0
    lines: list[str] = []
    for raw in proc.stdout.splitlines():
        parts = raw.split("\t")
        if len(parts) != 3:
            continue
        added, deleted, path = parts
        try:
            added_int = 0 if added == "-" else int(added)
            deleted_int = 0 if deleted == "-" else int(deleted)
        except ValueError:
            continue
        total_lines += added_int + deleted_int
        lines.append(f"{path}: +{added_int} -{deleted_int}")
    return total_lines, "\n".join(lines[:40]) or "no diff lines detected"


def git_diff_excerpt(project_root: Path, changed_files: list[str], max_chars: int = 10000) -> str:
    if not changed_files:
        return "No changed files captured."

    proc = _run_git(project_root, ["diff", "--", *changed_files[:25]])
    if proc is None or proc.returncode != 0:
        return "git diff unavailable"
    text = proc.stdout.strip()
    if not text:
        return "git diff is empty"
    return text[:max_chars]


def build_trigger(
    project_root: Path,
    project_name: str,
    changed_files: list[str],
    quiet_seconds: int,
) -> WatchTrigger:
    diff_lines, diff_stat = git_diff_stat(project_root)
    diff_excerpt = git_diff_excerpt(project_root, changed_files)
    active_context = _safe_read(get_active_context_file(project_root), limit=5000)
    recent_memory = _safe_read(get_fallback_memory_file(project_root), limit=5000)
    return WatchTrigger(
        project_root=project_root,
        project_name=project_name,
        changed_files=changed_files,
        quiet_seconds=quiet_seconds,
        diff_lines=diff_lines,
        diff_stat=diff_stat,
        diff_excerpt=diff_excerpt,
        active_context=active_context,
        recent_memory=recent_memory,
    )


def _groq_client():
    from groq import Groq

    api_key = get_groq_api_key()
    if not api_key:
        raise RuntimeError(
            "Groq API key is not configured. Re-run `agent-mem init` or set GROQ_API_KEY."
        )
    return Groq(api_key=api_key)


def _extract_bullets(block: str) -> list[str]:
    items: list[str] = []
    for line in block.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            items.append(stripped[2:].strip())
    return items


def _extract_section(text: str, heading: str) -> str:
    pattern = rf"(?ms)^##\s+{re.escape(heading)}\s*\n(.*?)(?=^##\s+|\Z)"
    match = re.search(pattern, text)
    return match.group(1).strip() if match else ""


def _parse_digest(text: str, trigger: WatchTrigger) -> HandoffDigest:
    current_task = _extract_section(text, "Current Task") or "Continue the active implementation milestone."
    next_step = _extract_section(text, "Next Step") or "Summarize the current work and start a fresh chat."
    context_window_risk = _extract_section(text, "Context Window Risk") or "The active session has enough accumulated work that context should be compressed now."
    key_decisions = _extract_bullets(_extract_section(text, "Key Decisions"))[:6]
    changed_files = _extract_bullets(_extract_section(text, "Changed Files"))[:12]
    blockers = _extract_bullets(_extract_section(text, "Blockers"))[:6]

    if not changed_files:
        changed_files = trigger.changed_files[:12]

    return HandoffDigest(
        current_task=current_task.strip(),
        key_decisions=key_decisions,
        changed_files=changed_files,
        blockers=blockers,
        next_step=next_step.strip(),
        context_window_risk=context_window_risk.strip(),
    )


def _render_bullets(items: list[str], fallback: str) -> str:
    if not items:
        return f"- {fallback}"
    return "\n".join(f"- {item}" for item in items)


def _format_final_handoff_prompt(trigger: WatchTrigger, digest: HandoffDigest) -> str:
    changed_files_block = _render_bullets(digest.changed_files, "No concrete file list available.")
    decisions_block = _render_bullets(digest.key_decisions, "No stable decisions were extracted; infer only from verified code.")
    blockers_block = _render_bullets(digest.blockers, "No blockers captured.")

    return (
        "## Why You Are Seeing This\n\n"
        f"{digest.context_window_risk}\n\n"
        "## Paste This Into Your IDE Chat\n\n"
        "```text\n"
        f"You are in an active {trigger.project_name} coding session that needs immediate context compression.\n\n"
        "Treat this message as a high-priority handoff request generated by agent-mem watch.\n\n"
        "Your job right now:\n"
        "1. Summarize the current work accurately using the exact sections:\n"
        "   - Goal\n"
        "   - Outcome\n"
        "   - Key decisions\n"
        "   - Files changed\n"
        "   - Open tasks or blockers\n"
        "   - Next prioritized steps\n"
        "2. If agent-mem memory tools are available, save that summary immediately to agent memory / Obsidian.\n"
        "3. If the tools are not available, still produce the exact structured summary in chat.\n"
        "4. Then produce a separate fresh-chat starter block that is short, concrete, and sufficient to continue in a brand-new chat.\n"
        "5. Explicitly tell the user to start a fresh chat after the save/handoff is done.\n\n"
        "Use this verified context only. Do not hallucinate beyond it.\n\n"
        f"Current task:\n{digest.current_task}\n\n"
        "Key decisions already in play:\n"
        f"{decisions_block}\n\n"
        "Files most likely involved:\n"
        f"{changed_files_block}\n\n"
        "Open tasks or blockers:\n"
        f"{blockers_block}\n\n"
        f"Immediate next step after summarizing:\n- {digest.next_step}\n"
        "```"
    )


def generate_dry_run_prompt(trigger: WatchTrigger) -> str:
    digest = HandoffDigest(
        current_task="Compress the current session and preserve only the essential continuation state.",
        key_decisions=[
            "Use the current code and saved memory as the source of truth.",
            "Produce a structured summary before continuing any new implementation.",
        ],
        changed_files=trigger.changed_files[:12],
        blockers=["Watcher dry run: replace this with real blockers from the live session if any."],
        next_step="Save the structured summary, output a fresh-chat starter block, and tell the user to continue in a new chat.",
        context_window_risk="Dry run from agent-mem watch. This simulates the prompt you will receive when the watcher decides the current chat should be compressed.",
    )
    return _format_final_handoff_prompt(trigger, digest)


def generate_handoff_prompt(trigger: WatchTrigger) -> str:
    config = get_config()
    model = config.get("groq_model") or DEFAULT_GROQ_MODEL
    client = _groq_client()
    try:
        completion = client.chat.completions.create(
            model=model,
            temperature=0.1,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You compress active coding work into a strict structured digest for an IDE handoff generator. "
                        "Do not write a user-facing explanation. "
                        "Do not write a final prompt. "
                        "Return only markdown with exactly these sections in this order:\n"
                        "## Current Task\n"
                        "## Key Decisions\n"
                        "## Changed Files\n"
                        "## Blockers\n"
                        "## Next Step\n"
                        "## Context Window Risk\n\n"
                        "Rules:\n"
                        "- Use bullet lists for Key Decisions, Changed Files, and Blockers.\n"
                        "- Be factual and implementation-oriented.\n"
                        "- Keep each bullet short.\n"
                        "- Prefer file paths and explicit decisions over vague summaries.\n"
                        "- If something is unknown, say so briefly instead of inventing it."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"Project: {trigger.project_name}\n"
                        f"Quiet window after work: {trigger.quiet_seconds}s\n"
                        f"Changed files ({len(trigger.changed_files)}):\n- " + "\n- ".join(trigger.changed_files[:25]) + "\n\n"
                        f"Git diff total changed lines: {trigger.diff_lines}\n"
                        f"Git diff stats:\n{trigger.diff_stat}\n\n"
                        f"Current active context:\n{trigger.active_context or 'None'}\n\n"
                        f"Recent memory excerpt:\n{trigger.recent_memory or 'None'}\n\n"
                        f"Git diff excerpt:\n{trigger.diff_excerpt}\n\n"
                        "Return only the structured digest sections requested in the system message."
                    ),
                },
            ],
        )
    except Exception as exc:
        message = str(exc)
        lowered = message.lower()
        if "invalid api key" in lowered or "expired_api_key" in lowered or "401" in lowered:
            raise RuntimeError("Groq authentication failed. Check GROQ_API_KEY or run `agent-mem configure-groq` with a valid key.") from exc
        if "connection error" in lowered or "connecterror" in lowered or "timed out" in lowered:
            raise RuntimeError("Groq request failed due to a network problem. Retry when network access is available.") from exc
        raise RuntimeError(f"Groq handoff generation failed: {message}") from exc

    digest_text = (completion.choices[0].message.content or "").strip()
    digest = _parse_digest(digest_text, trigger)
    return _format_final_handoff_prompt(trigger, digest)


def write_handoff_outbox(project_root: Path, prompt: str) -> Path:
    outbox_path = get_handoff_outbox_file(project_root)
    outbox_path.write_text(prompt + "\n", encoding="utf-8")
    return outbox_path


def copy_to_clipboard(prompt: str) -> bool:
    try:
        import pyperclip

        pyperclip.copy(prompt)
        return True
    except Exception:
        return False


def render_alert(result: WatchResult, dry_run: bool) -> str:
    mode = "DRY RUN" if dry_run else "HANDOFF READY"
    clipboard = "yes" if result.clipboard_ok else "no"
    lines = [
        "=" * 72,
        f"AGENT-MEM {mode}",
        "",
        f"Clipboard updated : {clipboard}",
        f"Outbox file       : {result.outbox_path}",
        "",
        "Paste the copied prompt into your IDE chat now, let the agent summarize,",
        "save memory, and then start a fresh chat with the generated handoff block.",
        "=" * 72,
    ]
    return "\n".join(lines)


class _EventHandler:
    def __init__(self, project_root: Path, state: WatchState):
        from watchdog.events import FileSystemEventHandler

        class _Handler(FileSystemEventHandler):
            def on_any_event(self, event):
                if getattr(event, "is_directory", False):
                    return
                raw_path = getattr(event, "src_path", "")
                if not raw_path:
                    return
                try:
                    relative = Path(raw_path).resolve().relative_to(project_root)
                except Exception:
                    return
                if _is_ignored(relative):
                    return
                state.pending_changes.add(str(relative))
                state.last_change_at = time.time()

        self.handler = _Handler()


def run_watch_loop(
    project_root: Path,
    project_name: str,
    *,
    quiet_seconds: int,
    min_changes: int,
    min_diff_lines: int,
    once: bool,
    dry_run: bool,
    on_result: Callable[[WatchResult], None],
    emit: Callable[[str], None],
) -> None:
    # Polling is slower than native backends, but it is much more reliable across
    # temp folders, synced drives, and odd macOS filesystem setups.
    from watchdog.observers.polling import PollingObserver

    state = WatchState()
    observer = PollingObserver(timeout=1.0)
    handler = _EventHandler(project_root, state).handler
    observer.schedule(handler, str(project_root), recursive=True)
    observer.start()

    emit(f"Watching {project_root}")
    emit(f"Project name     : {project_name}")
    emit(f"Quiet threshold  : {quiet_seconds}s")
    emit(f"Min file changes : {min_changes}")
    emit(f"Min diff lines   : {min_diff_lines}")
    emit("Press Ctrl+C to stop.")

    try:
        while True:
            time.sleep(1.0)
            if not state.pending_changes or state.last_change_at is None:
                continue

            if (time.time() - state.last_change_at) < quiet_seconds:
                continue

            changed_files = sorted(state.pending_changes)
            trigger = build_trigger(project_root, project_name, changed_files, quiet_seconds)
            if len(changed_files) < min_changes and trigger.diff_lines < min_diff_lines:
                continue

            if dry_run:
                prompt = generate_dry_run_prompt(trigger)
            else:
                prompt = generate_handoff_prompt(trigger)

            outbox_path = write_handoff_outbox(project_root, prompt)
            clipboard_ok = copy_to_clipboard(prompt)
            result = WatchResult(prompt=prompt, clipboard_ok=clipboard_ok, outbox_path=outbox_path)
            on_result(result)

            state.pending_changes.clear()
            state.last_change_at = None

            if once:
                return
    finally:
        observer.stop()
        observer.join(timeout=5)
