# Product Blueprint — Inventory Risk Agent

## The problem and the vision

On 1 September, Rheinmetall moved a 400-unit delivery for Frankfurt Assembly from 11 to 25 September. By 4 September, 200 units of committed demand due on 16 and 18 September were uncovered. The data contained recovery options, but the existing process did not connect the supplier change to the exposure in time.

The Frankfurt plant is a small example of a broader manufacturing problem: procurement teams often have the data needed to see supply risk, but not the continuous decision support needed to act on it early. Supplier performance is uneven even among high-performing plants: one benchmark reported supplier on-time delivery ranging from 44% at the low end to a 90% median.[1] When a delay reaches committed demand, the cost escalates quickly. Siemens reports that downtime can cost small and mid-sized manufacturers up to $150,000 per hour and automotive manufacturers approximately $2.3 million per hour.[2] Gartner reports that more than a third of supply-chain organizations spend at least 30% of their time firefighting disruptions.[3]

The common thread is late detection. Once a supply problem becomes visible on the shop floor, lower-cost recovery options may already be gone. Planners are left with premium freight, split deliveries, production interruptions, or difficult customer conversations.

Our vision is an Inventory Risk Agent that changes when procurement teams find out. It would continuously monitor materials, plants, demand, inventory, inbound supply, and vendor status, then turn meaningful changes into actionable alerts while practical recovery options are still available.

It acts first. Planners should not have to search across orders, inventory, and supplier updates to discover exposure. The agent identifies emerging risk, ranks it by business impact, and brings it to the people who own the decision.

It earns trust through evidence. Every shortfall, date, and recommendation should be traceable to transactional data, business rules, or an explicit assumption. The agent should remain quiet when coverage is healthy and avoid exaggeration, unsupported certainty, and noisy alerts.

It ends in a decision. Each alert should explain what changed, quantify the impact, recommend a feasible course of action, and provide a fallback if the preferred option fails. Recommendations should respect the company’s own policies—for example, using available stock before buying, relying only on approved and dependable suppliers, and protecting committed demand before forecasts.

## How the agent works

The first version runs this full loop on the challenge data. It detects the Frankfurt exposure on its own, explains the cause, recommends a plan within the customer's rules, and delivers it to Slack.

```
 Source data ──► Relational model ──► Decision tools ◄── Context model
 (ERP extract)   (SQLite: facts)      (Python: all numbers)  (Markdown/YAML: meaning, rules, assumptions)
                                            ▲
                                            │ tool calls
                                     Agent (Gemini, ReAct)
                                            │
                              grounding check ──► Briefing ──► Slack
                                                     └──► Chat (follow-up questions)
```

**Relational model.** The source data is loaded into SQLite as eight tables: the six source objects (vendors, material-plants, material requirements, purchase requirements, purchase orders, and purchase-order lines), a table of vendor approvals, and the event log. Primary keys, foreign keys, and value checks reject broken records on load, and the loader verifies that every event points to a real object. The model stores facts only: projected stock, shortfalls, and spare stock are always calculated, never stored, so they cannot go stale. Unusual but legitimate records, such as an over-delivery or a purchase order with a vendor whose approval was later withdrawn, remain visible rather than being silently normalized away.

**Context model.** Twenty-six Markdown files describe what the data means and what the customer wants: a one-page index the agent reads first; objects (8), describing what each table represents and how it connects; concepts (9), defining calculations such as projected stock, shortfall, spare stock, and date slip, each naming the tool that computes it; and rules (8), the customer's policies, each quoting the discovery interview. Every file has a header the code reads; rules carry the thresholds the tools use, such as an on-time rate above 90%, quality tier A, and never transferring below the sending plant's safety stock. Wherever the data and the interview were silent, we made an assumption and recorded it in the file it affects, marked as ours. Four of them shape the Frankfurt answer most: the analysis date is fixed at the dataset's 4 September snapshot rather than the system clock; a transfer between plants takes two days; a new purchase order takes two days to reach the supplier, based on the typical requisition-to-order time in the event log; and demand counts as committed by order type (production and sales orders), with priority only ranking within it. The full list is in the Appendix.

