from __future__ import annotations

import importlib
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    tomllib = importlib.import_module("tomllib")
else:  # pragma: no cover
    tomllib = importlib.import_module("tomli")

CONFIG_DIR = Path.home() / ".config" / "agent-mem"
CONFIG_FILE = CONFIG_DIR / "config.toml"
DEFAULT_CONFIG = {"use_obsidian": False, "obsidian_vault": None}


def _normalize_config(config: dict) -> dict:
    normalized = dict(DEFAULT_CONFIG)
    normalized.update(config)

    use_obsidian = normalized.get("use_obsidian")
    if isinstance(use_obsidian, str):
        normalized["use_obsidian"] = use_obsidian.lower() in {"1", "true", "yes", "y"}

    vault = normalized.get("obsidian_vault")
    if isinstance(vault, str) and not vault.strip():
        normalized["obsidian_vault"] = None

    if not normalized.get("obsidian_vault"):
        normalized["use_obsidian"] = False

    return normalized


def _serialize_toml(config: dict) -> str:
    lines = []
    for key, value in config.items():
        if value is None:
            value_repr = '""'
        elif isinstance(value, bool):
            value_repr = "true" if value else "false"
        elif isinstance(value, (int, float)):
            value_repr = str(value)
        else:
            escaped = str(value).replace("\\", "\\\\").replace('"', '\\"')
            value_repr = f'"{escaped}"'
        lines.append(f"{key} = {value_repr}")
    return "\n".join(lines) + "\n"


def get_config() -> dict:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if not CONFIG_FILE.exists():
        return dict(DEFAULT_CONFIG)

    with open(CONFIG_FILE, "rb") as file:
        loaded = tomllib.load(file)
    return _normalize_config(loaded)

def save_config(config: dict):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(_serialize_toml(_normalize_config(config)), encoding="utf-8")