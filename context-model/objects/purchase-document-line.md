---
id: purchase-document-line
type: object
table: PurchaseDocumentLine
grain: one PO line item
primary_key: purchaseDocumentLineId
aliases: [line, PO line, supply line, inbound, delivery, purchase order line]
related: [purchase-document, material-plant, purchase-requirement]
---
# PO line (inbound supply)

## Role
A vendor's commitment to deliver a quantity of one material-plant by a date. This is the thing that "moves" when a vendor slips.

## Fields that matter
- `confirmedDeliveryDate`: the date that counts. `requestedDeliveryDate` is only what was asked for.
- `orderedQuantity` − `goodsReceiptQuantity` = quantity still to arrive (see [open supply](../concepts/open-supply.md)). Use the quantities, not `lineStatus`.
- `netPrice`: unit price paid to this vendor. The cost baseline for comparing options.

## How it connects
- Vendor: via [purchase document](purchase-document.md) (`purchaseDocumentId` → `vendorId`). The vendor is not on the line.
- [Material-plant](material-plant.md) via `materialPlantId`. Demand is reached only through it.
- [Requisition](purchase-requirement.md) via `purchaseRequirementId`.

## Events
- "Line Created", "Delivery Date Confirmed", "Goods Received".
- "Delivery Date Changed": attributes carry the old date, new date, and reason. That's the evidence for a [date slip](../concepts/date-slip.md).

## Gotchas
- When the customer says "the line moved", they mean this object, not a production line.
