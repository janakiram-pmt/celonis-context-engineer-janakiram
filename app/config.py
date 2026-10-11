"""Paths, the analysis date, and settings from the environment or `.env`."""

import json
import os
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_JSON = ROOT / "data" / "mock_data_schema.json"
DATA_MODEL_DIR = ROOT / "data-model"
DB_PATH = DATA_MODEL_DIR / "procurement.db"
CONTEXT_DIR = ROOT / "context-model"
DEMO_DIR = ROOT / "demo"
DEFAULT_MODEL = "gemini-flash-latest"


def analysis_date():
    """The dataset's as-of date. Never the system clock (see context-model/index.md)."""
    meta = json.loads(SOURCE_JSON.read_text())["metadata"]
    return date.fromisoformat(meta["asOfDate"])


def setting(name, default=None):
    """Read a setting from the environment, falling back to `.env` at the repo root."""
    if os.environ.get(name):
        return os.environ[name]
    env_file = ROOT / ".env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            key, sep, value = line.strip().partition("=")
            if sep and key == name and not line.lstrip().startswith("#"):
                return value.strip().strip('"').strip("'")
    return default
