---
id: open-supply
type: concept
aliases: [open supply, inbound, incoming, replenishment, expected receipt, in flight]
inputs:
  - PurchaseDocumentLine.purchaseDocumentLineId
  - PurchaseDocumentLine.materialPlantId
  - PurchaseDocumentLine.orderedQuantity
  - PurchaseDocumentLine.goodsReceiptQuantity
  - PurchaseDocumentLine.confirmedDeliveryDate
computed_by: check_stock_risk
output: per PO line, quantity still to arrive and its arrival date
related: [purchase-document-line, projected-stock]
assumptions:
  - name: overdue supply
    value: an open line whose confirmed date is before the analysis date is not counted until it is received
    why: Nothing has arrived despite the promise, so assuming it lands today would hide a late-delivery risk.
---
# Open supply

## Definition
What is still coming in: for each PO line, the quantity not yet delivered, arriving on its confirmed date.

## Formula
`open quantity = orderedQuantity − goodsReceiptQuantity`, arriving on `confirmedDeliveryDate`. Only lines with open quantity > 0 count.

## How to read it
- Open supply is what ends a stock gap. No open supply means nothing is on the way.

## Edge cases
- Use `confirmedDeliveryDate`, never `requestedDeliveryDate`.
- Use quantities, not `lineStatus`. A stale status must not change the number.
- A partially received line contributes only its remainder.
- **Overdue** lines (confirmed date already passed, not fully received) are listed separately and not counted. They are a vendor issue in the why.

## Assumptions (ours, not the customer's)
- Overdue supply isn't counted until it's received.
