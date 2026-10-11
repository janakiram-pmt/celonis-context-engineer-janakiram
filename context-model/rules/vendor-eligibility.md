---
id: vendor-eligibility
type: rule
strength: hard
params:
  must_be_approved: true
  min_on_time_rate: 0.90
  on_time_comparison: greater_than
  allowed_quality: [A]
assumptions:
  - name: "north of ninety percent"
    value: strictly greater than 0.90
    why: Literal reading of Maria's wording; a vendor at exactly 0.90 does not qualify.
  - name: order processing time
    value: 2 days from deciding to buy until the PO is with the vendor
    why: Typical requisition-to-PO time in the event log (2 days for 3 of 4 requisitions; 5 days once). The vendor's lead time counts from the PO.
source: discovery_interview.md (Maria, Tom)
applies_to: [vendor, vendor-approval, vendor-reliability]
used_by: [find_alternate_vendors, find_critical_suppliers, rank_resolution_options]
---
# Vendor eligibility

> "Today" means the [analysis date](../index.md#conventions): `metadata.asOfDate`, never the system clock.

## Rule
A vendor can be used to expedite or top up only if it is **approved** for that material-plant, has an on-time rate **above 90%**, and quality tier **A**. The same bar decides whether a vendor on the critical path counts as unreliable.

## Why
> "We won't onboard a new vendor in a crisis and we won't use one that isn't approved for that material and plant. If they're approved and reliable — say, north of ninety percent on-time, top quality tier — that's who I want for the top-up." (Maria)
>
> "Their reliability is poor and an expedite promise from them isn't worth much." (Tom, on the incumbent)

## How to apply
1. Approved: a row exists in [vendor approval](../objects/vendor-approval.md) for the vendor and material-plant.
2. On-time rate > `min_on_time_rate`.
3. Quality in `allowed_quality`.
4. Then check timing: today + order processing time + `avgLeadTimeDays` must be on or before the requirement date.

## What not to do
- Don't treat a vendor's "yes" to an earlier date as reliable if it fails this bar.

## Assumptions (ours, not the customer's)
- "North of ninety" read as strictly greater than 0.90.
- Order processing time: 2 days before a new PO reaches the vendor (same value as in [alerting](alerting.md)).
