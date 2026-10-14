# Inventory Risk Agent

An agent that watches inventory and inbound supply, notices when a supplier change puts committed demand at risk, and sends planners an evidence-backed briefing with a recommended plan and a fallback. Every number comes from deterministic tools; the language model decides what to investigate and explains the result.

On the challenge data it finds the one real exposure: **Frankfurt's bearing housings, 200 units of committed demand uncovered by 18 September** after Rheinmetall moved a delivery from 11 to 25 September. It recommends **transferring 160 units from Leipzig and ordering 40 from Bavaria Precision Parts**, with a split delivery as the fallback.

## Start here (5 minutes)

1. **[`demo/briefing.md`](demo/briefing.md)**: the briefing the live agent produced (also as a Slack message in [`demo/slack_message.json`](demo/slack_message.json)).
2. **[`demo/sample_run.md`](demo/sample_run.md)**: the agent's run step by step: every tool call, its result, and the briefing passing the grounding check.
3. **[`blueprint.md`](blueprint.md)**: the product narrative: problem and vision, how the agent works, how it scales, rollout and KPIs.
4. **[`context-model/index.md`](context-model/index.md)**: the semantic layer the agent reads first.
5. Run it yourself without an API key: `python -m app briefing --offline` (see below).

## Stack and why

| Tool | Used for | Why |
|---|---|---|
| **Claude Code** | Building the project | The AI coding assistant for this challenge |
| **Gemini** (`gemini-flash-latest`) | The agent at runtime | Free tier, reliable tool calling |
| **GitHub** | Repository and history | Required for submission |
| **Slack** (incoming webhook) | Delivering the briefing | The product's point is to push the alert to planners. This is a deliberate fourth tool; without a webhook the message is written to `demo/slack_message.json`, so the app runs on three |

Everything else is in the repo: Python 3.9+, SQLite, and a Markdown/YAML context model.

## Run it

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 79 deterministic tests, no API key needed (under a second)
.venv/bin/python -W ignore -m unittest discover tests -v

# The briefing without the language model: same tools, same validation
.venv/bin/python -W ignore -m app briefing --offline --no-deliver
```

With a Gemini key in `.env` (see below):

```bash
# The live agent: runs the check, validates the briefing, posts to Slack if a webhook is set
.venv/bin/python -W ignore -m app briefing

# Follow-up questions
.venv/bin/python -W ignore -m app ask "Any alerts today?"
.venv/bin/python -W ignore -m app chat

# The agent evaluation (real model; checks behavior, not wording); writes demo/agent_eval.md
.venv/bin/python -W ignore evals/agent_eval.py
```

The SQLite database is built automatically from `data/mock_data_schema.json` on first run (or explicitly with `python3 data-model/load_sqlite.py`). Each run saves its briefing and transcript to `demo/`. The free Gemini tier allows about 20 requests a day per model; a briefing uses 5–10.

## Environment variables

Copy [`.env.example`](.env.example) to `.env` (never committed):

| Variable | Required | Purpose |
|---|---|---|
| `GEMINI_API_KEY` | For the live agent | Free key from [Google AI Studio](https://aistudio.google.com/apikey). Not needed for `--offline` or the tests |
| `GEMINI_MODEL` | No | Model id; default `gemini-flash-latest` |
| `SLACK_WEBHOOK_URL` | No | Slack incoming webhook. Without it, the message is saved to `demo/slack_message.json` |

## What's where

| Folder | Contents |
|---|---|
| [`data-model/`](data-model/erd.md) | Task 1, relational layer: ERD, SQLite schema, loader |
| [`context-model/`](context-model/index.md) | Task 1, semantic layer: objects, concepts, and rules (with assumptions), read by the agent and the tools |
| [`app/`](app/) | Task 2: decision tools (`decisions.py`), tool registry (`tools.py`), agent loop (`agent.py`), briefing and grounding check (`briefing.py`), offline pipeline, Slack delivery, CLI |
| [`tests/`](tests/) | 79 deterministic tests: data model, context model, tools, scenarios, registry, grounding |
| [`evals/`](evals/agent_eval.py) | Live agent evaluation: the Frankfurt case and a variant |
| [`demo/`](demo/) | Recorded runs: briefings, transcript, Slack message |
| [`notes/`](notes/initial-reading.md) | First notes from reading the challenge |
| [`docs/`](docs/challenge.md) | The original challenge brief and data walkthrough |
| [`blueprint.md`](blueprint.md) | Task 3: the product narrative |
