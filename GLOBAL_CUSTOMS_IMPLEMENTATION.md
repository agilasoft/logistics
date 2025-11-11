# Global Customs Implementation Guide

## Overview

Global Customs module handles country-specific customs manifest and filing requirements for international trade. This includes systems like:
- **CA eManifest** (Canada)
- **US AMS** (Automated Manifest System)
- **US ISF** (Importer Security Filing)
- **JP AFR** (Japan Advance Filing Rules)
- **Global Manifest** (Multi-country)

---

## Module Structure

```
logistics/
└── global_customs/
    ├── __init__.py
    ├── doctype/
    │   ├── global_manifest/
    │   ├── global_manifest_bill/
    │   ├── ca_emanifest_forwarder/
    │   ├── us_ams/
    │   ├── us_ams_bill/
    │   ├── us_isf/
    │   ├── jp_afr/
    │   ├── jp_afr_bill/
    │   └── manifest_settings/
    ├── workspace/
    │   └── global_customs/
    └── report/
```

---

## Core DocTypes

### 1. **Global Manifest** (Main Transaction)
**Purpose**: Central manifest document that can be used for multiple countries

**Fields**:
- `manifest_number` (Data, Unique) - Manifest reference number
- `manifest_type` (Select) - Import, Export, Transit
- `country` (Link: Country) - Destination country
- `port_of_loading` (Link: UNLOCO)
- `port_of_discharge` (Link: UNLOCO)
- `vessel_flight_number` (Data)
- `voyage_number` (Data)
- `etd` (Date)
- `eta` (Date)
- `carrier` (Link: Supplier/Customer)
- `forwarder` (Link: Supplier)
- `status` (Select) - Draft, Submitted, Accepted, Rejected, Amended
- `submission_date` (Date)
- `submission_time` (Time)
- `acceptance_date` (Date)
- `rejection_reason` (Text)
- `bills` (Table) - Global Manifest Bill child table
- `containers` (Table) - Container details
- `commodities` (Table) - Commodity details
- `parties` (Table) - Parties (shipper, consignee, notify)
- `company` (Link: Company)
- `branch` (Link: Branch)

**Integration**:
- Links to Sea Shipment, Air Shipment, Transport Order
- Can create country-specific filings (AMS, eManifest, AFR, ISF)

---

### 2. **Global Manifest Bill** (Child Table)
**Purpose**: Bill of Lading/Air Waybill details within a manifest

**Fields**:
- `bill_number` (Data, Required) - BL/AWB number
- `bill_type` (Select) - Bill of Lading, Air Waybill, House BL, Master BL
- `shipper` (Link: Shipper)
- `consignee` (Link: Consignee)
- `notify_party` (Link: Customer)
- `commodity_description` (Text)
- `package_count` (Int)
- `package_type` (Data)
- `weight` (Float)
- `weight_uom` (Link: UOM)
- `volume` (Float)
- `volume_uom` (Link: UOM)
- `declaration` (Link: Declaration) - Related customs declaration
- `sea_shipment` (Link: Sea Shipment)
- `air_shipment` (Link: Air Shipment)
- `container_numbers` (Small Text) - Comma-separated
- `seal_numbers` (Small Text) - Comma-separated

---

### 3. **CA eManifest Forwarder** (Transaction)
**Purpose**: Canada eManifest filing for forwarders

**Fields**:
- `manifest_number` (Data, Unique)
- `global_manifest` (Link: Global Manifest)
- `carrier_code` (Data) - CBSA carrier code
- `submission_type` (Select) - Original, Amendment, Cancellation
- `cbsa_office_code` (Data) - CBSA office code
- `port_of_entry` (Link: UNLOCO)
- `conveyance_reference_number` (Data) - CRN
- `conveyance_type` (Select) - Vessel, Aircraft, Rail, Truck
- `conveyance_name` (Data)
- `voyage_number` (Data)
- `eta` (Date)
- `status` (Select) - Draft, Submitted, Accepted, Rejected, Amended
- `cbsa_transaction_number` (Data) - From CBSA response
- `submission_date` (Date)
- `submission_time` (Time)
- `acceptance_date` (Date)
- `rejection_reason` (Text)
- `bills` (Table) - eManifest Bill child table
- `containers` (Table) - Container details
- `api_credentials` (Section) - CBSA API credentials
- `api_endpoint` (Data)
- `api_username` (Data)
- `api_password` (Password)
- `company` (Link: Company)

**Workflow**:
- Draft → Submitted → Accepted/Rejected
- Can be amended or cancelled
- Integrates with CBSA eManifest system

---

### 4. **US AMS** (Automated Manifest System) (Transaction)
**Purpose**: US Customs Automated Manifest System filing

