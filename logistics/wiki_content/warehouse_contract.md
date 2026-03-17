# Warehouse Contract

**Warehouse Contract** is a master that defines the commercial terms between the warehouse operator and the customer. It specifies storage rates, handling rates, value-added service rates, and billing terms.

A Warehouse Contract is linked to Inbound Orders and Release Orders for billing. It supports periodic billing for storage and one-time charges for handling and VAS.

To access Warehouse Contract, go to:

**Home > Warehousing > Warehouse Contract**

## 1. Prerequisites

Before creating a Warehouse Contract, it is advised to set up the following:

- Customer (from ERPNext)
- [Warehouse Settings](welcome/warehouse-settings)
- [Storage Location](welcome/storage-location) – For storage rates
- [VAS Order Type](welcome/vas-order-type) – For VAS rates

## 2. How to Create a Warehouse Contract

1. Go to the Warehouse Contract list, click **New**.
2. Enter **Contract Name** and select **Customer**.
3. Enter **Start Date** and **End Date**.
4. Add **Storage Rates** (per CBM, per pallet, etc.).
5. Add **Handling Rates** (receiving, putaway, pick, release).
6. Add **VAS Rates** (labeling, repacking, etc.).
7. **Save** the document.

## 3. Features

### 3.1 Billing

Warehouse Contract is used for automated periodic billing and for calculating charges on Inbound Orders, Release Orders, and Warehouse Jobs.

## 4. Related Topics

- [Inbound Order](welcome/inbound-order)
- [Release Order](welcome/release-order)
- [Warehouse Job](welcome/warehouse-job)
- [Warehouse Settings](welcome/warehouse-settings)
