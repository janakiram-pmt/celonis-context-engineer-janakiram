---
id: vendor-approval
type: object
table: VendorApproval
grain: one vendor approved for one material-plant
primary_key: [vendorId, materialPlantId]
aliases: [approved supplier, approved vendor, approval, approved for]
related: [vendor, material-plant]
---
# Vendor approval

## Role
The list of who may supply what. A vendor can only be considered for a material-plant if a row exists here. That's the first filter in [vendor eligibility](../rules/vendor-eligibility.md).

## Fields that matter
- `vendorId` + `materialPlantId`: a row means "approved". There are no other attributes.

## How it connects
- [Vendor](vendor.md) via `vendorId`; [material-plant](material-plant.md) via `materialPlantId`.

## Events
None.

## Gotchas
- Built from the source field `Vendor.approvedForMaterials` (a list), normalized into rows.
- Approval is **current** state. Existing POs aren't checked against it, since an approval may have changed after a PO was placed. The rule applies when choosing a vendor now.