**Fields**:
- `ams_number` (Data, Unique) - AMS reference number
- `global_manifest` (Link: Global Manifest)
- `filer_code` (Data) - AMS filer code
- `submission_type` (Select) - Original, Update, Cancel
- `port_of_unlading` (Link: UNLOCO) - US port
- `estimated_arrival_date` (Date)
- `carrier_code` (Data) - SCAC code
- `vessel_name` (Data)
- `voyage_number` (Data)
- `status` (Select) - Draft, Submitted, Accepted, Rejected, Hold, Released
- `ams_transaction_number` (Data) - From CBP response
- `hold_reason` (Text)
- `release_date` (Date)
- `submission_date` (Date)
- `submission_time` (Time)
- `bills` (Table) - AMS Bill child table
- `containers` (Table) - Container details
- `api_credentials` (Section) - CBP API credentials
- `company` (Link: Company)

**Workflow**:
- Draft → Submitted → Accepted/Hold/Rejected → Released
- Can be updated or cancelled
- Integrates with CBP AMS system

---

### 5. **US AMS Bill** (Child Table)
**Purpose**: Bill details for AMS filing

**Fields**:
- `bill_number` (Data, Required)
- `bill_type` (Select) - Master BL, House BL
- `shipper` (Link: Shipper)
- `consignee` (Link: Consignee)
- `notify_party` (Link: Customer)
- `commodity_description` (Text)
- `package_count` (Int)
- `weight` (Float)
- `container_numbers` (Small Text)
- `seal_numbers` (Small Text)
- `hazmat` (Check) - Hazardous materials flag
- `status` (Select) - Pending, Accepted, Hold, Released

---

### 6. **US ISF** (Importer Security Filing) (Transaction)
**Purpose**: US Importer Security Filing (10+2 filing)

**Fields**:
- `isf_number` (Data, Unique)
- `global_manifest` (Link: Global Manifest)
- `ams` (Link: US AMS) - Related AMS filing
- `importer_of_record` (Link: Customer)
- `consignee` (Link: Consignee)
- `buyer` (Link: Customer)
- `seller` (Link: Supplier)
- `ship_to_party` (Link: Customer)
- `manufacturer` (Link: Supplier)
- `country_of_origin` (Link: Country)
- `commodity_hs_code` (Data) - HS code
- `container_stuffing_location` (Link: UNLOCO)
- `consolidator` (Link: Supplier)
- `estimated_arrival_date` (Date)
- `status` (Select) - Draft, Submitted, Accepted, Rejected
- `submission_date` (Date)
- `submission_time` (Time)
- `isf_10_data` (Section) - ISF-10 data elements
- `isf_2_data` (Section) - ISF-2 data elements
- `company` (Link: Company)

**Workflow**:
- Must be filed 24 hours before vessel departure
- Links to AMS filing
- Can be amended

---

### 7. **JP AFR** (Japan Advance Filing Rules) (Transaction)
**Purpose**: Japan Advance Filing Rules filing

**Fields**:
- `afr_number` (Data, Unique)
- `global_manifest` (Link: Global Manifest)
- `filer_code` (Data) - Japan customs filer code
- `submission_type` (Select) - Original, Amendment, Cancellation
- `port_of_loading` (Link: UNLOCO)
- `port_of_discharge` (Link: UNLOCO)
- `vessel_name` (Data)
- `voyage_number` (Data)
- `eta` (Date)
- `status` (Select) - Draft, Submitted, Accepted, Rejected
- `japan_customs_number` (Data) - From Japan customs response
- `submission_date` (Date)
- `submission_time` (Time)
- `bills` (Table) - AFR Bill child table
- `containers` (Table) - Container details
- `company` (Link: Company)

**Workflow**:
- Must be filed before vessel departure
- Can be amended or cancelled
- Integrates with Japan customs system

---

### 8. **JP AFR Bill** (Child Table)
**Purpose**: Bill details for AFR filing

**Fields**:
- `bill_number` (Data, Required)
- `shipper` (Link: Shipper)
- `consignee` (Link: Consignee)
- `commodity_description` (Text)
- `package_count` (Int)
- `weight` (Float)
- `container_numbers` (Small Text)

---

### 9. **Manifest Settings** (Settings DocType)
**Purpose**: Configuration for Global Customs module

**Fields**:
- `company` (Link: Company, Required)
- `default_carrier` (Link: Supplier)
- `default_forwarder` (Link: Supplier)
- `enable_ca_emanifest` (Check)
- `enable_us_ams` (Check)
- `enable_us_isf` (Check)
- `enable_jp_afr` (Check)
- `ca_emanifest_section` (Section)
  - `cbsa_api_endpoint` (Data)
  - `cbsa_api_username` (Data)
  - `cbsa_api_password` (Password)
  - `cbsa_carrier_code` (Data)
- `us_ams_section` (Section)
  - `cbp_api_endpoint` (Data)
  - `cbp_api_username` (Data)
  - `cbp_api_password` (Password)
  - `ams_filer_code` (Data)
- `us_isf_section` (Section)
  - `isf_filer_code` (Data)
- `jp_afr_section` (Section)
  - `japan_customs_api_endpoint` (Data)
  - `japan_customs_filer_code` (Data)

---

## Integration Points

### With Existing Modules

1. **Sea Shipment**:
   - Can create Global Manifest from Sea Shipment
   - Auto-populate vessel, voyage, ports, ETD/ETA
   - Link bills from Sea Shipment

