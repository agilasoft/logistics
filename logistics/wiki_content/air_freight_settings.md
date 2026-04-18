# Air Freight Settings

**Air Freight Settings** is a single-document configuration that defines default values and behavior for the Air Freight module. It controls company defaults, location defaults, calculation methods, document generation, consolidation, and billing.

To access Air Freight Settings, go to:

**Home > Air Freight > Air Freight Settings**

## 1. Prerequisites

Before configuring Air Freight Settings, ensure the following are set up:

- Company, Branch, Cost Center, Profit Center (from ERPNext)
- Airport masters (Origin, Destination)
- [ULD Type](welcome/uld-type) for default ULD
- [Logistics Service Level](welcome/logistics-service-level)

## 2. How to Configure

1. Go to **Air Freight Settings** (single document; no list).
2. Configure each section as needed.
3. **Save** the document.

## 3. Features

### 3.1 General Settings

- **Company** – Company for new Air Bookings and Air Shipments
- **Default Branch**, **Default Cost Center**, **Default Profit Center**
- **Default Currency**, **Default Incoterm**, **Default Service Level**
- **Default House Type** – Direct, Consolidation, Groupage
- **Default Direction** – Import, Export, Domestic
- **Default Entry Type** – Direct, Transit, Transshipment

### 3.2 Location Settings

- **Default Origin Airport**, **Default Destination Airport**
- **Default Origin Port**, **Default Destination Port**

### 3.3 Business Settings

- **Default Airline**, **Default Freight Agent**
- **Allow Creation of Sales Order**, **Auto-create Job Number**
- **Enable Milestone Tracking**

### 3.4 Calculation Settings

- **Volume to Weight Factor** – Divisor for chargeable weight (typically 6000 for air)
- **Chargeable Weight Calculation** – Gross, Volumetric, Chargeable
- **Default Charge Basis**, **Default Weight UOM**, **Default Volume UOM**

### 3.5 Document Settings

- **Auto Generate House AWB** – Auto-generate house air waybill numbers
- **Auto Generate Master AWB** – Auto-generate master AWB numbers
- **Require DG Declaration** – Require dangerous goods declaration
- **Default ULD Type** – Default ULD type for packages

### 3.6 Consolidation Settings

- **Default Consolidation Type** – Type for air consolidations
- **Auto Assign to Consolidation** – Automatically assign shipments
- **Max Consolidation Weight**, **Max Consolidation Volume**

### 3.7 Billing Settings

- **Auto Billing Enabled** – Enable automated billing
- **Default Billing Currency** – Currency for billing
- **Enable Billing Alerts** – Alert for unbilled shipments


<!-- wiki-field-reference:start -->

## Complete field reference

_All fields from DocType **Air Freight Settings** and nested child tables, in form order (including layout breaks). Columns: **Label** with technical **field name** in backticks, **Type**, and **Description** (from the DocType definition and standard freight/ERP semantics)._

