---
id: date-slip
type: concept
aliases: [date slip, delay, slipped, pushed out, line moved, delivery date changed]
inputs:
  - Event.eventId
  - Event.objectType
  - Event.objectId
  - Event.activity
  - Event.timestamp
  - Event.attributes
  - PurchaseDocumentLine.purchaseDocumentLineId
  - PurchaseDocumentLine.confirmedDeliveryDate
  - PurchaseDocumentLine.requestedDeliveryDate
computed_by: find_changes
output: per slipped PO line, old date, new date, days slipped, reason, event id, when it was recorded
related: [event, purchase-document-line, critical-path-supply]
---
# Date slip

> "Today" means the [analysis date](../index.md#conventions): `metadata.asOfDate`, never the system clock.

## Definition
A vendor moved a PO line's confirmed delivery date **later**. Found in the [event log](../objects/event.md), not inferred from current fields.

## Formula
Events with `activity = 'Delivery Date Changed'` and `attributes.newConfirmedDeliveryDate > attributes.oldConfirmedDeliveryDate`. `days slipped = new − old`.

## How to read it
- A slip only matters if the line is [critical-path supply](critical-path-supply.md) for committed demand. Most slips are noise.
- The event gives the evidence the customer asked for: which line moved, from what date to what date, and why.
- The gap between the event timestamp and the analysis date is the **age** of the change. The data doesn't show when anyone noticed it.

## Edge cases
- A change to an **earlier** date is a pull-in, not a slip.
- Several changes on one line: the latest confirmed date is current; report the full chain.
