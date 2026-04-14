# Change Request

**Change Request** is a document used to add additional charges to an existing job (Air Shipment, Sea Shipment, Transport Job, Warehouse Job, Declaration). When approved, the charges are applied to the linked job.

To access Change Request, go to:

**Home > Pricing Center > Change Request**

## 1. How to Use

1. Open a job (e.g., Air Shipment, Transport Job).
2. Click **Create Change Request** (from the Additional Charges or custom button).
3. Add charge lines in the **Charges** child table.
4. Submit the Change Request.
5. Approve the Change Request – charges are applied to the job.
6. Optionally, create a **Sales Quote** from the Change Request for billing.

## 2. Supported Job Types

- Air Shipment
- Sea Shipment (via Sea Shipment Charges)
- Transport Job
- Warehouse Job
- Declaration


<!-- wiki-field-reference:start -->

## Complete field reference

_All fields from DocType **Change Request** and nested child tables, in form order (including layout breaks). Columns: **Label** with technical **field name** in backticks, **Type**, and **Description** (from the DocType definition and standard freight/ERP semantics)._

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Naming Series (`naming_series`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: CR-.#########. |
| Job Type (`job_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Transport Job, Warehouse Job, Air Shipment, Sea Shipment, Declaration. |
| Job (`job`) | Dynamic Link | **Purpose:** References another document whose **DocType** is chosen in field **job_type** (same pattern as ERPNext Dynamic Link). **What to enter:** First set the DocType field, then pick the document **name** for that type. |
| `column_break_cr` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Status (`status`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Draft, Submitted, Approved, Sales Quote Created. |
| Charge Items (`section_break_charges`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Charges (`charges`) | Table | **Purpose:** Stores repeating **Change Request Charge** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |
| Remarks (`section_break_remarks`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Remarks (`remarks`) | Long Text | **Purpose:** Long remarks: cargo description, marks & numbers, special instructions, legal text. **What to enter:** Enter the full operational or legal wording; paste from external docs if allowed by policy. |
| Sales Quote (`sales_quote`) | Link | **Purpose:** Creates a controlled reference to **Sales Quote** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Sales Quote**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |

#### Child table: Change Request Charge (field `charges` on parent)

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Item Code (`item_code`) | Link | **Purpose:** Creates a controlled reference to **Item** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Item**. Create the master first if it does not exist. |
| Description (`description`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| `column_break_crc` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Quantity (`quantity`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. |
| UOM (`uom`) | Link | **Purpose:** Creates a controlled reference to **UOM** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **UOM**. Create the master first if it does not exist. |
| Currency (`currency`) | Link | **Purpose:** Creates a controlled reference to **Currency** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Currency**. Create the master first if it does not exist. |
| Unit Cost (`unit_cost`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). |
| Amount (`amount`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Remarks (`remarks`) | Text | **Purpose:** Multi-line narrative (instructions, clauses, template text). **What to enter:** Free text across multiple lines; use line breaks where helpful. |

<!-- wiki-field-reference:end -->

## 3. Related Topics

- [Sales Quote](welcome/sales-quote)
- [Air Shipment](welcome/air-shipment)
- [Transport Job](welcome/transport-job)
- [Warehouse Job](welcome/warehouse-job)
- [Declaration](welcome/declaration)
