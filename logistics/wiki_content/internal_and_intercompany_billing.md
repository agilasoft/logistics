# Internal Billing and Intercompany Billing Between Logistics Modules

This document describes how **internal billing** (within the same company, across logistics modules) and **intercompany billing** (between companies in the same group) work in the Logistics app.

---

## 1. Unified Logic (Same for Internal and Intercompany)

**The same business logic applies to both internal billing and intercompany billing.** The only difference is *how* Internal Jobs are billed (Journal Entry vs Sales Invoice).

### 1.1 Main Job

- The **Main Job** is the single leg designated on the Sales Quote (one Main Job per quote).
- The Main Job **contains all charges to be billed** to the end customer.
- When creating the customer Sales Invoice, all billable charges come from the Main Job (whether consolidated on one document or split by service type per configuration).

### 1.2 Internal Jobs

- **Internal Jobs** are the other legs (non‑main) that provide specific services (e.g. Transport, Customs, Warehousing).
- Each Internal Job **contains only the charges specific to its respective service** (its own charge lines).
- **Revenue** of an Internal Job = **Cost of Main Job** allocated to that service (i.e. what the Main Job “pays” for this internal service). This keeps internal jobs at transfer price relative to the main job.
- **Cost** of an Internal Job depends on the charge:
  - **Supplier or actual cost** is billed with a **Purchase Invoice**.
  - **Internal tariff cost** (**Internal** and **Use Tariff in Cost** on the charge) is posted with **Post → Standard Costs** (§3.6). It is not a Purchase Invoice.

### 1.3 How Internal Jobs Are Billed: The Only Difference

| Scenario | Same company as Main Job (Internal billing) | Different company (Intercompany) |
|----------|---------------------------------------------|----------------------------------|
| **Mechanism** | **No Sales Invoice.** Internal billing is entered through **Journal Entry** (same operating company as Main Job). | **Sales Invoice.** The Internal Job’s operating company bills the **Main Job’s operating company** (billing company). |
| **Result** | Cost/revenue allocation within one company via JV. | Intercompany SI (from internal job’s company to billing company) + PI (billing company records purchase from internal job’s company). |

So: **Main Job = all customer charges; Internal Jobs = service-specific charges, revenue from cost of Main Job, cost from a supplier invoice or an internal-tariff standard-cost journal.** Same logic. Internal = JV (same company); Intercompany = SI to main job’s company.

---

## 2. Cross-Module Billing (Unified Layer)

Location: `logistics/billing/cross_module_billing.py`.

Under the **unified logic** (§1), the Main Job supplies all customer-facing charges; Internal Jobs supply only their service-specific charges (revenue from cost of Main Job; cost from a supplier invoice or an internal-tariff standard-cost journal, §3.6). This layer is used for:
- Creating **customer Sales Invoices** from a Sales Quote (consolidated or per leg).
- **Intercompany** invoice creation (same item extraction, different company/customer/supplier).

### 2.1 Job Types That Can Supply Invoice Items

- Transport Job  
- Air Shipment  
- Sea Shipment  
- Warehouse Job  
- Declaration  
- Declaration Order  

(Bookings like Air Booking and Sea Booking can act as **anchors** in routing; contributors are discovered via the registry below.)

### 2.2 Anchor–Contributor Registry

For each **anchor** DocType, the system knows which **contributor** jobs can be billed together (e.g. transport and warehousing under a shipment):

| Anchor | Contributors (DocType, link field to anchor) |
|--------|----------------------------------------------|
| Air Shipment | Transport Job (`air_shipment`), Warehouse Job (`air_shipment`) |
| Sea Shipment | Transport Job (`sea_shipment`), Warehouse Job (`sea_shipment`) |
| Transport Job | Warehouse Job (`transport_job`) |
| Air Booking | Transport Job (`air_shipment`) |
| Sea Booking | (none) |

So one “billing set” = **anchor job + its contributors**. Invoice items are built from all of them together (e.g. one customer invoice line per charge from the main job and from each contributor).

### 2.3 Key Functions

- **`get_invoice_items_from_job(job_type, job_name, customer)`**  
  Returns list of invoice line dicts (`item_code`, `item_name`, `qty`, `rate`, `uom`, `description`) from the job’s charges. Used for both customer invoicing and intercompany SI/PI.

