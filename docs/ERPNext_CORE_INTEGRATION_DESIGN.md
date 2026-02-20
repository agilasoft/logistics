# Logistics ↔ ERPNext Core Integration: Current Status & Proposed Design

**Date:** February 14, 2026  
**Scope:** Cost and revenue flows from logistics jobs/shipments to ERPNext Purchase and Sales modules; invoicing and payment monitoring  
**Purpose:** Document current state and propose a unified design for cost → Purchase Invoice (or PR/PO) and revenue → Sales Invoice, plus full invoicing/payment status tracking

---

## 1. Executive Summary

| Flow | Current State | Proposed |
|------|---------------|----------|
| **Revenue → Sales Invoice** | ✅ Implemented for Transport Job, Air Shipment, Sea Shipment, Warehouse Job, Declaration, Periodic Billing | Enhance with reference linkage and monitoring fields |
| **Costs → Purchase Invoice** | ❌ Not implemented | Add create_purchase_invoice from job/shipment costs |
| **Costs → Purchase Request/Order** | ❌ Not implemented | Add optional flow via module settings |
| **Fully Invoiced / Fully Paid** | ⚠️ Partial (billing_status only) | Add standardized monitoring fields and dates |

---

## 2. Current Status

### 2.1 Revenue → Sales Invoice (Implemented)

| Source DocType | Method | Link Field | Notes |
|----------------|--------|-------------|-------|
| **Transport Job** | `create_sales_invoice(job_name)` | `sales_invoice` | Charges → SI items; auto-trigger on status=Completed |
| **Air Shipment** | `create_sales_invoice()` | `sales_invoice` | Charges → SI items; filter by bill_to, invoice_type |
| **Sea Shipment** | `create_sales_invoice(shipment_name, posting_date, customer, …)` | — | Charges → SI items; filter by bill_to, invoice_type |
| **Warehouse Job** | `create_sales_invoice_from_job()` | — | Charges → SI items; via ops.py |
| **Declaration** | `create_sales_invoice(declaration_name)` | — | Charges → SI items |
| **Periodic Billing** | `create_sales_invoice_from_periodic_billing()` | `sales_invoice` | PB charges → SI items |

**Gaps:**
- Sea Shipment and some others do not consistently set `sales_invoice` back-reference on the source document.
- Sales Invoice Item does **not** receive `reference_doctype` / `reference_name` when created from jobs — the Recognition Engine’s `calculate_actual_revenue_as_of()` expects these on SI Item but they are not populated.
- No standardized “fully invoiced” or “fully paid” flags or dates at job/shipment level.

### 2.2 Costs → Purchase Invoice (Not Implemented)

| Aspect | Status |
|--------|--------|
| Create Purchase Invoice from job/shipment costs | ❌ No function exists |
| Link Purchase Invoice back to job/shipment | ❌ No `purchase_invoice` field on jobs/shipments |
| Purchase Invoice Item reference to job | Recognition Engine expects `reference_doctype` / `reference_name` on PI Item; standard PI Item has no such fields |

**Recognition Engine (existing):**
- `calculate_actual_costs_as_of()` queries `Purchase Invoice Item` with `reference_doctype` = job type and `reference_name` = job name.
- These fields are not present on standard ERPNext Purchase Invoice Item.
- Cost recognition today is via **Journal Entry** (accrual) only, not via Purchase Invoice.

### 2.3 Costs → Purchase Request / Purchase Order (Not Implemented)

| Aspect | Status |
|--------|--------|
| Create Purchase Request from costs | ❌ Not implemented |
| Create Purchase Order from costs | ❌ Not implemented |
| Module setting “costs require purchasing process” | ❌ No such setting exists |

### 2.4 Charge Schemas (Cost vs Revenue)

