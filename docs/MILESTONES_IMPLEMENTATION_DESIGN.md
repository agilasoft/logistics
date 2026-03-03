# Milestones Implementation – Revised Design

## Overview

This document describes the revised milestones implementation: **milestones as child tables** on Shipment, Job, and Declaration doctypes, **generated and updated from templates**, with optional **fetch** from external sources (carrier/EDI).

The design mirrors the existing **Document List Template** pattern: a template defines which items apply per product/context; parent documents get a child table populated from the template and an optional override template link.

---

## 1. Current State (Brief)

- **Job Milestone**: Standalone doctype with `job_type` (DocType) + `job_number` (Dynamic Link). One record per milestone per parent.
- **Logistics Milestone**: Master list of milestone codes (e.g. SF-GATE-IN, AF-DEPARTED) with flags (air_freight, sea_freight, transport, customs).
- Milestones are shown in a **virtual HTML table** via `get_milestone_html()` that queries `Job Milestone` by `job_type` and `job_number`.
- There is **no template**: which milestones appear is not driven by a configurable template; it’s implicit from usage or from the master.

---

## 2. Target State

### 2.1 Child tables on parents

Each supported parent has a **child table** of milestones (one row per milestone instance):

| Parent DocType       | Child Table DocType        |
|----------------------|----------------------------|
| Air Shipment         | Air Shipment Milestone     |
| Sea Shipment         | Sea Shipment Milestone     |
| Transport Job        | Transport Job Milestone    |
| Declaration          | Declaration Milestone      |
| General Job          | General Job Milestone (optional) |
| Special Project      | Special Project Milestone (optional) |

**Child table fields (common pattern):**

- `milestone` — Link to **Logistics Milestone**
- `status` — Select: Planned / Started / Completed
- `planned_start` — Datetime
- `planned_end` — Datetime
- `actual_start` — Datetime
- `actual_end` — Datetime
- Display order: use table `idx` (no separate sequence field)
- Optional: `source` — Select: Manual / Fetched (for “Fetched” tracking)
- Optional: `fetched_at` — Datetime (last time this row was updated from external source)

Parents that have **Documents** today may also get:

- `milestone_template` — Link to **Milestone Template** (optional override). If blank, resolution uses product type + applies_to + direction/entry_type like Document List Template.

### 2.2 Milestone Template (new)

A **Milestone Template** doctype defines which milestones apply for a given context, analogous to **Document List Template**:

**Milestone Template (master):**

- `template_name` — Data, unique
- `product_type` — Select: Air Freight / Sea Freight / Transport / Customs / Warehousing / Special Projects / General
- `applies_to` — Select: Booking / Shipment/Job / Both
- `direction` — Select: (blank) / Import / Export / Domestic / All
- `entry_type` — Select: (blank) / Direct / Transit / Transshipment / ATA Carnet / All
- `is_default` — Check (default template when no override is set)
- `description` — Small Text

**Milestone Template Item (child table):**

- `milestone` — Link to **Logistics Milestone**, required
- `sequence` — Int (order of milestones in the flow)
- Optional: `planned_days_offset` — Int (e.g. relative to job/shipment date for default planned dates)
- Optional: `date_basis` — Select: Job Date / ETD / ETA / Booking Date / Manual / None (for “Generate” logic)

Templates are filtered by `product_type` and `applies_to`; optionally by `direction` and `entry_type` (same pattern as document_management’s `get_document_template_items`).

### 2.3 Generation from template

- **When**: On “Generate from template” action and/or optionally on first save (if child table is empty and a template can be resolved).
- **How**:
  1. Resolve template: if parent has `milestone_template`, use it; else use same context as Document List Template (`product_type`, `applies_to`, `direction`, `entry_type` from parent) to pick default/non-default template.
  2. For each **Milestone Template Item** (ordered by `sequence`), append a child row: set `milestone`, `status = "Planned"`, and optionally `planned_start`/`planned_end` from `date_basis` + `planned_days_offset`. Table row order (idx) is used in dashboards.
  3. Only **add** rows for template items that are not already present (e.g. by `milestone` link); do not remove existing rows (user may have added extras or have actuals).
- **API**: e.g. `populate_milestones_from_template(doctype, docname)` in document_management or a dedicated milestone API module, called from client or from server events.

### 2.4 Fetched milestones

