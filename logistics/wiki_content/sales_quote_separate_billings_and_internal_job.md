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