- **`get_suggested_contributors(anchor_doctype, anchor_name, sales_quote)`**  
  Returns candidate contributing jobs for an anchor (for UI: “bill with contributors”).

- **`get_all_billing_jobs_from_sales_quote(sales_quote)`**  
  Returns all `(job_type, job_no)` to be billed from the quote: each routing leg’s anchor + each leg’s contributors. Used for intercompany (one SI/PI pair per job where company differs).

- **`get_billing_set_items(anchor_type, anchor_name, contributors, customer, description_prefix)`**  
  Builds the combined list of invoice items for one billing set (anchor + contributors). Used when creating Sales Invoices from the quote.

Charge sources per job type (conceptually):

- **Transport Job**: `charges` table (item, qty, rate / actual_revenue / estimated_revenue).  
- **Air Shipment**: `charges` table (item_code, quantity, rate / actual_revenue / total_amount).  
- **Sea Shipment**: `charges` table; customer filtering via `get_charge_bill_to_customers` for Sea.  
- **Warehouse Job**: `charges` table (item_code/item, quantity, rate, actual_revenue / estimated_revenue).  
- **Declaration / Declaration Order**: `charges` table (item_code, quantity, unit_rate/rate, actual_revenue / total_amount / estimated_revenue).

---

## 3. Internal Billing (Same Company, Between Modules)

When the Main Job and all Internal Jobs are in the **same company**, internal billing uses **Journal Entry** only (no Sales Invoice for internal legs).

### 3.1 Main Job Holds All Customer Charges

- The **Main Job** holds **all charges to be billed** to the end customer. Customer Sales Invoice is created from the Main Job (and its contributors if consolidated).
- **Separate Billings per Service Type** (Sales Quote) only affects how charges are *distributed* to documents when creating from the quote; the Main Job remains the one that carries the full billable amount to the customer when using a single consolidated invoice.

### 3.2 Internal Jobs: Service-Specific Charges, Revenue from Cost of Main Job

- **Internal Jobs** (non‑main legs) contain **only the charges specific to their respective services** (their own charge lines).
- **Revenue** of each Internal Job = **Cost of Main Job** allocated to that service (transfer price from main job to internal service).
- **Cost** of each Internal Job = a **supplier Purchase Invoice**, or an **internal tariff** posted as a standard-cost journal (§3.6).
- Internal Jobs are linked to the Main Job via **Main Job** reference.

### 3.3 No Invoice for Internal Billing — Journal Entry Only

- For **internal billing** (same operating company as Main Job), **no Sales Invoice** is raised for linked (internal) jobs.
- **One Journal Entry** per billing event (Sales Quote + optional trigger Sales Invoice) transfers each linked job’s **charge revenue** to the **Main Job as cost**.
- Per charge line with revenue and `item_code`:
  - **Dr** Item `expense_account` (from Item Defaults) on the **Main Job** (cost center / Job Number dimensions).
  - **Cr** Item `income_account` (from Item Defaults) on the **linked job** (cost center / Job Number dimensions).
- Linked-job **cost** is not posted in this JV. Supplier cost still uses a Purchase Invoice. An internal tariff cost uses **Post → Standard Costs** (§3.6). WIP/accrual reversal still runs separately when recognition is open on the linked job. Accrual recognition skips internal tariff cost lines, because that cost is the standard-cost journal rather than an accrual.
- When linked-service revenue is stored on **main job charge rows** (`charge_scope = Linked`), internal billing reads those rows and resolves the operational linked job via the `linked_service` link (e.g. Air Shipment for an air leg on a Sea main job).
- Each charge item must have **Item Defaults** (or Item Group Defaults) with both income and expense accounts for the company.

### 3.4 Consolidated vs Per-Product Customer Invoices

When creating **Sales Invoice from Sales Quote** (customer-facing):

- **Consolidated**: One Sales Invoice with items from the **Main Job** (and its contributors). All billable charges appear on this one customer invoice.
- **Per Product**: One Sales Invoice per routing leg; each leg’s anchor + contributors supply items. Main Job logic still applies: the leg that is Main Job carries the charges that are billed from that leg.

The **cross-module logic** (`get_billing_set_items`, `_get_contributors_for_leg`) is used to build invoice items from the Main Job and contributors.

### 3.5 Main Job company (no separate “billing company” field on jobs)

