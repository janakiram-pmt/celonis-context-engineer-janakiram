"""Agent eval: run the real LLM agent and check behavior, not wording.

Not part of the unit suite (it calls Gemini). Run:
    .venv/bin/python -W ignore evals/agent_eval.py
Writes demo/agent_eval.md.
"""

import copy
import json
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app import agent, decisions  # noqa: E402
from app.tools import Session  # noqa: E402

SOURCE = json.loads((ROOT / "data" / "mock_data_schema.json").read_text())
FRANKFURT, LEIPZIG, BAVARIA = "MP-1010-8891", "MP-1020-8891", "V-2002"


def plan_steps(b):
    return sorted((a["type"], a["source"], float(a["quantity"])) for a in b.get("recommended_plan", []))


def golden_checks(session):
    b = session.accepted or {}
    text = json.dumps(b)
    called = [name for name, _, _ in session.calls]
    return {
        "briefing accepted (grounding + plan check)": bool(session.accepted),
        "called check_stock_risk": "check_stock_risk" in called,
        "called rank_resolution_options": "rank_resolution_options" in called,
        "read the context model": "read_context" in called,
        "cites EVT-0006, MREQ-7001, MREQ-7002": all(i in text for i in ("EVT-0006", "MREQ-7001", "MREQ-7002")),
        "recommends 160 from Leipzig + 40 from Bavaria":
            plan_steps(b) == sorted([("transfer", LEIPZIG, 160.0), ("alternate_vendor", BAVARIA, 40.0)]),
        "mentions Rheinmetall's 0.72 reliability": "0.72" in text or "72%" in text,
        "includes a fallback": bool(b.get("fallback")),
        "no 200-unit transfer": ("transfer", LEIPZIG, 200.0) not in plan_steps(b),
        "only Frankfurt alerted": b.get("material_plant_id") == FRANKFURT,
    }


def variant_checks(session):
    b = session.accepted or {}
    return {
        "briefing accepted": bool(session.accepted),
        "no Bavaria order": all(a["source"] != BAVARIA for a in b.get("recommended_plan", [])),
        "transfer 160 still recommended": ("transfer", LEIPZIG, 160.0) in plan_steps(b),
        "fallback is incumbent expedite": "expedite" in (b.get("fallback") or "").lower(),
    }


def variant_session(tmp):
    data = copy.deepcopy(SOURCE)  # Bavaria loses its approval for Frankfurt
    vendor = next(v for v in data["objects"]["Vendor"]["records"] if v["vendorId"] == BAVARIA)
    vendor["approvedForMaterials"].remove(FRANKFURT)
    db = Path(tmp) / "variant.db"
    decisions._loader.load(db, data).close()
    return Session(decisions.Decisions(decisions.connect(db)))


def report(name, session, transcript, checks):
    passed = sum(checks.values())
    lines = [f"## {name}: {passed}/{len(checks)} checks passed", ""]
    lines += [f"- {'✅' if ok else '❌'} {check}" for check, ok in checks.items()]
    lines += ["", f"Tool calls ({len(session.calls)}): " + ", ".join(n for n, _, _ in session.calls), ""]
    if session.accepted:
        lines += ["Recommended plan: " + json.dumps(session.accepted.get("recommended_plan")),
                  "", "Fallback: " + str(session.accepted.get("fallback")), ""]
    else:
        lines += ["No accepted briefing. Last steps:", ""] + transcript[-6:] + [""]
    return lines, passed == len(checks)


def main():
    out = ["# Agent eval", "", "Checks behavior (tools, grounding, policy, evidence), not wording.", ""]
    session, transcript = agent.run()
    lines, ok_golden = report("Golden: Frankfurt scenario", session, transcript, golden_checks(session))
    out += lines
    with tempfile.TemporaryDirectory() as tmp:
        session, transcript = agent.run(variant_session(tmp))
        lines, ok_variant = report("Variant: Bavaria not approved", session, transcript, variant_checks(session))
        session.decisions.conn.close()
    out += lines
    (ROOT / "demo").mkdir(exist_ok=True)
    (ROOT / "demo" / "agent_eval.md").write_text("\n".join(out))
    print("\n".join(out))
    sys.exit(0 if ok_golden and ok_variant else 1)


if __name__ == "__main__":
    main()
