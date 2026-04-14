# Transfer Order

**Transfer Order** is a transaction that captures internal warehouse transfer requirements. It is used when moving stock between storage locations, warehouses, or for internal movements such as staging, replenishment, or rebalancing.

A Transfer Order records the items, quantities, source and destination locations, and handling requirements. It links to a Warehouse Job for execution. Unlike Inbound and Release Orders, it typically does not involve external customers—it is for internal warehouse operations.

To access Transfer Order, go to:

**Home > Warehousing > Transfer Order**

## 1. Prerequisites

Before creating a Transfer Order, it is advised to set up the following:

- [Warehouse Settings](welcome/warehouse-settings) – Warehouses, storage locations
- Items (from ERPNext)
- Storage Location masters

## 2. How to Create a Transfer Order

1. Go to the Transfer Order list, click **New**.
2. Enter **Order Date** and select **Warehouse** (if multi-warehouse).
3. Add **Items** with quantities, source and destination locations.
4. Add **Charges** if internal transfer charges apply.
5. **Save** the document.

### 2.1 Statuses

- **Draft** – Order is being prepared
- **Submitted** – Order is confirmed (when submittable)
- **Cancelled** – Order has been cancelled

## 3. Features

### 3.1 Integration with Warehouse Job

Once a Transfer Order is confirmed, create a Warehouse Job and link it to this order. The job executes the transfer between locations.


<!-- wiki-field-reference:start -->

## Complete field reference

_All fields from DocType **Transfer Order** and nested child tables, in form order (including layout breaks). Columns: **Label** with technical **field name** in backticks, **Type**, and **Description** (from the DocType definition and standard freight/ERP semantics)._

