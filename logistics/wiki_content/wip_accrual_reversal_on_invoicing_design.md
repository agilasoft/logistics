# Design: WIP and Accrual Reversal on Posted Invoices and Internal Billing

**Implementation status:** The behaviour below is implemented in `logistics/invoice_integration/` — `wip_reversal.py` (Sales Invoice), `accrual_reversal.py` (Purchase Invoice, idempotent + multi-job helper), `internal_billing_recognition_reversal.py` (internal billing JE), and `recognition_voucher_reversal.py` (shared idempotency). Intercompany SI/PI use the standard ERPNext doctypes and the same submit hooks.

This document specifies the process for reversing **WIP recognition** and **cost accrual recognition** in step with real economic documents: **Sales Invoice**, **Purchase Invoice**, **intercompany SI/PI**, and **internal billing Journal Entries**. The goal is **line-level** (or best-available **item-level**) alignment between what was recognized and what is now being billed or accrued via standard postings.

---

## 1. Context and today’s behavior

### 1.1 Recognition (summary)

- **WIP recognition** (policy): Journal Entry that **Dr Revenue Liability**, **Cr WIP (Income)**. Tracked on the job via `wip_amount`, `wip_journal_entry`, etc. Reversal today uses **WIP adjustment** / **closure** JEs (**Dr WIP**, **Cr Revenue Liability**) via `RecognitionEngine.adjust_wip` / `close_wip` — not tied to Sales Invoice submit.
- **Cost accrual recognition** (policy): Accrual JE split by charge lines when possible (**Dr Cost Accrual**, **Cr Accrued Cost Liability**). Tracked via `accrual_amount`, `accrual_journal_entry`, etc.

### 1.2 What already exists

- **Purchase Invoice submit**: `reverse_cost_accrual_for_purchase_invoice` (`logistics/invoice_integration/accrual_reversal.py`) posts an **accrual reversal** JE (**Dr Accrued Cost Liability**, **Cr Cost Accrual**) up to each PI line amount, capped by open `accrual_amount`, with **optional per-item** matching when Item is an accounting dimension on GL Entry (see `_paired_accrual_open_for_item`).
- **Sales Invoice submit**: Updates job lifecycle and charge-row status only; **does not** reverse WIP.
- **Internal billing** (`logistics/billing/internal_billing.py`): On customer SI submit, a balancing **Journal Entry** records internal job revenue/cost; rows reference the Internal Job via `reference_type` / `reference_name` but **do not** currently drive WIP/accrual reversal.

This design **extends** the PI accrual pattern to **SI → WIP**, **intercompany documents**, and **internal billing JVs**, with consistent rules.

---

## 2. Design principles

1. **Same policy, same accounts**  
   Reversal JEs must use the job’s **Recognition Policy** (WIP account, revenue liability, cost accrual, accrued liability) resolved via **Job Number** on the voucher (same as today for PI accrual).

2. **Resolve the job**  
   For each posting, determine `(job_doctype, job_name)` and **JCN** from:
   - header `job_number` → Job Number → job; and/or  
   - `Sales Invoice Item` / `Purchase Invoice Item` `reference_doctype` / `reference_name` when they point to a logistics job or charge row’s parent job; and/or  
   - intercompany log: `(job_type, job_no)` stored on **Intercompany Invoice Log** for the intercompany SI/PI.

3. **Line-level reversal where possible**  
   For each invoice line with a positive **base net amount** (or equivalent for JV segments — see §5):
   - **WIP**: reverse up to `min(line_amount, open_WIP_for_item, remaining_job_wip_balance)` using the same **item** matching approach as accrual reversal when Item dimension exists on GL; otherwise fall back to **FIFO or proportional** consumption of open WIP against lines (configurable; default **min(line, remaining)** in document line order).
   - **Accrual**: keep current rule — `min(line_amount, open_accrual_for_item, remaining_job_accrual)` per PI line.

4. **No double reversal**  
   - Store a link from the job (or a small child log) to **which voucher** already triggered reversal, or encode **reference_type / reference_name** on reversal JE rows pointing to SI/PI/JE so a resubmit/recreate does not duplicate (idempotency check before posting).

5. **Company boundary**  
   Reversal runs in the **company of the posted document**. The **job** whose `wip_amount` / `accrual_amount` is updated must be the job whose recognition was posted in that same economic context (operating company’s job for intercompany SI from the internal leg; billing company’s PI may reference JCN in billing company — design must define which job holds accrual when two companies are involved; see §4).

