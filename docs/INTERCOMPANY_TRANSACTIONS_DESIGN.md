# Intercompany Transactions Design

This document describes the design for **intercompany invoicing** when a forwarding company (billing company) creates a quotation that includes services operated by other group companies (e.g. Warehouse by Company B, Transport by Company C, Air by Company A). The customer is billed once by the billing company; operating companies must bill the billing company based on tariff and/or cost used in the quotation.

---

## 1. Scenario

| Role | Company | Service in quote | Bills |
|------|---------|------------------|--------|
| **Forwarder / Billing company** | Company A | Air (operates), overall quote owner | **Customer** (one Sales Invoice with all charges: Warehouse + Transport + Air) |
| **Warehouse operator** | Company B | Warehouse | **Company A** (intercompany invoice) |
| **Transport operator** | Company C | Transport | **Company A** (intercompany invoice) |
| **Air operator** | Company A | Air | — (same company; no intercompany) |

**Goal:** Automate creation of intercompany invoices so that Company B and Company C bill Company A using the tariff/cost from the quotation (or from the resulting jobs), and Company A issues a single Sales Invoice to the customer.

---

## 2. Concepts

### 2.1 Billing Company (Quote Owner)

- The **billing company** is the company that owns the Sales Quote and that will issue the **customer-facing Sales Invoice**. In the scenario above, this is **Company A**.
- Today, Sales Quote has a single `company` field. For intercompany, this company is treated as the **billing company** (the one that invoices the customer).

### 2.2 Operating Company (Per Leg / Job)

- Each job (Transport Job, Air Shipment, Sea Shipment, Warehouse Job, etc.) has a `company` field: the **operating company** that performs the service and bears cost/revenue in its books.
- When **operating company ≠ billing company**, that leg is **intercompany**: the operating company must invoice the billing company.

### 2.3 Intercompany Invoice

- An **intercompany invoice** is a document (or pair of documents) by which the **operating company** bills the **billing company** for services rendered in the context of a shared quotation/job.
- From the **billing company’s** perspective: it is a **Purchase Invoice** (buying services from the operating company).
- From the **operating company’s** perspective: it is a **Sales Invoice** (selling services to the billing company).
- Amounts are based on **tariff/cost from the quotation** (or from the job’s charges if no quote or if policy says “use job”).

---

## 3. Data Model

### 3.1 Existing Fields (No Change Required for Minimum Design)

- **Sales Quote**
  - `company` → **Billing company** (owner of quote; will invoice customer).
- **Sales Quote Routing Leg**
  - `job_type`, `job_no` → link to the job that performs the leg.
- **Job doctypes** (Transport Job, Air Shipment, Sea Shipment, Warehouse Job, etc.)
  - `company` → **Operating company** for that job.
  - Charges tables (e.g. `charges`) hold tariff/cost used for billing.

### 3.2 New / Extended Elements (Proposed)

1. **Sales Quote**
   - Optional: `billing_company` (default from `company`) for clarity when you later support “quote in one company, bill from another”.
   - For Phase 1, **billing company = Sales Quote.company**.

2. **Intercompany Invoice Request / Log (new doctype, optional)**
   - Purpose: track which legs have intercompany and whether the intercompany invoice has been created.
   - Fields (conceptual): `sales_quote`, `routing_leg` (or leg order), `job_type`, `job_no`, `billing_company`, `operating_company`, `intercompany_sales_invoice` (operating co), `intercompany_purchase_invoice` (billing co), `status`, `amount`, `currency`.
   - Alternatively, this can be implemented as **custom fields on the job** (e.g. `intercompany_sales_invoice`, `intercompany_purchase_invoice`, `billing_company`) to avoid a new doctype in Phase 1.

3. **Intercompany Settings (new or in Logistics Settings)**
   - Define **intercompany relationships**: which companies can act as billing vs operating and how they map (e.g. Company B → Company A as “internal customer/supplier”).
   - Optional: default **internal customer** (billing company as customer in operating company’s books) and **internal supplier** (operating company as supplier in billing company’s books).
   - Optional: **pricing basis** for intercompany: “From Quote (tariff/cost at quote)”, “From Job (charges on job)”, or “From Quote then Job fallback”.