Internal and intercompany logic use **`company` on the Main Job** (via `main_job_type` / `main_job` on internal jobs), not a copied **Billing Company** field on each job. Same-company internal billing: internal job `company` equals Main Job `company`. Intercompany: they differ.

### 3.6 Internal tariff cost — standard cost journal

An internal job’s own cost is separate from the internal-billing journal in §3.3. When a charge’s cost is an **internal tariff**, **Post → Standard Costs** records it. The same action is used whether the job is same-company or intercompany. Code: `logistics/job_management/standard_cost_posting.py`.

A charge qualifies when all of the following are true:

- **Internal** (`cost_internal`) is ticked.
- **Use Tariff in Cost** (`use_tariff_in_cost`) is ticked.
- **Charge Type** is not **Disbursement**.

**Use Tariff in Cost** alone still goes to a Purchase Invoice. **Internal** alone does not create this journal.

**Where:** open the job and choose **Post → Standard Costs**.

| Document | Menu |
|----------|------|
| Air Shipment, Sea Shipment, Transport Job, Declaration, Special Project, MICE Project, Docket (MICE and Exhibits) | **Post → Standard Costs** |

Warehouse Job has its own **Post Standard Costs** action for warehouse standard unit cost. That path is not this internal-tariff journal.

**What one run does**

1. Reads unposted qualifying lines on the job’s `charges` table and, when present, `consolidation_charges`.
2. Takes the tariff amount in this order: **Estimated Cost**, then **Cost Base Amount**, then **Actual Cost** (or quantity × unit cost when those are empty).
3. Converts that amount into **company currency** with the buying rate when the charge cost currency differs. Posting date is today.
4. Submits **one Journal Entry** that covers every line that can be posted:
   - **Dr** Item **Standard Cost Account** (`custom_standard_cost_account`)
   - **Cr** Item **Applied Standard Cost Account** (`custom_applied_standard_cost_account`)
5. Copies the job’s company, branch, cost center, profit center, and job number onto the journal and onto each line. Each line also stores the charge item.
6. Stamps the charge: **Standard Cost Posted**, **Standard Cost Posted At**, and **Journal Entry** (`journal_entry_reference`).

Lines already marked **Standard Cost Posted** are left alone. Run the action again to post only the remaining lines; that creates a new journal.

**Before you post**

- The job has a **Company**.
- Each charge has an **Item**.
- That Item has both **Standard Cost Account** and **Applied Standard Cost Account**.
- You can write the job and create a Journal Entry.

If a line cannot be posted, the message names it (missing item, zero tariff cost, or missing Item accounts) and continues with the lines that can. If none can be posted, the message is **No internal tariff costs to post.**

**What this replaces**

- **Create Purchase Invoice** omits these lines, including internal-tariff rows on a consolidation when that consolidation’s purchase invoice is built.
- Job readiness treats an unposted internal tariff cost as a missing **submitted standard-cost journal**, not a missing Purchase Invoice. A submitted journal on **Journal Entry** satisfies that check.
- **Accrual** recognition skips these lines. WIP recognition is unchanged.

---

## 4. Intercompany Billing (Between Companies)

When an **Internal Job**’s **operating company** (job’s company) is **different** from the **Main Job’s operating company** (billing company), that Internal Job is **billed using Sales Invoice** to the Main Job’s operating company. The same logic applies: Main Job holds all customer charges; Internal Jobs hold service-specific charges; revenue = cost of Main Job (allocated). The “billing” of the Internal Job to the Main Job’s company is done via **intercompany Sales Invoice** (and corresponding Purchase Invoice). The operating company’s own **internal tariff cost** is still the standard-cost journal in §3.6, posted in the operating company. That journal is not the intercompany Purchase Invoice.

Location: `logistics/intercompany/intercompany_invoice.py` and Intercompany Settings.

### 4.1 Internal Job Billed to Main Job’s Company via Sales Invoice

- **Billing company** = Main Job’s operating company (the one that invoices the end customer).
- **Operating company** = the company that owns the Internal Job (or any non‑main job).
- When **operating company ≠ billing company**, the Internal Job is **billed using Sales Invoice**: the operating company raises a Sales Invoice to the **Main Job’s operating company** (recorded as internal customer). The billing company records a Purchase Invoice from the operating company (internal supplier).

**Summary:** Intercompany job = billed using Sales Invoice, billed to Main Job’s operating company.

### 4.2 When Intercompany Invoices Are Created

