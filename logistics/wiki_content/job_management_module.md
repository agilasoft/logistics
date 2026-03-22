# Job Management Module

**Job Management** provides cross-module support for job costing, revenue recognition, and organizational structure. It integrates with Air Shipment, Sea Shipment, Transport Job, Warehouse Job, Declaration, and General Job for recognition policies and cost center allocation.

To access: **Home > Job Management**

## 1. Key Concepts

### 1.1 Job Costing Number

**Job Costing Number** is a master that defines costing series and defaults for jobs. Used when creating jobs to assign cost centers and profit centers.

### 1.2 Revenue Recognition Policy Settings

**Revenue Recognition Policy Settings** (DocType: Recognition Policy Settings) is **one document per company**. Rules live in **Recognition Parameters** (dimensions + single **Recognition Date Basis** + four GL accounts). **Post → Recognize WIP & Accrual** uses one posting date for both WIP and accrual. Disbursement charge lines are excluded from recognition totals.

**Detail:** [Revenue Recognition Policy — Accounts, Dates, and Charges](welcome/revenue-recognition-policy-accounts-and-dates)

### 1.3 Masters

- **Company** – ERPNext Company
- **Branch** – Branch for job allocation
- **Cost Center** – Cost center for job costs
- **Profit Center** – Profit center for job revenue

## 2. Estimated vs Actual Revenue and Cost

On charge child tables (Air Shipment Charges, Sea Shipment Charges, Transport Job Charges, Warehouse Job Charges, Declaration Charges), each row has:

- **Estimated Revenue / Estimated Cost** – Taken from the source Booking or Order; used as the basis for **WIP** and **Accrual** recognition.
- **Actual Revenue / Actual Cost** – Calculated on the shipment or job using the same calculation method; used for **Sales Invoice** and **Purchase Invoice** when present and &gt; 0 (otherwise the system falls back to estimated amounts).

**Recalculate All Charges** on the parent document updates only Actual Revenue and Actual Cost; estimated amounts are left unchanged. This keeps WIP and accrual on estimates while invoicing can use confirmed actual amounts.

## 3. Profitability (from GL)

Job Management provides a **Profitability** section on job and shipment forms. When a document has **Job Costing Number** and **Company** set, the section loads revenue, cost, gross profit, profit margin, WIP amount, and accrual amount from the General Ledger (GL Entry by job_costing_number). It also shows a table of related GL entries with links to view the source vouchers (Sales Invoice, Purchase Invoice, Journal Entry, etc.).

**Supported doctypes:** Air Shipment, Sea Shipment, Transport Job, Warehouse Job, Declaration, General Job

Figures are computed from posted GL entries: Income accounts for revenue, Expense accounts for cost. WIP and accrual use accounts from the Recognition Policy when configured.

For a description of the **proforma GL entries** (expected vouchers and account movements), see [Proforma GL Entries](welcome/proforma-gl-entries).

## 4. Reports

- **Recognition Status** – WIP and revenue recognition status across jobs

## 5. Related Topics

- [Recent Platform Updates](welcome/recent-platform-updates) – summary of billing, recognition, and transport changes
- [WIP and Accrual Reversal on Invoicing](welcome/wip-accrual-reversal-on-invoicing-design) – invoice and internal billing reversal design
- [Internal and Intercompany Billing](welcome/internal-and-intercompany-billing)
- [General Job](welcome/general-job)
- [Air Shipment](welcome/air-shipment)
- [Sea Shipment](welcome/sea-shipment)
- [Transport Job](welcome/transport-job)
- [Warehouse Job](welcome/warehouse-job)
- [Declaration](welcome/declaration)
- [Reports Overview](welcome/reports-overview)