---

## 4. End-to-End Flow

### 4.1 Quote Creation (Company A)

1. User creates a **Sales Quote** with:
   - Warehouse (leg) → will be operated by **Company B** (e.g. warehouse selected is of Company B, or leg-level “operating company” set to B).
2. Transport (leg) → operated by **Company C** (e.g. transport branch/company = C).
3. Air (leg) → operated by **Company A**.
4. **Company** on quote = **Company A** → billing company.

(If jobs are not yet created, “operating company” can be inferred when jobs are created from the quote, from each job’s `company`.)

### 4.2 Job Creation from Quote

- From Sales Quote, user (or automation) creates:
  - Warehouse Job (company = B),
  - Transport Order → Transport Job (company = C),
  - Air Booking → Air Shipment (company = A).
- Routing legs are updated with `job_no` / `job_type`. Each job’s `company` is the **operating company** for that leg.

### 4.3 Customer Invoice (Company A)

- User (or automation) creates **Sales Invoice** from Sales Quote (e.g. via existing “Create Sales Invoice from Sales Quote”).
- For **intercompany-aware consolidated** mode:
  - **Sales Invoice** is raised by **billing company (Company A)** to the **customer**.
  - Line items are built from **all legs** (Warehouse + Transport + Air) using **selling/tariff from quote or job** (same logic as today for “consolidated” invoice), so the customer sees one invoice with all charges.

### 4.4 Intercompany Invoices (Automated)

- For each **routing leg** where **operating company ≠ billing company**:
  - **Operating company** (B or C) creates a **Sales Invoice** to **billing company (A)** as “internal customer”.
  - **Billing company (A)** gets a **Purchase Invoice** from the **operating company** (B or C) as “internal supplier”.
- **Amounts**: Based on **pricing basis** (e.g. from quote tariff/cost for that leg, or from job charges). Same currency and amounts as agreed in the quote (or job) to avoid mismatch.
- **Trigger** (see Section 5): e.g. when the **customer Sales Invoice** is submitted, or when the job is “billable” and intercompany flag is set.

### 4.5 Same-Company Legs (No Intercompany)

- Legs where `job.company == billing_company` (e.g. Air by Company A) do **not** generate intercompany invoices; they are internal to Company A.

---

## 5. Automation: When and How to Create Intercompany Invoices

### 5.1 Trigger Options

| Option | When | Pros | Cons |
|--------|------|------|------|
| **A. On Customer SI submit** | When the consolidated Sales Invoice (Company A → customer) is submitted | One place; customer and intercompany stay in sync | Requires SI to be created first |
| **B. On job “Ready to bill”** | When each job is marked ready to bill and is intercompany | Can bill as each leg completes | Risk of partial billing before customer SI |
| **C. On “Create intercompany” button** | User runs action from Sales Quote or from Customer SI | Full control | Manual step |

**Recommendation:** Support **A** as primary automation (on customer Sales Invoice submit), with optional **C** for manual creation or regeneration. Option B can be added later for “bill by leg” policies.

### 5.2 Algorithm (Trigger: Customer Sales Invoice Submitted)

1. Get **Sales Quote** from the Sales Invoice (e.g. `quotation_no` or link to Sales Quote).
2. Get **billing company** = Sales Quote company (or explicit billing_company if added).
3. For each **routing leg** with `job_type` and `job_no`:
   - Load job; **operating company** = job.company.
   - If operating company == billing company → skip (no intercompany).
   - If operating company != billing company:
     - Check if an intercompany invoice for this leg already exists (e.g. via Intercompany Invoice Log or custom fields on job).
     - If not, **create intercompany pair**:
       - **Operating company**: create **Sales Invoice** (to billing company as customer), lines from quote/job tariff or job charges (see 5.3).
       - **Billing company**: create **Purchase Invoice** (from operating company as supplier), same lines/amounts.
     - Link both to job and to Sales Quote (and optionally to customer SI) for traceability.

