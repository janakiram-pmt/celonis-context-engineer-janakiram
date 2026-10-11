---
id: material-plant
type: object
table: MaterialPlant
grain: one material at one plant
primary_key: materialPlantId
aliases: [material-plant, inventory, stock, plant stock, site stock]
related: [material-requirement, purchase-document-line, purchase-requirement, vendor-approval]
---
# Material-plant (inventory of one material at one site)

## Role
The unit that risk is assessed at. Demand, supply, and vendor approvals all attach to a material-plant, so it's the hub every risk question joins through.

## Fields that matter
- `onHandQuantity`: physical stock as of `metadata.asOfDate`. The starting point of [projected stock](../concepts/projected-stock.md).
- `safetyStock`: the buffer (the customer's word: "buffer"). Plans should not dip below it. It also caps what this plant can give away (see [spare stock](../concepts/spare-stock.md)).
- `reorderPoint`: the level that normally triggers replenishment. Informational only. The data has no stock history, so it isn't used to judge risk.
- `standardCost`: valuation per unit, not the price paid. Prices are on PO lines.
- `materialId`: the same material at other plants. Those rows are the transfer candidates.

## How it connects
- Demand: `MaterialRequirements.materialPlantId` → [material requirement](material-requirement.md)
- Supply: `PurchaseDocumentLine.materialPlantId` → [PO line](purchase-document-line.md); requisitions via `PurchaseRequirement.materialPlantId`
- Approved vendors: `VendorApproval.materialPlantId` → [vendor approval](vendor-approval.md)
- Same material elsewhere: other `MaterialPlant` rows with the same `materialId`

## Events
None are recorded against a material-plant directly. Changes reach it through events on its PO lines and requirements.

## Gotchas
- Demand and supply are never linked to each other directly. They are netted here, by date.
- The pair (`materialId`, `plantId`) is unique. Neither field is unique on its own.
