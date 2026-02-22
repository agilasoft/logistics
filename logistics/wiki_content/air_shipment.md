# Air Shipment

**Air Shipment** is a transaction that represents the execution of air freight. It is the job document that tracks the actual cargo movement from origin to destination, linked to one or more Air Bookings.

An Air Shipment records flight details, ULD assignments, routing legs, packages, charges, documents, and milestones. It flows from Air Booking and supports consolidation, customs integration, and billing.

To access Air Shipment, go to:

**Home > Air Freight > Air Shipment**

## 1. Prerequisites

Before creating an Air Shipment, it is advised to set up the following:

- [Air Freight Settings](welcome/air-freight-settings)
- [Air Booking](welcome/air-booking) – Typically create from booking
- [Air Freight Master Data](welcome/air-freight-master-data) – ULD types, services, charge types
- [Logistics Milestone](welcome/logistics-milestone) – For milestone tracking

## 2. How to Create an Air Shipment

1. Go to the Air Shipment list, click **New**.
2. Select **Air Booking** (or enter details manually).
3. Enter **Flight**, **Flight Date**, **ETD**, **ETA**.
4. Add **Packages** with weights, dimensions, and ULD types.
5. Add **Routing Legs** for multi-leg routing.
6. Add **Services** and **Charges**.
7. **Save** the document.

### 2.1 Creating from Air Booking

The recommended way is to create an Air Shipment from an Air Booking. Use **Create Air Shipment** from the Air Booking, or create new and link the booking.

### 2.2 Statuses

- **Draft** – Shipment is being prepared
- **Submitted** – Shipment is confirmed and in execution
- **Cancelled** – Shipment has been cancelled

## 3. Features

### 3.1 Dashboard Tab

The Dashboard tab shows Document Alerts, Milestone Flow, and Key Metrics.

### 3.2 Milestones Tab

Track operational milestones with status (Planned, Started, Completed) and actual dates.

### 3.3 Documents Tab

Track required documents with status and attachments. Use **Populate from Template**.

### 3.4 Consolidation

Link an Air Shipment to an [Air Consolidation](welcome/air-consolidation) for consolidated shipments.

### 3.5 Billing

Create Sales Invoice from the Air Shipment. Track invoice status in the Accounts tab.

## 4. Related Topics

- [Air Booking](welcome/air-booking)
- [Air Consolidation](welcome/air-consolidation)
- [Master Air Waybill](welcome/master-air-waybill)
- [Document Management](welcome/document-management)
- [Milestone Tracking](welcome/milestone-tracking)
