"""Tool registry tests: names line up with the context model; errors are structured.

Run: .venv/bin/python -m unittest discover tests -v
"""

import re
import sys
import unittest
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.tools import TOOLS, Session  # noqa: E402

FRONTMATTER = re.compile(r"^---\n(.*?)\n---\n", re.S)


def context_tool_names():
    names = set()
    for path in (ROOT / "context-model").rglob("*.md"):
        meta = yaml.safe_load(FRONTMATTER.match(path.read_text()).group(1))
        if meta.get("computed_by"):
            names.add(meta["computed_by"])
        names.update(meta.get("used_by", []))
    return names


class ToolsTest(unittest.TestCase):
    def setUp(self):
        self.session = Session()
        self.addCleanup(self.session.decisions.conn.close)

    def test_every_tool_named_in_the_context_model_exists(self):
        self.assertLessEqual(context_tool_names(), set(TOOLS))

    def test_declarations_are_well_formed(self):
        for name, spec in TOOLS.items():
            with self.subTest(tool=name):
                self.assertTrue(spec["description"])
                self.assertEqual(spec["parameters"]["type"], "object")
                for required in spec["parameters"].get("required", []):
                    self.assertIn(required, spec["parameters"]["properties"])

    def test_every_tool_has_a_handler(self):
        for name in TOOLS:
            with self.subTest(tool=name):
                self.assertTrue(hasattr(self.session, f"_{name}"))

    def test_unknown_id_returns_a_structured_error(self):
        result = self.session.call("find_transfer_options", {"material_plant_id": "MP-0000-0000"})
        self.assertIn("error", result)
        self.assertIn("MP-0000-0000", result["error"])

    def test_unknown_tool_returns_a_structured_error(self):
        self.assertIn("error", self.session.call("delete_everything", {}))

    def test_read_context_is_confined_to_the_context_model(self):
        self.assertIn("ok", self.session.call("read_context", {"path": "index.md"}))
        for path in ("../README.md", "../.env", "/etc/passwd", "rules/missing.md"):
            with self.subTest(path=path):
                self.assertIn("error", self.session.call("read_context", {"path": path}))

    def test_answer_is_grounded(self):
        self.session.call("check_stock_risk", {"material_plant_id": "MP-1010-8891"})
        ok = self.session.call("answer", {"text": "MP-1010-8891 is 200 short by 2026-09-18.", "citations": ["MREQ-7002"]})
        self.assertTrue(ok["ok"]["accepted"])
        bad = self.session.call("answer", {"text": "MP-1010-8891 is 175 short.", "citations": []})
        self.assertIn("number 175 does not appear in any tool output", bad["ok"]["problems"])

    def test_outputs_are_recorded_as_evidence(self):
        self.session.call("check_stock_risk", {"material_plant_id": "MP-1010-8891"})
        self.assertEqual(len(self.session.evidence), 1)
        self.assertIn("MREQ-7001", self.session.evidence[0])


if __name__ == "__main__":
    unittest.main()
