# Supply risk briefing: MP-1010-8891

**Committed shortfall of 200 EA for Bearing Housing, Cast at 1010 Frankfurt Assembly (MP-1010-8891) starting 2026-09-16, fully short by 2026-09-18.**

## Recommended plan
- **transfer**: 160 from MP-1020-8891, arrives 2026-09-06
- **alternate vendor**: 40 from V-2002, arrives 2026-09-15

**Result:** The plan fully closes the committed gap of 200 EA. Re-check confirms sending plant MP-1020-8891 holds at or above its safety stock of 60 EA (lowest balance 60 on 2026-09-28, tier quiet) and alternate vendor Bavaria Precision Parts AG (V-2002) is eligible (on-time rate 0.94 > 0.90, quality rating A). MP-1010-8891 moves to watch tier.

**Fallback:** transfer + split: Transfer 160 EA from MP-1020-8891 arriving 2026-09-06, covering MREQ-7001 in full and 100 EA of MREQ-7002; split MREQ-7002 so that the remaining 40 EA waits for open supply PDOC-4500001234-10 arriving 2026-09-25.

## Why
- **Shortfall:** 200 by 2026-09-18
- **Cause:** PO line PDOC-4500001234-10 confirmed delivery date moved from 2026-09-11 to 2026-09-25 (14 days slip) due to 'Vendor capacity constraint' (event EVT-0006). Vendor Rheinmetall Components GmbH (V-2001) has an on-time delivery rate of 0.72 (below the 0.90 threshold) and quality rating A.
- **Affected demand:**
  - MREQ-7001 (ProductionOrder, 2026-09-16, 60 short)
  - MREQ-7002 (SalesOrder, 2026-09-18, 140 short)

## Options considered
- Transfer 160 EA from MP-1020-8891 (arrival 2026-09-06, stock already owned; no purchase cost) + alternate vendor order 40 EA from Bavaria Precision Parts AG V-2002 (arrival 2026-09-15, incumbent net price 40.00 EUR baseline): Chosen as primary plan because it fully closes the committed shortfall before requirement dates.
- Transfer only: Sender spare stock is capped at 160 EA to keep MP-1020-8891 at or above safety stock of 60 EA, leaving 40 EA uncovered.
- Alternate vendor only (200 EA from Bavaria Precision Parts AG V-2002): Rejected as primary because resolution order prefers transfer of existing inventory before placing new vendor orders.
- Alternate vendor order from Adriatic Castings d.o.o. (V-2003): Rejected because vendor is ineligible (on-time rate 0.81 <= 0.90, quality B) and lead time 35 days (arrival 2026-10-11) misses demand dates.
- Incumbent expedite with Rheinmetall Components GmbH (V-2001): Rejected / last resort only due to unreliable on-time rate (0.72) and arrival date 2026-09-27.

## Watch
- Alternate vendor price for Bavaria Precision Parts AG (V-2002) is unquoted; incumbent net price 40.00 EUR per unit serves as baseline.
- Sending plant MP-1020-8891 reaches its exact safety stock buffer of 60 EA on 2026-09-28 when forecast MREQ-7010 is due, until PDOC-4500001240-10 arrives on 2026-10-02.
- Incumbent open PO line PDOC-4500001234-10 (400 EA) remains scheduled for delivery on 2026-09-25 from Rheinmetall Components GmbH (V-2001), which has a low on-time rate of 0.72.

## Assumptions
- analysis date: 2026-09-04 (index.md)
- order processing time: 2 days from deciding to buy until the PO is with the vendor (rules/alerting.md)
- transfer lead time: 2 days (rules/transfer-limit.md)
- near-term horizon: today + order processing time + avgLeadTimeDays of the vendor on the material-plant's open supply; if none, the shortest lead time among eligible approved vendors; if none is eligible, the longest lead time among approved vendors (rules/alerting.md)
- same-day ordering: demand is subtracted before supply is added on the same date (concepts/projected-stock.md)
- backlog: the balance may go negative; a missed requirement is still owed, and later supply fills it first (concepts/projected-stock.md)
- type decides commitment: requirementType decides committed (ProductionOrder, SalesOrder); priority only ranks within committed demand (concepts/committed-demand.md)
- north of ninety percent: strictly greater than 0.90 (rules/vendor-eligibility.md)
- alternate vendor price: unknown; premium to be quoted (rules/spending-policy.md)

_4 of 5 material-plants checked are healthy with no shortfalls or safety stock breaches (MP-1010-8892, MP-1020-7400, MP-1020-8891, MP-1030-8892)._

Sources: MP-1010-8891, MP-1020-8891, MP-1010-8892, MP-1020-7400, MP-1030-8892, MREQ-7001, MREQ-7002, MREQ-7003, MREQ-7010, PDOC-4500001234-10, PDOC-4500001240-10, EVT-0006, V-2001, V-2002, V-2003, context-model/index.md, context-model/rules/alerting.md, context-model/rules/resolution-order.md, context-model/rules/vendor-eligibility.md, context-model/rules/transfer-limit.md, context-model/rules/spending-policy.md, context-model/rules/recommendation-output.md
