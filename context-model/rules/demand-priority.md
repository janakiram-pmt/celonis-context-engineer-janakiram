---
id: demand-priority
type: rule
strength: hard
params:
  protect_first: committed
  rank_by: [committed, priority, requirementDate]
  priority_order: [High, Medium, Low]
source: discovery_interview.md (Maria)
applies_to: [committed-demand, material-requirement]
used_by: [check_stock_risk, rank_resolution_options]
---
# Demand priority

## Rule
Protect committed, high-priority demand first, always. Forecast demand can be re-planned.

## Why
> "I don't care if a forecast slips a week. I care a lot if a production order or a firm sales order is going to go uncovered. Protect the committed, high-priority demand first — always." (Maria)

## How to apply
- When stock or supply is scarce, allocate it in order: committed before forecast, then High → Low priority, then earliest date first.
- The nearest high-priority requirement is the one to cover first (see [split policy](split-policy.md)).
- Priority ranks demand; it doesn't make demand committed. Commitment comes from the requirement type (see the assumption in [committed demand](../concepts/committed-demand.md)).

## What not to do
- Never let a production order go short to cover a forecast.
