# Transport Order

**Transport Order** is the customer-facing order document for transport. It captures origin, destination, load type, packages, charges, and documents. Transport Jobs are created from Transport Orders.

To access: **Home > Transport > Transport Order**

## 1. Prerequisites

- [Transport Settings](welcome/transport-settings)
- [Transport Template](welcome/transport-template), [Load Type](welcome/load-type)
- Shipper, Consignee, locations

## 2. Key Fields

- **Load Type** – FCL, LCL, Palletized, etc.
- **Origin / Destination** – Locations, pick/drop mode
- **Packages** – Weight, volume
- **Contains Dangerous Goods** – When set, dangerous-goods detail fields apply (compliance and documentation). Renamed from the earlier “hazardous” flag; existing data is migrated on upgrade.
- **Charges** – Selling and cost charges; supports quantity breaks (unified calculation engine; revenue and cost calculation methods)
- **Documents** – Job Document child table; Populate from Template

### 2.1 Charges from Sales Quote

When the order is created from a [Sales Quote](welcome/sales-quote), charge lines copy **charge category**, **Bill To**, **Pay To**, **description**, **Item Tax Template**, and **Invoice Type** (from the Item where applicable) together with item and rate fields.

### 2.2 Inter-module field copy

Fields may be pre-filled when the order is created from linked sea/air/transport customs documents. See [Transport Order — Inter-module Field Copy](welcome/transport-order-intermodule-field-copy).

## 3. Workflow

1. Create Transport Order from [Sales Quote](welcome/sales-quote) or manually.
2. Add packages, charges.
3. Submit when ready.
4. Create [Transport Job](welcome/transport-job) from the order.

## 4. Related Topics

- [Recent Platform Updates](welcome/recent-platform-updates)
- [Transport Job](welcome/transport-job)
- [Transport Consolidation](welcome/transport-consolidation)
- [Transport Module](welcome/transport-module)
- [Document Management](welcome/document-management)
