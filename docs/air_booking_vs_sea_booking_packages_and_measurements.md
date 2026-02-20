# Comparison: Package and Measurement Implementation — Air Booking vs Sea Booking

This document compares how **packages** and **measurements** (volume, weight, chargeable weight, UOMs) are implemented in **Air Booking** and **Sea Booking** in the logistics app.

---

## 1. Overview

| Aspect | Air Booking | Sea Booking |
|--------|-------------|-------------|
| **Package child table** | Air Booking Packages | Sea Booking Packages |
| **Header measurements** | Volume (m³), Weight (kg), Chargeable (kg) | Volume (m³), Weight (kg), Chargeable (kg) |
| **Override** | Yes — "Override Volume & Weight" | Yes — "Override Volume & Weight" |
| **Containers** | No | Yes — Sea Booking has a **Containers** section (Sea Booking Containers) before Packages |

---

## 2. Header-Level Measurements

### 2.1 Fields (Details tab – Measurements section)

| Field | Air Booking | Sea Booking |
|-------|-------------|-------------|
| Override Volume & Weight | ✓ Check; when set, header values are manual | ✓ Same |
| Volume (m³) | ✓ Read-only (aggregated from packages unless override) | ✓ Editable (only volume is aggregated; weight/chargeable are manual) |
| Weight (kg) | ✓ Read-only (aggregated from packages unless override) | ✓ Editable (not aggregated from packages) |
| Chargeable Weight (kg) | ✓ Read-only (calculated from volume/weight and divisor) | ✓ Editable (not calculated on header) |
| Volume-to-weight factor | ✓ **volume_to_weight_factor_type** (IATA / Custom) | — Not on header |
| Custom divisor | ✓ **custom_volume_to_weight_divisor** (optional override) | — Not on header |
| Density factor UI | ✓ **density_factor_html** (visual indicator) | ✓ Same (density_factor_html) |

### 2.2 Aggregation and calculation (parent document)

| Behavior | Air Booking | Sea Booking |
|----------|-------------|-------------|
| UOM conversion on package rows | ✓ `apply_measurement_uom_conversion_to_children(self, "packages", company=...)` in `validate()` | ✓ Same |
| Aggregate **volume** from packages to header | ✓ `aggregate_volume_from_packages()` (when not override) | ✓ `aggregate_volume_from_packages()` (when not override) |
| Aggregate **weight** from packages to header | ✓ `aggregate_weight_from_packages()` (when not override) | ✗ **Not implemented** — header weight is manual |
| Calculate **chargeable weight** on header | ✓ `calculate_chargeable_weight()` using divisor (IATA/Custom/airline) | ✗ **Not implemented** — header chargeable is manual |
| Whitelisted “refresh” API | ✓ `aggregate_volume_from_packages_api()` returns volume, weight, chargeable | ✓ `aggregate_volume_from_packages_api()` returns only volume |

**Summary:**  
- **Air Booking:** Header volume, weight, and chargeable are **derived** from packages (with optional override) and use IATA or custom volume-to-weight divisor.  
- **Sea Booking:** Only header **volume** is derived from packages; **weight** and **chargeable** are **manual**.

---

## 3. Package Child Table Structure

### 3.1 Field comparison

| Field | Air Booking Packages | Sea Booking Packages |
|-------|----------------------|----------------------|
| commodity | ✓ Link → Commodity | ✓ Link → Commodity |
| hs_code | ✓ Link → Customs Tariff Number | ✓ Link (fetch_from commodity.default_hs_code) |
| reference_no | ✓ Data | ✓ Data |
| container | — | ✓ **Data** (Sea only — link to container) |
| goods_description | ✓ Long Text | ✓ Long Text |
| uom | ✓ Link → UOM | ✓ Link → UOM |
| no_of_packs | ✓ Float | ✓ Float |
| **Measurements section** | | |
| dimension_uom | ✓ Link → UOM | ✓ Link → UOM |
| length, width, height | ✓ Float | ✓ Float |
| volume_uom | ✓ Link → UOM | ✓ Link → UOM |
| volume | ✓ Float | ✓ Float |
| weight_uom | ✓ Link → UOM | ✓ Link → UOM |
| weight | ✓ Float | ✓ Float |
| chargeable_weight_uom | ✓ Link → UOM | ✓ Link → UOM |
| chargeable_weight | ✓ Float | ✓ Float |

