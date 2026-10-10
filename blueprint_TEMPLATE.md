# Product Blueprint — <Your Solution Name>

> This is an **optional scaffold** for Task 3. Rename your finished version to `blueprint.md` at the repo root. Delete the guidance in blockquotes. Length target: 2–4 pages. Prose over bullet-dumps — this is a product narrative, not a checklist.

## 1. The problem in one paragraph
> What breaks today when a material movement is delayed, who feels it, and why the current (dashboard/manual) approach is too slow. Ground it in the scenario but frame it as a general class of problem.

## 2. Architecture & rationale
> Explain what you built and, more importantly, *why*. Cover:
> - How your **context/semantic model** is structured and why that structure lets an LLM reason without hard-coded queries.
> - Your **orchestration pattern** (tools, retrieval, agent loop) and why it fits this problem.
> - Where the **LLM sits** vs. what you kept deterministic (e.g., computing the shortfall in code, not in the model).
> - How you keep it **grounded and trustworthy** (citations, computed numbers, validation, guardrails).
> - One trade-off you considered and **rejected**, and why.

A simple diagram (ASCII or image) here is worth a lot.

## 3. How it scales
> Move from this toy dataset to reality:
> - Data volume: millions of objects, thousands of plants/vendors — what holds, what moves.
> - Cost, latency, and quality trade-offs at scale.
> - Generalization to **other process domains** (order-to-cash, invoice management) with minimal rework.
> - What you'd re-architect vs. reuse.

## 4. Strategic value
> The case you'd make to an executive buyer (CFO / CPO):
> - Operational value: cycle time, stockouts avoided, analyst hours reclaimed.
> - Commercial value and the KPIs you'd commit to.
> - Why this is categorically different from a better dashboard.
> - A brief adoption / rollout view.

## 5. What I'd do next
> Given more than 4 hours: the top 3 things you'd build or harden, in priority order.