| DocType | Revenue Fields | Cost Fields | Supplier |
|---------|----------------|-------------|----------|
| **Transport Job Charges** | `unit_rate`, `estimated_revenue` | `unit_cost`, `estimated_cost` | — |
| **Air Shipment Charges** | `estimated_revenue`, `total_amount` | `estimated_cost` | — |
| **Sea Freight Charges** | `selling_amount`, `bill_to` | `buying_amount`, `pay_to` (Supplier) | `pay_to` |
| **Warehouse Job Charges** | `rate`, `total` | `standard_unit_cost`, `total_standard_cost` | — |
| **Declaration Charges** | `unit_rate`, `estimated_revenue` | `unit_cost`, `estimated_cost` | — |

- **Sea Freight Charges** is the only schema with an explicit `pay_to` (Supplier) link.
- **Warehouse Job Charges**: cost flows via Journal Entry (`post_standard_costs`) when standard costing is enabled, not via Purchase Invoice.

### 2.5 Invoicing and Payment Monitoring

| DocType | Fields | Values |
|---------|--------|--------|
| **Air Shipment** | `billing_status`, `billing_amount`, `billing_date`, `sales_invoice` | Not Billed, Pending, Billed, Partially Billed, Overdue, Cancelled |
| **Sea Shipment** | `billing_status` | Similar |
| **Air Shipment Charges** | `billing_status`, `payment_status` | Pending, Billed, Paid, Overdue, Cancelled |
| **Air/Sea Consolidation Charges** | `billing_status`, `payment_status` | Same |
| **Declaration** | `payment_status` | No `sales_invoice` link; no billing_status |
| **Transport Job** | `sales_invoice` only | No billing_status |
| **Warehouse Job** | — | No `sales_invoice`, no billing_status; billing via Periodic Billing |

**Missing:**
- `fully_invoiced` (Check)
- `fully_paid` (Check)
- `date_fully_invoiced` (Date)
- `date_fully_paid` (Date)
- Lifecycle dates: `date_sales_invoice_requested`, `date_sales_invoice_submitted`, `date_purchase_invoice_requested`, `date_purchase_invoice_submitted`, `date_costs_fully_paid`
- Consistent `purchase_invoice` link for cost tracking

### 2.6 Customs Module

| Aspect | Status |
|--------|--------|
| **Declaration** create_sales_invoice | ✅ Implemented; uses charges or default customs item |
| **Declaration** sales_invoice link | ❌ Not set on Declaration after SI creation |
| **Declaration** costs → Purchase Invoice | ❌ Not implemented |
| **Declaration Charges** | `estimated_revenue`, `estimated_cost`, `unit_rate`, `unit_cost` (same structure as Transport) |
| **Customs Settings** | Company-specific; `default_revenue_calculation_method`, `default_cost_calculation_method`, `enable_auto_calculation`; no billing/invoicing purchase settings |

### 2.7 Warehousing Module

| Aspect | Status |
|--------|--------|
| **Warehouse Job** create_sales_invoice | ✅ Via `create_sales_invoice_from_job()` in ops.py |
| **Warehouse Job** sales_invoice link | ❌ Not set on Warehouse Job; SI may have `warehouse_job` custom field |
| **Warehouse Job** costs → Purchase Invoice | ❌ Not implemented; costs posted via Journal Entry (`post_standard_costs`) when standard costing enabled |
| **Warehouse Job Charges** | `rate`, `total` (revenue); `standard_unit_cost`, `total_standard_cost` (cost) |
| **Periodic Billing** | Has `sales_invoice`; used for recurring warehouse billing |
| **Warehouse Settings** | Company-specific; `enable_volume_billing`, `vas_total_sum_type`; `enable_standard_costing`, `post_gl_entry_for_standard_costing`; no create_purchase_invoice settings |

---

## 3. Proposed Design

### 3.1 Standard Fields for Job/Shipment DocTypes

Add to **Transport Job, Air Shipment, Sea Shipment, Warehouse Job, Declaration** (and optionally General Job):

