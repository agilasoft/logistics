# Document List Template

**Document List Template** is a master that defines which documents are required for each product type and context. It is used by the Documents tab to auto-populate document requirements on Bookings, Orders, Shipments, and Jobs.

Each template has a name (e.g., "Air Export Standard", "Sea Import FCL") and applies to a product type (Air Freight, Sea Freight, Transport, Customs, Warehousing, General, Special Projects), applies to (Booking, Shipment/Job, Both), and optionally direction and entry type.

To access Document List Template, go to:

**Home > Logistics > Document List Template**

## 1. Prerequisites

Before creating a Document List Template, it is advised to set up the following:

- [Logistics Document Type](welcome/logistics-document-type) – Master list of document types (CI, PL, BL, AWB, etc.)

## 2. How to Create a Document List Template

1. Go to the Document List Template list, click **New**.
2. Enter **Template Name** (e.g., "Air Export Standard").
3. Select **Product Type** (Air Freight, Sea Freight, Transport, Customs, Warehousing, General, Special Projects).
4. Select **Applies To** (Booking, Shipment/Job, Both).
5. Select **Direction** (Import, Export, Domestic, All) if applicable.
6. Select **Entry Type** (Direct, Transit, Transshipment, All) if applicable.
7. Check **Is Default** if this is the default template for this product when no match.
8. Add **Document List Template Items** – for each required document:
   - **Document Type** – Link to Logistics Document Type
   - **Sequence** – Display order
   - **Is Mandatory** – Required for submission
   - **Date Required Basis** – ETD, ETA, Booking Date, Job Date, Manual, None
   - **Days Offset** – Days before/after basis date (e.g., -7 = 7 days before ETD)
9. **Save** the document.

## 3. Features

### 3.1 Template Selection Logic

When a document is opened, the system finds the matching template by product type, applies to, direction, and entry type. The first match wins; otherwise the default template is used.

### 3.2 Populate from Template

On each supported doctype, the **Populate from Template** button creates/refreshes document rows from the matching template.


<!-- wiki-field-reference:start -->

## Complete field reference

_All fields from DocType **Document List Template** and nested child tables, in form order (including layout breaks). Columns: **Label** with technical **field name** in backticks, **Type**, and **Description** (from the DocType definition and standard freight/ERP semantics)._

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

- [Document Management](welcome/document-management)
- [Logistics Document Type](welcome/logistics-document-type)
- [Sea Booking](welcome/sea-booking)
- [Air Booking](welcome/air-booking)
