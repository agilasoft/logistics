# Transport Job

**Transport Job** is a transaction that represents the execution of domestic transport. It is the job document that tracks pickup, transit, and delivery, linked to a Transport Order.

A Transport Job records legs, packages, vehicle assignment, proof of delivery, charges, documents, and milestones. It supports consolidation, carbon footprint calculation, and integration with Lalamove/Transportify.

To access Transport Job, go to:

**Home > Transport > Transport Job**

## 1. Prerequisites

Before creating a Transport Job, it is advised to set up the following:

- [Transport Settings](welcome/transport-settings)
- [Transport Order](welcome/transport-order) – Typically create from order
- [Transport Master Data](welcome/transport-master-data) – Vehicle types, load types
- [Logistics Milestone](welcome/logistics-milestone) – For milestone tracking

## 2. How to Create a Transport Job

1. Go to the Transport Job list, click **New**.
2. Select **Transport Order** (or enter details manually).
3. Add **Legs** with pickup and delivery addresses, dates, times.
4. Add **Packages** with weights and dimensions.
5. Assign **Vehicle** and **Driver** if applicable.
6. Add **Charges**.
7. **Save** the document.

### 2.1 Creating from Transport Order

The recommended way is to create a Transport Job from a Transport Order. Use **Create Transport Job** from the order, or create new and link the order.

### 2.2 Statuses

- **Draft** – Job is being prepared
- **Scheduled** – Job is scheduled
- **In Transit** – Job is in progress
- **Delivered** – Job is completed
- **Cancelled** – Job has been cancelled

## 3. Features

### 3.1 Dashboard Tab

The Dashboard tab shows:
- **Document Alerts** – Missing, overdue documents
- **Milestone Flow** – Visual timeline (Pick-Up, In-Transit, Delivered)
- **Carbon Footprint** – Calculated emissions

### 3.2 Milestones Tab

Track milestones (Pick-Up, In-Transit, Delivered) with status and actual dates. Use **Capture Actual Start** and **Capture Actual End**.

### 3.3 Documents Tab

Track required documents (Delivery Order, Proof of Delivery) with status and attachments. Use **Populate from Template**.

### 3.4 Proof of Delivery

Capture proof of delivery (signature, photo) on the Transport Leg or via the Proof of Delivery doctype.

### 3.5 Consolidation

Link a Transport Job to a [Transport Consolidation](welcome/transport-consolidation) for multi-stop or shared truckload.

### 3.6 Carbon Footprint

Carbon emissions are calculated automatically based on distance, weight, and emission factors from Transport Settings.

## 4. Related Topics

- [Transport Order](welcome/transport-order)
- [Transport Leg](welcome/transport-leg)
- [Run Sheet](welcome/run-sheet)
- [Proof of Delivery](welcome/proof-of-delivery)
- [Document Management](welcome/document-management)
- [Milestone Tracking](welcome/milestone-tracking)
