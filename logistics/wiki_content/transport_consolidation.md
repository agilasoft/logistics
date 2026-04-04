# Transport Consolidation

**Transport Consolidation** groups multiple Transport Jobs for shared truckload or multi-stop optimization. Reduces cost and improves vehicle utilization.

Industry practice: LTL consolidation, milk runs, multi-stop routes.

To access: **Home > Transport > Transport Consolidation**

## 1. Prerequisites

- [Transport Job](welcome/transport-job) records to consolidate
- [Transport Settings](welcome/transport-settings) – consolidation rules

## 2. How to Create

1. Go to Transport Consolidation list, click **New**.
2. Add **Transport Jobs** to consolidate.
3. Assign **Vehicle** and **Driver**.
4. **Save**.

## 3. Features

- Links multiple Transport Jobs
- Route optimization
- Consolidation Savings Report for analysis


<!-- wiki-field-reference:start -->

## Complete field reference

_All fields from DocType **Transport Consolidation** and nested child tables, in form order (including layout breaks). Columns: **Label** with technical **field name** in backticks, **Type**, and **Description** (from the DocType definition and standard freight/ERP semantics)._

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Dashboard (`dashboard_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Dashboard (`dashboard_html`) | HTML | **Purpose:** Shows calculated or static HTML (KPIs, dashboards, embedded help, milestone views). **What to enter:** Nothing to type — content is rendered by the system. |
| Naming Series (`naming_series`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: TC.#########. |
| Consolidation Date (`consolidation_date`) | Date | **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. |
| `column_break_1` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Consolidation Type (`consolidation_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Route, Pick, Drop, Both. |
| Load Type (`load_type`) | Link | **From definition:** The Load Type for this consolidation. All jobs must have the same Load Type. **Purpose:** Creates a controlled reference to **Load Type** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Load Type**. Create the master first if it does not exist. |
| Transport Jobs (`section_break_jobs`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Transport Jobs (`transport_jobs`) | Table | **Purpose:** Stores repeating **Transport Consolidation Job** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |
| Consolidation Details (`section_break_details`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Total Weight (`total_weight`) | Float | **Purpose:** Mass for rating, load planning, and DG limits. **What to enter:** Numeric weight; unit is implied by the label (often kg) — match company standard. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Total Volume (`total_volume`) | Float | **Purpose:** Volume for chargeable calculations and vessel/air capacity. **What to enter:** Decimal cubic measure per your label (e.g. CBM). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Total Volume UOM (`total_volume_uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Total Weight UOM (`total_weight_uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| `column_break_2` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Consolidation Notes (`consolidation_notes`) | Text Editor | **Purpose:** Field type **Text Editor** — stores or displays data per Frappe standard behaviour. **What to enter:** Enter or select a value appropriate to the label; see ERPNext docs for this field type if unsure. |
| Run Sheet (`run_sheet_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Run Sheet (`run_sheet`) | Link | **Purpose:** Creates a controlled reference to **Run Sheet** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Run Sheet**. Create the master first if it does not exist. |
| Accounts (`accounts_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Company (`company`) | Link | **Purpose:** Creates a controlled reference to **Company** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Company**. Create the master first if it does not exist. |
| Branch (`branch`) | Link | **Purpose:** Creates a controlled reference to **Branch** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Branch**. Create the master first if it does not exist. |
| Cost Center (`cost_center`) | Link | **Purpose:** Creates a controlled reference to **Cost Center** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Cost Center**. Create the master first if it does not exist. |
| Profit Center (`profit_center`) | Link | **Purpose:** Creates a controlled reference to **Profit Center** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Profit Center**. Create the master first if it does not exist. |
| Job Number (`job_number`) | Link | **Purpose:** Creates a controlled reference to **Job Number** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Job Number**. Create the master first if it does not exist. |
| Amended From (`amended_from`) | Link | **Purpose:** Creates a controlled reference to **Transport Consolidation** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Transport Consolidation**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |

#### Child table: Transport Consolidation Job (field `transport_jobs` on parent)

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Transport Job (`transport_job`) | Link | **Purpose:** Creates a controlled reference to **Transport Job** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Transport Job**. Create the master first if it does not exist. |
| Customer (`customer`) | Link | **Purpose:** Creates a controlled reference to **Customer** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Customer**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `transport_job.customer` when the link/source changes — verify after edits. |
| `column_break_1` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Weight (kg) (`weight`) | Float | **Purpose:** Mass for rating, load planning, and DG limits. **What to enter:** Numeric weight; unit is implied by the label (often kg) — match company standard. |
| Volume (m³) (`volume`) | Float | **Purpose:** Volume for chargeable calculations and vessel/air capacity. **What to enter:** Decimal cubic measure per your label (e.g. CBM). |
| `column_break_2` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Pick Address (`pick_address`) | Link | **Purpose:** Creates a controlled reference to **Address** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Address**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Drop Address (`drop_address`) | Link | **Purpose:** Creates a controlled reference to **Address** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Address**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |

<!-- wiki-field-reference:end -->

## 4. Related Topics

- [Transport Job](welcome/transport-job)
- [Transport Leg](welcome/transport-leg)
- [Run Sheet](welcome/run-sheet)
- [Transport Module](welcome/transport-module)
