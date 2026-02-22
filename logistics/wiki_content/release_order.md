# Release Order

**Release Order** is a transaction that captures warehouse dispatch/release requirements from the customer. It serves as the order document that flows into Warehouse Job for outbound execution (pick, pack, release).

A Release Order records the customer's requirements for releasing cargo from the warehouse, including items, quantities, handling units, dock preferences, and value-added services. It can be created from a Sales Quote or entered directly. Once confirmed, it links to a Warehouse Job for execution.

To access Release Order, go to:

**Home > Warehousing > Release Order**

## 1. Prerequisites

Before creating a Release Order, it is advised to set up the following:

- [Warehouse Settings](welcome/warehouse-settings) – Warehouses, storage locations, dock doors
- [Warehouse Contract](welcome/warehouse-contract) – If billing is contract-based
- Customer, Items (from ERPNext)
- Storage Location, Handling Unit Type masters

## 2. How to Create a Release Order

1. Go to the Release Order list, click **New**.
2. Enter **Order Date** and select **Customer**.
3. Add **Items** with quantities, handling units, and pick location preferences.
4. Add **Dock** preferences if dock scheduling is used.
5. Add **Charges** (picking, handling, loading, etc.) as needed.
6. **Save** the document.

### 2.1 Statuses

- **Draft** – Order is being prepared
- **Submitted** – Order is confirmed (when submittable)
- **Cancelled** – Order has been cancelled

## 3. Features

### 3.1 Documents Tab

The Documents tab allows you to track required documents (Delivery Order, Commercial Invoice, Packing List, Proof of Delivery, etc.) with status, date required, and attachments. Use **Populate from Template** to load document requirements.

### 3.2 Integration with Warehouse Job

Once a Release Order is confirmed, create a Warehouse Job and link it to this order. The job inherits items, quantities, and dock preferences for pick and release operations.

## 4. Related Topics

- [Warehouse Jobs Operations](welcome/warehouse-jobs-operations)
- [Inbound Order](welcome/inbound-order)
- [Transfer Order](welcome/transfer-order)
- [Warehouse Contract](welcome/warehouse-contract)
