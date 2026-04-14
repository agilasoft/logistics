# Sales Quote: Separate Billings per Service Type and Internal Jobs

This document describes the **Separate Billings per Service Type** option on Sales Quote and the behaviour of **Internal Jobs** when a related service has no charges.

---

## 1. Checkbox: Separate Billings per Service Type

On the Sales Quote, in the **Routing** tab, the field **Separate Billings per Service Type** controls how charges are applied when creating Bookings and Orders from the quote.

| Checkbox | Behaviour |
|----------|-----------|
| **Checked** | Each Booking/Order gets **only the charges that match its service type**. Air Booking gets Air charges only; Sea Booking gets Sea charges only; Transport Order gets Transport charges only; Declaration gets Customs charges only. |
| **Unchecked** | **All charges** from the Sales Quote are added to the **main service** Booking/Order. The main service is the one marked as Main Job in the routing legs (or the quote’s main service). Other service types still get their own Bookings/Orders where applicable, but charge handling follows the Internal Job rules below when they have no charges. |

### 1.1 Charge tables on Bookings/Orders

- When **Separate Billings per Service Type** is **checked**: each document’s charges table is populated only with Sales Quote Charge rows where `service_type` matches that document (Air, Sea, Transport, Customs, etc.). Existing charge tables support this; ensure filters use `service_type` when this option is on.
- When **Separate Billings per Service Type** is **unchecked**: the **main service** Booking/Order must accept **all** charge types. Charge tables (e.g. Air Booking Charges, Sea Booking Charges, Transport Order Charges, Declaration Charges) must **allow all charges** from the quote—i.e. allow rows that may have different `service_type` or an “other service” indicator (e.g. `other_service_type`) so that the main job can carry Air + Sea + Transport + Customs + Warehousing etc. as needed.

---


<!-- wiki-field-reference:start -->

## Complete field reference

_Fields mentioned here (**Separate Billings per Service Type**, **Internal Job**, **Main Job**, routing, charges) are on **Sales Quote** and on each Booking / Order / Job DocType. Full column lists:_

- [Sales Quote](welcome/sales-quote)
- [Air Booking](welcome/air-booking), [Sea Booking](welcome/sea-booking), [Transport Order](welcome/transport-order), [Declaration Order](welcome/declaration-order), [Declaration](welcome/declaration)

<!-- wiki-field-reference:end -->

## 2. Internal Job: when there are no charges for a related service

When creating a Booking/Order for a **non‑main** service type (e.g. Customs, Transport leg) from the same Sales Quote:

- If the quote has **no charges** for that service type (no rows in Sales Quote Charges for that `service_type`), the created document must be treated as an **Internal Job**.

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
| Main service Booking/Order | Only charges for that service type | **All** charges from the quote (all service types allowed in charges table) |
| Other service Booking/Order (has charges in quote) | Only charges for that service type | Only charges for that service type |
| Other service Booking/Order (no charges in quote) | Create as **Internal Job**, reference **Main Job**; charges = internal billing; Revenue = Cost of Main Job; Cost = as per tariff | Same: **Internal Job**, reference **Main Job**; internal billing; Revenue = Cost of Main Job; Cost = as per tariff |

---

## 4. Implementation notes

- **Sales Quote**: Field `separate_billings_per_service_type` (Check) is in the Routing section.
- **Bookings/Orders** (e.g. Air Booking, Sea Booking, Transport Order, Declaration Order / Declaration): Support fields **Internal Job** (Check) and **Main Job** (reference: e.g. `main_job_type` + `main_job` Dynamic Link, or single link to the main job document).
- **Charge population**:
  - If `separate_billings_per_service_type` is true: existing behaviour—filter Sales Quote Charges by `service_type` per document.
  - If false: main service document gets all Sales Quote Charges (no `service_type` filter for main); other documents get only their service type; if a non‑main service has no charges, create as Internal Job and apply internal billing/revenue/cost rules above.
- **Internal Job**: When creating a job/booking/order for a leg with no charges for that service, set Internal Job and Main Job reference, then create charges as internal billing with Revenue = Cost of Main Job and Cost as per tariff.

---

## 5. Proposed design: dialog-driven Internal Job creation

### 5.1 Why change current flow

Current implementation auto-creates Internal Jobs for no-charge non-main legs, but users cannot confirm assumptions before creation. This update introduces a guided dialog so users can review defaults and provide missing operational details in one step.

### 5.2 Trigger points

Show the dialog when all conditions are true:

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

- Show toast with created document name and service type.
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
