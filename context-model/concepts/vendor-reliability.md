---
id: vendor-reliability
type: concept
aliases: [vendor reliability, supplier reliability, on-time rate, OTD, dependable, quality tier]
inputs:
  - Vendor.vendorId
  - Vendor.onTimeDeliveryRate
  - Vendor.qualityRating
  - Vendor.avgLeadTimeDays
  - VendorApproval.vendorId
  - VendorApproval.materialPlantId
computed_by: find_alternate_vendors
output: per vendor, on-time rate, quality tier, lead time, and pass/fail against vendor eligibility
related: [vendor, vendor-eligibility, critical-path-supply]
---
# Vendor reliability

## Definition
How likely a vendor is to deliver on its confirmed date, at acceptable quality. Read directly from the vendor's record.

## Formula
- On-time: `onTimeDeliveryRate` (share of lines delivered on or before the confirmed date, trailing 12 months).
- Quality: `qualityRating` (A best).
- Pass/fail uses the thresholds in [vendor eligibility](../rules/vendor-eligibility.md).

## How to read it
- `1 − onTimeDeliveryRate` is roughly the chance a confirmed date won't hold. An expedite promise from an unreliable vendor carries the same risk.

## Edge cases
- Lead time is an average, not a commitment.
