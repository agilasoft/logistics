# Warehouse Settings

**Warehouse Settings** is a single-document configuration that defines default values and behavior for the Warehousing module. It controls billing, capacity, storage, handling units, and integration options.

To access Warehouse Settings, go to:

**Home > Warehousing > Warehouse Settings**

## 1. Prerequisites

Before configuring Warehouse Settings, ensure the following are set up:

- Company, Branch, Cost Center (from ERPNext)
- Warehouse (from ERPNext Stock)
- [Storage Location](welcome/storage-location) – For storage hierarchy
- [Handling Unit Type](welcome/handling-unit-type) – For inventory tracking

## 2. How to Configure

1. Go to **Warehouse Settings** (single document; no list).
2. Configure each section as needed.
3. **Save** the document.

## 3. Features

### 3.1 General Settings

- **Default Company** – Company for new warehouse documents
- **Default Branch** – Branch for warehouse operations
- **Default Cost Center** – Cost center for warehouse costs
- **Default Warehouse** – Default warehouse for operations

### 3.2 Billing Settings

- **Enable Periodic Billing** – Enable automated periodic billing for storage
- **Billing Frequency** – Daily, Weekly, Monthly
- **Default Billing Currency** – Currency for warehouse charges

### 3.3 Capacity Settings

- **Enable Capacity Management** – Track and enforce capacity limits
- **Capacity Alert Threshold (%)** – Alert when capacity exceeds this percentage
- **Default Volume UOM** – CBM, CFT for capacity
- **Default Weight UOM** – kg, lb for capacity

### 3.4 Storage Settings

- **Default Storage Type** – Default storage type for locations
- **Default Storage Environment** – Ambient, Cold, Frozen, etc.
- **Enable Storage Location Configurator** – Use configurator for location setup

### 3.5 Handling Unit Settings

- **Default Handling Unit Type** – Default for inbound/outbound
- **Enable Handling Unit Tracking** – Track handling units (pallets, boxes)
- **Handling Unit Barcode Format** – Barcode format for scanning

### 3.6 Integration Settings

- **Enable Plate Scanner** – Enable license plate scanning at dock
- **Enable Count Sheet** – Enable count sheet for stocktake
- **Enable Gate Pass** – Enable gate pass for movements

### 3.7 Sustainability Settings

- **Enable Carbon Footprint** – Track carbon for warehouse operations
- **Enable Energy Consumption Tracking** – Track energy usage


<!-- wiki-field-reference:start -->

## Complete field reference

