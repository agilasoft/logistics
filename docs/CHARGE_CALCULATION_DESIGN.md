# Charge Calculation Design

## Overview

This document describes how charge calculations are implemented in Sales Quote charges and how the same pattern is applied to charges of Transport Order, Transport Job, Air Booking, Air Shipment, Sea Booking, Sea Shipment, Declaration Order, and Declaration.

## 1. Sales Quote Charge Calculation Pattern

### 1.1 Architecture

Sales Quote uses child tables for each service type:
- **Sales Quote Air Freight** – air freight charges
- **Sales Quote Sea Freight** – sea freight charges  
- **Sales Quote Transport** – transport charges
- **Sales Quote Customs** – customs charges (minimal; aligned with Declaration Charges)

Each child uses the **TransportRateCalculationEngine** for calculations.

### 1.2 Calculation Flow

1. **Server-side (validate)**
   - `calculate_quantities()` – derives quantity from parent (weight, volume, pieces, distance, etc.) based on `unit_type`
   - `calculate_estimated_revenue()` – uses `TransportRateCalculationEngine.calculate_transport_rate()` with `rate_data` and `actual_data`
   - `calculate_estimated_cost()` – same engine with cost fields (`cost_calculation_method`, `unit_cost`, etc.)

2. **Client-side**
   - Field change handlers (e.g. `calculation_method`, `unit_rate`, `quantity`, `minimum_charge`, etc.) call `calculate_charges()`
   - `calculate_charges()` invokes a server API (e.g. `calculate_sea_freight_line`) with row data
   - Server creates a temporary doc, runs calculations, returns `estimated_revenue`, `estimated_cost`, `revenue_calc_notes`, `cost_calc_notes`

### 1.3 Supported Calculation Methods

| Method | Description |
|--------|-------------|
| Per Unit | `amount = unit_rate × quantity`; supports min/max charge |
| Fixed Amount | `amount = unit_rate` (flat) |
| Flat Rate | Same as Fixed Amount |
| Base Plus Additional | `amount = base_amount + (unit_rate × (quantity - base_quantity))` |
| First Plus Additional | First N at unit_rate, additional at unit_rate |
| Percentage | `amount = base_amount × (unit_rate / 100)` |
| Weight Break | Rate from Sales Quote Weight Break by actual weight |
| Qty Break | Rate from Sales Quote Qty Break by actual quantity |

### 1.4 Required Fields (Revenue)

- `calculation_method` – one of the methods above
- `unit_rate` – rate (or percentage for Percentage)
- `unit_type` – Weight, Volume, Distance, Package, Piece, TEU, Operation Time, etc.
- `minimum_charge`, `maximum_charge` – optional caps
- `base_amount`, `base_quantity`, `minimum_quantity` – for Base Plus Additional, First Plus Additional, Percentage

### 1.5 Required Fields (Cost)

- `cost_calculation_method`
- `unit_cost`
- `cost_unit_type`
- `cost_minimum_charge`, `cost_maximum_charge`
- `cost_base_amount`, `cost_base_quantity`, `cost_minimum_quantity`

---

## 2. Centralized Charge Calculation Module

### 2.1 Location

`logistics/utils/charges_calculation.py`

### 2.2 API

- `calculate_charge_revenue(charge_doc, parent_doc=None)` → `{amount, calc_notes, success, error}`
- `calculate_charge_cost(charge_doc, parent_doc=None)` → `{amount, calc_notes, success, error}`

### 2.3 Field Mapping

The module supports both naming conventions:

| Sales Quote | Charge Doctypes (legacy) |
|-------------|--------------------------|
| `calculation_method` | `charge_basis` (mapped to Per Unit, Flat Rate, etc.) |
| `unit_rate` | `rate` |
| `unit_type` | `unit_type` |

### 2.4 Parent Data Extraction

`_get_parent_actual_data()` reads from the parent document:

- **Air Booking / Air Shipment**: `total_weight`, `chargeable_weight`, `weight`, `total_volume`, `volume`, `total_pieces`
- **Sea Booking / Sea Shipment**: `total_weight`, `weight`, `total_volume`, `volume`, `total_pieces`, `total_teu`, `total_containers`
- **Transport Order / Transport Job**: `total_weight`, `weight`, `total_volume`, `volume`, `total_distance`, `total_pieces`
- **Declaration**: `total_weight`, `weight`, `total_volume`, `volume`, `total_pieces`

### 2.5 Weight Break and Qty Break

- Uses `Sales Quote Weight Break` and `Sales Quote Qty Break` with:
  - `reference_doctype` = charge doctype (e.g. `Air Booking Charges`)
  - `reference_no` = charge row `name`
  - `type` = `Selling` or `Cost`

---

## 3. Current State by Doctype

### 3.1 Already Using Centralized Calculation

| Parent Doctype | Child Doctype | Status |
|----------------|---------------|--------|
| Transport Order | Transport Order Charges | Uses `calculate_charge_revenue`, `calculate_charge_cost` in `validate()` |
| Transport Job | Transport Job Charges | Same |
| Air Booking | Air Booking Charges | Same |
| Air Shipment | Air Shipment Charges | Same |
| Sea Booking | Sea Booking Charges | Same |
| Sea Shipment | Sea Freight Charges | Same |
| Declaration | Declaration Charges | Same |

### 3.2 Gaps and Inconsistencies

1. **Air Shipment `recalculate_all_charges`**
   - Calls `charge.calculate_charge_amount()` and uses `charge.total_amount`
   - Air Shipment Charges has no `calculate_charge_amount()` and uses `estimated_revenue` instead of `total_amount`
   - **Fix**: Add `calculate_charge_amount()` that delegates to `_calculate_charges()` and set `total_amount = estimated_revenue` where needed, or align parent logic to use `estimated_revenue`

2. **Declaration Order**
   - No charges child table
   - **Design choice**: Add charges if Declaration Order should carry pricing before creating Declaration

3. **Client-side recalculation**
   - Sales Quote child tables trigger recalculation on field change
   - Charge doctypes (Transport Order Charges, etc.) only recalculate on `validate()`
   - **Enhancement**: Add client-side handlers to recalculate when `unit_rate`, `quantity`, `calculation_method`, etc. change

4. **Field alignment**
   - Some charge doctypes may use `charge_basis` instead of `calculation_method`
   - Some may use `rate` instead of `unit_rate`
   - `charges_calculation` supports both; ensure JSON schemas expose the right fields

---

## 4. Implementation Plan

### 4.1 Charge Doctypes to Align

| Doctype | Actions |
|---------|---------|
| Transport Order Charges | Ensure fields; add client-side recalculation |
| Transport Job Charges | Same |
| Air Booking Charges | Same |
| Air Shipment Charges | Same; fix `recalculate_all_charges` usage |
| Sea Booking Charges | Same |
| Sea Freight Charges | Same |
| Declaration Charges | Same |
| Declaration Order Charges | Add if Declaration Order gets charges |

### 4.2 Required Field Structure (Child Table)

Each charge child table should have:

**Revenue**
- `calculation_method` or `charge_basis`
- `unit_rate` or `rate`
- `unit_type`
- `quantity` (optional; can be derived from parent)
- `minimum_charge`, `maximum_charge`
- `base_amount`, `base_quantity`, `minimum_quantity` (for Base Plus Additional, First Plus Additional, Percentage)
- `estimated_revenue`
- `revenue_calc_notes` or `calculation_notes`

**Cost**
- `cost_calculation_method`
- `unit_cost`
- `cost_unit_type`
- `cost_minimum_charge`, `cost_maximum_charge`
- `cost_base_amount`, `cost_base_quantity`, `cost_minimum_quantity`
- `estimated_cost`
- `cost_calc_notes`

### 4.3 Server-Side (Python)

1. **Charge child doctype**
   - In `validate()`: call `_calculate_charges()` which uses `calculate_charge_revenue()` and `calculate_charge_cost()`
   - Set `estimated_revenue`, `estimated_cost`, `revenue_calc_notes`, `cost_calc_notes`

