# Discovery Interview — Procurement / Materials Planning

*A ~20-minute discovery call, lightly edited for readability. Your solution should reflect what the customer tells you here: which actions they consider viable, what they prefer and avoid, and the situations they want flagged. Names are fictional.*

**Participants**
- **SE** — you (solution engineer, Celonis)
- **Maria** — Materials Planning Lead, Frankfurt plant (1010)
- **Tom** — Procurement Operations Manager (covers all plants)

---

**SE:** Thanks both. To start — when a supplier moves a delivery date, how do you find out today, and what do you do?

**Maria:** Honestly? Too late, usually. The date changes in the system and nobody tells me. I find out when I'm checking coverage for a production run and the parts aren't going to be there. By then I'm firefighting.

**Tom:** That's the core of it. We're reactive. A confirmed date slips, and the first real signal is a planner noticing a gap days later. If something could just flag "this specific line moved and it now puts a plant short," that alone would be worth a lot.

**SE:** Good — so surfacing a *confirmed date that moved later* on something that matters is the headline. What makes it "matter"?

**Maria:** Whether it actually threatens demand we've committed to. I don't care if a forecast slips a week. I care a lot if a **production order** or a firm **sales order** is going to go uncovered. Protect the committed, high-priority demand first — always. A line going down because a housing didn't show up is a very bad day; a forecast we can re-plan.

**Tom:** And please don't cry wolf. We have material-plants that sit comfortably above safety stock with steady supply. If the tool lights those up, planners will stop trusting it within a week. Alert fatigue is real. Flag the thing that's genuinely at risk, stay quiet on the rest.

**SE:** Understood. When something *is* at risk, what are your options, and how do you think about them?

**Maria:** A few plays. First, I look at whether another plant has stock I can pull — a transfer is usually my favorite because it's fast and it's inventory we already paid for. But — and this is important — I won't strip a sending plant below its own safety stock to cover me. I'm not going to create a second fire to put out the first. So a transfer only counts for what the other site can spare *above* its buffer.

**Tom:** Second option is expediting. And here's a strong preference: we do **not** like leaning on Rheinmetall to go faster. They'll say yes to an earlier date and then miss it — their reliability is poor and an expedite promise from them isn't worth much. So "ask the incumbent to hurry" is close to our last resort, not our first.

**Maria:** Right. If a transfer doesn't fully cover it, I'd rather bring in a **different, already-approved supplier** who's actually dependable — someone with a strong on-time record and good quality. We won't onboard a new vendor in a crisis and we won't use one that isn't approved for that material and plant. If they're approved and reliable — say, north of ninety percent on-time, top quality tier — that's who I want for the top-up.

**Tom:** We're willing to pay a premium to protect committed production. Cost matters, but continuity matters more when it's a high-priority order. For forecast demand, no — don't spend to expedite a forecast.

**SE:** What about only partially solving it — covering the urgent piece and letting the rest ride?

**Maria:** That's fine and we do it. Cover the nearest high-priority requirement from whatever's fastest, and let lower-priority or later demand wait for the original delivery. The only downside is a split creates extra receiving and admin work, so it should be a deliberate choice, not the default.

**SE:** If the tool recommends an action, what do you need to see to trust it?

**Maria:** Show me the math. If it just says "you're short," I won't believe it. I want the number — how short, by when — and *why*: which line moved, from what date to what date, what demand it was covering. If the number is just something the AI "thinks," that's worthless to me. It has to be calculated from the actual records.

**Tom:** Same. Give me the recommendation, the evidence behind it, and ideally a fallback if the first option can't fully close the gap. I don't need a fancy screen — I need a trustworthy call I can act on.

**SE:** Last thing — anything specific you always want watched, beyond this one event?

**Maria:** Confirmed dates slipping later on lines that cover near-term committed demand — top of the list. Stock projected to drop below safety stock. And a reliable-supplier issue on the critical path — if the only thing standing between me and a stockout is a vendor who misses half their dates, I want to know.

**Tom:** And keep scope sane. One clear, correct, well-evidenced recommendation for the thing that's actually broken beats a dashboard of everything.

**SE:** That's really helpful — thank you both.

---

## Requirements captured (SE's notes)

- **Detect and flag:** a *confirmed delivery date that moved later* on a line covering near-term **high-priority** demand; stock projected **below safety stock**; an unreliable vendor sitting on the critical path.
- **Protect committed demand first:** production/firm sales orders over forecast; never stop a line for a forecast.
- **Preferred resolution order (roughly):** (1) **stock transfer** from a plant with genuine surplus — *never* dropping the sending plant below its own safety stock; (2) **expedite via an alternate, already-approved, reliable supplier** (strong on-time record + top quality tier) for whatever the transfer can't cover; (3) **partial/split** coverage of the urgent piece; (4) **expedite with the incumbent** only as a last resort, because their reliability is poor.
- **Avoid:** false positives on healthy material-plants (alert fatigue); using non-approved or unreliable vendors; spending to expedite forecast demand.
- **Trust requirements:** every recommendation shows the computed shortfall (how much, by when) and the evidence (which line/event, which demand). Numbers must be **calculated from the records**, not asserted by the model. Provide a fallback option where the primary can't fully close the gap.
