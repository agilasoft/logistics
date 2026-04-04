# VAS Order (Value-Added Services)

**VAS Order** is a transaction that captures value-added service requirements for warehouse operations. Examples include labeling, repacking, kitting, quality inspection, fumigation, and other custom services.

A VAS Order records the customer, items, service types, quantities, and charges. It links to a Warehouse Job for execution. VAS Orders can be standalone or linked to Inbound/Release Orders.

To access VAS Order, go to:

**Home > Warehousing > VAS Order**

## 1. Prerequisites

Before creating a VAS Order, it is advised to set up the following:

- [Warehouse Settings](welcome/warehouse-settings)
- [VAS Order Type](welcome/vas-order-type) – Master list of service types
- Customer, Items (from ERPNext)

## 2. How to Create a VAS Order

1. Go to the VAS Order list, click **New**.
2. Enter **Order Date** and select **Customer**.
3. Add **Items** with service type, quantity, and charges.
4. **Save** the document.

## 3. Features

### 3.1 Integration with Warehouse Job

Once a VAS Order is confirmed, create a Warehouse Job and link it to this order. The job executes the value-added services.


<!-- wiki-field-reference:start -->

## Complete field reference

_All fields from DocType **VAS Order** and nested child tables, in form order (including layout breaks). Columns: **Label** with technical **field name** in backticks, **Type**, and **Description** (from the DocType definition and standard freight/ERP semantics)._