- **Meaning**: “Fetched” = actual (and optionally planned) dates/status updated from an external system (carrier API, EDI, etc.).
- **Storage**: On the child table row: optional `source` (Manual / Fetched) and `fetched_at`; actuals in `actual_start` / `actual_end`, status can be derived or stored.
- **Behaviour**:
  - A “Fetch milestones” action (or scheduled job) calls an integration that returns a list of milestone code + dates/status.
  - For each returned milestone, find the child row with matching `milestone` (Logistics Milestone code) and update `actual_start`, `actual_end`, and `status`; set `source = "Fetched"` and `fetched_at = now()`.
  - If the external system reports a milestone that does not exist on the child table, either: (a) ignore, or (b) optionally append a new row (with `source = "Fetched"`) if the template allows it or a config says “add missing from fetch”. Design choice: start with (a); document (b) as future option.
- **Templates**: Fetched data does not change which rows exist; that still comes from the template. Fetch only updates existing child rows. Generation from template remains the single place that adds/defines the set of milestone rows.

---

## 3. Doctype and Module Layout

### 3.1 New doctypes

- **Milestone Template** — module Logistics (or Document Management). Same module as Document List Template is reasonable.
- **Milestone Template Item** — child of Milestone Template, istable.

### 3.2 New child table doctypes (one per parent type)

- **Air Shipment Milestone** — istable, parent in Air Freight.
- **Sea Shipment Milestone** — istable, parent in Sea Freight.
- **Transport Job Milestone** — istable, parent in Transport.
- **Declaration Milestone** — istable, parent in Customs.
- (Optional) **General Job Milestone**, **Special Project Milestone** — if those parents should use the same pattern.

### 3.3 Parent doctype changes

- Add section “Milestones” with:
  - `milestone_template` — Link to Milestone Template (optional).
  - Child table: `milestones` (or `air_shipment_milestone` etc. per naming).
- Remove or deprecate reliance on standalone **Job Milestone** for these parents (and remove virtual `milestone_html` if replaced by the grid).
- Keep **Logistics Milestone** as the master; child tables link to it.

---

## 4. UI and Behaviour

### 4.1 Form

- **Milestones** section on the form: standard Frappe table/grid of the child table (editable). Columns: Milestone, Status, Planned Start, Planned End, Actual Start, Actual End, (optional) Source, Fetched At.
- Buttons/actions:
  - **Generate from template** — runs `populate_milestones_from_template`; only adds missing rows.
  - **Fetch milestones** (optional) — calls fetch API and updates existing rows’ actuals and status.

### 4.2 Dashboard / reports

- Any dashboard or report that today uses `Job Milestone` (e.g. delay alerts, run sheet layout) should be switched to read from the new child tables (e.g. `Air Shipment Milestone`, `Sea Shipment Milestone`, …) filtered by parent.
- Delay logic (e.g. Sea Shipment’s delay tracking) continues to use planned_end vs actual_end and “now”, but reads from the parent’s child table instead of Job Milestone.

### 4.3 Backward compatibility / migration

- **Job Milestone** can remain in the schema for a transition period. A one-time patch or script can:
  - For each parent (e.g. Air Shipment, Sea Shipment, …) that has Job Milestone rows, create corresponding child table rows and link them to the parent.
  - After migration, prefer the child table everywhere and stop creating new Job Milestone rows for these doctypes.
- Once all consumers are moved, Job Milestone can be deprecated or restricted to legacy data only.

---

## 5. API Summary

| API | Purpose |
|-----|--------|
| `get_milestone_template_items(product_type, applies_to, direction, entry_type)` | Resolve template and return list of milestone template items (for UI or server-side generate). |
| `populate_milestones_from_template(doctype, docname)` | Populate parent’s milestone child table from resolved (or override) template; only add missing milestones. |
| `fetch_milestones(doctype, docname)` (optional) | Call external integration and update child table rows’ actual_start, actual_end, status, source, fetched_at. |

---

## 6. Summary

- **Child tables** on Shipment, Job, Declaration (and optionally General Job, Special Project) hold one row per milestone instance.
- **Milestone Template** + **Milestone Template Item** define which milestones apply per product/context; **generation** populates the child table from the template (with optional parent-level template override).
- **Fetched** means updating existing child rows from an external source (carrier/EDI); generation from template remains the single source of which rows exist.
- **Logistics Milestone** stays the master; child rows link to it. Existing delay alerts and dashboards are adapted to read from the new child tables instead of Job Milestone.

This design keeps the same product-type and document-context model as Document List Template, and makes milestones consistent with the “template-driven child table” pattern used for documents.
