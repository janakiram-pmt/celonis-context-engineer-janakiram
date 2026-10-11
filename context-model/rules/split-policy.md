---
id: split-policy
type: rule
strength: preference
params:
  allowed: true
  default: false
  cover_first: nearest_high_priority_requirement
source: discovery_interview.md (Maria)
applies_to: [shortfall, committed-demand]
used_by: [rank_resolution_options]
---
# Split policy

## Rule
Partial coverage is allowed: cover the nearest high-priority requirement from the fastest source, and let lower-priority or later demand wait for the original delivery. It must be a deliberate choice, not the default.

## Why
> "That's fine and we do it. Cover the nearest high-priority requirement from whatever's fastest, and let lower-priority or later demand wait for the original delivery. The only downside is a split creates extra receiving and admin work, so it should be a deliberate choice, not the default." (Maria)

## How to apply
- Prefer a plan that fully closes the gap. Use a split when that isn't possible, and say so.
- Note the extra receiving and admin work as a cost.

## What not to do
- Don't propose a split when a single option covers the gap.
