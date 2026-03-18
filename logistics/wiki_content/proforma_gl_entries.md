# Proforma GL Entries (Job Costing)

This document describes the **proforma** (expected) General Ledger entries that appear under a job when **Job Costing Number** is set. All such entries are linked via the `job_costing_number` accounting dimension on GL Entry. The **Profitability (from GL)** section on job/shipment forms reads these entries to show Revenue, Cost, WIP, and Accrual.

---

## 1. Revenue (Income)

**Source:** Sales Invoice (created from or linked to the job).

When a Sales Invoice has **Job Costing Number** set, ERPNext posts GL entries with that dimension. Income account entries determine **Revenue** in the Profitability section.

| Account (Root Type) | Debit | Credit | Effect on Revenue |
|---------------------|-------|--------|-------------------|
| Income              | 0     | amount | + (credit − debit) |
| Receivable / other  | amount | 0     | —                 |

**Proforma (simplified):**

| Account        | Root Type | Debit | Credit |
|----------------|-----------|-------|--------|
| Sales - Jobs   | Income    | 0     | X      |
| Debtors        | Asset     | X     | 0      |

Revenue = sum of **(credit − debit)** for all GL rows where the account’s **Root Type = Income** and `job_costing_number` matches the job.

---

## 2. Cost (Expense)

**Source:** Purchase Invoice (created from or linked to the job).

When a Purchase Invoice has **Job Costing Number** set, ERPNext posts GL entries with that dimension. Expense account entries determine **Cost** in the Profitability section.

| Account (Root Type) | Debit | Credit | Effect on Cost |
|---------------------|-------|--------|----------------|
| Expense             | amount | 0     | + (debit − credit) |
| Payable / other     | 0     | amount | —                 |

**Proforma (simplified):**

| Account           | Root Type | Debit | Credit |
|-------------------|-----------|-------|--------|
| Cost of Goods / Expense | Expense | X     | 0      |
| Creditors         | Liability | 0    | X      |

Cost = sum of **(debit − credit)** for all GL rows where the account’s **Root Type = Expense** and `job_costing_number` matches the job. (WIP and Accrued Cost Liability are typically Asset/Liability, so they are not part of the Expense total; the **Cost Accrual Account** used in accrual JEs is Expense and is included in Cost.)

---

## 3. WIP (Work in Progress)

**Source:** Journal Entries created by the recognition engine (WIP Recognition, WIP Adjustment, WIP Closure). Account names come from **Recognition Policy Settings** (e.g. **WIP Account**, **Revenue Liability Account**).

### 3.1 WIP Recognition (e.g. on job submit)

| Account                    | Root Type | Debit | Credit | Remark     |
|----------------------------|-----------|-------|--------|------------|
| WIP Account                | Asset     | X     | 0      | Dr. WIP    |
| Revenue Liability Account  | Liability | 0     | X      | Cr. Revenue Liability |

**Profitability:** WIP amount = sum of **(debit − credit)** for the **WIP Account** only (from the job’s recognition policy), for the job’s `job_costing_number`.

### 3.2 WIP Adjustment / Closure

| Account                    | Root Type | Debit | Credit | Remark        |
|----------------------------|-----------|-------|--------|---------------|
| Revenue Liability Account  | Liability | X     | 0      | Dr. Liability |
| WIP Account                | Asset     | 0     | X      | Cr. WIP       |

This reduces the WIP account balance for the job.

---

## 4. Accrual (Accrued Cost Liability)

**Source:** Journal Entries created by the recognition engine (Accrual Recognition, Accrual Adjustment, Accrual Closure). Account names come from **Recognition Policy Settings** (e.g. **Cost Accrual Account**, **Accrued Cost Liability Account**).

### 4.1 Accrual Recognition (e.g. on job submit)

| Account                         | Root Type | Debit | Credit | Remark      |
|---------------------------------|-----------|-------|--------|-------------|
| Cost Accrual Account            | Expense   | X     | 0      | Dr. Cost Accrual |
| Accrued Cost Liability Account  | Liability | 0     | X      | Cr. Liability    |

**Profitability:** Accrual amount = sum of **(credit − debit)** for the **Accrued Cost Liability Account** only (from the job’s recognition policy), for the job’s `job_costing_number`.

### 4.2 Accrual Adjustment / Closure

| Account                         | Root Type | Debit | Credit | Remark        |
|---------------------------------|-----------|-------|--------|---------------|
| Accrued Cost Liability Account  | Liability | X     | 0      | Dr. Liability |
| Cost Accrual Account            | Expense   | 0     | X      | Cr. Cost Accrual |

This reduces the accrued cost liability balance for the job.

---

## 5. Summary: How Profitability Uses These

| Column   | GL basis |
|----------|----------|
| **Revenue** | Sum of (credit − debit) for accounts with **Root Type = Income** and `job_costing_number` = job. |
| **Cost**    | Sum of (debit − credit) for accounts with **Root Type = Expense** and `job_costing_number` = job. (WIP and accrual policy accounts are used only for WIP/Accrual columns.) |
| **WIP**     | Sum of (debit − credit) for the **WIP Account** from the job’s **Recognition Policy** (same dimension). If no policy or no WIP account, WIP = 0. |
| **Accrual** | Sum of (credit − debit) for the **Accrued Cost Liability Account** from the job’s **Recognition Policy** (same dimension). If no policy or no accrual account, Accrual = 0. |

All figures are from **posted** GL entries (`docstatus = 1`) and optional date filters. See [Job Management Module](welcome/job-management-module) and the **Profitability (from GL)** section on job/shipment forms.
