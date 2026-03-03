# Booking vs Shipment Doctype Alignment Report

**Generated:** Comparison of Air Booking vs Air Shipment and Sea Booking vs Sea Shipment for field and structure alignment.

**Alignment implemented (patch `v1_0_align_booking_shipment_fields`):** Sea `good_value` → `goods_value`; Sea Booking `chargeable_weight` → `chargeable`; Sea `notify_to_party`/`notify_to_address` → `notify_party`/`notify_party_address`; added `atd`/`ata` to both Bookings; Sea Booking `service_level` options → Logistics Service Level.

---

## 1. Executive Summary

| Aspect | Air Booking ↔ Air Shipment | Sea Booking ↔ Sea Shipment |
|--------|----------------------------|----------------------------|
| **Parent link** | Booking has no parent; Shipment has `air_booking` | Booking has no parent; Shipment has `sea_booking` |
| **Tabs / UX** | Shipment adds Dashboard, Milestones, Billing, Recognition, Customs, etc. | Shipment adds Dashboard, Milestones, Invoice monitoring, Recognition, SLA, Sustainability, Delays/Penalties |
| **Actual dates** | Shipment has `atd`, `ata`; Booking has only `etd`, `eta` | Same: Shipment has `atd`, `ata` |
| **Goods value** | Both use `goods_value` | Booking: `good_value`; Shipment: `good_value` (align name to `goods_value`) |
| **Chargeable weight** | Both use `chargeable` | Booking: `chargeable_weight`; Shipment: `chargeable` (align name) |
| **Notify party** | Both use `notify_party`, `notify_party_address` | Booking: `notify_to_party`, `notify_to_address`; Shipment: same (different from Air) |
| **Charge table** | Air Booking Charges ↔ Air Shipment Charges (same pattern: item_code, rate, etc.) | Sea Booking Charges ↔ Sea Freight Charges (Sea uses charge_item, selling_amount vs Air item_code, rate) |
| **Service level** | Booking: `Logistics Service Level`; Shipment: same | Booking: `Service Level Agreement`; Shipment: `Logistics Service Level` (option mismatch) |

---

## 2. Air: Booking vs Shipment

### 2.1 Fields only on Air Booking (missing on Shipment for comparison)

- `quote_reference_section` (section; Shipment has `sales_quote` in different place)
- `volume_to_weight_factor_type`, `custom_volume_to_weight_divisor` (Booking has these; Shipment may have different placement or logic)
- `contacts_addresses` (tab/section name difference)

### 2.2 Fields only on Air Shipment (not on Booking)

| Field / area | Purpose |
|--------------|---------|
| `dashboard_tab`, `dashboard_html` | Dashboard |
| `milestones_tab`, `milestone_*` | Milestones |
| `transport_mode_column` | Layout |
| `air_booking` | Link to source booking |
| `atd`, `ata` | Actual departure/arrival dates |
| `master_details_section`, `master_awb` | Master AWB (shipment-level) |
| `excess_weight_volume` | Weight/volume excess |
| `contacts_and_addresses_tab` (naming) | Same concept as Booking addresses |
| `document_management_section`, `documents_html` | Documents UI |
| `billing_automation_section` | `auto_billing_enabled`, `billing_status`, `sales_invoice`, `billing_date`, `billing_amount`, `billing_currency` |
| `invoice_monitoring_section` | `purchase_invoice`, `fully_invoiced`, `date_fully_invoiced`, `fully_paid`, `date_fully_paid`, lifecycle dates |
| `revenue_section` | Revenue recognition fields |
| `recognition_section` | WIP/accrual recognition (estimated_revenue, wip_*, accrual_*, etc.) |
| `customs_section` | Customs declaration, license, permit, broker, duty, tax, clearance date |
| `temperature_section` | Temperature control and cold chain |
| `insurance_section` | Insurance provider, policy, value, claim fields |
| `tracking_section` | Tracking provider, number, URL, status |
| `sustainability_section` | Carbon footprint, fuel, notes |
| `sla_section` | SLA target, status, notes |
| `eawb_section`, `iata_section` | eAWB, IATA messaging |
| `casslink_section`, `tact_section` | CASS/TACT billing |
| `connections_tab` | Connections |

**Alignment:** Booking is the “quote/order” stage; Shipment is the “execution” stage. Optional alignment: add `atd`/`ata` to Booking (for actuals when known) and ensure same core party/address/contact field names.

### 2.3 Naming alignment (Air)

- **Goods value:** Both use `goods_value` — aligned.
- **Chargeable:** Both use `chargeable` — aligned.
- **Notify:** Both use `notify_party`, `notify_party_address` — aligned.
- **Section label:** Booking “Booking Details”, Shipment “Details” + `section_break_main` — consider same section label.

