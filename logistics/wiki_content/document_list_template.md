# Document List Template

**Document List Template** is a master that defines which documents are required for each product type and context. It is used by the Documents tab to auto-populate document requirements on Bookings, Orders, Shipments, and Jobs.

Each template has a name (e.g., "Air Export Standard", "Sea Import FCL") and applies to a product type (Air Freight, Sea Freight, Transport, Customs, Warehousing, General), applies to (Booking, Shipment/Job, Both), and optionally direction and entry type.

To access Document List Template, go to:

**Home > Logistics > Document List Template**

## 1. Prerequisites

Before creating a Document List Template, it is advised to set up the following:

- [Logistics Document Type](welcome/logistics-document-type) – Master list of document types (CI, PL, BL, AWB, etc.)

## 2. How to Create a Document List Template

1. Go to the Document List Template list, click **New**.
2. Enter **Template Name** (e.g., "Air Export Standard").
3. Select **Product Type** (Air Freight, Sea Freight, Transport, Customs, Warehousing, General).
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

## 4. Related Topics

- [Document Management](welcome/document-management)
- [Logistics Document Type](welcome/logistics-document-type)
- [Sea Booking](welcome/sea-booking)
- [Air Booking](welcome/air-booking)
