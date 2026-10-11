---
id: vendor
type: object
table: Vendor
grain: one supplier
primary_key: vendorId
aliases: [vendor, supplier, incumbent, alternate supplier]
related: [vendor-approval, purchase-document]
---
# Vendor (supplier)

## Role
A supplier that fulfils purchase orders. Its attributes decide whether it can be trusted on the critical path or used for a top-up.

## Fields that matter
- `avgLeadTimeDays`: how long a **new** order typically takes. Used to judge whether an alternate vendor can arrive in time, and to set the alerting horizon.
- `onTimeDeliveryRate`: share of lines delivered on or before the confirmed date, trailing 12 months (0–1). See [vendor reliability](../concepts/vendor-reliability.md).
- `qualityRating`: A (best) to C.

## How it connects
- Its POs: `PurchaseDocument.vendorId` → [purchase document](purchase-document.md). The vendor sits on the PO **header**, not on the line.
- What it may supply: `VendorApproval.vendorId` → [vendor approval](vendor-approval.md)

## Events
None are recorded against vendors. A vendor's behavior shows up as events on its PO lines (e.g., "Delivery Date Changed").

## Gotchas
- The "incumbent" is whichever vendor holds the open PO line for that material-plant. It's a role, not a field.
- `avgLeadTimeDays` is a historical average, not a promise.
