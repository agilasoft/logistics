# Special Project: Lifecycle Jobs and Charge Roll-up

**Status:** Phase 1–2 implemented  
**Last updated:** 2026-06-03  
**Context:** Charge-to-lifecycle allocation uses inline **Lifecycle Jobs** (plural) child rows on the Charges tab; legacy `lifecycle_job_row`, Programme Lifecycle Job registry, and standalone SPCLT documents were removed.

---

## 1. Purpose

This document captures how **Lifecycle Jobs**, **programme charges**, and **operational jobs** should work together on Special Project — what the product does today, what breaks, and what we recommend before changing code.

It is the reference for implementation of execution-led financial roll-up from jobs linked on lifecycle rows (`job_no`).

---

## 2. Key concepts

| Term | Meaning |
|------|---------|
| **Special Project** | Programme document; ERPNext Project; multimodal portfolio. |
| **Lifecycle Job** (`lifecycle_jobs`, singular DocType) | One **planned operational leg** on the Lifecycle tab (Air, Sea, Transport, Customs, etc.). Drives create booking/order and lifecycle stage gating. |
| **Programme charges** (`charges` on Special Project) | Budget / quote lines on the Charges tab. |
| **`lifecycle_job_allocations`** (`Lifecycle Jobs`, plural DocType) | Child table on Special Project (Charges tab): links a **charge row** to a **lifecycle job line** with `cost_allocation_percentage`, `job_no`, and computed `allocated_cost` / `allocated_revenue`. % must sum to 100% per charge when multiple rows exist. |
| **`allocation_method`** (on charge) | **Equal** (auto-split 100% across allocation rows) or **Custom** (user sets % per row; validated on save). |
| **`job_no`** (on a lifecycle row) | Link to the created operational document (e.g. Transport Order). Used for create flow, milestones, maps — **not** automatic financial sync today. |
| **Operational job** | Transport Order, Transport Job, Air/Sea Booking/Shipment, Declaration, etc. |
| **Internal job** | Document with `is_internal_job=1` and `main_job` / `main_job_type`. Its charge totals roll up to the **main service’s Internal Job Detail** row (see `logistics.utils.internal_job_main_rollup`). |
| **Main service** | Primary leg document (e.g. Transport Order with `is_main_service=1`). Special Project–created transport orders are typically **standalone mains** (`is_internal_job=0`), one per lifecycle row. |

---

## 3. Current behaviour (as implemented)

### 3.1 On Special Project save (`validate`)

1. `_sync_charges_with_parent_actuals()` — recalculates **each programme charge** `actual_cost` / `actual_revenue` via charge calculation (SI/PI, recognition), not from linked Transport Order.
2. `recompute_all_charge_tag_allocations()` / `validate_charge_lifecycle_allocations()` — proportional `allocated_cost` / `allocated_revenue` per allocation row; **Cost Allocation % must sum to 100%** when multiple rows exist for one charge.
3. `sync_lifecycle_job_planned_from_charges()` — sums programme charges into each lifecycle row’s **`planned_cost` / `planned_revenue`**, using allocation rows (or implicit 100% when exactly one lifecycle row matches the charge service type).

Relevant code: `logistics/special_projects/special_project_charge_lifecycle.py`, `lifecycle_job_planned_rollup.py`, `special_project.py` validate.

### 3.2 Validation that caused the error

When a charge has **allocation rows**, each row must reference a valid **Lifecycle Job** line on the same Special Project; duplicate lines per charge are rejected; allocation % must sum to 100%.

Charges **without** allocation rows still attribute to a lifecycle row when **exactly one** row matches the charge service type (or exactly one planning row without `job_no` among duplicates).

**Multi-leg charges:** one charge can have multiple **Lifecycle Jobs** allocation rows (e.g. “Handling In” on Air legs 1–3). Planned roll-up uses `allocated_cost` / `allocated_revenue` per leg. Operational charge copy scales by `cost_allocation_percentage / 100`.

### 3.3 Lifecycle `actual_cost` / `actual_revenue`

