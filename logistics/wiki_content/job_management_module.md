# Job Management Module

**Job Management** provides cross-module support for job costing, revenue recognition, and organizational structure. It integrates with Air Shipment, Sea Shipment, Transport Job, Warehouse Job, Declaration, and General Job for recognition policies and cost center allocation.

To access: **Home > Job Management**

## 1. Key Concepts

### 1.1 Job Costing Number

**Job Costing Number** is a master that defines costing series and defaults for jobs. Used when creating jobs to assign cost centers and profit centers.

### 1.2 Recognition Policy Settings

**Recognition Policy Settings** configures revenue and cost recognition policies per job type. Controls when revenue and cost are recognized (e.g., on milestone completion, on delivery).

### 1.3 Masters

- **Company** – ERPNext Company
- **Branch** – Branch for job allocation
- **Cost Center** – Cost center for job costs
- **Profit Center** – Profit center for job revenue

## 2. Profitability (from GL)

Job Management provides a **Profitability** section on job and shipment forms. When a document has **Job Costing Number** and **Company** set, the section loads revenue, cost, gross profit, profit margin, WIP amount, and accrual amount from the General Ledger (GL Entry by job_costing_number). It also shows a table of related GL entries with links to view the source vouchers (Sales Invoice, Purchase Invoice, Journal Entry, etc.).

**Supported doctypes:** Air Shipment, Sea Shipment, Transport Job, Warehouse Job, Declaration, General Job

Figures are computed from posted GL entries: Income accounts for revenue, Expense accounts for cost. WIP and accrual use accounts from the Recognition Policy when configured.

## 3. Reports

- **Recognition Status** – WIP and revenue recognition status across jobs

## 4. Related Topics

- [General Job](welcome/general-job)
- [Air Shipment](welcome/air-shipment)
- [Sea Shipment](welcome/sea-shipment)
- [Transport Job](welcome/transport-job)
- [Warehouse Job](welcome/warehouse-job)
- [Declaration](welcome/declaration)
- [Reports Overview](welcome/reports-overview)
