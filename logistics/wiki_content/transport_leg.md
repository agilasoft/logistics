# Transport Leg

**Transport Leg** is one pickup-to-delivery segment in a Transport Job or Run Sheet. A job can have multiple legs for multi-stop delivery.

Each leg has: Origin, Destination, Scheduled Date/Time, Vehicle, Driver, Status, Proof of Delivery.

To access: **Home > Transport > Transport Leg**

## 1. Prerequisites

- [Transport Job](welcome/transport-job) or [Run Sheet](welcome/run-sheet)
- Addresses for origin and destination

## 2. Features

- Created as child of Transport Job or Run Sheet
- Vehicle and driver assignment
- [Proof of Delivery](welcome/proof-of-delivery) capture
- Time window constraints (from Transport Settings)


<!-- wiki-field-reference:start -->

## Complete field reference

_All fields from DocType **Transport Leg** and nested child tables, in form order (including layout breaks). Columns: **Label** with technical **field name** in backticks, **Type**, and **Description** (from the DocType definition and standard freight/ERP semantics)._

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Map (`tab_7_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Route Map (`route_map`) | HTML | **Purpose:** Shows calculated or static HTML (KPIs, dashboards, embedded help, milestone views). **What to enter:** Nothing to type — content is rendered by the system. |
| Details (`details_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| `section_break_fcp1` | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Naming Series (`naming_series`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: L.#######. |
| Leg Type (`leg_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Job, Connecting, Dispatch, Backhaul, Return. |
| Amended From (`amended_from`) | Link | **Purpose:** Creates a controlled reference to **Transport Leg** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Transport Leg**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Date (`date`) | Date | **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. |
| Priority (`priority`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Low, Normal, High. |
| Run Date (`run_date`) | Date | **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. **Behaviour:** Auto-filled from `run_sheet.run_date` when the link/source changes — verify after edits. |
| `column_break_srly` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Transport Job (`transport_job`) | Link | **Purpose:** Creates a controlled reference to **Transport Job** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Transport Job**. Create the master first if it does not exist. |
| Transport Job Type (`transport_job_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Container, Non-Container, Special, Oversized, Multimodal, Heavy Haul. |
| Vehicle Type (`vehicle_type`) | Link | **Purpose:** Creates a controlled reference to **Vehicle Type** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Vehicle Type**. Create the master first if it does not exist. **Behaviour:** Auto-filled from `transport_job.vehicle_type` when the link/source changes — verify after edits. |
| Hazardous (`contains_dangerous_goods`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `transport_job.contains_dangerous_goods` when the link/source changes — verify after edits. |
| Refrigeration (`refrigeration`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `transport_job.refrigeration` when the link/source changes — verify after edits. |
| `column_break_jewt` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Status (`status`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Open, Assigned, Started, Completed, Billed. |
| Order (`order`) | Int | **Purpose:** Sort order or sequence number for lists and templates. **What to enter:** Whole number; lower usually appears first unless the form states otherwise. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Run Sheet (`run_sheet`) | Link | **Purpose:** Creates a controlled reference to **Run Sheet** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Run Sheet**. Create the master first if it does not exist. |
| Sales Invoice (`sales_invoice`) | Link | **Purpose:** Creates a controlled reference to **Sales Invoice** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Sales Invoice**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Pick (`pickup_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| `column_break_ddgn` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Facility Type From (`facility_type_from`) | Link | **Purpose:** Creates a controlled reference to **DocType** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **DocType**. Create the master first if it does not exist. |
| Facility From (`facility_from`) | Dynamic Link | **Purpose:** References another document whose **DocType** is chosen in field **facility_type_from** (same pattern as ERPNext Dynamic Link). **What to enter:** First set the DocType field, then pick the document **name** for that type. |
| Pick Address (`pick_address`) | Link | **Purpose:** Creates a controlled reference to **Address** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Address**. Create the master first if it does not exist. |
| `pick_address_format` | Text | **Purpose:** Multi-line narrative (instructions, clauses, template text). **What to enter:** Free text across multiple lines; use line breaks where helpful. |
| `column_break_nzht` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Pick Mode (`pick_mode`) | Link | **Purpose:** Creates a controlled reference to **Pick and Drop Mode** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Pick and Drop Mode**. Create the master first if it does not exist. |
| Pick Window Start (`pick_window_start`) | Time | **Purpose:** Clock time for shifts, gate hours, or cut-off times without a full date. **What to enter:** Time only (HH:MM or per ERPNext control). **Behaviour:** Auto-filled from `pick_address.custom_pickup_window_start` when the link/source changes — verify after edits. |
| Pick Window End (`pick_window_end`) | Time | **Purpose:** Clock time for shifts, gate hours, or cut-off times without a full date. **What to enter:** Time only (HH:MM or per ERPNext control). **Behaviour:** Auto-filled from `pick_address.custom_pickup_window_end` when the link/source changes — verify after edits. |
| Pick Consolidated (`pick_consolidated`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Signature (`pick_signature`) | Signature | **Purpose:** Captures sign-off on delivery or authorisation. **What to enter:** Sign on screen or attached pad per device. |
| Signed By (`pick_signed_by`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Drop (`drop_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| `column_break_xsyy` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Facility Type To (`facility_type_to`) | Link | **Purpose:** Creates a controlled reference to **DocType** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **DocType**. Create the master first if it does not exist. |
| Facility To (`facility_to`) | Dynamic Link | **Purpose:** References another document whose **DocType** is chosen in field **facility_type_to** (same pattern as ERPNext Dynamic Link). **What to enter:** First set the DocType field, then pick the document **name** for that type. |
| Drop Address (`drop_address`) | Link | **Purpose:** Creates a controlled reference to **Address** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Address**. Create the master first if it does not exist. |
| `drop_address_html` | Text | **Purpose:** Multi-line narrative (instructions, clauses, template text). **What to enter:** Free text across multiple lines; use line breaks where helpful. |
| `column_break_nmkr` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Drop Mode (`drop_mode`) | Link | **Purpose:** Creates a controlled reference to **Pick and Drop Mode** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Pick and Drop Mode**. Create the master first if it does not exist. |
| Drop Window Start (`drop_window_start`) | Time | **Purpose:** Clock time for shifts, gate hours, or cut-off times without a full date. **What to enter:** Time only (HH:MM or per ERPNext control). **Behaviour:** Auto-filled from `drop_address.custom_drop_window_start` when the link/source changes — verify after edits. |
| Drop Window End (`drop_window_end`) | Time | **Purpose:** Clock time for shifts, gate hours, or cut-off times without a full date. **What to enter:** Time only (HH:MM or per ERPNext control). **Behaviour:** Auto-filled from `drop_address.custom_drop_windows_end` when the link/source changes — verify after edits. |
| Drop Consolidated (`drop_consolidated`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Signature (`drop_signature`) | Signature | **Purpose:** Captures sign-off on delivery or authorisation. **What to enter:** Sign on screen or attached pad per device. |
| Signed By (`drop_signed_by`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Date Signed (`date_signed`) | Datetime | **Purpose:** Exact timestamp for events, SLAs, or audit (more precise than **Date** alone). **What to enter:** Pick date and time; use the time zone your process expects (often local site). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Routing (`routing_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Distance (km) (`distance_km`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Duration (min) (`duration_min`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Actual Distance (km) (`actual_distance_km`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Actual Duration (min) (`actual_duration_min`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| `column_break_vbhy` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Start Date (`start_date`) | Datetime | **Purpose:** Exact timestamp for events, SLAs, or audit (more precise than **Date** alone). **What to enter:** Pick date and time; use the time zone your process expects (often local site). |
| End Date (`end_date`) | Datetime | **Purpose:** Exact timestamp for events, SLAs, or audit (more precise than **Date** alone). **What to enter:** Pick date and time; use the time zone your process expects (often local site). |
| `column_break_yocf` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Routing Provider (`routing_provider`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Routing Profile (`routing_profile`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Telematics (`telematics_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| ETA at Drop (`eta_at_drop`) | Datetime | **Purpose:** Exact timestamp for events, SLAs, or audit (more precise than **Date** alone). **What to enter:** Pick date and time; use the time zone your process expects (often local site). |
| Remaining (km) (`remaining_km`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Remaining (min) (`remaining_min`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| `column_break_hdfr` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Auto Arrival Enabled (`auto_arrival_enabled`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Auto Departure Enabled (`auto_departure_enabled`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Arrival Radius (m) (`arrival_radius_m`) | Int | **Purpose:** Whole number (counts, packages, TEU count, integer quantities). **What to enter:** Digits only; no decimal point. |
| Departure Radius (m) (`departure_radius_m`) | Int | **Purpose:** Whole number (counts, packages, TEU count, integer quantities). **What to enter:** Digits only; no decimal point. |
| `column_break_pbaa` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Route Failure Reason (`route_failure_reason`) | Small Text | **Purpose:** Short note or identifier where a full **Text** field is not needed. **What to enter:** One line of text; keep it brief for list views. |
| Carbon (`carbon_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| CO₂e (kg) (`co2e_kg`) | Float | **Purpose:** Mass for rating, load planning, and DG limits. **What to enter:** Numeric weight; unit is implied by the label (often kg) — match company standard. |
| Emission Method (`co2e_method`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: PER_TON_KM, PER_KM. |
| Emission Scope Applied (`co2e_scope`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Emission Factor (`emission_factor`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Emission Factor (g/scop) (`emission_factor_gscop`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| `column_break_dreg` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Carbon Provider (`carbon_provider`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Carbon Source (`co2e_source`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Carbon Last Computed (`co2e_last_computed`) | Datetime | **Purpose:** Exact timestamp for events, SLAs, or audit (more precise than **Date** alone). **What to enter:** Pick date and time; use the time zone your process expects (often local site). |
| Cargo Weight (kg) (`cargo_weight_kg`) | Float | **Purpose:** Mass for rating, load planning, and DG limits. **What to enter:** Numeric weight; unit is implied by the label (often kg) — match company standard. |
| Operations (`operations_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Operational Details (`operations_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Delay Reasons (`delay_reasons`) | Small Text | **Purpose:** Short note or identifier where a full **Text** field is not needed. **What to enter:** One line of text; keep it brief for list views. |
| `column_break_operations` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Exception Handling Notes (`exception_handling_notes`) | Text Editor | **Purpose:** Field type **Text Editor** — stores or displays data per Frappe standard behaviour. **What to enter:** Enter or select a value appropriate to the label; see ERPNext docs for this field type if unsure. |
| Selected Route Polyline (`selected_route_polyline`) | Long Text | **Purpose:** Long remarks: cargo description, marks & numbers, special instructions, legal text. **What to enter:** Enter the full operational or legal wording; paste from external docs if allowed by policy. **Behaviour:** Hidden in default layout; may still be set by import, API, or script. |
| Selected Route Index (`selected_route_index`) | Int | **Purpose:** Whole number (counts, packages, TEU count, integer quantities). **What to enter:** Digits only; no decimal point. **Behaviour:** Hidden in default layout; may still be set by import, API, or script. |

<!-- wiki-field-reference:end -->

## 3. Related Topics

- [Transport Job](welcome/transport-job)
- [Run Sheet](welcome/run-sheet)
- [Proof of Delivery](welcome/proof-of-delivery)
- [Transport Module](welcome/transport-module)
