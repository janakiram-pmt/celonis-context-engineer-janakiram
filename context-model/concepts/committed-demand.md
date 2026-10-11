---
id: committed-demand
type: concept
aliases: [committed demand, firm demand, firm order, high-priority demand]
inputs: [MaterialRequirements.requirementType, MaterialRequirements.priority, MaterialRequirements.requirementQuantity, MaterialRequirements.requirementDate]
computed_by: assess_coverage
output: each requirement tagged committed / not committed, ranked by priority then date
related: [material-requirement, shortfall, demand-priority, spending-policy]
params:
  committed_types: [ProductionOrder, SalesOrder]
assumptions:
  - name: type decides commitment
    value: requirementType decides committed (ProductionOrder, SalesOrder); priority only ranks within committed demand
    why: Maria's "committed, high-priority demand" could mean both conditions. We read commitment from type, so a Low-priority production order is still committed and a High-priority forecast is not.
---
# Committed demand

## Definition
Demand the business has promised and must protect: **production orders and sales orders**. Forecasts are not committed; they can be re-planned.

> "I care a lot if a production order or a firm sales order is going to go uncovered." (Maria)

## Formula
`committed = requirementType IN params.committed_types` (ProductionOrder, SalesOrder). Within committed demand, rank by `priority` (High → Low), then `requirementDate`.

## How to read it
- A shortfall against committed demand is **Critical** (see [alerting](../rules/alerting.md)).
- A shortfall against forecast only is a **Warning**, and never justifies spending (see [spending policy](../rules/spending-policy.md)).

## Edge cases
- `priority` doesn't decide whether demand is committed, only the order it's covered in (see the assumption below and [demand priority](../rules/demand-priority.md)).

## Assumptions (ours, not the customer's)
- The requirement **type** decides commitment, and `priority` only ranks within committed demand. A Low-priority production order is still committed; a High-priority forecast is not.