| Field | Type | Label | Description |
|-------|------|-------|-------------|
| `sales_invoice` | Link → Sales Invoice | Sales Invoice | Already exists on some; add where missing |
| `purchase_invoice` | Link → Purchase Invoice | Purchase Invoice | Primary PI for costs (or first if multiple) |
| `fully_invoiced` | Check | Fully Invoiced | Revenue fully billed |
| `date_fully_invoiced` | Date | Date Fully Invoiced | When revenue was fully invoiced |
| `fully_paid` | Check | Fully Paid | All receivables paid |
| `date_fully_paid` | Date | Date Fully Paid | When fully paid |
| `date_sales_invoice_requested` | Date | SI Requested | When Sales Invoice was created (requested) |
| `date_sales_invoice_submitted` | Date | SI Submitted | When Sales Invoice was submitted/posted |
| `date_purchase_invoice_requested` | Date | PI Requested | When Purchase Invoice (or PR) was created |
| `date_purchase_invoice_submitted` | Date | PI Submitted | When Purchase Invoice was submitted/posted |
| `date_costs_fully_paid` | Date | Costs Paid | When linked Purchase Invoice(s) fully paid |
| `costs_fully_paid` | Check | Costs Fully Paid | All cost payables settled |

**Child / charge-level (where applicable):**
- `purchase_invoice` on charge rows for cost items that have been invoiced by supplier.

### 3.2 Cost Flow: Create Purchase Invoice

**New function:** `create_purchase_invoice(job_type, job_name, supplier=None, posting_date=None)`

**Logic:**
1. Load job (Transport Job, Air Shipment, Sea Shipment, Warehouse Job, Declaration).
2. Filter charges with cost amount > 0 and (where applicable) `pay_to` (supplier).
3. For each charge:
   - If `pay_to` exists → use as supplier for that line (or group by supplier).
   - If no supplier → use default supplier from module settings or company.
4. Create Purchase Invoice with:
   - `supplier` from charge or default
   - Items from charges (item_code, qty, rate = cost amount)
   - `reference_type` = job type, `reference_name` = job name (on PI header)
5. Add custom fields to **Purchase Invoice** and **Purchase Invoice Item**:
   - PI: `reference_doctype`, `reference_name` (or use standard `reference_type`/`reference_name` if available)
   - PI Item: `reference_doctype`, `reference_name` (for Recognition Engine)
6. Set `purchase_invoice` on job.
7. Support multiple PIs per job when costs are split by supplier.

**Module setting (per module):**
- `require_purchasing_process` (Check): If enabled, costs must go through Purchase Request → Purchase Order → Purchase Invoice instead of direct PI.

### 3.3 Cost Flow: Purchase Request / Purchase Order (Optional)

When `require_purchasing_process` is enabled:

1. **Create Purchase Request** from job costs:
   - One PR per job (or per supplier) with items from charges.
   - Link PR to job via `reference_doctype` / `reference_name`.

2. **Create Purchase Order** from PR (standard ERPNext flow).

3. **Create Purchase Invoice** from PO (standard ERPNext flow).

4. On PI creation/submit:
   - Set `purchase_invoice` on job (or append to list if multiple).
   - Update `fully_invoiced` for costs when all cost charges are covered by PI(s).

### 3.4 Revenue Flow: Enhancements

1. **Set `reference_doctype` / `reference_name` on Sales Invoice Item** when creating SI from job:
   - Ensures Recognition Engine’s `calculate_actual_revenue_as_of()` works.
   - Add custom fields to Sales Invoice Item if not present.

2. **Set `sales_invoice` on source** for all modules (Sea Shipment, Declaration, Warehouse Job where missing).

3. **Update `fully_invoiced` and `date_fully_invoiced`**:
   - On SI submit: compare sum of SI amounts vs total revenue from charges.
   - If equal (within tolerance) → `fully_invoiced` = 1, `date_fully_invoiced` = SI posting_date.

### 3.5 Invoice Lifecycle Monitoring (Requested → Submitted → Paid)

Monitor Sales Invoice and Purchase Invoice through their full lifecycle on the linked job/shipment.

