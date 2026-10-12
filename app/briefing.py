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
                "source_name": {"type": "string", "description": "Plant or vendor name, e.g. 'Leipzig Distribution'."},
                "arrival": {"type": "string"},
            }, "required": ["type", "quantity", "source", "arrival"]},
        },
        "result_after_plan": {"type": "string", "description": "Whether the committed gap closes, and the re-check of senders and vendors."},
        "options_considered": {"type": "array", "items": {"type": "string"},
                               "description": "Each option and why it was chosen or rejected."},
        "fallback": {"type": "string", "description": "What to do if the primary plan can't fully close the gap."},
        "watch": {"type": "array", "items": {"type": "string"}, "description": "Caveats worth watching."},
        "assumptions_used": {"type": "array", "items": {"type": "string"}},
        "other_findings": {"type": "array", "items": {"type": "string"},
                           "description": "Every other Critical/Warning material-plant, in findingOrder: id, tier, "
                                          "shortfall, date. Planned one at a time after this one is resolved."},
        "next_steps": {"type": "string", "description": "What to do first, and how to get the next alert planned."},
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
CHAT_HINT = ("Questions? Run `python -m app chat` (e.g. 'any other alerts today?', "
             "'why not ask Rheinmetall to expedite?', 'plan the next alert').")


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


def _ungrounded(text, evidence_texts):
    """Dates, ids, and numbers in `text` that appear in no tool output."""
    dates, ids, numbers = _allowed(evidence_texts)
    b_dates, b_ids, b_numbers = _tokens(text)
    return ([f"date {d} does not appear in any tool output" for d in sorted(b_dates - dates)]
            + [f"record id {i} does not appear in any tool output" for i in sorted(b_ids - ids)]
            + [f"number {n:g} does not appear in any tool output" for n in sorted(b_numbers - numbers - FREE_NUMBERS)])


def validate_answer(text, citations, evidence_texts):
    """Ask mode: an answer is accepted only if its numbers, dates, and ids come from tool outputs."""
    if not text:
        return ["missing answer text"]
    return _ungrounded(json.dumps({"text": text, "citations": citations}), evidence_texts)


def _claims(briefing, finding):
    """Key facts of the main finding must match the tool exactly, not just appear somewhere."""
    problems = []
    short = finding["committedShortfall"]
    if short["total"]:
        if float(briefing.get("shortfall_quantity") or 0) != float(short["total"]):
            problems.append(f"shortfall_quantity must be {short['total']:g} (check_stock_risk)")
        if briefing.get("shortfall_by_date") != short["requirements"][-1]["date"]:
            problems.append(f"shortfall_by_date must be {short['requirements'][-1]['date']} (check_stock_risk)")
    lines = briefing.get("affected_demand") or []
    for r in short["requirements"]:
        ok = any(r["requirementId"] in line and r["date"] in line and float(r["uncovered"]) in _tokens(line)[2]
                 for line in lines)
        if not ok:
            problems.append(f"affected_demand must pair {r['requirementId']} with {r['uncovered']:g} short on {r['date']}")
    cause = briefing.get("cause") or ""
    for c in finding.get("why", {}).get("vendorChanges", []):
        ref = c.get("eventId") or c["objectId"]
        for fact in (ref, c.get("before"), c.get("after")):
            if fact and fact not in cause:
                problems.append(f"cause must mention {fact} ({ref})")
    return problems


def validate(briefing, evidence_texts, plan=None, risk=None):
    """Return a list of problems; empty means accepted.

    evidence_texts: JSON of every tool output plus any context files read.
    plan: the rank_resolution_options result for the briefing's material-plant.
    risk: check_stock_risk over all material-plants (to check nothing is dropped and key facts match).
    """
    problems = [f"missing field: {f}" for f in SCHEMA["required"] if not briefing.get(f)]
    if briefing.get("status") == "alert":  # 0 and [] are valid values (e.g. a warning with no committed shortfall)
        problems += [f"alert is missing field: {f}" for f in ALERT_FIELDS if briefing.get(f) in (None, "")]

    problems += _ungrounded(json.dumps(briefing), evidence_texts)

    if risk is not None:
        order = risk.get("findingOrder", [])
        main = briefing.get("material_plant_id")
        if order and briefing.get("status") != "alert":
            problems.append(f"status must be alert: {', '.join(order)} flagged by check_stock_risk")
        if order and main and main != order[0]:
            problems.append(f"the main finding must be {order[0]} (first in findingOrder)")
        others = " ".join(briefing.get("other_findings") or [])
        problems += [f"other_findings must list {mp_id}" for mp_id in order[1:] if mp_id not in others]
        finding = next((m for m in risk["materialPlants"] if m["materialPlantId"] == main), None)
        if finding and briefing.get("status") == "alert":
            problems += _claims(briefing, finding)

    no_committed_gap = bool(plan) and plan.get("status") == "no_committed_shortfall"
    if briefing.get("status") == "alert" and no_committed_gap:
        if briefing.get("recommended_plan"):  # rules/spending-policy.md: no premium spend without committed demand
            problems.append("no committed shortfall: recommended_plan must be empty (no premium spend)")
    elif briefing.get("status") == "alert":
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


