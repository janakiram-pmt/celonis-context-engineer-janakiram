---
id: projected-stock
type: concept
aliases: [projected stock, projected available stock, stock projection, coverage, running balance]
inputs:
  - MaterialPlant.materialPlantId
  - MaterialPlant.onHandQuantity
  - MaterialRequirements.requirementId
  - MaterialRequirements.materialPlantId
  - MaterialRequirements.requirementQuantity
  - MaterialRequirements.requirementDate
  - PurchaseDocumentLine.purchaseDocumentLineId
  - PurchaseDocumentLine.materialPlantId
  - PurchaseDocumentLine.orderedQuantity
  - PurchaseDocumentLine.goodsReceiptQuantity
  - PurchaseDocumentLine.confirmedDeliveryDate
computed_by: project_stock
output: timeline of (date, change, balance, source record) per material-plant
related: [open-supply, committed-demand, shortfall, safety-stock-breach, spare-stock]
assumptions:
  - name: same-day ordering
    value: demand is subtracted before supply is added on the same date
    why: Conservative. A delivery arriving late in the day can't cover a requirement due that morning.
  - name: backlog
    value: the balance may go negative; a missed requirement is still owed, and later supply fills it first
    why: Committed orders that miss their date are delivered late, not cancelled.
  - name: past-due demand
    value: a requirement dated before the analysis date that isn't Covered is still owed and counts as due on the analysis date
    why: Skipping it would hide a shortfall. Past-due requirements with status Covered are skipped, since on-hand already reflects them.
---
# Projected stock

> "Today" means the [analysis date](../index.md#conventions): `metadata.asOfDate`, never the system clock.

## Definition
A running balance over time for one material-plant. Start with stock on hand today, add [open supply](open-supply.md) on its arrival dates, and subtract demand on its requirement dates.

## Formula
`balance(today) = onHandQuantity`, then in date order: `balance += open quantity` for each arrival, `balance −= requirementQuantity` for each requirement (all demand types). Each step cites the record that caused it.

- **Points only where something changes:** today (`metadata.asOfDate`), every requirement date, and every arrival date. Between points the balance is flat; the balance on any date is the last point on or before it.
- **Same-day order:** demand before supply; same-day demand is served committed first, then by priority (High → Low), per [demand priority](../rules/demand-priority.md).
- **Runs to the last record:** through the latest requirement or arrival for the material-plant, not just to the next arrival. Consumers (e.g., [alerting](../rules/alerting.md)) apply their own horizon.

## How to read it
- Below 0 → demand can't be met: a [shortfall](shortfall.md).
- Below `safetyStock` → the buffer is eroded: a [safety-stock breach](safety-stock-breach.md).

## Edge cases
- Includes forecast demand. Separating committed from non-committed happens in [shortfall](shortfall.md).
- Requirements dated before today: if not `Covered`, they're still owed and count as due today; if `Covered`, on-hand already reflects them.
- Open supply confirmed before today and not received is **overdue** and isn't counted (see [open supply](open-supply.md)).
- Because shortfalls carry forward as backlog, the balance after a late delivery is what's left once the backlog is filled. Treating missed demand as lost would overstate later stock.

## Assumptions (ours, not the customer's)
- On the same date, demand comes before supply.
- Shortfalls carry forward as backlog: the balance can go negative, and later supply fills it first.
- Past-due requirements that aren't covered count as due today.
