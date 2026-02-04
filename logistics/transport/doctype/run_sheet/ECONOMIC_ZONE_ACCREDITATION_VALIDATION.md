# Run Sheet: Economic Zone Accreditation Validation

## Overview

When a Run Sheet includes Transport Legs that visit addresses inside an **Economic Zone**, the assigned Transport Vehicle must hold a valid **accreditation** to that Economic Zone. This document describes the business rule, data model, and implementation design.

## Business Rule

- **Rule:** If any Transport Leg in a Run Sheet has a **pick** or **drop** address that is linked to an Economic Zone (address with **Economic Zone** value set), then the Run Sheet’s **Vehicle** must have an accreditation record for that Economic Zone in its **accreditations** child table.
- **Purpose:** Ensures only vehicles accredited to an Economic Zone are used for legs that touch that zone (e.g. free zones, special economic zones).

## Data Model

### Relevant Doctypes and Fields

| Doctype | Field | Description |
|--------|--------|-------------|
| **Run Sheet** | `vehicle` | Link to Transport Vehicle assigned to the run. |
| **Run Sheet** | `legs` | Table **Run Sheet Leg** (child). Each row links to a Transport Leg. |
| **Run Sheet Leg** | `transport_leg` | Link to Transport Leg. |
| **Run Sheet Leg** | `address_from` | Fetched from Transport Leg `pick_address`. |
| **Run Sheet Leg** | `address_to` | Fetched from Transport Leg `drop_address`. |
| **Transport Leg** | `pick_address` | Link to Address (pick-up). |
| **Transport Leg** | `drop_address` | Link to Address (drop-off). |
| **Address** | `custom_economic_zone` | Custom field, Link to **Economic Zone**. Identifies an “Economic Zone address”. |
| **Transport Vehicle** | `accreditations` | Table **Transport Vehicle EZ Accreditation** (child). |
| **Transport Vehicle EZ Accreditation** | `economic_zone` | Link to Economic Zone. |
| **Transport Vehicle EZ Accreditation** | `valid_until` | Optional; accreditation validity end date. |

### Flow

1. Run Sheet has one **Vehicle** and many **legs** (Run Sheet Leg).
2. Each Run Sheet Leg points to a **Transport Leg**, which has **pick_address** and **drop_address** (Address).
3. An Address is an “Economic Zone address” when **custom_economic_zone** is set.
4. The Run Sheet’s Vehicle has **accreditations** (Transport Vehicle EZ Accreditation); each row has **economic_zone** (and optionally **valid_until**).

## Validation Logic

### When to Run

- Run during **Run Sheet `validate()`**, so it applies on save and submit.
- Only run when:
  - Run Sheet has a **vehicle** assigned, and
  - Run Sheet has at least one **leg** (Run Sheet Leg with `transport_leg`).

### Steps

1. **Collect Economic Zones from legs**
   - For each Run Sheet Leg row, resolve the underlying **Transport Leg** (`transport_leg`).
   - From each Transport Leg, get **pick_address** and **drop_address**.
   - For each of these addresses, read **custom_economic_zone** (from Address).
   - Collect the set of Economic Zone names that are non-empty.

2. **Get vehicle accreditations**
   - Load the Run Sheet’s **Transport Vehicle** and read its **accreditations** child table.
   - Build the set of **economic_zone** values from that table.
   - Optionally, filter to “valid” rows only (e.g. `valid_until` is empty or `valid_until >= today`). Design choice: can be “has any accreditation row for that zone” or “has a valid (non-expired) accreditation”.

3. **Check coverage**
   - For every Economic Zone in the set from step 1, ensure that zone appears in the vehicle’s accreditation set from step 2.
   - If any zone is missing, **throw a validation error** that:
     - States the rule (vehicle must be accredited to the Economic Zone),
     - Names the Economic Zone(s) missing accreditation,
     - Names the Run Sheet’s vehicle,
     - Optionally names the leg(s) or address(es) that use that zone.

### Error Message (Example)

- *"Vehicle {vehicle} is not accredited to Economic Zone(s): {zone_list}. The Run Sheet contains leg(s) with pick or drop at addresses in these zones. Please assign a vehicle that has accreditations for these Economic Zones, or use addresses outside these zones."*

## Implementation Details

### Location

- **Doctype:** Run Sheet  
- **File:** `logistics/transport/doctype/run_sheet/run_sheet.py`  
- **Hook:** Add a new method `validate_vehicle_economic_zone_accreditation()` and call it from `validate()`.

### Address Economic Zone

- Custom field on **Address**: `custom_economic_zone` (Link to Economic Zone).  
- Access via `frappe.db.get_value("Address", address_name, "custom_economic_zone")` or by loading the Address doc, depending on existing patterns.

### Vehicle Accreditations

- Child table **Transport Vehicle EZ Accreditation** on **Transport Vehicle**; fieldname on vehicle: `accreditations`.
- Each row has `economic_zone` (Link to Economic Zone). Optionally use `valid_until` to consider only non-expired accreditations (e.g. `valid_until is null or valid_until >= today`).

### Performance

- One query to get all Address → Economic Zone for the addresses used in the Run Sheet legs (or one per address if preferred).
- Vehicle doc is often already loaded in other validations (e.g. capacity); reuse where possible to avoid extra DB reads.

## Optional Enhancements

- **Validity check:** Only treat accreditation as valid if `valid_until` is empty or `valid_until >= run_date` (or today).
- **Client hint:** On Run Sheet form, if user selects a vehicle, optionally show which Economic Zones the vehicle is accredited for, and which zones appear in the current legs.
- **Filter vehicles:** In the Run Sheet Vehicle link field, optionally filter to vehicles that have accreditations for all Economic Zones present in the current legs (advanced).

## Summary

| Item | Description |
|------|-------------|
| **Rule** | Legs with Economic Zone addresses require the Run Sheet vehicle to have accreditation to that Economic Zone. |
| **Where** | Run Sheet `validate()`. |
| **Data** | Address `custom_economic_zone`; Transport Vehicle `accreditations` (Transport Vehicle EZ Accreditation) with `economic_zone`. |
| **Failure** | Throw with clear message listing missing zones and the assigned vehicle. |
