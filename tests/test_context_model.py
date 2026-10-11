"""Consistency tests for the context model.

Run: .venv/bin/python -m unittest discover tests -v
"""

import re
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CONTEXT = ROOT / "context-model"
SCHEMA = (ROOT / "data-model" / "schema.sql").read_text()

REQUIRED = {
    "object": {"id", "type", "table", "grain", "primary_key", "aliases", "related"},
    "concept": {"id", "type", "aliases", "inputs", "computed_by", "output", "related"},
    "rule": {"id", "type", "strength", "params", "source", "applies_to", "used_by"},
}
FOLDER_TYPE = {"objects": "object", "concepts": "concept", "rules": "rule"}
MD_LINK = re.compile(r"\]\(([^)#]+\.md)(?:#[^)]*)?\)")


def parse(path):
    text = path.read_text()
    match = re.match(r"^---\n(.*?)\n---\n(.*)$", text, re.S)
    if not match:
        raise ValueError(f"{path}: missing frontmatter")
    return yaml.safe_load(match.group(1)), match.group(2)


def schema_columns():
    """Map each table in schema.sql to its column names."""
    tables = {}
    for name, body in re.findall(r"CREATE TABLE (\w+) \((.*?)\n\);", SCHEMA, re.S):
        cols = set()
        for line in body.splitlines():
            word = line.strip().split(" ")[0]
            if word and word.isidentifier() and word not in {"PRIMARY", "UNIQUE", "FOREIGN", "CHECK"}:
                cols.add(word)
        tables[name] = cols
    return tables


FILES = {p: parse(p) for p in CONTEXT.rglob("*.md")}
IDS = {meta["id"]: path for path, (meta, _) in FILES.items()}
TABLES = schema_columns()


class ContextModelTest(unittest.TestCase):
    def test_ids_match_file_names_and_are_unique(self):
        self.assertEqual(len(IDS), len(FILES))
        for path, (meta, _) in FILES.items():
            with self.subTest(file=path.name):
                self.assertEqual(meta["id"], path.stem)

    def test_required_fields_by_type(self):
        for path, (meta, _) in FILES.items():
            folder = path.parent.name
            if folder not in FOLDER_TYPE:
                continue
            with self.subTest(file=f"{folder}/{path.name}"):
                self.assertEqual(meta["type"], FOLDER_TYPE[folder])
                self.assertLessEqual(REQUIRED[meta["type"]], set(meta))

    def test_references_resolve(self):
        for path, (meta, _) in FILES.items():
            for key in ("related", "applies_to"):
                for ref in meta.get(key, []):
                    with self.subTest(file=path.name, key=key, ref=ref):
                        self.assertIn(ref, IDS)

    def test_markdown_links_resolve(self):
        for path, (_, body) in FILES.items():
            for target in MD_LINK.findall(body):
                if "data-model" in target:
                    continue
                with self.subTest(file=path.name, link=target):
                    self.assertTrue((path.parent / target).resolve().exists())

    def test_objects_map_to_schema_tables(self):
        for path, (meta, _) in FILES.items():
            if meta["type"] != "object":
                continue
            with self.subTest(file=path.name):
                self.assertIn(meta["table"], TABLES)
                keys = meta["primary_key"] if isinstance(meta["primary_key"], list) else [meta["primary_key"]]
                for key in keys:
                    self.assertIn(key, TABLES[meta["table"]])

    def test_every_table_has_an_object_file(self):
        mapped = {meta["table"] for meta, _ in FILES.values() if meta["type"] == "object"}
        self.assertEqual(mapped, set(TABLES))

    def test_concept_inputs_exist_in_schema(self):
        for path, (meta, _) in FILES.items():
            if meta["type"] != "concept":
                continue
            for ref in meta["inputs"]:
                table, column = ref.split(".")
                with self.subTest(file=path.name, input=ref):
                    self.assertIn(table, TABLES)
                    self.assertIn(column, TABLES[table])

    def test_rule_strength_is_known(self):
        for path, (meta, _) in FILES.items():
            if meta["type"] == "rule":
                with self.subTest(file=path.name):
                    self.assertIn(meta["strength"], {"hard", "preference"})

    def test_assumptions_are_separate_and_complete(self):
        for path, (meta, body) in FILES.items():
            assumptions = meta.get("assumptions", [])
            with self.subTest(file=path.name):
                if assumptions:
                    self.assertIn("## Assumptions (ours, not the customer's)", body)
                for item in assumptions:
                    self.assertEqual(set(item), {"name", "value", "why"})
                param_names = set(meta.get("params", {}))
                self.assertFalse(param_names & {a["name"] for a in assumptions})

    def test_index_lists_every_file(self):
        _, body = FILES[CONTEXT / "index.md"]
        linked = {(CONTEXT / target).resolve() for target in MD_LINK.findall(body)}
        for path in FILES:
            if path.name != "index.md":
                with self.subTest(file=path.name):
                    self.assertIn(path.resolve(), linked)


if __name__ == "__main__":
    unittest.main()