#### 3.5.1 Sales Invoice Lifecycle

| Stage | Trigger | Fields Updated |
|-------|---------|----------------|
| **Requested** | SI created (insert) from job | `date_sales_invoice_requested` = today; `sales_invoice` set when SI submitted |
| **Submitted/Posted** | SI submitted (docstatus = 1) | `sales_invoice` = SI name; `date_sales_invoice_submitted` = SI posting_date; `fully_invoiced`, `date_fully_invoiced` if full amount |
| **Paid** | SI outstanding_amount = 0 (via Payment Entry) | `fully_paid` = 1; `date_fully_paid` = date of final payment |

**Implementation:** Hooks on Sales Invoice `on_submit`, `on_update_after_submit` (for payment); or scheduled job to sync `outstanding_amount`.

#### 3.5.2 Purchase Invoice Lifecycle

| Stage | Trigger | Fields Updated |
|-------|---------|----------------|
| **Requested** | PI created (direct flow), or Purchase Request created (if PR→PO→PI flow) | `date_purchase_invoice_requested` = creation date of PI or PR |
| **Submitted/Posted** | PI submitted (docstatus = 1) | `purchase_invoice` = PI name; `date_purchase_invoice_submitted` = PI posting_date |
| **Paid** | PI outstanding_amount = 0 (via Payment Entry) | `costs_fully_paid` = 1; `date_costs_fully_paid` = date of final payment |

**Implementation:** Hooks on Purchase Invoice `on_submit`; Payment Entry or scheduled job for paid status.

#### 3.5.3 Summary: Invoice Status Fields

| Field | Revenue (Sales) | Cost (Purchase) |
|-------|-----------------|-----------------|
| Requested | `date_sales_invoice_requested` | `date_purchase_invoice_requested` |
| Submitted/Posted | `date_sales_invoice_submitted` (= `date_fully_invoiced` when full) | `date_purchase_invoice_submitted` |
| Paid | `date_fully_paid` | `date_costs_fully_paid` |

### 3.6 Module Settings

#### 3.6.1 Current Settings (Relevant to Billing/Invoicing)

| Module | Settings DocType | Existing Billing/Invoicing Settings |
|--------|------------------|-------------------------------------|
| **Transport** | Transport Settings | `enable_auto_billing` — auto-create SI when job status = Completed |
| **Sea Freight** | Sea Freight Settings | — |
| **Air Freight** | Air Freight Settings | — |
| **Customs** | Customs Settings | `default_revenue_calculation_method`, `default_cost_calculation_method`, `enable_auto_calculation`, `round_off_precision` |
| **Warehousing** | Warehouse Settings | `enable_volume_billing`, `vas_total_sum_type`; `enable_standard_costing`, `post_gl_entry_for_standard_costing` |
| **Logistics** | Logistics Settings | `default_customs_item` (used when Declaration has no charge items) |

#### 3.6.2 Proposed New Settings (Per Module)

Add to **Transport Settings, Sea Freight Settings, Air Freight Settings, Customs Settings, Warehouse Settings** (and optionally Logistics Settings):

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `create_purchase_invoice_from_costs` | Check | 0 | Allow creating PI from job/shipment costs |
| `require_purchasing_process` | Check | 0 | If enabled, use PR → PO → PI instead of direct PI |
| `default_cost_supplier` | Link → Supplier | — | Default supplier when charge has no pay_to |
| `auto_create_purchase_invoice_on_complete` | Check | 0 | Auto-create PI when job/shipment status = Completed |

**Customs Settings** — add under a new "Billing & Cost Integration" section:
- Same proposed settings as above.
- `default_customs_item` remains in Logistics Settings (or optionally move to Customs Settings).

**Warehouse Settings** — add under Billing tab:
- Same proposed settings.
- Note: Warehouse costs today use standard costing (Journal Entry). `create_purchase_invoice_from_costs` would apply when costs are from external suppliers (e.g. subcontracted handling), not internal standard cost.

