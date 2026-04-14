# Storage Location

**Storage Location** is a master that defines storage locations within a warehouse. It supports hierarchy (Warehouse > Zone > Aisle > Rack > Level > Bin) for putaway and pick operations.

To access Storage Location, go to:

**Home > Warehousing > Storage Location**

## 1. How to Create a Storage Location

1. Go to the Storage Location list, click **New**.
2. Enter **Storage Location Name**.
3. Select **Parent Storage Location** (for hierarchy) or leave blank for top-level.
4. Select **Warehouse** (from ERPNext).
5. **Save** the document.


<!-- wiki-field-reference:start -->

## Complete field reference

_All fields from DocType **Storage Location** and nested child tables, in form order (including layout breaks). Columns: **Label** with technical **field name** in backticks, **Type**, and **Description** (from the DocType definition and standard freight/ERP semantics)._

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Site (`site`) | Link | **Purpose:** Creates a controlled reference to **Storage Location Configurator** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Storage Location Configurator**. Create the master first if it does not exist. |
| Building (`building`) | Link | **Purpose:** Creates a controlled reference to **Storage Location Configurator** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Storage Location Configurator**. Create the master first if it does not exist. |
| Zone (`zone`) | Link | **Purpose:** Creates a controlled reference to **Storage Location Configurator** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Storage Location Configurator**. Create the master first if it does not exist. |
| Aisle (`aisle`) | Link | **Purpose:** Creates a controlled reference to **Storage Location Configurator** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Storage Location Configurator**. Create the master first if it does not exist. |
| Bay (`bay`) | Link | **Purpose:** Creates a controlled reference to **Storage Location Configurator** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Storage Location Configurator**. Create the master first if it does not exist. |
| Level (`level`) | Link | **Purpose:** Creates a controlled reference to **Storage Location Configurator** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Storage Location Configurator**. Create the master first if it does not exist. |
| Location Code (`location_code`) | Data | **Purpose:** Short stable code for lists, integrations, and EDI (often uppercase). **What to enter:** Unique code within this master; match what customs, carriers, or APIs expect. |
| `column_break_mquf` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Site Code (`site_code`) | Data | **Purpose:** Short stable code for lists, integrations, and EDI (often uppercase). **What to enter:** Unique code within this master; match what customs, carriers, or APIs expect. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `site.code` when the link/source changes — verify after edits. |
| Building Code (`building_code`) | Data | **Purpose:** Short stable code for lists, integrations, and EDI (often uppercase). **What to enter:** Unique code within this master; match what customs, carriers, or APIs expect. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `building.code` when the link/source changes — verify after edits. |
| Zone Code (`zone_code`) | Data | **Purpose:** Short stable code for lists, integrations, and EDI (often uppercase). **What to enter:** Unique code within this master; match what customs, carriers, or APIs expect. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `zone.code` when the link/source changes — verify after edits. |
| Aisle Code (`aisle_code`) | Data | **Purpose:** Short stable code for lists, integrations, and EDI (often uppercase). **What to enter:** Unique code within this master; match what customs, carriers, or APIs expect. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `aisle.code` when the link/source changes — verify after edits. |
| Bay Code (`bay_code`) | Data | **Purpose:** Short stable code for lists, integrations, and EDI (often uppercase). **What to enter:** Unique code within this master; match what customs, carriers, or APIs expect. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `bay.code` when the link/source changes — verify after edits. |
| Level Code (`level_code`) | Data | **Purpose:** Short stable code for lists, integrations, and EDI (often uppercase). **What to enter:** Unique code within this master; match what customs, carriers, or APIs expect. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `level.code` when the link/source changes — verify after edits. |
| Configuration (`configuration_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| `column_break_fgum` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Allow Mix Batches (`allow_mix_batches`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Allow Mix Items (`allow_mix_items`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Allow Mix Customers (`allow_mix_customers`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Dedicated Item (`dedicated_item`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Staging Area (`staging_area`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Pick Face (`pick_face`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| `column_break_anrj` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Status (`status`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Available, Assigned, In Use, Under Maintenance, Inactive. |
| Storage Type (`storage_type`) | Link | **Purpose:** Creates a controlled reference to **Storage Type** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Storage Type**. Create the master first if it does not exist. |
| Bin Priority (`bin_priority`) | Int | **Purpose:** Whole number (counts, packages, TEU count, integer quantities). **What to enter:** Digits only; no decimal point. |
| Max HU Slot (`max_hu_slot`) | Int | **Purpose:** Whole number (counts, packages, TEU count, integer quantities). **What to enter:** Digits only; no decimal point. |
| Item (`item`) | Link | **Purpose:** Creates a controlled reference to **Warehouse Item** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Warehouse Item**. Create the master first if it does not exist. |
| Capacity Management (`capacity_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Measurements (`measurements_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Max Volume (`max_volume`) | Float | **Purpose:** Volume for chargeable calculations and vessel/air capacity. **What to enter:** Decimal cubic measure per your label (e.g. CBM). |
| Max Weight (`max_weight`) | Float | **Purpose:** Mass for rating, load planning, and DG limits. **What to enter:** Numeric weight; unit is implied by the label (often kg) — match company standard. |
| Max Height (`max_height`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Max Width (`max_width`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Max Length (`max_length`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Capacity UOM (`capacity_uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Weight UOM (`weight_uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Current Volume (`current_volume`) | Float | **Purpose:** Volume for chargeable calculations and vessel/air capacity. **What to enter:** Decimal cubic measure per your label (e.g. CBM). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Current Weight (`current_weight`) | Float | **Purpose:** Mass for rating, load planning, and DG limits. **What to enter:** Numeric weight; unit is implied by the label (often kg) — match company standard. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Utilization % (`utilization_percentage`) | Percent | **Purpose:** Percentage for margins, duty rates, or capacity use. **What to enter:** Numeric percent (often 0–100); confirm whether the form expects whole percent or fraction. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Capacity Alerts (`capacity_alerts_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Enable Capacity Alerts (`enable_capacity_alerts`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Volume Alert Threshold (`volume_alert_threshold`) | Percent | **Purpose:** Percentage for margins, duty rates, or capacity use. **What to enter:** Numeric percent (often 0–100); confirm whether the form expects whole percent or fraction. |
| Weight Alert Threshold (`weight_alert_threshold`) | Percent | **Purpose:** Percentage for margins, duty rates, or capacity use. **What to enter:** Numeric percent (often 0–100); confirm whether the form expects whole percent or fraction. |
| Utilization Alert Threshold (`utilization_alert_threshold`) | Percent | **Purpose:** Percentage for margins, duty rates, or capacity use. **What to enter:** Numeric percent (often 0–100); confirm whether the form expects whole percent or fraction. |
| Entity (`entity_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Company (`company`) | Link | **Purpose:** Creates a controlled reference to **Company** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Company**. Create the master first if it does not exist. |
| Branch (`branch`) | Link | **Purpose:** Creates a controlled reference to **Branch** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Branch**. Create the master first if it does not exist. |

<!-- wiki-field-reference:end -->

## 2. Related Topics

- [Warehouse Job](welcome/warehouse-job)
- [Inbound Order](welcome/inbound-order)
- [Release Order](welcome/release-order)
- [Warehouse Settings](welcome/warehouse-settings)
