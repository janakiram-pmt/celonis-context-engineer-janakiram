# Supply risk briefing

**Frankfurt Assembly (MP-1010-8891) faces a critical committed shortfall of 200 EA of Bearing Housing, Cast starting 2026-09-16 and reaching 200 EA by 2026-09-18.**

## Recommended plan
- **transfer**: 160 from Leipzig Distribution (MP-1020-8891), arrives 2026-09-06
- **alternate vendor**: 40 from Bavaria Precision Parts AG (V-2002), arrives 2026-09-15

**Result:** Primary plan closes the committed shortfall completely (0 EA remaining). Senders recheck holds: Leipzig Distribution (MP-1020-8891) remains quiet and stays at or above safety stock of 60 EA (lowest balance 60 EA on 2026-09-28). Alternate vendor Bavaria Precision Parts AG (V-2002) is approved and eligible. MP-1010-8891 tier shifts from critical to watch due to temporary safety stock breach until 2026-09-25.

**Fallback:** Transfer + split: Transfer 160 EA from Leipzig Distribution (MP-1020-8891) arriving 2026-09-06 to cover MREQ-7001 (60 EA) and partially cover MREQ-7002 (100 EA), leaving 40 EA of MREQ-7002 (SalesOrder, 2026-09-18) uncovered until delayed line PDOC-4500001234-10 from Rheinmetall Components GmbH (V-2001) arrives on 2026-09-25.

## Why
- **Shortfall:** 200 by 2026-09-18
- **Cause:** Purchase document line PDOC-4500001234-10 for 400 EA slipped 14 days from confirmed delivery date 2026-09-11 to 2026-09-25 due to 'Vendor capacity constraint' (Event EVT-0006 on 2026-09-01T07:45:00Z). Vendor Rheinmetall Components GmbH (V-2001) is unreliable with an on-time delivery rate of 0.72 (below required threshold of 0.90) and quality rating A.
- **Affected demand:**
  - MREQ-7001 (ProductionOrder, 2026-09-16, 60 short)
  - MREQ-7002 (SalesOrder, 2026-09-18, 140 short)

## Options considered
- Transfer 160 EA from Leipzig Distribution (MP-1020-8891) arriving 2026-09-06: Selected for primary plan (rank 1); utilizes owned inventory without purchase cost, limited by sender spare stock (sender safety stock 60 EA, upcoming forecast MREQ-7010). Cannot close the full 200 EA gap alone.
- Alternate vendor order for 40 EA from Bavaria Precision Parts AG (V-2002) arriving 2026-09-15: Selected as top-up in primary plan (rank 2); approved vendor, fully eligible (on-time rate 0.94 > 0.90, quality A), lead time 9 days + 2 days processing arrives before requirement date 2026-09-16. Baseline net price is 40.00 EUR per unit (premium unquoted).
- Alternate vendor order only (200 EA from V-2002): Rejected because stock transfer is available and preferred under resolution order (owned stock first).
- Alternate vendor order from Adriatic Castings d.o.o. (V-2003): Rejected because vendor is ineligible (on-time rate 0.81 is not above 0.90, quality tier B is not in ['A']) and lead time (35 days + 2 days processing = arrival 2026-10-11) misses requirement dates.
- Incumbent expedite from Rheinmetall Components GmbH (V-2001): Rejected as last resort only because vendor on-time rate 0.72 is unreliable.
- Transfer + split (fallback): Transfer 160 EA from MP-1020-8891 and split MREQ-7002, waiting for line PDOC-4500001234-10 on 2026-09-25 for remaining 40 EA. Kept as fallback if alternate vendor top-up cannot be placed.

## Watch
- MP-1010-8891 projected balance drops to 0 EA on 2026-09-18 (below safety stock of 150 EA) until Rheinmetall delivery arrives on 2026-09-25.
- Bavaria Precision Parts AG (V-2002) unit price premium is not yet quoted; baseline is incumbent net price of 40.00 EUR per unit.
- Sending plant Leipzig Distribution (MP-1020-8891) balance drops to its exact safety stock of 60 EA on 2026-09-28 prior to replenishment on 2026-10-02.

## Assumptions
- analysis date: 2026-09-04 (index.md)
- near-term horizon: today + order processing time + avgLeadTimeDays of the vendor on the material-plant's open supply; if none, the shortest lead time among eligible approved vendors; if none is eligible, the longest lead time among approved vendors (rules/alerting.md)
- order processing time: 2 days from deciding to buy until the PO is with the vendor (rules/alerting.md)
- transfer lead time: 2 days (rules/transfer-limit.md)
- same-day ordering: demand is subtracted before supply is added on the same date (concepts/projected-stock.md)
- backlog: the balance may go negative; a missed requirement is still owed, and later supply fills it first (concepts/projected-stock.md)
- type decides commitment: requirementType decides committed (ProductionOrder, SalesOrder); priority only ranks within committed demand (concepts/committed-demand.md)
- north of ninety percent: strictly greater than 0.90 (rules/vendor-eligibility.md)
- alternate vendor price: unknown; premium to be quoted (rules/spending-policy.md)
- overdue supply: an open line whose confirmed date is before the analysis date is not counted until it is received (concepts/open-supply.md)
- past-due demand: a requirement dated before the analysis date that isn't Covered is still owed and counts as due on the analysis date (concepts/projected-stock.md)

_4 of 5 material-plants checked are healthy and require no action._

Sources: MP-1010-8891, MP-1020-8891, MREQ-7001, MREQ-7002, MREQ-7003, MREQ-7010, PDOC-4500001234-10, PDOC-4500001240-10, EVT-0006, V-2001, V-2002, V-2003, index.md, rules/alerting.md, rules/resolution-order.md, rules/vendor-eligibility.md, rules/transfer-limit.md, rules/spending-policy.md, rules/recommendation-output.md, concepts/shortfall.md, concepts/date-slip.md, concepts/projected-stock.md, concepts/spare-stock.md, concepts/committed-demand.md

Questions? Run `python -m app chat` (e.g. 'any other alerts today?', 'why not ask Rheinmetall to expedite?', 'plan the next alert').
