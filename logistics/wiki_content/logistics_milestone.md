# Logistics Milestone

**Logistics Milestone** is a master that defines operational milestones used in Milestone Tracking. Examples include SF-GATE-IN, SF-LOADED, AF-DEPARTED, TR-PICKUP, TR-DELIVERED.

Each milestone has a code, description, and flags for applicability (Sea Freight, Air Freight, Transport, Customs). Job Milestone records link to this master.

To access Logistics Milestone, go to:

**Home > Logistics > Logistics Milestone**

## 1. How to Create a Logistics Milestone

1. Go to the Logistics Milestone list, click **New**.
2. Enter **Code** (e.g., "SF-GATE-IN", "AF-DEPARTED").
3. Enter **Description** (e.g., "Gate-In at Port", "Departed").
4. Check **Sea Freight**, **Air Freight**, **Transport**, **Customs** as applicable.
5. **Save** the document.


<!-- wiki-field-reference:start -->

## Complete field reference

_All fields from DocType **Logistics Milestone** and nested child tables, in form order (including layout breaks). Columns: **Label** with technical **field name** in backticks, **Type**, and **Description** (from the DocType definition and standard freight/ERP semantics)._

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Code (`code`) | Data | **Purpose:** Short stable code for lists, integrations, and EDI (often uppercase). **What to enter:** Unique code within this master; match what customs, carriers, or APIs expect. |
| Description (`description`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Icon (`icon`) | Icon | **Purpose:** Visual icon for milestones or workspace navigation. **What to enter:** Pick an icon from the selector. |
| `column_break_rydr` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Air Freight (`air_freight`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Sea Freight (`sea_freight`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Transport (`transport`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Customs (`customs`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |

<!-- wiki-field-reference:end -->

## 2. Related Topics

- [Milestone Tracking](welcome/milestone-tracking)
- [Sea Shipment](welcome/sea-shipment)
- [Air Shipment](welcome/air-shipment)
- [Transport Job](welcome/transport-job)
- [Declaration](welcome/declaration)
