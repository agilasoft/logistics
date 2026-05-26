# Special Project: Site Materials

**Status:** Implemented  
**Last updated:** 2026-05-25  
**Context:** [GitHub issue #942](https://github.com/agilasoft/logistics/issues/942), programme site inventory and partial shipment creation from Lifecycle.

The legacy **Programme Cargo** child table has been folded into **Site Materials**; an `include_on_create` flag on each Site Material row decides whether the row is a tracked requirement or an always-along package template.

---

## 1. Purpose

Track **required vs on-site** quantities per material line on a Special Project, record **receipts** with **source job** and **container** provenance, and pre-fill **packages** on Transport/Air/Sea/Inbound documents when creating from **Create → Booking / Order**. Always-along packages (tool kits, dunnage, DG kits) are kept on the same grid via the `include_on_create` flag.

---

## 2. Data model

| Child table | Role |
|-------------|------|
| `site_materials` (`Special Project Site Material`) | One row per material. Tracked requirements (`include_on_create = 0`) carry `qty_required`, computed `qty_on_site`, `qty_short`. Always-along rows (`include_on_create = 1`) carry the same package fields (HS code, dimensions, weight, volume, DG flag, no_of_packs) but are excluded from the requirement ledger. |
| `site_receipts` (`Special Project Site Receipt`) | Movement: `qty_received`, `source_job_type` / `source_job_no`, `container_no`, idempotency keys. |

**Balance rules** (`special_project_site_materials.py`):

```
For each row in site_materials:
  if include_on_create == 1:
      qty_on_site = qty_short = 0   # off-ledger
      continue
  qty_on_site = SUM(posted receipt.qty_received) per row / warehouse_item / commodity / description
  qty_short   = max(qty_required - qty_on_site, 0)
```

`qty_required > 0` is enforced for every row, including always-along (typically `1`).

---

## 3. User flows

### 3.1 Programme setup

1. Add **Site Materials** rows (or seed from Sales Quote `project_products`). Tick **Include on Create** on rows that should auto-ride every booking.
2. Optional: **Receipts** for stock already on site (manual, with job/container if known).
3. **Lifecycle** rows for Transport / Air / Sea.

### 3.2 Create Transport with Item A × 50 only

1. **Create → Booking / Order** on Transport lifecycle row.
2. **Shipment lines** prompt lists only tracked requirements; user types qty (e.g. Item A = 50; others 0).
3. TRO created with **Packages** rows for the picked qty (dimensions/weight/HS prefilled from each matched requirement row) plus one row per always-along site material.
4. On **Submit** TRO → posted **site receipts** on Special Project (+50 for Item A, tagged TRO + container). Always-along packages are skipped.

### 3.3 Example: 900 required, 200 on site, truck with 200

| Step | Item A |
|------|--------|
| Required | 900 |
| Receipts before truck | 200 (past jobs) |
| This TRO packages | 200 |
| After TRO submit | on site 400, short 500 |

Two trucks (300 + 200) produce two receipt rows with different `source_job_no`.

---

## 4. Integration points

| Trigger | Behaviour |
|---------|-----------|
| Special Project `validate` | `validate_site_materials` enforces `qty_required > 0` and identification per row, then `sync_site_material_balances` (skips `include_on_create` rows). |
| Sales Quote → Special Project | `seed_site_materials_from_sales_quote`. |
| `create_booking_or_order_from_special_project` | `apply_shipment_lines_to_target` (carries dimensions from the matched requirement row); `copy_always_along_site_materials_to_target` for `include_on_create = 1` rows. |
| `get_site_materials_for_shipment_picker` | Filters out `include_on_create = 1` rows so they cannot be picked. |
| Transport Order `on_submit` | `post_site_receipts_from_transport_order`; packages whose matched site material is `include_on_create = 1` are skipped. |
| Transport Order `on_cancel` | `cancel_receipts_for_transport_order`. |
| Project Order `on_submit` | `post_site_receipts_from_project_doc`; reads the order's `materials_received` table (warehouse_item + qty_received), resolves parent SP via `special_project`. |
| Project Order `on_cancel` | `cancel_receipts_for_project_doc`. |
| Project Job `on_submit` | `post_site_receipts_from_project_doc`; same behaviour as Project Order, reads `materials_received`. |
| Project Job `on_cancel` | `cancel_receipts_for_project_doc`. |

---

## 5. Code references

| Area | Path |
|------|------|
| Core logic | `logistics/special_projects/special_project_site_materials.py` |
| Create booking/order | `logistics/special_projects/special_project_booking_creation.py` |
| Booking dialog | `logistics/public/js/special_project_booking_dialog.js` |
| Form JS | `logistics/special_projects/doctype/special_project/special_project.js` |
| Tests | `logistics/special_projects/test_special_project_site_materials.py` |
| Migration patch | `logistics/patches/v1_0_merge_programme_cargo_into_site_materials.py` |

---

## 6. Out of scope (follow-ups)

- Sea/Air Shipment auto-receipt on submit  
- Inbound Order receipt posting  
- ERPNext stock ledger sync  
- Exhibit programme parity  
