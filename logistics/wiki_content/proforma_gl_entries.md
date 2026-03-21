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

Cost = sum of **(debit − credit)** for all GL rows where the account’s **Root Type = Expense** and `job_costing_number` matches the job, **excluding** the policy **Cost Accrual Account** (that expense is treated as part of the accrual story, not “realized” job cost in the summary).

---

## 3. WIP (Work in Progress)

**Source:** Journal Entries created by the recognition engine (WIP Recognition, WIP Adjustment, WIP Closure). Account names come from **Revenue Recognition Policy Settings** / **Recognition Parameters** (e.g. **WIP Account**, **Revenue Liability Account**).

### 3.1 WIP Recognition (e.g. on job submit)

| Account                    | Root Type | Debit | Credit | Remark        |
|----------------------------|-----------|-------|--------|---------------|
| Revenue Liability Account  | Asset*    | X     | 0      | Dr. WIP liability (policy account) |
| WIP Account                | Income    | 0     | X      | Cr. WIP       |

\*Policy validation uses **Asset** for Revenue Liability Account (e.g. contract asset / unbilled); your COA label may say “WIP Liability”.

**Profitability:** WIP amount = sum of **(credit − debit)** for the **WIP Account** only (from the job’s recognition policy), for the job’s `job_costing_number`.

### 3.2 WIP Adjustment / Closure

| Account                    | Root Type | Debit | Credit | Remark        |
|----------------------------|-----------|-------|--------|---------------|
| WIP Account                | Income    | X     | 0      | Dr. WIP (reversal) |
| Revenue Liability Account  | Asset*    | 0     | X      | Cr. liability |

This unwinds the WIP (Income) credit from recognition for the adjusted/closed amount.

---

## 4. Accrual (Accrued Cost Liability)

**Source:** Journal Entries created by the recognition engine (Accrual Recognition, Accrual Adjustment, Accrual Closure). Account names come from **Revenue Recognition Policy Settings** / **Recognition Parameters** (e.g. **Cost Accrual Account**, **Accrued Cost Liability Account**).

### 4.1 Accrual Recognition (e.g. on job submit)

| Account                         | Root Type | Debit | Credit | Remark      |
|---------------------------------|-----------|-------|--------|-------------|
| Cost Accrual Account            | Expense   | X     | 0      | Dr. Cost Accrual |
| Accrued Cost Liability Account  | Liability | 0     | X      | Cr. Liability    |

Accrual recognition may post **one Dr/Cr pair per charge line**, with the **Item** accounting dimension set on both rows when the site has an Item dimension on Journal Entry Account (same value as on charge `item_code` / `charge_item` when present).

**Profitability:** The summary tile **Accrual amount** = sum of **(credit − debit)** for the **Accrued Cost Liability Account** only (from the job’s recognition policy), for the job’s `job_costing_number`.

In the **Related GL Entries** table, rows on the **Cost Accrual Account** appear under the **Accrual** column (debit − credit), not under **Cost**, so accrual expense is visually grouped with accrual activity.

### 4.2 Accrual Adjustment / Closure

| Account                         | Root Type | Debit | Credit | Remark        |
|---------------------------------|-----------|-------|--------|---------------|
| Accrued Cost Liability Account  | Liability | X     | 0      | Dr. Liability |
| Cost Accrual Account            | Expense   | 0     | X      | Cr. Cost Accrual |

This reduces the accrued cost liability balance for the job.

### 4.3 Accrual reversal when Purchase Invoice is posted

When a **Purchase Invoice** is submitted with the same **Job Costing Number** as the job, and the job still has **open accrual** (`accrual_amount`), logistics posts an **Accrual reversal** Journal Entry: **Dr Accrued Cost Liability**, **Cr Cost Accrual**, up to each PI line amount (and capped by open accrual). The job’s `accrual_amount` and `recognized_costs` are updated. Where GL supports it, reversal lines use the same **Item** dimension as the PI line so accrual can be matched per item.

---

## 5. Summary: How Profitability Uses These

| Column   | GL basis |
|----------|----------|
| **Revenue** | Sum of (credit − debit) for **Income** and `job_costing_number` = job, **excluding** the policy **WIP Account** and accounts whose **Job Profit Account Type** is **Disbursements**, **WIP**, or **Accrual**. |
| **Cost**    | Sum of (debit − credit) for **Expense** and `job_costing_number` = job, **excluding** the policy **Cost Accrual Account** and the same **Job Profit Account Type** tags as above. |
| **WIP**     | Summary tile: **(credit − debit)** for the policy **WIP Account** only. The GL table also classifies accounts tagged **WIP** (Job Profit Account Type). |
| **Accrual** | Summary tile: **(credit − debit)** on the policy **Accrued Cost Liability Account** only. The GL table includes **Cost Accrual** (policy) and accounts tagged **Accrual** (Job Profit Account Type). |
| **Disbursements** | Sum of signed GL on accounts with **Job Profit Account Type = Disbursements** (by root type). |

## 6. Item Code on GL rows (Accounting Dimension)

If the site defines an **Accounting Dimension** for **Item**, ERPNext adds a Link field to **Item** on **GL Entry** and on **Sales Invoice Item** / **Purchase Invoice Item**. CargoNext **syncs `item_code` into that dimension field** on validate/submit (and on update after submit) so posted **Sales Invoice** and **Purchase Invoice** GL lines carry the item for job profitability.

The profitability table shows this as **Item Code** (same value as on the invoice line). The underlying GL column name follows your dimension (e.g. `item` or “Dimension Item”).

## 7. Disbursements (Job Profit Account Type)

On **Account**, the custom field **Job Profit Account Type** (`job_profit_account_type`) can be set to **Disbursements** (and **WIP**, **Accrual**, **Profit**). Rows on accounts tagged **Disbursements** appear in the **Disbursements** column in profitability (signed by root type like Income/Expense). They are excluded from the headline **Revenue** and **Cost** totals, which use **Profit**-style Income/Expense only (plus untagged Income/Expense). The KPI card **Disbursements** sums those GL lines.

## 8. Summary vs Details (tabs) and classified rows only

The profitability section uses **tabs** (**Summary** | **Details**): **Summary** totals **per Item Code** (up to 5000 classified GL rows); **Details** lists each classified GL entry (up to 100 rows). Switching tabs uses native label/radio behaviour (no desk JS required). GL lines that do not map to Revenue, Cost, WIP, Accrual, or Disbursements (including untagged Asset/Liability lines that are not policy accrual/WIP accounts) are **hidden**.

All figures are from **posted** GL entries (`docstatus = 1`) and optional date filters. See [Job Management Module](welcome/job-management-module) and the **Profitability (from GL)** section on job/shipment forms.
