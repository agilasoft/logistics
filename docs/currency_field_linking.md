# Currency fields in logistics — summary

This document describes **how many Currency fields exist in the logistics app**, **what their DocType JSON `options` are set to** (this is what Frappe uses for **number format** on the form), and **where the displayed currency comes from** when that value is missing.

Figures below are from a scan of **DocType** JSON files under [`logistics/`](../logistics/) (Currency `fieldtype` only).

## Snapshot

| Metric | Count |
|--------|------:|
| Total **Currency** fields (all DocTypes) | 433 |
| With **`options`** set | 99 |
| With **no** `options` (format uses boot default only) | 334 |

No logistics DocType uses the **`DocType:link_field:field`** form of `options` (e.g. `Company:company:default_currency`) on Currency fields — only **plain fieldnames** appear.

## `options` values used in logistics (DocType JSON)

These are the **only** `options` strings that appear on Currency fields today. The form resolves format by reading the **value of that field** from the **child row** `doc` first, then the **parent** `cur_frm.doc` (see Frappe resolution below).

| `options` value | # fields | Meaning / typical use |
|-----------------|----------|------------------------|
| **`currency`** | 56 | Selling / revenue side; field `currency` is usually **Link → Currency** on the same row or parent. |
| **`cost_currency`** | 39 | Cost / buy side; field `cost_currency` is usually **Link → Currency**. |
| **`inv_currency`** | 3 | Invoice-related amounts on **Declaration**, **Declaration Order**. |
| **`payment_currency`** | 1 | Payment amounts on **Declaration Order**. |

**DocTypes that use linked formatting (subset):**

- **`options: "currency"`** (26 DocTypes, 56 fields): includes **Air Booking Charges** (and weight/qty break child tables), **Sales Quote** charge lines and breaks, **Declaration** totals that reference `currency`, **Transport Order Charges**, **Sea/Air Shipment** charge breaks where configured, etc.
- **`options: "cost_currency"`** (8 DocTypes, 39 fields): **Air Booking Charges**, **Cost Sheet Charge**, **Change Request Charge**, **Sales Quote** transport/sea/air/charge lines, **Transport Order Charges**.

Many other DocTypes define **Currency** amounts but leave **`options` empty** — the UI then formats those amounts using **`frappe.boot.sysdefaults.currency`** (or **`USD`** if missing), **not** from a Link field on the document unless you add `options` or custom code.

## DocTypes with the most Currency fields **missing** `options`

These are the worst offenders (count = number of Currency fields with no `options` on that DocType):

- **Transport Job Charges** — 16  
- **Sea Consolidation Charges** — 16  
- **Air Shipment Charges** — 14  
- **Declaration Charges** — 14  
- **Sea Shipment Charges** — 14  
- **Declaration** — 13  
- **Declaration Order Charges** — 12  
- **Sales Quote Customs** — 12  
- **Sea Booking Charges** — 12  
- **Air Shipment** / **Sea Shipment** / **Transport Job** — 6–9 each (often WIP / revenue / cost rollups)  

Overall **82 DocTypes** have at least one Currency field without `options`.

## Where currency **format** is resolved (Frappe behaviour)

Relevant client code: `frappe.meta.get_field_currency(df, doc)` in Frappe’s `meta.js`.

1. **Start:** `frappe.boot.sysdefaults.currency` → else **`USD`**.  
2. **If** the Currency field has **`df.options`**:
   - **Plain name** (all logistics cases today): use **`doc[options]`**, else **`cur_frm.doc[options]`**, else stay at step 1.  
   - **Contains `:`** (not used in logistics Currency JSON today): resolve linked document and read a field from it.
3. **If** `options` is empty: **only** step 1 applies for standard form controls.

**Child tables:** for correct row currency, the **Link → Currency** field (`currency`, `cost_currency`, etc.) should exist on the **same row** as the Currency amounts, and those amounts should set **`"options": "currency"`** or **`"cost_currency"`** as appropriate.

## Custom UI (not from DocType `options`)

Some screens build HTML or dialogs and pass currency explicitly, for example:

- [`sales_quote.js`](../logistics/pricing_center/doctype/sales_quote/sales_quote.js) — `frappe.format(..., { fieldtype: "Currency", options: ch.cost_currency || "" })`
- [`charge_break_dialogs.js`](../logistics/public/js/charge_break_dialogs.js) — falls back `row.currency || row.cost_currency || "USD"`

Those paths **do not** read DocType JSON `options`; they use whatever object is passed in code.

## See also

- Frappe: `frappe/public/js/frappe/model/meta.js` — `get_field_currency`  
- Frappe: `frappe/public/js/frappe/form/controls/float.js` — `get_number_format` for Currency/Float with options  
