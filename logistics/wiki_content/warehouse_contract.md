# Warehouse Contract

**Warehouse Contract** is a master that defines the commercial terms between the warehouse operator and the customer. It specifies storage rates, handling rates, value-added service rates, and billing terms.

A Warehouse Contract is linked to Inbound Orders and Release Orders for billing. It supports periodic billing for storage and one-time charges for handling and VAS.

To access Warehouse Contract, go to:

**Home > Warehousing > Warehouse Contract**

## 1. Prerequisites

Before creating a Warehouse Contract, it is advised to set up the following:

- Customer (from ERPNext)
- [Warehouse Settings](welcome/warehouse-settings)
- [Storage Location](welcome/storage-location) – For storage rates
- [VAS Order Type](welcome/vas-order-type) – For VAS rates

## 2. How to Create a Warehouse Contract

1. Go to the Warehouse Contract list, click **New**.
2. Enter **Contract Name** and select **Customer**.
3. Enter **Start Date** and **End Date**.
4. Add **Storage Rates** (per CBM, per pallet, etc.).
5. Add **Handling Rates** (receiving, putaway, pick, release).
6. Add **VAS Rates** (labeling, repacking, etc.).
7. **Save** the document.

## 3. Features

### 3.1 Billing

Warehouse Contract is used for automated periodic billing and for calculating charges on Inbound Orders, Release Orders, and Warehouse Jobs.


<!-- wiki-field-reference:start -->

## Complete field reference

_All fields from DocType **Warehouse Contract** and nested child tables, in form order (including layout breaks). Columns: **Label** with technical **field name** in backticks, **Type**, and **Description** (from the DocType definition and standard freight/ERP semantics)._

| Label (Field name) | Type | Description |
| --- | --- | --- |
| `section_break_upjh` | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Amended From (`amended_from`) | Link | **Purpose:** Creates a controlled reference to **Warehouse Contract** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Warehouse Contract**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Date (`date`) | Date | **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. |
| Customer (`customer`) | Link | **Purpose:** Creates a controlled reference to **Customer** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Customer**. Create the master first if it does not exist. |
| `column_break_djlp` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Valid until (`valid_until`) | Date | **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. |
| Site (`site`) | Link | **Purpose:** Creates a controlled reference to **Storage Location Configurator** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Storage Location Configurator**. Create the master first if it does not exist. |
| Sales Quote (`sales_quote`) | Link | **Purpose:** Creates a controlled reference to **Sales Quote** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Sales Quote**. Create the master first if it does not exist. |
| Shipper (`shipper`) | Link | **Purpose:** Creates a controlled reference to **Shipper** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Shipper**. Create the master first if it does not exist. |
| Consignee (`consignee`) | Link | **Purpose:** Creates a controlled reference to **Consignee** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Consignee**. Create the master first if it does not exist. |
| `section_break_cvch` | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| `items` | Table | **Purpose:** Stores repeating **Warehouse Contract Item** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |
| Connections (`connections_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Accounts (`accounts_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Company (`company`) | Link | **Purpose:** Creates a controlled reference to **Company** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Company**. Create the master first if it does not exist. |
| Branch (`branch`) | Link | **Purpose:** Creates a controlled reference to **Branch** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Branch**. Create the master first if it does not exist. |
| Profit Center (`profit_center`) | Link | **Purpose:** Creates a controlled reference to **Profit Center** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Profit Center**. Create the master first if it does not exist. |
| Cost Center (`cost_center`) | Link | **Purpose:** Creates a controlled reference to **Cost Center** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Cost Center**. Create the master first if it does not exist. |
| `column_break_accounts` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Job Number (`job_number`) | Link | **From definition:** For revenue/cost recognition **Purpose:** Creates a controlled reference to **Job Number** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Job Number**. Create the master first if it does not exist. |

#### Child table: Warehouse Contract Item (field `items` on parent)

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Item Charge (`item_charge`) | Link | **Purpose:** Creates a controlled reference to **Item** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Item**. Create the master first if it does not exist. |
| Item Name (`item_name`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). **Behaviour:** Auto-filled from `item_charge.item_name` when the link/source changes — verify after edits. |
| Storage Charge (`storage_charge`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `item_charge.custom_storage_charge` when the link/source changes — verify after edits. |
| Inbound Charge (`inbound_charge`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `item_charge.custom_inbound_charge` when the link/source changes — verify after edits. |
| Outbound Charge (`outbound_charge`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `item_charge.custom_outbound_charge` when the link/source changes — verify after edits. |
| Transfer Charge (`transfer_charge`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `item_charge.custom_transfer_charge` when the link/source changes — verify after edits. |
| VAS Charge (`vas_charge`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `item_charge.custom_vas_charge` when the link/source changes — verify after edits. |
| Stocktake Charge (`stocktake_charge`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. **Behaviour:** Auto-filled from `item_charge.custom_stocktake_charge` when the link/source changes — verify after edits. |
| `column_break_oijb` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Handling Unit Type (`handling_unit_type`) | Link | **Purpose:** Creates a controlled reference to **Handling Unit Type** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Handling Unit Type**. Create the master first if it does not exist. |
| Storage Type (`storage_type`) | Link | **Purpose:** Creates a controlled reference to **Storage Type** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Storage Type**. Create the master first if it does not exist. |
| Calculation Method (`calculation_method`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Per Unit, Fixed Amount, Base Plus Additional, First Plus Additional, Percentage. |
| Unit Type (`unit_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Handling Unit, Weight, Chargeable Weight, Volume, Package, Piece, Job, TEU, Operation Time. |
| Volume Calculation Method (`volume_calculation_method`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Daily Volume, Peak Volume, Average Volume, End Volume. |
| Container Type (`container_type`) | Link | **Purpose:** Creates a controlled reference to **Container Type** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Container Type**. Create the master first if it does not exist. |
| `column_break_zaxi` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| UOM (`uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Currency (`currency`) | Link | **Purpose:** Creates a controlled reference to **Currency** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Currency**. Create the master first if it does not exist. |
| Rate (`rate`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). |
| Minimum Quantity (`minimum_quantity`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Minimum Charge (`minimum_charge`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). |
| Maximum Charge (`maximum_charge`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). |
| Base Amount (`base_amount`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). |
| Billing Time Settings (`billing_time_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Billing Time Unit (`billing_time_unit`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Day, Week, Hour. |
| `column_break_nrhl` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Billing Time Multiplier (`billing_time_multiplier`) | Float | **From definition:** Multiplier for billing time calculation (e.g., 1.5 for 1.5x rate) **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Minimum Billing Time (`minimum_billing_time`) | Float | **From definition:** Minimum billing time to charge (e.g., minimum 1 day) **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |

<!-- wiki-field-reference:end -->

## 4. Related Topics

- [Inbound Order](welcome/inbound-order)
- [Release Order](welcome/release-order)
- [Warehouse Job](welcome/warehouse-job)
- [Warehouse Settings](welcome/warehouse-settings)
