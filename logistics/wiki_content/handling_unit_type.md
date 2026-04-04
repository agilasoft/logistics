# Handling Unit Type

**Handling Unit Type** is a master that defines unit types for warehouse inventory tracking. Examples include Pallet, Box, Carton, Container.

To access Handling Unit Type, go to:

**Home > Warehousing > Handling Unit Type**

## 1. How to Create a Handling Unit Type

1. Go to the Handling Unit Type list, click **New**.
2. Enter **Handling Unit Type** (e.g., "Pallet", "Box").
3. Enter **Length**, **Width**, **Height** (in cm).
4. Enter **Max Gross Weight**.
5. **Save** the document.


<!-- wiki-field-reference:start -->

## Complete field reference

_All fields from DocType **Handling Unit Type** and nested child tables, in form order (including layout breaks). Columns: **Label** with technical **field name** in backticks, **Type**, and **Description** (from the DocType definition and standard freight/ERP semantics)._

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Code (`code`) | Data | **Purpose:** Short stable code for lists, integrations, and EDI (often uppercase). **What to enter:** Unique code within this master; match what customs, carriers, or APIs expect. |
| Description (`description`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Default Billing UOM (`default_billing_uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Naming Series (`naming_series`) | Data | **Purpose:** Chooses which document number sequence applies (ERPNext naming series). **What to enter:** Pick the series your organisation configured for this site or document type. |
| Allowed Storage Type (`allowed_storage_type`) | Table MultiSelect | **Purpose:** Links this record to many **Handling Unit Type Storage** rows in one control (tags / multi-link pattern). **What to enter:** Pick one or more existing **Handling Unit Type Storage** records from the picker. |
| `column_break_cady` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Notes (`notes`) | Long Text | **Purpose:** Long remarks: cargo description, marks & numbers, special instructions, legal text. **What to enter:** Enter the full operational or legal wording; paste from external docs if allowed by policy. |
| Configurations (`configurations_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Measurements (`measurements_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Dimension UOM (`dimension_uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| External Length (`external_length`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| External Width (`external_width`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| External Height (`external_height`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| `column_break_vbyj` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Tare Weight (kg) (`tare_weight_kg`) | Float | **Purpose:** Mass for rating, load planning, and DG limits. **What to enter:** Numeric weight; unit is implied by the label (often kg) — match company standard. |
| Max Gross (kg) (`max_gross_kg`) | Float | **Purpose:** Mass for rating, load planning, and DG limits. **What to enter:** Numeric weight; unit is implied by the label (often kg) — match company standard. |
| Max Volume (cbm) (`max_volume_cbm`) | Float | **Purpose:** Volume for chargeable calculations and vessel/air capacity. **What to enter:** Decimal cubic measure per your label (e.g. CBM). |
| Capacity Basis (`capacity_basis`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Weight, Volume, Count, Mixed. |
| Default Qty Capacity (`default_qty_capacity`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Storage Location Size (`storage_location_size`) | Int | **From definition:** Number of storage locations this handling unit type will occupy. When location overflow is enabled, this value will be fetched into handling units of this type. **Purpose:** Whole number (counts, packages, TEU count, integer quantities). **What to enter:** Digits only; no decimal point. |
| `column_break_wywy` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Stackable (`stackable`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Nestable (`nestable`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Returnable (`returnable`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Serializable (`serializable`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| `section_break_hjno` | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| uoms (`uoms`) | Table | **Purpose:** Stores repeating **Handling Unit Type UOM** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |
| Lift Methods (`lift_methods_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |

#### Child table (multi): Handling Unit Type Storage (field `allowed_storage_type` on parent)

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Storage Type (`storage_type`) | Link | **Purpose:** Creates a controlled reference to **Storage Type** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Storage Type**. Create the master first if it does not exist. |

#### Child table: Handling Unit Type UOM (field `uoms` on parent)

| Label (Field name) | Type | Description |
| --- | --- | --- |
| UOM (`uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Conversion (`conversion`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |

<!-- wiki-field-reference:end -->

## 2. Related Topics

- [Warehouse Job](welcome/warehouse-job)
- [Inbound Order](welcome/inbound-order)
- [Release Order](welcome/release-order)
- [Warehouse Settings](welcome/warehouse-settings)
