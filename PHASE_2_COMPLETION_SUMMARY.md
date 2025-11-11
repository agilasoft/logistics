# Phase 2: US Systems (AMS & ISF) - Completion Summary

## ✅ Completed Tasks

### 1. US AMS DocType ✅
**Location**: `logistics/customs/doctype/us_ams/`

**Files Created:**
- `us_ams.json` - DocType definition
- `us_ams.py` - Python class with business logic
- `__init__.py` - Module initialization

**Key Features:**
- Transaction DocType for US Automated Manifest System filing
- Status workflow: Draft → Submitted → Accepted/Rejected/Hold → Released
- Auto-population from linked Global Manifest
- SCAC code validation (4 uppercase letters)
- Integration method to create from Global Manifest
- Links to Global Manifest
- Tracks AMS transaction number from CBP response

**Key Fields:**
- `ams_number` (Auto-numbered)
- `global_manifest` (Link: Global Manifest)
- `submission_type` (Original/Update/Cancel)
- `status` (Draft/Submitted/Accepted/Rejected/Hold/Released)
- `filer_code` (AMS filer code)
- `port_of_unlading` (US port)
- `estimated_arrival_date`
- `carrier_code` (SCAC - 4 uppercase letters)
- `vessel_name`, `voyage_number`
- `ams_transaction_number` (From CBP)
- `hold_reason`, `release_date`
- `bills` (Table: US AMS Bill)

**Validation:**
- SCAC code format validation (4 uppercase letters)
- Required fields for submission
- Submission type rules (only Draft can be cancelled)

**Integration Method:**
- `create_from_global_manifest(global_manifest_name)` - Creates US AMS from Global Manifest
  - Validates country is United States
  - Auto-populates vessel, port, dates
  - Copies bills from Global Manifest
  - Gets filer code from Manifest Settings

---

### 2. US AMS Bill (Child Table) ✅
**Location**: `logistics/customs/doctype/us_ams_bill/`

**Files Created:**
- `us_ams_bill.json` - Child table definition
- `us_ams_bill.py` - Python class
- `__init__.py` - Module initialization

**Key Features:**
- Child table for bills within US AMS filing
- Fields for bill number, type, parties, commodity
- Hazardous materials flag
- Container and seal number tracking
- Status tracking per bill

**Key Fields:**
- `bill_number` (Required)
- `bill_type` (Master BL, House BL)
- `shipper`, `consignee`, `notify_party`
- `commodity_description`
- `package_count`, `weight`
- `hazmat` (Check - Hazardous materials flag)
- `container_numbers`, `seal_numbers`
- `declaration`, `sea_shipment`, `air_shipment`
- `status` (Pending/Accepted/Hold/Released)

---

### 3. US ISF DocType ✅
**Location**: `logistics/customs/doctype/us_isf/`

**Files Created:**
- `us_isf.json` - DocType definition
- `us_isf.py` - Python class with business logic
- `__init__.py` - Module initialization

**Key Features:**
- Transaction DocType for US Importer Security Filing (10+2 filing)
- ISF-10 data elements (required 24 hours before vessel departure)
- ISF-2 data elements (carrier responsibility)
- 24-hour rule validation
- Auto-population from Global Manifest or AMS
- Integration method to create from US AMS

**Key Fields:**
- `isf_number` (Auto-numbered)
- `global_manifest` (Link: Global Manifest)
- `ams` (Link: US AMS)
- `status` (Draft/Submitted/Accepted/Rejected)

**ISF-10 Data Elements (Required):**
1. `importer_of_record` (Link: Customer)
2. `consignee` (Link: Consignee)
3. `buyer` (Link: Customer)
4. `seller` (Link: Supplier)
5. `ship_to_party` (Link: Customer)
6. `manufacturer` (Link: Supplier)
7. `country_of_origin` (Link: Country)
8. `commodity_hs_code` (HTSUS number)
9. `container_stuffing_location` (Link: UNLOCO)
10. `consolidator` (Link: Supplier)

**ISF-2 Data Elements:**
1. `vessel_stow_plan` (Data)
2. `container_status_message` (Data)

**Validation:**
- All ISF-10 elements must be present
- HS code format validation (numeric)
- 24-hour rule validation (must be filed 24 hours before vessel departure)
- Real-time validation status display

**Integration Methods:**
- `create_from_ams(ams_name)` - Creates US ISF from US AMS
- `validate_24_hour_rule(isf_name)` - Validates 24-hour rule compliance

**24-Hour Rule Validation:**
- Calculates hours until vessel departure (ETD from Global Manifest)
- Validates if ISF is filed at least 24 hours before departure
- Shows validation status (Valid/Warning/Error)
- Displays time remaining/elapsed

---

### 4. Manifest Settings ✅
**Status**: Already includes US sections from Phase 1

**US AMS Settings:**
- `cbp_api_endpoint` - CBP API endpoint
- `cbp_api_username` - CBP API username
- `cbp_api_password` - CBP API password
- `ams_filer_code` - AMS filer code

**US ISF Settings:**
- `isf_filer_code` - ISF filer code

---

## 📋 Files Created

```
logistics/customs/doctype/
├── us_ams/
│   ├── __init__.py
│   ├── us_ams.json
│   └── us_ams.py
├── us_ams_bill/
│   ├── __init__.py
│   ├── us_ams_bill.json
│   └── us_ams_bill.py
└── us_isf/
    ├── __init__.py
    ├── us_isf.json
    └── us_isf.py
```

---

## 🔗 Integration Flow

1. **Create Global Manifest** (from Sea Shipment/Air Shipment)
2. **Create US AMS** from Global Manifest
   - Validates country is United States
   - Auto-populates vessel, port, dates
   - Copies bills from Global Manifest
3. **Create US ISF** from US AMS
   - Links to both AMS and Global Manifest
   - Validates 24-hour rule
   - Requires all ISF-10 elements

---

## 🧪 Testing Checklist

Before running `bench migrate`, verify:

- [x] All JSON files are valid
- [x] All Python files have proper imports
- [x] No linting errors
- [x] DocType names are unique
- [x] Field references are correct
- [x] Child table properly marked with `istable: 1`
- [x] Validation logic is correct
- [x] Integration methods are whitelisted

---

## 🚀 Next Steps

1. **Run Migration:**
   ```bash
   cd /home/frappe/frappe-bench
   bench migrate
   bench clear-cache
   ```

2. **Test in UI:**
   - Create Global Manifest for US shipment
   - Create US AMS from Global Manifest
   - Add bills to AMS
   - Create US ISF from AMS
   - Test 24-hour rule validation
   - Test SCAC code validation

3. **Proceed to Phase 3:**
   - CA eManifest Forwarder DocType
   - CA eManifest Bill child table

---

## 📝 Key Features Implemented

### US AMS:
- ✅ SCAC code validation
- ✅ Auto-population from Global Manifest
- ✅ Status workflow with Hold/Release
- ✅ AMS transaction number tracking
- ✅ Bill management

### US ISF:
- ✅ Complete ISF-10 data elements
- ✅ ISF-2 data elements
- ✅ 24-hour rule validation
- ✅ Real-time validation status
- ✅ Auto-population from AMS/Manifest
- ✅ HS code format validation

---

## ⚠️ Notes

- US AMS requires country to be "United States"
- US ISF must be filed 24 hours before vessel departure
- SCAC code must be exactly 4 uppercase letters
- All ISF-10 elements are required
- Integration methods check for existing records to prevent duplicates

---

**Status**: ✅ Phase 2 Complete - Ready for Migration

