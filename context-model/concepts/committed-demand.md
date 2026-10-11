---
id: committed-demand
type: concept
aliases: [committed demand, firm demand, firm order, high-priority demand]
inputs: [MaterialRequirements.requirementType, MaterialRequirements.priority, MaterialRequirements.requirementQuantity, MaterialRequirements.requirementDate]
computed_by: assess_coverage
output: each requirement tagged committed / not committed, ranked by priority then date
related: [material-requirement, shortfall, demand-priority, spending-policy]
assumptions:
  - name: sales orders are firm
    value: every SalesOrder counts as committed
    why: Maria protects "a firm sales order", but the data has no firm/unfirm flag.
---
# Committed demand

## Definition
Demand the business has promised and must protect: **production orders and sales orders**. Forecasts are not committed; they can be re-planned.

## Formula
`committed = requirementType IN ('ProductionOrder', 'SalesOrder')`. Within committed demand, rank by `priority` (High → Low), then `requirementDate`.

## How to read it
- A shortfall against committed demand is **Critical** (see [alerting](../rules/alerting.md)).
- A shortfall against forecast only is a **Warning**, and never justifies spending (see [spending policy](../rules/spending-policy.md)).

## Edge cases
- Priority and type are independent: a Medium-priority sales order is still committed.

## Assumptions (ours, not the customer's)
- All sales orders are treated as firm.
