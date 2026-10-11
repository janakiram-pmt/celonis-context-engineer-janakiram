"""The briefing: schema, validation (grounding), and rendering.

A briefing is accepted only if every number, date, and record id in it came
from a tool output, and its recommended plan matches the plan the ranking tool
returned (rules/recommendation-output.md).
"""

import json
import re

ACTION_TYPES = ["transfer", "alternate_vendor", "split", "incumbent_expedite"]

SCHEMA = {
    "type": "object",
    "properties": {
        "status": {"type": "string", "enum": ["alert", "all_clear"],
                   "description": "alert if any material-plant is Critical or Warning, else all_clear"},
        "headline": {"type": "string", "description": "One sentence: what is at risk, how much, by when."},
        "material_plant_id": {"type": "string", "description": "The material-plant at risk (empty if all_clear)."},
        "shortfall_quantity": {"type": "number", "description": "Committed shortfall from check_stock_risk."},
        "shortfall_by_date": {"type": "string", "description": "Date by which the full shortfall is reached."},
        "affected_demand": {"type": "array", "items": {"type": "string"},
                            "description": "Requirement ids short, e.g. 'MREQ-7001 (ProductionOrder, 2026-09-16, 60 short)'."},
        "cause": {"type": "string", "description": "Which line moved, from what date to what date, why, event id, vendor and its reliability."},
        "recommended_plan": {
            "type": "array",
            "description": "The primary plan from rank_resolution_options, one item per action.",
            "items": {"type": "object", "properties": {
                "type": {"type": "string", "enum": ACTION_TYPES},
                "quantity": {"type": "number"},
                "source": {"type": "string", "description": "Sending material-plant id or vendor id."},
                "arrival": {"type": "string"},
            }, "required": ["type", "quantity", "source", "arrival"]},
        },
        "result_after_plan": {"type": "string", "description": "Whether the committed gap closes, and the re-check of senders and vendors."},
        "options_considered": {"type": "array", "items": {"type": "string"},
                               "description": "Each option and why it was chosen or rejected."},
        "fallback": {"type": "string", "description": "What to do if the primary plan can't fully close the gap."},
        "watch": {"type": "array", "items": {"type": "string"}, "description": "Caveats worth watching."},
        "assumptions_used": {"type": "array", "items": {"type": "string"}},
        "healthy_summary": {"type": "string", "description": "One line on the material-plants that are fine."},
        "citations": {"type": "array", "items": {"type": "string"},
                      "description": "Record ids and context files the briefing relies on."},
    },
    "required": ["status", "headline", "healthy_summary", "citations"],
}

ALERT_FIELDS = ["material_plant_id", "shortfall_quantity", "shortfall_by_date", "affected_demand", "cause",
                "recommended_plan", "result_after_plan", "options_considered", "fallback", "assumptions_used"]

DATE = re.compile(r"\b\d{4}-\d{2}-\d{2}\b")
RECORD_ID = re.compile(r"\b(?:MREQ|PDOC|EVT|MP|PR|V)-[0-9][0-9-]*[0-9]\b")
NUMBER = re.compile(r"(?<![\w.-])\d+(?:\.\d+)?")
FREE_NUMBERS = set(range(0, 11))  # small counts ("2 options", "step 1") are not claims


def _tokens(text):
    """Dates, record ids, and numbers mentioned in a piece of text."""
    dates = set(DATE.findall(text))
    ids = set(RECORD_ID.findall(text))
    stripped = RECORD_ID.sub(" ", DATE.sub(" ", text))
    numbers = {float(n) for n in NUMBER.findall(stripped)}
    return dates, ids, numbers


def _allowed(evidence_texts):
    dates, ids, numbers = set(), set(), set()
    for text in evidence_texts:
        d, i, n = _tokens(text)
        dates |= d
        ids |= i
        numbers |= n
    numbers |= {round(n * 100, 1) for n in numbers if 0 < n < 1}  # 0.72 may be written as 72%
    return dates, ids, numbers


