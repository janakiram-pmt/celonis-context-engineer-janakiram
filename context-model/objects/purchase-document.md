---
id: purchase-document
type: object
table: PurchaseDocument
grain: one purchase order header
primary_key: purchaseDocumentId
aliases: [purchase order, PO, PO header]
related: [vendor, purchase-document-line]
---
# Purchase document (PO header)

## Role
Groups PO lines under one vendor. Use it to find **who** is supplying a line.

## Fields that matter
- `vendorId`: the supplier for all its lines.
- `status`: header lifecycle (Open / PartiallyReceived / Closed). Informational.

## How it connects
- [Vendor](vendor.md) via `vendorId`.
- Its lines: `PurchaseDocumentLine.purchaseDocumentId` → [PO line](purchase-document-line.md) (one-to-many).

## Events
- "Purchase Order Created", "Purchase Order Approved".

## Gotchas
- Quantities, dates, and material-plants live on the **lines**, not here.
