# Sea Freight Settings

**Sea Freight Settings** is a single-document configuration that defines default values and behavior for the Sea Freight module. It controls company defaults, location defaults, penalty rates, calculation methods, and integration options.

To access Sea Freight Settings, go to:

**Home > Sea Freight > Sea Freight Settings**

## 1. Prerequisites

Before configuring Sea Freight Settings, ensure the following are set up:

- Company, Branch, Cost Center, Profit Center (from ERPNext)
- Port masters (Origin Port, Destination Port)
- Shipping Line, Freight Agent (if applicable)
- [Logistics Service Level](welcome/logistics-service-level) for default service level

## 2. How to Configure

1. Go to **Sea Freight Settings** (single document; no list).
2. Configure each section as needed.
3. **Save** the document.

## 3. Features

### 3.1 General Settings

- **Default Company** – Company for new Sea Bookings and Sea Shipments
- **Default Branch** – Branch for new documents
- **Default Cost Center** – Cost center for job costing
- **Default Profit Center** – Profit center for revenue allocation
- **Default Currency** – Currency for charges
- **Default Incoterm** – Trade terms (FOB, CIF, etc.)
- **Default Service Level** – Logistics Service Level for sea freight

### 3.2 Location Settings

- **Default Origin Location** – Default origin for new bookings
- **Default Destination Location** – Default destination
- **Default Origin Port** – Default origin port
- **Default Destination Port** – Default destination port

### 3.3 Business Settings

- **Default Shipping Line** – Default shipping line
- **Default Freight Agent** – Default freight agent
- **Allow Creation of Sales Order** – Enable creating Sales Order from Sea Booking
- **Auto-create Job Number** – Automatically create **Job Number** records
- **Enable Milestone Tracking** – Enable Job Milestone on Sea Shipments

### 3.4 Penalty Settings

- **Default Free Time Days** – Free time before detention/demurrage
- **Detention Rate Per Day** – Detention charge rate
- **Demurrage Rate Per Day** – Demurrage charge rate

### 3.5 Calculation Settings

- **Volume to Weight Factor** – Divisor for volumetric weight
- **Chargeable Weight Calculation** – Method (Gross, Volumetric, Chargeable)
- **Default Charge Basis** – TEU Count, Container Count, Weight, Volume
- **Default Weight UOM**, **Default Volume UOM** – Units of measure

### 3.6 Integration Settings

- **Enable Vessel Tracking** – Integrate vessel tracking
- **Enable Customs Clearance Tracking** – Track customs clearance status
- **Enable EDI Integration** – Enable EDI for shipping lines

### 3.7 Container deposit (GL)

- **Deposits Pending for Refund Request** – Balance sheet account debited on **Purchase Invoice** lines for container-deposit items (with Job Number / Container accounting dimensions when configured).
- **Container Deposit Receivable Account** – Receivable (AR) account used on the **Request Deposit Refund** journal entry from **Container** (debit), with a credit to Deposits Pending for Refund Request.

For **Sea Shipment** charge rows that use a container-deposit item, the **Deposit pending refund GL** column shows this pending-refund account for reconciliation. Align **Item Group** or **Item** purchase defaults with the same account where your chart of accounts requires it.

<!-- wiki-field-reference:start -->

## Complete field reference

_All fields from DocType **Sea Freight Settings** and nested child tables, in form order (including layout breaks). Columns: **Label** with technical **field name** in backticks, **Type**, and **Description** (from the DocType definition and standard freight/ERP semantics)._

