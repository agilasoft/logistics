# Revenue and Cost Recognition, WIP and Accrual

This document describes how revenue recognition, cost recognition, Work in Progress (WIP), and accrual accounting work in the Logistics application, including the accounting entries created.

---

## Overview

The recognition system supports **accrual-based accounting** for logistics jobs (Air Shipment, Sea Shipment, Transport Job, Warehouse Job, Declaration, General Job). It enables:

1. **WIP (Work in Progress)** – Recognition of estimated revenue before billing
2. **Accrual** – Recognition of estimated costs before supplier invoices are received
3. **Adjustments** – Closing out WIP/accruals when actual revenue/costs are posted (Sales Invoice, Purchase Invoice)
4. **Job closure** – Automatic close-out of remaining WIP and accruals when a job is closed

---

## Concepts

### Revenue Recognition

- **Estimated Revenue**: Sum of `estimated_revenue` or `amount` from the job’s charges table
- **Recognized Revenue**: Revenue that has been moved from WIP to P&L (via adjustments or closure)
- **Actual Revenue**: Revenue from submitted Sales Invoices linked to the job

### Cost Recognition

- **Estimated Costs**: Sum of `estimated_cost` or `cost` from the job’s charges table
- **Recognized Costs**: Costs that have been moved from accrual to P&L (via adjustments or closure)
- **Actual Costs**: Costs from submitted Purchase Invoices linked to the job

### WIP (Work in Progress)

WIP represents **unbilled revenue** – work performed but not yet invoiced. It is an **asset** on the balance sheet.

- **WIP Recognition**: When a job is booked, estimated revenue can be recognized as WIP
- **WIP Adjustment**: When a Sales Invoice is posted, WIP is reduced and revenue is recognized
- **WIP Closure**: When the job is closed, remaining WIP is fully recognized

### Accrual

Accrual represents **incurred but not yet invoiced costs** – expenses expected but not yet billed by suppliers. It is a **liability** on the balance sheet.

- **Accrual Recognition**: When a job is booked, estimated costs can be accrued
- **Accrual Adjustment**: When a Purchase Invoice is posted, accruals are reduced and costs are recognized
- **Accrual Closure**: When the job is closed, remaining accruals are fully recognized

---

## Recognition Policy Settings

Recognition is controlled by **Recognition Policy Settings**, which define:

| Setting | Description |
|--------|-------------|
| **Company** | Company the policy applies to |
| **Cost Center / Profit Center / Branch** | Optional dimensions for matching (blank = default) |
| **Enable WIP Recognition** | Whether to recognize WIP |
| **Enable Accrual Recognition** | Whether to recognize accruals |
| **WIP Recognition Date Basis** | Date used for WIP: ATA, ATD, Job Booking Date, Job Creation, User Specified |
| **Accrual Recognition Date Basis** | Date used for accruals: same options |
| **WIP Account** | Asset account for Work in Progress |
| **Revenue Liability Account** | Liability account for deferred/unbilled revenue |
| **Cost Accrual Account** | Expense account for accrued costs |
| **Accrued Cost Liability Account** | Liability account for accrued costs payable |
| **Minimum WIP Amount** | Skip WIP if estimated revenue is below this |
| **Minimum Accrual Amount** | Skip accrual if estimated costs is below this |

### Settings Hierarchy

1. **Job-level overrides** (highest priority)
2. **Recognition Policy** matched by Cost Center + Profit Center + Branch (via Job Costing Number)
3. **Company default** (policy with blank dimensions)

---

## Accounting Entries Summary

### WIP Recognition

When WIP is first recognized for a job:

| Account | Debit | Credit |
|---------|-------|--------|
| WIP Account (Asset) | Amount | |
| Revenue Liability Account (Liability) | | Amount |

**Effect**: Asset increases (WIP), liability increases (deferred revenue).

---

### WIP Adjustment (when actual revenue is posted)

When a Sales Invoice is posted or during period closing:

| Account | Debit | Credit |
|---------|-------|--------|
| Revenue Liability Account (Liability) | Amount | |
| WIP Account (Asset) | | Amount |

**Effect**: Liability decreases, asset decreases. Revenue is recognized via the Sales Invoice entry (Dr Receivable, Cr Revenue).

---

### WIP Closure (job closed)

When the job is closed and remaining WIP is closed out:

| Account | Debit | Credit |
|---------|-------|--------|
| Revenue Liability Account (Liability) | Amount | |
| WIP Account (Asset) | | Amount |

**Effect**: Same as WIP adjustment; remaining WIP is fully recognized.

---

### Accrual Recognition

When accruals are first recognized for a job:

| Account | Debit | Credit |
|---------|-------|--------|
| Cost Accrual Account (Expense) | Amount | |
| Accrued Cost Liability Account (Liability) | | Amount |

**Effect**: Expense increases (accrued cost), liability increases (accrued payable).

---

### Accrual Adjustment (when actual costs are posted)

When a Purchase Invoice is posted or during period closing:

