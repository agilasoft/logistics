# Default Details and Relationships

This page describes **default details** to set up for key parties (Shipper, Consignee) and service providers (Freight Agent, Carrier/Shipping Line, Airline), and how they **relate** across Sea Freight, Air Freight, Transport, and Customs.

To access organizations: **Home > Sea Freight > Organizations** or **Home > Transport > Organizations**

## 1. Shipper

**Shipper** is the party who tenders cargo for transport (exporter/consignor). Used on bookings, shipments, transport orders, declarations, and quotes.

### 1.1 Default details to set

| Field / area | Purpose |
|--------------|--------|
| **Shipper Name** | Display name; required. |
| **Customer** | Link to ERPNext Customer (optional; for billing/portal). |
| **Address** | At least one address (pickup/origin); used for BL, AWB, commercial invoice. |
| **Contact** | At least one contact; used for documentation and notifications. |

Create masters via **Home > Sea Freight > Organizations > Shipper** (or Transport > Organizations > Shipper). No system-wide “default shipper” is applied; users choose the shipper per [Sea Booking](welcome/sea-booking), [Air Booking](welcome/air-booking), [Transport Order](welcome/transport-order), [Declaration](welcome/declaration), [Sales Quote](welcome/sales-quote), and warehousing orders.

### 1.2 Relationships

- **Bookings:** [Sea Booking](welcome/sea-booking), [Air Booking](welcome/air-booking) – shipper + shipper address/contact.
- **Shipments:** [Sea Shipment](welcome/sea-shipment), [Air Shipment](welcome/air-shipment) – shipper and addresses flow from booking or are set on the shipment.
- **Transport:** [Transport Order](welcome/transport-order) – shipper for pickup/origin.
- **Customs:** [Declaration](welcome/declaration) – shipper for export/import.
- **Pricing:** [Sales Quote](welcome/sales-quote) – shipper for the quoted party.
- **Warehousing:** [Inbound Order](welcome/inbound-order), [Release Order](welcome/release-order), [Transfer Order](welcome/transfer-order), [Warehouse Job](welcome/warehouse-job), [Warehouse Contract](welcome/warehouse-contract), [VAS Order](welcome/vas-order), [Stocktake Order](welcome/stocktake-order).

---

## 2. Consignee

**Consignee** is the party to whom cargo is delivered (importer/receiver). Used on the same document types as Shipper for the delivery side.

### 2.1 Default details to set

| Field / area | Purpose |
|--------------|--------|
| **Consignee Name** | Display name; required. |
| **Customer** | Link to ERPNext Customer (optional). |
| **Address** | At least one address (delivery); used for BL, AWB, delivery legs. |
| **Contact** | At least one contact; used for documentation and notifications. |

Create masters via **Home > Sea Freight > Organizations > Consignee** (or Transport > Organizations > Consignee). There is no system-wide “default consignee”; selection is per document.

### 2.2 Relationships

- **Bookings:** [Sea Booking](welcome/sea-booking), [Air Booking](welcome/air-booking) – consignee + consignee address/contact.
- **Shipments:** [Sea Shipment](welcome/sea-shipment), [Air Shipment](welcome/air-shipment) – consignee and addresses from booking or set on shipment.
- **Transport:** [Transport Order](welcome/transport-order) – consignee for delivery.
- **Customs:** [Declaration](welcome/declaration) – consignee for export/import.
- **Pricing:** [Sales Quote](welcome/sales-quote).
- **Warehousing:** Same as Shipper (Inbound Order, Release Order, Transfer Order, Warehouse Job, Warehouse Contract, VAS Order, Stocktake Order).
- **Consolidations:** [Sea Consolidation](welcome/sea-consolidation), [Air Consolidation](welcome/air-consolidation) – package-level shipper/consignee.

---

## 3. Freight Agent

**Freight Agent** is the intermediary that arranges freight with carriers. Create Freight Agent masters and optionally set **defaults** so new Sea/Air documents pick a default agent.

### 3.1 Default details to set (master)

