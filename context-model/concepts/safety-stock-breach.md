---
id: safety-stock-breach
type: concept
aliases: [safety stock breach, below safety stock, below buffer, buffer eroded]
inputs: [MaterialPlant.safetyStock, MaterialPlant.onHandQuantity]
computed_by: assess_coverage
output: first date below safety stock, lowest balance, and whether (and when) open supply restores it
related: [projected-stock, open-supply, shortfall, alerting]
---
# Safety-stock breach

## Definition
[Projected stock](projected-stock.md) falls below the material-plant's `safetyStock`, the buffer the business isn't supposed to dip below.

## Formula
Breach dates = timeline dates where `balance < safetyStock`. **Restored** = some later [open supply](open-supply.md) arrival brings the balance back to ≥ `safetyStock`.

## How to read it
- Breach, no shortage, restored by open supply → **Watch**.
- Breach with no open supply to restore it, or with a shortfall for any demand → **Warning**.
- See [alerting](../rules/alerting.md) for the full tiers.

## Edge cases
- Stock can already be below safety stock **today**; that counts as a breach from today.
- Exactly at safety stock is not a breach.
