# Run Sheet

**Run Sheet** groups Transport Legs for a driver/vehicle. Used to assign a set of pickups and deliveries to one run. Supports mobile scanning via [Run Sheet Scan](welcome/run-sheet-scan) page.

To access: **Home > Transport > Run Sheet**

## 1. Prerequisites

- [Transport Leg](welcome/transport-leg) records (from Transport Jobs)
- [Transport Vehicle](welcome/transport-vehicle), Driver

## 2. How to Create

1. Go to Run Sheet list, click **New**.
2. Select **Vehicle** and **Driver**.
3. Add **Legs** (from unassigned Transport Legs).
4. Set **Date** and sequence.
5. **Save**.

## 3. Features

- Groups legs for one driver
- Mobile execution via Run Sheet Scan page
- Route sequence
- Status tracking (Planned, In Progress, Completed)


<!-- wiki-field-reference:start -->

## Complete field reference

_All fields from DocType **Run Sheet** and nested child tables, in form order (including layout breaks). Columns: **Label** with technical **field name** in backticks, **Type**, and **Description** (from the DocType definition and standard freight/ERP semantics)._

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Dashboard (`map_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Route Map (`route_map`) | HTML | **Purpose:** Shows calculated or static HTML (KPIs, dashboards, embedded help, milestone views). **What to enter:** Nothing to type — content is rendered by the system. |
| Details (`details_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| `section_break_e1zq` | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Amended From (`amended_from`) | Link | **Purpose:** Creates a controlled reference to **Run Sheet** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Run Sheet**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Naming Series (`naming_series`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: RS.#########. |
| Run Date (`run_date`) | Datetime | **Purpose:** Exact timestamp for events, SLAs, or audit (more precise than **Date** alone). **What to enter:** Pick date and time; use the time zone your process expects (often local site). |
| Run Type (`run_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Regular, Backload, Spot, Reposition, Others. |
| Route Name (`route_name`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Transport Consolidation (`transport_consolidation`) | Link | **Purpose:** Creates a controlled reference to **Transport Consolidation** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Transport Consolidation**. Create the master first if it does not exist. |
| `column_break_gwan` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Status (`status`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Draft, Dispatched, In-Progress, Hold, Completed, Cancelled. |
| Vehicle Type (`vehicle_type`) | Link | **Purpose:** Creates a controlled reference to **Vehicle Type** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Vehicle Type**. Create the master first if it does not exist. |
| Trailer Type (`trailer_type`) | Link | **Purpose:** Creates a controlled reference to **Vehicle Type** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Vehicle Type**. Create the master first if it does not exist. |
| Vehicle (`vehicle`) | Link | **Purpose:** Creates a controlled reference to **Transport Vehicle** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Transport Vehicle**. Create the master first if it does not exist. |
| Transport Company (`transport_company`) | Link | **Purpose:** Creates a controlled reference to **Transport Company** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Transport Company**. Create the master first if it does not exist. |
| Driver (`driver`) | Link | **Purpose:** Creates a controlled reference to **Driver** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Driver**. Create the master first if it does not exist. |
| Driver Name (`driver_name`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `driver.full_name` when the link/source changes — verify after edits. |
| Dispatch and Return (`dispatch_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| `column_break_aftz` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Dispatch Terminal (`dispatch_terminal`) | Link | **Purpose:** Creates a controlled reference to **Transport Terminal** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Transport Terminal**. Create the master first if it does not exist. |
| Dispatcher (`dispatcher`) | Link | **Purpose:** Creates a controlled reference to **Employee** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Employee**. Create the master first if it does not exist. |
| Estimated Dispatch Datetime (`estimated_dispatch_datetime`) | Datetime | **Purpose:** Exact timestamp for events, SLAs, or audit (more precise than **Date** alone). **What to enter:** Pick date and time; use the time zone your process expects (often local site). |
| `column_break_vvon` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Return Terminal (`return_terminal`) | Link | **Purpose:** Creates a controlled reference to **Transport Terminal** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Transport Terminal**. Create the master first if it does not exist. |
| Return Inspector (`return_inspector`) | Link | **Purpose:** Creates a controlled reference to **Employee** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Employee**. Create the master first if it does not exist. |
| Estimated Return Datetime (`estimated_return_datetime`) | Datetime | **Purpose:** Exact timestamp for events, SLAs, or audit (more precise than **Date** alone). **What to enter:** Pick date and time; use the time zone your process expects (often local site). |
| Transport Leg (`transport_leg_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| `legs` | Table | **Purpose:** Stores repeating **Run Sheet Leg** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| `section_break_pkdh` | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Estimated Completion Time (`estimated_completion_time`) | Datetime | **Purpose:** Exact timestamp for events, SLAs, or audit (more precise than **Date** alone). **What to enter:** Pick date and time; use the time zone your process expects (often local site). |
| Actual Completion Time (`actual_completion_time`) | Datetime | **Purpose:** Exact timestamp for events, SLAs, or audit (more precise than **Date** alone). **What to enter:** Pick date and time; use the time zone your process expects (often local site). |
| Route Optimization Score (`route_optimization_score`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Selected Route Polyline (`selected_route_polyline`) | Long Text | **Purpose:** Long remarks: cargo description, marks & numbers, special instructions, legal text. **What to enter:** Enter the full operational or legal wording; paste from external docs if allowed by policy. **Behaviour:** Hidden in default layout; may still be set by import, API, or script. |
| Selected Route Index (`selected_route_index`) | Int | **Purpose:** Whole number (counts, packages, TEU count, integer quantities). **What to enter:** Digits only; no decimal point. **Behaviour:** Hidden in default layout; may still be set by import, API, or script. |

#### Child table: Run Sheet Leg (field `legs` on parent)

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Transport Leg (`transport_leg`) | Link | **Purpose:** Creates a controlled reference to **Transport Leg** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Transport Leg**. Create the master first if it does not exist. |
| Transport Job (`transport_job`) | Link | **Purpose:** Creates a controlled reference to **Transport Job** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Transport Job**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `transport_leg.transport_job` when the link/source changes — verify after edits. |
| Customer (`customer`) | Link | **Purpose:** Creates a controlled reference to **Customer** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Customer**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `transport_job.customer` when the link/source changes — verify after edits. |
| `section_break_ssrh` | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Facility Type From (`facility_type_from`) | Link | **Purpose:** Creates a controlled reference to **DocType** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **DocType**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `transport_leg.facility_type_from` when the link/source changes — verify after edits. |
| Facility From (`facility_from`) | Dynamic Link | **Purpose:** References another document whose **DocType** is chosen in field **facility_type_from** (same pattern as ERPNext Dynamic Link). **What to enter:** First set the DocType field, then pick the document **name** for that type. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `transport_leg.facility_from` when the link/source changes — verify after edits. |
| Pick Mode (`pick_mode`) | Link | **Purpose:** Creates a controlled reference to **Pick and Drop Mode** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Pick and Drop Mode**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `transport_leg.pick_mode` when the link/source changes — verify after edits. |
| Address From (`address_from`) | Link | **Purpose:** Creates a controlled reference to **Address** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Address**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `transport_leg.pick_address` when the link/source changes — verify after edits. |
| `column_break_nstg` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Facility Type To (`facility_type_to`) | Link | **Purpose:** Creates a controlled reference to **DocType** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **DocType**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `transport_leg.facility_type_to` when the link/source changes — verify after edits. |
| Facility To (`facility_to`) | Dynamic Link | **Purpose:** References another document whose **DocType** is chosen in field **facility_type_to** (same pattern as ERPNext Dynamic Link). **What to enter:** First set the DocType field, then pick the document **name** for that type. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `transport_leg.facility_to` when the link/source changes — verify after edits. |
| Drop Mode (`drop_mode`) | Link | **Purpose:** Creates a controlled reference to **Pick and Drop Mode** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Pick and Drop Mode**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `transport_leg.drop_mode` when the link/source changes — verify after edits. |
| Address To (`address_to`) | Link | **Purpose:** Creates a controlled reference to **Address** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Address**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `transport_leg.drop_address` when the link/source changes — verify after edits. |

<!-- wiki-field-reference:end -->

## 4. Related Topics

- [Transport Leg](welcome/transport-leg)
- [Run Sheet Scan](welcome/run-sheet-scan)
- [Transport Job](welcome/transport-job)
- [Transport Module](welcome/transport-module)
