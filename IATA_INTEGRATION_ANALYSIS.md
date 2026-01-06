# IATA Integration Master Files Consolidation Analysis

## Overview
IATA integration introduced master files that duplicate existing Air Freight module masters. This document identifies which doctypes to modify, which to delete, and which scripts need updates.

**Strategy:** Use UNLOCO as the master location doctype and merge Airport Master data into it via an Airport tab.

---

## 📋 DOCTYPES TO MODIFY (Add Tabs)

### 1. **UNLOCO** → Add Airport Tab
**Current Location:** `logistics/air_freight/doctype/unlocode/`

**Action:** Add "Airport" tab with Airport Master-specific fields:
- Airport Name (airport_name) - maps to location_name if not exists
- IATA Code (iata_code) - already exists in UNLOCO, keep it
- ICAO Code (icao_code) - already exists in UNLOCO, keep it
- Airport Type (airport_type)
- Altitude Meters (altitude_meters)
- GMT Offset (gmt_offset) - may overlap with utc_offset
- DST (dst)
- Is Cargo Hub (is_cargo_hub)
- Is International (is_international)
- Has Customs Facility (has_customs) - may overlap with has_customs
- Supports Dangerous Goods (supports_dangerous_goods)
- Supports Live Animals (supports_live_animals)
- Supports Refrigerated (supports_refrigerated)
- Contact Information:
  - Website (website)
  - Phone (phone)
  - Email (email)
  - Address Line 1 (address_line_1)
  - Address Line 2 (address_line_2)
  - Postal Code (postal_code)
- Metadata:
  - Data Source (data_source) - may overlap
  - Last Synced (last_synced) - may overlap with last_updated
  - Is Active (is_active)
  - Disabled (disabled)

**Fields to keep from UNLOCO:**
- All existing UNLOCO fields remain in their respective tabs
- IATA Code and ICAO Code already exist in UNLOCO (identifiers_tab)

**Note:** Some fields may overlap (e.g., latitude/longitude, timezone, country). Use existing UNLOCO fields where they exist.

---

### 2. **Airline** → Add IATA Integration Tab
**Current Location:** `logistics/air_freight/doctype/airline/`

**Action:** Add "IATA Integration" tab with Airline Master-specific fields:
- IATA Code (iata_code) - maps to existing `code` field
- ICAO Code (icao_code) - maps to existing `three_letter_numeric_code` field
- Callsign (callsign)
- Country (country) - Link to Country doctype
- Airline Type (airline_type)
- Is Active (is_active)
- Capabilities:
  - Is Cargo Carrier (is_cargo_carrier)
  - Is Passenger Carrier (is_passenger_carrier)
  - Supports Oversized (supports_oversized) - Airline already has supports_dangerous_goods, supports_live_animals, supports_refrigerated
- Contact Information:
  - Website (website)
  - Phone (phone)
  - Email (email)
  - Address Line 1 (address_line_1)
  - Address Line 2 (address_line_2)
  - City (city)
  - Postal Code (postal_code)
- API Integration:
  - Has API Integration (has_api_integration)
  - API Endpoint (api_endpoint)
  - API Key (api_key)
  - API Username (api_username)
  - API Password (api_password)
- Metadata:
  - Data Source (data_source)
  - Last Synced (last_synced)
  - Disabled (disabled)

**Fields to keep from Airline:**
- All existing Airline fields remain (code, airline_name, logo, airline_numeric_code, three_letter_numeric_code, two_character_code, memberships, short_name, address, performance fields, etc.)

**Note:** Some fields overlap:
- `code` in Airline = `iata_code` in Airline Master
- `three_letter_numeric_code` in Airline = `icao_code` in Airline Master
- `two_character_code` in Airline = `iata_code` in Airline Master
- Performance fields already exist in both
- Use existing Airline fields where they exist

---

## 🗑️ DOCTYPES TO DELETE (After Migration)

### 1. **Airport Master**
**Location:** `logistics/air_freight/doctype/airport_master/`

**Reason:** Duplicate of UNLOCO. Airport Master data will be merged into UNLOCO's Airport tab.

**Migration Required:**
- Migrate all Airport Master records to corresponding UNLOCO records (match by IATA code)
- If UNLOCO doesn't exist for an airport, create it with Airport Master data
- Update all references from Airport Master to UNLOCO

**Files to Delete:**
- `airport_master.json`
- `airport_master.py`
- `airport_master.js` (if exists)

---

### 2. **Airline Master**
**Location:** `logistics/air_freight/doctype/airline_master/`

**Reason:** Duplicate of Airline. Airline Master data will be merged into Airline's IATA Integration tab.

