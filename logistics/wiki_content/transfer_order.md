# Transfer Order

**Transfer Order** is a transaction that captures internal warehouse transfer requirements. It is used when moving stock between storage locations, warehouses, or for internal movements such as staging, replenishment, or rebalancing.

A Transfer Order records the items, quantities, source and destination locations, and handling requirements. It links to a Warehouse Job for execution. Unlike Inbound and Release Orders, it typically does not involve external customers—it is for internal warehouse operations.

To access Transfer Order, go to:

**Home > Warehousing > Transfer Order**

## 1. Prerequisites

Before creating a Transfer Order, it is advised to set up the following:

- [Warehouse Settings](welcome/warehouse-settings) – Warehouses, storage locations
- Items (from ERPNext)
- Storage Location masters

## 2. How to Create a Transfer Order

1. Go to the Transfer Order list, click **New**.
2. Enter **Order Date** and select **Warehouse** (if multi-warehouse).
3. Add **Items** with quantities, source and destination locations.
4. Add **Charges** if internal transfer charges apply.
5. **Save** the document.

### 2.1 Statuses

- **Draft** – Order is being prepared
- **Submitted** – Order is confirmed (when submittable)
- **Cancelled** – Order has been cancelled

## 3. Features

### 3.1 Integration with Warehouse Job

Once a Transfer Order is confirmed, create a Warehouse Job and link it to this order. The job executes the transfer between locations.

## 4. Related Topics

- [Warehouse Jobs Operations](welcome/warehouse-jobs-operations)
- [Inbound Order](welcome/inbound-order)
- [Release Order](welcome/release-order)
- [Storage Location](welcome/storage-location)