2. **Parent doctype**
   - If it has `recalculate_all_charges` or similar:
     - Iterate over charges and trigger their calculation (e.g. `charge._calculate_charges()` or a shared helper)
     - Use `estimated_revenue` (or `total_amount` if that is the canonical field) for totals

3. **Air Shipment**
   - Update `calculate_total_charges` and `recalculate_all_charges` to use `estimated_revenue` (or add `calculate_charge_amount()` on Air Shipment Charges that calls `_calculate_charges()` and sets `total_amount = estimated_revenue` for compatibility)

### 4.4 Client-Side (JavaScript)

1. **Charge child table form events**
   - On change of: `calculation_method`, `charge_basis`, `unit_rate`, `rate`, `quantity`, `unit_type`, `minimum_charge`, `maximum_charge`, `base_amount`, `cost_calculation_method`, `unit_cost`, etc.
   - Call `frappe.call()` to a whitelisted method that:
     - Accepts `parenttype`, `parent`, `row` (or `doctype`, `name`, `row`)
     - Loads or builds the charge doc, runs `_calculate_charges()`, returns `estimated_revenue`, `estimated_cost`, `revenue_calc_notes`, `cost_calc_notes`
   - Update the row in `locals` and `frm.refresh_field('charges')`

2. **Shared API**
   - Add `logistics.utils.charges_calculation.calculate_charge_row(parenttype, parent, row_data)` (or similar) as a whitelisted API
   - Reusable by all charge doctypes

### 4.5 Declaration Order Charges (Implemented)

Declaration Order now has a charges child table:

1. **Declaration Order Charges** – child doctype with same structure as Declaration Charges
2. Uses centralized `charges_calculation` in `validate()`
3. Populates from Sales Quote Customs when `sales_quote` is set (client-side API + server)
4. When creating Declaration from Declaration Order, charges are copied from the order (or from Sales Quote if order has none)

---

## 5. Summary

| Component | Responsibility |
|-----------|----------------|
| `TransportRateCalculationEngine` | Core calculation logic (Per Unit, Fixed, Base Plus Additional, etc.) |
| `charges_calculation.py` | Wrapper for charge doctypes; handles Weight Break, Qty Break, field mapping, parent data |
| Charge child doctypes | Call `_calculate_charges()` in `validate()` |
| Parent doctypes | Use `estimated_revenue` / `estimated_cost` for totals; fix any `calculate_charge_amount` / `total_amount` usage |
| Client-side | Add form events to recalculate on field change |
| Declaration Order | Add charges child table if required by business process |

---

## 7. Implementation Summary (Completed)

The following changes were implemented:

1. **Air Shipment Charges**
   - Added `calculate_charge_amount(parent_doc)` for parent-initiated recalculation
   - `_calculate_charges(parent_doc)` now accepts optional parent for correct actual data
   - Sets `total_amount = estimated_revenue` when field exists

2. **Air Shipment**
   - `recalculate_all_charges` now uses `calculate_charge_amount(parent_doc=self)` and passes parent for correct weight/volume data
   - `calculate_total_charges` uses `estimated_revenue` or `total_amount` for summing

3. **All charge doctypes** (Transport Order, Transport Job, Air Booking, Air Shipment, Sea Booking, Sea Freight, Declaration)
   - Added `_calculate_charges(parent_doc=None)` with optional parent
   - Added `calculate_charge_amount(parent_doc=None)` for consistency
   - Set `total_amount` when field exists for backward compatibility

4. **Shared API**
   - `logistics.utils.charges_calculation.calculate_charge_row(doctype, parenttype, parent, row_data)` for client-side recalculation

5. **Declaration Order**
   - Declaration Order Charges child table added; populates from Sales Quote Customs

---

## 6. References

- `logistics/pricing_center/doctype/sales_quote_air_freight/sales_quote_air_freight.py` – Sales Quote calculation pattern
- `logistics/pricing_center/doctype/sales_quote_sea_freight/sales_quote_sea_freight.js` – Client-side triggers
- `logistics/utils/charges_calculation.py` – Centralized module
- `logistics/pricing_center/api_parts/transport_rate_calculation_engine.py` – Calculation engine
