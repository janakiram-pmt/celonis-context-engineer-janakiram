"""Deterministic pipeline: the same tool calls as the agent, composed without an LLM.

Lets reviewers run the app without an API key, and is the reference the agent
eval compares against.
"""


def _g(x):
    return f"{x:g}"


def build_briefing(session):
    risk = session.call("check_stock_risk", {})["ok"]
    plants = risk["materialPlants"]
    by_id = {m["materialPlantId"]: m for m in plants}
    flagged = [by_id[mp_id] for mp_id in risk["findingOrder"]]
    healthy = [m for m in plants if m not in flagged]
    healthy_summary = (f"{len(healthy)} other material-plants checked: "
                       + ", ".join(f"{m['material']} at {m['plant']} ({m['materialPlantId']}) {m['tier']}"
                                   for m in healthy) + ".")
    if not flagged:
        return {"status": "all_clear", "headline": f"All {len(plants)} material-plants are covered.",
                "healthy_summary": healthy_summary, "citations": [m["materialPlantId"] for m in plants]}

    mp = flagged[0]
    mp_id = mp["materialPlantId"]
    others = [_finding_line(m) for m in flagged[1:]]
    next_steps = ("Resolve this alert first, then run `python -m app chat` and ask for the next alert; "
                  "stock promised here is reserved when the next one is planned." if others else
                  "Approve the recommended plan; re-run the check after the orders are booked.")
    why = mp["why"]
    plan = session.call("rank_resolution_options", {"material_plant_id": mp_id})["ok"]
    session.call("find_transfer_options", {"material_plant_id": mp_id})
    session.call("find_alternate_vendors", {"material_plant_id": mp_id})

    short = mp["committedShortfall"]
    affected = [f"{r['requirementId']} ({r['requirementType']}, {r['date']}, {_g(r['uncovered'])} short)"
                for r in short["requirements"]]
    causes = []
    for c in why["vendorChanges"]:
        reliability = (f"{c['vendorName']} ({c['vendorId']}), on-time {c['onTimeDeliveryRate']:.2f}, "
                       + ("eligible" if c["vendorEligible"] else "fails vendor eligibility"))
        if c["type"] == "overdue":
            causes.append(f"{c['objectId']} ({reliability}) was due {c['before']} and is still not received.")
        else:
            causes.append(f"{c['objectId']} ({reliability}) moved from {c['before']} to {c['after']} "
                          f"({c['reason']}, {c['eventId']}).")
    causes.append(f"{why['note']} Gap as promised: {_g(why['gapAsPromised'])}; now: {_g(why['gapNow'])}.")

    if plan.get("status") == "no_committed_shortfall":
        headline = f"{mp['material']} at {mp['plant']} ({mp_id}) is {mp['tier']}: below safety stock, no committed shortfall."
        return {"status": "alert", "headline": headline, "material_plant_id": mp_id,
                "shortfall_quantity": 0, "shortfall_by_date": mp["safetyStockBreach"]["firstDate"],
                "affected_demand": [f"{s['requirementId']} ({s['requirementType']}, {_g(s['uncovered'])} short)"
                                    for s in mp["otherShortfall"]] or ["none committed"],
                "cause": " ".join(causes), "recommended_plan": [],
                "result_after_plan": "No premium spend: only forecast demand or safety stock is affected.",
                "options_considered": ["Re-plan the forecast or place a normal replenishment order."],
                "fallback": "Re-check on the next run.", "assumptions_used": _assumptions(risk, plan),
                "other_findings": others, "next_steps": next_steps,
                "healthy_summary": healthy_summary, "citations": [mp_id]}

    primary, result = plan["primary"], plan["resultAfterPlan"]
    steps = [{"type": a["type"], "quantity": a["quantity"], "source": a.get("from") or a.get("vendorId"),
              "source_name": a.get("fromName") or a.get("vendorName"), "arrival": a["arrival"]}
             for a in primary["actions"]]
    names = {m["materialPlantId"]: m["plant"] for m in plants}
    senders = "; ".join(f"{names.get(s['materialPlantId'], '')} ({s['materialPlantId']}) lowest {_g(s['lowest'])} "
                        f"vs safety stock {_g(s['safetyStock'])}"
                        f" ({'holds' if s['holds'] else 'breaks'})" for s in result["recheck"]["senders"])
    result_text = ("Closes the committed gap." if result["closesCommittedGap"] else
                   "Does not fully close the committed gap: " + ", ".join(
                       f"{r['requirementId']} {_g(r['uncovered'])} short" for r in primary["remaining"]) + ".")
    result_text += f" {mp['plant']} ({mp_id}) tier after the plan: {result['tier']}."
    if senders:
        result_text += f" Sender re-check: {senders}."

    options = [f"Chosen: {primary['name']}."]
    options += [f"Rejected: {r['name']} ({r['reason']})." for r in plan["rejected"]]
    options += [f"Last resort: {r['name']} ({r['reason']})." for r in plan["lastResort"]]

    watch = []
    breach = result.get("safetyStockBreach") or {}
    for period in breach.get("periods", []):
        if period["inHorizon"] and period["start"] != risk["analysisDate"]:
            watch.append(f"{mp['plant']} ({mp_id}) below safety stock from {period['start']} to "
                         f"{period['end'] or 'beyond the data'}"
                         + (f", restored by {period['restoredBy']}" if period["restoredBy"] else "") + ".")
    for c in why["vendorChanges"]:
        if not c["vendorEligible"]:
            watch.append(f"Recovery depends on {c['vendorName']} ({c['vendorId']}, on-time "
                         f"{c['onTimeDeliveryRate']:.2f}).")

    return {
        "status": "alert",
        "headline": (f"{mp['material']} at {mp['plant']} ({mp_id}): {_g(short['total'])} units of committed demand "
                     f"uncovered by {short['requirements'][-1]['date']}."),
        "material_plant_id": mp_id,
        "shortfall_quantity": short["total"],
        "shortfall_by_date": short["requirements"][-1]["date"],
        "affected_demand": affected,
        "cause": " ".join(causes),
        "recommended_plan": steps,
        "result_after_plan": result_text,
        "options_considered": options,
        "fallback": _fallback(plan["fallback"]),
        "watch": watch,
        "other_findings": others,
        "next_steps": next_steps,
        "assumptions_used": _assumptions(risk, plan),
        "healthy_summary": healthy_summary,
        "citations": sorted({mp_id, *[r["requirementId"] for r in short["requirements"]],
                             *[c.get("eventId") or c["objectId"] for c in why["vendorChanges"]],
                             "rules/resolution-order.md", "rules/alerting.md"}),
    }