**Migration Required:**
- Migrate all Airline Master records to corresponding Airline records (match by IATA code: Airline Master `iata_code` → Airline `code`)
- If Airline doesn't exist for an airline master, create it with Airline Master data
- Update all references from Airline Master to Airline

**Files to Delete:**
- `airline_master.json`
- `airline_master.py`
- `airline_master.js` (if exists)

---

## 📝 SCRIPTS TO MODIFY

### 1. **master_data_sync.py**
**Location:** `logistics/air_freight/flight_schedules/master_data_sync.py`

**Current Functions (TO REMOVE/MODIFY):**
- `sync_airline_master_to_airline()` - **MODIFY** to sync Airline Master → Airline (for migration)
- `sync_airline_to_airline_master()` - **REMOVE** (no longer needed)
- `sync_airport_master_to_location()` - **MODIFY** to sync Airport Master → UNLOCO
- `sync_location_to_airport_master()` - **MODIFY** to sync UNLOCO → Airport Master (if needed for backward compatibility)
- `sync_all_airlines_to_airline_master()` - **REMOVE**
- `sync_all_airline_masters_to_airline()` - **MODIFY** to sync all Airline Masters → Airlines (for migration)
- `get_airline_from_airline_master()` - **MODIFY** (return Airline directly)
- `get_airline_master_from_airline()` - **REMOVE**
- `get_location_from_airport_master()` - **MODIFY** to get UNLOCO from Airport Master
- `get_airport_master_from_location()` - **MODIFY** to get Airport Master from UNLOCO (if needed)

**Action:** 
- Modify sync functions to support one-way migration: Airline Master → Airline
- Remove reverse sync functions (Airline → Airline Master)
- Modify Airport Master ↔ Location sync to Airport Master ↔ UNLOCO sync

---

### 2. **Doctype References to Update**

#### Files that reference "Airport Master" (change to "UNLOCO"):
1. `air_consolidation/air_consolidation.json` - Line 136
2. `air_freight_settings/air_freight_settings.json` - Lines 135, 141
3. `flight_schedule/flight_schedule.json` - Lines 88, 136, 195
4. `flight_route/flight_route.json` - Lines 52, 71, 80
5. `air_consolidation_routes/air_consolidation_routes.json` - Lines 78, 85
6. `flight_schedule_sync_log/flight_schedule_sync_log.json` - Line 56

#### Files that reference "UNLOCO" (keep as is):
- All existing UNLOCO references remain valid
- Files that reference UNLOCO:
  1. `air_booking/air_booking.json` - Line 165
  2. `master_air_waybill/master_air_waybill.json` - Lines 225, 255
  3. `air_consolidation/air_consolidation.json` - Line 143
  4. `air_shipment/air_shipment.json` - Lines 302, 314
  5. `air_freight_settings/air_freight_settings.json` - Lines 151, 158
  6. All report files (multiple)

#### Files that reference "Airline Master" (change to "Airline"):
1. `air_consolidation/air_consolidation.json` - Line 166
2. `flight_schedule/flight_schedule.json` - Line 88
3. `flight_route/flight_route.json` - Line 52
4. `air_consolidation_routes/air_consolidation_routes.json` - Line 96
5. `flight_schedule_sync_log/flight_schedule_sync_log.json` - Line 56

#### Files that reference "Airline" (keep as is):
- All existing Airline references remain valid
- Files that reference Airline:
  1. `air_booking/air_booking.json` - Line 113
  2. `master_air_waybill/master_air_waybill.json` - Line 112
  3. `air_shipment/air_shipment.json` - Line 227
  4. `air_freight_settings/air_freight_settings.json` - Line 170
  5. All report files (multiple):
     - `air_shipment_status_report/air_shipment_status_report.py` - Line 96
     - `airline_performance_report/airline_performance_report.py` - Line 23
     - `air_freight_cost_analysis/air_freight_cost_analysis.py` - Line 50
     - `on_time_performance_report/on_time_performance_report.py` - Line 50
     - `route_analysis_report/route_analysis_report.py` - Line 89

---

### 3. **Python Scripts to Update**

#### Files that use Airport Master doctype:
1. `airport_master/airport_master.py` - **DELETE** entire file
2. `flight_schedules/master_data_sync.py` - Update sync functions
3. `tests/test_helpers.py` - Line 36-51 (create_test_airport function) - Update to create UNLOCO instead
4. Any other files referencing Airport Master

#### Files that use UNLOCO doctype:
1. `air_shipment/air_shipment.py` - Lines 1350-1358 (get_coordinates_from_unloco function) - Keep as is
2. `tests/test_helpers.py` - Line 54-85 (create_test_unloco function) - Keep as is
3. `utils/unlocode_utils.py` - Keep as is
4. `unlocode/unlocode.py` - Keep as is, may need to add Airport tab logic

