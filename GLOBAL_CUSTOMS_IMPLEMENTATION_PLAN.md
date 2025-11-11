# Global Customs - Detailed Implementation Plan

## Overview

This plan outlines the step-by-step implementation of the Global Customs module, broken down into manageable phases with clear deliverables and dependencies.

---

## Phase 1: Foundation & Core Structure

### Duration: 2-3 days
### Priority: Critical

### Tasks

#### 1.1 Module Setup
- [ ] Create `global_customs` module directory structure
- [ ] Create `__init__.py` files
- [ ] Update `hooks.py` to include global_customs module
- [ ] Create module configuration

**Deliverables:**
- Module directory structure
- Module registered in Frappe

**Files to Create:**
```
logistics/global_customs/
├── __init__.py
├── doctype/
│   └── __init__.py
├── workspace/
│   └── global_customs/
└── report/
```

---

#### 1.2 Global Manifest (Main Transaction)
- [ ] Create DocType JSON structure
- [ ] Create Python class with validation
- [ ] Add fields:
  - Basic info (manifest number, type, country, ports)
  - Transport info (vessel/flight, voyage, ETD/ETA)
  - Parties (carrier, forwarder)
  - Status tracking
  - Links to shipments
- [ ] Add child tables:
  - Bills (Global Manifest Bill)
  - Containers
  - Commodities
  - Parties
- [ ] Add workflow (Draft → Submitted → Accepted/Rejected)
- [ ] Add auto-numbering
- [ ] Add permissions

**Deliverables:**
- `global_manifest.json`
- `global_manifest.py`
- `__init__.py`

**Key Fields:**
- `manifest_number` (Unique, Auto)
- `manifest_type` (Import/Export/Transit)
- `country` (Link: Country)
- `port_of_loading` (Link: UNLOCO)
- `port_of_discharge` (Link: UNLOCO)
- `vessel_flight_number` (Data)
- `voyage_number` (Data)
- `etd`, `eta` (Date)
- `carrier` (Link: Supplier)
- `forwarder` (Link: Supplier)
- `status` (Select)
- `sea_shipment` (Link: Sea Shipment)
- `air_shipment` (Link: Air Shipment)
- `transport_order` (Link: Transport Order)

**Validation Logic:**
- Validate ETD < ETA
- Validate required fields based on manifest type
- Validate country-specific requirements

---

#### 1.3 Global Manifest Bill (Child Table)
- [ ] Create child table DocType
- [ ] Add fields:
  - Bill number, type
  - Parties (shipper, consignee, notify)
  - Commodity description
  - Package/weight/volume
  - Container/seal numbers
  - Links to declarations and shipments

**Deliverables:**
- `global_manifest_bill.json`
- `global_manifest_bill.py`
- `__init__.py`

**Key Fields:**
- `bill_number` (Data, Required)
- `bill_type` (Select: BL, AWB, House BL, Master BL)
- `shipper` (Link: Shipper)
- `consignee` (Link: Consignee)
- `notify_party` (Link: Customer)
- `commodity_description` (Text)
- `package_count` (Int)
- `package_type` (Data)
- `weight`, `weight_uom` (Float, Link: UOM)
- `volume`, `volume_uom` (Float, Link: UOM)
- `declaration` (Link: Declaration)
- `sea_shipment` (Link: Sea Shipment)
- `air_shipment` (Link: Air Shipment)
- `container_numbers` (Small Text)
- `seal_numbers` (Small Text)

---

#### 1.4 Manifest Settings (Settings DocType)
- [ ] Create settings DocType
- [ ] Add company-level settings
- [ ] Add country enable/disable flags
- [ ] Add default values
- [ ] Add API credential sections (stubs for now)

**Deliverables:**
- `manifest_settings.json`
- `manifest_settings.py`
- `__init__.py`

**Key Fields:**
- `company` (Link: Company, Required, Unique)
- `default_carrier` (Link: Supplier)
- `default_forwarder` (Link: Supplier)
- `enable_ca_emanifest` (Check)
- `enable_us_ams` (Check)
- `enable_us_isf` (Check)
- `enable_jp_afr` (Check)
- Sections for each country's API settings (stubs)

---