### 3.7 Invoice Cancellation

When a **Sales Invoice** or **Purchase Invoice** is cancelled, update the linked job/shipment and related records accordingly.

#### 3.7.1 Sales Invoice Cancelled

| Action | Target | Field / Detail |
|--------|--------|----------------|
| Clear link | Job/Shipment (Transport Job, Air Shipment, Sea Shipment, Warehouse Job, Declaration) | Set `sales_invoice` = None where it matches the cancelled SI |
| Reset invoicing status | Job/Shipment | Set `fully_invoiced` = 0, `date_fully_invoiced` = None |
| Reset payment status | Job/Shipment | Set `fully_paid` = 0, `date_fully_paid` = None |
| Reset lifecycle dates | Job/Shipment | Set `date_sales_invoice_requested` = None, `date_sales_invoice_submitted` = None (or recalc from remaining SIs) |
| Update billing status | Air Shipment, Sea Shipment | Recalculate `billing_status` (e.g. → Not Billed, Pending, or Partially Billed if other SIs exist) |
| Update billing amount/date | Air Shipment | Recalculate `billing_amount`, `billing_date` from remaining linked SIs |
| Update charge-level status | Air Shipment Charges, etc. | Reset `billing_status`, `payment_status` on charges that were linked to this SI |

**Implementation:** Hook on Sales Invoice `on_cancel` — resolve linked jobs via `reference_doctype`/`reference_name` on SI Item, or via `sales_invoice` field on jobs that point to this SI.

#### 3.7.2 Purchase Invoice Cancelled

| Action | Target | Field / Detail |
|--------|--------|----------------|
| Clear link | Job/Shipment | Set `purchase_invoice` = None where it matches the cancelled PI |
| Reset cost invoicing | Job/Shipment | Set `costs_fully_paid` = 0; clear `date_costs_fully_paid` |
| Reset lifecycle dates | Job/Shipment | Set `date_purchase_invoice_requested` = None, `date_purchase_invoice_submitted` = None (or recalc from remaining PIs) |
| Clear charge-level link | Charge rows (Transport Job Charges, Sea Freight Charges, etc.) | Set `purchase_invoice` = None on rows that referenced this PI |

**Implementation:** Hook on Purchase Invoice `on_cancel` — resolve linked jobs via `reference_doctype`/`reference_name` on PI header or PI Item.

#### 3.7.3 Multiple Invoices

When a job has multiple Sales Invoices or Purchase Invoices (e.g. partial billing):
- On cancel of one SI/PI: clear only that reference; recalculate aggregate status from remaining linked invoices.
- If the cancelled invoice was the sole one → full reset as above.
- Consider `sales_invoices` / `purchase_invoices` (Table or CSV) if multiple links are supported; remove the cancelled one from the list.

---

## 4. Data Model Summary

### 4.1 Job/Shipment Level

```
Transport Job / Air Shipment / Sea Shipment / Warehouse Job / Declaration
├── sales_invoice (Link)
├── purchase_invoice (Link) — NEW
├── fully_invoiced (Check) — NEW
├── date_fully_invoiced (Date) — NEW
├── fully_paid (Check) — NEW
├── date_fully_paid (Date) — NEW
├── date_sales_invoice_requested (Date) — NEW
├── date_sales_invoice_submitted (Date) — NEW
├── date_purchase_invoice_requested (Date) — NEW
├── date_purchase_invoice_submitted (Date) — NEW
├── costs_fully_paid (Check) — NEW
└── date_costs_fully_paid (Date) — NEW
```

### 4.2 Charge Level (Cost Charges)

```
Transport Job Charges / Air Shipment Charges / Sea Freight Charges / Declaration Charges
├── pay_to (Link → Supplier) — Sea Freight has; add to others as needed
├── estimated_cost / buying_amount / unit_cost
└── purchase_invoice (Link) — NEW, optional per-row

Warehouse Job Charges
├── rate, total (revenue)
├── standard_unit_cost, total_standard_cost (cost — posted via Journal Entry when standard costing enabled)
└── pay_to (Link → Supplier) — NEW, for external/subcontracted costs; purchase_invoice (Link) — NEW
```

