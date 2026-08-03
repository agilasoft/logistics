# Cross-Docking Order

**Cross-Docking Order** is a warehouse order for temporary staging and docking of cargo that is received and released without putaway into long-term storage. It combines inbound (stage in) and outbound (stage out) functionality on a single order that converts to a Warehouse Job of type **Cross Dock**.

Use Cross-Docking when cargo is docked briefly for consolidation, transfer, or onward movement rather than stored.

To access Cross-Docking Order, go to:

**Home > Warehousing > Cross-Docking Order**

## 1. Prerequisites

- [Warehouse Settings](welcome/warehouse-settings) – Staging areas and dock doors
- [Warehouse Contract](welcome/warehouse-contract) – Optional; cross-dock charge items
- Customer and Warehouse Items

## 2. How to Create a Cross-Docking Order

1. Go to the Cross-Docking Order list, click **New**.
2. Enter **Order Date** and select **Customer** (and Contract if used).
3. Add **Items** with quantities and handling units.
4. On the **Docking** tab, add dock rows with **Direction** Inbound or Outbound.
5. Add **Charges** as needed (Get Charges from Contract uses cross-dock context).
6. **Save** and **Submit**.

### 2.1 From Sales Quote

Add a **Cross-Docking** Linked Service (and matching charge lines) on a Sales Quote whose Primary Service Type is another module (e.g. Air/Sea/Transport), then create the Cross-Docking Order via **Create → Internal Job** / linked-service flows.

Cross-Docking is **not** a Primary Service Type on Sales Quote (it belongs to the Warehousing module). Linked Service type **Cross-Docking** maps to Cross-Docking Order (linked Warehousing continues to map to VAS Order CROSS-DOCK for backward compatibility).

## 3. Convert to Warehouse Job

After submit, use **Create → Warehouse Job**. The job is created with:

- Type: **Cross Dock**
- Reference Order Type / Reference Order: the Cross-Docking Order

### 3.1 Job execution

1. Set **Staging Area** on the job.
2. **Allocate Staging** – copies order lines onto job items at the staging location.
3. **Submit** the job.
4. **Post → Post Receiving** – stock in to staging.
5. **Post → Post Release** – stock out from staging.

There is no Putaway or Pick allocation against storage locations.

## 4. Related

- [Warehousing Module](welcome/warehousing-module)
- [Inbound Order](welcome/inbound-order)
- [Release Order](welcome/release-order)
- [Warehouse Job](welcome/warehouse-job)
- [VAS Order](welcome/vas-order) (linked Warehousing CROSS-DOCK path)
