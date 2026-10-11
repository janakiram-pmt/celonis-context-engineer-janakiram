"""Behavioral tests: the decision functions reproduce the Frankfurt scenario.

Run: .venv/bin/python -m unittest discover tests -v
"""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import decisions  # noqa: E402

FRANKFURT = "MP-1010-8891"
LEIPZIG = "MP-1020-8891"


class DecisionsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        db = Path(cls.tmp.name) / "test.db"
        decisions._loader.load(db).close()
        cls.d = decisions.Decisions(decisions.connect(db))
        cls.risk = {m["materialPlantId"]: m for m in cls.d.check_stock_risk()["materialPlants"]}
        cls.plan = cls.d.rank_resolution_options(FRANKFURT)

    @classmethod
    def tearDownClass(cls):
        cls.d.conn.close()
        cls.tmp.cleanup()

    # --- Detect

    def test_analysis_date_is_dataset_as_of_date(self):
        self.assertEqual(self.d.today.isoformat(), "2026-09-04")

    def test_frankfurt_is_critical_with_200_short_by_0918(self):
        fr = self.risk[FRANKFURT]
        self.assertEqual(fr["tier"], "critical")
        self.assertEqual(fr["horizon"], "2026-09-27")
        short = fr["committedShortfall"]
        self.assertEqual(short["total"], 200)
        self.assertEqual(short["firstDate"], "2026-09-16")
        self.assertEqual([(r["requirementId"], r["date"], r["uncovered"]) for r in short["requirements"]],
                         [("MREQ-7001", "2026-09-16", 60), ("MREQ-7002", "2026-09-18", 140)])

    def test_frankfurt_timeline(self):
        timeline = [(p["date"], p["balance"], p["sourceId"]) for p in self.risk[FRANKFURT]["timeline"]]
        self.assertEqual(timeline, [
            ("2026-09-04", 120, FRANKFURT),
            ("2026-09-16", -60, "MREQ-7001"),
            ("2026-09-18", -200, "MREQ-7002"),
            ("2026-09-25", 200, "PDOC-4500001234-10"),
            ("2026-09-30", 140, "MREQ-7003"),
        ])

    def test_other_material_plants_are_quiet(self):
        expected_horizons = {"MP-1020-8891": "2026-09-27", "MP-1010-8892": "2026-09-20",
                             "MP-1030-8892": "2026-09-20", "MP-1020-7400": "2026-09-18"}
        for mp_id, horizon in expected_horizons.items():
            with self.subTest(mp=mp_id):
                self.assertEqual(self.risk[mp_id]["tier"], "quiet")
                self.assertEqual(self.risk[mp_id]["horizon"], horizon)
                self.assertNotIn("why", self.risk[mp_id])

    def test_plant_scope_returns_quiet_summary(self):
        munich = self.d.check_stock_risk(plant_id="1030")["materialPlants"]
        self.assertEqual([m["materialPlantId"] for m in munich], ["MP-1030-8892"])
        self.assertEqual(munich[0]["tier"], "quiet")
        self.assertEqual(munich[0]["summary"]["onHand"], 300)

    def test_unknown_scope_raises(self):
        with self.assertRaises(LookupError):
            self.d.check_stock_risk(plant_id="9999")

    # --- Why

    def test_why_names_the_vendor_slip(self):
        why = self.risk[FRANKFURT]["why"]
        self.assertEqual(why["verdict"], "vendor_change")
        self.assertEqual((why["gapNow"], why["gapAsPromised"]), (200, 0))
        slip = why["vendorChanges"][0]
        self.assertEqual((slip["eventId"], slip["before"], slip["after"]), ("EVT-0006", "2026-09-11", "2026-09-25"))
        self.assertEqual([r["requirementId"] for r in slip["movedPast"]], ["MREQ-7001", "MREQ-7002"])
        self.assertTrue(all(c["coveredUnderPromise"] for c in why["demandAfterCommitment"]))

    def test_find_changes_date_slips(self):
        slips = self.d.find_changes(type="date_slip")["changes"]
        self.assertEqual([(c["eventId"], c["days"], c["reason"], c["ageDays"]) for c in slips],
                         [("EVT-0006", 14, "Vendor capacity constraint", 3)])

    def test_find_changes_rejects_unknown_type(self):
        with self.assertRaises(ValueError):
            self.d.find_changes(type="earthquake")

    def test_no_unreliable_supplier_on_committed_critical_path(self):
        self.assertEqual(self.d.find_critical_suppliers()["dependencies"], [])

    # --- Resolve

    def test_leipzig_can_spare_160_not_200(self):
        option = self.d.find_transfer_options(FRANKFURT)["options"][0]
        self.assertEqual((option["fromMaterialPlantId"], option["spare"], option["limitedBy"], option["arrival"]),
                         (LEIPZIG, 160, "MREQ-7010", "2026-09-06"))

    def test_vendor_eligibility(self):
        vendors = {v["vendorId"]: v for v in self.d.find_alternate_vendors(FRANKFURT)["vendors"]}
        self.assertTrue(vendors["V-2002"]["eligible"])
        self.assertEqual(vendors["V-2002"]["arrival"], "2026-09-15")
        self.assertTrue(vendors["V-2002"]["inTimeForFirstNeed"])
        self.assertFalse(vendors["V-2001"]["eligible"])
        self.assertEqual(vendors["V-2001"]["role"], "incumbent")
        self.assertFalse(vendors["V-2003"]["eligible"])

    def test_primary_plan_is_transfer_160_plus_bavaria_40(self):
        actions = [(a["type"], a.get("from") or a.get("vendorId"), a["quantity"], a["arrival"])
                   for a in self.plan["primary"]["actions"]]
        self.assertEqual(actions, [("transfer", LEIPZIG, 160, "2026-09-06"),
                                   ("alternate_vendor", "V-2002", 40, "2026-09-15")])

    def test_plan_closes_gap_and_holds(self):
        result = self.plan["resultAfterPlan"]
        self.assertTrue(result["closesCommittedGap"])
        self.assertEqual([p["balance"] for p in result["timeline"]], [120, 280, 320, 140, 0, 400, 340])
        self.assertEqual(result["tier"], "watch")
        sender = result["recheck"]["senders"][0]
        self.assertEqual((sender["materialPlantId"], sender["lowest"], sender["holds"]), (LEIPZIG, 60, True))
        self.assertTrue(result["recheck"]["holds"])

    def test_fallback_is_split_waiting_for_original_delivery(self):
        fallback = self.plan["fallback"]
        self.assertEqual(fallback["name"], "transfer + split")
        self.assertEqual([(r["requirementId"], r["uncovered"]) for r in fallback["remaining"]], [("MREQ-7002", 40)])
        self.assertEqual(fallback["waitsFor"], {"lineId": "PDOC-4500001234-10", "date": "2026-09-25"})

    def test_incumbent_is_last_resort(self):
        self.assertIn("Rheinmetall", self.plan["lastResort"][0]["name"])

    def test_results_carry_assumptions(self):
        names = {a["name"] for a in self.plan["assumptions_used"]}
        self.assertLessEqual({"analysis date", "transfer lead time", "order processing time", "backlog"}, names)


if __name__ == "__main__":
    unittest.main()
