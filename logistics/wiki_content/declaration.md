# Declaration

**Declaration** is a transaction that represents a customs declaration submitted to customs authorities. It is the execution document for customs clearance, linked to a Declaration Order.

A Declaration records commodities, parties, duty/tax, documents, and clearance status. It supports import, export, and transit declarations with HS code classification and document tracking.

To access Declaration, go to:

**Home > Customs > Declaration**

## 1. Prerequisites

Before creating a Declaration, it is advised to set up the following:

- [Customs Settings](welcome/customs-settings)
- [Declaration Order](welcome/declaration-order) – Typically create from order
- [Customs Master Data](welcome/customs-master-data) – Commodity, Customs Authority, HS codes
- [Document List Template](welcome/document-list-template) – For document requirements

## 2. How to Create a Declaration

1. Go to the Declaration list, click **New**.
2. Select **Declaration Order** (or enter details manually).
3. Select **Customs Authority** and **Declaration Type** (Import, Export, Transit).
4. Add **Commodities** with HS codes, descriptions, quantities, values.
5. Add **Parties** (Importer, Exporter, Declarant).
6. Add **Documents** (Commercial Invoice, Packing List, Bill of Lading, etc.).
7. **Save** the document.

### 2.1 Creating from Declaration Order

The recommended way is to create a Declaration from a Declaration Order. Use **Create Declaration** from the order, or create new and link the order.

### 2.2 Statuses

- **Draft** – Declaration is being prepared
- **Submitted** – Declaration submitted to customs
- **Under Review** – Customs is reviewing
- **Cleared** – Customs clearance approved
- **Released** – Cargo released
- **Rejected** – Declaration rejected
- **Cancelled** – Declaration cancelled

## 3. Features

### 3.1 Dashboard Tab

The Dashboard tab provides a compact overview of declaration status, alerts, and key metrics:

- **Status** – Current status (Draft, Submitted, In Progress, Approved, Rejected, Cancelled) with color-coded badge
- **Alerts** – Document alerts (expired/rejected, pending, expiring soon), missing permits, and compliance exceptions
- **Key Metrics** – Declaration type, number, payment status, expected/actual clearance dates
- **Summary** – Commodities count, declaration value, total payable

Use the Dashboard to monitor status, spot missing documents or permits, and track compliance at a glance.

### 3.2 Milestones Tab

Track declaration milestones (Submitted, Under Review, Cleared, Released) with status and actual dates.

### 3.3 Documents Tab

Declaration has a Documents tab (Declaration Document child table) for tracking required customs documents with status and attachments.

### 3.4 Duty and Tax

Calculate duty and tax based on [Customs Rate](welcome/customs-rate) and commodity values.

### 3.5 Integration

Link Declaration to Sea Shipment, Air Shipment, or Transport Job for end-to-end visibility.

## 4. Related Topics

- [Declaration Order](welcome/declaration-order)
- [Commodity](welcome/commodity)
- [Customs Authority](welcome/customs-authority)
- [Customs Rate](welcome/customs-rate)
- [Document Management](welcome/document-management)
- [Milestone Tracking](welcome/milestone-tracking)
