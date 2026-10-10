# Data Model — Human-Readable Companion

This document explains the source data in [`../data/mock_data_schema.json`](../data/mock_data_schema.json) in plain language. The JSON is the source of truth; this is here so you can orient quickly. You do **not** need to clean the data — it is intentionally consistent and complete. Note that it covers **several** materials, plants, vendors and purchase orders; most are operating normally, and part of the task is to find the one situation that actually needs attention.

## The shape of the file

The JSON has four top-level sections:

- **`objects`** — six object *types* (below), each with an attribute schema *and* sample `records`. There are multiple records per type (several material-plants, vendors, POs, etc.).
- **`events`** — a flat, append-only event log across objects (this is what makes the data object-centric / process-aware).
- **`relationships`** — the foreign-key edges between object types, stated explicitly.
- **`scenario`** — the framing: what changed, and what you're asked to do. It intentionally does **not** state the impact or the options.

## The six object types

| Object | Grain | Role |
|--------|-------|------|
| **Vendor** | one supplier | Fulfils purchase documents. Carries lead time, on-time rate, quality, and which material-plants it's approved to supply. |
| **MaterialPlant** | one material at one plant | The inventory state: on-hand, safety stock, reorder point, standard cost. |
| **MaterialRequirements** | one unit of demand | Demand (production order, sales order, forecast) against a material-plant, with a date and priority. |
| **PurchaseRequirement** | one requisition | The demand-driven request to buy. |
| **PurchaseDocument** | one PO header | Groups lines under one vendor. |
| **PurchaseDocumentLine** | one PO line item | The ordered quantity, prices, and the requested vs. **confirmed delivery date** — plus receipt status. |

## How they connect

```
Vendor ──placedWith── PurchaseDocument ──has── PurchaseDocumentLine
                                                     │ convertedFrom → PurchaseRequirement
                                                     │ supplies       → MaterialPlant
MaterialRequirements ──demands──────────────────────┘ (same MaterialPlant)
```

Every relationship is also declared machine-readably in the `relationships` block, with cardinality and the joining field.

## The events layer

Each event references the object it belongs to (`objectType` + `objectId`) plus an `activity` and `timestamp`. Replaying them reconstructs each object's lifecycle — creations, confirmations, goods receipts, and date changes. Treating these as a process/event stream (rather than only reading current attribute values) is what lets you explain *when and why* something changed.

## How coverage risk works (the concept — not the answer)

A material-plant is at risk when the stock **projected to be available** falls below the **demand due before the next replenishment arrives**. To reason about it you combine, per material-plant: current on-hand and safety stock, the demand against it (quantities, dates, priority), and the timing and quantity of inbound purchase order lines (their confirmed delivery dates and receipt status). Safety stock is the buffer you're not supposed to dip below. Working out *whether* — and *by how much* — any material-plant is short is part of the task; we don't state the figure here.

## Where your options live

The data is built so that, where a genuine risk exists, more than one reasonable response is possible. The attributes that give you room to manoeuvre include vendor lead times, on-time rates, quality and approvals (`Vendor`), and inventory held at other plants for the same material (`MaterialPlant`). Discovering which options are actually viable for the situation you find — and weighing their trade-offs — is up to you. There is no single correct answer. Show your reasoning.
