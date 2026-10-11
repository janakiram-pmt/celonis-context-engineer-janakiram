---
id: resolution-order
type: rule
strength: preference
params:
  order: [transfer, alternate_vendor, split, incumbent_expedite]
  never: [new_vendor]
  combinable: true
source: discovery_interview.md (Maria, Tom)
applies_to: [shortfall, spare-stock, vendor-reliability]
used_by: [rank_resolution_options]
---
# Resolution order

## Rule
Close a gap with these options, in this order of preference:
1. **Transfer** from another plant's [spare stock](../concepts/spare-stock.md).
2. **Alternate vendor:** expedite or top up from an already-approved, reliable vendor for whatever the transfer can't cover.
3. **Split:** cover the urgent piece now and let later or lower-priority demand wait for the original delivery.
4. **Incumbent expedite:** ask the current vendor to deliver sooner. Last resort.

Options can be combined (e.g., a transfer plus an alternate-vendor top-up).

## Why
> "A transfer is usually my favorite because it's fast and it's inventory we already paid for." (Maria)
>
> "We do not like leaning on Rheinmetall to go faster. They'll say yes to an earlier date and then miss it." (Tom)
>
> "If a transfer doesn't fully cover it, I'd rather bring in a different, already-approved supplier who's actually dependable." (Maria)

## How to apply
- Filter first with the hard rules ([transfer limit](transfer-limit.md), [vendor eligibility](vendor-eligibility.md), [spending policy](spending-policy.md)), then rank what remains by this order.
- Every option must arrive before the demand it covers.
- If the top option can't close the gap alone, add the next one, and offer a fallback (see [recommendation output](recommendation-output.md)).

## What not to do
- Never onboard a new vendor in a crisis.
- Don't lead with an incumbent expedite.
