---
id: spare-stock
type: concept
aliases: [spare stock, surplus, transferable stock, stock to spare, above its buffer]
inputs:
  - MaterialPlant.materialPlantId
  - MaterialPlant.onHandQuantity
  - MaterialPlant.safetyStock
  - MaterialPlant.materialId
  - MaterialRequirements.requirementId
  - MaterialRequirements.materialPlantId
  - MaterialRequirements.requirementQuantity
  - MaterialRequirements.requirementDate
  - PurchaseDocumentLine.purchaseDocumentLineId
  - PurchaseDocumentLine.materialPlantId
  - PurchaseDocumentLine.orderedQuantity
  - PurchaseDocumentLine.goodsReceiptQuantity
  - PurchaseDocumentLine.confirmedDeliveryDate
computed_by: find_transfer_options
output: per other plant holding the same material, quantity it can give away
related: [projected-stock, material-plant, transfer-limit]
---
# Spare stock

> "Today" means the [analysis date](../index.md#conventions): `metadata.asOfDate`, never the system clock.

## Definition
How much a plant can give away **without going below its own safety stock**, counting its own demand before its next delivery. This is Maria's "what the other site can spare above its buffer."

## Formula
For a sending material-plant: `spare = max(0, min(balance − safetyStock))` over its [projected stock](projected-stock.md) timeline from today up to (not including) its next open-supply arrival. If it has no open supply, use the whole horizon.

## How to read it
- Candidates are other material-plants with the same `materialId`.
- The amount actually transferred is capped by [transfer limit](../rules/transfer-limit.md).

## Edge cases
- The sender's forecast demand counts. Taking stock it will need anyway just moves the problem.
- Supply arriving later doesn't increase spare stock today; the gap before it arrives is what matters.
