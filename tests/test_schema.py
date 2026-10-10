"""Schema tests for the relational model.

Run: python3 -m unittest discover tests -v
"""

import copy
import json
import sqlite3
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "data-model"))

import load_sqlite  # noqa: E402

SOURCE = json.loads((ROOT / "data" / "mock_data_schema.json").read_text())


class SchemaTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Path(self.tmp.name) / "test.db"

    def tearDown(self):
        self.tmp.cleanup()

    def load(self, data=None):
        conn = load_sqlite.load(self.db, data if data is not None else SOURCE)
        self.addCleanup(conn.close)
        return conn

    def mutated(self, change):
        """Return a copy of the source data with `change` applied."""
        data = copy.deepcopy(SOURCE)
        change(data)
        return data

    def records(self, data, object_type):
        return data["objects"][object_type]["records"]

    # --- Loading the real data ---

    def test_row_counts(self):
        conn = self.load()
        expected = {
            "Vendor": 5,
            "MaterialPlant": 5,
            "VendorApproval": 8,
            "MaterialRequirements": 8,
            "PurchaseRequirement": 4,
            "PurchaseDocument": 4,
            "PurchaseDocumentLine": 4,
            "Event": 24,
        }
        for table, count in expected.items():
            with self.subTest(table=table):
                self.assertEqual(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0], count)

    def test_every_source_field_loaded(self):
        conn = self.load()
        for object_type, pk in load_sqlite.OBJECT_TABLES.items():
            for record in SOURCE["objects"][object_type]["records"]:
                row = conn.execute(f"SELECT * FROM {object_type} WHERE {pk} = ?", (record[pk],))
                cols = [d[0] for d in row.description]
                loaded = dict(zip(cols, row.fetchone()))
                for field, value in record.items():
                    if field == "approvedForMaterials":
                        continue
                    with self.subTest(object=record[pk], field=field):
                        self.assertEqual(loaded[field], value)

    def test_vendor_approvals_match_source(self):
        conn = self.load()
        expected = {
            (v["vendorId"], mp)
            for v in SOURCE["objects"]["Vendor"]["records"]
            for mp in v["approvedForMaterials"]
        }
        self.assertEqual(set(conn.execute("SELECT vendorId, materialPlantId FROM VendorApproval")), expected)

    def test_event_attributes_queryable_as_json(self):
        conn = self.load()
        new_date = conn.execute(
            "SELECT json_extract(attributes, '$.newConfirmedDeliveryDate') FROM Event WHERE eventId = 'EVT-0006'"
        ).fetchone()[0]
        self.assertEqual(new_date, "2026-09-25")

    def test_connect_enforces_foreign_keys(self):
        self.load().close()
        conn = load_sqlite.connect(self.db)
        self.addCleanup(conn.close)
        self.assertEqual(conn.execute("PRAGMA foreign_keys").fetchone()[0], 1)
        with self.assertRaises(sqlite3.IntegrityError):
            conn.execute("INSERT INTO VendorApproval VALUES ('V-2001', 'MP-DOES-NOT-EXIST')")

    # --- Database checks reject broken data ---

    def assertRejected(self, change):
        with self.assertRaises((sqlite3.IntegrityError, ValueError)):
            self.load(self.mutated(change))

    def test_rejects_orphan_foreign_key(self):
        def change(d):
            self.records(d, "PurchaseDocumentLine")[0]["purchaseDocumentId"] = "PDOC-MISSING"
        self.assertRejected(change)

    def test_rejects_unknown_approved_material_plant(self):
        def change(d):
            self.records(d, "Vendor")[0]["approvedForMaterials"].append("MP-MISSING")
        self.assertRejected(change)

    def test_rejects_value_outside_source_vocabulary(self):
        def change(d):
            self.records(d, "MaterialRequirements")[0]["priority"] = "Urgent"
        self.assertRejected(change)

    def test_rejects_negative_quantity(self):
        def change(d):
            self.records(d, "MaterialPlant")[0]["onHandQuantity"] = -1
        self.assertRejected(change)

    def test_rejects_duplicate_line_number_on_a_po(self):
        def change(d):
            lines = self.records(d, "PurchaseDocumentLine")
            dup = dict(lines[0], purchaseDocumentLineId="PDOC-4500001234-10-DUP")
            lines.append(dup)
        self.assertRejected(change)

    def test_rejects_event_for_missing_object(self):
        def change(d):
            d["events"]["records"][0]["objectId"] = "PR-MISSING"
        self.assertRejected(change)

    def test_rejects_unknown_event_object_type(self):
        def change(d):
            d["events"]["records"][0]["objectType"] = "Shipment"
        self.assertRejected(change)

    # --- Unusual but legitimate data is stored, not rejected ---

    def test_accepts_over_delivery(self):
        def change(d):
            line = self.records(d, "PurchaseDocumentLine")[2]
            line["goodsReceiptQuantity"] = line["orderedQuantity"] + 10
        self.load(self.mutated(change))

    def test_accepts_po_with_unapproved_vendor(self):
        def change(d):
            for v in self.records(d, "Vendor"):
                if v["vendorId"] == "V-2001":
                    v["approvedForMaterials"] = []
        self.load(self.mutated(change))


if __name__ == "__main__":
    unittest.main()
