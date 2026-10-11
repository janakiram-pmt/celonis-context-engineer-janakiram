"""Deliver the briefing to Slack (incoming webhook), or write it to demo/ if no webhook is set."""

import json
import urllib.request

from app.config import DEMO_DIR, setting


def deliver(slack_message, enabled=True):
    """Return a short description of where the message went."""
    DEMO_DIR.mkdir(exist_ok=True)
    (DEMO_DIR / "slack_message.json").write_text(json.dumps(slack_message, indent=2) + "\n")
    url = setting("SLACK_WEBHOOK_URL")
    if not enabled or not url:
        return "written to demo/slack_message.json (no Slack webhook set)" if enabled else "delivery skipped"
    request = urllib.request.Request(url, data=json.dumps(slack_message).encode(),
                                     headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=10) as response:
        return f"posted to Slack (HTTP {response.status})"
