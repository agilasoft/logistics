# Revenue and Cost Recognition - User Guide

## Overview

The Revenue and Cost Recognition module allows you to:
- Recognize **WIP (Work In Progress)** for estimated revenue before actual billing
- Recognize **Accruals** for estimated costs before actual vendor invoices
- Automatically adjust WIP and Accruals when actual transactions are posted
- Close recognition entries when jobs are completed

---

## 1. Setup

### 1.1 Create Recognition Policy Settings

Navigate to: **Job Management > Recognition Policy Settings > New**

#### Basic Configuration

| Field | Description |
|-------|-------------|
| **Company** | Select your company (required) |
| **Cost Center** | Leave blank for company-wide default, or select specific cost center |
| **Profit Center** | Leave blank for company-wide default, or select specific profit center |
| **Branch** | Leave blank for company-wide default, or select specific branch |
| **Enabled** | Check to activate this policy |
| **Priority** | Higher number = higher priority when multiple policies match |

#### WIP Recognition Settings

| Field | Description |
|-------|-------------|
| **Enable WIP Recognition** | Check to enable WIP recognition for matching jobs |
| **WIP Recognition Date Basis** | When to recognize WIP: ATA, ATD, Job Booking Date, Job Creation, or User Specified |
| **WIP Account** | Asset account for Work In Progress (e.g., "Work In Progress - Assets") |
| **Revenue Liability Account** | Liability account for deferred revenue (e.g., "Deferred Revenue - Liabilities") |
| **Minimum WIP Amount** | Skip WIP recognition if estimated revenue is below this amount |

#### Accrual Recognition Settings

| Field | Description |
|-------|-------------|
| **Enable Accrual Recognition** | Check to enable accrual recognition for matching jobs |
| **Accrual Recognition Date Basis** | When to recognize accruals: ATA, ATD, Job Booking Date, Job Creation, or User Specified |
| **Cost Accrual Account** | Expense account for accrued costs (e.g., "Cost Accrual - Expenses") |
| **Accrued Cost Liability Account** | Liability account for accrued costs payable |
| **Minimum Accrual Amount** | Skip accrual recognition if estimated cost is below this amount |

### 1.2 Setup Examples

#### Example 1: Company-Wide Default Policy
Create a policy with:
- Company: Your Company
- Cost Center: *(leave blank)*
- Profit Center: *(leave blank)*
- Branch: *(leave blank)*
- Priority: 0

This will apply to all jobs in the company unless overridden by a more specific policy.

#### Example 2: Specific Cost Center Policy
Create a policy with:
- Company: Your Company
- Cost Center: Air Freight Operations
- Profit Center: *(leave blank)*
- Branch: *(leave blank)*
- Priority: 10

This will override the company default for all jobs with "Air Freight Operations" cost center.

#### Example 3: Branch-Specific Policy
Create a policy with:
- Company: Your Company
- Cost Center: *(leave blank)*
- Profit Center: *(leave blank)*
- Branch: Manila Branch
- Priority: 5

This will apply to all jobs from Manila Branch.

### 1.3 Required Accounts

Before using recognition, ensure these accounts exist in your Chart of Accounts:

| Account | Type | Purpose |
|---------|------|---------|
| WIP Account | Asset | Holds recognized revenue before billing |
| Revenue Liability | Liability | Deferred revenue liability |
| Cost Accrual | Expense | Accrued cost expense |
| Accrued Cost Liability | Liability | Costs payable not yet invoiced |

---

## 2. Using Recognition on Jobs

### 2.1 Supported Job Types

Recognition is available on:
- Air Shipment
- Sea Shipment
- Transport Job
- Warehouse Job
- Customs Declaration
- General Job

### 2.2 Recognition Section on Job Form

After submitting a job, you'll see a **Revenue & Cost Recognition** section with:

**WIP Fields:**
- Estimated Revenue
- WIP Amount (current balance)
- Recognized Revenue (amount already closed)
- WIP Journal Entry (link to initial recognition)
- WIP Adjustment JE (link to adjustment entries)
- WIP Closed (checkbox)

