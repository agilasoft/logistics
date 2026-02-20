# Global Measurements Design — Logistics Module

## 1. Overview

This document defines a **global, uniform implementation of measurements** across the logistics module: a single set of dimension, volume, weight, and chargeable-weight fields, with **base UOMs** for internal conversion and **automatic conversion** when users change UOMs on transaction documents.

## 2. Goals

- **Uniform field set**: Same measurement field names and semantics everywhere (packages, order items, shipments, etc.).
- **Base UOMs**: Single base UOM for dimension, volume, and weight; all conversions can be expressed via base when needed.
- **Conversion on UOM change**: When a user changes the default/display UOM on a transaction (e.g. dimension UOM from CM to M), existing numeric values are converted so that **physical quantity is preserved** and only the unit of measure changes.

## 3. Uniform Field Set

Every doctype that carries measurements (e.g. package lines, order items, shipment lines) should expose the following **standard fields**.

### 3.1 Dimensions

| Field           | Type   | Description                                      |
|----------------|--------|--------------------------------------------------|
| `length`       | Float  | Length in `dimension_uom`                        |
| `width`        | Float  | Width in `dimension_uom`                         |
| `height`       | Float  | Height in `dimension_uom`                        |
| `dimension_uom`| Link (UOM) | Unit for length, width, height (single UOM for all three axes) |

**Note:** Using one `dimension_uom` for all three axes is the standard; optional per-axis UOMs (length_uom, width_uom, height_uom) can be added later if required.

### 3.2 Volume

| Field        | Type   | Description                          |
|-------------|--------|--------------------------------------|
| `volume`   | Float  | Volume in `volume_uom` (can be auto-calculated from dimensions) |
| `volume_uom`| Link (UOM) | Unit for volume (e.g. CBM, CFT)   |

### 3.3 Weight

| Field        | Type   | Description                    |
|-------------|--------|--------------------------------|
| `weight`   | Float  | Actual weight in `weight_uom`  |
| `weight_uom`| Link (UOM) | Unit for weight (e.g. KG, LB) |

### 3.4 Chargeable weight

| Field                  | Type   | Description                                      |
|------------------------|--------|--------------------------------------------------|
| `chargeable_weight`   | Float  | Chargeable weight in `chargeable_weight_uom`     |
| `chargeable_weight_uom`| Link (UOM) | Unit for chargeable weight (e.g. KG)          |

Chargeable weight is typically derived (e.g. max of actual weight and volume weight) but may be overridden; when present it should use this UOM.

### 3.5 Optional: base value fields (internal)

For reporting or aggregation in a single unit, the system may maintain **base** values. These are optional in the schema and can be computed on the fly if preferred.

| Concept            | Purpose                                                                 |
|--------------------|-------------------------------------------------------------------------|
| Base dimension UOM | All dimension conversions can go through this (e.g. CM or M).           |
| Base volume UOM    | All volume conversions can go through this (e.g. CBM).                  |
| Base weight UOM    | All weight (and chargeable weight) conversions can go through this (e.g. KG). |

Stored base fields (e.g. `length_base`, `volume_base`, `weight_base`) are **not** required on every child doctype if we always convert from display UOM to base when needed (e.g. in reports or roll-ups). The design only requires that **base UOMs are defined in settings** and used by conversion APIs.

## 4. Base UOMs and Default UOMs

### 4.1 Where to define

- **Logistics Settings** (single doctype) is the preferred place for **base UOMs** and **default display UOMs** used across the whole logistics module.
- Existing module-specific settings (Warehouse Settings, Transport Capacity Settings, Air/Sea Freight Settings) can **reference** these defaults or override them per sub-module if needed.

Proposed fields in **Logistics Settings** (or a dedicated **Logistics Measurement Settings** single doc):

| Field                    | Type   | Description |
|--------------------------|--------|-------------|
| `base_dimension_uom`     | Link (UOM) | Base UOM for length/width/height (e.g. CM). All dimension conversions use this as pivot. |
| `base_volume_uom`        | Link (UOM) | Base UOM for volume (e.g. CBM). |
| `base_weight_uom`        | Link (UOM) | Base UOM for weight and chargeable weight (e.g. KG). |
| `default_dimension_uom`  | Link (UOM) | Default for `dimension_uom` on new transaction lines. |
| `default_volume_uom`     | Link (UOM) | Default for `volume_uom` on new transaction lines. |
| `default_weight_uom`     | Link (UOM) | Default for `weight_uom` on new transaction lines. |
| `default_chargeable_weight_uom` | Link (UOM) | Default for `chargeable_weight_uom`. |

Default UOMs are used when creating new rows; base UOMs are used for conversion logic and reporting.

### 4.2 Conversion flow

- **User UOM → Base:** `value_base = value_display × factor(display_uom → base_uom)`
- **Base → User UOM:** `value_display = value_base × factor(base_uom → display_uom)`
- **When user changes UOM on a doc:**  
  Preserve physical quantity:  
  `value_new = value_old × factor(old_uom → new_uom)`  
  Then set `dimension_uom` / `volume_uom` / `weight_uom` / `chargeable_weight_uom` to the new selection.