2. **Air Shipment**:
   - Can create Global Manifest from Air Shipment
   - Auto-populate flight, airports, ETD/ETA
   - Link bills from Air Shipment

3. **Declaration**:
   - Link declarations to manifest bills
   - Auto-populate commodity and party information

4. **Transport Order**:
   - Can create manifest for land transport
   - Link to transport documents

---

## Workflow

### Typical Flow

1. **Create Global Manifest**
   - From Sea Shipment, Air Shipment, or manually
   - Add bills and containers
   - Add commodities and parties

2. **Create Country-Specific Filing**
   - Based on destination country, create:
     - US AMS (for US imports)
     - US ISF (for US imports, if required)
     - CA eManifest (for Canada imports)
     - JP AFR (for Japan imports)

3. **Submit Filing**
   - Validate required fields
   - Submit to government system via API
   - Receive response (Accepted/Rejected/Hold)

4. **Track Status**
   - Monitor submission status
   - Handle holds and rejections
   - Process amendments if needed

---

## API Integration

### Canada eManifest (CBSA)
- **Endpoint**: CBSA eManifest API
- **Authentication**: Username/Password or Certificate
- **Format**: XML or JSON
- **Response**: Transaction number, status, errors

### US AMS (CBP)
- **Endpoint**: CBP AMS API
- **Authentication**: API Key or Certificate
- **Format**: EDI or XML
- **Response**: AMS transaction number, status, hold reasons

### US ISF (CBP)
- **Endpoint**: CBP ISF API
- **Authentication**: API Key
- **Format**: EDI or XML
- **Response**: ISF number, status

### Japan AFR
- **Endpoint**: Japan Customs API
- **Authentication**: Certificate-based
- **Format**: XML
- **Response**: Customs number, status

---

## Implementation Priority

### Phase 1: Foundation
1. ✅ Global Manifest (Main transaction)
2. ✅ Global Manifest Bill (Child table)
3. ✅ Manifest Settings (Configuration)

### Phase 2: US Systems
4. ✅ US AMS
5. ✅ US AMS Bill
6. ✅ US ISF

### Phase 3: Canada System
7. ✅ CA eManifest Forwarder

### Phase 4: Japan System
8. ✅ JP AFR
9. ✅ JP AFR Bill

### Phase 5: Integration & Automation
10. API Integration
11. Auto-creation from shipments
12. Status synchronization
13. Reports

---

## Workspace Structure

```
Global Customs Workspace
│
├── Quick Access
│   ├── Global Manifest
│   ├── US AMS
│   ├── CA eManifest Forwarder
│   └── JP AFR
│
├── US Filings
│   ├── US AMS
│   ├── US AMS Bill
│   └── US ISF
│
├── Canada Filings
│   └── CA eManifest Forwarder
│
├── Japan Filings
│   ├── JP AFR
│   └── JP AFR Bill
│
├── Settings
│   └── Manifest Settings
│
└── Reports
    ├── Manifest Status Report
    ├── Filing Compliance Report
    └── Global Customs Dashboard
```

---

## Key Features

### 1. Multi-Country Support
- Handle different country requirements
- Country-specific fields and validations
- Country-specific API integrations

### 2. Auto-Population
- Create manifest from shipments
- Auto-populate from related documents
- Smart defaults from settings

### 3. Validation
- Country-specific validation rules
- Required field checks
- Data format validation
- Business rule validation

### 4. API Integration
- Submit to government systems
- Receive and process responses
- Handle errors and retries
- Status synchronization

### 5. Amendment Support
- Track amendments
- Maintain history
- Version control

### 6. Compliance
- Track filing deadlines
- Monitor status
- Alert on issues
- Compliance reporting

---

## Data Model Relationships

```
Global Manifest
├── Global Manifest Bill (1:N)
├── Container (1:N)
├── Commodity (1:N)
└── Party (1:N)

Global Manifest → US AMS (1:1)
Global Manifest → CA eManifest (1:1)
Global Manifest → JP AFR (1:1)

US AMS → US ISF (1:1)

Sea Shipment → Global Manifest (1:1)
Air Shipment → Global Manifest (1:1)
```

---

## Next Steps

1. **Create Module Structure**
   - Create `global_customs` directory
   - Set up module structure

2. **Implement Core DocTypes**
   - Global Manifest
   - Global Manifest Bill
   - Manifest Settings

3. **Implement Country-Specific DocTypes**
   - US AMS, US ISF
   - CA eManifest
   - JP AFR

4. **Add Integration Logic**
   - Auto-creation from shipments
   - API integration stubs
   - Validation logic

5. **Create Workspace**
   - Add to workspace
   - Organize by country

6. **Add Reports**
   - Status reports
   - Compliance reports
   - Dashboard

---

## Notes

- Each country has different requirements and formats
- API integrations may require certificates or special authentication
- Filing deadlines vary by country (e.g., ISF must be filed 24 hours before departure)
- Some filings are mandatory, others are optional
- Amendments and cancellations have specific rules per country

---

**Status**: Design Document - Ready for Implementation