| Label (Field name) | Type | Description |
| --- | --- | --- |
| General Settings (`general_settings_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Default Company (`default_company`) | Link | **Purpose:** Creates a controlled reference to **Company** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Company**. Create the master first if it does not exist. |
| Default Branch (`default_branch`) | Link | **Purpose:** Creates a controlled reference to **Branch** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Branch**. Create the master first if it does not exist. |
| Default Cost Center (`default_cost_center`) | Link | **Purpose:** Creates a controlled reference to **Cost Center** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Cost Center**. Create the master first if it does not exist. |
| `column_break_general` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Default Profit Center (`default_profit_center`) | Link | **Purpose:** Creates a controlled reference to **Profit Center** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Profit Center**. Create the master first if it does not exist. |
| Default Currency (`default_currency`) | Link | **Purpose:** Creates a controlled reference to **Currency** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Currency**. Create the master first if it does not exist. |
| Default Incoterm (`default_incoterm`) | Link | **Purpose:** Creates a controlled reference to **Incoterm** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Incoterm**. Create the master first if it does not exist. |
| Default Service Level (`default_service_level`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Standard, Express, Economy, Premium. |
| Location Settings (`location_settings_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Default Origin Location (`default_origin_location`) | Link | **Purpose:** Creates a controlled reference to **UNLOCO** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UNLOCO**. Create the master first if it does not exist. |
| Default Destination Location (`default_destination_location`) | Link | **Purpose:** Creates a controlled reference to **UNLOCO** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UNLOCO**. Create the master first if it does not exist. |
| `column_break_location` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Default Origin Port (`default_origin_port`) | Link | **From definition:** Default origin port UNLOCO code **Purpose:** Creates a controlled reference to **UNLOCO** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UNLOCO**. Create the master first if it does not exist. |
| Default Destination Port (`default_destination_port`) | Link | **From definition:** Default destination port UNLOCO code **Purpose:** Creates a controlled reference to **UNLOCO** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UNLOCO**. Create the master first if it does not exist. |
| Business Settings (`business_settings_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Default Shipping Line (`default_shipping_line`) | Link | **Purpose:** Creates a controlled reference to **Shipping Line** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Shipping Line**. Create the master first if it does not exist. |
| Default Freight Agent (`default_freight_agent`) | Link | **Purpose:** Creates a controlled reference to **Freight Agent** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Freight Agent**. Create the master first if it does not exist. |
| `column_break_business` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Allow Creation of Sales Order (`allow_creation_of_sales_order`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Auto-create Job Number (`auto_create_job_costing`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Enable Milestone Tracking (`enable_milestone_tracking`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Penalty Settings (`penalty_settings_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Default Free Time (Days) (`default_free_time_days`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Detention Rate per Day (`detention_rate_per_day`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). |
| `column_break_penalty` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Demurrage Rate per Day (`demurrage_rate_per_day`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). |
| Alert Settings (`alert_settings_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Enable Delay Alerts (`enable_delay_alerts`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Enable Penalty Alerts (`enable_penalty_alerts`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| `column_break_alert` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Alert Check Interval (Hours) (`alert_check_interval_hours`) | Int | **Purpose:** Whole number (counts, packages, TEU count, integer quantities). **What to enter:** Digits only; no decimal point. |
| Calculation Settings (`calculation_settings_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Volume to Weight Factor (kg/m³) (`volume_to_weight_factor`) | Float | **From definition:** Factor to convert volume (m³) to weight (kg) for chargeable weight calculation **Purpose:** Mass for rating, load planning, and DG limits. **What to enter:** Numeric weight; unit is implied by the label (often kg) — match company standard. |
| Chargeable Weight Calculation (`chargeable_weight_calculation`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Actual Weight, Volume Weight, Higher of Both. |
| `column_break_calculation` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Default Calculation Method (`default_calculation_method`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Per Unit, Fixed Amount, Base Plus Additional, First Plus Additional, Percentage. |
| Default Weight UOM (`default_weight_uom`) | Link | **From definition:** Default UOM for weight in Sales Quote Sea tab and sea-related doctypes **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Default Volume UOM (`default_volume_uom`) | Link | **From definition:** Default UOM for volume in Sales Quote Sea tab and sea-related doctypes **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Default Chargeable UOM (`default_chargeable_uom`) | Link | **From definition:** Default UOM for chargeable weight in Sales Quote Sea tab and sea-related doctypes **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Integration Settings (`integration_settings_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Enable Vessel Tracking (`enable_vessel_tracking`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Enable Customs Clearance Tracking (`enable_customs_clearance_tracking`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| `column_break_integration` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Enable EDI Integration (`enable_edi_integration`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |

<!-- wiki-field-reference:end -->

## 4. Related Topics

- [Sea Booking](welcome/sea-booking)
- [Sea Shipment](welcome/sea-shipment)
- [Sea Freight Consolidation](welcome/sea-freight-consolidation)
- [Logistics Service Level](welcome/logistics-service-level)