#### 1.5 Integration Methods
- [ ] Add method to create Global Manifest from Sea Shipment
- [ ] Add method to create Global Manifest from Air Shipment
- [ ] Add method to create Global Manifest from Transport Order
- [ ] Add auto-population logic

**Deliverables:**
- Methods in `global_manifest.py`:
  - `create_from_sea_shipment(sea_shipment_name)`
  - `create_from_air_shipment(air_shipment_name)`
  - `create_from_transport_order(transport_order_name)`

---

#### 1.6 Workspace Setup
- [ ] Create workspace JSON
- [ ] Add Global Manifest shortcut
- [ ] Add basic structure

**Deliverables:**
- `workspace/global_customs/global_customs.json`

---

### Phase 1 Deliverables Summary
- ✅ Module structure created
- ✅ Global Manifest DocType (transaction)
- ✅ Global Manifest Bill (child table)
- ✅ Manifest Settings (settings)
- ✅ Integration methods (create from shipments)
- ✅ Basic workspace
- ✅ Migration ready

**Testing Checklist:**
- [ ] Create Global Manifest manually
- [ ] Add bills to manifest
- [ ] Create from Sea Shipment
- [ ] Create from Air Shipment
- [ ] Validate required fields
- [ ] Test status workflow

---

## Phase 2: US Systems (AMS & ISF)

### Duration: 3-4 days
### Priority: High
### Dependencies: Phase 1 Complete

### Tasks

#### 2.1 US AMS (Automated Manifest System)
- [ ] Create DocType JSON structure
- [ ] Create Python class
- [ ] Add fields:
  - AMS number, filer code
  - Port of unlading
  - Carrier code (SCAC)
  - Vessel/voyage info
  - Status tracking
  - API response fields
- [ ] Add child table: US AMS Bill
- [ ] Add workflow (Draft → Submitted → Accepted/Hold/Rejected → Released)
- [ ] Add validation logic
- [ ] Add link to Global Manifest

**Deliverables:**
- `us_ams.json`
- `us_ams.py`
- `__init__.py`

**Key Fields:**
- `ams_number` (Data, Unique, Auto)
- `global_manifest` (Link: Global Manifest)
- `filer_code` (Data) - AMS filer code
- `submission_type` (Select: Original, Update, Cancel)
- `port_of_unlading` (Link: UNLOCO)
- `estimated_arrival_date` (Date)
- `carrier_code` (Data) - SCAC code
- `vessel_name` (Data)
- `voyage_number` (Data)
- `status` (Select: Draft, Submitted, Accepted, Rejected, Hold, Released)
- `ams_transaction_number` (Data) - From CBP
- `hold_reason` (Text)
- `release_date` (Date)
- `submission_date`, `submission_time` (Date, Time)
- `bills` (Table: US AMS Bill)
- `containers` (Table)
- `company` (Link: Company)

**Validation:**
- Validate SCAC code format
- Validate port codes
- Validate required fields for submission
- Validate submission type rules

---

#### 2.2 US AMS Bill (Child Table)
- [ ] Create child table DocType
- [ ] Add fields:
  - Bill number, type
  - Parties
  - Commodity
  - Package/weight
  - Container/seal numbers
  - Hazmat flag
  - Status

**Deliverables:**
- `us_ams_bill.json`
- `us_ams_bill.py`
- `__init__.py`

**Key Fields:**
- `bill_number` (Data, Required)
- `bill_type` (Select: Master BL, House BL)
- `shipper` (Link: Shipper)
- `consignee` (Link: Consignee)
- `notify_party` (Link: Customer)
- `commodity_description` (Text)
- `package_count` (Int)
- `weight` (Float)
- `container_numbers` (Small Text)
- `seal_numbers` (Small Text)
- `hazmat` (Check)
- `status` (Select: Pending, Accepted, Hold, Released)

---

#### 2.3 US ISF (Importer Security Filing)
- [ ] Create DocType JSON structure
- [ ] Create Python class
- [ ] Add fields:
  - ISF number
  - ISF-10 data elements
  - ISF-2 data elements
  - Parties (importer, consignee, buyer, seller, etc.)
  - Commodity info
  - Container stuffing location
  - Links to AMS and Global Manifest
- [ ] Add validation (24-hour rule)
- [ ] Add workflow

**Deliverables:**
- `us_isf.json`
- `us_isf.py`
- `__init__.py`

