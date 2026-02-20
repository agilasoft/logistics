# Additional Charges for Jobs – Feature Specification

## Overview

Jobs (Transport Job, Warehouse Job, Air Shipment, Sea Shipment, Customs Declaration) receive their charges from their respective **orders** and **bookings** when the job is created. During execution, **additional charges** may be incurred (e.g. extra handling, demurrage, re-weighing) that require **client approval** before being applied to the job and billed.

This document describes the feature to support:

1. **Change Request** (new DocType) – captures additional charge costs and is the basis for creating a Sales Quote.
2. **Sales Quote** – extended with an “Additional Charge” flag and job reference; used for client approval of additional charges.
3. **Jobs** – Actions menu: “Get Additional Charges” (Sales Quote selection) and creation of Change Request; charge items get a **Sales Quote Link** to trace the source of each charge.

## Business Context

| Item | Description |
|------|-------------|
| **Current behavior** | Charges on jobs come from orders/bookings at job creation. |
| **Gap** | Ongoing jobs can incur extra charges that are not yet approved or quoted. |
| **Goal** | Allow creation of a Change Request → Sales Quote (with Additional Charge + job reference) → client approval → apply charges to the job with clear lineage (Sales Quote Link on charge rows). |

## Affected Job Types

- **Transport Job**
- **Warehouse Job**
- **Air Shipment**
- **Sea Shipment**
- **Customs Declaration**

Each has (or will have) a charges child table. Each charge row shall support a **Sales Quote Link** field to identify the source of the charge (original order/booking vs. additional-charge Sales Quote).

---

## Data Model

### 1. Change Request (New DocType)

**Purpose:** Capture additional charges (costs and, if needed, revenue) incurred during a job. This document is the **basis for creating a Sales Quote** for client approval.

| Field | Type | Description |
|-------|------|-------------|
| **Job Type** | Select | One of: Transport Job, Warehouse Job, Air Shipment, Sea Shipment, Customs Declaration. |
| **Job** | Dynamic Link | Link to the specific job (filtered by Job Type). |
| **Status** | Select | Draft, Submitted, Sales Quote Created, etc. (as per workflow). |
| **Remarks** | Text / Long Text | Reason or notes for the additional charges. |
| **Charge Items** | Table (Child) | **Change Request Charge** – see below. |

**Child table: Change Request Charge**

| Field | Type | Description |
|-------|------|-------------|
| **Item Code** | Link (Item) | Charge item. |
| **Description** | Data / Text | Optional description. |
| **Quantity** | Float | Quantity. |
| **UOM** | Link (UOM) | Unit of measure. |
| **Currency** | Link (Currency) | Currency. |
| **Unit Cost** | Currency | Cost per unit. |
| **Amount / Estimated Cost** | Currency | Total cost (and optionally revenue if needed). |
| **Remarks** | Text | Line-level notes. |

Change Request **contains the additional charge costs** (and optionally revenue) that will later be reflected in the Sales Quote and then applied to the job.

---

### 2. Sales Quote – New/Updated Fields

| Field | Type | Description |
|-------|------|-------------|
| **Additional Charge** | Check | If set, this Sales Quote is for additional charges (post-job-creation) and must reference a job. |
| **Job Type** | Select (or Link) | Type of job (Transport Job, Warehouse Job, Air Shipment, Sea Shipment, Customs Declaration). Optional; can be inferred from first item. |
| **Job** | Dynamic Link | The job to which these additional charges apply. Shown when **Additional Charge** is checked. |

**Sales Quote Items (child table)** – new field:

| Field | Type | Description |
|-------|------|-------------|
| **Job** | Dynamic Link (or Job Type + Job) | Job reference for this line (for additional-charge quotes). Links the quote line to the job for which the charge applies. |

Validation: When **Additional Charge** is checked, **Job** (and optionally Job Type) should be required; item rows for additional charges should carry the job reference.

---

### 3. Job Charge Tables – New Field

For each job type, the **charges child table** (e.g. Transport Job Charges, Warehouse Job Charges, Air Shipment Charges, Sea Shipment Charges, Customs Declaration charges) gets:

| Field | Type | Description |
|-------|------|-------------|
| **Sales Quote Link** | Link (Sales Quote) | Identifies the Sales Quote from which this charge row was taken (original order/booking quote or additional-charge quote). Null for charges that were not sourced from a Sales Quote. |

This allows reporting and traceability: which charges came from the original booking vs. which came from an “Additional Charge” Sales Quote.

---

## User Flows

### Flow A: Create Change Request from Job

1. User opens a **Job** (e.g. Transport Job, Air Shipment).
2. **Actions** → **Create Change Request** (or “Add Change Request”).
3. System creates a new **Change Request** with:
   - **Job Type** = current doctype.
   - **Job** = current job name.
