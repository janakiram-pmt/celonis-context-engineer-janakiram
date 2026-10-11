# Supply risk briefing: MP-1010-8891

**Bearing Housing, Cast at 1010 Frankfurt Assembly (MP-1010-8891): 200 units of committed demand uncovered by 2026-09-18.**

## Recommended plan
- **transfer**: 160 from MP-1020-8891, arrives 2026-09-06
- **alternate vendor**: 40 from V-2002, arrives 2026-09-15

**Result:** Closes the committed gap. MP-1010-8891 tier after the plan: watch. Sender re-check: MP-1020-8891 lowest 60 vs safety stock 60 (holds).

**Fallback:** transfer + split: cover what arrives in time; still short MREQ-7002 40, waiting for PDOC-4500001234-10 on 2026-09-25.

## Why
- **Shortfall:** 200 by 2026-09-18
- **Cause:** PDOC-4500001234-10 (Rheinmetall Components GmbH, on-time 0.72, fails vendor eligibility) moved from 2026-09-11 to 2026-09-25 (Vendor capacity constraint, EVT-0006). Had the vendor kept its original promise (date, or delivery of an overdue line), there would be no gap. Gap as promised: 0; now: 200.
- **Affected demand:**
  - MREQ-7001 (ProductionOrder, 2026-09-16, 60 short)
  - MREQ-7002 (SalesOrder, 2026-09-18, 140 short)

## Options considered
- Chosen: transfer + alternate vendor.
- Rejected: alternate vendor only (closes the gap but ranks lower in resolution-order (alternate_vendor before transfer)).
- Rejected: alternate vendor: Adriatic Castings d.o.o. (on-time rate 0.81 is not above 0.90; quality B is not in ['A']).
- Last resort: incumbent expedite: Rheinmetall Components GmbH (on-time rate 0.72 is not above 0.90 (last resort only)).

## Watch
- MP-1010-8891 below safety stock from 2026-09-16 to 2026-09-25, restored by PDOC-4500001234-10.
- Recovery depends on Rheinmetall Components GmbH (on-time 0.72).

## Assumptions
- analysis date: 2026-09-04
- near-term horizon: today + order processing time + avgLeadTimeDays of the vendor on the material-plant's open supply; if none, the shortest lead time among eligible approved vendors; if none is eligible, the longest lead time among approved vendors
- order processing time: 2 days from deciding to buy until the PO is with the vendor
- same-day ordering: demand is subtracted before supply is added on the same date
- backlog: the balance may go negative; a missed requirement is still owed, and later supply fills it first
- type decides commitment: requirementType decides committed (ProductionOrder, SalesOrder); priority only ranks within committed demand
- north of ninety percent: strictly greater than 0.90
- overdue supply: an open line whose confirmed date is before the analysis date is not counted until it is received
- past-due demand: a requirement dated before the analysis date that isn't Covered is still owed and counts as due on the analysis date
- transfer lead time: 2 days
- alternate vendor price: unknown; premium to be quoted

_4 other material-plants checked: MP-1010-8892 quiet, MP-1020-7400 quiet, MP-1020-8891 quiet, MP-1030-8892 quiet._

Sources: EVT-0006, MP-1010-8891, MREQ-7001, MREQ-7002, rules/alerting.md, rules/resolution-order.md