6. **Charges alignment**  
   Prefer matching **item_code** on invoice lines to **charge lines** that fed WIP/accrual recognition (`_get_accrual_lines_from_charges` / estimated revenue used for WIP). If an item is not on the original recognition split, use the **aggregate** fallback for that line’s amount only.

---

## 3. Customer Sales Invoice (from job / shipment)

**Trigger**: `on_sales_invoice_submit` after ERPNext posts SI GL (or immediately after submit in same transaction, consistent with PI hook).

**Preconditions**

- SI has **Job Number** (or resolvable job references on lines).
- Job has **open WIP** (`wip_amount` > 0 or open balance on policy **WIP account** in GL for that JCN).
- Policy has **WIP account** and **revenue liability account**.

**Action**

- For each SI line (in sequence):
  - Compute **reversal amount** per §2.3 (WIP branch).
  - Post **one consolidated WIP reversal JE** per SI (or one per job if multi-job SI is ever allowed): for each slice, **Dr WIP account**, **Cr Revenue liability**, with **job_number**, cost/profit centers, and **Item** dimension when present (mirror `create_wip_adjustment_je` in `recognition_engine.py`).
- Update job: `wip_amount -= total_reversed`, set `wip_adjustment_journal_entry` (append or last pointer per product decision), increment `recognized_revenue` analogously to `adjust_wip`.

**Fully invoiced**  
Optional: when cumulative reversed WIP ≥ original recognized WIP, set flags consistent with manual close (without forcing `wip_closed` if further SI expected — product choice).

---

## 4. Customer Purchase Invoice (from job / shipment)

**Trigger**: existing `update_job_on_purchase_invoice_submit` → `reverse_cost_accrual_for_purchase_invoice`.

**Design refinement**

- Keep current behavior as the **baseline**.
- Ensure **intercompany Purchase Invoice** (billing company) is **included**: same hook on submit; resolve JCN and job; if the PI is the mirror of an intercompany SI, **job_number** and items should match the leg so **per-item** accrual reversal applies.
- If billing-company PI uses a **different JCN** than the operating job’s recognition, document a **mapping rule** (e.g. same logical shipment ID on both companies) or restrict v1 to **JCN on PI equals recognition job**.

---

## 5. Intercompany Sales Invoice and Purchase Invoice

Intercompany flow is described in [Internal and Intercompany Billing](welcome/internal-and-intercompany-billing): one **SI** (operating company) and one **PI** (billing company) per internal leg.

| Document | Company | Reversal target (typical) |
|----------|---------|---------------------------|
| **Intercompany SI** | Operating company | **WIP** on the **Internal Job** (that leg’s job), for line amounts / items on that SI |
| **Intercompany PI** | Billing company | **Cost accrual** on the job whose costs were accrued **in billing company books** — if recognition only exists on the operating job, **either** (a) replicate recognition metadata to billing company job, or (b) accrue only on operating company and reverse only there (then PI reversal is N/A on billing PI). **Recommended v1**: recognition and reversal stay on the **job that submitted recognition** (usually operating company’s Internal Job); intercompany **PI** in billing company carries JCN that **still points** to that job’s costing number if shared, or use **one JCN per legal entity** with clear policy — **implementation must choose one model and document it in settings**. |

**Process (symmetric)**

1. On **intercompany SI submit** → run the **same WIP reversal routine** as §3 (operating company, job from log + lines).
2. On **intercompany PI submit** → run the **same accrual reversal routine** as §4 (billing company, job + JCN from PI).

**Duplicate customer SI**  
When customer SI submit **also** creates intercompany SI/PI, avoid **double WIP reversal** for the same leg: either skip WIP reversal on customer SI for lines that belong only to internal legs, **or** reverse WIP only on **intercompany SI** for internal legs and only on **customer SI** for main job lines. **Recommended**: reverse **WIP** on the document that **first** recognizes revenue for that leg at arm’s length — **customer SI** for main job; **intercompany SI** for internal jobs. Charge rows / quote routing must identify **which job** each line belongs to.

---

## 6. Internal billing Journal Entry

**Trigger**: After `create_internal_billing_journal_entries_for_quote` submits the JV (`je.submit()`), call a new handler e.g. `reverse_wip_and_accrual_for_internal_billing_je(je_doc)`.

**Why**  
Internal jobs are **not** invoiced with SI; the JV is the economic recognition of **internal revenue** and **internal cost**. WIP and policy accrual on those internal jobs should be cleared consistently with §3–4.

