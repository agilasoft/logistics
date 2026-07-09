# Sales Quote: Separate Billings per Service Type and Internal Jobs

This document describes the **Separate Billings per Service Type** option on Sales Quote and the behaviour of **Internal Jobs** when a related service has no charges.

---

## 1. Checkbox: Separate Billings per Service Type

On the Sales Quote, in the **Routing** tab, the field **Separate Billings per Service Type** controls how charges are applied when creating Bookings and Orders from the quote.

| Checkbox | Behaviour |
|----------|-----------|
| **Checked** | Each Booking/Order gets **only the charges that match its service type**. Air Booking gets Air charges only; Sea Booking gets Sea charges only; Transport Order gets Transport charges only; Declaration gets Customs charges only. |
| **Unchecked** | **All charges** from the Sales Quote are added to the Booking/Order whose **document type matches the quote Main Service** (e.g. Sea Booking when quote Main Service is Sea). This applies **regardless of the Main Service checkbox** on that booking. Other service types still get their own Bookings/Orders with only their service-type charges; legs with no charges follow the Internal Job rules below. |

### 1.1 Quote Main Service vs booking Main Service checkbox

Two different fields control related but distinct behaviour:

| Field | Where | Role |
|-------|--------|------|
| **Main Service** (`main_service`) | Sales Quote header (Routing) | Selects which service mode carries **combined billing** when Separate Billings is off (Air, Sea, Transport, Customs, …). |
| **Main Service** (`is_main_service`) | Booking / Order / Job (Charges tab → Job Details) | Marks **service role** (primary operational job, internal-job hub, invoice routing). Does **not** gate charge rollup when Separate Billings is off. |

**Charge rollup when Separate Billings per Service Type is off** (example: quote Main Service = **Sea**):

| Document | Main Service checkbox | Charges loaded |
|----------|----------------------|----------------|
| Sea Booking | Checked or **unchecked** | **All** quote charges (Air + Sea + Customs + …) |
| Air Booking | Either | **Air only** |
| Declaration Order | Either | **Customs only** (plus customs-parameter filtering) |
| Transport Order | Either | **Transport only** |

**When Separate Billings per Service Type is on**, every document gets **only** charges matching its own service type (Sea Booking → Sea only), regardless of the quote Main Service field.

### 1.3 Multimodal quotes (Air + Sea + Transport + Customs on one Sales Quote)

A single Sales Quote may include charge lines for **several service types** (for example Air FREIGHT, Sea FREIGHT, Transport DELIVERY, Customs BROKERAGE, and Special Project fees). When you create or fetch charges onto operational documents, each booking/order receives **only the lines for its own service type** — unless **combined billing** applies (see §1.1).

| Operational document | Charges loaded from quote |
|----------------------|---------------------------|
| **Air Booking** / **Air Shipment** | **Air only** |
| **Sea Booking** / **Sea Shipment** | **Sea only** |
| **Transport Order** / **Transport Job** | **Transport only** |
| **Declaration Order** / **Declaration** | **Customs only** (plus customs-parameter filtering) |
| **Special Project** / programme jobs | Per programme rules (see [Special Projects](welcome/special-projects-module)) |

**Combined billing exception:** When **Separate Billings per Service Type** is **off** and the quote **Main Service** matches the document type (e.g. Main Service = **Sea** on a **Sea Booking**), that main-service document receives **all** quote charge rows. Other service documents still receive **only their own** `service_type`.

#### Example: quote Main Service = Special Project

Quote **PQ00234** (Main Service = **Special Project**, Separate Billings = off) has five charge lines:

| # | Item | Service type | Scope |
|---|------|--------------|-------|
| 1 | FREIGHT | Air | Linked |
| 2 | FREIGHT | Sea | Linked |
| 3 | DELIVERY | Transport | Linked |
| 4 | BROKERAGE FEE | Customs | Linked |
| 5 | SP-PM-FEE | Special Project | Main |

Expected split when creating jobs from this quote:

| Document | Charges loaded |
|----------|----------------|
| **Air Booking** (e.g. ABK-000000763) | Row 1 — **Air FREIGHT only** |
| **Sea Booking** | Row 2 — **Sea FREIGHT only** |
| **Transport Order** | Row 3 — **DELIVERY only** |
| **Declaration Order** | Row 4 — **BROKERAGE FEE only** |
| **Special Project** | Row 5 and programme rules for Main scope |

Sea charges must **not** appear on an Air Booking. If they do (for example after an older fetch), remove the Sea line or re-fetch from quotation after the platform update; create a **Sea Booking** for the Sea FREIGHT leg.

#### Fetch from Quotation / Create from Sales Quote

