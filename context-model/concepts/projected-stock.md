---
id: projected-stock
type: concept
aliases: [projected stock, projected available stock, stock projection, coverage, running balance]
inputs: [MaterialPlant.onHandQuantity, MaterialPlant.safetyStock, MaterialRequirements.requirementQuantity, MaterialRequirements.requirementDate, PurchaseDocumentLine.confirmedDeliveryDate]
computed_by: project_stock
output: timeline of (date, change, balance, source record) per material-plant
related: [open-supply, committed-demand, shortfall, safety-stock-breach, spare-stock]
assumptions:
  - name: same-day ordering
    value: demand is subtracted before supply is added on the same date
    why: Conservative. A delivery arriving late in the day can't cover a requirement due that morning.
---
# Projected stock

## Definition
A running balance over time for one material-plant. Start with stock on hand today, add [open supply](open-supply.md) on its arrival dates, and subtract demand on its requirement dates.

## Formula
`balance(today) = onHandQuantity`, then in date order: `balance += open quantity` for each arrival, `balance −= requirementQuantity` for each requirement (all demand types). Each step cites the record that caused it.

- **Points only where something changes:** today (`metadata.asOfDate`), every requirement date, and every arrival date. Between points the balance is flat; the balance on any date is the last point on or before it.
- **Runs to the last record:** through the latest requirement or arrival for the material-plant, not just to the next arrival. Consumers (e.g., [alerting](../rules/alerting.md)) apply their own horizon.

## How to read it
- Below 0 → demand can't be met: a [shortfall](shortfall.md).
- Below `safetyStock` → the buffer is eroded: a [safety-stock breach](safety-stock-breach.md).

## Edge cases
- Includes forecast demand. Separating committed from non-committed happens in [shortfall](shortfall.md).
- Dates before today are not projected; on-hand already reflects them.

## Assumptions (ours, not the customer's)
- On the same date, demand comes before supply.
