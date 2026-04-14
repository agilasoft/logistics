# Document Management (Documents Tab)

**Document Management** is a unified feature across Booking/Order and Shipment/Job doctypes that provides centralized document tracking, compliance monitoring, and overdue alerts. Documents are managed via the **Documents** tab on each supported doctype.

The Documents tab shows a checklist of required documents (Commercial Invoice, Packing List, Bill of Lading, Air Waybill, etc.) with status, date required, date received, and attachments. Document requirements are driven by **Document List Templates** configured per product type and context. Document rows are stored in the **Job Document** child table; each row links to a Logistics Document Type and tracks status, dates, attachments, and verification.

To access document configuration, go to:

**Home > Logistics > Document List Template** (setup)

## 1. Prerequisites

Before using the Documents tab, it is advised to set up the following:

- [Logistics Document Type](welcome/logistics-document-type) – Master list of document types (CI, PL, BL, AWB, etc.)
- **Document List Template** – Defines which documents are required for each product (Air Export, Sea Import FCL, Transport Job, etc.)

## 2. How to Use the Documents Tab

1. Open a supported document (e.g., Air Shipment, Sea Booking, Transport Job, Warehouse Job, Declaration).
2. Go to the **Documents** tab.
3. Click **Populate from Template** to load document requirements based on the product type, direction, and entry type.
4. For each document row:
   - **Status** – Pending, Uploaded, Done, Received, Verified, Overdue, Expired
   - **Date Required** – When the document must be available (calculated from ETD/ETA/Booking Date or manual)
   - **Attachment** – Upload the document file
   - **Date Received** – When the document was received

### 2.1 Document List Template

Document List Templates define which documents are required for each context:

- **Product Type** – Air Freight, Sea Freight, Transport, Customs, Warehousing, General
- **Applies To** – Booking, Shipment/Job, Both
- **Direction** – Import, Export, Domestic, All
- **Entry Type** – Direct, Transit, Transshipment, All

Each template has **Document List Template Items** specifying: Document Type, sequence, mandatory flag, date required basis (ETD, ETA, Booking Date, Job Date, Manual), days offset, and status flow.

## 3. Features

### 3.1 Dashboard Alerts

For doctypes with a Dashboard tab (Air Shipment, Sea Shipment, Warehouse Job, Transport Job), document alerts are shown:

- **Missing Documents** – Required documents not yet uploaded
- **Overdue Documents** – Documents past the date required
- **Expiring Soon** – Documents with expiry date within the next 7 days

On customs-related documents, dashboard-style alert cards may also surface **permit** and **exemption** counts (distinct styling) when those workflows are in use.

### 3.2 Date Required Calculation

- **ETD** – date_required = ETD + days_offset (e.g., -3 = 3 days before ETD)
- **ETA** – date_required = ETA + days_offset
- **Booking Date** – date_required = booking_date + days_offset
- **Job Date** – date_required = job date + days_offset
- **Manual** – User enters date_required

### 3.3 Supported Doctypes

**Bookings/Orders:** Air Booking, Sea Booking, Transport Order, Declaration Order, Inbound Order, Release Order, Transfer Order

**Shipments/Jobs:** Air Shipment, Sea Shipment, Sea Consolidation, Transport Job, Warehouse Job, General Job, Declaration, Special Project


<!-- wiki-field-reference:start -->

## Complete field reference

_All fields from DocTypes **Job Document**, **Document List Template** (subsections below) and their nested child tables, in form order. Columns: **Label** (`field name`), **Type**, **Description**._

### Job Document

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

### Document List Template

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Template Name (`template_name`) | Data | **Purpose:** Short free-text for codes, references, or labels that are not master-linked. **What to enter:** Type the value as it should appear on print/PDF (no line breaks). |
| Product Type (`product_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Air Freight, Sea Freight, Transport, Customs, Warehousing, Special Projects, General. |
| Applies To (`applies_to`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Booking, Shipment/Job, Both. |
| `column_break_1` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Direction (`direction`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Import, Export, Domestic, All. |
| Entry Type (`entry_type`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: Direct, Transit, Transshipment, ATA Carnet, All. |
| Default Template (`is_default`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Description (`section_break_desc`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Description (`description`) | Small Text | **Purpose:** Short note or identifier where a full **Text** field is not needed. **What to enter:** One line of text; keep it brief for list views. |
| Document Requirements (`documents_section`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Documents (`documents`) | Table | **Purpose:** Stores repeating **Document List Template Item** lines (child records) such as packages, charges, legs, or documents. **What to enter:** Use **Add row**, fill each line, and remove rows you do not need. Save the parent to persist child rows. |

#### Child table: Document List Template Item (field `documents` on parent)

| Label (Field name) | Type | Description |
| --- | --- | --- |
| Document Type (`document_type`) | Link | **Purpose:** Creates a controlled reference to **Logistics Document Type** so party, place, item, or document data stays consistent for reporting and integrations. **What to enter:** Type to search or click the link icon; select an existing **Logistics Document Type**. Create the master first if it does not exist. |
| Sequence (`sequence`) | Int | **Purpose:** Sort order or sequence number for lists and templates. **What to enter:** Whole number; lower usually appears first unless the form states otherwise. |
| Mandatory (`is_mandatory`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| `column_break_1` | Column Break | **Purpose:** Continues the current row in a second column (standard ERP two-column layout). **What to enter:** No data — layout only. |
| Date Required Basis (`date_required_basis`) | Select | **Purpose:** Constrains input to predefined values (compliance, mode, status, or internal classification). **What to enter:** Pick exactly one value from the list: ETD, ETA, Booking Date, Job Date, Manual, None. |
| Days Offset (`days_offset`) | Int | **From definition:** Negative = before basis date, Positive = after **Purpose:** Whole-day offset or SLA duration (e.g. days before ETD, processing days). **What to enter:** Integer only (no decimals); sign follows your process (negative = before event). |
| Allow Early Upload (`allow_early_upload`) | Check | **Purpose:** Boolean flag that drives validation, billing, DG handling, or UI (depending on the field label). **What to enter:** Tick **Yes** / enabled, untick **No** / disabled. |
| Description (`section_break_desc`) | Section Break | **Purpose:** Visual grouping and optional heading for the fields that follow (improves long freight forms). **What to enter:** No data — informational layout only. |
| Description (`description`) | Small Text | **Purpose:** Short note or identifier where a full **Text** field is not needed. **What to enter:** One line of text; keep it brief for list views. |

<!-- wiki-field-reference:end -->

## 4. Related Topics

- [Sea Shipment](welcome/sea-shipment)
- [Air Shipment](welcome/air-shipment)
- [Transport Job](welcome/transport-job)
- [Warehouse Job](welcome/warehouse-job)
- [Milestone Tracking](welcome/milestone-tracking)
