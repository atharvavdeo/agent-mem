"""Textual-based terminal UI for agent-mem."""
from __future__ import annotations

import subprocess
from pathlib import Path

from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Container, Vertical, ScrollableContainer
from textual.widgets import (
    Button,
    Footer,
    Header,
    Input,
    Label,
    Markdown,
    Static,
    TabbedContent,
    TabPane,
)

from .config import get_config, get_groq_api_key
from .memory import (
    get_active_context_file,
    get_fallback_memory_file,
    is_obsidian_enabled,
    list_recent_session_files,
    recall_memory,
)


def _project_root() -> Path:
    return Path.cwd().resolve()


def _project_name() -> str:
    return _project_root().name


class StatusPanel(Static):
    """Shows storage mode, Groq status, and recent sessions."""

    DEFAULT_CSS = """
    StatusPanel {
        height: auto;
        padding: 1 2;
    }
    .status-row {
        height: 1;
        margin-bottom: 1;
    }
    .section-title {
        color: $accent;
        text-style: bold;
        margin-bottom: 1;
    }
    """

    def compose(self) -> ComposeResult:
        root = _project_root()
        project_name = _project_name()

        # Storage mode
        if is_obsidian_enabled():
            storage = "Obsidian vault"
        else:
            mem_file = get_fallback_memory_file(root)
            storage = f"Local fallback ({'.agent-memory/memory.md'})"
            if not mem_file.exists():
                storage += " [no file yet]"

        # Groq
        groq_key = get_groq_api_key()
        groq_status = "configured" if groq_key else "not configured (watch mode disabled)"

        # Active context
        active_file = get_active_context_file(root)
        active_status = "present" if active_file.exists() else "none"

        info_lines = [
            f"**Project:** {project_name}",
            f"**Root:** {root}",
            f"**Storage:** {storage}",
            f"**Groq API:** {groq_status}",
            f"**Active context:** {active_status}",
        ]

        # Recent sessions
        sessions = list_recent_session_files(project_name, count=5, project_root=root)
        if sessions:
            info_lines.append("")
            info_lines.append("**Recent sessions:**")
            for s in sessions:
                info_lines.append(f"- {s.name}")
        else:
            info_lines.append("")
            info_lines.append("*No sessions yet — run `agent-mem summarize` to create one.*")

        yield Markdown("\n".join(info_lines))


class MemoryPanel(Vertical):
    """Memory search and active context viewer."""

    DEFAULT_CSS = """
    MemoryPanel {
        height: 1fr;
        padding: 1 2;
    }
    #memory-input {
        margin-bottom: 1;
        dock: top;
    }
    #memory-output {
        height: 1fr;
        border: solid $accent;
        padding: 1;
    }
    """

    def compose(self) -> ComposeResult:
        yield Input(placeholder="Search memory (leave blank for active context)…", id="memory-input")
        yield Button("Search", id="memory-search-btn", variant="primary")
        yield ScrollableContainer(
            Markdown("*Press Search or Enter to load memory.*", id="memory-md"),
            id="memory-output",
        )

    def on_mount(self) -> None:
        self._load_active()

    def _load_active(self) -> None:
        root = _project_root()
        active_file = get_active_context_file(root)
        if active_file.exists():
            content = active_file.read_text(encoding="utf-8", errors="replace")
            self.query_one("#memory-md", Markdown).update(content)
        else:
            fallback = get_fallback_memory_file(root)
            if fallback.exists():
                content = fallback.read_text(encoding="utf-8", errors="replace")[-4000:]
                self.query_one("#memory-md", Markdown).update(content)
            else:
                self.query_one("#memory-md", Markdown).update("*No memory found. Run `agent-mem summarize` first.*")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "memory-search-btn":
            self._run_search()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._run_search()

    def _run_search(self) -> None:
        query = self.query_one("#memory-input", Input).value.strip()
        if not query:
            self._load_active()
            return
        root = _project_root()
        name = _project_name()
        try:
            result = recall_memory(name, query, count=5, project_root=root)
            self.query_one("#memory-md", Markdown).update(result or "*No results found.*")
        except Exception as exc:
            self.query_one("#memory-md", Markdown).update(f"*Error: {exc}*")


class BenchmarkPanel(Vertical):
    """Run and display graph benchmark output."""

    DEFAULT_CSS = """
    BenchmarkPanel {
        height: 1fr;
        padding: 1 2;
    }
    #bench-output {
        height: 1fr;
        border: solid $accent;
        padding: 1;
        overflow-y: scroll;
    }
    #bench-run-btn {
        margin-bottom: 1;
        dock: top;
    }
    """

    def compose(self) -> ComposeResult:
        yield Button("Run Benchmark", id="bench-run-btn", variant="primary")
        yield ScrollableContainer(
            Static("Press 'Run Benchmark' to execute agent-mem graph benchmark.", id="bench-output"),
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "bench-run-btn":
            self._run()

    def _run(self) -> None:
        output_widget = self.query_one("#bench-output", Static)
        output_widget.update("Running benchmark…")
        try:
            result = subprocess.run(
                ["agent-mem", "graph", "benchmark"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(_project_root()),
            )
            out = result.stdout + (("\n[stderr]\n" + result.stderr) if result.stderr else "")
            output_widget.update(out or "(no output)")
        except FileNotFoundError:
            output_widget.update("agent-mem not found in PATH. Install with: pip install -e .")
        except subprocess.TimeoutExpired:
            output_widget.update("Benchmark timed out after 60 seconds.")
        except Exception as exc:
            output_widget.update(f"Error: {exc}")


class AgentMemApp(App):
    """agent-mem terminal UI."""

    TITLE = "agent-mem"
    SUB_TITLE = f"project: {_project_name()}"
    CSS = """
    TabbedContent {
        height: 1fr;
    }
    TabPane {
        height: 1fr;
    }
    """
    BINDINGS = [
        Binding("q", "quit", "Quit"),
        Binding("r", "refresh", "Refresh"),
    ]

    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane("Status", id="tab-status"):
                yield ScrollableContainer(StatusPanel())
            with TabPane("Memory", id="tab-memory"):
                yield MemoryPanel()
            with TabPane("Benchmark", id="tab-benchmark"):
                yield BenchmarkPanel()
        yield Footer()

    def action_refresh(self) -> None:
        """Reload the status panel."""
        self.query_one(StatusPanel).remove()
        self.query_one("#tab-status ScrollableContainer").mount(StatusPanel())


def launch() -> None:
    """Entry point for `agent-mem tui`."""
    app = AgentMemApp()
    app.run()
