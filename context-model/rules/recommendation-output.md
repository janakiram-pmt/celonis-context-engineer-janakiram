---
id: recommendation-output
type: rule
strength: hard
params:
  primary_recommendations: 1
  fallback_required: true
  numbers_from_tools_only: true
  required_evidence: [shortfall_quantity, shortfall_date, causal_event, affected_demand, options_considered, assumptions_used]
source: discovery_interview.md (Maria, Tom)
applies_to: [shortfall, date-slip, committed-demand]
used_by: [submit_briefing]
---
# Recommendation output

## Rule
Give **one** clear recommendation for what is actually broken, plus a fallback. Every number must come from a tool, and every claim must cite its evidence.

## Why
> "Show me the math. … I want the number — how short, by when — and why: which line moved, from what date to what date, what demand it was covering. If the number is just something the AI 'thinks,' that's worthless to me." (Maria)
>
> "Give me the recommendation, the evidence behind it, and ideally a fallback if the first option can't fully close the gap." (Tom)
>
> "One clear, correct, well-evidenced recommendation for the thing that's actually broken beats a dashboard of everything." (Tom)

## How to apply
Each recommendation includes:
- **Shortfall:** quantity and date (from [shortfall](../concepts/shortfall.md)).
- **Cause:** the event: which line, old → new date, reason, event id (from [date slip](../concepts/date-slip.md)).
- **Affected demand:** which requirements, their type and priority.
- **Options considered:** each with quantity, arrival date, cost note, and why it was chosen or rejected.
- **Fallback:** what to do if the primary option can't fully close the gap.
- **Assumptions used:** relayed from the tools.

## What not to do
- Never state a quantity or date that no tool returned.
- Don't list every material-plant; summarize the healthy ones in one line.
