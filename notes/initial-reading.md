From README file:
Build the foundations and agentic application that can:
    1. Distill signal from noise.
    2. Validate if there is a risk.
    3. Quantify the risk.
    4. Recommend next steps or path to resolution.
    5. Show evidence backing the recommendation - explainability.
    6. Do all of this fast.

Requirements
    1. Viable resolution actions.
    2. Which ones they prefer? Why?
    3. Which ones they avoid? Why?
    4. How they prioritize?
    5. Constraints to respect.
    6. Situations they want flagged and the ones they don't to avoid decision fatigue - basically, what they will consider risk vs not.

Tasks:
1. Classic DB model (ERD should suffice and suites github)
2. Semantic layer (.md or yaml should suffice and github friendly)
3. Application - shape can be CLI or web app.
4. Protect from hallucinations by relying on tools (deterministic decision functions) for numbers.
5. Blueprint to weave technical choices to business value. (a) Define current architecture, (b) How to scale?, (c) Value prop: How will you sell this to an executive buyer? How to measure success?

1. Max 3 tools.
2. Repo format provided - stick to it as much as possible.

From the discovery interview:
First pass:
1. Honestly? Too late, usually. We are reactive -> Timing is as important as accuracy of flagging a risk. The solution should flag risks proactively.
2. I don't care if a forecast slips a week. I care a lot if a **production order** -> Differentiate real risk from noise.
3. Alert fatigue is real. -> Too many false positive reduces trust on the tool.
4. Options: (1) **stock transfer** from another plant only so much that plant can afford. (2) If transfer does not cover, then **expedite** - bring in an already-approved and trusted supplier different from the incumbent. Continuity over cost. Willing to negotiate a premium (excluding forecast). (3) Cover only what is urgent - **split** orders increase **receiving work** - generally avoided. (4) Push the incumbent - they almost always say yes but delay. (5) Bring in a new supplier to manage crisis - won't work.
5. Explainability and details. Not just "short". How short? when and why? Include fallbacks. "Calculated from the actual records"
6. "Don't need a fancy screen". "One clear, correct, well-evidenced recommendation for the thing that's actually broken".
7. Anomalies: (a) Confirmed dates slipping for near-term committed demand. (b) stock when goes below safety stock. (c) unreliable vendor on the critical.

*Thoughts*: It looks like a anomaly notifying agent is a better solution than a chat agent. The agent should proactively initiate and share a report. If the customer has to ask "anything wrong today?", thats already a bad experience.

Second pass (formula and keywords for the semantic layer):
1. "**coverage** for a **production run**". "**parts** aren't going to come"
2. "this specific **line** moved and it now puts a **plant** **short**"
3. I don't care if a **forecast** slips a week. I care a lot if a **production order** or a firm **sales order** is going to go uncovered. Protect the committed, high-priority demand first — always. A **line** going down because a housing didn't show up is a very bad day.
4. We have **material-plants** that sit comfortably above **safety stock** with steady **supply**.
5. It's **inventory** we already paid for.
6. spare above its **buffer**.
7. **vendor** **crisis**
8. **already-approved supplier**
9. supplier / vendor reliability = north of ninety percent **on-time**, top quality tier
10. **top-up**
11. **which line moved**.
12. Confirmed dates slipping later on lines that cover **near-term committed demand** — top of the list. **Stock projected to drop below safety stock**. And a **reliable-supplier issue** on the **critical path** — if the only thing standing between me and a **stockout** is a vendor who misses half their dates, I want to know.

*Thoughts*: Its looks the word "line" can have 2 different meanings based on context. "line moved" means the delivery date for a supply line has changed. "line going down" means a production line disrupted. Something to be clear in the semantic layer. 

From data scheme:

1st pass
1. Supplier reliability is fairly straightforward. Vendor data already has onTimeDeliveryRate and qualityRating.
2. Bavaria Precision Parts AG serves the same material-plant as Rheinmetall. Bavaria is also highly reliable vendor. 
3. Material-plant -> Its interesting that we don't have depletion rate directly. Something to be computed from events? Or computed using reorder point, safety stock and average lead time?
5. AsOfDate for this dataset is 4th Sept.
4. Leipzig is comfortably above safety stock for the same material Frankfurt is struggling for.
5. *Question* How connected is material requirements to the reorder point? Are all the material requirements raised at the reorder point? Also, there is no date for when the requirement was raised.
6. *Question* How is material req. and purchase req. are interelated? PR is part of the usual procure-to-pay. Not sure about material req.
7. Purchase doc = PO. PR for Rheinmetall was raised on 10th Aug and it was converted into PO on 12th Aug for 400 units of bear housing, cast (MP-1010-8891). *Question* Does that mean it reached the reorder point of 200 on 10th Aug? Will this help estimate depletion rate?
8. Purchase doc line ties it all back to the PR along with details of delivery status. *Question* Still unclear the point of material requirement because of lack of any foreign key connection.
9. 5th Aug MREQ-7001 was created. this is the material req. for the material-plant in question.
10. Rheinmetall confirmed 11th Sept delivery date on 15th Aug.
11. Its interesting that the PO for both plants Frankfurt and Leipzig is placed with Rheinmetall. No PO with Bavaria which is a highly reliable approved supplier for the same material.

2nd pass.
1. Realized that material requirements represents demand raised for the material-plant combination. PR represents the approved request for supply. 
2. Depletion rate is not available. But we can use material requirements to understand the immediate demand and demand severity.
3. With the given data, we cannot know when something reaches reorder point.
