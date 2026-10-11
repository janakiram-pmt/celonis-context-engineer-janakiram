---
id: critical-path-supply
type: concept
aliases: [critical path, single point of failure, the only thing standing between me and a stockout]
inputs: [PurchaseDocumentLine.purchaseDocumentLineId, PurchaseDocumentLine.confirmedDeliveryDate, MaterialRequirements.requirementType, Vendor.onTimeDeliveryRate]
computed_by: assess_critical_path
output: per committed requirement, the open-supply lines it depends on and their vendors' reliability
related: [open-supply, committed-demand, vendor-reliability, date-slip, alerting]
---
# Critical-path supply

## Definition
An open-supply line that committed demand **depends on**: without it, that demand would go short. Maria: "if the only thing standing between me and a stockout is a vendor who misses half their dates, I want to know."

## Formula
For each committed requirement: re-run [projected stock](projected-stock.md) without the line. If the requirement goes short (or more short), the line is on its critical path.

## How to read it
- Critical-path line from a vendor that fails [vendor eligibility](../rules/vendor-eligibility.md) → flagged (see [alerting](../rules/alerting.md)), even if no shortfall is projected today.
- Apply it to recommended plans too: a fix that depends on an unreliable vendor is fragile.

## Edge cases
- If committed demand is covered by stock already on hand, no line is on its critical path.