**Decision tools.** Eight Python tools do all the arithmetic. Each answers one question a planner would ask, reads its thresholds from the context model, and cites the records behind every number.

| Tool | Question |
|---|---|
| `check_stock_risk` | Is anything at risk, how badly, and why? |
| `find_changes` | What changed in the event log? |
| `find_critical_suppliers` | Does committed demand depend on an unreliable supplier? |
| `find_transfer_options` | Which plants can spare stock? |
| `find_alternate_vendors` | Which approved suppliers can deliver in time? |
| `rank_resolution_options` | What is the best plan and fallback, and does it hold? |
| `read_context` | What does this term or rule mean? |
| `submit_briefing` | Here is the final briefing (validated before it is accepted) |

**Orchestration.** The agent runs a ReAct loop on Gemini: it reasons, calls a tool, reads the result, and decides what to do next, until it submits a briefing. ReAct fits this problem because the right next step depends on what the last tool returned. If everything is healthy it stops early; if one plant is critical it investigates that one; if a transfer closes the gap, it does not need to look for a new supplier. A short system prompt sets the job and the guardrails; the policies themselves stay in the context model. The loop allows up to 20 turns and two rejected briefings, and retries automatically when the model service is overloaded. When several alerts exist, the briefing lists all of them, plans the most urgent, and reserves the stock that plan uses, so the next alert planned in chat cannot be promised the same inventory. An offline mode runs the same tools without the language model, so the app can be reviewed without an API key.

**Grounding and testing.** Every briefing is validated before it is sent. It is rejected if:

- a number, date, or record ID cannot be traced to a tool output;
- the shortfall, the affected orders and their quantities, or the cause (event, old and new dates) do not match the tools exactly;
- the recommended plan differs from the one `rank_resolution_options` produced;
- a flagged material-plant is missing, or the alert has no fallback;
- a premium purchase is recommended when no committed demand is short.

Answers in chat pass the same check for invented values. Beneath the agent, 79 automated tests check the data model, the context model, the tool calculations on the Frankfurt case and sixteen changed scenarios, and the grounding check itself. They run in under a second without an API key. A separate evaluation runs the live agent and scores its behavior rather than its wording. Details are in the Appendix.

**Slack and command line.** The briefing is posted to a Slack channel through an incoming webhook. It leads with the headline, the plan, the fallback, and the cause, and ends with a line on the material-plants that are healthy; if no webhook is configured, the message is saved to a file instead. Plants, suppliers, and materials appear by name with their ID. Planners can follow up from the command line:

- `python -m app briefing` runs the check and delivers the briefing (`--offline` runs it without the language model);
- `python -m app ask "…"` answers a single question;
- `python -m app chat` holds a conversation, for example "any other alerts today?", "why not ask Rheinmetall to expedite?", or "plan the next alert".

Every run saves its transcript and briefing for review.

## Limitations and how it scales

On one customer's snapshot, this version does the hard part well. It separates the one real exposure from healthy activity, explains it with traceable evidence, and recommends a plan that follows the customer's own rules. It is also only a beginning. Each limitation below was a deliberate scope choice for a first version, and each has a clear path to scale.

### From isolated alerts to coordinated decisions

The largest gap is in how the agent reasons across problems. Today, each alert is diagnosed on its own and resolved in sequence (a transfer first, a top-up second, one alert after another), with stock reserved so that no two plans promise the same inventory. That is safe, but each decision only sees what the earlier ones left behind. Real supply problems rarely arrive one at a time, and the next version should look at all of them together.

In diagnosis, that starts with recognizing that a single event often involves several objects at once: one supplier notice can push lines for Frankfurt and Leipzig together; one truck delivery can be received against two purchase orders; one stock transfer takes stock out of one plant and puts it in transit to another. Because each of those objects leads to its own material-plant and its own demand, a single event can open exposures at several plants. The agent should trace it to every one of them and report one incident with several impacts, rather than a set of unrelated alerts. The reverse holds as well: a single shortfall can combine a supplier slip, a new order, and a stock correction, and each deserves its share of the gap. The result is a map from causes to alerts rather than a list of alerts, and it tells the planner more than any single alert can. A shortfall that is mostly a supplier problem needs a recovery plan; one that is mostly inventory inaccuracy needs a cycle count.