4. User fills **Change Request Charge** rows (item, quantity, UOM, unit cost, amount, remarks).
5. User saves/submits the Change Request.
6. Later: **Create Sales Quote from Change Request** (server action or button on Change Request). This creates a Sales Quote with **Additional Charge** checked, **Job** set, and items populated from the Change Request charges (cost/revenue as per business rules).

### Flow B: Get Additional Charges from Sales Quote into Job

1. An **Additional Charge** Sales Quote already exists (e.g. created from a Change Request or manually), with **Job** and quote items linked to the job.
2. User opens the **Job**.
3. **Actions** → **Get Additional Charges**.
4. System shows a **Sales Quote** selection dialog (filter: **Additional Charge** = 1, and optionally **Job** = current job).
5. User selects one Sales Quote and confirms.
6. System copies the relevant quote items into the job’s charge table, setting **Sales Quote Link** = selected Sales Quote for each new charge row.
7. Existing charge rows are not duplicated; only new lines from the selected quote are added (business logic may restrict to one quote per job or allow multiple; design choice).

---

## Actions Menu on Jobs

For each job doctype (Transport Job, Warehouse Job, Air Shipment, Sea Shipment, Customs Declaration):

| Action | Description |
|--------|-------------|
| **Get Additional Charges** | Opens Sales Quote selection (filter by Additional Charge and optionally current job). On confirm, adds selected quote’s items to the job’s charges and sets **Sales Quote Link** on each new row. |
| **Create Change Request** | Creates a new **Change Request** linked to the current job (Job Type + Job). User then fills charge lines; this document is the basis for creating a Sales Quote (Additional Charge + job reference). |

Implementation: Add these as **Custom** or **Server Actions** in the respective job doctypes, or as buttons that call whitelisted methods.

---

## Implementation Summary

| Component | Description |
|-----------|-------------|
| **New DocType** | **Change Request** – header (Job Type, Job, Status, Remarks) + child table **Change Request Charge** (item, quantity, UOM, currency, unit cost, amount, remarks). Contains additional charge costs. |
| **Sales Quote** | Add **Additional Charge** (Check), **Job Type**, **Job**; add **Job** (or job reference) on **Sales Quote Item** for additional-charge lines. |
| **Job charge tables** | Add **Sales Quote Link** (Link to Sales Quote) on each charges child table (Transport Job Charges, Warehouse Job Charges, Air Shipment Charges, Sea Shipment Charges, Customs Declaration charges). |
| **Job Actions** | **Get Additional Charges** – prompt Sales Quote selection; apply selected quote’s items to job charges with Sales Quote Link set. **Create Change Request** – create Change Request linked to current job. |
| **Change Request → Sales Quote** | Button or action on Change Request to **Create Sales Quote** – creates a Sales Quote with Additional Charge = 1, Job set, and items from Change Request Charge. |

---

## Validation and Rules (Suggested)

1. **Sales Quote:** If **Additional Charge** is checked, **Job** (and Job Type if used) is required.
2. **Sales Quote Items:** For Additional Charge quotes, each item row should have job reference (or inherit from header).
3. **Get Additional Charges:** Only allow selecting Sales Quotes where **Additional Charge** = 1 and **Job** = current job (or leave flexible to support multi-job quotes if required).
4. **Change Request:** **Job** and **Job Type** required; at least one **Change Request Charge** row before submission (if submitted state is used).
5. **Charge items on job:** When adding rows via **Get Additional Charges**, set **Sales Quote Link** to the selected Sales Quote; do not overwrite existing rows’ Sales Quote Link.

---

## Optional Enhancements

- **Workflow on Change Request:** Draft → Submitted → Sales Quote Created.
- **Link from Sales Quote back to Change Request:** If Sales Quote was created from a Change Request, store **Change Request** link on Sales Quote for audit trail.
- **Permissions:** Restrict “Get Additional Charges” and “Create Change Request” by role if only certain users should add or approve additional charges.
- **Reporting:** List view or report of jobs with additional charges (where any charge row has **Sales Quote Link** pointing to an Additional Charge quote).

---

## Summary

| Item | Description |
|------|-------------|
| **Feature** | Support additional charges on jobs with client approval via Sales Quote and traceability via Sales Quote Link on charge rows. |
| **New DocType** | **Change Request** – holds additional charge costs; basis for creating an “Additional Charge” Sales Quote. |
| **Sales Quote** | **Additional Charge** checkbox; **Job** (and Job Type) and job reference on items. |
| **Job charge tables** | **Sales Quote Link** on each charge row. |
| **Job Actions** | **Get Additional Charges** (Sales Quote selection → apply to job); **Create Change Request** (new Change Request linked to job). |
