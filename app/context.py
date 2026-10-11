"""Read the context model: rule parameters, assumptions, and file text."""

import re
from functools import lru_cache

import yaml

from app.config import CONTEXT_DIR

FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n(.*)$", re.S)


@lru_cache(maxsize=None)
def _files():
    """Map each file id to (frontmatter, body, path relative to the context model)."""
    files = {}
    for path in CONTEXT_DIR.rglob("*.md"):
        match = FRONTMATTER.match(path.read_text())
        meta = yaml.safe_load(match.group(1))
        files[meta["id"]] = (meta, match.group(2), str(path.relative_to(CONTEXT_DIR)))
    return files


def params(file_id):
    return _files()[file_id][0].get("params", {})


def assumption(file_id, name):
    """Return the assumption entry {name, value, why} plus the file it came from."""
    meta, _, rel = _files()[file_id]
    for item in meta.get("assumptions", []):
        if item["name"] == name:
            return {"file": rel, **item}
    raise KeyError(f"{file_id}: no assumption named {name!r}")


def assumption_days(file_id, name):
    """Leading whole number of days in an assumption's value, e.g. '2 days …' -> 2."""
    value = assumption(file_id, name)["value"]
    match = re.match(r"\s*(\d+)\s*day", value)
    if not match:
        raise ValueError(f"{file_id}/{name}: value {value!r} doesn't start with a number of days")
    return int(match.group(1))
