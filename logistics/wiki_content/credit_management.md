# Credit management (logistics-wide)

This document describes the **CargoNext logistics credit control** feature: how customer credit state is represented, how **Logistics Settings** configures enforcement, and how **create / save / submit / print** are blocked consistently across modules.

## Goals

- One place to decide **which DocTypes** are subject to credit holds and **which actions** are blocked (new document, save, submit, print/PDF).
- Combine **manual** credit classification on the Customer with **automatic** signals from ERPNext (**credit limit**) and **overdue Sales Invoices** (payment terms deviation).
- Apply consistently to operational documents that link a **Customer** (or equivalent party field—see below).

## Customer: Credit tab

Custom fields on **Customer** (synced from the logistics app custom fixture):

| Field | Purpose |
|--------|---------|
| **Credit** (tab) | Groups logistics credit fields. |
| **Credit Status** (`logistics_credit_status`) | Select: **Good** (default), **Watch**, **On Hold**. Drives manual hold when enabled in settings. |

ERPNext’s own **Accounting** tab still holds **Payment Terms**, **Credit Limits** (per company), and **Credit Limit** on **Customer Group**—those feed the automated checks.

## Logistics Settings → Credit Control

Single DocType **Logistics Settings**, tab **Credit Control**.

### Master switch

- **Enable logistics credit control** — feature is off until this is checked.

### When is a customer “on hold”?

Any **enabled** condition below contributes; if at least one fires, the customer is on hold for enforcement:

1. **Manual status**  
   - **Hold when Credit Status is On Hold** (default on).  
   - **Hold when Credit Status is Watch** (default off)—use for stricter accounts.

2. **Credit limit deviation**  
   - **Hold when credit limit is exceeded** (default on).  
   - Uses ERPNext’s `get_credit_limit` and `get_customer_outstanding` for the **Customer** and **Company** resolved from the document (same conceptual basis as Selling).  
   - If **Company** is empty on the document, the user’s default company is used; if still missing, limit checks are skipped.

3. **Payment terms deviation**  
   - **Hold on payment terms deviation** (default on).  
   - **Payment terms grace (days)** extends the due date threshold (due date must be **before** `today − grace` to count).  
   - Implementation: any **submitted Sales Invoice** for that customer and company with **outstanding_amount > 0** and **due_date** before the cutoff.

### Per-doctype rules (child table)

**Per-doctype actions** (`Logistics Settings Credit Rule`):

| Column | Meaning |
|--------|---------|
| **DocType** | Target document type (only listed types are enforced). |
| **Block new documents** | `before_insert` — block creation. |
| **Block updates (save)** | `validate` on existing rows — block saves. |
| **Block submit** | `before_submit`. |
| **Block print / PDF** | Enforced by patching Frappe’s `validate_print_permission` (in `printview` and `print_format`). This is required because core print allows access if the user has **either** read **or** print—blocking only the print permission check is not enough. |

Each flag is independent (e.g. allow save but block submit).

### Bypass

- **Bypass role** — users with this role skip all credit blocks (optional). **Administrator** always bypasses.

### Server-side escape hatch

- Set `doc.flags.skip_credit_control = True` before save/submit in trusted server code only (integrations, controlled migrations).

## Which documents are covered?

Hooks are registered for a fixed list of **CREDIT_SUBJECT_DOCTYPES** in `logistics/utils/credit_management.py` (Sales Quote, air/sea bookings and shipments, transport, customs, warehousing jobs/orders, etc.).

**Important:** A DocType is only enforced if:

1. It appears in that list **and**
2. It has a row in **Per-doctype actions** **and**
3. **Enable logistics credit control** is on.

To extend coverage, add the DocType to `CREDIT_SUBJECT_DOCTYPES` and add a row in Logistics Settings.

## Resolving the “credit customer” on a document

The helper scans, in order, the first populated link field among:

`customer` → `local_customer` → `booking_party` → `controlling_party`

only if the field’s **options** are **Customer**.  
This matches most CargoNext logistics forms (e.g. **local_customer** / **booking_party** on bookings).

If none is set, no credit enforcement runs for that document.

## Flow (high level)

```mermaid
flowchart TD
  A[Document action: insert / save / submit / print] --> B{Credit control enabled?}
  B -->|no| Z[Allow]
  B -->|yes| C{DocType in rules table?}
  C -->|no| Z
  C -->|yes| D{User bypass role / Administrator?}
  D -->|yes| Z
  D -->|no| E[Resolve Customer + Company]
  E --> F{Any hold condition true?}
  F -->|no| Z
  F -->|yes| G{This action blocked in rule row?}
  G -->|no| Z
  G -->|yes| H[Throw or deny print]
```

## Relation to ERPNext Selling credit

- ERPNext may already block **Sales Order** / **Delivery Note** via credit controller and `check_credit_limit`. This feature is **orthogonal**: it targets **logistics DocTypes** and **print**, using the same customer master data.
- Align **Credit Controller** role in **Accounts Settings** with **Bypass role** in Logistics Settings if the same people should override both worlds.

## Implementation map

| Area | Location |
|------|-----------|
| Rules + settings fields | `logistics/logistics/doctype/logistics_settings/` |
| Child row DocType | `logistics/logistics/doctype/logistics_settings_credit_rule/` |
| Core logic + doctype list | `logistics/utils/credit_management.py` |
| Hooks (`doc_events` + print validator patch) | `logistics/hooks.py`, `logistics/utils/credit_management.py` |
| Customer tab + **Credit Status** | `logistics/logistics/custom/customer.json` |

## Operational checklist

1. Migrate / sync custom fields and DocTypes.  
2. Open **Logistics Settings → Credit Control**, enable the feature.  
3. Add **Per-doctype actions** rows for each DocType you want controlled; set checkboxes per action.  
4. Set **Credit Status** on customers as needed; maintain **Credit Limits** and **Payment Terms** in ERPNext as usual.  
5. Optionally set **Bypass role** for credit officers.

## Future extensions (not implemented)

- Email / PDF API hooks beyond standard print permission.  
- Portal / website routes (separate permission paths).  
- Weighting **Watch** as warning-only (toast) while still allowing save.  
- Using **Payment Schedule** lines instead of header **due_date** for finer overdue detection.
