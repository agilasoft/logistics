# Transport Plan

**Transport Plan** is a planning view that shows Transport Jobs and Legs over a date range. Used for capacity planning, vehicle assignment, and constraint checking.

To access: **Home > Transport > Transport Plan**

## 1. Prerequisites

- [Transport Settings](welcome/transport-settings) – Forward/Backward days, constraints
- [Transport Job](welcome/transport-job) and [Transport Leg](welcome/transport-leg) records

## 2. Features

- Date range view (configurable in Transport Settings)
- Capacity vs demand
- Constraint checking (time windows, vehicle type, plate coding)
- Vehicle assignment


<!-- wiki-field-reference:start -->

## Complete field reference

_All fields from DocType **Transport Plan** and nested child tables, in form order (including layout breaks). Columns: **Label** with technical **field name** in backticks, **Type**, and **Description** (from the DocType definition and standard freight/ERP semantics)._

| Label (Field name) | Type | Description |
| --- | --- | --- |
| `section_break_9p7s` | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Naming Series (`naming_series`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: TRP.#########. |
| Amended From (`amended_from`) | Link | **Purpose:** Creates a controlled reference to **Transport Plan** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Transport Plan**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Plan Date (`plan_date`) | Date | **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. |
| Transport Planner (`transport_planner`) | Link | **Purpose:** Creates a controlled reference to **Employee** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Employee**. Create the master first if it does not exist. |
| `column_break_lgwc` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Company (`company`) | Link | **Purpose:** Creates a controlled reference to **Company** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Company**. Create the master first if it does not exist. |
| Branch (`branch`) | Link | **Purpose:** Creates a controlled reference to **Branch** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Branch**. Create the master first if it does not exist. |
| `section_break_hawq` | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| `runsheets` | Table | **Purpose:** Stores repeating **Transport Plan Run Sheets** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |

#### Child table: Transport Plan Run Sheets (field `runsheets` on parent)

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Run Sheet (`run_sheet`) | Link | **Purpose:** Creates a controlled reference to **Run Sheet** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Run Sheet**. Create the master first if it does not exist. |
| Run Date (`run_date`) | Date | **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `run_sheet.run_date` when the link/source changes — verify after edits. |
| Vehicle (`vehicle`) | Link | **Purpose:** Creates a controlled reference to **Transport Vehicle** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Transport Vehicle**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `run_sheet.vehicle` when the link/source changes — verify after edits. |
| Driver (`driver`) | Link | **Purpose:** Creates a controlled reference to **Driver** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Driver**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `run_sheet.driver` when the link/source changes — verify after edits. |

<!-- wiki-field-reference:end -->

## 3. Related Topics

- [Transport Job](welcome/transport-job)
- [Transport Leg](welcome/transport-leg)
- [Transport Settings](welcome/transport-settings)
- [Transport Module](welcome/transport-module)