- Fields on **Lifecycle Job** are **read-only**; synced on Special Project save via `sync_lifecycle_job_financials`.
- When `job_no` is set, totals come from the linked job charge stack (see Phase 1–2 below), resolving execution docs (Transport Job, Air/Sea Shipment, etc.) like dashboard milestones.
- Order/booking charge tables without `actual_cost` use **estimated** amounts as actual until invoice-driven actuals exist on the execution doc.
- Reports (cost vs revenue, profitability) read stored values on `tabLifecycle Job`.

### 3.4 `job_no` linking

- Resolves to operational refs for dashboard/milestones (e.g. Transport Order → Transport Job): `logistics.utils.special_project_internal_jobs`.
- **Create** from lifecycle copies matching programme charges onto the new order: `special_project_charge_copy.py` (filtered by allocation rows, scaled by allocation %).
- Orders created from Special Project are **standalone** mains linked via `project`; not internal jobs of each other by default.

### 3.5 Separate roll-up path (operational)

**Internal job → main service:** `internal_job_main_rollup` pushes planned/actual from internal job **charges** to **Internal Job Detail** on the main document. This does **not** update Special Project `lifecycle_jobs` financial columns.

---

## 4. Problem statement

| Issue | Description |
|-------|-------------|
| **Ambiguous programme charges** | Users expect Transport charges to “belong to the project.” With multiple Transport lifecycle rows, service type alone is insufficient; manual `lifecycle_job_row` feels redundant if `job_no` already links the leg. |
| **Two sources of truth** | Programme charges drive lifecycle **planned**; operational orders drive execution and invoicing. Numbers can diverge after orders exist. |
| **Lifecycle actuals unused** | Lifecycle `actual_*` are not filled from linked jobs; users may assume `job_no` drives financials. |
| **“One charge, all legs”** | Supported via **multi-tag charges** with allocation % summing to 100%; each leg receives its share in planned roll-up without double-counting. |
| **Trip vs lifecycle row** | One lifecycle row ≈ one programme job line (often one Transport Order), not strictly one Trip record. Trips/legs live inside Transport Order. |

---

## 5. Domain rules (agreed mental model)

1. **Multiple Transport lifecycle rows on one Special Project is normal** (e.g. inbound + return, two venues).
2. **One lifecycle Transport row** usually maps to **one main Transport Order** when created from the programme (not automatically one Trip entity).
3. **Whole project cost** = sum of **all** lifecycle legs (all modes) + programme-only work — **not** a single transport main absorbing every leg unless explicitly modeled (main + internal jobs).
4. **Trip / satellite transport** costs roll to a **main** only when the satellite is an **internal job** pointing at that main (`main_job`). Two lifecycle-created Transport Orders are two mains unless restructured.
5. **Programme-wide fees** (e.g. project DELIVERY, coordination) must be modeled explicitly: Special Project service lifecycle row, split across legs, or assigned to one owning leg — not left as Transport with no `lifecycle_job_row` when multiple Transport rows exist.

---

## 6. User scenarios (current product)

### 6.1 Single Transport leg

- One lifecycle row (Transport).
- Programme charges: Service Type Transport; `lifecycle_job_row` often auto-filled.
- Create → Transport Order → `job_no` set.
- **Planned** on lifecycle from programme charges; **actual** execution on order charges.

### 6.2 Two Transport legs (validation case)

- Two lifecycle rows, both Transport.
- Every Transport programme charge needs **Lifecycle Job** = row 1 or 2.
- DELIVERY for leg 1 only → Lifecycle Job = 1; blank → save error.
- Create one Transport Order per row.

### 6.3 Programme-wide fee

Do **not** leave Transport + empty Lifecycle Job when multiple Transport rows exist.

| Approach | Action |
|----------|--------|
| Overhead | Lifecycle row with Service Type **Special Project**; charge on that row. |
| Split | Multiple charge lines with amounts per leg and correct `lifecycle_job_row`. |
| Single leg owner | One charge, Lifecycle Job = chosen leg. |

### 6.4 Quote first, orders later

