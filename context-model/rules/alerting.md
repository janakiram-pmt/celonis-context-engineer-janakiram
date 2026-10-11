---
id: alerting
type: rule
strength: hard
params:
  tiers: [critical, warning, watch, quiet]
  horizon: supplying_vendor_lead_time
  critical_path_trigger: true
  recheck_after_plan: true
assumptions:
  - name: near-term horizon
    value: today + order processing time + avgLeadTimeDays of the vendor on the material-plant's open supply; if none, the shortest lead time among eligible approved vendors; if none is eligible, the longest lead time among approved vendors
    why: Our reading of "near-term". Demand further out can still be met by a normal order placed today from the fastest dependable vendor, so it needs no intervention yet. With no dependable vendor, a wider window is the honest choice.
  - name: order processing time
    value: 2 days from deciding to buy until the PO is with the vendor
    why: Typical requisition-to-PO time in the event log (2 days for 3 of 4 requisitions; 5 days once). The vendor's lead time counts from the PO.
source: discovery_interview.md (Maria, Tom)
applies_to: [shortfall, safety-stock-breach, committed-demand, critical-path-supply]
used_by: [assess_coverage, assess_critical_path]
---
# Alerting: what to flag, what to leave alone

> "Today" means the [analysis date](../index.md#conventions): `metadata.asOfDate`, never the system clock.

## Rule
Flag only what is genuinely at risk, ranked by tier. Stay quiet on healthy material-plants.

## Why
> "Please don't cry wolf. … If the tool lights those up, planners will stop trusting it within a week." (Tom)
>
> "Confirmed dates slipping later on lines that cover near-term committed demand — top of the list. Stock projected to drop below safety stock. And a reliable-supplier issue on the critical path." (Maria)

## How to apply
**Coverage tiers.** Assessed inside the horizon; the highest tier wins per material-plant, and lower-tier signals are still listed.

| Tier | Condition | In the briefing |
|---|---|---|
| **Critical** | [Shortfall](../concepts/shortfall.md) (< 0) for [committed demand](../concepts/committed-demand.md) | Top, with a recommendation |
| **Warning** | [Below safety stock](../concepts/safety-stock-breach.md) AND (no open supply restores it OR a shortfall for any demand, forecast included) | Listed, with a suggested action |
| **Watch** | Below safety stock, no shortage, open supply restores it | One line |
| **Quiet** | Never below safety stock | Nothing |

**Critical-path trigger** (no horizon): committed coverage depends on a [critical-path](../concepts/critical-path-supply.md) line whose vendor fails [vendor eligibility](vendor-eligibility.md).

**After a plan is proposed:** re-run both checks on every material-plant the plan touches, including sending plants, and on the plan's own vendors.

## What not to do
- Don't flag a material-plant just because a date moved, it has no open supply, or it's below its reorder point.
- Don't list healthy material-plants individually; one summary line ("N checked, all healthy") is enough.

## Assumptions (ours, not the customer's)
- Near-term = today + order processing time (2 days) + the lead time of the vendor on the open supply.
- No open supply: use the fastest vendor that passes [vendor eligibility](vendor-eligibility.md), since a normal order from it today would arrive by then. If no approved vendor is eligible, use the slowest approved vendor (no dependable fast option, so cast a wider net).
- Order processing time: 2 days, the typical requisition-to-PO time in the event log.
