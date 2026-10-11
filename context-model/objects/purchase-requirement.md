---
id: purchase-requirement
type: object
table: PurchaseRequirement
grain: one requisition
primary_key: purchaseRequirementId
aliases: [requisition, purchase request, PR]
related: [material-plant, purchase-document-line]
---
# Purchase requirement (requisition)

## Role
The request to buy that a PO line was created from. It records the original need (`neededByDate`). The supply that actually counts is the [PO line](purchase-document-line.md).

## Fields that matter
- `neededByDate`: when the buyer originally needed the material. Useful context for how late a slipped line is.
- `status`: `Converted` means a PO line exists for it.

## How it connects
- [Material-plant](material-plant.md) via `materialPlantId`.
- PO lines point to it: `PurchaseDocumentLine.purchaseRequirementId`.

## Events
- "Purchase Requirement Created".

## Gotchas
- It's not demand and not supply. Don't add its quantity to the PO line's, or supply is double-counted.
