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
| Code (`code`) | Data | **Purpose:** Short stable code for lists, integrations, and EDI (often uppercase). **What to enter:** Unique code within this master; match what customs, carriers, or APIs expect. |
| Description (`description`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| `column_break_mkgm` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Sea (`sea`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Air (`air`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Transport (`transport`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |

<!-- wiki-field-reference:end -->

## 2. Related Topics

- [Transport Job](welcome/transport-job)
- [Transport Capacity Settings](welcome/transport-capacity-settings)
- [Sea Booking](welcome/sea-booking)
