# Periodic Billing

**Periodic Billing** generates recurring invoices for warehouse services (storage, handling, VAS) based on contracts and usage over a period.

Industry practice: 3PLs bill monthly or weekly for storage (per pallet/day), handling (per move), and value-added services.

To access: **Home > Warehousing > Periodic Billing**

## 1. How to Use

1. Go to Periodic Billing.
2. Select **Period** (e.g. month), **Warehouse**, **Customer** (optional).
3. Run **Generate** to create draft Sales Invoices from [Warehouse Contract](welcome/warehouse-contract) and usage.
4. Review and submit invoices.


<!-- wiki-field-reference:start -->

## Complete field reference

_All fields from DocType **Periodic Billing** and nested child tables, in form order (including layout breaks). Columns: **Label** with technical **field name** in backticks, **Type**, and **Description** (from the DocType definition and standard freight/ERP semantics)._

| Label (Field name) | Type | Description |
| --- | --- | --- |
| `section_break_zfq8` | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Amended From (`amended_from`) | Link | **Purpose:** Creates a controlled reference to **Periodic Billing** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Periodic Billing**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Naming Series (`naming_series`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: PC.######. |
| Customer (`customer`) | Link | **Purpose:** Creates a controlled reference to **Customer** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Customer**. Create the master first if it does not exist. |
| Date (`date`) | Date | **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. |
| `column_break_cpbc` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Date From (`date_from`) | Date | **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. |
| Date To (`date_to`) | Date | **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. |
| Warehouse Contract (`warehouse_contract`) | Link | **Purpose:** Creates a controlled reference to **Warehouse Contract** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Warehouse Contract**. Create the master first if it does not exist. |
| Sales Invoice (`sales_invoice`) | Link | **Purpose:** Creates a controlled reference to **Sales Invoice** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Sales Invoice**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| `section_break_vdnw` | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| `charges` | Table | **Purpose:** Stores repeating **Periodic Billing Charges** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |
| Storage Details (`storage_details_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| `storage_details` | Table | **Purpose:** Stores repeating **Periodic Billing Storage** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |
| Entity (`entity_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Company (`company`) | Link | **Purpose:** Creates a controlled reference to **Company** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Company**. Create the master first if it does not exist. |
| Branch (`branch`) | Link | **Purpose:** Creates a controlled reference to **Branch** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Branch**. Create the master first if it does not exist. |
| `column_break_dimensions` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Profit Center (`profit_center`) | Link | **Purpose:** Creates a controlled reference to **Profit Center** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Profit Center**. Create the master first if it does not exist. |
| Cost Center (`cost_center`) | Link | **Purpose:** Creates a controlled reference to **Cost Center** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Cost Center**. Create the master first if it does not exist. |
| Job Number (`job_number`) | Link | **Purpose:** Creates a controlled reference to **Job Number** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Job Number**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |

#### Child table: Periodic Billing Charges (field `charges` on parent)

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Item (`item`) | Link | **Purpose:** Creates a controlled reference to **Item** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Item**. Create the master first if it does not exist. |
| Item Name (`item_name`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Charge Type (`charge_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Margin, Disbursement, Revenue, Cost. |
| Charge Category (`charge_category`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Freight, Fuel Surcharge, Terminal Handling, Customs Clearance, Documentation, Insurance, Storage, Handling, Other. |
| UOM (`uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Quantity (`quantity`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| Rate (`rate`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). |
| Total (`total`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). |
| `column_break_lthu` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Handling Unit (`handling_unit`) | Link | **Purpose:** Creates a controlled reference to **Handling Unit** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Handling Unit**. Create the master first if it does not exist. |
| Storage Location (`storage_location`) | Link | **Purpose:** Creates a controlled reference to **Storage Location** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Storage Location**. Create the master first if it does not exist. |
| Handling Unit Type (`handling_unit_type`) | Link | **Purpose:** Creates a controlled reference to **Handling Unit Type** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Handling Unit Type**. Create the master first if it does not exist. **Behaviour:** Auto-filled from `handling_unit.type` when the link/source changes — verify after edits. |
| Storage Type (`storage_type`) | Link | **Purpose:** Creates a controlled reference to **Storage Type** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Storage Type**. Create the master first if it does not exist. **Behaviour:** Auto-filled from `storage_location.storage_type` when the link/source changes — verify after edits. |
| `column_break_nbjd` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Invoiced (`invoiced`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Sales Invoice (`sales_invoice`) | Link | **Purpose:** Creates a controlled reference to **Sales Invoice** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Sales Invoice**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Warehouse Job (`warehouse_job`) | Link | **Purpose:** Creates a controlled reference to **Warehouse Job** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Warehouse Job**. Create the master first if it does not exist. |
| `section_break_mwep` | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Calculation Notes (`calculation_notes`) | Long Text | **Purpose:** Long remarks: cargo description, marks & numbers, special instructions, legal text. **What to enter:** Enter the full operational or legal wording; paste from external docs if allowed by policy. |

#### Child table: Periodic Billing Storage (field `storage_details` on parent)

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Date (`date`) | Date | **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Handling Unit (`handling_unit`) | Link | **Purpose:** Creates a controlled reference to **Handling Unit** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Handling Unit**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Volume (`volume`) | Float | **Purpose:** Volume for chargeable calculations and vessel/air capacity. **What to enter:** Decimal cubic measure per your label (e.g. CBM). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Weight (`weight`) | Float | **Purpose:** Mass for rating, load planning, and DG limits. **What to enter:** Numeric weight; unit is implied by the label (often kg) — match company standard. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| HU Count (`hu_count`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |

<!-- wiki-field-reference:end -->

## 2. Related Topics

- [Warehouse Contract](welcome/warehouse-contract)
- [Warehouse Job](welcome/warehouse-job)
- [Warehousing Module](welcome/warehousing-module)
