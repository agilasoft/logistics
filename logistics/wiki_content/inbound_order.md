# Inbound Order

**Inbound Order** is a transaction that captures warehouse receipt requirements from the customer. It serves as the order document that flows into Warehouse Job for inbound execution (receiving, putaway, staging).

An Inbound Order records the customer's requirements for receiving cargo into the warehouse, including items, quantities, handling units, dock preferences, and value-added services. It can be created from a Sales Quote or entered directly. Once confirmed, it links to a Warehouse Job for execution.

To access Inbound Order, go to:

**Home > Warehousing > Inbound Order**

## 1. Prerequisites

Before creating an Inbound Order, it is advised to set up the following:

- [Warehouse Settings](welcome/warehouse-settings) – Warehouses, storage locations, dock doors
- [Warehouse Contract](welcome/warehouse-contract) – If billing is contract-based
- Customer, Items (from ERPNext)
- Storage Location, Handling Unit Type masters

## 2. How to Create an Inbound Order

1. Go to the Inbound Order list, click **New**.
2. Enter **Order Date** and select **Customer**.
3. Add **Items** with quantities, handling units, and storage location preferences.
4. Add **Dock** preferences if dock scheduling is used.
5. Add **Charges** (receiving, handling, storage, etc.) as needed.
6. **Save** the document.

### 2.1 Statuses

- **Draft** – Order is being prepared
- **Submitted** – Order is confirmed (when submittable)
- **Cancelled** – Order has been cancelled

## 3. Features

### 3.1 Documents Tab

The Documents tab allows you to track required documents (Delivery Order, Commercial Invoice, Packing List, etc.) with status, date required, and attachments. Use **Populate from Template** to load document requirements.

### 3.2 Integration with Warehouse Job

Once an Inbound Order is confirmed, create a Warehouse Job and link it to this order. The job inherits items, quantities, and dock preferences for receiving and putaway operations.

## 4. Related Topics

- [Warehouse Jobs Operations](welcome/warehouse-jobs-operations)
- [Release Order](welcome/release-order)
- [Transfer Order](welcome/transfer-order)
- [Warehouse Contract](welcome/warehouse-contract)
