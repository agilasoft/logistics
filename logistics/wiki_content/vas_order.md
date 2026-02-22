# VAS Order (Value-Added Services)

**VAS Order** is a transaction that captures value-added service requirements for warehouse operations. Examples include labeling, repacking, kitting, quality inspection, fumigation, and other custom services.

A VAS Order records the customer, items, service types, quantities, and charges. It links to a Warehouse Job for execution. VAS Orders can be standalone or linked to Inbound/Release Orders.

To access VAS Order, go to:

**Home > Warehousing > VAS Order**

## 1. Prerequisites

Before creating a VAS Order, it is advised to set up the following:

- [Warehouse Settings](welcome/warehouse-settings)
- [VAS Order Type](welcome/vas-order-type) – Master list of service types
- Customer, Items (from ERPNext)

## 2. How to Create a VAS Order

1. Go to the VAS Order list, click **New**.
2. Enter **Order Date** and select **Customer**.
3. Add **Items** with service type, quantity, and charges.
4. **Save** the document.

## 3. Features

### 3.1 Integration with Warehouse Job

Once a VAS Order is confirmed, create a Warehouse Job and link it to this order. The job executes the value-added services.

## 4. Related Topics

- [Warehouse Job](welcome/warehouse-job)
- [Inbound Order](welcome/inbound-order)
- [Release Order](welcome/release-order)
- [Warehouse Contract](welcome/warehouse-contract)
