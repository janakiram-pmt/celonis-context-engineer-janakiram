"""CLI:
    python -m app briefing [--offline] [--no-deliver]   proactive briefing (Slack if a webhook is set)
    python -m app ask "question"                         one follow-up question
    python -m app chat                                   follow-up conversation; earlier plans stay reserved
"""

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
    ask = sub.add_parser("ask", help="Ask one follow-up question.")
    ask.add_argument("question")
    sub.add_parser("chat", help="Follow-up conversation (empty line or 'exit' to quit).")
    args = parser.parse_args()

    if args.command in ("ask", "chat"):
        return converse([args.question] if args.command == "ask" else None)

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


def converse(questions=None):
    """Answer questions with the agent; read them from stdin when none are given."""
    from app import agent
    chat = agent.Chat()
    asked = iter(questions) if questions is not None else iter(lambda: input("\nYou: ").strip(), "exit")
    for question in asked:
        if not question:
            break
        answer = chat.ask(question)
        if answer:
            print(f"\nAgent: {answer['text']}\nSources: {', '.join(answer['citations'])}")
        else:
            print("\nAgent: I couldn't produce a grounded answer. See demo/chat_transcript.md.")
    DEMO_DIR.mkdir(exist_ok=True)
    (DEMO_DIR / "chat_transcript.md").write_text("\n".join(chat.agent.transcript) + "\n")


if __name__ == "__main__":
    main()