**Accrual Fields:**
- Estimated Costs
- Accrual Amount (current balance)
- Recognized Costs (amount already closed)
- Accrual Journal Entry (link to initial recognition)
- Accrual Adjustment JE (link to adjustment entries)
- Accrual Closed (checkbox)

### 2.3 Job-Level Overrides

You can override the default recognition settings on individual jobs:
- **Enable WIP Recognition**: Override company/cost center setting
- **WIP Recognition Date Basis**: Override default date basis
- **Enable Accrual Recognition**: Override company/cost center setting
- **Accrual Recognition Date Basis**: Override default date basis
- **Recognition Date**: Used when date basis is "User Specified"

---

## 3. Recognition Workflow

### 3.1 Initial WIP Recognition

**When to use:** When you want to recognize estimated revenue before actual billing.

**Steps:**
1. Open a submitted job document
2. Click **Recognition > Recognize WIP**
3. Enter the recognition date (defaults to today)
4. Click **Create**

**Journal Entry Created:**
```
Dr. WIP Account (Asset)              [Estimated Revenue]
    Cr. Revenue Liability                [Estimated Revenue]
```

### 3.2 Initial Accrual Recognition

**When to use:** When you want to recognize estimated costs before actual vendor invoices.

**Steps:**
1. Open a submitted job document
2. Click **Recognition > Recognize Accruals**
3. Enter the recognition date (defaults to today)
4. Click **Create**

**Journal Entry Created:**
```
Dr. Cost Accrual (Expense)           [Estimated Cost]
    Cr. Accrued Cost Liability           [Estimated Cost]
```

### 3.3 Adjusting WIP (Upon Actual Billing)

**When to use:** When you create a Sales Invoice for the job.

**Steps:**
1. Open the job document
2. Click **Recognition > Adjust WIP**
3. Enter the adjustment amount (amount billed)
4. Enter the adjustment date (billing date)
5. Click **Create**

**Journal Entry Created:**
```
Dr. Revenue Liability                [Billed Amount]
    Cr. WIP Account                      [Billed Amount]
```

**Note:** The actual Sales Invoice posts separately (Dr. Accounts Receivable, Cr. Revenue).

### 3.4 Adjusting Accruals (Upon Actual Invoice Receipt)

**When to use:** When you receive a Purchase Invoice for the job.

**Steps:**
1. Open the job document
2. Click **Recognition > Adjust Accruals**
3. Enter the adjustment amount (invoiced amount)
4. Enter the adjustment date (invoice date)
5. Click **Create**

**Journal Entry Created:**
```
Dr. Accrued Cost Liability           [Invoiced Amount]
    Cr. Cost Accrual                     [Invoiced Amount]
```

**Note:** The actual Purchase Invoice posts separately (Dr. Expense, Cr. Accounts Payable).

### 3.5 Closing Recognition (Job Closure)

**When to use:** When a job is completed and you want to close all remaining WIP and Accruals.

**Steps:**
1. Open the job document
2. Click **Recognition > Close Recognition**
3. Confirm the action
4. Enter the closure date
5. Click **Close**

This will:
- Close out any remaining WIP balance
- Close out any remaining Accrual balance
- Mark WIP and Accrual as "Closed"

**Automatic Closure:** Recognition is also automatically closed when the job status changes to "Closed", "Completed", or "Cancelled".

---

## 4. Accounting Entry Summary

### WIP (Revenue Recognition)

| Event | Debit | Credit |
|-------|-------|--------|
| Initial Recognition | WIP (Asset) | Revenue Liability |
| Adjustment (on billing) | Revenue Liability | WIP (Asset) |
| Closure | Revenue Liability | WIP (Asset) |

### Accrual (Cost Recognition)

| Event | Debit | Credit |
|-------|-------|--------|
| Initial Recognition | Cost Accrual (Expense) | Accrued Cost Liability |
| Adjustment (on invoice) | Accrued Cost Liability | Cost Accrual (Expense) |
| Closure | Accrued Cost Liability | Cost Accrual (Expense) |

---

## 5. Reports

### 5.1 Recognition Status Report

Navigate to: **Job Management > Reports > Recognition Status**

