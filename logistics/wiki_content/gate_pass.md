# Gate Pass

**Gate Pass** is a document authorizing movement of goods through a warehouse or facility gate. Used for outbound releases, transfers, or returns.

Industry practice: Gate pass = gate release, outbound permit. Guards check gate pass before allowing trucks to leave.

To access: **Home > Warehousing > Gate Pass**

## 1. How to Create

Typically created from [Release Order](welcome/release-order) or [Transfer Order](welcome/transfer-order) when goods are ready for dispatch.

## 2. Features

- Links to Release Order or Transfer Order
- Vehicle/driver details
- Gate-in/gate-out timestamps
- [Pages Overview](welcome/pages-overview) (Plate Scanner) for gate scanning


<!-- wiki-field-reference:start -->

## Complete field reference

_All fields from DocType **Gate Pass** and nested child tables, in form order (including layout breaks). Columns: **Label** with technical **field name** in backticks, **Type**, and **Description** (from the DocType definition and standard freight/ERP semantics)._

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Basic Information (`section_break_basic_info`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Series (`naming_series`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: GP-.########. |
| Gate Pass Date (`gate_pass_date`) | Date | **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. |
| Gate Pass Time (`gate_pass_time`) | Time | **Purpose:** Clock time for shifts, gate hours, or cut-off times without a full date. **What to enter:** Time only (HH:MM or per ERPNext control). |
| `column_break_references` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Warehouse Job (`warehouse_job`) | Link | **Purpose:** Creates a controlled reference to **Warehouse Job** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Warehouse Job**. Create the master first if it does not exist. |
| Job Type (`job_type`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Reference Order Type (`reference_order_type`) | Link | **Purpose:** Creates a controlled reference to **DocType** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **DocType**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Reference Order (`reference_order`) | Dynamic Link | **Purpose:** References another document whose **DocType** is chosen in field **reference_order_type** (same pattern as ERPNext Dynamic Link). **What to enter:** First set the DocType field, then pick the document **name** for that type. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Customer (`customer`) | Link | **Purpose:** Creates a controlled reference to **Customer** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Customer**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `warehouse_job.customer` when the link/source changes — verify after edits. |
| Docking Details (`docking_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Dock Door (`dock_door`) | Link | **Purpose:** Creates a controlled reference to **Dock Door** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Dock Door**. Create the master first if it does not exist. |
| ETA (`eta`) | Datetime | **Purpose:** Exact timestamp for events, SLAs, or audit (more precise than **Date** alone). **What to enter:** Pick date and time; use the time zone your process expects (often local site). |
| `column_break_transport` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Transport Company (`transport_company`) | Link | **Purpose:** Creates a controlled reference to **Transport Company** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Transport Company**. Create the master first if it does not exist. |
| Vehicle Type (`vehicle_type`) | Link | **Purpose:** Creates a controlled reference to **Vehicle Type** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Vehicle Type**. Create the master first if it does not exist. |
| Plate No. (`plate_no`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Driver Name (`driver_name`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Driver Contact (`driver_contact`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Container Type (`container_type`) | Link | **Purpose:** Creates a controlled reference to **Container Type** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Container Type**. Create the master first if it does not exist. |
| Container No. (`container_no`) | Data | **Purpose:** Carrier, customs, or commercial reference printed on transport or customs documents. **What to enter:** The exact identifier from the MAWB/HAWB, B/L, container interchange, or tax invoice. |
| Items (`section_break_items`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Items (`items`) | Table | **Purpose:** Stores repeating **Gate Pass Item** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |
| Authorization (`section_break_authorization`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Authorized By (`authorized_by`) | Link | **Purpose:** Creates a controlled reference to **User** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **User**. Create the master first if it does not exist. |
| Authorized Date (`authorized_date`) | Date | **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. |
| `column_break_security` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Security Checked By (`security_checked_by`) | Link | **Purpose:** Creates a controlled reference to **User** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **User**. Create the master first if it does not exist. |
| Security Check Time (`security_check_time`) | Datetime | **Purpose:** Exact timestamp for events, SLAs, or audit (more precise than **Date** alone). **What to enter:** Pick date and time; use the time zone your process expects (often local site). |
| Security Notes (`security_notes`) | Small Text | **Purpose:** Short note or identifier where a full **Text** field is not needed. **What to enter:** One line of text; keep it brief for list views. |
| Status (`section_break_status`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Status (`status`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Draft, Authorized, In Progress, Completed, Cancelled. |
| Actual In Time (`actual_in_time`) | Datetime | **Purpose:** Exact timestamp for events, SLAs, or audit (more precise than **Date** alone). **What to enter:** Pick date and time; use the time zone your process expects (often local site). |
| Actual Out Time (`actual_out_time`) | Datetime | **Purpose:** Exact timestamp for events, SLAs, or audit (more precise than **Date** alone). **What to enter:** Pick date and time; use the time zone your process expects (often local site). |
| Notes (`notes_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| `notes` | Text Editor | **Purpose:** Field type **Text Editor** — stores or displays data per Frappe standard behaviour. **What to enter:** Enter or select a value appropriate to the label; see ERPNext docs for this field type if unsure. |
| Transaction Entity (`transaction_entity_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Company (`company`) | Link | **Purpose:** Creates a controlled reference to **Company** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Company**. Create the master first if it does not exist. |
| Branch (`branch`) | Link | **Purpose:** Creates a controlled reference to **Branch** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Branch**. Create the master first if it does not exist. |

#### Child table: Gate Pass Item (field `items` on parent)

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Item Code (`item_code`) | Link | **Purpose:** Creates a controlled reference to **Warehouse Item** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Warehouse Item**. Create the master first if it does not exist. |
| Item Name (`item_name`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `item_code.item_name` when the link/source changes — verify after edits. |
| Description (`description`) | Small Text | **Purpose:** Short note or identifier where a full **Text** field is not needed. **What to enter:** One line of text; keep it brief for list views. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `item_code.description` when the link/source changes — verify after edits. |
| `column_break_quantity` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Quantity (`qty`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| UOM (`uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `item_code.uom` when the link/source changes — verify after edits. |
| `column_break_location` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Branch (`branch`) | Link | **Purpose:** Creates a controlled reference to **Branch** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Branch**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `parent.branch` when the link/source changes — verify after edits. |
| Handling Unit (`handling_unit`) | Link | **Purpose:** Creates a controlled reference to **Handling Unit** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Handling Unit**. Create the master first if it does not exist. |

<!-- wiki-field-reference:end -->

## 3. Related Topics

- [Release Order](welcome/release-order)
- [Transfer Order](welcome/transfer-order)
- [Plate Scanner](welcome/pages-overview)
- [Warehousing Module](welcome/warehousing-module)