---

## 3. Sea: Booking vs Shipment

### 3.1 Fields only on Sea Booking (not on Shipment for same concept)

- No major structural gaps; Shipment has more sections (see below).
- **Naming:** `good_value` (Booking) vs `good_value` (Shipment) — both use `good_value` but should align with Air as `goods_value`.
- **Chargeable:** Booking uses `chargeable_weight`; Shipment uses `chargeable` — recommend one name (e.g. `chargeable`) for code and JSON.

### 3.2 Fields only on Sea Shipment (not on Booking)

| Field / area | Purpose |
|--------------|---------|
| `dashboard_tab`, `dashboard_html`, `milestones_*` | Dashboard and milestones |
| `sea_booking` | Link to source booking |
| `atd`, `ata` | Actual dates |
| `vessel`, `voyage_no`, `container_type` | Voyage/container (shipment-level) |
| `excess_weight_volume` | Weight/volume excess |
| `handling_branch`, `handling_department`, `job_description`, `quote_no` | Operations and quote ref |
| `documents_html` | Documents UI |
| `invoice_monitoring_section` | sales_invoice, purchase_invoice, lifecycle dates |
| `recognition_section` | WIP/accrual (estimated_revenue, wip_*, accrual_*, etc.) |
| `notes_tab` / `notes_section` | `external_notes`, `internal_notes`, `client_notes` |
| `sla_section` | SLA target, status, notes |
| `sustainability_section` | Carbon, fuel, notes |
| `delay_alerts_section` | has_delays, delay_count, last_delay_check, delay_alert_sent |
| `penalty_alerts_section` | has_penalties, detention_days, demurrage_days, free_time_days, penalty_alert_sent, last_penalty_check, estimated_penalty_amount |
| `addresses_tab`, `bill_of_lading_addresses_section`, `shipping_contacts_section` | Address/contact grouping (same data as Booking, different layout names) |
| `connections_tab` | Connections |

### 3.3 Naming alignment (Sea)

| Concept | Sea Booking | Sea Shipment | Recommendation |
|---------|-------------|---------------|-----------------|
| Goods value | `good_value` | `good_value` | Align with Air: rename to `goods_value` in both Sea doctypes. |
| Chargeable weight | `chargeable_weight` | `chargeable` | Use one name; prefer `chargeable` (matches Air and Shipment code). Add `chargeable` to Booking or map `chargeable_weight` → `chargeable` on convert. |
| Notify party | `notify_to_party`, `notify_to_address` | `notify_to_party`, `notify_to_address` | Aligned between Sea B/S. Optionally align with Air: `notify_party`, `notify_party_address` for cross-mode consistency. |
| Service level link | `Service Level Agreement` | — (Shipment may use same or different) | Unify options: use one DocType (e.g. Logistics Service Level) for both Booking and Shipment. |

---

## 4. Charge Child Tables

### 4.1 Air: Air Booking Charges vs Air Shipment Charges

| Concept | Air Booking Charges | Air Shipment Charges | Aligned? |
|---------|---------------------|----------------------|----------|
| Item | `item_code`, `item_name` | `item_code`, `item_name` | Yes |
| Revenue amount | `rate`, `estimated_revenue` | `rate`, `estimated_revenue` | Yes |
| Currency | `currency` | `currency` | Yes |
| Cost | (concept only in some rows) | `unit_cost`, `estimated_cost`, `cost_*` | Shipment has full cost block |
| Bill To | — (patch adds `bill_to`) | `bill_to` | Yes (after patch) |
| Pay To | — (patch adds `pay_to`) | `pay_to` | Yes (after patch) |
| Calculation | `charge_basis`, `calculation_method`, etc. | `charge_basis`, `calculation_notes_*`, etc. | Largely same pattern |

**Alignment:** Structure is aligned. Ensure patch adds `bill_to` and `pay_to` to Air Booking Charges and that copy Booking → Shipment maps them.

### 4.2 Sea: Sea Booking Charges vs Sea Freight Charges (Sea Shipment)

| Concept | Sea Booking Charges | Sea Freight Charges (Shipment) | Aligned? |
|---------|---------------------|---------------------------------|----------|
| Item | `charge_item`, `charge_name` | `charge_item`, `charge_name` (from code) | Yes |
| Description | `charge_description` | `charge_description` | Yes |
| Revenue amount | `selling_amount`, `per_unit_rate` | `selling_amount` | Yes |
| Currency | `selling_currency` | `selling_currency` | Yes |
| Cost | `pay_to`, `buying_currency`, `buying_amount`, `cost_calc_type` | Same pattern | Yes |
| Bill To / Pay To | `bill_to`, `pay_to` | `bill_to`, `pay_to` | Yes |