This report shows:
- All jobs with their WIP and Accrual status
- Filter by Company, Cost Center
- Filter by WIP Status: Not Started, Open, Recognized, Closed
- Filter by Accrual Status: Not Started, Open, Recognized, Closed

Use this report to:
- Monitor open WIP and Accrual balances
- Identify jobs that need adjustment
- Review closed recognition entries

---

## 6. Period Closing

### 6.1 Manual Period Closing

For period-end adjustments, review all open WIP and Accruals:

1. Run the **Recognition Status Report**
2. Filter for "Open" WIP and Accrual status
3. For each job with open balances:
   - Review actual revenue/costs posted
   - Create appropriate adjustments
   - Or close if the job is complete

### 6.2 Automated Period Closing

An administrator can run the period closing process:

```python
from logistics.job_management.recognition_engine import process_period_closing_adjustments

result = process_period_closing_adjustments(
    company="Your Company",
    period_end_date="2024-12-31"
)
```

This will automatically adjust WIP and Accruals based on actual revenue and costs posted.

---

## 7. Estimated Revenue/Cost Sources

### 7.1 From Charges Table

The system calculates estimated amounts from the charges child table:
- **Estimated Revenue**: Sum of `estimated_revenue` field in charges
- **Estimated Cost**: Sum of `estimated_cost` field in charges

### 7.2 Fallback Calculation

If `estimated_revenue` or `estimated_cost` fields are not set in charges:
- Falls back to `amount` field for revenue
- Falls back to `cost` field for costs

### 7.3 Populating Estimates

To ensure accurate recognition:
1. Enter estimated revenue and cost in each charge line
2. Or ensure the `amount` and `cost` fields are populated
3. The job's total estimates are auto-calculated on save

---

## 8. Recognition Date Basis Options

| Option | Description |
|--------|-------------|
| **ATA** | Actual Time of Arrival - uses `ata`, `actual_arrival`, or `arrival_date` field |
| **ATD** | Actual Time of Departure - uses `atd`, `actual_departure`, or `departure_date` field |
| **Job Booking Date** | Uses `booking_date`, `job_booking_date`, or `job_open_date` field |
| **Job Creation** | Uses the document creation date |
| **User Specified** | Uses the `recognition_date` field on the job |

---

## 9. Settings Priority

When multiple Recognition Policy Settings could apply, the system uses this priority:

1. **Job-Level Overrides** (highest priority)
   - Settings directly on the job document

2. **Exact Match Policy**
   - Policy matching all three: Cost Center + Profit Center + Branch

3. **Partial Match Policy**
   - Policy matching some dimensions (blank fields act as wildcards)
   - Higher `priority` value wins when multiple match

4. **Company Default** (lowest priority)
   - Policy with blank Cost Center, Profit Center, and Branch

---

## 10. Troubleshooting

### Issue: Recognition buttons not appearing
- Ensure the job is submitted (docstatus = 1)
- Check that Recognition Policy Settings exists for the company
- Verify WIP or Accrual recognition is enabled in settings

### Issue: "Recognition date could not be determined"
- Check the Recognition Date Basis setting
- Ensure the corresponding date field is populated on the job
- Or use "User Specified" and enter a Recognition Date

### Issue: "Estimated revenue must be greater than zero"
- Enter estimated revenue in the charges table
- Or populate the job-level estimated_revenue field

### Issue: Account not found
- Ensure WIP, Revenue Liability, Cost Accrual, and Accrued Cost Liability accounts are set in Recognition Policy Settings
- Verify accounts belong to the correct company

---

## 11. Best Practices

1. **Create a company-wide default policy first** - This ensures all jobs have a fallback policy

2. **Use specific policies for exceptions** - Create policies with higher priority for cost centers or branches that need different settings

3. **Set minimum amounts** - Use minimum WIP/Accrual amounts to skip recognition for small jobs

4. **Regular period review** - Run the Recognition Status Report monthly to review open balances

5. **Close jobs properly** - Ensure job status is updated to "Closed" or "Completed" to trigger automatic recognition closure

6. **Document estimates** - Enter estimated revenue and costs in charges as early as possible for accurate recognition