| Label (Field name) | Type | Description |
| --- | --- | --- |
| `section_break_rh0z` | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Amended From (`amended_from`) | Link | **Purpose:** Creates a controlled reference to **VAS Order** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **VAS Order**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Series (`naming_series`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: VAS.######. |
| Order Date (`order_date`) | Date | **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. |
| Shipper (`shipper`) | Link | **Purpose:** Creates a controlled reference to **Shipper** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Shipper**. Create the master first if it does not exist. |
| Consignee (`consignee`) | Link | **Purpose:** Creates a controlled reference to **Consignee** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Consignee**. Create the master first if it does not exist. |
| Type (`type`) | Link | **Purpose:** Creates a controlled reference to **VAS Order Type** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **VAS Order Type**. Create the master first if it does not exist. |
| `column_break_berz` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Customer (`customer`) | Link | **Purpose:** Creates a controlled reference to **Customer** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Customer**. Create the master first if it does not exist. |
| Project (`project`) | Link | **From definition:** ERPNext Project for Special Projects integration **Purpose:** Creates a controlled reference to **Project** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Project**. Create the master first if it does not exist. |
| Contract (`contract`) | Link | **Purpose:** Creates a controlled reference to **Warehouse Contract** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Warehouse Contract**. Create the master first if it does not exist. |
| Cust. Reference (`cust_reference`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| `column_break_vsgc` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Priority (`priority`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Low, Medium, High. |
| Planned Date (`planned_date`) | Datetime | **Purpose:** Exact timestamp for events, SLAs, or audit (more precise than **Date** alone). **What to enter:** Pick date and time; use the time zone your process expects (often local site). |
| Due Date (`due_date`) | Datetime | **Purpose:** Exact timestamp for events, SLAs, or audit (more precise than **Date** alone). **What to enter:** Pick date and time; use the time zone your process expects (often local site). |
| `section_break_cwsn` | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| `items` | Table | **Purpose:** Stores repeating **VAS Order Item** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |
| Charges (`tab_2_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| `charges` | Table | **Purpose:** Stores repeating **VAS Order Charges** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |
| Accounts (`accounts_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Company (`company`) | Link | **Purpose:** Creates a controlled reference to **Company** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Company**. Create the master first if it does not exist. |
| Branch (`branch`) | Link | **Purpose:** Creates a controlled reference to **Branch** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Branch**. Create the master first if it does not exist. |
| Cost Center (`cost_center`) | Link | **Purpose:** Creates a controlled reference to **Cost Center** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Cost Center**. Create the master first if it does not exist. |
| Profit Center (`profit_center`) | Link | **Purpose:** Creates a controlled reference to **Profit Center** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Profit Center**. Create the master first if it does not exist. |
| `column_break_accounts` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Job Number (`job_number`) | Link | **From definition:** For revenue/cost recognition **Purpose:** Creates a controlled reference to **Job Number** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Job Number**. Create the master first if it does not exist. |

#### Child table: VAS Order Item (field `items` on parent)

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Item (`item`) | Link | **Purpose:** Creates a controlled reference to **Warehouse Item** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Warehouse Item**. Create the master first if it does not exist. |
| Item Name (`item_name`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). **Behaviour:** Auto-filled from `item.item_name` when the link/source changes — verify after edits. |
| UOM (`uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. **Behaviour:** Auto-filled from `item.uom` when the link/source changes — verify after edits. |
| Quantity (`quantity`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| SKU Tracking (`sku_tracking`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `item.sku_tracking` when the link/source changes — verify after edits. |
| Serial Tracking (`serial_tracking`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `item.serial_tracking` when the link/source changes — verify after edits. |
| Batch Tracking (`batch_tracking`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `item.batch_tracking` when the link/source changes — verify after edits. |
| `column_break_kytz` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Handling Unit Type (`handling_unit_type`) | Link | **Purpose:** Creates a controlled reference to **Handling Unit Type** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Handling Unit Type**. Create the master first if it does not exist. |
| Handling Unit (`handling_unit`) | Link | **Purpose:** Creates a controlled reference to **Handling Unit** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Handling Unit**. Create the master first if it does not exist. |
| Serial No (`serial_no`) | Link | **Purpose:** Creates a controlled reference to **Warehouse Serial** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Warehouse Serial**. Create the master first if it does not exist. |
| Batch No (`batch_no`) | Link | **Purpose:** Creates a controlled reference to **Warehouse Batch** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Warehouse Batch**. Create the master first if it does not exist. |
| Measurements (`dimensions_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Length (`length`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. **Behaviour:** Auto-filled from `item.length` when the link/source changes — verify after edits. |
| Width (`width`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. **Behaviour:** Auto-filled from `item.width` when the link/source changes — verify after edits. |
| Height (`height`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. **Behaviour:** Auto-filled from `item.height` when the link/source changes — verify after edits. |
| Dimension UOM (`dimension_uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| `column_break_pnda` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Volume (`volume`) | Float | **Purpose:** Volume for chargeable calculations and vessel/air capacity. **What to enter:** Decimal cubic measure per your label (e.g. CBM). |
| Volume UOM (`volume_uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Weight (`weight`) | Float | **Purpose:** Mass for rating, load planning, and DG limits. **What to enter:** Numeric weight; unit is implied by the label (often kg) — match company standard. **Behaviour:** Auto-filled from `item.weight` when the link/source changes — verify after edits. |
| Weight UOM (`weight_uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Chargeable Weight (`chargeable_weight`) | Float | **Purpose:** Mass for rating, load planning, and DG limits. **What to enter:** Numeric weight; unit is implied by the label (often kg) — match company standard. |
| Chargeable Weight UOM (`chargeable_weight_uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |

#### Child table: VAS Order Charges (field `charges` on parent)

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Item Code (`item_code`) | Link | **Purpose:** Creates a controlled reference to **Item** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Item**. Create the master first if it does not exist. |
| Charge Type (`charge_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Margin, Disbursement, Revenue, Cost. |
| Charge Category (`charge_category`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Freight, Fuel Surcharge, Terminal Handling, Customs Clearance, Documentation, Insurance, Storage, Handling, Other. |
| Item Name (`item_name`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| UOM (`uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| `column_break_ncfj` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Quantity (`quantity`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Currency (`currency`) | Link | **Purpose:** Creates a controlled reference to **Currency** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Currency**. Create the master first if it does not exist. |
| Rate (`rate`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). |
| Total (`total`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). |

<!-- wiki-field-reference:end -->

## 4. Related Topics

- [Warehouse Job](welcome/warehouse-job)
- [Inbound Order](welcome/inbound-order)
- [Release Order](welcome/release-order)
- [Warehouse Contract](welcome/warehouse-contract)
