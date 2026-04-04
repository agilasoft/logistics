# Stocktake Order

**Stocktake Order** is a transaction that captures physical inventory count requirements. It is used for cycle counts, full stocktakes, and blind counts to reconcile system inventory with physical stock.

A Stocktake Order records the items and locations to be counted, count type, and whether QA or blind count is required. It links to a Warehouse Job for execution.

To access Stocktake Order, go to:

**Home > Warehousing > Stocktake Order**

## 1. Prerequisites

Before creating a Stocktake Order, it is advised to set up the following:

- [Warehouse Settings](welcome/warehouse-settings)
- Items, Storage Locations (from ERPNext)

## 2. How to Create a Stocktake Order

1. Go to the Stocktake Order list, click **New**.
2. Enter **Count Date** and select **Warehouse**.
3. Select **Count Type** (Full, Cycle, etc.) and **Blind Count** if applicable.
4. Add **Items** with quantities to count.
5. **Save** the document.

## 3. Features

### 3.1 Integration with Warehouse Job

Once a Stocktake Order is confirmed, create a Warehouse Job and link it to this order. The job executes the count and posts variances.


<!-- wiki-field-reference:start -->

## Complete field reference

_All fields from DocType **Stocktake Order** and nested child tables, in form order (including layout breaks). Columns: **Label** with technical **field name** in backticks, **Type**, and **Description** (from the DocType definition and standard freight/ERP semantics)._

