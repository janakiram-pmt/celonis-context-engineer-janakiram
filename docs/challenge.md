# Context Engineer Challenge

**Role:** Senior Application Product Manager
**Domain focus:** Supply Chain / Procurement
**Time budget:** ~4 hours
**Format:** Take-home. You submit a Git repository (private, with a reviewer invited — see [Submission guidelines](#submission-guidelines)).

---

## Getting started

You received this challenge as a zip. Turn it into your own Git repository before you start:

```bash
unzip context-engineer-challenge.zip && cd context-engineer-challenge
git init
git add . && git commit -m "Start from challenge template"
```

Then create a **new, empty repository** in your own GitHub account (keep it **private**) and push to it:

```bash
git remote add origin https://github.com/<your-username>/celonis-context-engineer-<yourname>.git
git branch -M main
git push -u origin main
```

From here it's yours — commit as you go (we read the history), and follow the [Submission guidelines](#submission-guidelines) when you're done.

---

## Why this challenge exists

At Celonis we build applications on top of a **Context Model** — a semantic layer that turns raw enterprise records (purchase orders, vendors, inventory) into objects, relationships, and events that both people *and* large language models can reason over. Increasingly, the applications we ship on top of that model are **agentic**: they don't just display data, they detect a problem, reason about it, and drive it toward resolution.

This challenge tests exactly that hybrid muscle. We want to see you:

- turn a flat dataset into a **context/knowledge model** an LLM can navigate,
- **orchestrate an LLM/agent** to solve a real operational bottleneck on top of it, and
- **frame the product story** the way you'd pitch it to an executive buyer.

We are explicitly **not** testing supply-chain expertise. The scenario is deliberately lightweight and generalizable. We are testing your **technical execution, AI fluency, and product judgment**, and how well you use AI tooling to move fast.

---

## The scenario

You've been dropped into a mid-sized manufacturer's procurement operation. One fact matters:

> On **2026-09-01**, vendor *Rheinmetall Components GmbH* pushed the confirmed delivery date of purchase order line **PDOC-4500001234-10** (400 units of *Bearing Housing, Cast*) from **2026-09-11** to **2026-09-25** because of a capacity constraint.

That line is the inbound supply for material *MAT-8891* at the Frankfurt plant (**1010**). The dataset also contains several other materials, plants, vendors and purchase orders that are running normally — so part of the job is to separate signal from noise. Whether this delay actually puts the plant at risk — and if so, by how much and what to do about it — is for you to work out from the data. Someone in procurement has to notice it, quantify it, and decide, fast.

> We've deliberately **not** pre-computed the impact or handed you a list of fixes. Deriving the risk and discovering the realistic options is part of the task. There's no single "correct" answer — we're evaluating how you reason, not whether you match a key.

Your job is to build the foundation and the application that make that decision faster and better. Everything you need is in [`data/mock_data_schema.json`](../data/mock_data_schema.json). The data is **pre-cleansed** — clean IDs, intact foreign keys, no missing values. You should spend your time on modeling, orchestration, and product thinking, **not** on data janitorial work. A human-readable walkthrough of the model lives in [`docs/data_model.md`](data_model.md).

Before you build, read the discovery call transcript in [`discovery_interview.md`](../discovery_interview.md) — a short session with the customer's operational leads. It is your **requirements source**: it tells you which resolution actions they consider viable, which they prefer and which they avoid (and why), how they prioritise, the constraints you must respect, and the specific situations they want flagged (and the ones they *don't*, to avoid alert fatigue). Because the UI is yours to shape, this business context — not a rigid spec — is what your solution should embody.

---

## Your tasks

### Task 1 — Context & Data Modeling *(foundation)*

Build a small **data and knowledge base** from the provided source, in **two layers**:

1. **A classical relational model.** Represent the objects and their foreign-key relationships the way a database or a Celonis process model would (tables/entities, keys, joins). A diagram plus DDL, an ERD, or equivalent is fine.
2. **A context / semantic model that an LLM can understand.** This is the layer that lets an agent reason without you hard-coding every query. Structure it however you'd defend as production-sensible — a **file system** of markdown/YAML, a **Notion** workspace, an **Obsidian** vault, a graph, or a retrieval index. It should capture what each object *means*, how objects relate, the business semantics an agent needs (the terms that define risk in this scenario), **and the business rules and preferences the customer describes in `discovery_interview.md`** so the agent can apply them.

**What we're looking for:** a clear separation between the raw relational truth and the semantic layer built on top of it, and semantics rich enough that an LLM can answer "is plant 1010 at risk, and why?" without you spoon-feeding it the join logic.

### Task 2 — Agentic Application *(execution)*

Build a **functional application** on top of your Task 1 foundation that **resolves the bottleneck in the scenario**. It should, at minimum, detect the risk, reason over the available options and their trade-offs, and produce a **defensible recommendation with the evidence it used** — one that **honors the customer's stated preferences and surfaces the cases they asked you to watch for** (see [`discovery_interview.md`](../discovery_interview.md)).

You choose the shape:

- a **SaaS-style interface + an agent** (e.g., a lightweight web app with an assistant), or
- a **purely agentic application** (e.g., a CLI/agent loop, a chat agent with tools, a scheduled agent that emits a briefing).

Your recommendation must rest on at least one **deterministic decision function** that the agent *calls* — e.g., a coverage/shortfall calculator or a cost-vs-lead-time-vs-reliability scorer — rather than having the LLM invent the numbers. Treat this as a small "decision intelligence" function the agent uses as a tool; a simple optimization or scoring routine is exactly right, and it's the pattern that keeps agentic recommendations trustworthy at enterprise scale.

**What we're looking for:** real **LLM orchestration** — tool/function calling, retrieval over your context model, and/or a multi-step agent loop — not a single hard-coded prompt — with the critical numbers computed in code, not generated by the model. The app should actually run against the provided data and produce output we can inspect.

### Task 3 — Product Blueprint *(narrative)*

Write a strategic product narrative as **`blueprint.md`** at the repo root. Use [`blueprint_TEMPLATE.md`](../blueprint_TEMPLATE.md) as a starting scaffold (optional but recommended). It must explain:

- **Architecture** — the choices you made and *why* (context model design, orchestration pattern, where the LLM sits, how you'd keep it grounded and trustworthy).
- **How it scales** — from this toy dataset to millions of objects and other process domains.
- **Strategic value** — the case you'd make to an executive buyer: what this changes operationally and commercially, and how you'd measure it.

**What we're looking for:** a coherent story that connects the technical choices to business value — the way a product leader would defend this in a room with both engineers and a CFO.

---

## Tooling & ground rules

- **Use AI aggressively.** This challenge assumes you'll pair with an AI coding/reasoning assistant. That's the point — we want to see your AI fluency, not watch you type boilerplate.
- **Keep it to at most three tools.** A realistic, sufficient stack is, for example: **an AI assistant** (Claude, Cursor, Codex, etc.), **GitHub**, and **one build/host/knowledge tool** (Render, Vercel, Notion, or Obsidian). Don't burn your budget evaluating tooling — pick a lean stack and go. All of these have free or low-cost tiers.
- **Bring your own model key.** If your app calls an LLM *at runtime*, you'll need an **API key**, which is separate from a chat subscription (e.g., a Claude Pro or ChatGPT Plus plan does **not** include API access). Pay-as-you-go API usage for this challenge costs cents, but if you'd rather avoid any cost, a **free tier is completely fine** — e.g., Google Gemini's free tier, Groq's free tier, or a local model via Ollama. Whatever you pick, **never commit secrets** — use environment variables and document them in `.env.example`.
- **The three-tool ceiling, practically.** The assistant you code with and the model your app calls at runtime can be the **same vendor** (counts as one tool), and your knowledge/context layer can just be **files in the repo** (no extra tool). So a lean, compliant stack is e.g. *one AI vendor + GitHub + one host (Render/Vercel)* — or drop the host entirely and ship a CLI/agent.
- **Scope for ~4 hours.** We are not looking for a polished production app. We're looking for sharp judgment about what to build, what to fake, and what to defend in the blueprint. It's better to ship a thin end-to-end slice than a half-built masterpiece.
- **AI-assisted is expected; understanding is required.** You should be able to explain and defend every choice in a follow-up conversation.

---

## What to submit

A single GitHub repository containing:

```
your-submission/
├── README.md              # How to run it, your stack, env vars, and a 3-5 min "start here" tour
├── blueprint.md           # Task 3 — the product narrative
├── context-model/         # Task 1 — your semantic/context model (files, or a link + export to Notion/Obsidian)
├── data-model/            # Task 1 — your relational model (DDL, ERD, or diagram)
├── app/                   # Task 2 — the runnable application + orchestration code
├── demo/                  # A sample run / transcript showing the app working end-to-end (no keys needed to review)
└── .env.example           # Any keys/vars needed, with placeholder values (never commit real secrets)
```

This is a suggested layout — adapt it, but make it easy to navigate.

### Submission guidelines

1. Push your work to the **private** repo you created in [Getting started](#getting-started) (`celonis-context-engineer-<yourname>`), and add the reviewer named in your invitation email as a **read-only collaborator**.
2. Commit incrementally with clear messages — we do read the git history to understand your process.
3. In your `README.md`, include: **your chosen stack (and why)**, exact **run instructions**, required **environment variables**, and a short **"start here"** pointer telling a reviewer what to open first and how to see the app work end-to-end.
4. Commit a **demo transcript or sample output** (e.g., `demo/sample_run.md` or a short recording/screenshots) showing the app working end-to-end on the provided data. Reviewers won't have your API key, so this is how we see it actually run — treat it as required, not optional.
5. If any part depends on a hosted tool (deployed app, Notion page, Obsidian vault), include a **link** *and* a committed **export/snapshot** so it can be reviewed even if the hosted version goes away.
6. Please keep your solution **private** — don't post it or the challenge publicly. Access via the reviewer invite is all we need.
7. Reply to your invitation email with the **repository URL** when you're done.

> **A note on grading:** your submission is read with an AI-assisted first pass and then reviewed by the hiring team. We publish our **evaluation criteria** ([`evaluation/scoring_criteria.md`](../evaluation/scoring_criteria.md)) on purpose — building toward a known, well-specified target is part of the job. Structuring your repo so it's easy for both a human and an agent to navigate is a (small) part of the signal.

> **What this challenge does and doesn't cover:** this take-home focuses on the build — context modeling, AI orchestration, and the product narrative. Platform-native skills (PQL and hands-on work in the Celonis Context Model), discovery workshops, project management, and live customer collaboration are core to the role but are assessed later in the interview process, not here. Treat this as one signal among several, not the whole bar.

Good luck — we're excited to see how you think.
