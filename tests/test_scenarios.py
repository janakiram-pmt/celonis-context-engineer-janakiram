"""Scenario variants: each rule decides something different when the data changes.

Guards against logic that only fits the Frankfurt answer.
Run: .venv/bin/python -m unittest discover tests -v
"""

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import briefing, decisions, offline  # noqa: E402
from app.tools import Session  # noqa: E402

SOURCE = json.loads((ROOT / "data" / "mock_data_schema.json").read_text())
FRANKFURT = "MP-1010-8891"
LINE = "PDOC-4500001234-10"


def record(data, object_type, key, value):
    pk = {"Vendor": "vendorId", "MaterialPlant": "materialPlantId", "MaterialRequirements": "requirementId",
          "PurchaseDocumentLine": "purchaseDocumentLineId"}[object_type]
    return next(r for r in data["objects"][object_type]["records"] if r[pk] == value)


def line_on_time(data):
    """Undo the slip: the line is confirmed for its original 09-11 date."""
    line = record(data, "PurchaseDocumentLine", "purchaseDocumentLineId", LINE)
    line.update(confirmedDeliveryDate="2026-09-11", lineStatus="Confirmed")
    data["events"]["records"] = [e for e in data["events"]["records"] if e["eventId"] != "EVT-0006"]


class ScenarioTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()

    def tearDown(self):
        self.tmp.cleanup()

    def build(self, change):
        data = copy.deepcopy(SOURCE)
        change(data)
        db = Path(self.tmp.name) / "variant.db"
        decisions._loader.load(db, data).close()
        d = decisions.Decisions(decisions.connect(db))
        self.addCleanup(d.conn.close)
        return d

    def risk(self, d, mp_id=FRANKFURT):
        return d.check_stock_risk(material_plant_id=mp_id)["materialPlants"][0]

    def test_no_slip_means_no_committed_shortfall(self):
        d = self.build(line_on_time)
        fr = self.risk(d)
        self.assertEqual(fr["committedShortfall"]["total"], 0)
        # Below safety stock today, restored by the on-time delivery on 09-11.
        self.assertEqual(fr["tier"], "watch")
        self.assertEqual(fr["safetyStockBreach"]["finalRestoration"], "2026-09-11")

    def test_no_spare_at_leipzig_means_bavaria_covers_all(self):
        def change(data):
            record(data, "MaterialPlant", "materialPlantId", "MP-1020-8891")["onHandQuantity"] = 100
        plan = self.build(change).rank_resolution_options(FRANKFURT)
        self.assertEqual([(a["type"], a.get("vendorId"), a["quantity"]) for a in plan["primary"]["actions"]],
                         [("alternate_vendor", "V-2002", 200)])
        self.assertTrue(plan["resultAfterPlan"]["closesCommittedGap"])

    def test_no_eligible_alternate_means_transfer_and_split(self):
        def change(data):
            record(data, "Vendor", "vendorId", "V-2002")["approvedForMaterials"].remove(FRANKFURT)
        plan = self.build(change).rank_resolution_options(FRANKFURT)
        self.assertEqual(plan["primary"]["name"], "transfer + split")
        self.assertFalse(plan["resultAfterPlan"]["closesCommittedGap"])
        self.assertEqual([(r["requirementId"], r["uncovered"]) for r in plan["primary"]["remaining"]],
                         [("MREQ-7002", 40)])
        self.assertIn("Rheinmetall", plan["lastResort"][0]["name"])
        fallback = plan["fallback"]
        self.assertEqual(fallback["name"], "incumbent expedite (last resort)")
        self.assertEqual([(a["vendorId"], a["quantity"]) for a in fallback["actions"]], [("V-2001", 40)])

    def test_new_demand_without_slip_is_a_demand_change(self):
        def change(data):
            line_on_time(data)
            data["objects"]["MaterialRequirements"]["records"].append({
                "requirementId": "MREQ-7099", "materialPlantId": FRANKFURT, "requirementType": "SalesOrder",
                "requirementQuantity": 400, "requirementDate": "2026-09-20", "priority": "High", "status": "Open"})
            data["events"]["records"].append({
                "eventId": "EVT-0099", "objectType": "MaterialRequirements", "objectId": "MREQ-7099",
                "activity": "Requirement Registered", "timestamp": "2026-09-02T06:00:00Z", "attributes": {}})
        fr = self.risk(self.build(change))
        self.assertEqual(fr["tier"], "critical")
        self.assertEqual(fr["committedShortfall"]["total"], 200)
        self.assertEqual(fr["why"]["verdict"], "demand_change")
        self.assertEqual(fr["why"]["vendorChanges"], [])

    def test_unexplained_drop_points_to_inventory(self):
        def change(data):
            line_on_time(data)
            record(data, "MaterialPlant", "materialPlantId", FRANKFURT)["onHandQuantity"] = 0
            record(data, "PurchaseDocumentLine", "purchaseDocumentLineId", LINE)["orderedQuantity"] = 300
            for event in data["events"]["records"]:  # all demand known before the supply was confirmed
                if event["objectId"] in ("MREQ-7002", "MREQ-7003"):
                    event["timestamp"] = "2026-08-01T06:00:00Z"
        fr = self.risk(self.build(change))
        self.assertEqual(fr["tier"], "critical")
        self.assertEqual(fr["why"]["verdict"], "not_explained")
        self.assertIn("Check inventory", fr["why"]["note"])

    def test_forecast_only_shortfall_is_a_warning_with_no_spend(self):
        def change(data):
            line_on_time(data)
            record(data, "MaterialRequirements", "requirementId", "MREQ-7003").update(
                requirementDate="2026-09-20", requirementQuantity=600)
        d = self.build(change)
        fr = self.risk(d)
        self.assertEqual(fr["tier"], "warning")
        self.assertEqual(fr["committedShortfall"]["total"], 0)
        self.assertEqual([s["requirementId"] for s in fr["otherShortfall"]], ["MREQ-7003"])
        self.assertEqual(d.rank_resolution_options(FRANKFURT)["status"], "no_committed_shortfall")

    def test_warning_briefing_is_accepted_with_no_spend(self):
        def change(data):
            line_on_time(data)
            record(data, "MaterialRequirements", "requirementId", "MREQ-7003").update(
                requirementDate="2026-09-20", requirementQuantity=600)
        session = Session(self.build(change))
        b = offline.build_briefing(session)
        self.assertEqual((b["shortfall_quantity"], b["recommended_plan"]), (0, []))
        result = session.call("submit_briefing", {"briefing": b})["ok"]
        self.assertTrue(result["accepted"], result.get("problems"))
        b["recommended_plan"] = [{"type": "alternate_vendor", "quantity": 400, "source": "V-2002", "arrival": "2026-09-15"}]
        rejected = session.call("submit_briefing", {"briefing": b})["ok"]
        self.assertIn("no committed shortfall: recommended_plan must be empty (no premium spend)", rejected["problems"])

    def test_overdue_supply_is_not_counted(self):
        def change(data):
            line_on_time(data)
            record(data, "PurchaseDocumentLine", "purchaseDocumentLineId", LINE)["confirmedDeliveryDate"] = "2026-09-01"
        fr = self.risk(self.build(change))
        self.assertEqual(fr["overdueSupply"], [{"lineId": LINE, "vendorId": "V-2001", "quantity": 400,
                                                 "confirmedDate": "2026-09-01", "daysOverdue": 3}])
        self.assertNotIn(LINE, [p["sourceId"] for p in fr["timeline"]])
        self.assertEqual(fr["tier"], "critical")
        why = fr["why"]
        self.assertEqual((why["verdict"], why["gapAsPromised"]), ("vendor_change", 0))
        self.assertEqual(why["vendorChanges"][0]["type"], "overdue")
        self.assertFalse(why["vendorChanges"][0]["vendorEligible"])

    def test_past_due_open_demand_counts_as_due_today(self):
        def change(data):
            data["objects"]["MaterialRequirements"]["records"].append({
                "requirementId": "MREQ-7098", "materialPlantId": "MP-1030-8892", "requirementType": "SalesOrder",
                "requirementQuantity": 250, "requirementDate": "2026-09-01", "priority": "High", "status": "Open"})
        munich = self.risk(self.build(change), "MP-1030-8892")
        point = next(p for p in munich["timeline"] if p["sourceId"] == "MREQ-7098")
        self.assertEqual((point["date"], point["balance"]), ("2026-09-04", 50))
        self.assertEqual(munich["tier"], "warning")  # below safety stock, nothing on the way to restore it

    def test_slip_reports_vendor_reliability(self):
        d = self.build(lambda data: None)
        slip = self.risk(d)["why"]["vendorChanges"][0]
        self.assertEqual((slip["vendorName"], slip["onTimeDeliveryRate"], slip["vendorEligible"]),
                         ("Rheinmetall Components GmbH", 0.72, False))

    def test_same_day_demand_serves_committed_first(self):
        def change(data):  # a forecast that sorts before the sales order by id, due the same day
            data["objects"]["MaterialRequirements"]["records"].append({
                "requirementId": "MREQ-0001", "materialPlantId": "MP-1030-8892", "requirementType": "Forecast",
                "requirementQuantity": 250, "requirementDate": "2026-09-22", "priority": "Low", "status": "Open"})
        munich = self.risk(self.build(change), "MP-1030-8892")
        uncovered = {p["sourceId"]: p["uncovered"] for p in munich["timeline"] if p["kind"] == "demand"}
        self.assertEqual(uncovered, {"MREQ-7021": 0, "MREQ-0001": 70})

    def test_on_time_unreliable_line_is_a_critical_supplier(self):
        result = self.build(line_on_time).find_critical_suppliers(material_plant_id=FRANKFURT)
        deps = [(d["requirementId"], d["lineId"], d["vendorId"], d["quantityAtRisk"]) for d in result["dependencies"]]
        self.assertEqual(deps, [("MREQ-7001", LINE, "V-2001", 60), ("MREQ-7002", LINE, "V-2001", 140)])
        self.assertEqual(len(result["unreliableOnCriticalPath"]), 2)

    def test_overdue_promise_restored_before_past_due_demand(self):
        def change(data):
            line_on_time(data)
            record(data, "PurchaseDocumentLine", "purchaseDocumentLineId", LINE)["confirmedDeliveryDate"] = "2026-09-01"
            data["objects"]["MaterialRequirements"]["records"].append({
                "requirementId": "MREQ-7097", "materialPlantId": FRANKFURT, "requirementType": "ProductionOrder",
                "requirementQuantity": 200, "requirementDate": "2026-09-02", "priority": "High", "status": "Open"})
        why = self.risk(self.build(change))["why"]
        self.assertEqual((why["verdict"], why["gapAsPromised"]), ("vendor_change", 0))

    def test_breach_periods_after_plan(self):
        breach = self.build(lambda data: None).rank_resolution_options(FRANKFURT)["resultAfterPlan"]["safetyStockBreach"]
        periods = [(q["start"], q["end"]) for q in breach["periods"] if q["inHorizon"]]
        self.assertEqual(periods, [("2026-09-04", "2026-09-06"), ("2026-09-16", "2026-09-25")])
        self.assertEqual(breach["finalRestoration"], "2026-09-25")

    def test_competing_alerts_never_double_book_transfer_stock(self):
        d = self.build(munich_needs_housings)
        risk = d.check_stock_risk()
        self.assertEqual(risk["findingOrder"], ["MP-1030-8891", FRANKFURT])  # Munich is short first (09-14)

        session = Session(d)
        munich = session.call("rank_resolution_options", {"material_plant_id": "MP-1030-8891"})["ok"]
        frankfurt = session.call("rank_resolution_options", {"material_plant_id": FRANKFURT})["ok"]
        from_leipzig = [a["quantity"] for plan in (munich, frankfurt)
                        for a in plan["primary"]["actions"] if a.get("from") == "MP-1020-8891"]
        self.assertEqual(from_leipzig, [100, 60])           # 160 spare, split in finding order
        self.assertLessEqual(sum(from_leipzig), 160)
        self.assertTrue(frankfurt["resultAfterPlan"]["recheck"]["holds"])
        self.assertEqual([r["quantity"] for r in frankfurt["reservedForEarlierPlans"]], [100])

    def test_briefing_lists_every_alert(self):
        session = Session(self.build(munich_needs_housings))
        b = offline.build_briefing(session)
        self.assertEqual(b["material_plant_id"], "MP-1030-8891")
        self.assertTrue(any(FRANKFURT in line for line in b["other_findings"]))
        self.assertEqual(briefing.validate(b, session.evidence, session.plans["MP-1030-8891"], session.last_risk), [])
        b["other_findings"] = []
        self.assertIn(f"other_findings must list {FRANKFURT}",
                      briefing.validate(b, session.evidence, session.plans["MP-1030-8891"], session.last_risk))


def munich_needs_housings(data):
    """A second bearing-housing alert at Munich, short before Frankfurt, also able to use Leipzig's stock."""
    data["objects"]["MaterialPlant"]["records"].append({
        "materialPlantId": "MP-1030-8891", "materialId": "MAT-8891", "materialDescription": "Bearing Housing, Cast",
        "plantId": "1030", "plantName": "Munich Assembly", "baseUnit": "EA", "onHandQuantity": 0,
        "safetyStock": 20, "reorderPoint": 40, "standardCost": 42.5})
    data["objects"]["MaterialRequirements"]["records"].append({
        "requirementId": "MREQ-7050", "materialPlantId": "MP-1030-8891", "requirementType": "ProductionOrder",
        "requirementQuantity": 100, "requirementDate": "2026-09-14", "priority": "High", "status": "Open"})
    data["events"]["records"].append({
        "eventId": "EVT-0050", "objectType": "MaterialRequirements", "objectId": "MREQ-7050",
        "activity": "Requirement Registered", "timestamp": "2026-09-02T06:00:00Z", "attributes": {}})
    record(data, "Vendor", "vendorId", "V-2002")["approvedForMaterials"].append("MP-1030-8891")


if __name__ == "__main__":
    unittest.main()