**Key Fields:**
- `isf_number` (Data, Unique, Auto)
- `global_manifest` (Link: Global Manifest)
- `ams` (Link: US AMS)
- `importer_of_record` (Link: Customer)
- `consignee` (Link: Consignee)
- `buyer` (Link: Customer)
- `seller` (Link: Supplier)
- `ship_to_party` (Link: Customer)
- `manufacturer` (Link: Supplier)
- `country_of_origin` (Link: Country)
- `commodity_hs_code` (Data)
- `container_stuffing_location` (Link: UNLOCO)
- `consolidator` (Link: Supplier)
- `estimated_arrival_date` (Date)
- `status` (Select: Draft, Submitted, Accepted, Rejected)
- `submission_date`, `submission_time` (Date, Time)
- `company` (Link: Company)

**ISF-10 Data Elements:**
1. Manufacturer (or supplier)
2. Seller
3. Buyer
4. Ship-to party
5. Container stuffing location
6. Consolidator
7. Importer of record number
8. Consignee number
9. Country of origin
10. Commodity HTSUS number

**ISF-2 Data Elements:**
1. Vessel stow plan
2. Container status message

**Validation:**
- Must be filed 24 hours before vessel departure
- Validate all ISF-10 elements are present
- Validate HS code format
- Validate party information

---

#### 2.4 Integration Methods
- [ ] Add method to create US AMS from Global Manifest
- [ ] Add method to create US ISF from US AMS
- [ ] Add auto-population logic
- [ ] Add validation for US-specific requirements

**Deliverables:**
- Methods in `us_ams.py`:
  - `create_from_global_manifest(global_manifest_name)`
- Methods in `us_isf.py`:
  - `create_from_ams(ams_name)`
  - `validate_24_hour_rule()`

---

#### 2.5 Update Manifest Settings
- [ ] Add US AMS API settings section
- [ ] Add US ISF settings section
- [ ] Add API endpoint fields
- [ ] Add credential fields (password fields)

**Deliverables:**
- Updated `manifest_settings.json`

---

### Phase 2 Deliverables Summary
- ✅ US AMS DocType (transaction)
- ✅ US AMS Bill (child table)
- ✅ US ISF DocType (transaction)
- ✅ Integration methods
- ✅ Updated settings
- ✅ Migration ready

**Testing Checklist:**
- [ ] Create US AMS from Global Manifest
- [ ] Add bills to AMS
- [ ] Create US ISF from AMS
- [ ] Validate 24-hour rule for ISF
- [ ] Test status workflows
- [ ] Test amendment/cancellation

---

## Phase 3: Canada System (eManifest)

### Duration: 2-3 days
### Priority: High
### Dependencies: Phase 1 Complete

### Tasks

#### 3.1 CA eManifest Forwarder
- [ ] Create DocType JSON structure
- [ ] Create Python class
- [ ] Add fields:
  - Manifest number
  - CBSA carrier code
  - Submission type
  - CBSA office code
  - Port of entry
  - Conveyance info (CRN, type, name, voyage)
  - Status tracking
  - API response fields
- [ ] Add child table: eManifest Bill
- [ ] Add workflow
- [ ] Add validation logic
- [ ] Add link to Global Manifest

**Deliverables:**
- `ca_emanifest_forwarder.json`
- `ca_emanifest_forwarder.py`
- `__init__.py`

**Key Fields:**
- `manifest_number` (Data, Unique, Auto)
- `global_manifest` (Link: Global Manifest)
- `carrier_code` (Data) - CBSA carrier code
- `submission_type` (Select: Original, Amendment, Cancellation)
- `cbsa_office_code` (Data)
- `port_of_entry` (Link: UNLOCO)
- `conveyance_reference_number` (Data) - CRN
- `conveyance_type` (Select: Vessel, Aircraft, Rail, Truck)
- `conveyance_name` (Data)
- `voyage_number` (Data)
- `eta` (Date)
- `status` (Select: Draft, Submitted, Accepted, Rejected, Amended)
- `cbsa_transaction_number` (Data) - From CBSA
- `submission_date`, `submission_time` (Date, Time)
- `acceptance_date` (Date)
- `rejection_reason` (Text)
- `bills` (Table: eManifest Bill)
- `containers` (Table)
- `company` (Link: Company)