def _named(action):
    """'Leipzig Distribution (MP-1020-8891)' when a name is known, else the id."""
    name = action.get("source_name")
    return f"{name} ({action['source']})" if name else action["source"]


def render_markdown(b):
    if b["status"] == "all_clear":
        return f"# Supply risk briefing: all clear\n\n{b['headline']}\n\n{b['healthy_summary']}\n\n{CHAT_HINT}\n"
    lines = ["# Supply risk briefing", "", f"**{b['headline']}**", ""]
    if b.get("other_findings"):
        lines += [f"**You have {len(b['other_findings'])} more alert(s). Resolve this one first, then run "
                  "`python -m app chat` and ask for the next alert:**"]
        lines += [f"- {o}" for o in b["other_findings"]] + [""]
    lines += ["## Recommended plan"]
    for a in b["recommended_plan"]:
        lines.append(f"- **{a['type'].replace('_', ' ')}**: {a['quantity']:g} from {_named(a)}, arrives {a['arrival']}")
    lines += ["", f"**Result:** {b['result_after_plan']}", "", f"**Fallback:** {b['fallback']}", "",
              "## Why", f"- **Shortfall:** {b['shortfall_quantity']:g} by {b['shortfall_by_date']}",
              f"- **Cause:** {b['cause']}", "- **Affected demand:**"]
    lines += [f"  - {d}" for d in b["affected_demand"]]
    lines += ["", "## Options considered"] + [f"- {o}" for o in b["options_considered"]]
    if b.get("watch"):
        lines += ["", "## Watch"] + [f"- {w}" for w in b["watch"]]
    lines += ["", "## Assumptions"] + [f"- {a}" for a in b["assumptions_used"]]
    lines += ["", f"_{b['healthy_summary']}_", "", "Sources: " + ", ".join(b["citations"]), "", CHAT_HINT, ""]
    return "\n".join(lines)


def render_slack(b):
    """Slack Block Kit message."""
    if b["status"] == "all_clear":
        return {"text": b["headline"], "blocks": [
            {"type": "section", "text": {"type": "mrkdwn", "text": f":white_check_mark: *{b['headline']}*\n{b['healthy_summary']}"}},
            {"type": "context", "elements": [{"type": "mrkdwn", "text": CHAT_HINT}]}]}
    plan = "\n".join(f"• *{a['type'].replace('_', ' ')}* {a['quantity']:g} from {_named(a)}, arrives {a['arrival']}"
                     for a in b["recommended_plan"])
    sections = [f":rotating_light: *{b['headline']}*"]
    if b.get("other_findings"):
        sections.append(f"*{len(b['other_findings'])} more alert(s): resolve this one first*\n"
                        + "\n".join(f"• {o}" for o in b["other_findings"]))
    sections += [
        f"*Recommended plan*\n{plan}\n_{b['result_after_plan']}_",
        f"*Fallback*\n{b['fallback']}",
        f"*Why*\n{b['cause']}\nAffected: " + "; ".join(b["affected_demand"]),
    ]
    if b.get("watch"):
        sections.append("*Watch*\n" + "\n".join(f"• {w}" for w in b["watch"]))
    blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": s}} for s in sections]
    blocks.append({"type": "context", "elements": [
        {"type": "mrkdwn", "text": f"{b['healthy_summary']} · Assumptions: " + "; ".join(b["assumptions_used"])}]})
    blocks.append({"type": "context", "elements": [{"type": "mrkdwn", "text": CHAT_HINT}]})
    return {"text": b["headline"], "blocks": blocks}