- **Agent name** and any required identifiers.
- **Address / contact** if used for correspondence or documentation.

Freight Agent is a shared master used across Sea and Air Freight.

### 3.2 Where defaults are applied

| Module | Settings document | Default field | Used on |
|--------|-------------------|---------------|--------|
| Sea Freight | [Sea Freight Settings](welcome/sea-freight-settings) | **Default Freight Agent** | Sea Shipment, Sea Booking (optional), Sales Quote Sea Freight |
| Air Freight | [Air Freight Settings](welcome/air-freight-settings) | **Default Freight Agent** | Air Shipment, Air Booking (optional), Air Consolidation, Sales Quote Air Freight, Master AWB |

Set **Default Freight Agent** in the relevant settings so new Sea Shipments and Air Shipments (and related documents) are pre-filled when no agent is already selected.

---

## 4. Carrier / Shipping Line (Sea) and Airline (Air)

**Carrier** in CargoNext is represented by **Shipping Line** (sea) and **Airline** (air). Set these masters and then set **defaults** in module settings so new documents are pre-filled.

### 4.1 Sea: Shipping Line

| What to set | Where | Purpose |
|-------------|--------|--------|
| Shipping Line masters | **Home > Sea Freight** (e.g. list/workspace for Shipping Line) | Used on Sea Booking, Sea Shipment, Sea Consolidation, Master Bill, routing legs, rates. |
| **Default Shipping Line** | [Sea Freight Settings](welcome/sea-freight-settings) → Business Settings | Default for new Sea Shipments (and related sea documents). |

### 4.2 Air: Airline

| What to set | Where | Purpose |
|-------------|--------|--------|
| Airline masters | **Home > Air Freight** (Airline list) | Used on Air Booking, Air Shipment, Air Consolidation, Master AWB, flight schedules, rates. |
| **Default Airline** | [Air Freight Settings](welcome/air-freight-settings) → Business Settings | Default for new Air Shipments and related air documents. |

### 4.3 Other “carrier” defaults

- **Manifest / Customs:** Where manifest or customs integration supports a carrier, **Default Carrier** may be configured in the relevant Customs or manifest settings for e-manifest or similar flows.

---

## 5. Summary

| Party / provider | Master(s) to create | Default configured in | Applied on |
|------------------|---------------------|------------------------|------------|
| **Shipper** | Shipper (name, customer, address, contact) | — (per document) | Bookings, Shipments, Transport Order, Declaration, Quotes, Warehousing |
| **Consignee** | Consignee (name, customer, address, contact) | — (per document) | Same as Shipper |
| **Freight Agent** | Freight Agent | Sea Freight Settings, Air Freight Settings | Sea/Air Shipments, Bookings, Consolidations, Quotes, Master AWB |
| **Carrier (Sea)** | Shipping Line | Sea Freight Settings → Default Shipping Line | Sea Shipment, Sea Booking, Sea Consolidation, Master Bill |
| **Carrier (Air)** | Airline | Air Freight Settings → Default Airline | Air Shipment, Air Booking, Air Consolidation, Master AWB |
| **Carrier (Manifest)** | As per customs/manifest setup | Manifest Settings (e.g. Default Carrier) | E-manifest / customs manifests |

Ensure at least one **Shipper** and one **Consignee** (with address and contact) exist before creating bookings or shipments. For Sea and Air, create at least one **Freight Agent**, one **Shipping Line** (sea), and one **Airline** (air), and set the **defaults** in [Sea Freight Settings](welcome/sea-freight-settings) and [Air Freight Settings](welcome/air-freight-settings) so new documents are filled automatically where applicable.

## 6. Related Topics

- [Shipper](welcome/shipper)
- [Consignee](welcome/consignee)
- [Sea Freight Settings](welcome/sea-freight-settings)
- [Air Freight Settings](welcome/air-freight-settings)
- [Getting Started](welcome/getting-started)
- [Sea Freight Module](welcome/sea-freight-module)
- [Air Freight Module](welcome/air-freight-module)
- [Glossary](welcome/glossary)