def validate(briefing, evidence_texts, plan=None):
    """Return a list of problems; empty means accepted.

    evidence_texts: JSON of every tool output plus any context files read.
    plan: the last rank_resolution_options result, if the agent called it.
    """
    problems = [f"missing field: {f}" for f in SCHEMA["required"] if not briefing.get(f)]
    if briefing.get("status") == "alert":
        problems += [f"alert is missing field: {f}" for f in ALERT_FIELDS if not briefing.get(f)]

    dates, ids, numbers = _allowed(evidence_texts)
    b_dates, b_ids, b_numbers = _tokens(json.dumps(briefing))
    problems += [f"date {d} does not appear in any tool output" for d in sorted(b_dates - dates)]
    problems += [f"record id {i} does not appear in any tool output" for i in sorted(b_ids - ids)]
    problems += [f"number {n:g} does not appear in any tool output"
                 for n in sorted(b_numbers - numbers - FREE_NUMBERS)]

    if briefing.get("status") == "alert":
        if not plan or not plan.get("primary"):
            problems.append("an alert needs rank_resolution_options to have produced a primary plan")
        else:
            expected = sorted((a["type"], a.get("from") or a.get("vendorId"), float(a["quantity"]))
                              for a in plan["primary"]["actions"])
            actions = [a for a in briefing.get("recommended_plan", []) if a.get("type") != "split"]
            given = sorted((a.get("type"), a.get("source"), float(a.get("quantity", 0))) for a in actions)
            if given != expected:
                problems.append(f"recommended_plan {given} does not match the ranked primary plan {expected}")
    return problems


def render_markdown(b):
    if b["status"] == "all_clear":
        return f"# Supply risk briefing: all clear\n\n{b['headline']}\n\n{b['healthy_summary']}\n"
    lines = [f"# Supply risk briefing: {b['material_plant_id']}", "", f"**{b['headline']}**", "",
             "## Recommended plan"]
    for a in b["recommended_plan"]:
        lines.append(f"- **{a['type'].replace('_', ' ')}**: {a['quantity']:g} from {a['source']}, arrives {a['arrival']}")
    lines += ["", f"**Result:** {b['result_after_plan']}", "", f"**Fallback:** {b['fallback']}", "",
              "## Why", f"- **Shortfall:** {b['shortfall_quantity']:g} by {b['shortfall_by_date']}",
              f"- **Cause:** {b['cause']}", "- **Affected demand:**"]
    lines += [f"  - {d}" for d in b["affected_demand"]]
    lines += ["", "## Options considered"] + [f"- {o}" for o in b["options_considered"]]
    if b.get("watch"):
        lines += ["", "## Watch"] + [f"- {w}" for w in b["watch"]]
    lines += ["", "## Assumptions"] + [f"- {a}" for a in b["assumptions_used"]]
    lines += ["", f"_{b['healthy_summary']}_", "", "Sources: " + ", ".join(b["citations"]), ""]
    return "\n".join(lines)


def render_slack(b):
    """Slack Block Kit message."""
    if b["status"] == "all_clear":
        return {"text": b["headline"], "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": f":white_check_mark: *{b['headline']}*\n{b['healthy_summary']}"}}]}
    plan = "\n".join(f"• *{a['type'].replace('_', ' ')}* {a['quantity']:g} from {a['source']}, arrives {a['arrival']}"
                     for a in b["recommended_plan"])
    sections = [
        f":rotating_light: *{b['headline']}*",
        f"*Recommended plan*\n{plan}\n_{b['result_after_plan']}_",
        f"*Fallback*\n{b['fallback']}",
        f"*Why*\n{b['cause']}\nAffected: " + "; ".join(b["affected_demand"]),
    ]
    if b.get("watch"):
        sections.append("*Watch*\n" + "\n".join(f"• {w}" for w in b["watch"]))
    blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": s}} for s in sections]
    blocks.append({"type": "context", "elements": [
        {"type": "mrkdwn", "text": f"{b['healthy_summary']} · Assumptions: " + "; ".join(b["assumptions_used"])}]})
    return {"text": b["headline"], "blocks": blocks}