In resolution, the agent should plan across all open alerts and all levers (transfers, top-ups, split deliveries, expedites) at once, and produce one sequenced resolution path. Consider two plants that need the same part. Planned one at a time, the plant with the earlier need takes the spare stock first, and the second plant is left with an expensive top-up that may still arrive too late. Planned together, the agent can see that the first plant's need is small enough for a reliable supplier to cover in time, while the second plant's is too close for any supplier. It sends the spare stock to the second plant and the supplier order to the first, and both are resolved at lower cost. The stock and the suppliers are the same; the outcome is better because the agent reasoned across alerts.

This requires four foundations:

- **An event model where each event links to every object it involves.** Today each event is recorded against one object, so a supplier notice that delayed several lines looks like several unrelated events. An event-to-object link table (the OCEL 2.0 standard), together with inventory-movement events, makes shared causes and internal stock changes visible.
- **An attribution method** that splits a shortfall fairly between interacting causes; Shapley values are the standard approach.
- **An allocation optimizer** that divides scarce stock and supplier capacity across alerts by business priority and timing, under the customer's rules.
- **An agent that explains the whole path**—for example, why the spare stock went to one plant rather than the other—in the customer's own policy terms.

### From snapshots to continuous intelligence

| Limitation today | How it scales |
|---|---|
| **Snapshot data, run on demand.** The analysis date is fixed, and the check runs on a schedule or by hand | **Event-driven monitoring.** Changes in the source system (confirmations, receipts, demand changes) trigger a recalculation of only the material-plants they affect, so a slip becomes an alert within minutes |
| **SQLite and a full scan of five material-plants** | **A warehouse or the Celonis data model,** with incremental projections partitioned by plant. The per-material-plant logic holds as volume grows; storage and scanning are what change |
| **Language-model cost and latency on every run** | **Deterministic triage first,** so the model only sees the handful of flagged items. A cached system prompt, compact tool outputs, and a lighter model for routine briefings keep cost per alert low, and it is tracked as a product metric |
| **Trust at today's scale.** Free-text explanations are checked only for invented values; evaluations run once per scenario against hand-written expectations | **Code fills every number, and the model writes the explanation around it.** Evaluations compare the agent against the tools' own answers, run several times per scenario, and add regression and prompt-injection tests. In production, alerts acted on and plans followed show whether planners trust what they receive |

### From a working agent to a decision product

The first version has one customer's rules, written by hand, and a basic experience: alerts are pushed to Slack, follow-up questions run in a terminal chat, and nothing can be actioned from the alert itself. Turning it into a product that many customers can adopt means scaling both the context the agent understands and the ways people turn its recommendations into decisions.

The agent's context should become a living, customer-visible operating model. A shared library of concepts would serve every customer, with a rule set per customer that business owners can edit themselves, versioned and protected by the same contract tests that guard it today. The fixed assumptions (two-day transfers, two-day order processing, unquoted supplier prices) should give way to parameters learned from the customer's own history, such as transfer times per lane, processing times per supplier, and prices from supplier quotes, each shown with a confidence range so planners know how far to rely on it. As the library grows into hundreds of files, search behind `read_context` replaces the hand-written index.

How people work with it should not depend on a single channel. The experience would start with Slack (chat in the thread, approve or reject buttons), then add Microsoft Teams and email for companies that do not use Slack. Over time, it becomes a web app with an audit trail of every decision and an approval workflow that writes transfer and purchase-order drafts back to the ERP for a human to confirm. The agent and its tools stay the same whatever the channel; only the delivery and the interaction change.

## Rollout plan and KPIs

A dashboard tells a planner what the numbers are. The Inventory Risk Agent tells them what changed, what it will cost, and what to do about it—before anyone has thought to look. That difference matters most in the few days after a supplier changes plans, when a dashboard is waiting to be opened and someone still has to connect orders, stock, and supplier updates by hand. By the time they do, the inexpensive options are often gone. The agent closes that window: it catches the change as it lands, traces it to the specific orders at risk, and arrives with a plan that follows the company's own sourcing rules, along with a fallback. It does not replace the planner's judgment; it removes the search, arithmetic, and delay that come before it.