**Validation:**
- Validate CBSA carrier code format
- Validate CRN format
- Validate conveyance type requirements
- Validate submission type rules

---

#### 3.2 CA eManifest Bill (Child Table)
- [ ] Create child table DocType
- [ ] Add fields similar to Global Manifest Bill
- [ ] Add Canada-specific fields if needed

**Deliverables:**
- `ca_emanifest_bill.json`
- `ca_emanifest_bill.py`
- `__init__.py`

---

#### 3.3 Integration Methods
- [ ] Add method to create CA eManifest from Global Manifest
- [ ] Add auto-population logic
- [ ] Add validation for Canada-specific requirements

**Deliverables:**
- Methods in `ca_emanifest_forwarder.py`:
  - `create_from_global_manifest(global_manifest_name)`

---

#### 3.4 Update Manifest Settings
- [ ] Add CA eManifest API settings section
- [ ] Add CBSA API endpoint
- [ ] Add credential fields

**Deliverables:**
- Updated `manifest_settings.json`

---

### Phase 3 Deliverables Summary
- ✅ CA eManifest Forwarder DocType
- ✅ CA eManifest Bill (child table)
- ✅ Integration methods
- ✅ Updated settings
- ✅ Migration ready

**Testing Checklist:**
- [ ] Create CA eManifest from Global Manifest
- [ ] Add bills to eManifest
- [ ] Test amendment workflow
- [ ] Test cancellation workflow
- [ ] Validate CBSA-specific requirements

---

## Phase 4: Japan System (AFR)

### Duration: 2-3 days
### Priority: Medium
### Dependencies: Phase 1 Complete

### Tasks

#### 4.1 JP AFR (Japan Advance Filing Rules)
- [ ] Create DocType JSON structure
- [ ] Create Python class
- [ ] Add fields:
  - AFR number
  - Japan customs filer code
  - Submission type
  - Ports (loading, discharge)
  - Vessel/voyage info
  - Status tracking
  - API response fields
- [ ] Add child table: JP AFR Bill
- [ ] Add workflow
- [ ] Add validation logic
- [ ] Add link to Global Manifest

**Deliverables:**
- `jp_afr.json`
- `jp_afr.py`
- `__init__.py`

**Key Fields:**
- `afr_number` (Data, Unique, Auto)
- `global_manifest` (Link: Global Manifest)
- `filer_code` (Data) - Japan customs filer code
- `submission_type` (Select: Original, Amendment, Cancellation)
- `port_of_loading` (Link: UNLOCO)
- `port_of_discharge` (Link: UNLOCO)
- `vessel_name` (Data)
- `voyage_number` (Data)
- `eta` (Date)
- `status` (Select: Draft, Submitted, Accepted, Rejected)
- `japan_customs_number` (Data) - From Japan customs
- `submission_date`, `submission_time` (Date, Time)
- `bills` (Table: JP AFR Bill)
- `containers` (Table)
- `company` (Link: Company)

**Validation:**
- Validate filer code format
- Validate port codes
- Validate required fields
- Validate submission timing (before departure)

---

#### 4.2 JP AFR Bill (Child Table)
- [ ] Create child table DocType
- [ ] Add fields similar to Global Manifest Bill
- [ ] Add Japan-specific fields if needed

**Deliverables:**
- `jp_afr_bill.json`
- `jp_afr_bill.py`
- `__init__.py`

---

#### 4.3 Integration Methods
- [ ] Add method to create JP AFR from Global Manifest
- [ ] Add auto-population logic
- [ ] Add validation for Japan-specific requirements

**Deliverables:**
- Methods in `jp_afr.py`:
  - `create_from_global_manifest(global_manifest_name)`

---

#### 4.4 Update Manifest Settings
- [ ] Add JP AFR API settings section
- [ ] Add Japan customs API endpoint
- [ ] Add credential fields

**Deliverables:**
- Updated `manifest_settings.json`

---

### Phase 4 Deliverables Summary
- ✅ JP AFR DocType
- ✅ JP AFR Bill (child table)
- ✅ Integration methods
- ✅ Updated settings
- ✅ Migration ready