## 5. Conversion when user changes UOM

### 5.1 Behaviour

When the user changes a UOM dropdown on a transaction document (e.g. `dimension_uom` from CM to M):

1. For each numeric field that uses that UOM (e.g. length, width, height for `dimension_uom`), convert the value so that the **physical quantity is unchanged**:
   - `new_value = old_value × conversion_factor(old_uom → new_uom)`
2. Set the UOM field to the new selection.
3. If volume is derived from dimensions, recalculate volume (in the new volume UOM if needed).
4. If chargeable weight is derived from volume/weight, recalculate it (in the new chargeable_weight_uom if needed).

Same logic applies when changing `volume_uom`, `weight_uom`, or `chargeable_weight_uom`: convert the corresponding numeric field(s) so that physical quantity is preserved.

### 5.2 Where to implement

- **Client (JS):** On change of `dimension_uom`, `volume_uom`, `weight_uom`, `chargeable_weight_uom` in forms (e.g. in table rows), call a shared helper that:
  - Reads current numeric values and old UOM (from field or from last known value).
  - Gets conversion factor (via server or a small client-side factor table for common UOMs).
  - Writes back converted values and new UOM.
- **Server (Python):** On validate (or before_save), if UOM fields were changed compared to DB, perform the same conversion so that stored values are consistent and physical quantity is preserved. This avoids relying solely on client-side logic.

### 5.3 Edge cases

- **New row:** No “old” UOM; use default UOMs from Logistics Settings (or module settings).
- **Missing conversion:** If a conversion factor is not defined (Dimension Volume UOM Conversion for dimension→volume; UOM Conversion Factor or logistics utility for weight/volume/dimension), either block the UOM change with a clear message or keep the previous UOM and warn.

## 6. Central conversion API

A single module should provide all conversion helpers so that base UOMs and conversion tables are used consistently.

Suggested location: **`logistics/utils/measurements.py`** (or extend existing `logistics/transport/capacity/uom_conversion.py` and `logistics/warehousing/utils/volume_conversion.py` behind a single facade).

### 6.1 Functions to expose

- `get_base_uoms()`  
  Returns `{ "dimension": base_dimension_uom, "volume": base_volume_uom, "weight": base_weight_uom }` from Logistics Settings.

- `get_default_uoms(company=None)`  
  Returns default dimension, volume, weight, chargeable_weight UOMs (from Logistics Settings and optionally company-specific overrides).

- `convert_dimension(value, from_uom, to_uom, company=None)`  
  Convert a single dimension value (length/width/height). Use base UOM as pivot if needed.

- `convert_volume(value, from_uom, to_uom, company=None)`  
  Convert volume. Use existing Dimension Volume UOM Conversion where applicable; otherwise linear dimension factors cubed or UOM Conversion Factor.

- `convert_weight(value, from_uom, to_uom, company=None)`  
  Convert weight (and chargeable weight). Use UOM Conversion Factor and base weight UOM.

- `calculate_volume_from_dimensions(length, width, height, dimension_uom, volume_uom, company=None)`  
  Already exists in warehousing/transport; ensure it uses base UOMs and the central conversion API where appropriate.

- `convert_measurements_to_uom(doc, uom_type, new_uom)`  
  Given a doc (or dict) with measurement fields and a UOM type (`dimension` | `volume` | `weight` | `chargeable_weight`), convert the relevant numeric fields to `new_uom` and set the corresponding UOM field. Used by server-side validation and by client-triggered logic.

### 6.2 Conversion factor sources (no hardcoded fallbacks)

**All conversion factors must be defined in the database.** The logistics module does **not** use any hardcoded UOM conversion fallbacks. If a conversion is missing, the API raises a clear error and the user must add the corresponding record.

- **Dimension ↔ dimension:** **UOM Conversion Factor** (Setup). No hardcoded factors; missing conversions raise an error.
- **Dimension (cubic) ↔ volume:** **Dimension Volume UOM Conversion** (Warehousing). No hardcoded factors; volume-from-dimensions requires this table (and the Warehousing module) or raises.
- **Volume ↔ volume:** **UOM Conversion Factor** (Setup). No hardcoded factors.
- **Weight ↔ weight:** **UOM Conversion Factor** (Setup). No hardcoded factors.

All conversions should be expressible via base UOM (e.g. display → base → display) so that only one set of factors (each UOM ↔ base) is required if desired. Implementations must not fall back to literal constants or in-code factor tables.

## 7. Applying the uniform field set to doctypes

### 7.1 Option A: Custom Field Group (recommended)

- Create a **Custom Field Group** (e.g. “Logistics Measurements”) containing the full set of fields:
  - length, width, height, dimension_uom
  - volume, volume_uom
  - weight, weight_uom
  - chargeable_weight, chargeable_weight_uom
- Add this field group to every child doctype that needs measurements (e.g. Transport Order Package, Transport Job Package, Inbound Order Item, VAS Order Item, Air Booking Packages, Sea Booking Packages, etc.).
- Ensures one definition, one place to update labels/options, and consistent behaviour.

### 7.2 Option B: Per-doctype fields

