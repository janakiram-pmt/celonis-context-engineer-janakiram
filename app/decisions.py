"""Deterministic decision functions: every number the agent reports comes from here.

Each public method answers one planner question, reads its thresholds from the
context model, and cites the source record behind every number. Definitions
live in context-model/concepts/; policies in context-model/rules/.
"""

import importlib.util
import json
import sqlite3
from datetime import date, timedelta

from app import context
from app.config import DATA_MODEL_DIR, DB_PATH, analysis_date

PRIORITY_RANK = {"High": 0, "Medium": 1, "Low": 2}

ACTIVITY_TYPES = {
    "Requirement Registered": "new_demand",
    "Requirement Changed": "demand_change",
    "Delivery Date Confirmed": "confirmation",
    "Goods Received": "receipt",
    "Purchase Requirement Created": "requisition_created",
    "Purchase Order Created": "po_created",
    "Purchase Order Approved": "po_approved",
    "Line Created": "line_created",
}
CHANGE_TYPES = {"date_slip", "date_pull_in", *ACTIVITY_TYPES.values()}


def _load_sqlite_module():
    spec = importlib.util.spec_from_file_location("load_sqlite", DATA_MODEL_DIR / "load_sqlite.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_loader = _load_sqlite_module()


def connect(db_path=DB_PATH):
    """Open the procurement database (building it from the source JSON if missing)."""
    if not db_path.exists():
        _loader.load(db_path).close()
    return _loader.connect(db_path)


def _d(value):
    return date.fromisoformat(value[:10])


def _plain(value):
    """Make a result JSON-serializable: dates become ISO strings."""
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, dict):
        return {k: _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


class Decisions:
    def __init__(self, conn=None, today=None):
        self.conn = conn or connect()
        self.conn.row_factory = sqlite3.Row
        self.today = today or analysis_date()
        self.processing_days = context.assumption_days("alerting", "order processing time")
        self.transfer_days = context.assumption_days("transfer-limit", "transfer lead time")
        self.eligibility_params = context.params("vendor-eligibility")
        self.preference = context.params("resolution-order")["order"]
        self.committed_types = tuple(context.params("committed-demand")["committed_types"])

    # ------------------------------------------------------------------ data access

    def _rows(self, sql, args=()):
        return [dict(r) for r in self.conn.execute(sql, args)]

    def _material_plant(self, mp_id):
        rows = self._rows("SELECT * FROM MaterialPlant WHERE materialPlantId = ?", (mp_id,))
        if not rows:
            raise LookupError(f"Unknown material-plant: {mp_id}")
        return rows[0]

    def _vendor(self, vendor_id):
        rows = self._rows("SELECT * FROM Vendor WHERE vendorId = ?", (vendor_id,))
        if not rows:
            raise LookupError(f"Unknown vendor: {vendor_id}")
        return rows[0]

    def _scope(self, material_plant_id=None, plant_id=None, material_id=None):
        sql, args = "SELECT * FROM MaterialPlant WHERE 1 = 1", []
        for column, value in (("materialPlantId", material_plant_id), ("plantId", plant_id), ("materialId", material_id)):
            if value is not None:
                sql += f" AND {column} = ?"
                args.append(value)
        rows = self._rows(sql + " ORDER BY materialPlantId", args)
        if not rows:
            raise LookupError(f"No material-plant matches material_plant_id={material_plant_id}, "
                              f"plant_id={plant_id}, material_id={material_id}")
        return rows

    def _demand(self, mp_id):
        """Demand by date. Past-due requirements that aren't covered are still owed: due today."""
        rows = self._rows("SELECT * FROM MaterialRequirements WHERE materialPlantId = ?", (mp_id,))
        rows = [r for r in rows if _d(r["requirementDate"]) >= self.today or r["status"] != "Covered"]
        return [{
            "date": max(_d(r["requirementDate"]), self.today),
            "pastDue": _d(r["requirementDate"]) < self.today,
            "quantity": r["requirementQuantity"],
            "sourceType": "MaterialRequirements",
            "sourceId": r["requirementId"],
            "requirementType": r["requirementType"],
            "priority": r["priority"],
        } for r in rows]

    def _open_supply(self, mp_id):
        """Open quantity per PO line due on or after the analysis date (concepts/open-supply.md)."""
        return [s for s in self._open_lines(mp_id) if not s["overdue"]]

    def _overdue_supply(self, mp_id):
        """Open lines whose confirmed date has passed: not counted until received."""
        return [s for s in self._open_lines(mp_id) if s["overdue"]]

    def _open_lines(self, mp_id):
        rows = self._rows(
            "SELECT l.*, d.vendorId FROM PurchaseDocumentLine l "
            "JOIN PurchaseDocument d ON d.purchaseDocumentId = l.purchaseDocumentId "
            "WHERE l.materialPlantId = ?", (mp_id,))
        supply = []
        for r in rows:
            open_qty = r["orderedQuantity"] - r["goodsReceiptQuantity"]
            if open_qty > 0:
                confirmed = _d(r["confirmedDeliveryDate"])
                supply.append({
                    "date": confirmed,
                    "overdue": confirmed < self.today,
                    "daysOverdue": max(0, (self.today - confirmed).days),
                    "quantity": open_qty,
                    "sourceType": "PurchaseDocumentLine",
                    "sourceId": r["purchaseDocumentLineId"],
                    "vendorId": r["vendorId"],
                    "netPrice": r["netPrice"],
                })
        return supply

    def _approved_vendors(self, mp_id):
        return self._rows(
            "SELECT v.* FROM Vendor v JOIN VendorApproval a ON a.vendorId = v.vendorId "
            "WHERE a.materialPlantId = ? ORDER BY v.vendorId", (mp_id,))

    # ------------------------------------------------------------------ core calculations

    def _project(self, mp, demand, supply):
        """Event-based projection (concepts/projected-stock.md).

        Points only where something changes; on the same date, demand comes
        before supply and is served committed first, then by priority
        (rules/demand-priority.md); the balance may go negative (backlog).
        Supply marked `arrivedBefore` (a restored overdue promise) counts first.
        """
        def rank(step):
            if step["order"] != 0:
                return (0, 0)
            committed = step.get("requirementType") in self.committed_types
            return (0 if committed else 1, PRIORITY_RANK.get(step.get("priority"), len(PRIORITY_RANK)))

        steps = [dict(s, order=0, change=-s["quantity"]) for s in demand]
        steps += [dict(s, order=-1 if s.get("arrivedBefore") else 1, change=s["quantity"]) for s in supply]
        steps.sort(key=lambda s: (s["date"], s["order"], *rank(s), s["sourceId"]))
        balance = mp["onHandQuantity"]
        timeline = [{"date": self.today, "change": 0, "balance": balance, "kind": "on_hand",
                     "sourceType": "MaterialPlant", "sourceId": mp["materialPlantId"]}]
        for s in steps:
            balance += s["change"]
            point = {"date": s["date"], "change": s["change"], "balance": balance,
                     "kind": "demand" if s["order"] == 0 else "supply",
                     "sourceType": s["sourceType"], "sourceId": s["sourceId"]}
            if s["order"] == 0:
                point["requirementType"] = s.get("requirementType")
                point["committed"] = s.get("requirementType") in self.committed_types
                point["uncovered"] = min(s["quantity"], -balance) if balance < 0 else 0
            timeline.append(point)
        return timeline

    @staticmethod
    def _shortfalls(timeline, until=None, committed_only=False):
        """Uncovered part of each requirement (concepts/shortfall.md)."""
        return [{"requirementId": p["sourceId"], "requirementType": p["requirementType"],
                 "date": p["date"], "uncovered": p["uncovered"]}
                for p in timeline
                if p["kind"] == "demand" and p["uncovered"] > 0
                and (until is None or p["date"] <= until)
                and (p["committed"] or not committed_only)]

    def _eligibility(self, vendor, mp_id):
        """Pass/fail against rules/vendor-eligibility.md, with reasons."""
        p = self.eligibility_params
        approved = bool(self._rows("SELECT 1 FROM VendorApproval WHERE vendorId = ? AND materialPlantId = ?",
                                   (vendor["vendorId"], mp_id)))
        rate, bar = vendor["onTimeDeliveryRate"], p["min_on_time_rate"]
        on_time = rate > bar if p["on_time_comparison"] == "greater_than" else rate >= bar
        quality = vendor["qualityRating"] in p["allowed_quality"]
        reasons = []
        if p["must_be_approved"] and not approved:
            reasons.append(f"not approved for {mp_id}")
        if not on_time:
            reasons.append(f"on-time rate {rate:.2f} is not above {bar:.2f}")
        if not quality:
            reasons.append(f"quality {vendor['qualityRating']} is not in {p['allowed_quality']}")
        return {"eligible": not reasons, "approved": approved, "onTime": on_time, "quality": quality, "reasons": reasons}

    def _horizon(self, mp_id, supply):
        """Near-term horizon (rules/alerting.md assumptions)."""
        if supply:
            line = min(supply, key=lambda s: s["date"])
            vendor = self._vendor(line["vendorId"])
            basis = f"lead time of {vendor['name']} on open supply {line['sourceId']}"
        else:
            approved = self._approved_vendors(mp_id)
            eligible = [v for v in approved if self._eligibility(v, mp_id)["eligible"]]
            if eligible:
                vendor = min(eligible, key=lambda v: v["avgLeadTimeDays"])
                basis = f"no open supply; fastest eligible approved vendor {vendor['name']}"
            elif approved:
                vendor = max(approved, key=lambda v: v["avgLeadTimeDays"])
                basis = f"no open supply and no eligible vendor; slowest approved vendor {vendor['name']}"
            else:
                return None, "no open supply and no approved vendor; whole timeline used"
        horizon = self.today + timedelta(days=self.processing_days + vendor["avgLeadTimeDays"])
        return horizon, f"{basis} ({vendor['avgLeadTimeDays']} d) + {self.processing_days} d order processing"

    @staticmethod
    def _in_horizon(timeline, horizon):
        return [p for p in timeline if horizon is None or p["date"] <= horizon]

    def _tier(self, mp, timeline, horizon):
        """Critical / Warning / Watch / Quiet (rules/alerting.md), with safety-stock breach periods."""
        ss = mp["safetyStock"]
        periods, current = [], None
        for p in timeline:
            if p["balance"] < ss:
                if current is None:
                    current = {"start": p["date"], "end": None, "restoredBy": None, "lowest": p["balance"]}
                current["lowest"] = min(current["lowest"], p["balance"])
            elif current is not None:
                current.update(end=p["date"], restoredBy=p["sourceId"])
                periods.append(current)
                current = None
        if current is not None:
            periods.append(current)
        for period in periods:
            period["inHorizon"] = horizon is None or period["start"] <= horizon
        in_horizon = [q for q in periods if q["inHorizon"]]

        if self._shortfalls(timeline, horizon, committed_only=True):
            tier = "critical"
        elif in_horizon and (any(q["end"] is None for q in in_horizon) or self._shortfalls(timeline, horizon)):
            tier = "warning"
        elif in_horizon:
            tier = "watch"
        else:
            tier = "quiet"
        breach = None
        if in_horizon:
            restored = all(q["end"] is not None for q in in_horizon)
            breach = {"firstDate": in_horizon[0]["start"], "lowest": min(q["lowest"] for q in in_horizon),
                      "finalRestoration": in_horizon[-1]["end"] if restored else None, "periods": periods}
        return tier, breach

    # ------------------------------------------------------------------ assumptions

    def _assumptions(self, *names):
        catalog = {
            "near-term horizon": ("alerting", "near-term horizon"),
            "order processing time": ("alerting", "order processing time"),
            "same-day ordering": ("projected-stock", "same-day ordering"),
            "backlog": ("projected-stock", "backlog"),
            "type decides commitment": ("committed-demand", "type decides commitment"),
            "north of ninety percent": ("vendor-eligibility", "north of ninety percent"),
            "transfer lead time": ("transfer-limit", "transfer lead time"),
            "alternate vendor price": ("spending-policy", "alternate vendor price"),
            "overdue supply": ("open-supply", "overdue supply"),
            "past-due demand": ("projected-stock", "past-due demand"),
        }
        used = [{"file": "index.md", "name": "analysis date", "value": self.today.isoformat()}]
        for name in names:
            entry = context.assumption(*catalog[name])
            used.append({"file": entry["file"], "name": entry["name"], "value": entry["value"]})
        return used

    # ------------------------------------------------------------------ tools

    def check_stock_risk(self, material_plant_id=None, plant_id=None, material_id=None):
        """Is anything at risk, how badly, and why?"""
        results = []
        for mp in self._scope(material_plant_id, plant_id, material_id):
            mp_id = mp["materialPlantId"]
            demand, supply = self._demand(mp_id), self._open_supply(mp_id)
            timeline = self._project(mp, demand, supply)
            overdue = self._overdue_supply(mp_id)
            horizon, basis = self._horizon(mp_id, supply or overdue)
            tier, breach = self._tier(mp, timeline, horizon)
            window = self._in_horizon(timeline, horizon)
            lowest = min(window, key=lambda p: p["balance"])
            committed = self._shortfalls(timeline, horizon, committed_only=True)
            result = {
                "materialPlantId": mp_id,
                "material": mp["materialDescription"],
                "plant": f"{mp['plantId']} {mp['plantName']}",
                "tier": tier,
                "horizon": horizon,
                "horizonBasis": basis,
                "summary": {
                    "onHand": mp["onHandQuantity"],
                    "safetyStock": mp["safetyStock"],
                    "demandInHorizon": sum(p["quantity"] for p in demand if self.today <= p["date"] <= (horizon or p["date"])),
                    "openSupply": sum(s["quantity"] for s in supply),
                    "lowestInHorizon": {"balance": lowest["balance"], "date": lowest["date"], "sourceId": lowest["sourceId"]},
                },
                "timeline": timeline,
                "committedShortfall": {
                    "total": sum(s["uncovered"] for s in committed),
                    "firstDate": committed[0]["date"] if committed else None,
                    "requirements": committed,
                },
                "otherShortfall": [s for s in self._shortfalls(timeline, horizon) if s["requirementType"] not in self.committed_types],
                "safetyStockBreach": breach,
                "overdueSupply": [{"lineId": s["sourceId"], "vendorId": s["vendorId"], "quantity": s["quantity"],
                                   "confirmedDate": s["date"], "daysOverdue": s["daysOverdue"]} for s in overdue],
            }
            if tier in ("critical", "warning"):
                result["why"] = self._why(mp, demand, supply, overdue, horizon, tier)
                first = (committed[0]["date"] if committed else
                         min([s["date"] for s in self._shortfalls(timeline, horizon)] + [breach["firstDate"]]))
                short_ids = {s["requirementId"] for s in self._shortfalls(timeline, horizon)}
                priority = min([PRIORITY_RANK.get(d["priority"], len(PRIORITY_RANK))
                                for d in demand if d["sourceId"] in short_ids] or [len(PRIORITY_RANK)])
                result["_order"] = (0 if tier == "critical" else 1, first, priority, mp_id)
            results.append(result)
        order = sorted((r for r in results if "_order" in r), key=lambda r: r["_order"])
        for r in results:
            r.pop("_order", None)
        return _plain({
            "analysisDate": self.today,
            "materialPlants": results,
            "findingOrder": [r["materialPlantId"] for r in order],
            "assumptions_used": self._assumptions("near-term horizon", "order processing time", "same-day ordering",
                                                  "backlog", "type decides commitment", "north of ninety percent",
                                                  "overdue supply", "past-due demand"),
        })

    def _vendor_facts(self, vendor_id, mp_id):
        vendor = self._vendor(vendor_id)
        check = self._eligibility(vendor, mp_id)
        return {"vendorName": vendor["name"], "onTimeDeliveryRate": vendor["onTimeDeliveryRate"],
                "qualityRating": vendor["qualityRating"], "vendorEligible": check["eligible"],
                "vendorReasons": check["reasons"]}

    def _why(self, mp, demand, supply, overdue, horizon, tier):
        """Cause by elimination: vendor promise vs. now, plus demand added after commitment."""
        def gap(timeline):
            if tier == "critical":
                return sum(s["uncovered"] for s in self._shortfalls(timeline, horizon, committed_only=True))
            short = sum(s["uncovered"] for s in self._shortfalls(timeline, horizon))
            if short:
                return short
            return max(0, mp["safetyStock"] - min(p["balance"] for p in self._in_horizon(timeline, horizon)))

        mp_id = mp["materialPlantId"]
        metric = "committed shortfall" if tier == "critical" else "shortfall or gap to safety stock"
        now = gap(self._project(mp, demand, supply))
        open_lines = {s["sourceId"] for s in supply + overdue}
        slips = [c for c in self.find_changes(type="date_slip", material_plant_id=mp_id)["changes"]
                 if c["objectId"] in open_lines]

        promised = {}
        for c in slips:  # the first change's old date is the original promise
            promised.setdefault(c["objectId"], _d(c["before"]))

        def restore(line_ids):
            restored = [dict(s, date=max(promised[s["sourceId"]], self.today)) if s["sourceId"] in line_ids else s
                        for s in supply]
            return restored + [dict(s, date=self.today, arrivedBefore=True) for s in overdue if s["sourceId"] in line_ids]

        vendor_changes = []
        for c in slips:
            vendor_changes.append({**c, **self._vendor_facts(c["vendorId"], mp_id),
                                   "gapAsPromised": gap(self._project(mp, demand, restore({c["objectId"]}))),
                                   "gapNow": now})
        for s in overdue:
            vendor_changes.append({"type": "overdue", "objectId": s["sourceId"], "vendorId": s["vendorId"],
                                   "before": s["date"], "daysOverdue": s["daysOverdue"], "quantity": s["quantity"],
                                   **self._vendor_facts(s["vendorId"], mp_id),
                                   "gapAsPromised": gap(self._project(mp, demand, restore({s["sourceId"]}))),
                                   "gapNow": now})
        all_restored_supply = restore(set(promised) | {s["sourceId"] for s in overdue})
        as_promised = gap(self._project(mp, demand, all_restored_supply))

        confirmations = self._rows(
            "SELECT objectId, MIN(timestamp) AS ts FROM Event WHERE activity = 'Delivery Date Confirmed' "
            "GROUP BY objectId")
        confirmed_at = min((r["ts"] for r in confirmations if r["objectId"] in open_lines), default=None)
        promised_timeline = self._project(mp, demand, all_restored_supply)
        uncovered_promised = {p["sourceId"]: p["uncovered"] for p in promised_timeline if p["kind"] == "demand"}
        demand_after = []
        if confirmed_at:
            for c in self.find_changes(material_plant_id=mp_id)["changes"]:
                if c["type"] in ("new_demand", "demand_change") and c["timestamp"] > confirmed_at:
                    demand_after.append({**c, "coveredUnderPromise": uncovered_promised.get(c["objectId"], 0) == 0})

        added = sum(c["after"]["quantity"] for c in demand_after if c["type"] == "new_demand")
        vendor_issue = bool(slips or overdue)
        if vendor_issue and as_promised == 0:
            verdict = "vendor_change"
        elif as_promised > 0 and demand_after and added >= as_promised:
            verdict = "vendor_and_demand_change" if vendor_issue and as_promised < now else "demand_change"
        else:
            verdict = "not_explained"
        notes = {
            "vendor_change": "Had the vendor kept its original promise (date, or delivery of an overdue line), there would be no gap.",
            "vendor_and_demand_change": "The vendor change and demand added after supply was committed explain the gap together.",
            "demand_change": "Demand added or changed after supply was committed explains the gap.",
            "not_explained": "Not explained by vendor or demand changes: most likely an internal stock change "
                             "(consumption, scrap, count correction) or a planning gap. Check inventory.",
        }
        return {"verdict": verdict, "note": notes[verdict], "metric": metric, "gapNow": now,
                "gapAsPromised": as_promised, "vendorChanges": vendor_changes,
                "demandAfterCommitment": demand_after, "supplyConfirmedAt": confirmed_at}

    def find_changes(self, type=None, vendor_id=None, material_plant_id=None, since=None, until=None):
        """What changed? Facts from the event log, filtered."""
        if type is not None and type not in CHANGE_TYPES:
            raise ValueError(f"Unknown change type {type!r}; use one of {sorted(CHANGE_TYPES)}")
        if vendor_id is not None:
            self._vendor(vendor_id)
        if material_plant_id is not None:
            self._material_plant(material_plant_id)
        since = _d(since) if isinstance(since, str) else since
        until = _d(until) if isinstance(until, str) else (until or self.today)

        lines = {r["purchaseDocumentLineId"]: r for r in self._rows(
            "SELECT l.*, d.vendorId FROM PurchaseDocumentLine l "
            "JOIN PurchaseDocument d ON d.purchaseDocumentId = l.purchaseDocumentId")}
        docs = {r["purchaseDocumentId"]: r for r in self._rows("SELECT * FROM PurchaseDocument")}
        reqs = {r["requirementId"]: r for r in self._rows("SELECT * FROM MaterialRequirements")}
        prs = {r["purchaseRequirementId"]: r for r in self._rows("SELECT * FROM PurchaseRequirement")}

        changes = []
        for e in self._rows("SELECT * FROM Event ORDER BY timestamp, eventId"):
            attrs = json.loads(e["attributes"])
            mp, vendor = None, None
            if e["objectType"] == "PurchaseDocumentLine":
                mp, vendor = lines[e["objectId"]]["materialPlantId"], lines[e["objectId"]]["vendorId"]
            elif e["objectType"] == "PurchaseDocument":
                vendor = docs[e["objectId"]]["vendorId"]
            elif e["objectType"] == "MaterialRequirements":
                mp = reqs[e["objectId"]]["materialPlantId"]
            elif e["objectType"] == "PurchaseRequirement":
                mp = prs[e["objectId"]]["materialPlantId"]

            change = {"eventId": e["eventId"], "timestamp": e["timestamp"], "activity": e["activity"],
                      "objectType": e["objectType"], "objectId": e["objectId"],
                      "materialPlantId": mp, "vendorId": vendor,
                      "ageDays": (self.today - _d(e["timestamp"])).days,
                      "before": None, "after": None, "reason": attrs.get("reason")}
            if e["activity"] == "Delivery Date Changed":
                old, new = _d(attrs["oldConfirmedDeliveryDate"]), _d(attrs["newConfirmedDeliveryDate"])
                change.update(type="date_slip" if new > old else "date_pull_in", before=old, after=new,
                              days=(new - old).days)
                if new > old:
                    change["movedPast"] = [
                        {"requirementId": r["requirementId"], "requirementDate": r["requirementDate"],
                         "requirementType": r["requirementType"]}
                        for r in reqs.values()
                        if r["materialPlantId"] == mp and r["requirementType"] in self.committed_types
                        and old < _d(r["requirementDate"]) <= new]
            elif e["activity"] == "Requirement Registered":
                r = reqs[e["objectId"]]
                change.update(type="new_demand", after={"quantity": r["requirementQuantity"], "date": r["requirementDate"],
                                                         "requirementType": r["requirementType"], "priority": r["priority"]})
            else:
                change.update(type=ACTIVITY_TYPES.get(e["activity"], "other"), after=attrs or None)

            event_date = _d(e["timestamp"])
            if type and change["type"] != type:
                continue
            if vendor_id and vendor != vendor_id:
                continue
            if material_plant_id and mp != material_plant_id:
                continue
            if (since and event_date < since) or event_date > until:
                continue
            changes.append(change)
        return _plain({"analysisDate": self.today, "changes": changes})

    def find_critical_suppliers(self, vendor_id=None, material_plant_id=None):
        """Is a supplier standing between committed demand and a stockout?"""
        if vendor_id is not None:
            self._vendor(vendor_id)
        dependencies = []
        for mp in self._scope(material_plant_id=material_plant_id):
            mp_id = mp["materialPlantId"]
            demand, supply = self._demand(mp_id), self._open_supply(mp_id)
            base = {p["sourceId"]: p for p in self._project(mp, demand, supply) if p["kind"] == "demand"}
            for line in supply:
                if vendor_id and line["vendorId"] != vendor_id:
                    continue
                without = self._project(mp, demand, [s for s in supply if s is not line])
                for p in without:
                    if p["kind"] == "demand" and p["committed"] and p["uncovered"] > base[p["sourceId"]]["uncovered"]:
                        vendor = self._vendor(line["vendorId"])
                        check = self._eligibility(vendor, mp_id)
                        dependencies.append({
                            "materialPlantId": mp_id, "requirementId": p["sourceId"], "requirementDate": p["date"],
                            "requirementType": p["requirementType"], "lineId": line["sourceId"],
                            "vendorId": vendor["vendorId"], "vendorName": vendor["name"],
                            "onTimeDeliveryRate": vendor["onTimeDeliveryRate"], "qualityRating": vendor["qualityRating"],
                            "quantityAtRisk": p["uncovered"] - base[p["sourceId"]]["uncovered"],
                            "vendorEligible": check["eligible"], "reasons": check["reasons"]})
        return _plain({
            "analysisDate": self.today,
            "dependencies": dependencies,
            "unreliableOnCriticalPath": [d for d in dependencies if not d["vendorEligible"]],
            "assumptions_used": self._assumptions("same-day ordering", "backlog", "type decides commitment",
                                                  "north of ninety percent"),
        })

    def _reservation(self, quantity):
        """Stock already promised to an earlier plan, taken out on the analysis date."""
        return {"date": self.today, "quantity": quantity, "sourceType": "Reservation",
                "sourceId": "RESERVED for an earlier plan", "requirementType": "Transfer"}

    @staticmethod
    def _reserved_from(reserved, mp_id):
        return sum(r["quantity"] for r in reserved or [] if r["from"] == mp_id)

    def _spare(self, sender, reserved_qty=0):
        """Spare stock of a sending material-plant (concepts/spare-stock.md), after earlier reservations."""
        mp_id = sender["materialPlantId"]
        demand, supply = self._demand(mp_id), self._open_supply(mp_id)
        if reserved_qty:
            demand = demand + [self._reservation(reserved_qty)]
        timeline = self._project(sender, demand, supply)
        next_arrival = min((s["date"] for s in supply), default=None)
        if next_arrival is not None:
            window = [p for p in timeline if p["date"] < next_arrival or p["kind"] == "on_hand"]
        else:
            window = self._in_horizon(timeline, self._horizon(mp_id, supply)[0])
        low = min(window, key=lambda p: p["balance"])
        return {"spare": max(0, low["balance"] - sender["safetyStock"]), "limitedBy": low["sourceId"],
                "windowEnd": next_arrival}

    def find_transfer_options(self, material_plant_id, reserved=None):
        """Who can spare stock of the same material? `reserved`: [{from, quantity}] already promised elsewhere."""
        target = self._material_plant(material_plant_id)
        senders = self._rows("SELECT * FROM MaterialPlant WHERE materialId = ? AND materialPlantId != ? "
                             "ORDER BY materialPlantId", (target["materialId"], material_plant_id))
        options = []
        for s in senders:
            held = self._reserved_from(reserved, s["materialPlantId"])
            spare = self._spare(s, held)
            options.append({"fromMaterialPlantId": s["materialPlantId"], "plant": f"{s['plantId']} {s['plantName']}",
                            "onHand": s["onHandQuantity"], "safetyStock": s["safetyStock"],
                            "reservedForEarlierPlans": held, **spare,
                            "arrival": self.today + timedelta(days=self.transfer_days)})
        return _plain({"analysisDate": self.today, "toMaterialPlantId": material_plant_id, "options": options,
                       "assumptions_used": self._assumptions("transfer lead time", "same-day ordering", "backlog")})

    def find_alternate_vendors(self, material_plant_id):
        """Which approved vendors pass eligibility and arrive in time?"""
        mp = self._material_plant(material_plant_id)
        demand, supply = self._demand(material_plant_id), self._open_supply(material_plant_id)
        horizon, _ = self._horizon(material_plant_id, supply or self._overdue_supply(material_plant_id))
        short = self._shortfalls(self._project(mp, demand, supply), horizon, committed_only=True)
        first_need = short[0]["date"] if short else None
        incumbents = {s["vendorId"] for s in self._open_lines(material_plant_id)}
        vendors = []
        for v in self._approved_vendors(material_plant_id):
            check = self._eligibility(v, material_plant_id)
            arrival = self.today + timedelta(days=self.processing_days + v["avgLeadTimeDays"])
            vendors.append({"vendorId": v["vendorId"], "name": v["name"],
                            "role": "incumbent" if v["vendorId"] in incumbents else "alternate",
                            "onTimeDeliveryRate": v["onTimeDeliveryRate"], "qualityRating": v["qualityRating"],
                            "leadTimeDays": v["avgLeadTimeDays"], "arrival": arrival,
                            "inTimeForFirstNeed": first_need is not None and arrival <= first_need,
                            **check})
        return _plain({"analysisDate": self.today, "materialPlantId": material_plant_id, "firstNeed": first_need,
                       "vendors": vendors,
                       "assumptions_used": self._assumptions("order processing time", "north of ninety percent")})

    def rank_resolution_options(self, material_plant_id, reserved=None):
        """Best plan to close the committed gap, a fallback, and whether the plan holds.

        `reserved`: transfers already promised to earlier plans ([{from, quantity}]), so the
        same stock is never promised twice.
        """
        mp = self._material_plant(material_plant_id)
        demand, supply = self._demand(material_plant_id), self._open_supply(material_plant_id)
        horizon, _ = self._horizon(material_plant_id, supply or self._overdue_supply(material_plant_id))
        base_short = self._shortfalls(self._project(mp, demand, supply), horizon, committed_only=True)
        assumptions = self._assumptions("transfer lead time", "order processing time", "same-day ordering", "backlog",
                                        "north of ninety percent", "alternate vendor price", "type decides commitment")
        if not base_short:
            return _plain({"analysisDate": self.today, "materialPlantId": material_plant_id,
                           "status": "no_committed_shortfall", "assumptions_used": assumptions})
        gap, last_need = sum(s["uncovered"] for s in base_short), base_short[-1]["date"]

        transfers = []
        remaining = gap
        for t in sorted(self.find_transfer_options(material_plant_id, reserved)["options"], key=lambda o: -o["spare"]):
            if remaining > 0 and t["spare"] > 0 and _d(t["arrival"]) <= last_need:
                qty = min(t["spare"], remaining)
                transfers.append({"type": "transfer", "from": t["fromMaterialPlantId"], "quantity": qty,
                                  "arrival": _d(t["arrival"]), "limitedBy": t["limitedBy"],
                                  "cost": "stock already owned; no purchase cost"})
                remaining -= qty

        vendor_report = self.find_alternate_vendors(material_plant_id)["vendors"]
        alternates = sorted([v for v in vendor_report if v["role"] == "alternate" and v["eligible"]
                             and _d(v["arrival"]) <= last_need],
                            key=lambda v: (v["arrival"], -v["onTimeDeliveryRate"]))
        baseline_price = min((s["netPrice"] for s in supply), default=None)

        def order_for(vendor, actions):
            """Size an alternate-vendor order to the committed gap it can still reach."""
            arrival = _d(vendor["arrival"])
            timeline = self._evaluate(mp, demand, supply, actions)
            qty = sum(s["uncovered"] for s in self._shortfalls(timeline, horizon, committed_only=True)
                      if s["date"] >= arrival)
            if qty <= 0:
                return None
            price = f"; incumbent net price {baseline_price:.2f} per unit as baseline" if baseline_price else ""
            return {"type": "alternate_vendor", "vendorId": vendor["vendorId"], "vendorName": vendor["name"],
                    "quantity": qty, "arrival": arrival, "cost": f"price not quoted{price}"}

        candidates = []
        if transfers and remaining == 0:
            candidates.append({"name": "transfer", "actions": list(transfers)})
        elif transfers and alternates:
            top_up = order_for(alternates[0], transfers)
            if top_up:
                candidates.append({"name": "transfer + alternate vendor", "actions": transfers + [top_up]})
        if alternates:
            only = order_for(alternates[0], [])
            if only:
                candidates.append({"name": "alternate vendor only", "actions": [only]})
        if transfers and remaining > 0:
            candidates.append({"name": "transfer + split", "actions": list(transfers), "split": True})

        for c in candidates:
            timeline = self._evaluate(mp, demand, supply, c["actions"])
            left = self._shortfalls(timeline, horizon, committed_only=True)
            c["closesGap"] = not left
            c["remaining"] = left
            c["preferenceRank"] = self.preference.index(c["actions"][0]["type"])
            c["timeline"] = timeline
        candidates.sort(key=lambda c: (not c["closesGap"], c["preferenceRank"], len(c["actions"])))

        primary = candidates[0] if candidates else None
        primary_vendors = {a.get("vendorId") for a in primary["actions"]} - {None} if primary else set()
        fallback = next((c for c in candidates[1:] if not ({a.get("vendorId") for a in c["actions"]} & primary_vendors)), None)
        if fallback and fallback.get("split"):
            waits_for = min((s for s in supply), key=lambda s: s["date"], default=None)
            fallback["waitsFor"] = {"lineId": waits_for["sourceId"], "date": waits_for["date"]} if waits_for else None

        if primary and fallback is None:
            fallback = self._last_resort_fallback(primary, vendor_report)

        rejected = [{"name": c["name"], "reason": "closes the gap but ranks lower in resolution-order "
                     f"({c['actions'][0]['type']} before transfer)"} for c in candidates[1:]
                    if c is not fallback and c["closesGap"]]
        for v in vendor_report:
            if not v["eligible"]:
                rejected.append({"name": f"{'incumbent expedite' if v['role'] == 'incumbent' else 'alternate vendor'}: "
                                         f"{v['name']}",
                                 "reason": "; ".join(v["reasons"]) + (" (last resort only)" if v["role"] == "incumbent" else "")})

        result = None
        if primary:
            tier, breach = self._tier(mp, primary["timeline"], horizon)
            result = {"closesCommittedGap": primary["closesGap"], "tier": tier, "safetyStockBreach": breach,
                      "timeline": primary["timeline"], "recheck": self._recheck(primary["actions"], vendor_report, reserved)}
        strip = lambda c: {k: v for k, v in c.items() if k not in ("timeline", "preferenceRank")} if c else None
        return _plain({
            "analysisDate": self.today, "materialPlantId": material_plant_id,
            "committedGap": {"total": gap, "requirements": base_short},
            "primary": strip(primary), "resultAfterPlan": result, "fallback": strip(fallback),
            "lastResort": [r for r in rejected if r["name"].startswith("incumbent")],
            "rejected": [r for r in rejected if not r["name"].startswith("incumbent")],
            "reservedForEarlierPlans": reserved or [],
            "assumptions_used": assumptions,
        })

    @staticmethod
    def _last_resort_fallback(primary, vendor_report):
        """Fallback when no other plan exists (rules/resolution-order.md: incumbent expedite is last)."""
        if primary["closesGap"]:
            quantity = sum(a["quantity"] for a in primary["actions"] if a["type"] == "alternate_vendor")
            purpose = "if the alternate vendor can't deliver"
        else:
            quantity = sum(r["uncovered"] for r in primary["remaining"])
            purpose = "to cover what the primary plan leaves short"
        incumbents = [v for v in vendor_report if v["role"] == "incumbent"]
        if not incumbents or quantity <= 0:
            return {"name": "no viable fallback",
                    "reason": "no other plan passes the hard rules and there is no incumbent to expedite"}
        v = incumbents[0]
        return {"name": "incumbent expedite (last resort)", "purpose": purpose,
                "actions": [{"type": "incumbent_expedite", "vendorId": v["vendorId"], "vendorName": v["name"],
                             "quantity": quantity}],
                "closesGap": None,
                "caveat": "depends on the incumbent agreeing and delivering; " + "; ".join(v["reasons"] or ["eligible"])}

    def _evaluate(self, mp, demand, supply, actions):
        extra = [{"date": a["arrival"], "quantity": a["quantity"],
                  "sourceType": "PlannedTransfer" if a["type"] == "transfer" else "PlannedOrder",
                  "sourceId": f"TRANSFER from {a['from']}" if a["type"] == "transfer" else f"ORDER {a['vendorId']}"}
                 for a in actions]
        return self._project(mp, demand, supply + extra)

    def _recheck(self, actions, vendor_report, reserved=None):
        """Re-check after the plan: senders stay at or above safety stock; vendors eligible."""
        senders = []
        for a in actions:
            if a["type"] != "transfer":
                continue
            sender = self._material_plant(a["from"])
            demand = self._demand(a["from"]) + [{"date": self.today, "quantity": a["quantity"],
                                                 "sourceType": "PlannedTransfer", "sourceId": "TRANSFER out",
                                                 "requirementType": "Transfer"}]
            held = self._reserved_from(reserved, a["from"])
            if held:
                demand.append(self._reservation(held))
            supply = self._open_supply(a["from"])
            timeline = self._project(sender, demand, supply)
            horizon, _ = self._horizon(a["from"], supply)
            tier, _ = self._tier(sender, timeline, horizon)
            lowest = min(timeline, key=lambda p: p["balance"])
            senders.append({"materialPlantId": a["from"], "lowest": lowest["balance"], "lowestDate": lowest["date"],
                            "safetyStock": sender["safetyStock"], "holds": lowest["balance"] >= sender["safetyStock"],
                            "tier": tier, "timeline": timeline})
        eligible = {v["vendorId"]: v["eligible"] for v in vendor_report}
        vendors = [{"vendorId": a["vendorId"], "eligible": eligible.get(a["vendorId"], False)}
                   for a in actions if a["type"] == "alternate_vendor"]
        return {"senders": senders, "vendors": vendors,
                "holds": all(s["holds"] for s in senders) and all(v["eligible"] for v in vendors)}
