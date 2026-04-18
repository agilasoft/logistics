# Load Type

**Load Type** is a master that defines cargo load types for Sea Freight, Air Freight, and Transport. Examples include FCL, LCL, Bulk, Palletized.

Each load type indicates applicability (sea, air, transport) and is used for capacity planning, pricing, and service selection.

To access Load Type, go to:

**Home > Transport > Load Type**

## 1. How to Create a Load Type

1. Go to the Load Type list, click **New**.
2. Enter **Load Type Name** (e.g., "FCL", "LCL").
3. Enter **Description**.
4. Check **Sea**, **Air**, **Transport** as applicable.
5. **Save** the document.


<!-- wiki-field-reference:start -->

## Complete field reference

_All fields from DocType **Load Type** and nested child tables, in form order (including layout breaks). Columns: **Label** with technical **field name** in backticks, **Type**, and **Description** (from the DocType definition and standard freight/ERP semantics)._

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Load Type Name (`load_type_name`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Description (`description`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Is Active (`is_active`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| `column_break_ljsj` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Air (`air`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Sea (`sea`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Transport (`transport`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Transport (`transport_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Can be Consolidated (`can_be_consolidated`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Can handle Consolidation (`can_handle_consolidation`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Consolidation Settings (`consolidation_settings_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Max Consolidation Jobs (`max_consolidation_jobs`) | Int | **From definition:** Maximum number of transport jobs that can be consolidated together. 0 = unlimited **Purpose:** Whole number (counts, packages, TEU count, integer quantities). **What to enter:** Digits only; no decimal point. |
| Max Weight (kg) (`max_weight`) | Float | **From definition:** Maximum total weight for consolidated shipments. 0 = unlimited **Purpose:** Mass for rating, load planning, and DG limits. **What to enter:** Numeric weight; unit is implied by the label (often kg) — match company standard. |
| Max Volume (m³) (`max_volume`) | Float | **From definition:** Maximum total volume for consolidated shipments. 0 = unlimited **Purpose:** Volume for chargeable calculations and vessel/air capacity. **What to enter:** Decimal cubic measure per your label (e.g. CBM). |
| Consolidation Rules (`consolidation_rules`) | Long Text | **From definition:** Document specific consolidation rules, compatibility requirements, and special handling instructions **Purpose:** Long remarks: cargo description, marks & numbers, special instructions, legal text. **What to enter:** Enter the full operational or legal wording; paste from external docs if allowed by policy. |
| Allowed Transport Job Types (`allowed_transport_job_types_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Container (`container`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Non-Container (`non_container`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Special (`special`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Oversized (`oversized`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Multimodal (`multimodal`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Heavy Haul (`heavy_haul`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |

<!-- wiki-field-reference:end -->

## 2. Related Topics

- [Transport Job](welcome/transport-job)
- [Transport Capacity Settings](welcome/transport-capacity-settings)
- [Sea Booking](welcome/sea-booking)
