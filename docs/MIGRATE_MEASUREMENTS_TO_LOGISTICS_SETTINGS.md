# Migration: All Measurement Settings to Logistics Settings and Conversion Logic to measurements.py

This document describes how to consolidate **all measurement-related settings** into **Logistics Settings** and **all conversion logic and algorithms** into **`logistics/utils/measurements.py`**, removing duplication across Transport, Warehousing, Air Freight, and Sea Freight.

**Implementation status:** Phases A and B are implemented. All conversion logic lives in `measurements.py`; `volume_conversion.py` and `uom_conversion.py` are thin wrappers. Run the optional patch once to copy existing UOM defaults into Logistics Settings:  
`bench --site <site> execute logistics.patches.v1_0_migrate_measurement_settings_to_logistics.execute`

---

## 1. Current State

### 1.1 Where settings live today

| Source | Fields | Used by |
|--------|--------|--------|
| **Logistics Settings** | `base_dimension_uom`, `base_volume_uom`, `base_weight_uom`, `default_dimension_uom`, `default_volume_uom`, `default_weight_uom`, `default_chargeable_weight_uom` | measurements.py (primary for packages) |
| **Transport Capacity Settings** | `default_dimension_uom`, `default_volume_uom`, `default_weight_uom` | transport/capacity/uom_conversion.py, transport order/job/consolidation |
| **Transport Settings** | `default_weight_uom`, `default_volume_uom` | Transport module |
| **Warehouse Settings** (per company) | `default_dimension_uom`, `default_volume_uom`, `default_weight_uom`, `default_chargeable_uom` | warehousing/utils/volume_conversion.py, warehouse_settings.get_default_uoms |
| **Air Freight Settings** | `default_volume_uom`, `default_weight_uom` | (removed in recent refactor; was fallback) |
| **Sea Freight Settings** | `default_volume_uom`, `default_weight_uom` | (removed in recent refactor; was fallback) |

### 1.2 Where conversion logic lives today

| Location | Responsibility | Data source |
|----------|----------------|------------|
| **logistics/utils/measurements.py** | `get_default_uoms()` (Logistics Settings only), `convert_dimension`, `convert_volume`, `convert_weight`, `convert_measurements_to_uom`, `apply_measurement_uom_conversion_to_children`, `get_converted_measurements_for_uom_change` | Delegates: `_get_uom_conversion_factor` → transport uom_conversion; `calculate_volume_from_dimensions` → warehousing or transport |
| **logistics/warehousing/utils/volume_conversion.py** | `get_volume_conversion_factor`, `calculate_volume_from_dimensions`, `convert_volume` (volume↔volume), `calculate_volume_from_dimensions_api` | **Dimension Volume UOM Conversion** doctype |
| **logistics/transport/capacity/uom_conversion.py** | `get_default_uoms()` (Transport Capacity Settings), `get_uom_conversion_factor`, `convert_weight`, `convert_volume`, `convert_dimension`, `calculate_volume_from_dimensions`, `standardize_capacity_value` | **UOM Conversion Factor** (Frappe); dimension→volume via warehousing |

---

## 2. Target State

### 2.1 Single source for measurement settings: Logistics Settings

- **All** default UOMs (dimension, volume, weight, chargeable weight) and base UOMs come **only** from **Logistics Settings**.
- No fallbacks to Transport Capacity Settings, Warehouse Settings, or Air/Sea Freight Settings for **measurement defaults**.
- Optional: keep **Warehouse Settings** / **Transport Capacity Settings** UOM fields as **read-only display** or **deprecate** them and remove from UI; a **migration patch** can copy existing values into Logistics Settings once.

### 2.2 Single module for conversion logic: measurements.py

- **All** conversion algorithms and factor lookups live in **`logistics/utils/measurements.py`** (or a submodule it owns, e.g. `logistics/utils/measurements_conversion.py` if you want to split API vs. internals).
- No delegation to `warehousing.utils.volume_conversion` or `transport.capacity.uom_conversion` for conversion math.
- **Data sources** (unchanged):
  - **Dimension → volume**: **Dimension Volume UOM Conversion** doctype (factor to multiply cubic dimension UOM to get volume UOM).
  - **Dimension ↔ dimension, volume ↔ volume, weight ↔ weight**: **UOM Conversion Factor** (Frappe standard).