| Label (Field name) | Type | Description |
| --- | --- | --- |
| General Settings (`general_settings_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Company (`company`) | Link | **Purpose:** Creates a controlled reference to **Company** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Company**. Create the master first if it does not exist. |
| Default Branch (`default_branch`) | Link | **Purpose:** Creates a controlled reference to **Branch** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Branch**. Create the master first if it does not exist. |
| Default Cost Center (`default_cost_center`) | Link | **Purpose:** Creates a controlled reference to **Cost Center** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Cost Center**. Create the master first if it does not exist. |
| `column_break_general` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Default Profit Center (`default_profit_center`) | Link | **Purpose:** Creates a controlled reference to **Profit Center** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Profit Center**. Create the master first if it does not exist. |
| Default Currency (`default_currency`) | Link | **Purpose:** Creates a controlled reference to **Currency** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Currency**. Create the master first if it does not exist. |
| Default Incoterm (`default_incoterm`) | Link | **Purpose:** Creates a controlled reference to **Incoterm** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Incoterm**. Create the master first if it does not exist. |
| Default Service Level (`default_service_level`) | Link | **Purpose:** Creates a controlled reference to **Service Level Agreement** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Service Level Agreement**. Create the master first if it does not exist. |
| Location Settings (`location_settings_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Default Origin Airport (`default_origin_airport`) | Link | **Purpose:** Creates a controlled reference to **UNLOCO** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UNLOCO**. Create the master first if it does not exist. |
| Default Destination Airport (`default_destination_airport`) | Link | **Purpose:** Creates a controlled reference to **UNLOCO** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UNLOCO**. Create the master first if it does not exist. |
| `column_break_location` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Default Origin Port (`default_origin_port`) | Link | **From definition:** Default origin port UNLOCO code **Purpose:** Creates a controlled reference to **UNLOCO** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UNLOCO**. Create the master first if it does not exist. |
| Default Destination Port (`default_destination_port`) | Link | **From definition:** Default destination port UNLOCO code **Purpose:** Creates a controlled reference to **UNLOCO** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UNLOCO**. Create the master first if it does not exist. |
| Business Settings (`business_settings_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Default Airline (`default_airline`) | Link | **Purpose:** Creates a controlled reference to **Airline** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Airline**. Create the master first if it does not exist. |
| Default Freight Agent (`default_freight_agent`) | Link | **Purpose:** Creates a controlled reference to **Freight Agent** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Freight Agent**. Create the master first if it does not exist. |
| `column_break_business` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Allow Creation of Sales Order (`allow_creation_of_sales_order`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Auto-create Job Number (`auto_create_job_costing`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Enable Milestone Tracking (`enable_milestone_tracking`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Default House Type (`default_house_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Standard House, Co-load Master, Blind Co-load Master, Co-load House, Buyer's Consol Lead, Shipper's Consol Lead, Break Bulk. |
| Default Direction (`default_direction`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Import, Export, Domestic. |
| Default Release Type (`default_release_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Prepaid, Collect, Third Party. |
| Default Entry Type (`default_entry_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Direct, Transit, Transshipment, ATA Carnet. |
| Calculation Settings (`calculation_settings_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Volume to Weight Factor (kg/m³) (`volume_to_weight_factor`) | Float | **From definition:** IATA standard factor: 167 kg/m³ (6 m³/1000 kg). Factor to convert volume (m³) to weight (kg) for chargeable weight calculation **Purpose:** Mass for rating, load planning, and DG limits. **What to enter:** Numeric weight; unit is implied by the label (often kg) — match company standard. |
| Chargeable Weight Calculation (`chargeable_weight_calculation`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Actual Weight, Volume Weight, Higher of Both. |
| `column_break_calculation` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Default Calculation Method (`default_calculation_method`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Per Unit, Fixed Amount, Base Plus Additional, First Plus Additional, Percentage. |
| Default Weight UOM (`default_weight_uom`) | Link | **From definition:** Default UOM for weight in Sales Quote Air tab and air-related doctypes **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Default Volume UOM (`default_volume_uom`) | Link | **From definition:** Default UOM for volume in Sales Quote Air tab and air-related doctypes **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Default Chargeable UOM (`default_chargeable_uom`) | Link | **From definition:** Default UOM for chargeable weight in Sales Quote Air tab and air-related doctypes **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Alert Settings (`alert_settings_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Enable Delay Alerts (`enable_delay_alerts`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Enable ETA Alerts (`enable_eta_alerts`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| `column_break_alert` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Alert Check Interval (Hours) (`alert_check_interval_hours`) | Int | **Purpose:** Whole number (counts, packages, TEU count, integer quantities). **What to enter:** Digits only; no decimal point. |
| Enable Dangerous Goods Compliance Alerts (`enable_dg_compliance_alerts`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Integration Settings (`integration_settings_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Enable Flight Tracking (`enable_flight_tracking`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Enable IATA Integration (`enable_iata_integration`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| `column_break_integration` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Enable Customs Clearance Tracking (`enable_customs_clearance_tracking`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Enable Real-time Tracking (`enable_real_time_tracking`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Document Settings (`document_settings_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Auto-generate House AWB Number (`auto_generate_house_awb`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Auto-generate Master AWB Number (`auto_generate_master_awb`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Use MAWB Stock for New MAWB (`use_mawb_stock`) | Check | **From definition:** When on, new Master AWB is issued from MAWB Stock Range instead of random reference **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Default MAWB Stock Range (`default_mawb_stock_range`) | Link | **Purpose:** Creates a controlled reference to **MAWB Stock Range** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **MAWB Stock Range**. Create the master first if it does not exist. |
| `column_break_document` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Require Dangerous Goods Declaration (`require_dg_declaration`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Require Customs Declaration (`require_customs_declaration`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Default ULD Type (`default_uld_type`) | Link | **Purpose:** Creates a controlled reference to **Unit Load Device** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Unit Load Device**. Create the master first if it does not exist. |
| Default Load Type (`default_load_type`) | Link | **Purpose:** Creates a controlled reference to **Load Type** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Load Type**. Create the master first if it does not exist. |
| Consolidation Settings (`consolidation_settings_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Default Consolidation Type (`default_consolidation_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Direct Consolidation, Transit Consolidation, Break-Bulk Consolidation, Multi-Country Consolidation. |
| Auto-assign to Consolidation (`auto_assign_to_consolidation`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| `column_break_consolidation` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Max Consolidation Weight (kg) (`max_consolidation_weight`) | Float | **From definition:** Maximum weight for automatic consolidation assignment **Purpose:** Mass for rating, load planning, and DG limits. **What to enter:** Numeric weight; unit is implied by the label (often kg) — match company standard. |
| Max Consolidation Volume (m³) (`max_consolidation_volume`) | Float | **From definition:** Maximum volume for automatic consolidation assignment **Purpose:** Volume for chargeable calculations and vessel/air capacity. **What to enter:** Decimal cubic measure per your label (e.g. CBM). |
| Billing Settings (`billing_settings_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Enable Auto Billing (`auto_billing_enabled`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Default Billing Currency (`default_billing_currency`) | Link | **Purpose:** Creates a controlled reference to **Currency** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Currency**. Create the master first if it does not exist. |
| `column_break_billing` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Billing Check Interval (Hours) (`billing_check_interval_hours`) | Int | **Purpose:** Whole number (counts, packages, TEU count, integer quantities). **What to enter:** Digits only; no decimal point. |
| Enable Billing Alerts (`enable_billing_alerts`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |

<!-- wiki-field-reference:end -->

## 4. Related Topics

- [Air Booking](welcome/air-booking)
- [Air Shipment](welcome/air-shipment)
- [Air Consolidation](welcome/air-consolidation)
- [ULD Type](welcome/uld-type)
- [IATA Settings](welcome/iata-settings)