- Add the same fields explicitly to each doctype JSON. More duplication but no dependency on custom field group.

### 7.3 Backward compatibility

- Doctypes that already have a subset (e.g. only `dimension_uom` and no `volume_uom`) should be extended to the full set; existing fields can be renamed or retained with mapping to the standard names in the conversion API.
- Existing behaviour (e.g. volume calculated from dimensions, chargeable weight from weight/volume) should remain; the new layer only unifies field names and UOM handling.

## 8. Doctypes to align (examples)

- Transport: **Transport Order Package**, **Transport Job Package**
- Warehousing: **Inbound Order Item**, **Release Order Item**, **Transfer Order Item**, **VAS Order Item**, **Stocktake Order Item**, **Warehouse Job Item**, **Warehouse Item**, etc.
- Air: **Air Booking Packages**, consolidation/shipment package tables
- Sea: **Sea Booking Packages**, **Sea Consolidation Packages**, etc.
- Pricing/Charges: Any child that has weight/volume (e.g. **Transport Job Charges**, **Sales Quote** lines) should use the same UOM and base UOM rules.

Each of these should eventually expose the uniform fields and use the central conversion API when UOMs change or when aggregating (e.g. total weight in base UOM).

## 9. Summary

| Item | Decision |
|------|----------|
| **Uniform fields** | length, width, height, dimension_uom; volume, volume_uom; weight, weight_uom; chargeable_weight, chargeable_weight_uom |
| **Base UOMs** | Stored in Logistics Settings: base_dimension_uom, base_volume_uom, base_weight_uom; used as pivot for all conversions |
| **Default UOMs** | default_dimension_uom, default_volume_uom, default_weight_uom, default_chargeable_weight_uom in Logistics Settings (or overridden per module) |
| **On UOM change** | Convert numeric values so physical quantity is preserved; implement on client and server |
| **Conversion API** | Central module (e.g. `logistics/utils/measurements.py`) with get_base_uoms, get_default_uoms, convert_* , convert_measurements_to_uom |
| **Field reuse** | Custom Field Group “Logistics Measurements” applied to all measurement-bearing child doctypes |
| **No hardcoded fallbacks** | All UOM conversion factors must come from **UOM Conversion Factor** (Setup) and **Dimension Volume UOM Conversion** (Warehousing). Missing conversions raise an error; no in-code factor tables or literal constants. |

## 10. Implemented doctypes (uniform fields + UOM conversion)

The following doctypes have the full uniform measurement field set and client/server UOM conversion.

### Packages (transport, air, sea)

| Doctype | Parent | Child table field | Notes |
|--------|--------|--------------------|-------|
| **Transport Order Package** | Transport Order | packages | volume_uom, weight_uom, chargeable_weight, chargeable_weight_uom added |
| **Transport Job Package** | Transport Job | packages | chargeable_weight, chargeable_weight_uom added |
| **Air Booking Packages** | Air Booking | packages | Full set: dimension_uom, length, width, height, volume_uom, weight_uom, chargeable_weight, chargeable_weight_uom |
| **Sea Booking Packages** | Sea Booking | packages | Same full set |
| **Air Shipment Packages** | Air Shipment | packages | Same full set |
| **Sea Freight Packages** | Sea Shipment | packages | Same full set |

### Warehouse order and job items

| Doctype | Parent | Child table field | Notes |
|--------|--------|--------------------|-------|
| **Inbound Order Item** | Inbound Order | items | chargeable_weight, chargeable_weight_uom added (already had dimension, volume, weight UOMs) |
| **Release Order Item** | Release Order | items | Same |
| **Transfer Order Item** | Transfer Order | items | Same |
| **VAS Order Item** | VAS Order | items | Same |
| **Stocktake Order Item** | Stocktake Order | items | Same |
| **Warehouse Job Item** | Warehouse Job | items | Same |
| **Warehouse Job Order Items** | Warehouse Job | (order items) | Same |
| **Warehouse Item** | (standalone) | — | chargeable_weight, chargeable_weight_uom added |

### Customs

| Doctype | Parent | Child table field | Notes |
|--------|--------|--------------------|-------|
| **Declaration Commodity** | Declaration | commodities | chargeable_weight, chargeable_weight_uom added (already had weight_uom, volume_uom) |

### Client and server behaviour

- **Client:** `logistics/public/js/measurements_uom_conversion.js` (included via `app_include_js`) registers `dimension_uom`, `volume_uom`, `weight_uom`, `chargeable_weight_uom` handlers for all of the above child doctypes. On UOM change, values are converted so physical quantity is preserved.
- **Server:** Parent `validate()` calls `apply_measurement_uom_conversion_to_children(doc, child_table_fieldname, company)` so UOM changes (e.g. after import) are converted before save.
- **Transport Order** and **Transport Job** form refresh set `_prev_*` UOM on package rows for reliable first-change conversion; other parents rely on the same in-row logic (first change stores new UOM as prev).

This design yields a single, consistent way to handle dimensions, volume, weight, and chargeable weight across the logistics module, with clear base UOMs and predictable conversion when users change UOMs on transaction documents.