1. Lifecycle + programme charges from Sales Quote.
2. Assign `lifecycle_job_row` where needed; save for planned totals per row.
3. Create operational documents per row; charges may copy down.
4. Ops and billing work on **order** charges; programme tab may diverge unless kept in sync.

### 6.5 Checking leg performance (today)

- **Planned:** lifecycle row (from programme charges).
- **Actual execution:** Transport Order / Job charges and invoices.
- User may need **both** until execution-led roll-up is implemented.

---

## 7. Recommended target design (execution-led)

### 7.1 Principles

1. **Single source of truth for lifecycle financials after `job_no` exists:** operational document linked on the lifecycle row.
2. **No double roll-up:** do not sum programme charges **and** job charges into the same lifecycle `planned_*` / `actual_*` without clear phase rules.
3. **Project total = sum of lifecycle rows** (and programme-only rows), not one transport main swallowing all legs.
4. **Explicit shared costs** — never attribute 100% of one charge to every Transport lifecycle row.

### 7.2 Lifecycle row financials

| Field | Source (target) |
|-------|------------------|
| `planned_cost` / `planned_revenue` | **Primary:** sum of charge lines on doc in `job_no` (same rules as `calculate_internal_job_rollup_totals`: exclude disbursements). **Before `job_no`:** programme charges linked via `lifecycle_job_row` OR quote-only row (current behaviour). |
| `actual_cost` / `actual_revenue` | **Read-only;** from linked job charges (and invoice-driven actuals on those rows). |

### 7.3 Programme charges (`Special Project.charges`)

Choose one primary role (implement consistently):

| Option | Description |
|--------|-------------|
| **A. Quote / pre-create only** | Used until orders exist; no roll-up to lifecycle after `job_no` is set; lifecycle reads jobs only. |
| **B. Sync on create** | Copy to order on create (existing); lifecycle planned/actual follow order thereafter. |
| **C. Dual with flag** | Keep programme lines for budget variance vs execution (advanced; needs clear UI). |

Recommendation: **A or B** for v1; avoid **C** until needed.

### 7.4 Validation (target)

Replace or narrow current rule:

- **Remove** (or only apply pre-`job_no`): mandatory `lifecycle_job_row` when duplicate service type **if** lifecycle planned/actual come from `job_no` charges.
- **Add** as needed:
  - Programme charge with Transport service type and multiple Transport lifecycle rows **and** no `job_no` on any row → require `lifecycle_job_row` OR project-level charge type.
  - Orphan programme Transport charges after all matching rows have `job_no` → warn or block.

### 7.5 Internal jobs and “trip adds to main”

Within **one transport stack**:

- Main Transport Order (lifecycle `job_no`).
- Satellite Transport Orders / jobs as **internal** with `main_job` → roll up to main’s **Internal Job Detail** (existing hook).
- Lifecycle row for that leg should point at the **main** `job_no`; lifecycle actuals for the leg = main document charge totals **including** rolled-up internal jobs (define whether roll-up reads Internal Job Detail on main or recomputes from main + linked internal job docs).

Across **two lifecycle Transport rows:**

- Each row’s financials = its own `job_no` stack; **no** automatic cross-row roll-up.

### 7.6 Multimodal programmes

Lifecycle rows for Air, Sea, Customs, Special Project, etc. each follow the same pattern: financials from linked `job_no` when present; programme charges only for planning or non-operational rows.

---

## 8. What not to do

| Anti-pattern | Why |
|--------------|-----|
| One programme charge counts toward **all** Transport lifecycle rows | Double-counts planned/actual on project and reports. |
| Roll up programme charges **and** job charges to lifecycle without rules | Two truths; inflated totals. |
| Assume **1 lifecycle row = 1 Trip** in code | Lifecycle = programme job line; trips/legs are inside Transport Order. |
| Assume **one transport main = whole Special Project cost** | Ignores other modes and second main TO from second lifecycle row. |
| Manual lifecycle `actual_*` while syncing from jobs | Conflicting edits. |

---

## 9. Implementation outline (phased)

### Phase 0 — Now (no code)

- User training: set **Lifecycle Job** on programme charges when multiple rows share service type; use scenarios in §6.
- Document programme-wide fees per §6.3.

