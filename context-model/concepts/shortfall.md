---
id: shortfall
type: concept
aliases: [shortfall, short, gap, uncovered demand, stockout, at risk, line going down]
inputs:
  - MaterialPlant.materialPlantId
  - MaterialPlant.onHandQuantity
  - MaterialRequirements.requirementId
  - MaterialRequirements.materialPlantId
  - MaterialRequirements.requirementQuantity
  - MaterialRequirements.requirementDate
  - MaterialRequirements.requirementType
  - PurchaseDocumentLine.purchaseDocumentLineId
  - PurchaseDocumentLine.materialPlantId
  - PurchaseDocumentLine.orderedQuantity
  - PurchaseDocumentLine.goodsReceiptQuantity
  - PurchaseDocumentLine.confirmedDeliveryDate
computed_by: assess_coverage
output: per uncovered requirement, quantity short and date; total and first date per material-plant
related: [projected-stock, committed-demand, safety-stock-breach, alerting]
---
# Shortfall

## Definition
Demand that projected stock can't cover: **how much** is short, and **by when**. This is the number the customer means by "how short, by when."

## Formula
Walk the [projected stock](projected-stock.md) timeline. When a requirement takes the balance below 0, the uncovered part is `min(requirementQuantity, −balance after it)`. The total shortfall is the sum over requirements; the first shortfall date is the earliest such requirement.

## How to read it
- Against [committed demand](committed-demand.md) → **Critical**: an order won't be met, and a production line may stop.
- Against forecast only → **Warning**: re-plan, don't spend.
- Measured against **zero**, not safety stock. The extra needed to restore the buffer is reported separately (see [safety-stock breach](safety-stock-breach.md)).

## Edge cases
- A later delivery doesn't cancel an earlier shortfall: stock that arrives after the requirement date doesn't cover it.