- **Automatic**: On **Sales Invoice submit**, if the Sales Invoice is linked to a **Sales Quote** (`quotation_no`) and Intercompany Settings has **Enable Intercompany Invoicing** checked, the app calls `create_intercompany_invoices_for_quote`. For every internal job from that quote where `job.company` ≠ **Main Job `company`**, it creates one intercompany SI (operating company → Main Job company) and one PI (Main Job company ← operating company).
- **Manual**: User can run **Intercompany Transactions** from the UI (e.g. on Air Shipment, Sea Shipment, Declaration). That calls the same `create_intercompany_invoices_for_quote` with the sales quote name (Main Job company is resolved in code).

### 4.3 Job Set Considered for Intercompany

- All jobs that should be billed from the quote are taken from **`get_all_billing_jobs_from_sales_quote(sales_quote)`**: each routing leg’s anchor + each leg’s contributors.
- Only jobs whose **DocType** is in **INTERCOMPANY_JOB_TYPES** are processed: Transport Job, Air Shipment, Sea Shipment, Warehouse Job, Declaration, Declaration Order.
- For each such job (that resolves as an internal job with a Main Job link):
  - **operating_company** = `job.company`.
  - **main_job_company** = `company` on the linked Main Job document.
  - If `operating_company` is empty or equals **main_job_company**, the job is **skipped** (same-company leg).
  - If `operating_company != main_job_company`, an **Intercompany Relationship** must exist for **(Billing Company = main_job_company, Operating Company = operating_company)** with **Internal Customer** (in operating company’s books) and **Internal Supplier** (in Main Job company’s books).

### 4.4 Intercompany Relationship

(**Intercompany Settings** > Intercompany Relationships; child **Intercompany Relationship**.)

- **Billing Company**: Company that invoices the end customer (quote’s company).
- **Operating Company**: Company that owns the job and performs the service.
- **Internal Customer**: In the **operating** company’s books, the billing company is represented as this Customer (used as `customer` on the intercompany **Sales Invoice**).
- **Internal Supplier**: In the **billing** company’s books, the operating company is represented as this Supplier (used as `supplier` on the intercompany **Purchase Invoice**).

So: Operating company sells to “Internal Customer” (= billing company), and Billing company buys from “Internal Supplier” (= operating company).

### 4.5 One SI/PI Pair per Intercompany Job

For each job with `company != main_job_company` (Main Job’s `company`) and a valid relationship:

1. **Items** are taken from **`get_invoice_items_from_job(job_type, job_no, customer_for_sea=end_customer)`** (implemented via cross_module_billing so amounts match what would be on the customer invoice for that leg).
2. **Intercompany Sales Invoice**:  
   - Company = operating_company, Customer = internal_customer, items from the job, linked to Sales Quote and trigger SI.
3. **Intercompany Purchase Invoice**:  
   - Company = main_job_company, Supplier = internal_supplier, same items/rates.

Each such pair is logged in **Intercompany Invoice Log** (sales_quote, job_type, job_no, **main_job_company**, operating_company, status, intercompany_sales_invoice, intercompany_purchase_invoice). Duplicate creation for the same quote+job is avoided by checking for an existing “Created” log.

### 4.6 Where the Main Job company comes from

- Resolved in code: **`get_main_job_company(main_job_type, main_job)`** reads **`company`** on the Main Job document linked from each internal job (`resolve_internal_job_main_job`). No per-job **Billing Company** field is used.

### 4.7 Operating company’s own cost

The intercompany Sales Invoice / Purchase Invoice pair is the transfer between companies. It does not post the operating company’s internal tariff.

On the operating company’s job, **Post → Standard Costs** (§3.6) posts qualifying lines in that company. Supplier costs on the same job still use **Create Purchase Invoice**. The billing company’s intercompany Purchase Invoice remains the purchase of the internal service from the internal supplier.

---

## 5. Summary Table (Unified Logic)

**Same logic for both:** Main Job = all charges to be billed; Internal Jobs = service-specific charges, revenue = cost of Main Job (allocated). Internal tariff cost is a standard-cost journal in the job’s own company; other cost is a supplier Purchase Invoice.