### Phase 1 — Lifecycle actuals from `job_no` — **Implemented**

- Module: [lifecycle_job_financial_rollup.py](lifecycle_job_financial_rollup.py) — `sync_lifecycle_job_financials`, `calculate_linked_job_stack_totals`.
- Wired from [special_project.py](doctype/special_project/special_project.py) `validate` (after `_sync_charges_with_parent_actuals`).
- Lifecycle `actual_*` read-only in [lifecycle_job.json](doctype/lifecycle_job/lifecycle_job.json).
- Tests: [test_lifecycle_job_financial_rollup.py](test_lifecycle_job_financial_rollup.py).

### Phase 2 — Lifecycle planned from jobs when `job_no` set — **Implemented**

- When `job_no` present and job doc active, `planned_*` and `actual_*` from job charge stack (main + internal satellites).
- Else programme charge roll-up via `_planned_totals_for_lifecycle_row`; `actual_*` = 0.
- `_validate_charge_lifecycle_links` relaxed when all duplicate-service-type lifecycle rows have `job_no`.
- `sync_lifecycle_job_planned_from_charges` delegates to `sync_lifecycle_job_financials`.

### Phase 3 — Programme charge UX

- Optional: Link field for lifecycle row instead of raw `idx`.
- Clear labels: “Budget line owner (required if multiple Transport jobs).”
- Dashboard copy: planned vs actual source.

### Phase 4 — Reports and variance

- Reports document whether totals use lifecycle stored fields or live job query.
- Optional budget vs execution variance (programme charge vs job).

---

## 10. Decisions (Phase 1–2 implementation)

| Question | Decision |
|----------|----------|
| Pre-`job_no` planned | Keep programme charge roll-up and validation when any matching lifecycle row lacks `job_no`. |
| Internal jobs | Main `job_no` document **plus** all non-cancelled internal jobs with `main_job` / `main_job_type` pointing at that main. |
| Disbursements | Excluded (same as `calculate_internal_job_rollup_totals`). |
| Project Order / Project Job | Included in internal-job-capable doctype list when they have `charges` and link fields. |
| Cancelled / missing `job_no` | Zero lifecycle financials for that row. |
| Exhibit | Not wired in this PR; use `sync_lifecycle_job_financials` in a follow-up. |
| Programme charges after `job_no` | Option A: lifecycle row does not include programme charges when job is linked. |

---

## 11. References (code)

| Area | Path |
|------|------|
| Financial roll-up (jobs + programme) | `logistics/special_projects/lifecycle_job_financial_rollup.py` |
| Planned roll-up + validation | `logistics/special_projects/lifecycle_job_planned_rollup.py` |
| Financial roll-up tests | `logistics/special_projects/test_lifecycle_job_financial_rollup.py` |
| Special Project validate | `logistics/special_projects/doctype/special_project/special_project.py` |
| Charge copy to orders | `logistics/special_projects/special_project_charge_copy.py` |
| Create booking/order from lifecycle | `logistics/special_projects/special_project_booking_creation.py` |
| Resolve `job_no` → operational ref | `logistics/utils/special_project_internal_jobs.py` |
| Internal job → main rollup | `logistics/utils/internal_job_main_rollup.py` |
| Tests (planned roll-up) | `logistics/special_projects/test_lifecycle_job_planned_rollup.py` |
| Migration note (financial columns) | `logistics/patches/v1_0_move_internal_job_details_to_lifecycle_jobs.py` |
| Charge field help | `special_project_charges.json` → `lifecycle_job_row` |

---

## 12. Summary (one paragraph)

**Today:** programme charges with `lifecycle_job_row` drive lifecycle **planned** totals; multiple Transport lifecycle rows require explicit charge attribution; **`job_no`** links ops and milestones but not lifecycle financials. **Target:** after orders exist, lifecycle **planned** and **actual** should come from charges on the document in **`job_no`** (plus internal-job roll-up within that stack); programme charges become quote/pre-create or one-time copy; project cost is the **sum of legs**, not one transport main. **Shared fees** need an explicit programme row, split, or single leg owner — never implicit “all Transport rows.”
