"""Load data/mock_data_schema.json into a SQLite database using schema.sql.

Usage: python3 data-model/load_sqlite.py [--db PATH]
Standard library only.
"""

import argparse
import json
import sqlite3
from pathlib import Path

HERE = Path(__file__).resolve().parent
SOURCE = HERE.parent / "data" / "mock_data_schema.json"
SCHEMA = HERE / "schema.sql"
DEFAULT_DB = HERE / "procurement.db"

# Source object type -> (table, primary key). Tables load in this order so
# foreign keys always point at rows that already exist.
OBJECT_TABLES = {
    "MaterialPlant": "materialPlantId",
    "Vendor": "vendorId",
    "MaterialRequirements": "requirementId",
    "PurchaseRequirement": "purchaseRequirementId",
    "PurchaseDocument": "purchaseDocumentId",
    "PurchaseDocumentLine": "purchaseDocumentLineId",
}


def connect(db_path=DEFAULT_DB):
    """Open the database with foreign keys enforced.

    SQLite turns foreign keys off for every new connection, so all code must
    open the database through this function.
    """
    conn = sqlite3.connect(db_path)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def insert(conn, table, row):
    cols = ", ".join(row)
    marks = ", ".join("?" for _ in row)
    conn.execute(f"INSERT INTO {table} ({cols}) VALUES ({marks})", list(row.values()))


def load(db_path, data=None):
    """Build db_path from the source JSON (or from `data`, for tests)."""
    if data is None:
        data = json.loads(SOURCE.read_text())
    db_path = Path(db_path)
    db_path.unlink(missing_ok=True)
    conn = connect(db_path)
    conn.executescript(SCHEMA.read_text())

    objects = data["objects"]
    for table in OBJECT_TABLES:
        for record in objects[table]["records"]:
            row = dict(record)
            approvals = row.pop("approvedForMaterials", None)
            insert(conn, table, row)
            if approvals is not None:
                for mp_id in approvals:
                    insert(conn, "VendorApproval", {"vendorId": row["vendorId"], "materialPlantId": mp_id})

    # Event.objectId cannot be a database FK, so check each reference here.
    for event in data["events"]["records"]:
        pk = OBJECT_TABLES.get(event["objectType"])
        if pk is None:
            raise ValueError(f"{event['eventId']}: unknown objectType {event['objectType']}")
        found = conn.execute(
            f"SELECT 1 FROM {event['objectType']} WHERE {pk} = ?", (event["objectId"],)
        ).fetchone()
        if not found:
            raise ValueError(f"{event['eventId']}: {event['objectType']} {event['objectId']} does not exist")
        insert(conn, "Event", {**event, "attributes": json.dumps(event.get("attributes", {}))})

    violations = conn.execute("PRAGMA foreign_key_check").fetchall()
    if violations:
        raise ValueError(f"Foreign key violations: {violations}")

    conn.commit()
    return conn


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()

    conn = load(args.db)
    print(f"Loaded {args.db}")
    for table in [*OBJECT_TABLES, "VendorApproval", "Event"]:
        count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        print(f"  {table:<22} {count}")
    conn.close()


if __name__ == "__main__":
    main()