### 5.3 Amount and Line Source (Tariff / Cost from Quote or Job)

- **Preferred**: Use the **same source** as the customer invoice for that leg (quote selling/tariff or job charges), so:
  - Customer SI line (for leg) and Intercompany SI/PI lines match in amount and description.
- **Implementation**:
  - If Sales Quote has leg-level selling amounts (e.g. from warehousing/transport/air_freight tables), use those for the corresponding leg.
  - Else use **job charges** (e.g. `estimated_revenue` or selling amount) for that job.
- **Currency**: Same as quote/job; no automatic FX in Phase 1.

### 5.4 Internal Customer / Supplier

- In **operating company’s** books: billing company (Company A) must exist as **Customer** (e.g. “Company A – Internal”).
- In **billing company’s** books: each operating company (B, C) must exist as **Supplier** (e.g. “Company B – Internal”, “Company C – Internal”).
- **Intercompany Settings** can store these mappings (billing_company ↔ operating_company and the internal Customer/Supplier IDs per company) so automation can resolve them without user input.

---

## 6. Implementation Outline

### Phase 1: Core Automation

1. **Settings**
   - Add **Intercompany** section in **Logistics Settings** or new **Intercompany Settings** doctype:
     - Enable intercompany invoicing.
     - Table: Billing Company, Operating Company, Internal Customer (in operating co), Internal Supplier (in billing co).
2. **Customer SI creation (existing)**
   - Ensure consolidated Sales Invoice from Sales Quote uses **billing company** (quote.company) and aggregates all legs. (Already uses main job company; extend so that when “intercompany mode” is on, SI company is always quote.company.)
3. **On Submit of Customer Sales Invoice**
   - In **Sales Invoice** `on_submit` (or via Invoice Integration / doc event):
     - If SI is linked to Sales Quote and intercompany is enabled, call **create_intercompany_invoices_for_quote(sales_quote, billing_company, trigger_si)**.
     - For each leg where job.company != billing_company, create:
       - Sales Invoice (operating company → billing company).
       - Purchase Invoice (billing company ← operating company).
     - Link created docs to job (e.g. `intercompany_sales_invoice`, `intercompany_purchase_invoice`) and optionally to a small log table or custom fields.
4. **Pricing**
   - Reuse existing helpers that build invoice lines from quote/job (e.g. `_get_invoice_items_from_job` or quote-level charge tables) to build lines for the intercompany SI and PI, so amounts align with quote tariff/cost.

### Phase 2: Traceability and Controls

- **Intercompany Invoice Log** doctype (or child table on Sales Quote): one row per leg with intercompany, with status and links to SI/PI.
- **Validations**: Prevent submitting customer SI if intercompany creation failed for a leg (or allow with warning and retry).
- **Report**: “Intercompany Invoices” by Sales Quote, by company, by date.

### Phase 3: Advanced

- **Pricing basis** selection: Quote-only vs Job-only vs Quote-then-Job.
- **Trigger on job** (option B): Create intercompany invoice when job is marked “Ready to bill” and quote is in “Intercompany” mode.
- **Multi-currency** and **intercompany reconciliation** (match PI to SI by reference).

---

## 7. Summary

| Item | Description |
|------|-------------|
| **Billing company** | Sales Quote company (Company A); issues one Sales Invoice to customer. |
| **Operating company** | Per-job `company` (B, C, or A). When ≠ billing company, leg is intercompany. |
| **Intercompany invoice** | Operating company raises Sales Invoice to billing company; billing company raises Purchase Invoice from operating company (same amounts). |
| **Amounts** | From quotation tariff/cost or job charges, consistent with customer invoice for that leg. |
| **Automation** | On submit of customer Sales Invoice, create intercompany SI/PI for each leg where operating company ≠ billing company. |
| **Settings** | Intercompany relationships and internal Customer/Supplier mapping per company pair. |

This design allows a forwarding company (Company A) to create one quotation for Warehouse (B), Transport (C), and Air (A), bill the customer with one Company A invoice, and automate intercompany invoices so Company B and Company C bill Company A based on the tariff/cost used in the quotation.