def _finding_line(m):
    short = m["committedShortfall"]
    if short["total"]:
        return (f"{m['materialPlantId']} ({m['material']}, {m['plant']}): {m['tier']}, "
                f"{_g(short['total'])} committed short by {short['requirements'][-1]['date']}")
    return f"{m['materialPlantId']} ({m['material']}, {m['plant']}): {m['tier']}, below safety stock"


def _fallback(fallback):
    if not fallback:
        return "No viable fallback."
    if fallback.get("name") == "no viable fallback":
        return f"No viable fallback: {fallback['reason']}."
    if fallback.get("split"):
        left = ", ".join(f"{r['requirementId']} {_g(r['uncovered'])}" for r in fallback["remaining"])
        waits = fallback.get("waitsFor")
        tail = (f", waiting for {waits['lineId']} from {waits['vendorName']} ({waits['vendorId']}) on {waits['date']}"
                if waits else "")
        return f"{fallback['name']}: cover what arrives in time; still short {left}{tail}."
    actions = "; ".join(f"{a['type'].replace('_', ' ')} {_g(a['quantity'])} from {a.get('vendorName') or a.get('from')}"
                        for a in fallback.get("actions", []))
    caveat = f" Caveat: {fallback['caveat']}." if fallback.get("caveat") else ""
    return f"{fallback['name']}: {actions}.{caveat}"


def _assumptions(*results):
    seen = {}
    for r in results:
        for a in r.get("assumptions_used", []):
            seen.setdefault(a["name"], f"{a['name']}: {a['value']}")
    return list(seen.values())