| Aspect | Internal Billing | Intercompany Billing |
|--------|------------------|----------------------|
| **Companies** | Same company (Main Job and Internal Jobs in one company) | Internal Job’s company ≠ Main Job’s company (billing company) |
| **How Internal Jobs are billed** | **No Sales Invoice.** Internal billing entered through **Journal Entry** (same operating company as Main Job). | **Sales Invoice.** Internal Job’s operating company bills **Main Job’s operating company** (billing company); corresponding PI in billing company. |
| **Main Job** | Holds all customer charges; customer SI from Main Job. | Same; billing company = Main Job’s operating company. |
| **Internal Job revenue** | Service-specific charges only; revenue = cost of Main Job (allocated); billed via JV. | Same logic; billed using Sales Invoice to Main Job’s company (SI + PI). |
| **Internal tariff cost** | **Post → Standard Costs** on the job. Dr Item **Standard Cost Account**, Cr Item **Applied Standard Cost Account**. Not a Purchase Invoice. | Same journal, in the **operating** company. The intercompany SI/PI pair is still the transfer to the Main Job’s company. |
| **Other cost** | Supplier Purchase Invoice on the job. | Supplier Purchase Invoice stays on the operating job. It is separate from the intercompany Purchase Invoice. |
| **Configuration** | Sales Quote (Main Job, routing legs); same company. Item **Standard Cost Account** and **Applied Standard Cost Account** for internal tariff lines. | Intercompany Settings (enable, Intercompany Relationship: internal_customer / internal_supplier). Same Item accounts on the operating company job. |
| **Trigger** | Create customer SI from Sales Quote; internal allocation via Journal Entry. Standard costs: **Post → Standard Costs**. | SI submit (if from quote) or “Intercompany Transactions” button → create intercompany SI/PI per internal job where job `company` ≠ Main Job `company`. Standard costs: **Post → Standard Costs** on the operating job. |

---

## 6. Related Code and DocTypes

- **Cross-module billing**: `logistics/billing/cross_module_billing.py` (BILLING_CONTRIBUTOR_QUERIES, BILLING_JOB_TYPES, get_invoice_items_from_job, get_all_billing_jobs_from_sales_quote, get_billing_set_items).
- **Internal tariff standard cost**: `logistics/job_management/standard_cost_posting.py` (`is_internal_tariff_cost_charge`, `post_internal_tariff_standard_costs`). Purchase Invoice creation skips those rows in `invoice_integration/purchase_invoice_api.py`. Job readiness checks the submitted journal in `job_management/job_readiness.py`. Accrual recognition skips them in `job_management/recognition_engine.py`.
- **Intercompany**: `logistics/intercompany/intercompany_invoice.py` (create_intercompany_invoices_for_quote, _create_intercompany_pair, get_relationship); `invoice_integration/invoice_hooks.py` (on_sales_invoice_submit).
- **Sales Quote invoice creation**: `pricing_center/doctype/sales_quote/sales_quote.py` (_create_consolidated_invoice, _create_separate_invoices_per_leg, _get_contributors_for_leg).
- **Module integration**: `utils/module_integration.py` (propagate `sales_quote` from linked freight; no job-level billing company field).
- **DocTypes**: Intercompany Settings, Intercompany Relationship (child row **Billing Company** = customer-invoicing entity, must match Main Job `company` for the pair), Intercompany Invoice Log (**main_job_company**); Sales Quote (routing_legs, Main Job, Separate Billings); job DocTypes with Internal Job / Main Job links.

---


<!-- wiki-field-reference:start -->

## Complete field reference

_Billing uses fields on customer/supplier invoices and on logistics jobs/shipments. Full schemas on:_

- [Sales Quote](welcome/sales-quote), [Change Request](welcome/change-request)
- [Air Shipment](welcome/air-shipment), [Sea Shipment](welcome/sea-shipment), [Transport Job](welcome/transport-job), [Warehouse Job](welcome/warehouse-job), [Declaration](welcome/declaration)
- [Intercompany Module](welcome/intercompany-module) _(overview)_

<!-- wiki-field-reference:end -->

## 7. Related Documentation

- [Sales Quote – Separate Billings and Internal Job](welcome/sales-quote-separate-billings-and-internal-job) – Charge allocation and Internal Job rules.
- [Intercompany Module](welcome/intercompany-module) – Intercompany settings and invoice log.
- [Job Management Module](welcome/job-management-module) – Accrual recognition skips internal tariff cost lines.
- [Sales Quote](welcome/sales-quote) – Routing, Main Job, and billing modes.