_All fields from DocType **Warehouse Settings** and nested child tables, in form order (including layout breaks). Columns: **Label** with technical **field name** in backticks, **Type**, and **Description** (from the DocType definition and standard freight/ERP semantics)._

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Company (`company`) | Link | **Purpose:** Creates a controlled reference to **Company** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Company**. Create the master first if it does not exist. |
| Warehouse Contract Address (`warehouse_contract_address`) | Link | **Purpose:** Creates a controlled reference to **Address** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Address**. Create the master first if it does not exist. |
| Default Cost Center (`default_cost_center`) | Link | **Purpose:** Creates a controlled reference to **Cost Center** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Cost Center**. Create the master first if it does not exist. |
| `column_break_tsti` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Planned Date Offset Days (`planned_date_offset_days`) | Int | **Purpose:** Whole-day offset or SLA duration (e.g. days before ETD, processing days). **What to enter:** Integer only (no decimals); sign follows your process (negative = before event). |
| Stocktake Days Past Zero (`stocktake_days_past_zero`) | Int | **From definition:** Number of days to include zero-stock items in stocktake count sheet if their last transaction is within this period. Items with zero stock but recent transactions will be included for counting. **Purpose:** Whole-day offset or SLA duration (e.g. days before ETD, processing days). **What to enter:** Integer only (no decimals); sign follows your process (negative = before event). |
| Allocation Level Limit (`allocation_level_limit`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Building, Aisle, Rack, Level, Position. |
| Allow Emergency Fallback (`allow_emergency_fallback`) | Check | **From definition:** Check this if emergency fallback allocation is allowed. **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Split Quantity Decimal Precision (`split_quantity_decimal_precision`) | Int | **Purpose:** Whole number (counts, packages, TEU count, integer quantities). **What to enter:** Digits only; no decimal point. |
| Replenishment Policy (`replenishment_policy`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: None, Replenish, Pick Face First. |
| Default Site (`default_site`) | Link | **Purpose:** Creates a controlled reference to **Storage Location Configurator** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Storage Location Configurator**. Create the master first if it does not exist. |
| Default Facility (`default_facility`) | Link | **Purpose:** Creates a controlled reference to **Storage Location Configurator** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Storage Location Configurator**. Create the master first if it does not exist. |
| Billing (`billing_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Billing Settings (`billing_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| `column_break_2` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Enable Volume Billing (`enable_volume_billing`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| VAS Total Sum Type (`vas_total_sum_type`) | Select | **From definition:** For VAS jobs, defines which items to include in total volume, weight, and handling units calculations. 'Both' sums all items (default behavior), 'Pick' only sums items with VAS Action = Pick, 'Putaway' only sums items with VAS Action = Putaway. **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Both, Pick, Putaway. |
| Capacity (`capacity_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Capacity Management (`capacity_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Enable Capacity Management (`enable_capacity_management`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Prevent Exceeding Capacity Limit (`prevent_exceeding_capacity_limit`) | Check | **From definition:** When checked, prevents processing of warehouse jobs (submit, post, etc.) when capacity limits are exceeded on handling units or locations. **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Capacity Tolerance Percentage (`capacity_tolerance_percentage`) | Percent | **From definition:** Allowable percentage by which capacity can be exceeded before blocking submission. For example, 5% allows jobs to be submitted if capacity is exceeded by up to 5% (e.g., 1.05 > 1.00 for a 5% tolerance). Set to 0 for strict enforcement (only allows exact capacity). **Purpose:** Percentage for margins, duty rates, or capacity use. **What to enter:** Numeric percent (often 0–100); confirm whether the form expects whole percent or fraction. |
| Enable Location Overflow (`enable_location_overflow`) | Check | **From definition:** When enabled, allows handling units to be split across multiple storage locations based on the 'Storage Location Size' field in the Handling Unit. This enables overflow allocation when a handling unit exceeds a single location's capacity. **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Round Down Allocation Qty in Putaway (`round_down_allocation_qty`) | Check | **From definition:** When checked, rounds down allocation quantity in putaway to whole numbers that do not exceed capacity. This ensures allocated quantities are whole numbers and never exceed the available capacity. **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Default Volume UOM (`default_volume_uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Volume Calculation Precision (`volume_calculation_precision`) | Int | **Purpose:** Whole number (counts, packages, TEU count, integer quantities). **What to enter:** Digits only; no decimal point. |
| Default Weight UOM (`default_weight_uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Default Chargeable UOM (`default_chargeable_uom`) | Link | **From definition:** Default UOM for chargeable weight in Sales Quote Warehousing tab and warehousing-related doctypes **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Default Dimension UOM (`default_dimension_uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| `column_break_cwga` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Default Volume Alert Threshold (`default_volume_alert_threshold`) | Percent | **Purpose:** Percentage for margins, duty rates, or capacity use. **What to enter:** Numeric percent (often 0–100); confirm whether the form expects whole percent or fraction. |
| Default Weight Alert Threshold (`default_weight_alert_threshold`) | Percent | **Purpose:** Percentage for margins, duty rates, or capacity use. **What to enter:** Numeric percent (often 0–100); confirm whether the form expects whole percent or fraction. |
| Default Utilization Alert Threshold (`default_utilization_alert_threshold`) | Percent | **Purpose:** Percentage for margins, duty rates, or capacity use. **What to enter:** Numeric percent (often 0–100); confirm whether the form expects whole percent or fraction. |
| `column_break_wzxc` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Default Pallet Volume (`default_pallet_volume`) | Float | **From definition:** Enter volume in m³ **Purpose:** Volume for chargeable calculations and vessel/air capacity. **What to enter:** Decimal cubic measure per your label (e.g. CBM). |
| Default Pallet Weight (`default_pallet_weight`) | Float | **From definition:** Enter weight in kg **Purpose:** Mass for rating, load planning, and DG limits. **What to enter:** Numeric weight; unit is implied by the label (often kg) — match company standard. |
| Default Box Volume (`default_box_volume`) | Float | **From definition:** Enter volume in m³ **Purpose:** Volume for chargeable calculations and vessel/air capacity. **What to enter:** Decimal cubic measure per your label (e.g. CBM). |
| Default Box Weight (`default_box_weight`) | Float | **From definition:** Enter weight in kg **Purpose:** Mass for rating, load planning, and DG limits. **What to enter:** Numeric weight; unit is implied by the label (often kg) — match company standard. |
| Sustainability (`sustainability_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Sustainability Settings (`sustainability_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Enable Sustainability Tracking (`enable_sustainability_tracking`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Green Certification Requirements (`green_certification_requirements`) | Table | **Purpose:** Stores repeating **Green Certification** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |
| Default Carbon Emission Factors (`default_carbon_emission_factors`) | Table | **Purpose:** Stores repeating **Carbon Emission Factor** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |
| Standard Costing (`standard_costing_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Standard Costing Settings (`standard_costing_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Enable Standard Costing (`enable_standard_costing`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Post GL Entry for Standard Costing (`post_gl_entry_for_standard_costing`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |

#### Child table: Green Certification (field `green_certification_requirements` on parent)

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Certification Name (`certification_name`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Certification Type (`certification_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Energy Efficiency, Carbon Neutral, LEED, BREEAM, ISO 14001, Green Building, Renewable Energy, Other. |
| Certification Body (`certification_body`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Certification Date (`certification_date`) | Date | **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. |
| Expiry Date (`expiry_date`) | Date | **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. |
| Certification Level (`certification_level`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Platinum, Gold, Silver, Bronze, Certified, Basic. |
| Certification Number (`certification_number`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Notes (`notes`) | Text | **Purpose:** Multi-line narrative (instructions, clauses, template text). **What to enter:** Free text across multiple lines; use line breaks where helpful. |

#### Child table: Carbon Emission Factor (field `default_carbon_emission_factors` on parent)

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Emission Source (`emission_source`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Factor Value (kg CO2e per unit) (`factor_value`) | Float | **Purpose:** Mass for rating, load planning, and DG limits. **What to enter:** Numeric weight; unit is implied by the label (often kg) — match company standard. |
| Unit of Measure (`unit_of_measure`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Factor Type (`factor_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Default, Regional, Industry-Specific, Custom. |
| Validity Period (`validity_period`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Notes (`notes`) | Text | **Purpose:** Multi-line narrative (instructions, clauses, template text). **What to enter:** Free text across multiple lines; use line breaks where helpful. |

<!-- wiki-field-reference:end -->

## 4. Related Topics

- [Inbound Order](welcome/inbound-order)
- [Release Order](welcome/release-order)
- [Warehouse Job](welcome/warehouse-job)
- [Warehouse Contract](welcome/warehouse-contract)
- [Storage Location](welcome/storage-location)
- [Handling Unit Type](welcome/handling-unit-type)
