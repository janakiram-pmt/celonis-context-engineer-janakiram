---
id: transfer-limit
type: rule
strength: hard
params:
  max_quantity: spare_stock
  sender_must_stay_at_or_above: safetyStock
assumptions:
  - name: transfer lead time
    value: 2 days
    why: Not in the data or the interview. Typical for a truck transfer between German plants; only matters if demand is due within a few days.
source: discovery_interview.md (Maria)
applies_to: [spare-stock, material-plant]
used_by: [find_transfer_options, rank_resolution_options]
---
# Transfer limit

## Rule
A transfer may take only what the sending plant can [spare](../concepts/spare-stock.md). The sender must never be projected below its own safety stock.

## Why
> "I won't strip a sending plant below its own safety stock to cover me. I'm not going to create a second fire to put out the first. So a transfer only counts for what the other site can spare above its buffer." (Maria)

## How to apply
- Transfer quantity ≤ spare stock of the sender.
- The transfer must arrive (today + transfer lead time) before the requirement it covers.
- After proposing a transfer, re-check the sender (see [alerting](alerting.md)).

## What not to do
- Don't compute spare as on hand − safety stock alone; the sender's own upcoming demand counts.

## Assumptions (ours, not the customer's)
- Transfer lead time: 2 days.
