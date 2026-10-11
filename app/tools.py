"""Tool registry: what the LLM can call, and a session that records every result.

Descriptions stay short and point to the context-model file that defines the
concept or rule; definitions are never repeated here.
"""

import json

from app import briefing as briefing_mod
from app.config import CONTEXT_DIR
from app.decisions import Decisions

MP = {"type": "string", "description": "Material-plant id, e.g. MP-1010-8891."}

TOOLS = {
    "read_context": {
        "description": "Read a context-model file (start with index.md). Meaning and rules live there.",
        "parameters": {"type": "object", "properties": {
            "path": {"type": "string", "description": "Path inside context-model/, e.g. index.md or rules/alerting.md."}},
            "required": ["path"]},
    },
    "check_stock_risk": {
        "description": "Is anything at risk, how badly, and why? Tier, projected-stock timeline, committed shortfall, "
                       "safety-stock breach, and for Critical/Warning the cause. See concepts/shortfall.md, rules/alerting.md.",
        "parameters": {"type": "object", "properties": {
            "material_plant_id": MP,
            "plant_id": {"type": "string", "description": "Plant id, e.g. 1010."},
            "material_id": {"type": "string", "description": "Material id, e.g. MAT-8891."}}},
    },
    "find_changes": {
        "description": "What changed? Events from the log, filterable. See concepts/date-slip.md.",
        "parameters": {"type": "object", "properties": {
            "type": {"type": "string", "description": "e.g. date_slip, new_demand, receipt."},
            "vendor_id": {"type": "string"}, "material_plant_id": MP,
            "since": {"type": "string", "description": "ISO date."}, "until": {"type": "string", "description": "ISO date."}}},
    },
    "find_critical_suppliers": {
        "description": "Which open PO lines does committed demand depend on, and are their vendors reliable? "
                       "See concepts/critical-path-supply.md.",
        "parameters": {"type": "object", "properties": {"vendor_id": {"type": "string"}, "material_plant_id": MP}},
    },
    "find_transfer_options": {
        "description": "Which other plants can spare stock of the same material? See concepts/spare-stock.md, rules/transfer-limit.md.",
        "parameters": {"type": "object", "properties": {"material_plant_id": MP}, "required": ["material_plant_id"]},
    },
    "find_alternate_vendors": {
        "description": "Which approved vendors pass eligibility and arrive in time? See rules/vendor-eligibility.md.",
        "parameters": {"type": "object", "properties": {"material_plant_id": MP}, "required": ["material_plant_id"]},
    },
    "rank_resolution_options": {
        "description": "Best plan to close the committed gap, a fallback, and whether the plan holds. "
                       "See rules/resolution-order.md.",
        "parameters": {"type": "object", "properties": {"material_plant_id": MP}, "required": ["material_plant_id"]},
    },
    "submit_briefing": {
        "description": "Submit the final briefing. It is rejected unless every number, date, and id comes from a tool "
                       "output and the plan matches rank_resolution_options. See rules/recommendation-output.md.",
        "parameters": {"type": "object", "properties": {"briefing": briefing_mod.SCHEMA}, "required": ["briefing"]},
    },
}


class Session:
    """Runs tools for one briefing and keeps every output as grounding evidence."""

    def __init__(self, decisions=None):
        self.decisions = decisions or Decisions()
        self.calls = []          # (name, args, result)
        self.evidence = []       # JSON text of every tool output and context file read
        self.last_plan = None
        self.accepted = None     # the accepted briefing, once submitted

    def call(self, name, args):
        args = {k: v for k, v in (args or {}).items() if v not in (None, "")}
        try:
            if name not in TOOLS:
                raise ValueError(f"unknown tool {name!r}")
            result = getattr(self, f"_{name}")(**args)
            response = {"ok": result}
        except (LookupError, ValueError, TypeError) as e:
            response = {"error": str(e)}
        self.calls.append((name, args, response))
        if "ok" in response and name != "submit_briefing":
            self.evidence.append(json.dumps(response["ok"]))
        return response

    def _read_context(self, path):
        target = (CONTEXT_DIR / path).resolve()
        if CONTEXT_DIR.resolve() not in target.parents or target.suffix != ".md" or not target.exists():
            raise LookupError(f"{path} is not a file in context-model/")
        return {"path": path, "text": target.read_text()}

    def _check_stock_risk(self, **kw):
        return self.decisions.check_stock_risk(**kw)

    def _find_changes(self, **kw):
        return self.decisions.find_changes(**kw)

    def _find_critical_suppliers(self, **kw):
        return self.decisions.find_critical_suppliers(**kw)

    def _find_transfer_options(self, material_plant_id):
        return self.decisions.find_transfer_options(material_plant_id)

    def _find_alternate_vendors(self, material_plant_id):
        return self.decisions.find_alternate_vendors(material_plant_id)

    def _rank_resolution_options(self, material_plant_id):
        self.last_plan = self.decisions.rank_resolution_options(material_plant_id)
        return self.last_plan

    def _submit_briefing(self, briefing):
        problems = briefing_mod.validate(briefing, self.evidence, self.last_plan)
        if problems:
            return {"accepted": False, "problems": problems}
        self.accepted = briefing
        return {"accepted": True}
