# Document Management (Documents Tab)

**Document Management** is a unified feature across Booking/Order and Shipment/Job doctypes that provides centralized document tracking, compliance monitoring, and overdue alerts. Documents are managed via the **Documents** tab on each supported doctype.

The Documents tab shows a checklist of required documents (Commercial Invoice, Packing List, Bill of Lading, Air Waybill, etc.) with status, date required, date received, and attachments. Document requirements are driven by **Document List Templates** configured per product type and context.

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

### 3.2 Date Required Calculation

- **ETD** – date_required = ETD + days_offset (e.g., -3 = 3 days before ETD)
- **ETA** – date_required = ETA + days_offset
- **Booking Date** – date_required = booking_date + days_offset
- **Job Date** – date_required = job date + days_offset
- **Manual** – User enters date_required

### 3.3 Supported Doctypes

**Bookings/Orders:** Air Booking, Sea Booking, Transport Order, Declaration Order, Inbound Order, Release Order, Transfer Order

**Shipments/Jobs:** Air Shipment, Sea Shipment, Transport Job, Warehouse Job, General Job, Declaration

## 4. Related Topics

- [Sea Shipment](welcome/sea-shipment)
- [Air Shipment](welcome/air-shipment)
- [Transport Job](welcome/transport-job)
- [Warehouse Job](welcome/warehouse-jobs-operations)
- [Milestone Tracking](welcome/milestone-tracking)
