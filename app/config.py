"""Paths and the analysis date."""

import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_JSON = ROOT / "data" / "mock_data_schema.json"
DATA_MODEL_DIR = ROOT / "data-model"
DB_PATH = DATA_MODEL_DIR / "procurement.db"
CONTEXT_DIR = ROOT / "context-model"


def analysis_date():
    """The dataset's as-of date. Never the system clock (see context-model/index.md)."""
    meta = json.loads(SOURCE_JSON.read_text())["metadata"]
    return date.fromisoformat(meta["asOfDate"])
