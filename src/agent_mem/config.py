from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

if sys.version_info >= (3, 11):
    tomllib = importlib.import_module("tomllib")
else:  # pragma: no cover
    tomllib = importlib.import_module("tomli")

def _config_dir() -> Path:
    override = os.environ.get("AGENT_MEM_CONFIG_DIR", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    return Path.home() / ".config" / "agent-mem"


def _config_file() -> Path:
    return _config_dir() / "config.toml"


DEFAULT_CONFIG = {
    "use_obsidian": False,
    "obsidian_vault": None,
    "groq_api_key": None,
    "groq_model": "openai/gpt-oss-120b",
    "llm_provider": "groq",
    "cerebras_api_key": None,
    "cerebras_model": "qwen-3.8-27b",
}


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

    api_key = normalized.get("groq_api_key")
    if isinstance(api_key, str) and not api_key.strip():
        normalized["groq_api_key"] = None

    model = normalized.get("groq_model")
    if isinstance(model, str) and not model.strip():
        normalized["groq_model"] = DEFAULT_CONFIG["groq_model"]

    for field in ("cerebras_api_key", "cerebras_model"):
        value = normalized.get(field)
        if isinstance(value, str):
            normalized[field] = value.strip() or DEFAULT_CONFIG[field]

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
    config_dir = _config_dir()
    config_file = _config_file()
    config_dir.mkdir(parents=True, exist_ok=True)
    if not config_file.exists():
        return dict(DEFAULT_CONFIG)

    with open(config_file, "rb") as file:
        loaded = tomllib.load(file)
    return _normalize_config(loaded)


def save_config(config: dict):
    config_dir = _config_dir()
    config_file = _config_file()
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file.write_text(_serialize_toml(_normalize_config(config)), encoding="utf-8")


def get_groq_api_key() -> str | None:
    env_key = os.environ.get("GROQ_API_KEY", "").strip()
    if env_key:
        return env_key
    return get_config().get("groq_api_key")


def get_llm_provider() -> str:
    provider = (os.environ.get("AGENT_MEM_LLM_PROVIDER") or get_config().get("llm_provider") or "groq").strip().lower()
    if provider not in {"groq", "cerebras"}:
        raise ValueError("llm_provider must be groq or cerebras")
    return provider


def get_llm_api_key(provider: str | None = None) -> str | None:
    provider = provider or get_llm_provider()
    return os.environ.get(f"{provider.upper()}_API_KEY", "").strip() or get_config().get(f"{provider}_api_key")


def get_llm_model(provider: str | None = None) -> str:
    provider = provider or get_llm_provider()
    return os.environ.get("AGENT_MEM_LLM_MODEL", "").strip() or get_config().get(f"{provider}_model") or ""
