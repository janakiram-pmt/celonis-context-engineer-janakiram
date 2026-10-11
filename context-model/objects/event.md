---
id: event
type: object
table: Event
grain: one thing that happened to one object
primary_key: eventId
aliases: [event, event log, history, change, activity]
related: [purchase-document-line, purchase-document, purchase-requirement, material-requirement]
---
# Event (what happened, and when)

## Role
The append-only log of activities. The current fields on objects say **what is true now**; events say **when and why it became true**. They supply the "why" in a recommendation.

## Fields that matter
- `objectType` + `objectId`: the object the event was recorded against (a table name and its key).
- `activity`, `timestamp`: what happened, when.
- `attributes` (JSON): activity-specific details. For example, "Delivery Date Changed" carries `oldConfirmedDeliveryDate`, `newConfirmedDeliveryDate`, and `reason`; "Goods Received" carries `goodsReceiptQuantity`.

## Activities in the data
Purchase Requirement Created · Purchase Order Created · Purchase Order Approved · Line Created · Delivery Date Confirmed · **Delivery Date Changed** · Goods Received · Requirement Registered

## How it connects
- `objectType` names the table; `objectId` is its key. To reach the affected material-plant from a PO line event, go through the line: `objectId` → `PurchaseDocumentLine.materialPlantId`.

## Gotchas
- Each event is recorded against exactly one object, but its effect travels through foreign keys. A date change on a line affects the material-plant it supplies, and so the demand against that material-plant.
- `objectId` isn't a database foreign key. The loader validates every reference.
