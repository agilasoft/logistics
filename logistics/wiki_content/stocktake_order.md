# Stocktake Order

**Stocktake Order** is a transaction that captures physical inventory count requirements. It is used for cycle counts, full stocktakes, and blind counts to reconcile system inventory with physical stock.

A Stocktake Order records the items and locations to be counted, count type, and whether QA or blind count is required. It links to a Warehouse Job for execution.

To access Stocktake Order, go to:

**Home > Warehousing > Stocktake Order**

## 1. Prerequisites

Before creating a Stocktake Order, it is advised to set up the following:

- [Warehouse Settings](welcome/warehouse-settings)
- Items, Storage Locations (from ERPNext)

## 2. How to Create a Stocktake Order

1. Go to the Stocktake Order list, click **New**.
2. Enter **Count Date** and select **Warehouse**.
3. Select **Count Type** (Full, Cycle, etc.) and **Blind Count** if applicable.
4. Add **Items** with quantities to count.
5. **Save** the document.

## 3. Features

### 3.1 Integration with Warehouse Job

Once a Stocktake Order is confirmed, create a Warehouse Job and link it to this order. The job executes the count and posts variances.

## 4. Related Topics

- [Warehouse Job](welcome/warehouse-job)
- [Inbound Order](welcome/inbound-order)
- [Release Order](welcome/release-order)
- [Warehouse Contract](welcome/warehouse-contract)
