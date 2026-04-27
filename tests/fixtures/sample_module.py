"""Sample module for benchmark testing."""
import os
import sys
from pathlib import Path
from typing import Optional

CONSTANT = 42

class DataProcessor:
    """Processes data."""

    def __init__(self, path: str):
        self.path = path
        self._cache = {}

    def load(self, strict: bool = False) -> dict:
        """Load data from path."""
        result = self._read_file()
        return result

    def _read_file(self) -> dict:
        # NOTE: fallback to empty dict on missing file
        if not os.path.exists(self.path):
            return {}
        return {"loaded": True}

    def process(self, data: dict, transform: Optional[str] = None) -> list:
        """Process data with optional transform."""
        items = list(data.items())
        filtered = self._filter(items)
        return filtered

    def _filter(self, items: list) -> list:
        return [i for i in items if i]


class ConfigManager:
    """Manages configuration."""

    def __init__(self):
        self.config = {}

    def load_from_path(self, path: Path) -> bool:
        """Load config from a file path."""
        data = self._parse(str(path))
        self.config.update(data)
        return True

    def _parse(self, raw: str) -> dict:
        # TODO: support YAML format
        return {}

    def get(self, key: str, default=None):
        return self.config.get(key, default)


def standalone_helper(value: int, multiplier: float = 1.0) -> float:
    """A standalone helper function."""
    result = compute(value)
    return result * multiplier


def compute(n: int) -> int:
    """Pure computation."""
    return n * CONSTANT


async def async_fetch(url: str, timeout: int = 30) -> bytes:
    """Async fetch operation."""
    data = await _async_read(url)
    return data


async def _async_read(url: str) -> bytes:
    return b""
