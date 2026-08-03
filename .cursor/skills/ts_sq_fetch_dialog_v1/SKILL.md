---
name: ts-sq-fetch-dialog-v1
description: >-
  Visual design spec for the free-edit Fetch dialog between Sales Quote and
  Time Sensitive Case (ts_sq_fetch_dialog_v1). Use when changing this fetch UX.
---

# ts_sq_fetch_dialog_v1

Canonical UI for **Fetch from Sales Quote** / **Fetch from Time Sensitive Case**.

## Reference

See [reference.png](reference.png) in this folder.

## Structure

1. **Header** — blue exchange icon, title, `SOURCE → TARGET`, close.
2. **Header Fields** — checkbox | Field | From Sales Quote | In Case (**editable**) | Direction | Action dropdown.
3. **Charges** — same columns; qty × rate editors; **Replace all charges from quote** link under table.
4. **Summary** — counts + safe/overwrite badge.
5. **Footer** — Cancel | hint pill | Apply Fetch.

**No Mode section.**

## Behaviour

- Every row is freely editable (no mode locking).
- Defaults: pre-check missing rows as Fill/Add; already-same → Skip.
- Direction per row: ← From Quote / → To Quote.
- Action dropdown: Fill / Replace / Skip (fields) or Add / Skip (charges).
- **Fetch all** shortcut (header + footer): selects every transferable row for the dialog direction and applies after confirm.
  - On Time Sensitive Case → all from Sales Quote
  - On Sales Quote → all from Time Sensitive Case
- Replace-all charges is an optional link, not a global mode.
- Apply sends selected rows + edited values + directions.

## Implementation

- JS: `logistics/public/js/ts_sq_fetch_dialog.js`
- CSS: `logistics/public/css/ts_sq_fetch_dialog.css` (`tsfd1-`)
- Python: `logistics.time_sensitive.ts_sq_fetch`
