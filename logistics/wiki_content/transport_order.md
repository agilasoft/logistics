# Transport Order

**Transport Order** is a transaction that captures domestic transport requirements from the customer before execution. It serves as the order document that flows into Transport Job for execution.

A Transport Order records pickup and delivery locations, packages, scheduled dates, and service requirements. It can be created from a Sales Quote or entered directly. Once confirmed, it links to one or more Transport Jobs for execution.

To access Transport Order, go to:

**Home > Transport > Transport Order**

## 1. Prerequisites

Before creating a Transport Order, it is advised to set up the following:

- [Transport Settings](welcome/transport-settings)
- [Transport Master Data](welcome/transport-master-data) – Vehicle types, load types, transport zones
- Customer (from ERPNext)
- Addresses for pickup and delivery

## 2. How to Create a Transport Order

1. Go to the Transport Order list, click **New**.
2. Enter **Order Date** and select **Customer**.
3. Add **Legs** with pickup and delivery addresses, dates, and times.
4. Add **Packages** with weights, dimensions, and quantity.
5. Select **Transport Template** if using predefined templates.
6. Add **Charges** as needed.
7. **Save** the document.

### 2.1 Creating from Sales Quote

You can create a Transport Order from an existing Sales Quote. Use the **Create from Sales Quote** button or action to auto-fill details.

### 2.2 Statuses

- **Draft** – Order is being prepared
- **Submitted** – Order is confirmed (when submittable)
- **Cancelled** – Order has been cancelled

## 3. Features

### 3.1 Documents Tab

The Documents tab allows you to track required documents (Delivery Order, Proof of Delivery, etc.) with status, date required, and attachments. Use **Populate from Template** to load document requirements.

### 3.2 Integration with Transport Job

Once a Transport Order is confirmed, create a Transport Job and link it to this order. The job inherits legs, packages, and customer details for execution.

## 4. Related Topics

- [Transport Job](welcome/transport-job)
- [Transport Template](welcome/transport-template)
- [Transport Consolidation](welcome/transport-consolidation)
- [Sales Quote](welcome/sales-quote)
- [Transport Settings](welcome/transport-settings)