**Inputs from current JV structure**

Today each internal job produces **aggregates**:

- **Revenue total** → internal allocation: Dr expense (allocation), Cr income — references Internal Job.
- **Cost total** → Dr expense, Cr payable — references Internal Job.

**Reversal amounts (v1 — job aggregate)**

- **WIP reversal** for each Internal Job referenced: amount = **min(internal revenue total posted on JV for that job, open wip on job)** (single line pair per job if no item split on JV).
- **Accrual reversal**: the JV’s “internal cost accrual” leg is **not** the same accounts as **policy cost accrual** (it uses `default_payable_account`). So policy accrual reversal should still be **Dr Liability / Cr Cost Accrual** for **min(cost_total, open accrual on job)** when the job had **enable_accrual_recognition** and open `accrual_amount`.

**v2 (item-level)**  
Extend internal billing JV construction to add **one JE row pair per charge item** (item_code + amount) with `job_number`, then reuse the same per-item reversal logic as invoices.

**Idempotency**  
Use `user_remark` / custom field **Internal Billing – Sales Quote {name} – Trigger SI {si}** (already present) to detect already-processed JVs before posting reversal JEs.

---

## 7. Orchestration and hooks (implementation map)

| Event | Handler location (proposed) | WIP | Accrual |
|-------|---------------------------|-----|---------|
| Sales Invoice submit | `invoice_integration/lifecycle.py` + new module e.g. `wip_reversal.py` | Yes | No |
| Purchase Invoice submit | existing `accrual_reversal.py` | No | Yes (extend for edge cases) |
| Intercompany SI submit | same as SI submit (document is standard SI) | Yes | No |
| Intercompany PI submit | same as PI submit | No | Yes |
| Internal billing JE submit | `internal_billing.py` after submit **or** `Journal Entry` hook filtered by remark/template | Yes (per job) | Yes (per job) |

Errors should **log** and **msgprint** (orange) like today’s accrual reversal, without blocking SI/PI/JE submit unless product requires strict coupling.

---

## 8. Data and testing notes

- **Unit tests**: scenarios with item-tagged recognition GL, multi-line SI/PI, partial reversal, second PI completing accrual, intercompany pair with shared JCN model, internal JV with two internal jobs.
- **Migration**: no schema change strictly required for v1 if reversal references stored in existing `wip_adjustment_journal_entry` / `accrual_adjustment_journal_entry` or new optional **child table** “Recognition Reversal Log” on job (voucher_type, voucher_no, amount_wip, amount_accrual).

---


<!-- wiki-field-reference:start -->

## Complete field reference

_Design doc; implementation fields are on invoices and jobs. See:_

- [Logistics Settings](welcome/logistics-settings)
- [Air Shipment](welcome/air-shipment), [Sea Shipment](welcome/sea-shipment), [Transport Job](welcome/transport-job), [Declaration](welcome/declaration), [General Job](welcome/general-job)

<!-- wiki-field-reference:end -->

## 9. Related documentation and code

- [Internal and Intercompany Billing](welcome/internal-and-intercompany-billing) — billing mechanisms and triggers.
- [Proforma GL entries / job profitability](welcome/proforma-gl-entries) — how WIP and accrual appear in GL.
- Code: `logistics/invoice_integration/accrual_reversal.py`, `logistics/invoice_integration/lifecycle.py`, `logistics/invoice_integration/invoice_hooks.py`, `logistics/job_management/recognition_engine.py`, `logistics/billing/internal_billing.py`, `logistics/intercompany/intercompany_invoice.py`.

---

## 10. Summary

| Source document | Posted in | Reverse WIP (per line / item when possible) | Reverse cost accrual (per line / item when possible) |
|-----------------|-----------|---------------------------------------------|------------------------------------------------------|
| Customer SI (job/shipment) | Billing / job company | Yes | No |
| Customer PI (job/shipment) | Job company | No | Yes (existing) |
| Intercompany SI | Operating company | Yes | No |
| Intercompany PI | Billing company | No | Yes (same as PI) |
| Internal billing JE | Billing company (same co. as main) | Yes (per internal job) | Yes (per internal job; policy accrual accounts) |

This yields a single conceptual model: **real revenue posting** (SI or internal revenue side of JV) drives **WIP reversal**; **real cost posting** (PI or policy accrual consumption) drives **accrual reversal**, extended consistently to **intercompany** and **internal billing**.