| Label (Field name) | Type | Description |
| --- | --- | --- |
| `section_break_z7lp` | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Amended From (`amended_from`) | Link | **Purpose:** Creates a controlled reference to **Stocktake Order** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Stocktake Order**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Naming Series (`naming_series`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: STT-.#########. |
| Date (`date`) | Date | **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. |
| Shipper (`shipper`) | Link | **Purpose:** Creates a controlled reference to **Shipper** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Shipper**. Create the master first if it does not exist. |
| Consignee (`consignee`) | Link | **Purpose:** Creates a controlled reference to **Consignee** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Consignee**. Create the master first if it does not exist. |
| Customer (`customer`) | Link | **Purpose:** Creates a controlled reference to **Customer** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Customer**. Create the master first if it does not exist. |
| Type (`type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Full, Cycle, Blind, Investigative, Ad-hoc. |
| `column_break_rtgm` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Scope (`scope`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Site, Building, Zone, Aisle, Bay, Level. |
| Contract (`contract`) | Link | **Purpose:** Creates a controlled reference to **Warehouse Contract** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Warehouse Contract**. Create the master first if it does not exist. |
| `column_break_ndxz` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Planned Date (`planned_date`) | Datetime | **Purpose:** Exact timestamp for events, SLAs, or audit (more precise than **Date** alone). **What to enter:** Pick date and time; use the time zone your process expects (often local site). |
| Due Date (`due_date`) | Datetime | **Purpose:** Exact timestamp for events, SLAs, or audit (more precise than **Date** alone). **What to enter:** Pick date and time; use the time zone your process expects (often local site). |
| Blind Count (`blind_count`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| QA Required (`qa_required`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Stocktake Days Past Zero (`stocktake_days_past_zero`) | Int | **From definition:** Number of days to include zero-stock items in stocktake count sheet if their last transaction is within this period. Items with zero stock but recent transactions will be included for counting. **Purpose:** Whole-day offset or SLA duration (e.g. days before ETD, processing days). **What to enter:** Integer only (no decimals); sign follows your process (negative = before event). |
| `section_break_mzvs` | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| `items` | Table | **Purpose:** Stores repeating **Stocktake Order Item** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |
| Charges (`charges_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| `charges` | Table | **Purpose:** Stores repeating **Stocktake Order Charges** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |
| Notes (`notes_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| `notes` | Text Editor | **Purpose:** Field type **Text Editor** — stores or displays data per Frappe standard behaviour. **What to enter:** Enter or select a value appropriate to the label; see ERPNext docs for this field type if unsure. |
| Accounts (`accounts_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Company (`company`) | Link | **Purpose:** Creates a controlled reference to **Company** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Company**. Create the master first if it does not exist. |
| Branch (`branch`) | Link | **Purpose:** Creates a controlled reference to **Branch** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Branch**. Create the master first if it does not exist. |
| Cost Center (`cost_center`) | Link | **Purpose:** Creates a controlled reference to **Cost Center** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Cost Center**. Create the master first if it does not exist. |
| Profit Center (`profit_center`) | Link | **Purpose:** Creates a controlled reference to **Profit Center** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Profit Center**. Create the master first if it does not exist. |
| `column_break_accounts` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Job Number (`job_number`) | Link | **From definition:** For revenue/cost recognition **Purpose:** Creates a controlled reference to **Job Number** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Job Number**. Create the master first if it does not exist. |

#### Child table: Stocktake Order Item (field `items` on parent)

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Item (`item`) | Link | **Purpose:** Creates a controlled reference to **Warehouse Item** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Warehouse Item**. Create the master first if it does not exist. |
| Item Name (`item_name`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). **Behaviour:** Auto-filled from `item.item_name` when the link/source changes — verify after edits. |
| UOM (`uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. **Behaviour:** Auto-filled from `item.uom` when the link/source changes — verify after edits. |
| SKU Tracking (`sku_tracking`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `item.sku_tracking` when the link/source changes — verify after edits. |
| Serial Tracking (`serial_tracking`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `item.serial_tracking` when the link/source changes — verify after edits. |
| Batch Tracking (`batch_tracking`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `item.batch_tracking` when the link/source changes — verify after edits. |
| `column_break_ivxg` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Handling Unit Type (`handling_unit_type`) | Link | **Purpose:** Creates a controlled reference to **Handling Unit Type** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Handling Unit Type**. Create the master first if it does not exist. |
| Handling Unit (`handling_unit`) | Link | **Purpose:** Creates a controlled reference to **Handling Unit** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Handling Unit**. Create the master first if it does not exist. |
| Serial No (`serial_no`) | Link | **From definition:** Can be left blank if counting all Serials. **Purpose:** Creates a controlled reference to **Warehouse Serial** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Warehouse Serial**. Create the master first if it does not exist. |
| Batch No (`batch_no`) | Link | **From definition:** Can be left blank if counting all Batches. **Purpose:** Creates a controlled reference to **Warehouse Batch** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Warehouse Batch**. Create the master first if it does not exist. |
| Measurements (`dimensions_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Length (`length`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. **Behaviour:** Auto-filled from `item.length` when the link/source changes — verify after edits. |
| Width (`width`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. **Behaviour:** Auto-filled from `item.width` when the link/source changes — verify after edits. |
| Height (`height`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. **Behaviour:** Auto-filled from `item.height` when the link/source changes — verify after edits. |
| Dimension UOM (`dimension_uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| `column_break_drkz` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Volume (`volume`) | Float | **Purpose:** Volume for chargeable calculations and vessel/air capacity. **What to enter:** Decimal cubic measure per your label (e.g. CBM). **Behaviour:** Auto-filled from `item.volume` when the link/source changes — verify after edits. |
| Volume UOM (`volume_uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Weight (`weight`) | Float | **Purpose:** Mass for rating, load planning, and DG limits. **What to enter:** Numeric weight; unit is implied by the label (often kg) — match company standard. **Behaviour:** Auto-filled from `item.weight` when the link/source changes — verify after edits. |
| Weight UOM (`weight_uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Chargeable Weight (`chargeable_weight`) | Float | **Purpose:** Mass for rating, load planning, and DG limits. **What to enter:** Numeric weight; unit is implied by the label (often kg) — match company standard. |
| Chargeable Weight UOM (`chargeable_weight_uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |

#### Child table: Stocktake Order Charges (field `charges` on parent)

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Item Code (`item_code`) | Link | **Purpose:** Creates a controlled reference to **Item** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Item**. Create the master first if it does not exist. |
| Charge Type (`charge_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Margin, Disbursement, Revenue, Cost. |
| Charge Category (`charge_category`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Freight, Fuel Surcharge, Terminal Handling, Customs Clearance, Documentation, Insurance, Storage, Handling, Other. |
| Item Name (`item_name`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| UOM (`uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| `column_break_nyoj` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Quantity (`quantity`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Currency (`currency`) | Link | **Purpose:** Creates a controlled reference to **Currency** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Currency**. Create the master first if it does not exist. |
| Rate (`rate`) | Float | **Purpose:** Unit rate or ratio used with quantity/UOM in charge calculations. **What to enter:** Decimal per your pricing rules; respect minimums/maximums on the charge line if shown. |
| Total (`total`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |

<!-- wiki-field-reference:end -->

## 4. Related Topics

- [Warehouse Job](welcome/warehouse-job)
- [Inbound Order](welcome/inbound-order)
- [Release Order](welcome/release-order)
- [Warehouse Contract](welcome/warehouse-contract)
