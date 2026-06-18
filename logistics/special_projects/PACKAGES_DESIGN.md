# Special Project: Packages & Deliveries

**Status:** Implemented
**Last updated:** 2026-06-02
**Context:** [GitHub issue #942](https://github.com/agilasoft/agilasoft/logistics/issues/942), programme site inventory, partial shipment creation from Lifecycle, per-stage delivery funnel.

The legacy **Programme Cargo** and **Site Materials** child tables have been folded into a single **Packages** table; an `include_on_create` flag on each row decides whether the row is a tracked requirement or an always-along package template. **Deliveries** (formerly Site Receipts) record movement on site, tagged by **Lifecycle Stage** so the Fulfillment tab can render a per-stage delivery funnel.

---

## 1. Purpose

Track **required vs delivered** quantities per package line on a Special Project, record **deliveries** with **source job**, **container**, and **lifecycle stage** provenance, and pre-fill **packages** on Transport/Air/Sea/Inbound documents when creating from **Create → Booking / Order**. Always-along packages (tool kits, dunnage, DG kits) are kept on the same grid via the `include_on_create` flag.

---

## 2. Data model

| Child table | Role |
|-------------|------|
| `packages` (`Special Project Package`) | One row per item/part to deliver. Tracked requirements (`include_on_create = 0`) carry `qty_required`, computed `qty_on_site` (Delivered), `qty_short` (Remaining). Always-along rows (`include_on_create = 1`) carry the same package fields (HS code, dimensions, weight, volume, DG flag, no_of_packs) but are excluded from the requirement ledger. |
| `deliveries` (`Special Project Site Receipt`) | Movement: `qty_received`, `lifecycle_stage`, `source_job_type` / `source_job_no`, `container_no`, idempotency keys. |

**Balance rules** (`special_project_packages.py`):

```
For each row in packages:
  if include_on_create == 1:
      qty_on_site = qty_short = 0   # off-ledger
      continue
  qty_on_site = SUM(posted delivery.qty_received) where delivery.package_row = row.idx
  (legacy fallback by warehouse_item / commodity / description only when exactly one tracked row shares that key)
  qty_short   = max(qty_required - qty_on_site, 0)
```

**Package row identity:** Each tracked Packages line has a stable 1-based `idx` (shown as “Line N” in the Shipment lines dialog). When creating bookings/orders, the dialog sends `package_row`; operational child tables (Transport Order Package, Air/Sea Booking Packages, Air Shipment Packages, Sea Freight Packages, Project Order/Job Package) store it. On submit, delivery receipts use that index so duplicate warehouse items on the programme do not share delivered quantities. If multiple programme rows match the same item and `package_row` is missing on the operational line, posting throws with an ambiguous-package error.

`qty_required > 0` is enforced for every row, including always-along (typically `1`).

The **Fulfillment summary** is a row-per-package, column-per-Lifecycle-Stage funnel. Each cell shows the qty delivered in that stage and a fill bar proportional to required qty.

---

## 3. User flows

### 3.1 Programme setup

1. Add **Packages** rows (or seed from Sales Quote `project_products`). Tick **Include on Create** on rows that should auto-ride every booking.
2. **Deliveries** are **read-only** on the Special Project form — posted automatically when operational jobs submit or cancel (Transport Order, Air/Sea Shipment, Project Job, etc.). Do not add manual delivery rows on the programme.
3. **Lifecycle** rows for Transport / Air / Sea (optionally seeded from a **Lifecycle Template**).

### 3.2 Create Transport with Item A × 50 only

1. **Create → Booking / Order** on Transport lifecycle row.
2. **Shipment lines** prompt lists only tracked package requirements; user types qty (e.g. Item A = 50; others 0).
3. TRO created with **Packages** rows for the picked qty (dimensions/weight/HS prefilled from each matched package row) plus one row per always-along package.
4. On **Submit** TRO → posted **deliveries** on Special Project (+50 for Item A, tagged TRO + container + originating lifecycle stage). Always-along packages are skipped.

### 3.3 Example: 900 required, 200 delivered, truck with 200

| Step | Item A |
|------|--------|
| Required | 900 |
| Deliveries before truck | 200 (past jobs) |
| This TRO packages | 200 |
| After TRO submit | delivered 400, remaining 500 |

Two trucks (300 + 200) produce two delivery rows with different `source_job_no` and potentially different `lifecycle_stage`.

---

## 4. Integration points

| Trigger | Behaviour |
|---------|-----------|
| Special Project `validate` | `validate_packages` enforces `qty_required > 0`, identification per row, and autofills `lifecycle_stage` on deliveries; `validate_deliveries_read_only` blocks manual add/edit/delete on `deliveries` unless `flags.ignore_delivery_validation` (system post helpers only); then `sync_package_delivery_balances` (skips `include_on_create` rows). |
| Sales Quote → Special Project | `seed_packages_from_sales_quote`. |
| `create_booking_or_order_from_special_project` | `apply_shipment_lines_to_target` (carries dimensions from the matched package row); `copy_always_along_packages_to_target` for `include_on_create = 1` rows. **Project Order** is included — shipment-lines dialog prefills `packages` on the order. |
| `get_packages_for_shipment_picker` | Filters out `include_on_create = 1` rows; returns `package_row`, site, reference_no for dialog labelling. |
| Operational package child tables | `package_row` (Int) links each line to the parent Special Project Packages row. |
| Transport Order `on_submit` | `post_site_receipts_from_transport_order`; packages whose matched site material is `include_on_create = 1` are skipped. Delivery rows are tagged with the lifecycle stage from the originating Lifecycle Job. |
| Transport Order `on_cancel` | `cancel_receipts_for_transport_order`. |
| Air / Sea Shipment `on_submit` | `post_site_receipts_from_freight_shipment` (via the `on_freight_shipment_submit` doc-events bridge); resolves the parent SP from `project`, then folds the Shipment's `packages` rows into Deliveries. The Lifecycle Job row references the Booking, so lifecycle stage is looked up first against the Shipment and then falls back to the linked `air_booking` / `sea_booking`. Air Booking / Sea Booking submission is purely planning and does **not** post receipts — only the executing Shipment does. |
| Air / Sea Shipment `on_cancel` | `cancel_receipts_for_freight_shipment` (via the `on_freight_shipment_cancel` doc-events bridge). |
| Project Job `on_submit` | `post_site_receipts_from_project_doc`; reads **`packages`** child table (preferred) or legacy `materials_received`, resolves parent SP via `special_project`. Project Order is a planning document and does **not** post receipts — only its derived Project Job does, to keep the SP's Deliveries table single-sourced. |
| Project Order create from lifecycle | Shipment-lines dialog + always-along packages copied to **`packages`** on Project Order; charges copied respecting programme lifecycle tags and allocation %. |
| Project Job create from order | **`packages`** copied from Project Order to Project Job. |
| Project Job `on_cancel` | `cancel_receipts_for_project_doc`. |

---

## 5. Code references

| Area | Path |
|------|------|
| Core logic | `logistics/special_projects/special_project_packages.py` |
| Create booking/order | `logistics/special_projects/special_project_booking_creation.py` |
| Booking dialog | `logistics/public/js/special_project_booking_dialog.js` |
| Form JS | `logistics/special_projects/doctype/special_project/special_project.js` |
| Funnel HTML | `logistics/special_projects/doctype/special_project/special_project.py` (`get_packages_summary_html`) |
| Tests | `logistics/special_projects/test_special_project_packages.py`, `test_deliveries_read_only.py` |
| Rename patch | `logistics/patches/v1_1_rename_special_project_site_material_to_package.py` |
| Programme-cargo merge (historical) | `logistics/patches/v1_0_merge_programme_cargo_into_site_materials.py` |

---

## 6. Out of scope (follow-ups)

- Inbound Order receipt posting
- ERPNext stock ledger sync
- Exhibit programme parity