**Difference:** Sea Booking Packages has an extra **container** (Data) field; otherwise the measurement fields are aligned.

---

## 4. Package Row Logic (child doctype)

Both **Air Booking Packages** and **Sea Booking Packages** share the same pattern:

| Hook / method | Air Booking Packages | Sea Booking Packages |
|---------------|----------------------|----------------------|
| `before_insert` | Set default dimension_uom, volume_uom, weight_uom from Logistics Settings | Same |
| `validate` | `calculate_volume()` then `calculate_chargeable_weight()` | Same |
| **calculate_volume()** | From L×W×H via `logistics.utils.measurements.calculate_volume_from_dimensions` (dimension_uom → volume_uom) | Same implementation |
| **calculate_chargeable_weight()** | Uses **parent** divisor: IATA (6000) or Custom (air_booking or Airline) | Uses **Sea Freight Settings** divisor: `volume_to_weight_factor` (kg/m³) → divisor = 1,000,000 / factor; default 1000 |

### 4.1 Volume-to-weight divisor source

| Doctype | Divisor source | Default |
|---------|----------------|---------|
| Air Booking Packages | Parent **Air Booking**: volume_to_weight_factor_type (IATA → 6000, Custom → custom_volume_to_weight_divisor or Airline.volume_to_weight_divisor) | 6000 (IATA) |
| Sea Booking Packages | **Sea Freight Settings**: volume_to_weight_factor (kg/m³); divisor = 1,000,000 / factor | 1000 (e.g. 1000 kg/m³) |

So:
- **Air:** Per-booking (and per-airline) divisor; IATA standard 6000.
- **Sea:** Global Sea Freight Settings; typical sea factor (e.g. 1000 kg/m³) → divisor 1000.

---

## 5. Shared Measurement Utilities

Both modules use the same utilities in **`logistics.utils.measurements`**:

- **get_default_uoms(company)** — default dimension, volume, weight (and chargeable weight) from Logistics Settings.
- **get_aggregation_volume_uom(company)** — UOM used when aggregating package volumes to header (base or default volume UOM).
- **convert_volume(from_uom, to_uom, company)**, **convert_weight(...)** — for aggregating package values into header UOM.
- **calculate_volume_from_dimensions(length, width, height, dimension_uom, volume_uom, company)** — L×W×H → volume in volume_uom.
- **apply_measurement_uom_conversion_to_children(doc, child_table_fieldname, company)** — normalizes/convert child UOMs before aggregation.

Default/base UOMs are defined in **Logistics Settings** (default_dimension_uom, default_volume_uom, default_weight_uom, base_volume_uom, etc.).

---

## 6. Conversion to Shipment (packages copy)

When converting to shipment, both copy package rows; the mapped fields are almost the same, with Sea adding **container**:

**Air Booking → Air Shipment packages:**

- commodity, hs_code, reference_no, goods_description, no_of_packs, uom, weight, volume  
- (No length/width/height/chargeable in the copied dict in the current implementation.)

**Sea Booking → Sea Shipment packages:**

- commodity, hs_code, reference_no, **container**, goods_description, no_of_packs, uom, weight, volume  
- Same note: dimension and chargeable fields are not shown in the copy loop in the current code.

---

## 7. Summary Table

| Feature | Air Booking | Sea Booking |
|---------|-------------|-------------|
| Package table | Air Booking Packages | Sea Booking Packages |
| Extra package field | — | container |
| Containers section | No | Yes |
| Header volume from packages | Yes (unless override) | Yes (unless override) |
| Header weight from packages | Yes (unless override) | No (manual) |
| Header chargeable from packages | Calculated (volume + weight + divisor) | No (manual) |
| Volume-to-weight on header | IATA / Custom (per booking/airline) | N/A |
| Package volume | L×W×H via measurements util | Same |
| Package chargeable weight | Parent divisor (IATA/Custom/airline) | Sea Freight Settings divisor |
| UOM conversion | Shared measurements module | Same |
| Default UOMs (package rows) | Logistics Settings | Same |

This reflects the usual industry difference: **air** uses chargeable weight (volume weight vs actual) and IATA (or custom) divisor at booking level; **sea** often uses volume or weight separately and a global factor, with header weight/chargeable left for manual or other workflows.