**Naming vs Air:** Sea uses `charge_item` / `charge_name` / `selling_amount` / `selling_currency`; Air uses `item_code` / `item_name` / `rate` / `currency`. For cross-mode code (e.g. invoice from job), code already maps (e.g. `charge_item` → `item_code`, `selling_amount` → `rate`). Optional long-term alignment: standardise one set of names (e.g. item_code, rate, currency) across Air and Sea charge tables and map in one place.

---

## 5. Cross-Mode Consistency (Air vs Sea)

| Concept | Air Booking | Air Shipment | Sea Booking | Sea Shipment |
|---------|-------------|--------------|-------------|--------------|
| Goods value field | `goods_value` | `goods_value` | `good_value` | `good_value` |
| Chargeable field | `chargeable` | `chargeable` | `chargeable_weight` | `chargeable` |
| Notify party | `notify_party` | `notify_party` | `notify_to_party` | `notify_to_party` |
| Notify address | `notify_party_address` | `notify_party_address` | `notify_to_address` | `notify_to_address` |
| Charge table item | `item_code` | `item_code` | `charge_item` | `charge_item` |
| Charge table amount | `rate` | `rate` | `selling_amount` | `selling_amount` |
| Service level options | Logistics Service Level | Logistics Service Level | Service Level Agreement | — |

---

## 6. Recommendations for Alignment

### 6.1 High priority (field naming)

1. **Sea: `good_value` → `goods_value`**  
   - In Sea Booking and Sea Shipment (and Sea Freight Charges if present), rename `good_value` to `goods_value` for consistency with Air.  
   - Add a one-time migration/patch to copy data and update references.

2. **Sea: chargeable weight field name**  
   - Use a single field name for “chargeable weight”: prefer `chargeable` (as in Air and Sea Shipment).  
   - In Sea Booking: add `chargeable` and sync from `chargeable_weight`, or rename `chargeable_weight` to `chargeable` and update all references (Python/JS).

### 6.2 Medium priority (structure / UX)

3. **Actual dates on Booking**  
   - Add `atd` and `ata` to Air Booking and Sea Booking (optional, for when actuals are known before or at conversion).  
   - Ensure conversion Booking → Shipment copies `atd`/`ata` if present.

4. **Service level options**  
   - Unify Service Level: use one DocType (e.g. “Logistics Service Level”) for both Air and Sea, Booking and Shipment.  
   - Update Sea Booking’s `service_level` options and any validations.

5. **Notify party naming (cross-mode)**  
   - Decide standard: either `notify_party` / `notify_party_address` (Air) or `notify_to_party` / `notify_to_address` (Sea).  
   - If standardising to Air naming, add a patch to add `notify_party`/`notify_party_address` to Sea and migrate/copy from `notify_to_*`, then deprecate old names.

### 6.3 Lower priority (charge table standardisation)

6. **Charge table field names (Air vs Sea)**  
   - Keep current names for now; mapping in code is already in place.  
   - If desired later: adopt one convention (e.g. `item_code`, `item_name`, `rate`, `currency`) for both Air and Sea charge child tables and do a single mapping layer (e.g. in `charges_calculation` or invoice API) from standard names to DocType-specific names.

### 6.4 Documentation and code

7. **Document mapping**  
   - Keep a short doc (or table) of “Booking → Shipment” field mapping for Air and Sea (and charge table mapping) for developers and for future patches.  
   - Reference this report in that doc.

8. **Conversion scripts**  
   - Ensure Air Booking → Air Shipment and Sea Booking → Sea Shipment copy all aligned fields (including `bill_to`, `pay_to`, `atd`/`ata` when present, and chargeable/goods value under the chosen names).

---

## 7. Summary Table: What to Align

| # | Item | Booking | Shipment | Action |
|---|------|---------|----------|--------|
| 1 | Goods value | Sea: `good_value` | Sea: `good_value` | Rename both to `goods_value` |
| 2 | Chargeable | Sea B: `chargeable_weight` | Sea S: `chargeable` | Use `chargeable` in both; migrate Sea Booking |
| 3 | Actual dates | — | Both: `atd`, `ata` | Optionally add to both Bookings |
| 4 | Service level | Sea: SLA | Air: Logistics Service Level | Unify options (one DocType) |
| 5 | Notify fields | Air: notify_party; Sea: notify_to_party | Same per mode | Optionally standardise to one naming (e.g. notify_party) |
| 6 | Charge Bill To / Pay To | Patch adds to all charge tables | Already on Shipment charges | Ensure patch applied and copy on convert |

---

*End of report.*
