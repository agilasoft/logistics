# Customs Module - Complete Workflow & Testing Guide

This comprehensive guide provides step-by-step workflows and real-world test scenarios for the Customs module in CargoNext.

## Table of Contents

1. [Module Overview](#module-overview)
2. [Prerequisites & Setup](#prerequisites--setup)
3. [Core Workflows](#core-workflows)
4. [Real-World Test Scenarios](#real-world-test-scenarios)
5. [Advanced Scenarios](#advanced-scenarios)
6. [Testing Checklist](#testing-checklist)

---

## Module Overview

The Customs module manages the complete lifecycle of customs declarations from quote to clearance:

**Main Flow:** Sales Quote → Declaration Order → Declaration → Submission → Clearance → Release

**Key Documents:**
- **Declaration Order** - Customer requirements for customs clearance
- **Declaration** - Actual customs declaration submitted to authorities
- **Permit Application** - Required permits for restricted goods
- **Exemption Certificate** - Duty/tax exemptions
- **Manifest Filings** - Country-specific manifest submissions (US AMS, US ISF, CA eManifest, JP AFR)

---

## Prerequisites & Setup

### 1. Master Data Setup

Before using the Customs module, ensure the following master data is configured:

#### 1.1 Customs Authority
**Path:** Home > Customs > Master Data > Customs Authority

**Steps:**
1. Create customs authorities for each country/region you operate in
2. Enter Authority Name, Country, Code
3. Add contact details and portal URLs if applicable
4. Examples:
   - US Customs and Border Protection (CBP) - United States
   - Canada Border Services Agency (CBSA) - Canada
   - Japan Customs - Japan
   - European Union Customs - EU countries

#### 1.2 Commodity Master
**Path:** Home > Customs > Master Data > Commodity

**Steps:**
1. Create commodity records with HS codes
2. Enter HS Code (6-10 digits), Description, Unit of Measure
3. Add duty rates, tax rates if known
4. Set country-specific classifications
5. Examples:
   - HS Code: 8471.30.01 - Laptop computers
   - HS Code: 8703.23.00 - Passenger vehicles
   - HS Code: 3004.90.00 - Medicinal products

#### 1.3 Permit Types
**Path:** Home > Customs > Master Data > Permit Type

**Steps:**
1. Create permit types for restricted goods
2. Configure validity periods, required countries, required commodities
3. Examples:
   - Import License (Pharmaceuticals)
   - Export Permit (Electronics)
   - CITES Permit (Wildlife products)

#### 1.4 Exemption Types
**Path:** Home > Customs > Master Data > Exemption Type

**Steps:**
1. Create exemption types for duty/tax exemptions
2. Set exemption percentage, maximum value limits
3. Configure if certificate is required
4. Examples:
   - Free Trade Agreement (FTA) - 100% duty exemption
   - Research & Development - 50% tax exemption
   - Diplomatic Exemption - 100% exemption

### 2. Configuration Setup

#### 2.1 Customs Settings
**Path:** Home > Customs > Customs Settings

**Configuration Steps:**
1. Set Default Company and Branch
2. Set Default Customs Authority
3. Set Default Currency
4. Configure Declaration Settings:
   - Default Declaration Type (Import/Export/Transit)
   - Require HS Code (Yes/No)
   - Require Commodity Description (Yes/No)
   - Auto Calculate Duty (Yes/No)
5. Configure Document Settings:
   - Default Document List Template
   - Require Commercial Invoice (Yes/No)
   - Require Packing List (Yes/No)
   - Require Bill of Lading (Yes/No)
6. Configure Compliance Settings:
   - Enable Compliance Alerts
   - Compliance Check Interval
   - Enable Manifest Integration

#### 2.2 Manifest Settings
**Path:** Home > Customs > Manifest Settings

**Configuration Steps:**
1. Select Company
2. Enable required manifest types:
   - **US AMS** (Automated Manifest System) - For US imports
   - **US ISF** (Importer Security Filing) - For US imports (24-hour rule)
   - **CA eManifest** - For Canada imports/exports
   - **JP AFR** (Advance Filing Rules) - For Japan imports
3. Configure API credentials for each enabled manifest type
4. Set filer codes and carrier codes

---

## Core Workflows

### Workflow 1: Standard Import Declaration

**Scenario:** Importing goods from overseas that require customs clearance.

#### Step 1: Create Sales Quote with Customs
1. Go to **Home > Pricing Center > Sales Quote**
2. Create new Sales Quote
3. Add customer, items, pricing
4. In Customs section, enable customs leg
5. Select Customs Authority, Port of Entry
6. Save and Submit Quote

#### Step 2: Create Declaration Order
1. Go to **Home > Customs > Declaration Order**
2. Click **New**
3. Link Sales Quote (or enter manually)
4. Enter Order Date
5. Select Customer
6. Select Customs Authority
7. Select Declaration Type: **Import**
8. Add Commodities:
   - Select Commodity (with HS Code)
   - Enter Quantity, Unit Price, Total Value
   - Add Description
9. Add Parties:
   - Importer/Consignee
   - Exporter/Shipper
   - Customs Broker (if applicable)
10. Add Documents (Documents tab):
    - Commercial Invoice (Required)
    - Packing List (Required)
    - Bill of Lading (Required)
    - Certificate of Origin (if applicable)
11. Save Declaration Order
12. Status: **Draft** → **Confirmed**

#### Step 3: Create Declaration
1. From Declaration Order, click **Create Declaration**
   OR
   Go to **Home > Customs > Declaration** → **New**
2. Declaration Order is auto-linked
3. Verify/Update:
   - Customs Authority
   - Declaration Type: **Import**
   - Declaration Date
4. Review Commodities (auto-populated from order)
5. Review Parties (auto-populated from order)
6. Add Transport Details:
   - Link Air Shipment or Sea Shipment
   - Port of Loading, Port of Discharge
   - Vessel/Flight Number
   - ETD, ETA
   - Container Numbers
7. Add Documents (Documents tab):
   - Upload Commercial Invoice
   - Upload Packing List
   - Upload Bill of Lading
   - Mark documents as "Received"
8. Review Financials:
   - Duty Amount (auto-calculated or manual)
   - Tax Amount
   - Other Charges
   - Total Payable
9. Save Declaration
10. Status: **Draft**

#### Step 4: Submit Declaration
1. Verify all required documents are attached
2. Verify all required permits are obtained (if applicable)
3. Click **Submit**
4. Status changes to: **Submitted**
5. Submission Date is recorded
6. Declaration Number is assigned (if auto-generated)

#### Step 5: Track Clearance
1. Monitor Declaration status:
   - **Submitted** → **Under Review** → **Cleared** → **Released**
2. Update status manually or via integration:
   - Approval Date (when Cleared)
   - Actual Clearance Date
   - Release Date
3. If rejected:
   - Status: **Rejected**
   - Enter Rejection Reason
   - Update Declaration and resubmit

#### Step 6: Create Sales Invoice
1. From Declaration, click **Create Sales Invoice**
2. Invoice is auto-populated with charges
3. Review and Submit Invoice
4. Link is maintained between Declaration and Invoice

---

### Workflow 2: Export Declaration

**Scenario:** Exporting goods that require customs declaration.

#### Steps:
1. Create Sales Quote with Export customs leg
2. Create Declaration Order:
   - Declaration Type: **Export**
   - Select Port of Exit
   - Add commodities with HS codes
3. Create Declaration from Order
4. Add Export-specific documents:
   - Export License (if required)
   - Commercial Invoice
   - Packing List
   - Shipping Bill
5. Submit Declaration
6. Track through: Submitted → Under Review → Cleared → Released

---

### Workflow 3: Declaration with Permit Requirements

**Scenario:** Importing restricted goods requiring permits.

#### Step 1: Create Permit Application
1. Go to **Home > Customs > Permit Application**
2. Click **New**
3. Select Permit Type (e.g., "Import License - Pharmaceuticals")
4. Select Applicant (Customer/Supplier)
5. Select Issuing Authority (Customs Authority)
6. Enter Application Date
7. Add required documents
8. Save
9. Status: **Draft** → **Submitted** → **Under Review** → **Approved**

#### Step 2: Link Permit to Declaration
1. Create Declaration Order (as per Workflow 1)
2. In Declaration, go to **Permit Requirements** tab
3. Add Permit Requirement:
   - Select Permit Type
   - Mark as Required
   - Link Approved Permit Application
   - Mark as Obtained
4. Save Declaration

#### Step 3: Submit Declaration
1. System validates all required permits are obtained
2. If permit missing, submission is blocked
3. Once all permits obtained, Submit Declaration

---

### Workflow 4: Declaration with Exemptions

**Scenario:** Using exemption certificates to reduce duty/tax.

#### Step 1: Create Exemption Certificate
1. Go to **Home > Customs > Exemption Certificate**
2. Click **New**
3. Select Exemption Type (e.g., "Free Trade Agreement")
4. Enter Certificate Number
5. Select Customer/Supplier
6. Set Valid From and Valid To dates
7. Enter Exemption Value or Quantity
8. Upload Certificate Document
9. Set Verification Status: **Verified**
10. Status: **Active**
11. Save

#### Step 2: Apply Exemption to Declaration
1. Create Declaration (as per Workflow 1)
2. In Declaration, go to **Exemptions** tab
3. Add Exemption:
   - Select Exemption Type
   - Select Exemption Certificate
   - Exemption Percentage (auto-filled from type)
   - Certificate Number (auto-filled)
4. Save Declaration
5. System calculates:
   - Exempted Duty
   - Exempted Tax
   - Exempted Fees
   - Total Exempted
   - Total Payable (after exemptions)

#### Step 3: Submit Declaration
1. Verify exemption certificate is valid and not expired
2. Submit Declaration
3. System tracks used exemption value/quantity

---

### Workflow 5: US AMS Manifest Filing

**Scenario:** Filing Automated Manifest System for US imports.

#### Step 1: Create Global Manifest
1. Go to **Home > Customs > Global Manifest**
2. Create manifest from Sea Shipment or Air Shipment
3. Enter vessel/flight details
4. Add bills with consignee, shipper, commodities
5. Save

#### Step 2: Create US AMS
1. From Global Manifest, click **Create US AMS**
   OR
   Go to **Home > Customs > US AMS** → **New**
2. Link Global Manifest
3. System auto-populates:
   - Vessel Name, Voyage Number
   - Port of Unlading
   - Estimated Arrival Date
   - Bills from Global Manifest
4. Verify Filer Code (from Manifest Settings)
5. Review and update bills if needed
6. Save
7. Status: **Draft**

#### Step 3: Submit US AMS
1. Click **Submit to CBP**
2. System validates:
   - All required fields
   - 24-hour rule compliance
3. Submission via API (if configured) or manual
4. Status: **Submitted**
5. CBSA Transaction Number assigned
6. Submission Date/Time recorded

#### Step 4: Track Status
1. Monitor status: Submitted → Accepted → Rejected
2. Use **Check Status** to query CBP system
3. Update status based on response

---

### Workflow 6: US ISF Filing (24-Hour Rule)

**Scenario:** Filing Importer Security Filing for US imports (required 24 hours before loading).

#### Step 1: Create US ISF
1. From US AMS, click **Create US ISF**
   OR
   Go to **Home > Customs > US ISF** → **New**
2. Link US AMS (auto-populates data)
3. Enter/Verify:
   - Consignee
   - Seller
   - Manufacturer
   - Country of Origin
   - Commodity HTSUS Codes
4. Set Estimated Arrival Date
5. Save
6. Status: **Draft**

#### Step 2: Validate 24-Hour Rule
1. Click **Validate 24-Hour Rule**
2. System checks:
   - ISF filed at least 24 hours before vessel departure
   - All required data present
3. Validation Status: **Pass** / **Warning** / **Fail**

#### Step 3: Submit US ISF
1. Ensure 24-hour rule is met
2. Click **Submit to CBP**
3. Status: **Submitted**
4. ISF Number assigned

---

### Workflow 7: Canada eManifest Filing

**Scenario:** Filing eManifest for Canada imports/exports.

#### Steps:
1. Create Global Manifest
2. Create **CA eManifest Forwarder** from Global Manifest
3. System auto-populates:
   - Carrier details
   - Conveyance information
   - Bills and commodities
4. Verify CBSA Carrier Code (from Manifest Settings)
5. Submit to CBSA via API
6. Track status and CBSA Transaction Number

---

### Workflow 8: Japan AFR Filing

**Scenario:** Filing Advance Filing Rules for Japan imports.

#### Steps:
1. Create Global Manifest
2. Create **JP AFR** from Global Manifest
3. System auto-populates:
   - Vessel details
   - Port information
   - Bills
4. Verify Japan Customs Filer Code
5. Submit to Japan Customs
6. Track AFR Number and status

---

## Real-World Test Scenarios

### Scenario 1: Simple Import - Electronics (No Permits/Exemptions)

**Objective:** Test basic import declaration workflow.

**Test Data:**
- Customer: ABC Electronics Inc.
- Commodity: Laptop Computers (HS Code: 8471.30.01)
- Quantity: 100 units
- Value: $50,000 USD
- Origin: China
- Destination: United States
- Customs Authority: US CBP

**Steps:**
1. ✅ Create Sales Quote with customs leg
2. ✅ Create Declaration Order (Import type)
3. ✅ Add commodity with HS code
4. ✅ Add required documents (Invoice, Packing List, B/L)
5. ✅ Create Declaration from Order
6. ✅ Verify auto-population of data
7. ✅ Calculate duty/tax (assume 5% duty, 8% tax)
8. ✅ Submit Declaration
9. ✅ Verify status progression: Draft → Submitted → Under Review → Cleared → Released
10. ✅ Create Sales Invoice
11. ✅ Verify all links maintained

**Expected Results:**
- Declaration value: $50,000
- Duty: $2,500 (5%)
- Tax: $4,000 (8%)
- Total Payable: $6,500
- All documents tracked
- Status updates correctly

---

### Scenario 2: Import with Free Trade Agreement Exemption

**Objective:** Test exemption certificate workflow.

**Test Data:**
- Customer: Global Trading Co.
- Commodity: Automotive Parts (HS Code: 8708.99.00)
- Quantity: 500 units
- Value: $100,000 USD
- Origin: Canada (USMCA/NAFTA)
- Exemption: FTA Certificate (100% duty exemption)
- Customs Authority: US CBP

**Steps:**
1. ✅ Create Exemption Certificate:
   - Type: Free Trade Agreement
   - Certificate Number: FTA-2024-001
   - Valid From: 2024-01-01
   - Valid To: 2024-12-31
   - Value: $200,000
   - Status: Active, Verified
2. ✅ Create Declaration Order
3. ✅ Create Declaration
4. ✅ Add Exemption:
   - Select FTA Exemption Type
   - Link Exemption Certificate
   - Exemption Percentage: 100%
5. ✅ Verify exemption calculation:
   - Duty: $5,000 (5% of $100,000)
   - Exempted Duty: $5,000 (100%)
   - Net Duty: $0
6. ✅ Submit Declaration
7. ✅ Verify used exemption value updated

**Expected Results:**
- Total Duty: $5,000
- Exempted Duty: $5,000
- Net Duty Payable: $0
- Tax: $8,000 (still applicable)
- Total Payable: $8,000
- Exemption Certificate used value: $100,000
- Remaining exemption value: $100,000

---

### Scenario 3: Import with Permit Requirement - Pharmaceuticals

**Objective:** Test permit application and validation.

**Test Data:**
- Customer: Pharma Corp
- Commodity: Prescription Drugs (HS Code: 3004.90.00)
- Quantity: 1,000 units
- Value: $250,000 USD
- Permit Required: Import License - Pharmaceuticals
- Customs Authority: US CBP

**Steps:**
1. ✅ Create Permit Type:
   - Name: Import License - Pharmaceuticals
   - Required for: Import
   - Required Countries: United States
   - Required Commodities: 3004.90.00
2. ✅ Create Permit Application:
   - Permit Type: Import License - Pharmaceuticals
   - Applicant: Pharma Corp
   - Application Date: 2024-01-15
   - Status: Draft → Submitted → Under Review → Approved
   - Approval Date: 2024-02-01
   - Valid From: 2024-02-01
   - Valid To: 2024-12-31
3. ✅ Create Declaration Order
4. ✅ Create Declaration
5. ✅ Add Permit Requirement:
   - Permit Type: Import License - Pharmaceuticals
   - Mark as Required
   - Link Approved Permit Application
   - Mark as Obtained
6. ✅ Try to Submit without permit → Should fail
7. ✅ Mark permit as obtained
8. ✅ Submit Declaration → Should succeed
9. ✅ Verify permit validation

**Expected Results:**
- System blocks submission if permit not obtained
- Error message: "The following required permits are not yet obtained: Import License - Pharmaceuticals"
- After permit obtained, submission succeeds
- Permit requirement tracked in declaration

---

### Scenario 4: Export Declaration - Machinery

**Objective:** Test export declaration workflow.

**Test Data:**
- Customer: Export Solutions Ltd.
- Commodity: Industrial Machinery (HS Code: 8428.90.00)
- Quantity: 50 units
- Value: $500,000 USD
- Origin: United States
- Destination: Germany
- Customs Authority: US CBP (Export)

**Steps:**
1. ✅ Create Sales Quote with Export customs leg
2. ✅ Create Declaration Order:
   - Declaration Type: Export
   - Port of Exit: Port of Los Angeles
3. ✅ Add Export License (if required for machinery)
4. ✅ Create Declaration
5. ✅ Add Export-specific documents:
   - Commercial Invoice
   - Packing List
   - Export License
   - Shipping Bill
6. ✅ Submit Declaration
7. ✅ Track clearance
8. ✅ Verify export compliance

**Expected Results:**
- Declaration Type: Export
- Port of Exit recorded
- Export License tracked
- Status progression works for exports
- Export value reported correctly

---

### Scenario 5: Multi-Commodity Declaration

**Objective:** Test declaration with multiple commodities.

**Test Data:**
- Customer: Multi-Product Imports
- Commodities:
  - Electronics (HS: 8471.30.01) - 200 units - $40,000
  - Textiles (HS: 6109.10.00) - 1,000 units - $30,000
  - Toys (HS: 9503.00.00) - 500 units - $20,000
- Total Value: $90,000 USD
- Customs Authority: US CBP

**Steps:**
1. ✅ Create Declaration Order
2. ✅ Add multiple commodities with different HS codes
3. ✅ Create Declaration
4. ✅ Verify all commodities auto-populated
5. ✅ Verify duty calculation per commodity:
   - Electronics: 5% duty
   - Textiles: 10% duty
   - Toys: 0% duty (duty-free)
6. ✅ Calculate total duty/tax
7. ✅ Submit Declaration
8. ✅ Verify commodity-level tracking

**Expected Results:**
- All commodities listed separately
- Duty calculated per HS code
- Electronics Duty: $2,000
- Textiles Duty: $3,000
- Toys Duty: $0
- Total Duty: $5,000
- Total Tax: $7,200 (8%)
- Total Payable: $12,200

---

### Scenario 6: US AMS Filing - Container Ship

**Objective:** Test US AMS manifest filing.

**Test Data:**
- Vessel: MV Atlantic Star
- Voyage: ATL-2024-001
- Port of Unlading: Port of Los Angeles
- ETA: 2024-03-15
- Bills: 3 bills with multiple containers
- Customs Authority: US CBP

**Steps:**
1. ✅ Create Sea Shipment
2. ✅ Create Global Manifest from Sea Shipment
3. ✅ Add bills with consignees, shippers, commodities
4. ✅ Create US AMS from Global Manifest
5. ✅ Verify auto-population:
   - Vessel Name: MV Atlantic Star
   - Voyage Number: ATL-2024-001
   - Port of Unlading: Port of Los Angeles
   - Estimated Arrival Date: 2024-03-15
   - All bills copied
6. ✅ Verify Filer Code (from Manifest Settings)
7. ✅ Submit US AMS to CBP
8. ✅ Verify:
   - Status: Submitted
   - CBP Transaction Number assigned
   - Submission Date/Time recorded
9. ✅ Check Status from CBP
10. ✅ Update status based on response

**Expected Results:**
- US AMS created successfully
- All bills included
- Filer code validated
- Submission successful
- CBP Transaction Number received
- Status tracking works

---

### Scenario 7: US ISF Filing - 24-Hour Rule Compliance

**Objective:** Test US ISF filing and 24-hour rule validation.

**Test Data:**
- Linked to US AMS from Scenario 6
- Vessel Departure: 2024-03-01 10:00
- ISF Filing: 2024-02-29 08:00 (26 hours before)
- Consignee: ABC Imports
- Seller: XYZ Exports
- Country of Origin: China

**Steps:**
1. ✅ Create US ISF from US AMS
2. ✅ Verify auto-population from AMS
3. ✅ Enter ISF-specific data:
   - Consignee
   - Seller
   - Manufacturer
   - Country of Origin
   - HTSUS Codes
4. ✅ Set Estimated Arrival Date
5. ✅ Validate 24-Hour Rule:
   - Filing Date: 2024-02-29 08:00
   - Vessel Departure: 2024-03-01 10:00
   - Time Difference: 26 hours
6. ✅ Verify validation: **Pass** (26 hours > 24 hours)
7. ✅ Submit US ISF
8. ✅ Test failure case:
   - Change filing to 20 hours before → Should show **Warning** or **Fail**

**Expected Results:**
- 24-hour rule validation: **Pass** (26 hours before)
- ISF submitted successfully
- ISF Number assigned
- Warning shown if < 24 hours
- Submission blocked if < 24 hours (if configured)

---

### Scenario 8: Declaration with Multiple Exemptions

**Objective:** Test multiple exemptions on single declaration.

**Test Data:**
- Customer: Advanced Imports
- Commodity: Medical Equipment (HS: 9018.90.00)
- Value: $150,000 USD
- Exemptions:
  - FTA Exemption: 100% duty (value: $50,000)
  - R&D Exemption: 50% tax (value: $100,000)

**Steps:**
1. ✅ Create two Exemption Certificates
2. ✅ Create Declaration
3. ✅ Add first exemption (FTA - 100% duty)
4. ✅ Add second exemption (R&D - 50% tax)
5. ✅ Verify calculations:
   - Total Duty: $7,500 (5%)
   - FTA Exempted Duty: $2,500 (on $50,000)
   - Net Duty: $5,000
   - Total Tax: $12,000 (8%)
   - R&D Exempted Tax: $4,000 (50% of $8,000 on $100,000)
   - Net Tax: $8,000
6. ✅ Submit Declaration
7. ✅ Verify both exemptions tracked

**Expected Results:**
- Multiple exemptions applied correctly
- Calculations accurate
- Both exemption certificates updated
- Total Payable: $13,000 ($5,000 duty + $8,000 tax)

---

### Scenario 9: Declaration Rejection and Resubmission

**Objective:** Test declaration rejection workflow.

**Test Data:**
- Declaration from Scenario 1 (Simple Import)
- Rejection Reason: Missing Certificate of Origin

**Steps:**
1. ✅ Submit Declaration (as per Scenario 1)
2. ✅ Status: Submitted → Under Review
3. ✅ Simulate rejection:
   - Status: **Rejected**
   - Rejection Date: 2024-03-10
   - Rejection Reason: "Missing Certificate of Origin"
4. ✅ Add missing document (Certificate of Origin)
5. ✅ Update Declaration
6. ✅ Resubmit Declaration
7. ✅ Verify status: Draft → Submitted
8. ✅ Track new submission

**Expected Results:**
- Rejection reason recorded
- Rejection date tracked
- Declaration can be updated
- Resubmission creates new submission record
- History maintained

---

### Scenario 10: Transit Declaration

**Objective:** Test transit declaration workflow.

**Test Data:**
- Goods in transit from China to Mexico via US
- Commodity: General Cargo
- Value: $75,000 USD
- Customs Authority: US CBP (Transit)

**Steps:**
1. ✅ Create Declaration Order:
   - Declaration Type: **Transit**
2. ✅ Create Declaration
3. ✅ Add transit-specific information:
   - Country of Origin: China
   - Country of Destination: Mexico
   - Transit Country: United States
4. ✅ Add transit documents
5. ✅ Submit Declaration
6. ✅ Track transit clearance

**Expected Results:**
- Declaration Type: Transit
- Transit route tracked
- Reduced duty/tax (transit goods)
- Transit documents required
- Status tracking works

---

### Scenario 11: Canada eManifest Filing

**Objective:** Test Canada eManifest workflow.

**Test Data:**
- Carrier: Canadian Freight Lines
- Conveyance: Truck
- Entry Port: Windsor, Ontario
- Bills: 5 bills
- Customs Authority: CBSA

**Steps:**
1. ✅ Create Global Manifest
2. ✅ Create CA eManifest Forwarder
3. ✅ Verify auto-population
4. ✅ Verify CBSA Carrier Code
5. ✅ Submit to CBSA via API
6. ✅ Verify:
   - Status: Submitted
   - CBSA Transaction Number
   - Submission confirmation
7. ✅ Check status from CBSA

**Expected Results:**
- CA eManifest created
- API submission successful
- CBSA Transaction Number received
- Status tracking works

---

### Scenario 12: Japan AFR Filing

**Objective:** Test Japan AFR workflow.

**Test Data:**
- Vessel: MV Pacific Express
- Port of Loading: Shanghai
- Port of Discharge: Tokyo
- ETA: 2024-04-01
- Bills: 10 bills
- Customs Authority: Japan Customs

**Steps:**
1. ✅ Create Global Manifest
2. ✅ Create JP AFR
3. ✅ Verify auto-population
4. ✅ Verify Japan Customs Filer Code
5. ✅ Submit to Japan Customs
6. ✅ Verify AFR Number
7. ✅ Track status

**Expected Results:**
- JP AFR created successfully
- Submission successful
- AFR Number assigned
- Status tracking works

---

### Scenario 13: Declaration with Partial Exemption

**Objective:** Test partial exemption (not 100%).

**Test Data:**
- Commodity: Industrial Equipment
- Value: $200,000 USD
- Exemption: 50% duty exemption (not 100%)

**Steps:**
1. ✅ Create Exemption Certificate (50% exemption)
2. ✅ Create Declaration
3. ✅ Add exemption
4. ✅ Verify calculation:
   - Total Duty: $10,000 (5%)
   - Exempted Duty: $5,000 (50%)
   - Net Duty: $5,000
5. ✅ Submit

**Expected Results:**
- Partial exemption calculated correctly
- Net duty: $5,000 (50% of $10,000)
- Tax still applies fully: $16,000
- Total Payable: $21,000

---

### Scenario 14: Permit Renewal Workflow

**Objective:** Test permit renewal.

**Test Data:**
- Original Permit: Import License - Pharmaceuticals (Expires 2024-12-31)
- Renewal Application: 2024-11-01

**Steps:**
1. ✅ Create Renewal Permit Application:
   - Link to original permit (Renewal Of field)
   - Same permit type
   - New validity dates
2. ✅ Submit renewal application
3. ✅ Approve renewal
4. ✅ Verify original permit status: **Renewed**
5. ✅ Use renewed permit in new declaration

**Expected Results:**
- Renewal linked to original
- Original permit marked as Renewed
- New permit active
- Can be used in declarations

---

### Scenario 15: Exemption Certificate Expiration

**Objective:** Test expired exemption handling.

**Test Data:**
- Exemption Certificate: Valid To 2024-12-31
- Declaration Date: 2025-01-15 (after expiration)

**Steps:**
1. ✅ Create Exemption Certificate (expired)
2. ✅ Create Declaration
3. ✅ Try to add expired exemption
4. ✅ Verify system validation:
   - Should warn/block expired certificate
   - Status check: Expired
5. ✅ Create new valid exemption
6. ✅ Use new exemption

**Expected Results:**
- System detects expired certificate
- Warning/error shown
- Cannot use expired certificate
- Must use valid certificate

---

### Scenario 16: Declaration Value Calculation

**Objective:** Test declaration value calculation from commodities.

**Test Data:**
- Commodity 1: 100 units × $500 = $50,000
- Commodity 2: 200 units × $150 = $30,000
- Commodity 3: 50 units × $400 = $20,000
- Total: $100,000

**Steps:**
1. ✅ Create Declaration
2. ✅ Add multiple commodities with quantities and prices
3. ✅ Verify auto-calculation:
   - Total Value per commodity
   - Declaration Value (sum of all)
4. ✅ Update commodity values
5. ✅ Verify declaration value updates

**Expected Results:**
- Declaration Value: $100,000 (auto-calculated)
- Updates when commodities change
- Accurate calculations

---

### Scenario 17: Document Status Tracking

**Objective:** Test document status workflow.

**Test Data:**
- Required Documents: Commercial Invoice, Packing List, B/L, COO

**Steps:**
1. ✅ Create Declaration
2. ✅ Add document requirements
3. ✅ Track document statuses:
   - Pending → Received → Verified → Submitted
4. ✅ Upload documents
5. ✅ Mark as Received
6. ✅ Mark as Verified
7. ✅ Submit declaration (documents marked as Submitted)
8. ✅ Verify document alerts:
   - Missing documents highlighted
   - Expired documents flagged
   - Pending documents shown

**Expected Results:**
- Document statuses tracked
- Alerts for missing documents
- Status progression works
- Document attachments maintained

---

### Scenario 18: Multi-Currency Declaration

**Objective:** Test multi-currency handling.

**Test Data:**
- Declaration Currency: USD
- Commodity Values: EUR, GBP, USD
- Exchange Rates: EUR/USD = 1.10, GBP/USD = 1.25

**Steps:**
1. ✅ Create Declaration (Currency: USD)
2. ✅ Add commodities with different currencies
3. ✅ Set exchange rates
4. ✅ Verify conversion:
   - EUR values converted to USD
   - GBP values converted to USD
   - Declaration Value in USD
5. ✅ Calculate duty/tax in USD
6. ✅ Submit

**Expected Results:**
- Currency conversion works
- Declaration Value in base currency (USD)
- Duty/tax calculated in base currency
- Exchange rates applied correctly

---

### Scenario 19: Declaration Amendment

**Objective:** Test declaration amendment workflow.

**Test Data:**
- Original Declaration: DEC-2024-001
- Amendment Reason: Quantity correction

**Steps:**
1. ✅ Create original Declaration
2. ✅ Submit Declaration
3. ✅ Create Amendment:
   - Link to original (Amended From)
   - Update quantities
   - Enter amendment reason
4. ✅ Submit Amendment
5. ✅ Verify:
   - Original declaration linked
   - Amendment tracked separately
   - Both declarations visible

**Expected Results:**
- Amendment created successfully
- Original declaration linked
- Amendment reason recorded
- Both declarations tracked

---

### Scenario 20: Compliance Reporting

**Objective:** Test compliance reports and dashboards.

**Steps:**
1. ✅ Create multiple declarations (various statuses)
2. ✅ Run **Declaration Status Report**:
   - Filter by status, date range, customer
   - Verify data accuracy
3. ✅ Run **Customs Compliance Report**:
   - Check compliance metrics
   - Identify issues
4. ✅ Run **Filing Compliance Report**:
   - Verify filing deadlines met
   - Check late filings
5. ✅ View **Customs Dashboard**:
   - Key metrics
   - Status overview
   - Alerts
6. ✅ View **Global Customs Dashboard**:
   - Multi-country view
   - Comparative metrics

**Expected Results:**
- Reports generate correctly
- Data accurate
- Filters work
- Dashboards show real-time data
- Alerts functional

---

## Advanced Scenarios

### Scenario 21: Complex Multi-Leg Shipment

**Scenario:** Shipment with multiple customs clearances (origin, transit, destination).

**Steps:**
1. ✅ Create Declaration Order (Origin country)
2. ✅ Create Declaration (Origin - Export)
3. ✅ Create Declaration (Transit country)
4. ✅ Create Declaration (Destination - Import)
5. ✅ Link all declarations
6. ✅ Track end-to-end

**Expected Results:**
- All declarations linked
- End-to-end visibility
- Status tracking per declaration

---

### Scenario 22: Bulk Declaration Creation

**Scenario:** Create multiple declarations from single order.

**Steps:**
1. ✅ Create Declaration Order with 10 commodities
2. ✅ Create multiple Declarations:
   - Split by commodity type
   - Split by value threshold
   - Split by permit requirements
3. ✅ Verify each declaration independent
4. ✅ Track separately

**Expected Results:**
- Multiple declarations created
- Each tracked independently
- Links maintained to order

---

### Scenario 23: Integration with Transport Module

**Scenario:** Declaration linked to Sea/Air Shipment.

**Steps:**
1. ✅ Create Sea Shipment
2. ✅ Create Declaration
3. ✅ Link Sea Shipment to Declaration
4. ✅ Verify auto-population:
   - Vessel details
   - Port information
   - ETD/ETA
   - Container numbers
5. ✅ Create Global Manifest from Shipment
6. ✅ Create US AMS from Manifest
7. ✅ Verify all links

**Expected Results:**
- Shipment linked to Declaration
- Data auto-populated
- Manifest created from shipment
- AMS created from manifest
- Full traceability

---

## Testing Checklist

### Functional Testing

#### Declaration Order
- [ ] Create Declaration Order manually
- [ ] Create Declaration Order from Sales Quote
- [ ] Add commodities with HS codes
- [ ] Add parties (Importer, Exporter, Broker)
- [ ] Add document requirements
- [ ] Status progression: Draft → Confirmed
- [ ] Link to Air/Sea Shipment
- [ ] Create Declaration from Order

#### Declaration
- [ ] Create Declaration manually
- [ ] Create Declaration from Order
- [ ] Auto-population from Order
- [ ] Add/Edit commodities
- [ ] Add/Edit parties
- [ ] Add transport details
- [ ] Link to Air/Sea Shipment
- [ ] Add documents with attachments
- [ ] Calculate declaration value
- [ ] Calculate duty/tax
- [ ] Add charges
- [ ] Status progression: Draft → Submitted → Under Review → Cleared → Released
- [ ] Rejection workflow
- [ ] Amendment workflow
- [ ] Create Sales Invoice

#### Permit Application
- [ ] Create Permit Application
- [ ] Link to Permit Type
- [ ] Add applicant (Customer/Supplier)
- [ ] Add documents
- [ ] Status progression: Draft → Submitted → Under Review → Approved
- [ ] Renewal workflow
- [ ] Link to Declaration
- [ ] Permit validation in Declaration

#### Exemption Certificate
- [ ] Create Exemption Certificate
- [ ] Link to Exemption Type
- [ ] Set validity dates
- [ ] Set exemption value/quantity
- [ ] Upload certificate document
- [ ] Verification status
- [ ] Status: Active/Expired
- [ ] Apply to Declaration
- [ ] Calculate exemptions
- [ ] Track used value/quantity
- [ ] Expiration handling

#### Manifest Filings
- [ ] Create Global Manifest
- [ ] Create US AMS from Global Manifest
- [ ] Submit US AMS to CBP
- [ ] Create US ISF from US AMS
- [ ] Validate 24-hour rule
- [ ] Submit US ISF
- [ ] Create CA eManifest
- [ ] Submit CA eManifest to CBSA
- [ ] Create JP AFR
- [ ] Submit JP AFR to Japan Customs
- [ ] Status tracking for all manifests

### Integration Testing

- [ ] Sales Quote → Declaration Order
- [ ] Declaration Order → Declaration
- [ ] Declaration → Sales Invoice
- [ ] Sea/Air Shipment → Declaration
- [ ] Sea/Air Shipment → Global Manifest
- [ ] Global Manifest → US AMS/CA eManifest/JP AFR
- [ ] US AMS → US ISF
- [ ] Permit Application → Declaration
- [ ] Exemption Certificate → Declaration

### Validation Testing

- [ ] Required fields validation
- [ ] HS code validation
- [ ] Permit requirement validation
- [ ] Exemption certificate validation (expired, used up)
- [ ] Document requirement validation
- [ ] 24-hour rule validation (US ISF)
- [ ] Currency conversion validation
- [ ] Date validation (valid from/to)
- [ ] Value/quantity validation (non-negative)

### Calculation Testing

- [ ] Declaration value calculation
- [ ] Duty calculation (per commodity, per HS code)
- [ ] Tax calculation
- [ ] Exemption calculation (percentage, maximum value)
- [ ] Total payable calculation
- [ ] Multi-currency conversion
- [ ] Exchange rate application

### Status Workflow Testing

- [ ] Declaration Order statuses
- [ ] Declaration statuses
- [ ] Permit Application statuses
- [ ] Exemption Certificate statuses
- [ ] Manifest statuses (US AMS, US ISF, CA eManifest, JP AFR)
- [ ] Status transitions
- [ ] Status-based validations

### Document Management Testing

- [ ] Document requirements
- [ ] Document attachments
- [ ] Document status tracking
- [ ] Document alerts (missing, expired, pending)
- [ ] Document templates
- [ ] Document verification

### Reporting Testing

- [ ] Declaration Status Report
- [ ] Customs Compliance Report
- [ ] Filing Compliance Report
- [ ] Declaration Value Report
- [ ] Customs Dashboard
- [ ] Global Customs Dashboard
- [ ] Report filters
- [ ] Report exports

### Error Handling Testing

- [ ] Missing required fields
- [ ] Invalid HS codes
- [ ] Missing permits
- [ ] Expired exemptions
- [ ] Missing documents
- [ ] Invalid dates
- [ ] Negative values
- [ ] API errors (manifest submissions)
- [ ] Validation errors
- [ ] Submission failures

### Performance Testing

- [ ] Large number of commodities (100+)
- [ ] Multiple declarations (1000+)
- [ ] Bulk operations
- [ ] Report generation (large datasets)
- [ ] Dashboard loading

### Security Testing

- [ ] User permissions
- [ ] Role-based access
- [ ] Data visibility
- [ ] API authentication
- [ ] Document access control

---

## Best Practices

### 1. Master Data Management
- Maintain accurate HS codes
- Keep commodity master updated
- Regularly update exemption certificates
- Monitor permit validity

### 2. Document Management
- Upload documents promptly
- Verify document completeness
- Track document statuses
- Set up document alerts

### 3. Compliance
- Monitor compliance reports regularly
- Set up compliance alerts
- Track filing deadlines
- Maintain audit trail

### 4. Integration
- Configure manifest settings correctly
- Test API integrations
- Monitor submission statuses
- Handle API errors gracefully

### 5. Workflow
- Follow standard workflow: Quote → Order → Declaration
- Validate before submission
- Track status changes
- Maintain document links

---

## Troubleshooting

### Common Issues

1. **Declaration submission fails**
   - Check required documents attached
   - Verify all required permits obtained
   - Check validation errors
   - Review compliance status

2. **Exemption not applying**
   - Verify exemption certificate is Active
   - Check validity dates
   - Verify exemption value/quantity not exhausted
   - Check exemption type configuration

3. **Permit validation fails**
   - Verify permit is Approved
   - Check permit validity dates
   - Verify permit linked correctly
   - Check permit type matches requirement

4. **Manifest submission errors**
   - Verify API credentials
   - Check filer codes
   - Validate required fields
   - Review API error messages

5. **Calculation discrepancies**
   - Verify HS codes
   - Check duty/tax rates
   - Review exemption calculations
   - Validate currency conversions

---

## Conclusion

This guide provides comprehensive workflows and test scenarios for the Customs module. Use these scenarios to:

1. **Understand** the complete customs workflow
2. **Test** all functionality thoroughly
3. **Validate** system behavior in real-world scenarios
4. **Train** users on customs processes
5. **Document** business processes

Regular testing using these scenarios ensures the system can handle all customs requirements effectively.

---

**Last Updated:** 2024
**Version:** 1.0
**Module:** Customs