| Account | Debit | Credit |
|---------|-------|--------|
| Accrued Cost Liability Account (Liability) | Amount | |
| Cost Accrual Account (Expense) | | Amount |

**Effect**: Liability decreases, expense decreases (reversal). Actual cost is recognized via the Purchase Invoice (Dr Expense, Cr Payable).

---

### Accrual Closure (job closed)

When the job is closed and remaining accruals are closed out:

| Account | Debit | Credit |
|---------|-------|--------|
| Accrued Cost Liability Account (Liability) | Amount | |
| Cost Accrual Account (Expense) | | Amount |

**Effect**: Same as accrual adjustment; remaining accruals are fully recognized.

---

## Lifecycle Flow

```
Job Created/Submitted
        │
        ├──► recognize_wip() ────────► Dr WIP, Cr Revenue Liability
        │
        └──► recognize_accruals() ──► Dr Cost Accrual, Cr Accrued Cost Liability
        │
        │    [Sales Invoice posted]
        ├──► adjust_wip() ──────────► Dr Revenue Liability, Cr WIP
        │
        │    [Purchase Invoice posted]
        ├──► adjust_accruals() ─────► Dr Accrued Cost Liability, Cr Cost Accrual
        │
        │    [Job status = Closed/Completed/Cancelled]
        └──► close_wip() + close_accruals() ─► Same entries as adjustments
```

---

## Recognition Triggers

Recognition is triggered in two ways:

1. **On Submit** – When a job is submitted, WIP and accruals are auto-recognized if enabled in Recognition Policy Settings (`enable_wip_recognition`, `enable_accrual_recognition`).
2. **Manual** – **Post > Recognize WIP & Accrual** on the submitted job form runs both WIP and accrual recognition in one step.

---

## APIs and Automation

### Whitelisted APIs

| API | Purpose |
|-----|---------|
| `recognize(doctype, docname, recognition_date)` | Recognize both WIP and accruals (manual action) |
| `recognize_wip(doctype, docname, recognition_date)` | Recognize WIP for a job |
| `recognize_accruals(doctype, docname, recognition_date)` | Recognize accruals for a job |
| `adjust_wip(doctype, docname, adjustment_amount, adjustment_date)` | Adjust WIP when revenue is billed |
| `adjust_accruals(doctype, docname, adjustment_amount, adjustment_date)` | Adjust accruals when costs are invoiced |
| `close_job_recognition(doctype, docname, closure_date)` | Close all WIP and accruals for a job |
| `process_period_closing_adjustments(company, period_end_date)` | Batch process adjustments for period end |

### Automatic Behavior

- **Job submit**: `on_job_submit()` runs WIP and accrual recognition when enabled in settings
- **Job update**: `update_estimates_from_charges()` recalculates `estimated_revenue` and `estimated_costs` from the charges table
- **Job closure**: When status is Closed, Completed, or Cancelled, `handle_job_closure()` calls `close_wip()` and `close_accruals()` if there are open balances

---

## Period Closing

`process_period_closing_adjustments(company, period_end_date)`:

1. Finds jobs with `wip_amount > 0` or `accrual_amount > 0`
2. Computes actual revenue (Sales Invoices) and actual costs (Purchase Invoices) as of `period_end_date`
3. Adjusts WIP by `min(actual_revenue, wip_amount)`
4. Adjusts accruals by `min(actual_costs, accrual_amount)`
5. Returns a summary of adjustments and any errors

---

## Date Basis Options

| Option | Source |
|--------|--------|
| **ATA** | Actual Time of Arrival (`ata`, `actual_arrival`, `arrival_date`) |
| **ATD** | Actual Time of Departure (`atd`, `actual_departure`, `departure_date`) |
| **Job Booking Date** | `booking_date`, `job_booking_date`, `job_open_date`, or `creation` |
| **Job Creation** | Document creation date |
| **User Specified** | `recognition_date` on the job |

---

## Air Shipment Revenue Recognition (Additional)

Air Shipment has an extra **revenue recognition** flow (separate from WIP):

- **revenue_amount**: Total revenue for the shipment
- **revenue_recognition_method**: e.g. "On Delivery"
- **revenue_recognition_date**: When revenue is recognized
- **partial_revenue_enabled**: Allows partial recognition
- **recognized_revenue_amount**: Amount recognized when partial

`recognize_revenue()` updates these fields and saves the document. It does **not** create Journal Entries; those are created by the WIP/accrual engine when used.

---

## Job Types with Recognition Support

- Air Shipment  
- Sea Shipment  
- Transport Job  
- Warehouse Job  
- Declaration  
- General Job  

Each uses a `charges` child table with `estimated_revenue`/`amount` and `estimated_cost`/`cost` for calculations.

---

## Recognition Status Report

**Job Management > Recognition Status** shows:

- Job type, name, company, cost center  
- Estimated revenue, WIP amount, recognized revenue, WIP status  
- Estimated costs, accrual amount, recognized costs, accrual status  

WIP status: Not Started, Open, Recognized, Closed  
Accrual status: Not Started, Open, Recognized, Closed  