### 4.3 Custom Fields on ERPNext Core

| DocType | Field | Type | Purpose |
|---------|-------|------|---------|
| Sales Invoice Item | reference_doctype | Link → DocType | Link to source job |
| Sales Invoice Item | reference_name | Dynamic Link | Job/shipment name |
| Purchase Invoice | reference_doctype | Link → DocType | Link to source job |
| Purchase Invoice | reference_name | Dynamic Link | Job/shipment name |
| Purchase Invoice Item | reference_doctype | Link → DocType | For Recognition Engine |
| Purchase Invoice Item | reference_name | Dynamic Link | Job/shipment name |

---

## 5. Implementation Phases

| Phase | Scope | Effort |
|-------|-------|--------|
| **Phase 1** | Add standard monitoring fields (`fully_invoiced`, `fully_paid`, `date_fully_invoiced`, `date_fully_paid`) to job/shipment doctypes | Low |
| **Phase 2** | Add custom fields to Sales Invoice Item for `reference_doctype` / `reference_name`; populate when creating SI from job | Low |
| **Phase 3** | Implement `create_purchase_invoice()` for Transport Job, Air Shipment, Sea Shipment, Warehouse Job, Declaration; add `purchase_invoice` link | Medium |
| **Phase 4** | Add custom fields to Purchase Invoice / Purchase Invoice Item; wire Recognition Engine | Low |
| **Phase 5** | Add module settings; implement `require_purchasing_process` (PR → PO → PI) | Medium |
| **Phase 6** | Hooks to update lifecycle fields (requested, submitted, paid) and `fully_invoiced`, `fully_paid` from SI/PI submit and Payment Entry | Medium |
| **Phase 7** | Hooks on Sales Invoice and Purchase Invoice `on_cancel` to clear links and reset statuses on linked jobs/shipments | Medium |

---

## 6. Reference: Existing Code Locations

| Component | Path |
|-----------|------|
| Transport Job create_sales_invoice | `logistics/transport/doctype/transport_job/transport_job.py` |
| Air Shipment create_sales_invoice | `logistics/air_freight/doctype/air_shipment/air_shipment.py` |
| Sea Shipment create_sales_invoice | `logistics/sea_freight/doctype/sea_shipment/sea_shipment.py` |
| Warehouse Job create_sales_invoice | `logistics/warehousing/api_parts/ops.py` |
| Declaration create_sales_invoice | `logistics/customs/doctype/declaration/declaration.py` |
| Recognition Engine (revenue/cost) | `logistics/job_management/recognition_engine.py` |
| Billing Status Reports | `logistics/air_freight/report/billing_status_report/`, `logistics/sea_freight/report/sea_freight_billing_status_report/` |
| Customs Settings | `logistics/customs/doctype/customs_settings/customs_settings.json` |
| Warehouse Settings | `logistics/warehousing/doctype/warehouse_settings/warehouse_settings.json` |
| Warehouse Job post_standard_costs | `logistics/warehousing/doctype/warehouse_job/warehouse_job.py` |
| Sales Invoice hooks (Transport) | `logistics/transport/sales_invoice_hooks.py` — validate only; add `on_cancel` in hooks.py |

---

## 7. Related Documents

- [ACCOUNTS_TAB_STANDARDIZATION_REPORT.md](./ACCOUNTS_TAB_STANDARDIZATION_REPORT.md) — Accounts fields on doctypes
- [LOGISTICS_MODULE_INTEGRATION_DESIGN.md](./LOGISTICS_MODULE_INTEGRATION_DESIGN.md) — Cross-module integration
- [SPECIAL_PROJECTS_MODULE_DESIGN.md](./SPECIAL_PROJECTS_MODULE_DESIGN.md) — Project costing and billing

---

*Document generated from codebase analysis.*
