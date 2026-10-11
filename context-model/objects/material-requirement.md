---
id: material-requirement
type: object
table: MaterialRequirements
grain: one unit of demand against a material-plant
primary_key: requirementId
aliases: [demand, requirement, production order, sales order, forecast, production run]
related: [material-plant]
---
# Material requirement (demand)

## Role
What will consume stock, and when. Whether it's **committed** decides how much it matters (see [committed demand](../concepts/committed-demand.md)).

## Fields that matter
- `requirementType`: `ProductionOrder` / `SalesOrder` (committed) or `Forecast` (not committed).
- `requirementQuantity`, `requirementDate`: how much is needed, by when.
- `priority`: High / Medium / Low. Ranks demand within the committed group.
- `status`: informational. Coverage is **computed** from stock and supply, not read from this field.

## How it connects
- Only through `materialPlantId` → [material-plant](material-plant.md). There is no link to the PO line that will cover it; demand and supply are netted per material-plant by date.

## Events
- "Requirement Registered": when the demand became known.

## Gotchas
- A production order is the closest thing in the data to a production line. A shortfall against it is what "a line going down" means.
