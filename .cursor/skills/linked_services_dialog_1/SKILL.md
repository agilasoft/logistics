---
name: linked-services-dialog-1
description: >-
  Visual design spec for the Manage Linked Services dialog (linked_services_dialog_1).
  Use when redesigning or rebuilding Time Sensitive Case / Linked Services manage dialogs
  to match this saved mockup.
---

# linked_services_dialog_1

Canonical UI for **Manage Linked Services** (toolbar → Services on manage DocTypes).

Used by Time Sensitive Case, Sales Quote, and Change Request via `logistics.show_linked_services_dialog`.

## Reference

See [reference.png](reference.png) in this folder.

## Structure

1. **Header** — title `Manage Linked Services`, subtitle `{parentLabel} {name}`, close (X).
2. **Add Linked Service card** — Service Type select + dark **+ Add Service**; hint under the field.
3. **Linked Services card** — count badge; rows with module icon, type, `IJ-…` link, job pill, **Edit** + **Remove** outlined icon buttons. Selected row uses light-blue fill + border.
4. **Edit Linked Service card** (appears on Edit) — meta `Type · IJ-…`, **Open full form**, type-aware field grid (3 columns), **Cancel** / **Save Changes**.
5. Services tab on the parent form stays a **read-only** live view.

## Visual tokens

| Token | Value |
|-------|--------|
| Dialog width | ~760px |
| Selected row | bg `#eff6ff`, border `#93c5fd` |
| Add Service button | near-black `#111827` |
| Save Changes | blue `#2563eb` / `#1d4ed8` |
| Remove / Edit | outlined square icon buttons (remove turns red on hover) |
| Cards | light border, radius ~8–12px |
| Service Type (edit) | read-only with lock icon |

## Behaviour (product)

- **Add** creates a new owned Linked Service for the selected type, then opens the edit panel for it.
- **Multiple services per type allowed** (e.g. international + domestic Sea).
- **Edit** loads quick fields in-dialog (Air/Sea parties & ports, etc.); **Open full form** for everything else.
- **Save Changes** persists via Linked Service dialog APIs; list + parent form refresh.
- **Remove** confirms, then deletes owned / unlinks shared; closes edit if that row was open.
- Switching edit target with dirty fields prompts to discard.

## Implementation

- Shared JS: `logistics/public/js/linked_services_dialog.js` → `logistics.show_linked_services_dialog(frm, options)`
- TSC wrapper: `logistics/public/js/time_sensitive_services_dialog.js`
- Change Request: toolbar Services button in `change_request.js` (same shared dialog)
- CSS: `logistics/public/css/linked_services_dialog.css` (class prefix `lsd1-`)
- Edit APIs: `linked_service.get_dialog_edit_payload` / `linked_service.update_dialog_edit`