---

## 3. Migration Steps

### Phase A: Consolidate conversion logic into measurements.py

1. **Move into measurements.py (or a single conversion module):**
   - **From warehousing/utils/volume_conversion.py:**
     - `ConversionNotFoundError` (or define in measurements and re-export for backward compat).
     - `get_volume_conversion_factor(dimension_uom, volume_uom, company)` — read from **Dimension Volume UOM Conversion** (same logic, no raw L×W×H).
     - Full implementation of `calculate_volume_from_dimensions(...)` (length, width, height, dimension_uom, volume_uom, company) using `get_volume_conversion_factor` and `raw_volume = length * width * height`.
     - Volume-to-volume conversion: either use **Dimension Volume UOM Conversion** (as warehousing does) or **UOM Conversion Factor** for volume↔volume; decide one rule and implement once in measurements.
   - **From transport/capacity/uom_conversion.py:**
     - `get_uom_conversion_factor(from_uom, to_uom)` — read from **UOM Conversion Factor** (same logic).
     - Inline or call from measurements: `convert_weight`, `convert_volume`, `convert_dimension` using that factor (measurements already has these but currently delegates to transport; replace delegation with local implementation using local `get_uom_conversion_factor`).
   - **Single rule for volume conversion:**  
     - **Dimension → volume:** always **Dimension Volume UOM Conversion**.  
     - **Volume → volume:** use **UOM Conversion Factor** in measurements (align with transport) so one table handles all volume↔volume; document that **Dimension Volume UOM Conversion** is only for (dimension_uom)³ → volume_uom.

2. **Keep measurements.py as the only public API:**
   - `get_default_uoms(company)` — from Logistics Settings only (already done).
   - `get_base_uoms()` — from Logistics Settings.
   - `get_volume_conversion_factor`, `get_uom_conversion_factor` — can stay internal (e.g. `_get_volume_conversion_factor`, `_get_uom_conversion_factor`) or remain public if other code needs them.
   - `convert_dimension`, `convert_volume`, `convert_weight` — use local `get_uom_conversion_factor` (and for volume-from-dimensions, use local `get_volume_conversion_factor` only inside `calculate_volume_from_dimensions`).
   - `calculate_volume_from_dimensions` — single implementation in measurements.py; no delegation to warehousing or transport.
   - `convert_measurements_to_uom`, `apply_measurement_uom_conversion_to_children`, `get_converted_measurements_for_uom_change`, whitelisted APIs — unchanged, but they will call the new local conversion functions.

3. **Deprecate or thin out:**
   - **warehousing/utils/volume_conversion.py:**  
     - Option A: Remove; all callers use `logistics.utils.measurements`.  
     - Option B: Keep as thin wrapper that imports and calls measurements (e.g. `from logistics.utils.measurements import calculate_volume_from_dimensions`) for backward compatibility, then deprecate in a later release.
   - **transport/capacity/uom_conversion.py:**  
     - Same: remove duplicate logic and either delete or make thin wrappers that call `logistics.utils.measurements` for `get_default_uoms`, `convert_*`, `calculate_volume_from_dimensions`.  
     - **Transport capacity** may still need `get_default_uoms(company)` for capacity logic; that should call `logistics.utils.measurements.get_default_uoms(company)` so the single source is Logistics Settings.

4. **Update all callers:**
   - Replace imports from `logistics.warehousing.utils.volume_conversion` and `logistics.transport.capacity.uom_conversion` with `logistics.utils.measurements` where the goal is default UOMs or conversion.
   - **Warehouse Settings** `calculate_volume_from_dimensions` (whitelist for JS): point to `logistics.utils.measurements.calculate_volume_from_dimensions` (or a small wrapper that returns `{"volume": ...}`) so the algorithm lives in one place.
   - **Transport** order/job/consolidation/capacity: use `measurements.get_default_uoms`, `measurements.convert_volume`, `measurements.calculate_volume_from_dimensions`, etc., instead of transport capacity uom_conversion.

### Phase B: Migrate all measurement settings to Logistics Settings

1. **Ensure Logistics Settings has all required fields** (already has):
   - `base_dimension_uom`, `base_volume_uom`, `base_weight_uom`
   - `default_dimension_uom`, `default_volume_uom`, `default_weight_uom`, `default_chargeable_weight_uom`