#### Files that use Airline Master doctype:
1. `airline_master/airline_master.py` - **DELETE** entire file
2. `flight_schedules/master_data_sync.py` - Update sync functions
3. Any other files referencing Airline Master

#### Files that use Airline doctype:
1. `tests/test_helpers.py` - Line 88+ (create_test_airline function) - Keep as is
2. `tests/test_airline.py` - All test functions - Keep as is
3. `tests/test_master_air_waybill.py` - Uses create_test_airline - Keep as is
4. `tests/test_air_freight_settings.py` - Uses create_test_airline - Keep as is

---

### 4. **JavaScript Files to Update**

#### Files that reference Airport Master:
- Check for any Airport Master-specific JS files
- `airport_master/airport_master.js` - **DELETE** (if exists)

#### Files that reference UNLOCO:
1. `unlocode/unlocode.js` - **KEEP** and may need updates for Airport tab
2. `air_shipment/air_shipment.js` - Line 781-791 (UNLOCO coordinate lookup) - Keep as is

#### Files that reference Airline Master:
- `airline_master/airline_master.js` - **DELETE** (if exists)

#### Files that reference Airline:
- Check for any Airline-specific JS files - **KEEP** as is

---

### 5. **Workspace Files to Update**

1. `workspace/air_freight/air_freight.json`:
   - Remove Airport Master link (Line 38-40)
   - Keep UNLOCO link (Line 58-60)
   - Keep Airline link (Line 28-30, 396-397)
   - Remove Airline Master link (Line 38-40)

---

## 🔄 MIGRATION STEPS (After Approval)

1. **Add Airport tab** to UNLOCO with Airport Master fields
2. **Add IATA Integration tab** to Airline with Airline Master fields
3. **Migrate data** from Airport Master to UNLOCO (match by IATA code)
   - If UNLOCO exists: Update Airport tab fields
   - If UNLOCO doesn't exist: Create UNLOCO with Airport Master data
4. **Migrate data** from Airline Master to Airline (match by IATA code: Airline Master `iata_code` → Airline `code`)
   - If Airline exists: Update IATA Integration tab fields
   - If Airline doesn't exist: Create Airline with Airline Master data
5. **Update all references** in JSON files:
   - Airport Master → UNLOCO
   - Airline Master → Airline
6. **Update Python scripts** to use new doctypes
7. **Update JavaScript files** to use new doctypes
8. **Modify sync functions** in master_data_sync.py
9. **Delete Airport Master and Airline doctypes**
10. **Update tests** to use new doctypes
11. **Update workspace** links

---

## ⚠️ NOTES

- **UNLOCO** uses `unlocode` as autoname (5 characters: country code + location code)
- **Airport Master** uses `iata_code` as autoname (3 characters)
- **Airline** uses `code` as autoname (2 characters)
- **Airline Master** uses `iata_code` as autoname (2 characters)

**Mapping Strategy:**
- Airport Master → UNLOCO: Match by `iata_code` field
  - If UNLOCO exists with matching IATA code: Update Airport tab
  - If UNLOCO doesn't exist: Create new UNLOCO with Airport Master data
- Airline Master → Airline: Match by `iata_code` in Airline Master (maps to `code` in Airline)
  - If Airline exists with matching code: Update IATA Integration tab
  - If Airline doesn't exist: Create new Airline with Airline Master data

**Field Overlaps (UNLOCO vs Airport Master):**
- `iata_code` - Already in UNLOCO (identifiers_tab)
- `icao_code` - Already in UNLOCO (identifiers_tab)
- `latitude/longitude` - Already in UNLOCO (coordinates_tab)
- `timezone` - Already in UNLOCO (logistics_tab)
- `country` - Already in UNLOCO (basic_info_tab)
- `city` - Already in UNLOCO (basic_info_tab)
- `has_customs` - Already in UNLOCO (function_tab)
- `data_source` - Already in UNLOCO (auto_populate_tab)
- `last_updated` - Similar to `last_synced` in UNLOCO

**Resolution:** Use existing UNLOCO fields where they overlap. Only add Airport Master-specific fields that don't exist in UNLOCO.

---

## ✅ APPROVAL REQUIRED

Please review and approve:
1. ✅ **RETAIN:** UNLOCO (with Airport tab added)
2. ✅ **RETAIN:** Airline (with IATA Integration tab added)
3. ❌ **DELETE:** Airport Master (after migration to UNLOCO)
4. ❌ **DELETE:** Airline Master (after migration to Airline)