- **Air Booking → Fetch from Quotation** copies **Air** charge lines only and links them to an **Air** Linked Service on the booking.
- **Sea Booking** copies **Sea** lines only.
- Do not expect one operational document to carry freight charges for multiple modes unless that document is the **combined-billing main service** (§1.1).

#### Linked Services

Each charge line on the quote may reference a quote-level **Linked Service** (Internal Job). When you convert a **full** quote to a booking or order, the system **clones** those legs onto the operational document while the **quote keeps its originals** (same pattern as charge rows). **Blanket call-off** conversions clone only the legs tied to selected charges.

On operational documents (Sea/Air bookings and shipments, Transport orders and jobs), the **Services** tab shows a read-only view of that document's linked legs. Full user guide: [Linked Services on Operational Documents](welcome/linked-services-on-operational-documents).

An Air Booking should have **Air** Linked Services tied to **Air** charge rows — not Sea/Transport/Customs services unless those are separate internal legs created deliberately.

### 1.2 Charge tables on Bookings/Orders

- When **Separate Billings per Service Type** is **checked**: each document’s charges table is populated only with Sales Quote Charge rows where `service_type` matches that document (Air, Sea, Transport, Customs, etc.). Existing charge tables support this; ensure filters use `service_type` when this option is on.
- When **Separate Billings per Service Type** is **unchecked**: the **main service** Booking/Order must accept **all** charge types. Charge tables (e.g. Air Booking Charges, Sea Booking Charges, Transport Order Charges, Declaration Charges) must **allow all charges** from the quote—i.e. allow rows that may have different `service_type` or an “other service” indicator (e.g. `other_service_type`) so that the main job can carry Air + Sea + Transport + Customs + Warehousing etc. as needed.

---


<!-- wiki-field-reference:start -->

## Complete field reference

_Fields mentioned here (**Separate Billings per Service Type**, **Internal Job**, **Main Job**, routing, charges) are on **Sales Quote** and on each Booking / Order / Job DocType. Full column lists:_

- [Sales Quote](welcome/sales-quote)
- [Air Booking](welcome/air-booking), [Sea Booking](welcome/sea-booking), [Transport Order](welcome/transport-order), [Declaration Order](welcome/declaration-order), [Declaration](welcome/declaration)

<!-- wiki-field-reference:end -->

## 2. Internal Job: prerequisites before creation

When creating a Booking/Order as an **Internal Job** for a related service (e.g. Customs, Transport leg):

- The Sales Quote (or programme parent such as Docket / Special Project) must have **at least one charge line** for that `service_type`.
- A **matching Internal Job** must be defined on the **Internal Jobs** tab (Sales Quote `internal_job_details`, or the parent’s `internal_job_details` / `internal_jobs` table) with parameters that align to those charge lines.

If **either** is missing, creation is **blocked** with a clear message. The system no longer auto-creates internal jobs for legs with no quote charges.

### 2.1 Tagging as Internal Job

- Set **Internal Job** = 1 (or equivalent checkbox) on that Booking/Order/Job.
- Set **Main Job** reference to the main service job (the one that carries customer billing). This links the internal job to the main job for cost allocation and internal billing.

### 2.2 Internal billing and revenue/cost

For an **Internal Job**:

- **Charges**: Add applicable charges as **internal billing** (e.g. internal transfer / intercompany or internal cost allocation, not customer-facing).
- **Revenue**: Revenue of the Internal Job is set equal to the **Cost of the Main Job** (the cost allocated to or incurred by the main job for this service).
- **Cost**: Cost is as per **tariff** (or cost tariff) for the internal job’s service.

So:

- **Revenue (Internal Job)** = Cost of Main Job (allocated to this internal service).
- **Cost (Internal Job)** = As per tariff.

This keeps internal jobs at cost-neutral or at transfer price relative to the main job.

---

## 3. Summary

| Scenario | Separate Billings = Yes | Separate Billings = No |
|----------|--------------------------|--------------------------|
| Booking/Order **matching quote Main Service** (e.g. Sea Booking when quote Main Service = Sea) | Only charges for that service type | **All** charges from the quote (all service types) — **Main Service checkbox does not matter** |
| **Other** service Booking/Order (has charges in quote) | Only charges for that service type | Only charges for that service type |
| Other service Booking/Order (no charges or no matching Internal Job on quote) | **Blocked** — add charge lines and a matching Internal Job on the Internal Jobs tab | Same |

---

## 4. Implementation notes

