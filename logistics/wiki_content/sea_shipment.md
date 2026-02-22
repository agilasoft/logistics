# Sea Shipment

**Sea Shipment** is a transaction that represents the execution of ocean freight. It is the job document that tracks the actual cargo movement from origin to destination, linked to one or more Sea Bookings.

A Sea Shipment records vessel details, container assignments, routing legs, packages, charges, documents, and milestones. It flows from Sea Booking and supports consolidation, customs integration, and billing.

To access Sea Shipment, go to:

**Home > Sea Freight > Sea Shipment**

## 1. Prerequisites

Before creating a Sea Shipment, it is advised to set up the following:

- [Sea Freight Settings](welcome/sea-freight-settings)
- [Sea Booking](welcome/sea-booking) – Typically create from booking
- [Sea Freight Master Data](welcome/sea-freight-master-data) – Container types, services, charge types
- [Logistics Milestone](welcome/logistics-milestone) – For milestone tracking

## 2. How to Create a Sea Shipment

1. Go to the Sea Shipment list, click **New**.
2. Select **Sea Booking** (or enter details manually).
3. Enter **Vessel**, **Voyage**, **ETD**, **ETA**.
4. Add **Containers** or **Packages** with weights and dimensions.
5. Add **Routing Legs** for multi-port routing.
6. Add **Services** and **Charges**.
7. **Save** the document.

### 2.1 Creating from Sea Booking

The recommended way is to create a Sea Shipment from a Sea Booking. Use **Create Sea Shipment** from the Sea Booking, or create new and link the booking. The shipment inherits routing, cargo, and party details.

### 2.2 Statuses

- **Draft** – Shipment is being prepared
- **Submitted** – Shipment is confirmed and in execution
- **Cancelled** – Shipment has been cancelled

## 3. Features

### 3.1 Dashboard Tab

The Dashboard tab shows Document Alerts, Milestone Flow, and Key Metrics.

### 3.2 Milestones Tab

Track operational milestones (Gate-In, Loaded, Departed, Arrived, etc.) with status (Planned, Started, Completed) and actual dates.

### 3.3 Documents Tab

Track required documents with status, date required, and attachments. Use **Populate from Template**.

### 3.4 Consolidation

Link a Sea Shipment to a [Sea Freight Consolidation](welcome/sea-freight-consolidation) for LCL/groupage shipments.

### 3.5 Billing

Create Sales Invoice from the Sea Shipment. Track invoice status in the Accounts tab.

## 4. Related Topics

- [Sea Booking](welcome/sea-booking)
- [Sea Freight Consolidation](welcome/sea-freight-consolidation)
- [Master Bill](welcome/master-bill)
- [Document Management](welcome/document-management)
- [Milestone Tracking](welcome/milestone-tracking)
