"""CLI: python -m app briefing [--offline] [--no-deliver]"""

import argparse
import sys

from app import briefing as briefing_mod
from app import notify, offline
from app.config import DEMO_DIR
from app.tools import Session


def main():
    parser = argparse.ArgumentParser(prog="python -m app", description="Proactive supply risk briefing.")
    sub = parser.add_subparsers(dest="command", required=True)
    run = sub.add_parser("briefing", help="Check supply risk and deliver one briefing.")
    run.add_argument("--offline", action="store_true", help="Run the same tools without the LLM (no API key needed).")
    run.add_argument("--no-deliver", action="store_true", help="Don't post to Slack.")
    args = parser.parse_args()

    DEMO_DIR.mkdir(exist_ok=True)
    if args.offline:
        session = Session()
        result = session.call("submit_briefing", {"briefing": offline.build_briefing(session)})["ok"]
        if not result["accepted"]:
            sys.exit("Offline briefing failed validation: " + "; ".join(result["problems"]))
        name = "briefing_offline.md"
    else:
        from app import agent
        session, transcript = agent.run()
        (DEMO_DIR / "sample_run.md").write_text("\n".join(transcript) + "\n")
        if not session.accepted:
            sys.exit("No briefing was accepted. See demo/sample_run.md.")
        name = "briefing.md"

    markdown = briefing_mod.render_markdown(session.accepted)
    (DEMO_DIR / name).write_text(markdown)
    print(markdown)
    print(f"[{len(session.calls)} tool calls] saved demo/{name}; "
          + notify.deliver(briefing_mod.render_slack(session.accepted), enabled=not args.no_deliver))


if __name__ == "__main__":
    main()