### The business outcomes we commit to

We take responsibility for two outcomes:

| Outcome | Why it matters | How we measure it | Formula |
|---|---|---|---|
| **Fewer stockouts on committed demand** | Every avoided stockout protects a production run or a customer order | Committed requirements whose goods receipts arrive after the requirement date, against the customer's own history before the agent went live | committed requirements received after their requirement date, per month, as % change against the same months in the baseline |
| **More shortfalls closed with stock already owned** | Each gap resolved by a transfer rather than a new purchase avoids a premium and puts working capital already on the books to use | The share of recovery orders that are transfers rather than new purchase orders | transfers ÷ (transfers + new purchase orders), across recovery orders |

As a conservative illustration, one mid-sized plant that avoids two four-hour supply-driven stoppages a year (at $25,000 per line-hour, well below the published industry range), cuts expedite spend from 10% to 7% of a $5 million freight budget, and frees a third of six planners' firefighting time would save about $400,000 a year. Every input is an assumption; each is replaced with the customer's own figures during onboarding.

These outcomes take months and volume to show. The rollout therefore runs in two phases: the first proves the agent is doing the right things, and the second proves that doing them pays off.

### Phase 1: Assisted, at one plant

The agent goes live at one plant for one material family, and planners act on its recommendations. Before go-live, onboarding calibrates the assumptions against the customer's history, so transfer and order-processing times reflect their operations rather than ours, and draws a baseline of stockouts and recovery orders from the previous six to twelve months of the event log. From day one, we track the signals that show whether the agent deserves the planners' trust:

*N* is the follow-up window (for example, 5 days); *t* is the quantity tolerance (for example, 10%).

| Metric | Why it matters | How we measure it | Formula |
|---|---|---|---|
| **Alerts acted on** (diagnosis) | Shows the agent flagged a real problem: the planner did something about it | A corrective event on the same material-plant within a few days of the alert—a new purchase order or line, a transfer, or a changed delivery date | alerts with at least one corrective event on the same material-plant within N days ÷ all alerts |
| **Plans followed** (resolution) | Shows the agent recommended the right fix, not just a real problem | Those corrective events matched against the recommended plan: same action type, same sending plant or supplier, and a similar quantity | alerts whose corrective events match every recommended action (same type, same source, quantity within ± t) ÷ alerts acted on |
| **Missed risks** | Staying quiet is only safe if nothing important is missed | Committed requirements still uncovered on their date with no alert beforehand, from goods-receipt events | count per month of committed requirements uncovered on their date with no prior alert (target: 0) |
| **Time from event to alert** | Early detection is the product's value; a late alert is worth little | The causal event's timestamp against the briefing's delivery timestamp | median of (briefing delivery time − causal event timestamp) |
| **Guardrail: unsupported numbers shipped** | Not a target but a line that must never be crossed: a planner should never see a number the tools did not produce | Every briefing or answer blocked by the grounding check is logged; the count shipped must stay at zero, and a rising block count is an early warning | shipped: delivered outputs with a value absent from every tool output (must be 0); blocked rate: rejected submissions ÷ all submissions |

The two business outcomes are tracked from the start as a trend against the baseline, but at one plant they are too rare to judge. Phase 1 is judged on these leading signals.

### Phase 2: Scale

Once the signals hold, the agent extends to all plants and material families, runs continuously on changes in the source system, and writes approved plans back to the ERP as transfer and purchase-order drafts. The same product metrics continue. With enough plants and months of volume, the two business outcomes become commitments, with targets agreed with the customer against their baseline.

### Releasing changes safely

Within and between these phases, the product changes continuously: assumptions are recalibrated, rules adjusted, the prompt refined, new scenarios covered. Each of these is a small release, and before any of them reaches planners it passes an offline check for regressions:

| Check | Why it matters | How we measure it | Formula |
|---|---|---|---|
| **Test pass rate** | Every number the agent reports comes from code, so a regression in code is a wrong number in front of a planner | The automated suite runs on every change | tests passed ÷ tests run (gate: 100%) |
| **Scenarios reproduced exactly** | The tools must give the known-correct answer across varied situations, not just one | Scenario tests compare tool results with expected values | scenarios matching expected values ÷ all scenarios |
| **Evaluation pass rate over repeated runs** | The model's behavior varies between runs; one good run proves little | The agent evaluation runs each scenario several times and reports the share of checks passed | checks passed across all runs ÷ (checks × runs) |
| **Briefings accepted on the first attempt** | Each rejection costs time and money and signals unclear instructions | The share of evaluation runs whose first briefing passes the grounding check | runs whose first briefing passes ÷ all evaluation runs |

A release goes out only if every test passes and the agent's evaluation pass rate is at least that of the last released version.

## Appendix: Assumptions

| Assumption | Value | Basis |
|---|---|---|
| Analysis date | 4 September 2026, the dataset's as-of date | The data is a snapshot; the system clock would make every date look past |
| Order processing time | 2 days from decision to purchase order | Typical requisition-to-order time in the event log |
| Transfer lead time | 2 days between plants | Not in the data; a plausible truck transfer within Germany |
| Committed demand | Decided by order type; priority only ranks within it | A low-priority production order is still committed; a high-priority forecast is not |
| Near-term horizon | Today + processing time + the supplying vendor's lead time | Inside that window, a normal order cannot arrive in time |
| "North of ninety percent" | On-time rate strictly above 0.90 | A literal reading of the interview |
| Same-day timing | Demand is served before supply arriving the same day | Dates have no time of day, so the cautious reading |
| Backlog | Missed demand is still owed and filled first by later supply | Committed orders run late; they are not cancelled |
| Overdue supply | Not counted until received | Counting it as arriving today would hide a late delivery |
| Past-due demand | Still owed, counted as due today | Skipping it would hide a shortfall |
| Alternate supplier price | Unknown; the premium must be quoted | The data only has prices on existing orders |

## Appendix: Tests and evaluation

| Suite | Tests | Covers |
|---|---|---|
| Relational model | 14 | Complete loading, rejection of broken data, acceptance of unusual but legitimate data |
| Context model | 11 | Valid headers, working links, columns that exist, assumptions kept separate and consistent |
| Decision tools | 19 | The Frankfurt answer: 200 short by 18 September, Leipzig spare 160, the 160 + 40 plan and its fallback |
| Scenarios | 16 | The same tools on changed data: no slip, no spare stock, no eligible supplier, overdue deliveries, forecast-only gaps, competing alerts |
| Tool registry | 8 | Tool names match the context model; bad inputs return clear errors |
| Grounding check | 11 | Accepts the reference briefing; rejects invented numbers, wrong pairings, resized plans, missing fallbacks |

**Agent evaluation.** The live agent runs twice and is scored on behavior, not wording.

- **Frankfurt case (10 checks):** briefing accepted; the right tools called; EVT-0006, MREQ-7001, and MREQ-7002 cited; 160 units from Leipzig and 40 from Bavaria recommended; Rheinmetall's 72% on-time rate mentioned; a fallback included; no 200-unit transfer; only Frankfurt alerted.
- **Bavaria not approved (4 checks):** briefing accepted; no Bavaria order; the 160-unit transfer kept; incumbent expedite as the fallback.

## Sources

[1] IndustryWeek, *2024 IW Best Plants Statistical Profile*. The benchmark reported a 90% median supplier on-time delivery rate and a 44% minimum. ([base.imgix.net](https://base.imgix.net/files/base/ebm/industryweek/document/2025/01/67910902565e06031b61a4ac-2024statprofilebest_plants.pdf?dl=67910902565e06031b61a4ac-2024statprofilebest_plants.pdf))

[2] Siemens, *The True Cost of an Hour’s Downtime: An Industry Analysis*. ([blog.siemens.com](https://blog.siemens.com/2024/07/the-true-cost-of-an-hours-downtime-an-industry-analysis/))

[3] Gartner, *Manage Supply Chain Disruption Without Firefighting*. ([gartner.com](https://www.gartner.com/en/articles/supply-chain-disruption))
