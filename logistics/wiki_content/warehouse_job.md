# Warehouse Job

**Warehouse Job** is a transaction that represents a warehouse operation. It executes Inbound Orders (receiving, putaway), Release Orders (pick, release), Transfer Orders, VAS Orders, or Stocktake Orders.

A Warehouse Job records items, quantities, operations, dock assignments, charges, documents, and operation-based milestones. It supports multiple job types and integrates with ERPNext Stock for inventory posting.

To access Warehouse Job, go to:

**Home > Warehousing > Warehouse Job**

## 1. Prerequisites

Before creating a Warehouse Job, it is advised to set up the following:

- [Warehouse Settings](welcome/warehouse-settings)
- Reference Order (Inbound Order, Release Order, Transfer Order, VAS Order, or Stocktake Order)
- [Storage Location](welcome/storage-location) – For putaway and pick
- [Handling Unit Type](welcome/handling-unit-type) – For inventory tracking

## 2. How to Create a Warehouse Job

1. Go to the Warehouse Job list, click **New**.
2. Select **Type** (Putaway, Pick, Transfer, VAS, Stocktake).
3. Select **Reference Order Type** and **Reference Order** (Inbound, Release, Transfer, VAS, Stocktake).
4. Add **Items** (or inherit from order).
5. Add **Docks** for dock scheduling.
6. **Save** the document.

### 2.1 Creating from Order

The recommended way is to create a Warehouse Job from an order. Use **Create Warehouse Job** from Inbound Order, Release Order, Transfer Order, VAS Order, or Stocktake Order.

### 2.2 Statuses

- **Draft** – Job is being prepared
- **Open** – Job is in progress
- **Completed** – Job is completed
- **Cancelled** – Job has been cancelled

## 3. Features

### 3.1 Dashboard Tab

The Dashboard tab shows:
- **Document Alerts** – Missing, overdue documents
- **Operation Flow** – Start → Received → Putaway → Pick → Release → End (varies by job type)
- **Key Metrics** – Totals, status

### 3.2 Operations Tab

Track operations on each item: staging, receiving, putaway, pick, release. Post operations to update inventory and progress the job.

### 3.3 Documents Tab

Track required documents with status and attachments. Use **Populate from Template**.

### 3.4 Docking Tab

Assign dock doors for receiving or dispatch. Schedule dock usage.

### 3.5 Charges Tab

Add warehouse charges (receiving, handling, storage, picking, loading). Create Sales Invoice from the job.

### 3.6 Integration with ERPNext Stock

Warehouse Job posts to ERPNext Stock Entry for inventory movements when operations are completed.

## 4. Related Topics

- [Inbound Order](welcome/inbound-order)
- [Release Order](welcome/release-order)
- [Transfer Order](welcome/transfer-order)
- [VAS Order](welcome/vas-order)
- [Stocktake Order](welcome/stocktake-order)
- [Warehouse Contract](welcome/warehouse-contract)
- [Document Management](welcome/document-management)
