---
id: spending-policy
type: rule
strength: hard
params:
  premium_allowed_for: committed
  premium_allowed_for_forecast: false
  priority: continuity_over_cost
assumptions:
  - name: alternate vendor price
    value: unknown; premium to be quoted
    why: The data only has prices on existing PO lines. Compare against the incumbent's netPrice and state that the premium is unquoted.
source: discovery_interview.md (Tom)
applies_to: [committed-demand, shortfall]
used_by: [rank_resolution_options]
---
# Spending policy

## Rule
Paying a premium (expedite, alternate vendor) is acceptable to protect **committed** demand. Never spend to expedite forecast demand.

## Why
> "We're willing to pay a premium to protect committed production. Cost matters, but continuity matters more when it's a high-priority order. For forecast demand, no — don't spend to expedite a forecast." (Tom)

## How to apply
- Options that cost extra may cover committed shortfalls only.
- Forecast-only gaps: re-plan, or wait for open supply.
- Show cost as a trade-off, not a blocker, when committed demand is at stake.

## What not to do
- Don't size a paid top-up to cover forecast demand.

## Assumptions (ours, not the customer's)
- Alternate-vendor price is unknown and must be quoted.
