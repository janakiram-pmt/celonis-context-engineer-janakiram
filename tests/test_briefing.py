"""Briefing tests: the grounding check accepts tool-backed briefings and rejects invented ones.

Run: .venv/bin/python -m unittest discover tests -v
"""

import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import briefing, offline  # noqa: E402
from app.tools import Session  # noqa: E402


class BriefingTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.session = Session()
        cls.good = offline.build_briefing(cls.session)

    @classmethod
    def tearDownClass(cls):
        cls.session.decisions.conn.close()

    def problems(self, b):
        return briefing.validate(b, self.session.evidence, self.session.last_plan, self.session.last_risk)

    def test_offline_briefing_is_accepted(self):
        self.assertEqual(self.problems(self.good), [])
        self.assertEqual(self.good["status"], "alert")

    def test_invented_number_is_rejected(self):
        b = copy.deepcopy(self.good)
        b["result_after_plan"] += " Saves 175 hours."
        self.assertIn("number 175 does not appear in any tool output", self.problems(b))

    def test_invented_record_id_is_rejected(self):
        b = copy.deepcopy(self.good)
        b["citations"].append("EVT-9999")
        self.assertIn("record id EVT-9999 does not appear in any tool output", self.problems(b))

    def test_resized_plan_is_rejected(self):
        b = copy.deepcopy(self.good)  # a 200-unit transfer uses real numbers but isn't the ranked plan
        b["recommended_plan"] = [{"type": "transfer", "quantity": 200, "source": "MP-1020-8891", "arrival": "2026-09-06"}]
        self.assertTrue(any("does not match the ranked primary plan" in p for p in self.problems(b)))

    def test_alert_without_fallback_is_rejected(self):
        b = copy.deepcopy(self.good)
        b["fallback"] = ""
        self.assertIn("alert is missing field: fallback", self.problems(b))

    def test_percentages_of_tool_rates_are_allowed(self):
        b = copy.deepcopy(self.good)
        b["watch"].append("Rheinmetall's on-time rate is 72%.")
        self.assertEqual(self.problems(b), [])

    def test_wrong_pairing_is_rejected(self):
        b = copy.deepcopy(self.good)  # 140 is a real number, but it belongs to MREQ-7002
        b["affected_demand"][0] = "MREQ-7001 (ProductionOrder, 2026-09-16, 140 short)"
        self.assertIn("affected_demand must pair MREQ-7001 with 60 short on 2026-09-16", self.problems(b))

    def test_wrong_shortfall_quantity_is_rejected(self):
        b = copy.deepcopy(self.good)
        b["shortfall_quantity"] = 140
        self.assertIn("shortfall_quantity must be 200 (check_stock_risk)", self.problems(b))

    def test_cause_must_name_the_event(self):
        b = copy.deepcopy(self.good)
        b["cause"] = b["cause"].replace("EVT-0006", "the event")
        self.assertIn("cause must mention EVT-0006 (EVT-0006)", self.problems(b))

    def test_chat_hint_in_both_renderings(self):
        self.assertIn("python -m app chat", briefing.render_markdown(self.good))
        self.assertIn("python -m app chat", json.dumps(briefing.render_slack(self.good)))

    def test_renders_markdown_and_slack(self):
        self.assertIn("160 from MP-1020-8891", briefing.render_markdown(self.good))
        slack = briefing.render_slack(self.good)
        self.assertEqual(slack["text"], self.good["headline"])
        self.assertTrue(slack["blocks"])


if __name__ == "__main__":
    unittest.main()