| Label (Field name) | Type | Description |
| --- | --- | --- |
| `section_break_xgkg` | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Amended From (`amended_from`) | Link | **Purpose:** Creates a controlled reference to **Transfer Order** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Transfer Order**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Series (`naming_series`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: WTR.######. |
| Order Date (`order_date`) | Date | **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. |
| Shipper (`shipper`) | Link | **Purpose:** Creates a controlled reference to **Shipper** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Shipper**. Create the master first if it does not exist. |
| Consignee (`consignee`) | Link | **Purpose:** Creates a controlled reference to **Consignee** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Consignee**. Create the master first if it does not exist. |
| Transfer Type (`transfer_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Internal, Customer, Others. |
| `column_break_zznj` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Customer (`customer`) | Link | **Purpose:** Creates a controlled reference to **Customer** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Customer**. Create the master first if it does not exist. |
| Project (`project`) | Link | **From definition:** ERPNext Project for Special Projects integration **Purpose:** Creates a controlled reference to **Project** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Project**. Create the master first if it does not exist. |
| Warehouse Contract (`contract`) | Link | **Purpose:** Creates a controlled reference to **Warehouse Contract** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Warehouse Contract**. Create the master first if it does not exist. |
| Cust. Reference (`cust_reference`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Reason (`reason`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Re-slot, Re-org, Staging, Quality, Quarantine, Returns, Others. |
| `column_break_rucg` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Priority (`priority`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Low, Normal, High. |
| Planned Date (`planned_date`) | Datetime | **Purpose:** Exact timestamp for events, SLAs, or audit (more precise than **Date** alone). **What to enter:** Pick date and time; use the time zone your process expects (often local site). |
| Due Date (`due_date`) | Datetime | **Purpose:** Exact timestamp for events, SLAs, or audit (more precise than **Date** alone). **What to enter:** Pick date and time; use the time zone your process expects (often local site). |
| `section_break_yuil` | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| `items` | Table | **Purpose:** Stores repeating **Transfer Order Item** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |
| Charges (`charges_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| `charges` | Table | **Purpose:** Stores repeating **Transfer Order Charges** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |
| Documents (`documents_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Document Checklist (`documents_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Document Summary (`documents_html`) | HTML | **Purpose:** Shows calculated or static HTML (KPIs, dashboards, embedded help, milestone views). **What to enter:** Nothing to type — content is rendered by the system. |
| Document Template (`document_list_template`) | Link | **From definition:** Override default template. Leave empty to use product default. **Purpose:** Creates a controlled reference to **Document List Template** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Document List Template**. Create the master first if it does not exist. |
| Documents (`documents`) | Table | **Purpose:** Stores repeating **Job Document** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |
| Accounts (`accounts_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Company (`company`) | Link | **Purpose:** Creates a controlled reference to **Company** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Company**. Create the master first if it does not exist. |
| Branch (`branch`) | Link | **Purpose:** Creates a controlled reference to **Branch** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Branch**. Create the master first if it does not exist. |
| Cost Center (`cost_center`) | Link | **Purpose:** Creates a controlled reference to **Cost Center** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Cost Center**. Create the master first if it does not exist. |
| Profit Center (`profit_center`) | Link | **Purpose:** Creates a controlled reference to **Profit Center** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Profit Center**. Create the master first if it does not exist. |
| `column_break_accounts` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Job Number (`job_number`) | Link | **From definition:** For revenue/cost recognition **Purpose:** Creates a controlled reference to **Job Number** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Job Number**. Create the master first if it does not exist. |

#### Child table: Transfer Order Item (field `items` on parent)

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Item (`item`) | Link | **Purpose:** Creates a controlled reference to **Warehouse Item** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Warehouse Item**. Create the master first if it does not exist. |
| Item Name (`item_name`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). **Behaviour:** Auto-filled from `item.item_name` when the link/source changes — verify after edits. |
| UOM (`uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. **Behaviour:** Auto-filled from `item.uom` when the link/source changes — verify after edits. |
| Quantity (`quantity`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| `column_break_rdbm` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| SKU Tracking (`sku_tracking`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. **Behaviour:** Auto-filled from `item.sku_tracking` when the link/source changes — verify after edits. |
| Serial Tracking (`serial_tracking`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. **Behaviour:** Auto-filled from `item.serial_tracking` when the link/source changes — verify after edits. |
| Batch Tracking (`batch_tracking`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. **Behaviour:** Auto-filled from `item.batch_tracking` when the link/source changes — verify after edits. |
| Serial No (`serial_no`) | Link | **Purpose:** Creates a controlled reference to **Warehouse Serial** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Warehouse Serial**. Create the master first if it does not exist. |
| Batch No (`batch_no`) | Link | **Purpose:** Creates a controlled reference to **Warehouse Batch** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Warehouse Batch**. Create the master first if it does not exist. |
| `section_break_rfub` | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| From (`column_break_oayf`) | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Handling Unit Type (`handling_unit_type_from`) | Link | **Purpose:** Creates a controlled reference to **Handling Unit Type** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Handling Unit Type**. Create the master first if it does not exist. |
| Handling Unit (`handling_unit_from`) | Link | **Purpose:** Creates a controlled reference to **Handling Unit** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Handling Unit**. Create the master first if it does not exist. |
| Storage Location (`storage_location_from`) | Link | **Purpose:** Creates a controlled reference to **Storage Location** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Storage Location**. Create the master first if it does not exist. |
| To (`to_column`) | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Handling Unit Type (`handling_unit_type`) | Link | **Purpose:** Creates a controlled reference to **Handling Unit Type** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Handling Unit Type**. Create the master first if it does not exist. |
| Handling Unit To (`handling_unit_to`) | Link | **Purpose:** Creates a controlled reference to **Handling Unit** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Handling Unit**. Create the master first if it does not exist. |
| Storage Location (`storage_location_to`) | Link | **Purpose:** Creates a controlled reference to **Storage Location** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Storage Location**. Create the master first if it does not exist. |
| Measurements (`dimensions_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Length (`length`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. **Behaviour:** Auto-filled from `item.length` when the link/source changes — verify after edits. |
| Width (`width`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. **Behaviour:** Auto-filled from `item.width` when the link/source changes — verify after edits. |
| Height (`height`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. **Behaviour:** Auto-filled from `item.height` when the link/source changes — verify after edits. |
| Dimension UOM (`dimension_uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| `column_break_drkz` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Volume (`volume`) | Float | **Purpose:** Volume for chargeable calculations and vessel/air capacity. **What to enter:** Decimal cubic measure per your label (e.g. CBM). |
| Volume UOM (`volume_uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Weight (`weight`) | Float | **Purpose:** Mass for rating, load planning, and DG limits. **What to enter:** Numeric weight; unit is implied by the label (often kg) — match company standard. **Behaviour:** Auto-filled from `item.weight` when the link/source changes — verify after edits. |
| Weight UOM (`weight_uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Chargeable Weight (`chargeable_weight`) | Float | **Purpose:** Mass for rating, load planning, and DG limits. **What to enter:** Numeric weight; unit is implied by the label (often kg) — match company standard. |
| Chargeable Weight UOM (`chargeable_weight_uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |

#### Child table: Transfer Order Charges (field `charges` on parent)

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Item Code (`item_code`) | Link | **Purpose:** Creates a controlled reference to **Item** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Item**. Create the master first if it does not exist. |
| Charge Type (`charge_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Margin, Disbursement, Revenue, Cost. |
| Charge Category (`charge_category`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Freight, Fuel Surcharge, Terminal Handling, Customs Clearance, Documentation, Insurance, Storage, Handling, Other. |
| Item Name (`item_name`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). **Behaviour:** Auto-filled from `item_code.item_name` when the link/source changes — verify after edits. |
| UOM (`uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. **Behaviour:** Auto-filled from `item_code.stock_uom` when the link/source changes — verify after edits. |
| `column_break_rdwy` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Quantity (`quantity`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Currency (`currency`) | Link | **Purpose:** Creates a controlled reference to **Currency** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Currency**. Create the master first if it does not exist. |
| Rate (`rate`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). |
| Total (`total`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |

#### Child table: Job Document (field `documents` on parent)

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Document Type (`document_type`) | Link | **Purpose:** Creates a controlled reference to **Logistics Document Type** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Logistics Document Type**. Create the master first if it does not exist. |
| Document Name (`document_name`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). **Behaviour:** Auto-filled from `document_type.document_name` when the link/source changes — verify after edits. |
| Document Number (`document_number`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Status (`status`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Pending, Uploaded, Done, Received, Verified, Overdue, Expired, Rejected. |
| `column_break_1` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Date Required (`date_required`) | Date | **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. |
| Date Received (`date_received`) | Date | **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. |
| Date Verified (`date_verified`) | Date | **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. |
| Expiry Date (`expiry_date`) | Date | **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. |
| Attachment (`attachment_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Attachment (`attachment`) | Attach | **Purpose:** Stores evidence: B/L, AWB, permits, POD scans, certificates. **What to enter:** Upload PDF/image from disk or drag-and-drop; use clear filenames; respect max size limits. |
| `column_break_attachment` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Required (`is_required`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Verified (`is_verified`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Verified By (`verified_by`) | Link | **Purpose:** Creates a controlled reference to **User** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **User**. Create the master first if it does not exist. |
| Issued By (`issued_by`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Overdue Days (`overdue_days`) | Int | **Purpose:** Whole-day offset or SLA duration (e.g. days before ETD, processing days). **What to enter:** Integer only (no decimals); sign follows your process (negative = before event). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Notes (`notes_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Notes (`notes`) | Small Text | **Purpose:** Short note or identifier where a full **Text** field is not needed. **What to enter:** One line of text; keep it brief for list views. |
| `column_break_meta` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Source (`source`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Manual, Fetched. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Created At (`created_at`) | Datetime | **Purpose:** Exact timestamp for events, SLAs, or audit (more precise than **Date** alone). **What to enter:** Pick date and time; use the time zone your process expects (often local site). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |

<!-- wiki-field-reference:end -->

## 4. Related Topics

- [Warehouse Jobs Operations](welcome/warehouse-jobs-operations)
- [Inbound Order](welcome/inbound-order)
- [Release Order](welcome/release-order)
- [Storage Location](welcome/storage-location)