- **Sales Quote**: Field `separate_billings_per_service_type` (Check) is in the Routing section.
- **Bookings/Orders** (e.g. Air Booking, Sea Booking, Transport Order, Declaration Order / Declaration): Support fields **Internal Job** (Check) and **Main Job** (reference: e.g. `main_job_type` + `main_job` Dynamic Link, or single link to the main job document).
- **Charge population**:
  - If `separate_billings_per_service_type` is true: filter Sales Quote Charges by `service_type` per document.
  - If false: the document whose doctype matches quote `main_service` gets all Sales Quote Charges (no `service_type` filter), **without requiring** `is_main_service` on that document; other documents get only their service type; internal jobs require both charge lines for the service and a matching row on the Internal Jobs tab.
- **Internal Job**: When creating a job/booking/order as an internal leg, ensure charge lines exist for that service and a matching Internal Job is configured on the quote before using **Create Internal Job** or **Create Booking/Order**.

---

## 5. Proposed design: dialog-driven Internal Job creation

### 5.1 Why change current flow

Current implementation auto-creates Internal Jobs for no-charge non-main legs, but users cannot confirm assumptions before creation. This update introduces a guided dialog so users can review defaults and provide missing operational details in one step.

### 5.2 Trigger points

Event the dialog when all conditions are true:

- User initiates **Create Bookings/Orders** from a Sales Quote.
- Leg is **non-main**.
- Leg service has **no quote charges** (internal job condition).
- Target document is not already created for that leg.

If multiple legs qualify, show the dialog once per leg in sequence, or as a leg selector within one modal.

### 5.3 Dialog goals

- Confirm that this leg will be created as an **Internal Job**.
- Pre-populate fields from Sales Quote, routing leg, and defaults.
- Collect only details that are still missing and required for the target job type.
- Prevent creating incomplete Internal Jobs.

### 5.4 Dialog structure

Suggested modal title:

- `Create Internal Job - {service_type} ({leg_identifier})`

Sections:

1. **Context (read-only)**
   - Sales Quote
   - Main Job (type + document)
   - Service Type
   - Routing leg reference
2. **Prefilled defaults (editable)**
   - Company / Billing Company
   - Branch / Cost Center / Department (if applicable)
   - Posting date / Expected dates
   - Currency and exchange rate policy
3. **Required additional details (must fill before submit)**
   - Operation owner / assignee
   - Vendor or partner details (if service-specific)
   - Service-specific operational fields (vehicle, vessel, customs office, etc.)
4. **Internal billing preview (read-only with override controls where allowed)**
   - `is_internal_job = 1`
   - `main_job_type` and `main_job`
   - Revenue basis: `= main job allocated cost`
   - Cost basis: `= tariff / configured costing rule`

### 5.5 Default population rules

Use deterministic fallback order:

1. **Routing leg values** (highest priority)
2. **Sales Quote header values**
3. **Party / company defaults**
4. **System defaults**

Examples:

- Company: leg company -> quote company -> user default company.
- Branch/cost center: leg -> quote -> company default.
- Dates: quote transaction date -> today.
- Currency: quote currency -> company currency.
- Main Job reference: always derived from the already-resolved main service document.

### 5.6 Required field strategy

Before showing submit action:

- Resolve required fields by target DocType metadata + service-specific rules.
- Mark fields as:
  - **Required now** (must be entered in dialog)
  - **Can defer** (allowed empty at creation, completed later)
- Disable submit until all **Required now** fields are valid.

Validation messages should be field-level and actionable (for example: `Select Transporter for Transport Internal Job`).

### 5.7 User actions

- **Create Internal Job**
  - Creates document with defaults + user input.
  - Applies internal flags and main-job linkage.
  - Runs normal server validations and returns created doc link.
- **Skip this leg**
  - Does not create current internal job; continue with other legs.
  - Log skipped leg in result summary.
- **Cancel all**
  - Stop creation flow; no further legs processed.

### 5.8 Post-submit behavior

After each successful creation:

- Event toast with created document name and service type.
- Append to a final summary table:
  - Created
  - Skipped
  - Failed (with reason)

If server-side creation fails, keep dialog open with returned error and preserve entered values.

### 5.9 API and backend expectations

- Keep existing backend rule: no-charge non-main service => internal job semantics.
- Extend create method input contract to accept `internal_job_dialog_payload` per leg.
- Server remains source of truth for:
  - Internal job flagging
  - Main job link integrity
  - Revenue/cost basis assignment
  - Permission and mandatory validation

### 5.10 Non-functional considerations

- **Auditability**: store who confirmed dialog and when.
- **Idempotency**: repeated submit should not duplicate jobs for same quote leg.
- **Performance**: bulk-create path should still support multi-leg processing with minimal round trips.
- **Consistency**: same dialog pattern should be reusable across Air, Sea, Transport, and Customs flows.
