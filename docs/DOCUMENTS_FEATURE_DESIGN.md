# Documents Tab & Document Management Feature Design

## Overview

This document describes the design for a unified **Documents Tab** feature across Booking/Order and Shipment/Job/Declaration doctypes in the Logistics app. The feature provides centralized document management, monitoring, and compliance tracking with configurable templates per product type, date-based requirements, and overdue alerts.

---

## 1. Scope & Target Doctypes

### 1.1 Booking/Order Doctypes (Pre-Execution Phase)

| Module | DocType | Description |
|--------|---------|-------------|
| Air Freight | Air Booking | Air freight booking/order |
| Sea Freight | Sea Booking | Sea freight booking/order |
| Transport | Transport Order | Domestic transport order |
| Customs | Declaration Order (Customs Declaration Order) | Customs declaration order |
| Warehousing | Inbound Order | Inbound warehouse order |
| Warehousing | Release Order | Release/outbound order |
| Warehousing | Transfer Order | Internal transfer order |

### 1.2 Shipment/Job/Declaration Doctypes (Execution Phase)

| Module | DocType | Description |
|--------|---------|-------------|
| Air Freight | Air Shipment | Air freight job/shipment |
| Sea Freight | Sea Shipment | Sea freight job/shipment |
| Transport | Transport Job | Domestic transport job |
| Warehousing | Warehouse Job | Warehouse operation job |
| Customs | Declaration | Customs declaration (already has Documents tab) |
| Logistics | General Job | General logistics job |

**Note:** Declaration already has a Documents tab with `Declaration Document` child table. The design will align with this pattern and optionally migrate/extend it to use the new template system.

---

## 2. Document List Template (Master Configuration)

### 2.1 Document List Template DocType

A new **Document List Template** doctype defines which documents are required for each product/context.

| Field | Type | Description |
|-------|------|-------------|
| `template_name` | Data | Template name (e.g., "Air Export Standard", "Sea Import FCL") |
| `product_type` | Select | Air Freight, Sea Freight, Transport, Customs, Warehousing, General |
| `applies_to` | Select | Booking, Shipment/Job, Both |
| `direction` | Select | Import, Export, Domestic, All (optional filter) |
| `entry_type` | Select | Direct, Transit, Transshipment, ATA Carnet, All (optional) |
| `is_default` | Check | Default template for this product when no match |
| `description` | Small Text | Template description |

### 2.2 Document List Template Item (Child Table)

Child table defining each document requirement:

| Field | Type | Description |
|-------|------|-------------|
| `document_type` | Link → Logistics Document Type | Reference to standard document type |
| `sequence` | Int | Display order |
| `is_mandatory` | Check | Required for submission/progression |
| `date_required_basis` | Select | ETD, ETA, Booking Date, Job Date, Manual, None |
| `days_offset` | Int | Days before/after basis date (e.g., -7 = 7 days before ETD) |
| `status_flow` | Select | Upload → Done → Received → Verified (comma-separated workflow) |
| `allow_early_upload` | Check | Can upload before date_required |
| `description` | Small Text | Help text for users |

### 2.3 Logistics Document Type (DocType)

Standard catalog of document types used across products. Named **Logistics Document Type** to avoid conflict with Frappe core's Document Type.

| Field | Type | Description |
|-------|------|-------------|
| `document_code` | Data | Short code (e.g., CI, PL, BL, AWB) |
| `document_name` | Data | Full name (e.g., Commercial Invoice, Packing List) |
| `category` | Select | Trade, Transport, Customs, Insurance, DG, Other |
| `typical_format` | Select | PDF, Image, Excel, Any |
| `has_expiry` | Check | Document has expiry date |
| `is_product_specific` | Check | Only for certain products |

**Standard Document Types (examples):**
- Commercial Invoice (CI)
- Packing List (PL)
- Bill of Lading (BL)
- Air Waybill (AWB)
- Certificate of Origin (COO)
- Export License
- Import License / Permit
- Insurance Certificate
- Phytosanitary Certificate
- Fumigation Certificate
- Dangerous Goods Declaration (DGD)
- Delivery Order (DO)
- CMR / Cargo Manifest
- Proof of Delivery (POD)

---

## 3. Document Tracking Child Table

### 3.1 Job Document (or Booking Document) – Child Table

A reusable child table attached to each target doctype:

| Field | Type | Description |
|-------|------|-------------|
| `document_type` | Link → Logistics Document Type | From template |
| `template_item` | Link | Optional link to template item for traceability |
| `document_name` | Data | Custom name override |
| `document_number` | Data | Reference number (BL#, AWB#, etc.) |
| `status` | Select | Pending, Uploaded, Done, Received, Verified, Overdue, Expired, Rejected |
| `date_required` | Date | Calculated or manual – when document must be available |
| `date_received` | Date | When document was received/uploaded |
| `date_verified` | Date | When verified (if applicable) |
| `expiry_date` | Date | For documents with validity |
| `issued_by` | Data | Issuing authority |
| `attachment` | Attach | File attachment |
| `is_required` | Check | From template (mandatory) |
| `is_verified` | Check | Verification complete |
| `verified_by` | Link → User | Who verified |
| `notes` | Small Text | Notes |
| `overdue_days` | Int | Computed: days past date_required (read-only) |

**Status Flow:**
```
Pending → Uploaded → Done → Received → Verified
    ↓         ↓
 Overdue   Expired (if expiry_date passed)
```

---

## 4. Documents Tab UI Layout

### 4.1 Tab Structure

Each target doctype gets a **Documents** tab containing:

1. **Document Checklist** (Table)
   - Rows auto-populated from Document List Template based on product + context
   - Columns: Document Type | Status | Date Required | Date Received | Attachment | Overdue | Actions
   - Inline edit for status, attachment, dates
   - Visual indicators: 🟢 Complete, 🟡 Pending, 🔴 Overdue

2. **Document Summary** (HTML/Collapsible)
   - Count: X of Y required documents complete
   - Overdue: N documents overdue
   - Next due: Document X due on [date]

3. **Dashboard Alerts** (in Dashboard tab)
   - Notice when documents are missing or overdue
   - Link to Documents tab

### 4.2 Template Selection Logic

When a document is opened/created:

1. Resolve `product_type` from doctype (e.g., Air Booking → Air Freight)
2. Resolve `applies_to` (Booking vs Shipment/Job)
3. Optionally use `direction`, `entry_type` from parent doc
4. Find matching Document List Template (first match by filters, else default)
5. Create/refresh child rows from template items
6. Compute `date_required` from `date_required_basis` + `days_offset`

---

## 5. Dashboard Integration

### 5.1 Dashboard Tab Alerts

For doctypes with a Dashboard tab (e.g., Air Shipment, Sea Shipment, Warehouse Job):

- Add an **Alerts** or **Notices** section
- Display:
  - **Missing Documents:** List of required documents not yet uploaded/received
  - **Overdue Documents:** Documents past `date_required` with days overdue
  - **Expiring Soon:** Documents with `expiry_date` within next 7 days
- Each item links to the Documents tab
- Use color coding: red (overdue), orange (due soon), green (complete)

### 5.2 HTML Widget

Example structure for dashboard notice:

```html
<div class="document-alerts">
  <div class="alert alert-danger" if overdue>
    <strong>2 documents overdue</strong>
    <ul>
      <li>Commercial Invoice – 3 days overdue</li>
      <li>Packing List – 1 day overdue</li>
    </ul>
    <a href="#documents_tab">View Documents</a>
  </div>
  <div class="alert alert-warning" if missing>
    <strong>1 required document pending</strong>
    <ul>
      <li>Bill of Lading – due 2025-02-25</li>
    </ul>
  </div>
</div>
```

---

## 6. Date Required & Overdue Logic

### 6.1 Date Required Calculation

| Basis | Source Field | Example |
|-------|--------------|---------|
| ETD | `etd` | date_required = etd + days_offset |
| ETA | `eta` | date_required = eta + days_offset |
| Booking Date | `booking_date` | date_required = booking_date + days_offset |
| Job Date | `creation` or `booking_date` | Same |
| Manual | User entry | User sets date_required |

### 6.2 Overdue Detection

- **Overdue:** `status` in (Pending, Uploaded) AND `date_required` < today
- **Days Overdue:** `date_diff(today, date_required)` when overdue
- **Expired:** `expiry_date` is set AND `expiry_date` < today

### 6.3 Scheduled Tasks (Optional)

- Daily job to:
  - Update `status` → Overdue for documents past `date_required`
  - Send notifications/emails for overdue documents
  - Update dashboard cache

---

## 7. Alerts & Notifications

### 7.1 In-App Alerts

- **Form load:** If document has overdue/missing required docs, show banner
- **Dashboard tab:** Always show document status summary
- **Before submit:** Warn if mandatory documents are missing (configurable – can block or allow with confirmation)

### 7.2 Notification Rules (Future)

- Email assignee when document becomes overdue
- Reminder X days before `date_required`
- Digest: daily summary of all overdue documents per user/customer

---

## 8. Implementation Phases

### Phase 1: Core Infrastructure
- [x] Create **Logistics Document Type** doctype
- [x] Create **Document List Template** and **Document List Template Item**
- [x] Create **Job Document** child table – generic, linkable to multiple parents
- [ ] Add `document_list_template` Link field to relevant doctypes for override

### Phase 2: Documents Tab
- [x] Add Documents tab + `documents` child table to:
  - Air Booking, Sea Booking
  - Transport Order, Declaration Order
  - Inbound Order, Release Order, Transfer Order
  - Air Shipment, Sea Shipment
  - Transport Job, Warehouse Job
  - General Job
- [x] Declaration: Has existing Documents tab with Declaration Document

### Phase 3: Template Population
- [x] Server method: `get_document_template_items(product_type, applies_to, direction, entry_type)`
- [x] Populate from Template button on all target doctypes
- [x] Compute `date_required` from parent fields (etd, eta, booking_date, order_date)
- [ ] Client script: refresh document rows when etd/eta/booking_date changes (optional)

### Phase 4: Dashboard Alerts
- [x] Add document alerts section to Dashboard tab (Air Shipment, Sea Shipment, Warehouse Job)
- [x] Server method: `get_document_alerts(parent_doctype, parent_name)`
- [x] Return: missing, overdue, expiring_soon
- [x] Render in milestone_html / dashboard HTML

### Phase 5: Overdue & Notifications
- [ ] Scheduled task: mark overdue, send notifications
- [ ] Report: Document Compliance Report (all products)
- [ ] Permission checks for document access

---

## 9. Data Model Summary

```
Logistics Document Type (master)
    ↑
Document List Template
    └── Document List Template Item (child) → Document Type

Air Booking / Sea Booking / Transport Order / ... (parent)
    └── Booking Document (child) → Document Type, status, dates, attachment

Air Shipment / Sea Shipment / Transport Job / ... (parent)
    └── Job Document (child) → Document Type, status, dates, attachment

Declaration (existing)
    └── Declaration Document (child) – align fields with Job Document
```

---

## 10. Migration Notes

- **Declaration Document:** Already exists. Options:
  - (A) Keep as-is, add template support only for Declaration
  - (B) Create generic **Job Document** and migrate Declaration to use it with a compatibility layer
  - (C) Rename/refactor Declaration Document to be the generic child table used everywhere

Recommendation: **(A)** for minimal disruption. Use **Job Document** for all new integrations; Declaration keeps its existing child table. Both can share the same Document Type master and similar status/date logic.

---

## 11. Configuration Examples

### Air Export – Standard Documents
| Document | Mandatory | Date Basis | Offset |
|----------|-----------|------------|--------|
| Commercial Invoice | Yes | ETD | -3 |
| Packing List | Yes | ETD | -3 |
| Certificate of Origin | No | ETD | -2 |
| Export License | If required | ETD | -5 |
| DG Declaration | If DG | ETD | -2 |

### Sea Import – Standard Documents
| Document | Mandatory | Date Basis | Offset |
|----------|-----------|------------|--------|
| Bill of Lading | Yes | ETA | -1 |
| Commercial Invoice | Yes | ETA | -2 |
| Packing List | Yes | ETA | -2 |
| Import Permit | If required | ETA | -5 |

### Transport Job
| Document | Mandatory | Date Basis | Offset |
|----------|-----------|------------|--------|
| Delivery Order | Yes | Job Date | 0 |
| Proof of Delivery | Yes | Job Date | +1 |

---

## 12. API & Extensibility

- **Whitelisted methods:**
  - `get_document_template_items(product_type, applies_to, direction, entry_type)`
  - `get_document_alerts(doctype, docname)`
  - `populate_documents_from_template(doctype, docname)` – for manual refresh
- **REST API:** Standard Frappe API for Document List Template, Document Type, and child document tables
- **Custom templates:** Customers can create their own Document List Templates and assign via `document_list_template` field

---

*Document Version: 1.0*  
*Last Updated: 2025-02-21*