2. **Data migration patch (optional):**
   - For each company that has **Warehouse Settings** with default UOMs set: if Logistics Settings defaults are empty, copy from the first Warehouse Settings (or from Transport Capacity Settings) into Logistics Settings once.
   - If you keep a single global Logistics Settings, copy from Transport Capacity Settings or any module’s settings into Logistics Settings so existing deployments get defaults without re-entering.

3. **Remove or repurpose duplicate settings:**
   - **Transport Capacity Settings:** Remove `default_dimension_uom`, `default_volume_uom`, `default_weight_uom` from use in code; read from Logistics Settings via `measurements.get_default_uoms()`. Optionally hide or deprecate these fields in the UI.
   - **Transport Settings:** Same for measurement-related defaults.
   - **Warehouse Settings:** Same; `get_default_uoms(company)` in warehouse_settings can call `logistics.utils.measurements.get_default_uoms(company)` and return the same structure so existing callers (e.g. Warehouse Contract Item) keep working.
   - **Air Freight Settings / Sea Freight Settings:** Already no longer used as fallback for package UOMs; ensure no code path reads measurement defaults from them.

4. **Documentation:**
   - In Logistics Settings form or help: “Default dimension, volume, and weight UOMs are used across Transport, Air Freight, Sea Freight, and Warehousing. Set them here once.”
   - In developer docs: “All measurement conversion is in `logistics.utils.measurements`. Do not add new conversion logic in transport or warehousing.”

---

## 4. File-Level Checklist

| Action | File / area |
|--------|-------------|
| Implement `get_volume_conversion_factor` (Dimension Volume UOM Conversion) | measurements.py |
| Implement `get_uom_conversion_factor` (UOM Conversion Factor) | measurements.py |
| Implement `calculate_volume_from_dimensions` (no delegation) | measurements.py |
| Implement volume-to-volume in `convert_volume` using UOM Conversion Factor | measurements.py |
| Replace `_get_uom_conversion_factor` to use local implementation | measurements.py |
| Remove delegation to warehousing/transport in `calculate_volume_from_dimensions` | measurements.py |
| Point Warehouse Settings `calculate_volume_from_dimensions` to measurements | warehouse_settings.py |
| Replace transport capacity `get_default_uoms` with call to measurements.get_default_uoms | transport/capacity/uom_conversion.py (or remove) |
| Replace transport capacity convert_* / calculate_volume_from_dimensions with measurements | transport/capacity/uom_conversion.py or callers |
| Update all imports from volume_conversion / uom_conversion to measurements | transport, air_freight, sea_freight, warehousing, pricing_center, customs |
| Deprecate or remove duplicate logic | warehousing/utils/volume_conversion.py, transport/capacity/uom_conversion.py |
| Optional: patch to copy default UOMs into Logistics Settings | patches/ |

---

## 5. Backward Compatibility

- **Warehouse Settings `get_default_uoms(company)`:** Keep the function; implement as “return measurements.get_default_uoms(company)” (and map keys if the old return shape had different names, e.g. `chargeable` → `chargeable_weight`).
- **Warehouse Settings `calculate_volume_from_dimensions` (whitelist):** Keep; implementation becomes a wrapper that calls measurements and returns `{"volume": ...}`.
- **Transport capacity:** If external code or other apps depend on `logistics.transport.capacity.uom_conversion.get_default_uoms` or `convert_volume`, keep those as thin wrappers that call measurements and mark as deprecated in docstrings.
- **Dimension Volume UOM Conversion** doctype: No change; it remains the data source for dimension→volume. Only the code that **reads** it moves to measurements.py.

---

## 6. Summary

- **Settings:** One place for measurement defaults and base UOMs → **Logistics Settings**.
- **Logic:** One module for all conversion and default UOMs → **logistics/utils/measurements.py** (no conversion in warehousing/volume_conversion or transport/capacity/uom_conversion).
- **Data:** **Dimension Volume UOM Conversion** for dimension→volume; **UOM Conversion Factor** for dimension, volume, and weight conversions between UOMs.
- **Migration:** Move conversion implementations into measurements.py, switch all callers to measurements, then migrate settings to Logistics Settings and optionally patch existing data.
