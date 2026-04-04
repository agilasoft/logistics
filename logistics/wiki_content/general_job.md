# General Job

**General Job** is a flexible job document for multi-leg or combined logistics operations that do not fit a single product type. It can link to Air Shipments, Sea Shipments, Transport Jobs, Warehouse Jobs, and Declarations.

A General Job is used when a shipment involves multiple modes (e.g., sea + transport + customs) and you need a parent job to track the overall flow. It has a Documents tab and optional Milestones tab.

To access General Job, go to:

**Home > Logistics > General Job**

## 1. Prerequisites

Before creating a General Job, it is advised to set up the following:

- [Logistics Milestone](welcome/logistics-milestone) – If using milestones
- [Document List Template](welcome/document-list-template) – For document tracking

## 2. How to Create a General Job

1. Go to the General Job list, click **New**.
2. Enter **Job Date** and select **Customer**.
3. Add **Reference** links to Air Shipment, Sea Shipment, Transport Job, Warehouse Job, or Declaration as needed.
4. Add **Documents** and **Milestones** if applicable.
5. **Save** the document.

## 3. Features

### 3.1 Documents Tab

The Documents tab allows you to track required documents. Use **Populate from Template** to load document requirements.

### 3.2 Integration with Other Jobs

General Job links to child jobs (Air Shipment, Sea Shipment, etc.) for end-to-end visibility.

### 3.3 Profitability (from GL)

When **Job Number** and **Company** are set, the form displays a Profitability section with revenue, cost, gross profit, WIP, and accrual from the General Ledger. See [Job Management Module](welcome/job-management-module).


<!-- wiki-field-reference:start -->

## Complete field reference

_All fields from DocType **General Job** and nested child tables, in form order (including layout breaks). Columns: **Label** with technical **field name** in backticks, **Type**, and **Description** (from the DocType definition and standard freight/ERP semantics)._

| Label (Field name) | Type | Description |
| --- | --- | --- |
| `section_break_co9p` | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Amended From (`amended_from`) | Link | **Purpose:** Creates a controlled reference to **General Job** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **General Job**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Naming Series (`naming_series`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: GEN.######. |
| Job Open Date (`job_open_date`) | Date | **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. |
| `column_break_cjac` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Customer (`customer`) | Link | **Purpose:** Creates a controlled reference to **Customer** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Customer**. Create the master first if it does not exist. |
| Accounts (`accounts_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Company (`company`) | Link | **Purpose:** Creates a controlled reference to **Company** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Company**. Create the master first if it does not exist. |
| Branch (`branch`) | Link | **Purpose:** Creates a controlled reference to **Branch** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Branch**. Create the master first if it does not exist. |
| Cost Center (`cost_center`) | Link | **Purpose:** Creates a controlled reference to **Cost Center** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Cost Center**. Create the master first if it does not exist. |
| Profit Center (`profit_center`) | Link | **Purpose:** Creates a controlled reference to **Profit Center** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Profit Center**. Create the master first if it does not exist. |
| `column_break_zmfn` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Job Number (`job_number`) | Link | **Purpose:** Creates a controlled reference to **Job Number** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Job Number**. Create the master first if it does not exist. |
| Revenue & Cost Recognition (`recognition_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Enable WIP Recognition (`wip_recognition_enabled`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Enable Accrual Recognition (`accrual_recognition_enabled`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Applicable Recognition Policy (`recognition_policy_reference`) | Small Text | **From definition:** Matched policy + parameter row for this job. **Purpose:** Short note or identifier where a full **Text** field is not needed. **What to enter:** One line of text; keep it brief for list views. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Recognition Date Basis (`recognition_date_basis`) | Select | **From definition:** From policy (single basis for WIP and accrual). **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: ATA, ATD, Job Booking Date, Job Creation, User Specified. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Recognition Date (`recognition_date`) | Date | **From definition:** Posting date for WIP and accrual. Editable when basis is User Specified. **Purpose:** Calendar date for the business event described by the label. **What to enter:** Choose the date from the picker; must reflect operational truth. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| `column_break_recognition` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Estimated Revenue (`estimated_revenue`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| WIP Amount (`wip_amount`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Recognized Revenue (`recognized_revenue`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| WIP Journal Entry (`wip_journal_entry`) | Link | **Purpose:** Creates a controlled reference to **Journal Entry** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Journal Entry**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| WIP Adjustment JE (`wip_adjustment_journal_entry`) | Link | **Purpose:** Creates a controlled reference to **Journal Entry** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Journal Entry**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| WIP Closed (`wip_closed`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| `column_break_accrual` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Estimated Costs (`estimated_costs`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Accrual Amount (`accrual_amount`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Recognized Costs (`recognized_costs`) | Currency | **Purpose:** Money amount in the document’s commercial context (freight, duty, insured value). **What to enter:** Amount in the currency indicated by field **currency** on this form (or company default). **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Accrual Journal Entry (`accrual_journal_entry`) | Link | **Purpose:** Creates a controlled reference to **Journal Entry** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Journal Entry**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Accrual Adjustment JE (`accrual_adjustment_journal_entry`) | Link | **Purpose:** Creates a controlled reference to **Journal Entry** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Journal Entry**. Create the master first if it does not exist. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Accrual Closed (`accrual_closed`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Sustainability (`sustainability_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Sustainability Metrics (`sustainability_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Estimated Energy Consumption (kWh) (`estimated_energy_consumption`) | Float | **Purpose:** Decimal quantity or measurement (weight, volume, count with decimals). **What to enter:** Enter a number using site decimal precision. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| Estimated Carbon Footprint (kg CO2e) (`estimated_carbon_footprint`) | Float | **Purpose:** Mass for rating, load planning, and DG limits. **What to enter:** Numeric weight; unit is implied by the label (often kg) — match company standard. **Behaviour:** Read-only here — value comes from calculation, another field, or workflow. |
| `column_break_sustainability` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Sustainability Notes (`sustainability_notes`) | Text | **Purpose:** Multi-line narrative (instructions, clauses, template text). **What to enter:** Free text across multiple lines; use line breaks where helpful. |
| Documents (`documents_tab`) | Tab Break | **Purpose:** Organises the form into tabs so related fields are easier to scan and edit. **What to enter:** No data — click the tab to show or hide its fields. |
| Document Checklist (`documents_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Document Summary (`documents_html`) | HTML | **Purpose:** Shows calculated or static HTML (KPIs, dashboards, embedded help, milestone views). **What to enter:** Nothing to type — content is rendered by the system. |
| Document Template (`document_list_template`) | Link | **From definition:** Override default template. Leave empty to use product default. **Purpose:** Creates a controlled reference to **Document List Template** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Document List Template**. Create the master first if it does not exist. |
| Documents (`documents`) | Table | **Purpose:** Stores repeating **Job Document** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |

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

- [Sea Shipment](welcome/sea-shipment)
- [Air Shipment](welcome/air-shipment)
- [Transport Job](welcome/transport-job)
- [Document Management](welcome/document-management)
- [Job Management Module](welcome/job-management-module)
