---
id: index
type: index
---
# Context Model: Index

**Read this first.** These files explain what the procurement data *means* and what the customer *wants*. Numbers always come from tools; never calculate them from these files.

The raw relational truth lives in [`../data-model/`](../data-model/erd.md). This layer sits on top of it.

## How it's organized

| Folder | Holds | Test |
|---|---|---|
| `objects/` | Things **stored** in tables: what they mean, which fields count, how they connect | Is it a table? |
| `concepts/` | Things **calculated** from tables: definition, formula, which tool computes it | Is it computed from tables? |
| `rules/` | The customer's **policy**, quoted from the discovery interview, with parameters the tools read | Did the customer decide it? |

Our own assumptions (things neither the data nor the customer states) sit in the file they affect, under **Assumptions (ours, not the customer's)** and in the `assumptions:` header.

## Files

**Objects**

| File | One line |
|---|---|
| [material-plant](objects/material-plant.md) | Inventory of one material at one plant; the hub demand and supply join through |
| [vendor](objects/vendor.md) | Supplier: lead time, on-time rate, quality |
| [vendor-approval](objects/vendor-approval.md) | Which vendor may supply which material-plant |
| [material-requirement](objects/material-requirement.md) | Demand: production order, sales order, or forecast |
| [purchase-requirement](objects/purchase-requirement.md) | Requisition a PO line was created from |
| [purchase-document](objects/purchase-document.md) | PO header; holds the vendor |
| [purchase-document-line](objects/purchase-document-line.md) | Inbound supply; its confirmed date is what counts |
| [event](objects/event.md) | What happened and when; the evidence for "why" |

**Concepts**

| File | One line |
|---|---|
| [committed-demand](concepts/committed-demand.md) | Production and sales orders; forecasts are not committed |
| [open-supply](concepts/open-supply.md) | Still to arrive = ordered − received, on the confirmed date |
| [projected-stock](concepts/projected-stock.md) | Running balance: on hand + arrivals − demand, by date |
| [shortfall](concepts/shortfall.md) | Demand not covered: how much, by when |
| [safety-stock-breach](concepts/safety-stock-breach.md) | Projected stock below safety stock, and whether supply restores it |
| [spare-stock](concepts/spare-stock.md) | What a plant can give away without dropping below its safety stock |
| [date-slip](concepts/date-slip.md) | A confirmed date moved later: old → new, reason, from the events |
| [vendor-reliability](concepts/vendor-reliability.md) | On-time rate + quality tier |
| [critical-path-supply](concepts/critical-path-supply.md) | Delivery that committed demand depends on |

**Rules**

| File | One line | Strength |
|---|---|---|
| [alerting](rules/alerting.md) | Critical / Warning / Watch / Quiet tiers; critical-path trigger; re-check after a plan | hard |
| [demand-priority](rules/demand-priority.md) | Committed, high-priority demand first | hard |
| [resolution-order](rules/resolution-order.md) | Transfer → alternate vendor → split → incumbent; never a new vendor | preference |
| [transfer-limit](rules/transfer-limit.md) | Never more than the sender's spare stock | hard |
| [vendor-eligibility](rules/vendor-eligibility.md) | Approved, on-time > 90%, quality A | hard |
| [spending-policy](rules/spending-policy.md) | Premium for committed demand only, never forecast | hard |
| [split-policy](rules/split-policy.md) | Allowed, but deliberate, not the default | preference |
| [recommendation-output](rules/recommendation-output.md) | One recommendation + fallback, tool numbers, cited evidence | hard |

**Hard** rules remove options. **Preference** rules rank the options that remain.

## Start here for common questions

| Question | Read |
|---|---|
| Is a material-plant at risk, and why? | [alerting](rules/alerting.md), [shortfall](concepts/shortfall.md), [date-slip](concepts/date-slip.md), [committed-demand](concepts/committed-demand.md) |
| What changed, and when? | [event](objects/event.md), [date-slip](concepts/date-slip.md) |
| What can we do about it? | [resolution-order](rules/resolution-order.md), [transfer-limit](rules/transfer-limit.md), [vendor-eligibility](rules/vendor-eligibility.md), [spending-policy](rules/spending-policy.md) |
| Is a vendor dependable? | [vendor-reliability](concepts/vendor-reliability.md), [critical-path-supply](concepts/critical-path-supply.md) |
| What should the answer look like? | [recommendation-output](rules/recommendation-output.md) |

## Customer words

| Customer says | Means | Go to |
|---|---|---|
| "the line moved" | A PO line's confirmed delivery date changed | [purchase-document-line](objects/purchase-document-line.md), [date-slip](concepts/date-slip.md) |
| "a line going down" | A production line stops. **Not modeled**; closest is a committed shortfall against a production order | [shortfall](concepts/shortfall.md) |
| "buffer" | Safety stock | [material-plant](objects/material-plant.md) |
| "spare above its buffer" | Spare stock | [spare-stock](concepts/spare-stock.md) |
| "top-up" | Cover the rest of a gap from an alternate approved vendor | [resolution-order](rules/resolution-order.md) |
| "expedite" | Get supply sooner: from an alternate vendor (preferred) or the incumbent (last resort) | [resolution-order](rules/resolution-order.md) |
| "firm sales order" | Any sales order (committed) | [committed-demand](concepts/committed-demand.md) |