**Testing Checklist:**
- [ ] Create JP AFR from Global Manifest
- [ ] Add bills to AFR
- [ ] Test amendment workflow
- [ ] Test cancellation workflow
- [ ] Validate Japan-specific requirements

---

## Phase 5: Workspace & Reports

### Duration: 1-2 days
### Priority: Medium
### Dependencies: Phases 1-4 Complete

### Tasks

#### 5.1 Complete Workspace
- [ ] Add all DocTypes to workspace
- [ ] Organize by country
- [ ] Add shortcuts
- [ ] Add cards for each country
- [ ] Add Reports section

**Deliverables:**
- Complete `workspace/global_customs/global_customs.json`

**Structure:**
```
Quick Access:
- Global Manifest
- US AMS
- CA eManifest Forwarder
- JP AFR

US Filings Card:
- US AMS
- US AMS Bill
- US ISF

Canada Filings Card:
- CA eManifest Forwarder

Japan Filings Card:
- JP AFR
- JP AFR Bill

Settings Card:
- Manifest Settings

Reports Card:
- Manifest Status Report
- Filing Compliance Report
- Global Customs Dashboard
```

---

#### 5.2 Reports
- [ ] Manifest Status Report
  - List all manifests with status
  - Filter by country, status, date
  - Show submission dates
- [ ] Filing Compliance Report
  - Track filing deadlines
  - Show overdue filings
  - Show compliance metrics
- [ ] Global Customs Dashboard
  - Key metrics
  - Status summary
  - Charts

**Deliverables:**
- `report/manifest_status_report/`
- `report/filing_compliance_report/`
- `report/global_customs_dashboard/`

---

### Phase 5 Deliverables Summary
- ✅ Complete workspace
- ✅ Reports created
- ✅ Dashboard created

---

## Phase 6: API Integration (Stubs)

### Duration: 2-3 days
### Priority: Low (Can be done later)
### Dependencies: Phases 1-4 Complete

### Tasks

#### 6.1 API Integration Framework
- [ ] Create API integration base class
- [ ] Create country-specific API classes
- [ ] Add error handling
- [ ] Add retry logic
- [ ] Add logging

**Deliverables:**
- `global_customs/api/`
  - `base_api.py`
  - `us_ams_api.py`
  - `us_isf_api.py`
  - `ca_emanifest_api.py`
  - `jp_afr_api.py`

---

#### 6.2 API Methods (Stubs)
- [ ] Add submit methods (stubs that return mock responses)
- [ ] Add status check methods
- [ ] Add amendment methods
- [ ] Add cancellation methods

**Deliverables:**
- API methods in each country-specific API class
- Methods return mock data for now
- Can be replaced with real API calls later

---

### Phase 6 Deliverables Summary
- ✅ API integration framework
- ✅ Stub methods for all countries
- ✅ Ready for real API integration

---

## Implementation Summary

### Total Estimated Duration: 12-18 days

### Phase Breakdown:
- **Phase 1**: Foundation (2-3 days) - Critical
- **Phase 2**: US Systems (3-4 days) - High Priority
- **Phase 3**: Canada System (2-3 days) - High Priority
- **Phase 4**: Japan System (2-3 days) - Medium Priority
- **Phase 5**: Workspace & Reports (1-2 days) - Medium Priority
- **Phase 6**: API Integration Stubs (2-3 days) - Low Priority (can defer)

### Dependencies:
- Phase 1 must be completed first
- Phases 2, 3, 4 can be done in parallel after Phase 1
- Phase 5 depends on Phases 1-4
- Phase 6 can be done anytime after Phase 1

### Risk Factors:
- API integration complexity (Phase 6)
- Country-specific validation rules
- Data format requirements per country

---

## Approval Checklist

Please review and approve:

- [ ] Phase 1: Foundation & Core Structure
- [ ] Phase 2: US Systems (AMS & ISF)
- [ ] Phase 3: Canada System (eManifest)
- [ ] Phase 4: Japan System (AFR)
- [ ] Phase 5: Workspace & Reports
- [ ] Phase 6: API Integration Stubs

**Questions to Consider:**
1. Should we implement all phases or prioritize specific countries?
2. Do you want API integration stubs now or later?
3. Any additional country requirements beyond US, Canada, Japan?
4. Any specific validation rules or business logic to include?

---

**Ready for Approval** ✅

