# Logistics Module Integration Design

## 1. Overview

This document describes the design of **integration** between different logistics modules in the application. Multi-modal supply chains typically involve combinations of:

- **Air Freight** — Air Booking → Air Shipment
- **Sea Freight** — Sea Booking → Sea Shipment
- **Transport** — Transport Order → Transport Job
- **Customs** — Declaration Order → Declaration, Global Manifest
- **Warehousing** — Inbound Order, Release Order, Warehouse Job

Integration enables:

1. **End-to-end visibility** — Trace cargo from quote through freight, customs, transport, and warehousing
2. **Data flow** — Parties (shipper, consignee), dates, packages, and charges flow between modules
3. **Document creation** — Create downstream documents from upstream sources (e.g. Global Manifest from Sea Shipment)
4. **Unified costing and billing** — Special Projects, Job Costing Number, and Sales Invoice link across modules

---

## 2. Integration Scenarios

### 2.1 Air/Sea Freight Shipment with Customs and Transport

**Typical flow:** Import or export shipment arrives at port/airport → customs clearance → domestic transport to warehouse or final destination.

```
Sales Quote (multi-modal)
    │
    ├── Air Booking / Sea Booking
    │       └── Convert to Air Shipment / Sea Shipment
    │
    ├── Declaration Order (Customs) ← from Sales Quote (is_customs=1)
    │       └── Declaration ← create_declaration_from_declaration_order
    │           (or create_declaration_from_sales_quote for one-off)
    │
    ├── Global Manifest ← created from Air Shipment / Sea Shipment / Transport Order
    │
    └── Transport Order ← created for pickup/delivery legs
            └── Transport Job
```

**Current integration points:**

| Source | Target | Mechanism |
|--------|--------|-----------|
| Air Shipment | Global Manifest | `create_from_air_shipment(air_shipment_name)` — populates vessel/flight, ports, ETD/ETA, carrier |
| Sea Shipment | Global Manifest | `create_from_sea_shipment(sea_shipment_name)` — populates vessel, voyage, ports, ETD/ETA, carrier |
| Air Shipment | Customs | Air Shipment has embedded **Customs Information** section: `customs_declaration_number`, `customs_status`, `customs_broker`, `duty_amount`, `customs_clearance_date` |
| Sea Shipment | Customs | Similar embedded customs fields; JP AFR Bill, CA eManifest Bill, US AMS Bill link `declaration`, `sea_shipment`, `air_shipment` |
| Sales Quote | Declaration Order | Declaration Order links to Sales Quote (is_customs=1); order-level customs request |
| Declaration Order | Declaration | `create_declaration_from_declaration_order()` — creates Declaration with customer, customs_authority, charges from Sales Quote |
| Sales Quote | Declaration | `create_declaration_from_sales_quote()` — one-off flow; creates Declaration directly when quote has customs |
| Shipment → Transport | Transport Order | Manual or via Special Projects; ODDs (Lalamove, Transportify) can create quotations from Air/Sea Shipment for last-mile delivery |

**Design recommendations:**

- **Declaration Order ↔ Shipment:** Add `air_shipment` and `sea_shipment` (Link) on Declaration Order when the customs order is tied to a specific freight shipment. Enables traceability and "Create Declaration Order from Shipment."
- **Declaration ↔ Shipment:** Add explicit `air_shipment` and `sea_shipment` (Link) fields on Declaration so customs declarations can be traced to the freight shipment. Today this is indirect (via Sales Quote, customs bills).
- **Transport Order from Shipment:** Add “Create Transport Order” action on Air Shipment and Sea Shipment for pickup-from-port or delivery-to-warehouse legs. Populate origin from shipment destination port/airport, destination from warehouse or consignee address.
- **Customs clearance gates:** Use `customs_status` and `customs_clearance_date` on shipment to gate transport job creation (e.g. only allow delivery after customs cleared).

---

### 2.2 Customs: Declaration Order and Declaration

**Typical flow:** Customs clearance is requested via Declaration Order (from Sales Quote) or directly as Declaration (one-off from Sales Quote). Declaration is the submitted customs declaration document.

```
Sales Quote (is_customs=1)
    │
    ├── Declaration Order (order-level customs request)
    │       └── Create Declaration
    │
    └── Declaration (one-off, create_declaration_from_sales_quote)
```

**Declaration Order** — Order/request for customs clearance. Links to Sales Quote. Created manually when a customer needs customs services.

**Declaration** — The actual customs declaration document. Created from:
- **Declaration Order** — `create_declaration_from_declaration_order()` — copies customer, customs_authority, company, charges from Sales Quote
- **Sales Quote** — `create_declaration_from_sales_quote()` — one-off flow when quote has customs

**Current integration:** Declaration has `declaration_order`, `sales_quote`; transport fields (port_of_loading, port_of_discharge, vessel_flight_number, etd, eta); commodities; charges. Declaration feeds into Global Manifest Bill, JP AFR Bill, CA eManifest Bill, US AMS Bill.

**Proposed:** Add `air_shipment`, `sea_shipment`, `transport_order` on both Declaration Order and Declaration to trace customs to freight/transport and enable "Create Declaration from Shipment" with auto-populated transport/vessel data.

---

### 2.3 Transport Job with Connected Sea/Air Shipment (Domestic, RORO)

**Typical flow:** Transport job that picks up from port (after sea/air arrival) or delivers to port (before sea/air departure). Includes RORO (Roll-on/Roll-off) — vehicles or machinery driven on/off vessel.

```
Sea Shipment / Air Shipment (domestic leg or port transfer)
    │
    └── Transport Order (port pickup/delivery)
            └── Transport Job
                    └── transport_job_type: Container, Non-Container, Special, Oversized, Multimodal, Heavy Haul
```

**Current integration points:**

| Source | Target | Mechanism |
|--------|--------|-----------|
| Transport Order | Transport Job | `action_create_transport_job(docname)` — creates Transport Job from submitted Transport Order |
| ODDs (Lalamove, Transportify) | Air/Sea Shipment | Odds Order and Odds Quotation have `air_shipment`, `air_booking`, `sea_shipment`, `sea_booking` — can create delivery from freight document |
| Transport Job | transport_job_type | Supports `Container`, `Multimodal`, `Heavy Haul` for RORO-style moves |

**Design recommendations:**

- **Transport Order ↔ Shipment:** Add `air_shipment` and `sea_shipment` (Link) on Transport Order and Transport Job when the transport leg is port pickup/delivery. Enables:
  - Traceability from transport to freight
  - Auto-populate origin (port/airport) and destination from shipment
  - Visibility: “Which transport jobs serve this air/sea shipment?”
- **RORO:** Use `transport_job_type = "Multimodal"` or `"Heavy Haul"`; optionally add `shipment` link for RORO vessel connection.
- **Create Transport Order from Shipment:** Add “Create Transport Order” (pickup/delivery) on Air Shipment and Sea Shipment. Pre-fill:
  - Origin: shipment destination (for import delivery) or customer (for export pickup)
  - Destination: shipment origin (export) or consignee/warehouse (import)
  - Packages, weight, volume from shipment
  - Shipper, consignee from shipment

---

### 2.4 Sea/Air/Transport to Warehouse Facility

**Typical flow:** Freight arrives → customs cleared → transport to warehouse → Inbound Order → Warehouse Job (Putaway).

```
Air Shipment / Sea Shipment / Transport Job
    │
    └── Inbound Order (receive goods into warehouse)
            └── Warehouse Job (Putaway)
```

**Current integration points:**

| Source | Target | Mechanism |
|--------|--------|-----------|
| Sales Quote | Warehouse Contract | Create Warehouse Contract from Sales Quote |
| Warehouse Contract | Inbound Order | Create Inbound Order under contract |
| Inbound Order | Warehouse Job | `make_warehouse_job()` — Putaway job |
| Shipper/Consignee | Propagate | Sales Quote → Warehouse Contract → Inbound Order → Warehouse Job |
| Special Projects | Inbound Order | Create Inbound Order from Special Project Product Request |

**Design recommendations:**

- **Shipment/Transport → Inbound Order:** Add `air_shipment`, `sea_shipment`, `transport_job` (Link) on Inbound Order. When creating Inbound Order from a shipment or transport job:
  - Auto-populate: customer, shipper, consignee, items (from shipment packages or transport packages), dates (ETA from shipment/transport)
  - Enables: “Create Inbound Order from Air Shipment” — extract packages, weights, descriptions, marks
- **Release Order → Shipment/Transport:** Add `air_shipment`, `sea_shipment`, `transport_order` (Link) on Release Order when goods are being shipped out via freight or transport. Enables:
  - Traceability from warehouse release to outbound shipment
  - Auto-populate delivery address or port from shipment
- **Warehouse Job links:** Add optional `air_shipment`, `sea_shipment`, `transport_job` on Warehouse Job for receiving jobs that correspond to a specific freight or transport leg.

---

## 3. Cross-Module Data Extraction

### 3.1 What Can Be Extracted from Freight to Warehousing

| Freight Field | Inbound Order / Warehouse Job |
|---------------|-------------------------------|
| Shipper | shipper |
| Consignee | consignee |
| Customer | customer (local_customer from shipment) |
| Packages | items (qty, UOM, weight, volume from shipment packages) |
| Description, Marks | item description, marks_and_nos |
| ETA | planned_date, due_date |
| Incoterm | (for billing/receiving terms) |
| Sales Quote | quote reference |

### 3.2 What Can Be Extracted from Transport to Warehousing

| Transport Field | Inbound Order / Warehouse Job |
|-----------------|-------------------------------|
| Origin / Destination | Dock assignment, receiving location |
| Packages | items |
| Shipper, Consignee | shipper, consignee |
| ETA | planned_date |
| Customer | customer |

### 3.3 What Can Be Extracted from Warehousing to Freight/Transport

| Warehouse Field | Freight / Transport |
|-----------------|---------------------|
| Release Order items | Sea/Air Booking/Shipment packages |
| Warehouse address | Transport Order destination (for delivery) |
| Shipper, Consignee | Propagate to shipment/transport |

---

## 4. Link Field Summary

### 4.1 Recommended New / Enhanced Links

| DocType | Link Field | Options | Purpose |
|---------|------------|---------|---------|
| Declaration Order | air_shipment | Air Shipment | Trace customs order to air freight |
| Declaration Order | sea_shipment | Sea Shipment | Trace customs order to sea freight |
| Declaration | air_shipment | Air Shipment | Trace customs declaration to air freight |
| Declaration | sea_shipment | Sea Shipment | Trace customs declaration to sea freight |
| Declaration | transport_order | Transport Order | Trace customs to domestic transport (cross-border) |
| Transport Order | air_shipment | Air Shipment | Port pickup/delivery for air freight |
| Transport Order | sea_shipment | Sea Shipment | Port pickup/delivery for sea freight |
| Transport Job | air_shipment | Air Shipment | Same as above |
| Transport Job | sea_shipment | Sea Shipment | Same as above |
| Inbound Order | air_shipment | Air Shipment | Receive goods from air freight |
| Inbound Order | sea_shipment | Sea Shipment | Receive goods from sea freight |
| Inbound Order | transport_job | Transport Job | Receive goods from domestic transport |
| Release Order | air_shipment | Air Shipment | Ship out via air |
| Release Order | sea_shipment | Sea Shipment | Ship out via sea |
| Release Order | transport_order | Transport Order | Ship out via transport |
| Warehouse Job | air_shipment | Air Shipment | Receiving from air |
| Warehouse Job | sea_shipment | Sea Shipment | Receiving from sea |
| Warehouse Job | transport_job | Transport Job | Receiving from transport |

### 4.2 Existing Links (No Change)

| DocType | Link Field | Options |
|---------|------------|---------|
| Declaration Order | sales_quote | Sales Quote |
| Declaration | declaration_order | Declaration Order |
| Declaration | sales_quote | Sales Quote |
| Global Manifest | sea_shipment | Sea Shipment |
| Global Manifest | air_shipment | Air Shipment |
| Global Manifest | transport_order | Transport Order |
| Odds Order / Odds Quotation | air_shipment, sea_shipment, air_booking, sea_booking, transport_order, transport_job, warehouse_job | Various |
| Lalamove Order | air_shipment, sea_shipment, air_booking, sea_booking, transport_order, transport_job, warehouse_job | Various |
| JP AFR Bill, CA eManifest Bill, US AMS Bill | declaration, sea_shipment, air_shipment | Customs bills |

---

## 5. Action Summaries

### 5.1 Create-From Actions

| Action | Source | Target | Status |
|--------|--------|--------|--------|
| Create Declaration Order | Sales Quote | Declaration Order | Implemented (manual; Sales Quote is_customs=1) |
| Create Declaration | Declaration Order | Declaration | Implemented (`create_declaration_from_declaration_order`) |
| Create Declaration | Sales Quote | Declaration | Implemented (`create_declaration_from_sales_quote` for one-off) |
| Create Global Manifest | Sea Shipment | Global Manifest | Implemented |
| Create Global Manifest | Air Shipment | Global Manifest | Implemented |
| Create Global Manifest | Transport Order | Global Manifest | Implemented |
| Create Transport Job | Transport Order | Transport Job | Implemented |
| Create Air Shipment | Air Booking | Air Shipment | Implemented |
| Create Sea Shipment | Sea Booking | Sea Shipment | Implemented |
| Create Transport Order | One-Off Quote | Transport Order | Implemented |
| Create Air Booking | One-Off Quote | Air Booking | Implemented |
| Create Sea Booking | One-Off Quote | Sea Booking | Implemented |
| Create Declaration Order | Air/Sea Shipment | Declaration Order | **Proposed** |
| Create Declaration | Air/Sea Shipment | Declaration | **Proposed** (or link existing) |
| Create Inbound Order | Shipment / Transport | Inbound Order | **Proposed** |
| Create Transport Order | Air/Sea Shipment | Transport Order | **Proposed** |
| Create Release Order | Shipment / Transport | Release Order | **Proposed** (or link existing) |

### 5.2 Propagate-On-Link

When a link field is set, propagate key fields where applicable:

| When | Copy From | To |
|------|-----------|-----|
| Inbound Order.air_shipment set | Air Shipment | Inbound Order: shipper, consignee, customer, packages, ETA |
| Inbound Order.sea_shipment set | Sea Shipment | Same |
| Inbound Order.transport_job set | Transport Job | Same |
| Transport Order.air_shipment set | Air Shipment | Transport Order: origin (airport), destination, packages, dates |
| Transport Order.sea_shipment set | Sea Shipment | Same (port) |
| Declaration Order.air_shipment set | Air Shipment | Declaration Order: customer, parties (from shipment) |
| Declaration Order.sea_shipment set | Sea Shipment | Same |
| Declaration.air_shipment set | Air Shipment | Declaration: exporter, importer, vessel/flight, ports, ETD/ETA |
| Declaration.sea_shipment set | Sea Shipment | Same |

---

## 6. Special Projects Integration

The **Special Projects** module already orchestrates multiple job types:

- Transport Job
- Warehouse Job
- Air Shipment
- Sea Shipment
- Declaration Order
- Declaration

All link via **project** (ERPNext Project). Special Project Jobs child table references these doctypes. Costing and billing roll up to the project.

**Integration with this design:** When adding `air_shipment`, `sea_shipment`, `transport_job` links to Inbound Order, Release Order, and Warehouse Job, ensure that:

- If the linked document has a `project`, optionally propagate or display it on the warehouse document for unified project visibility.
- Special Project Product Request → Create Inbound Order can optionally pass `air_shipment` / `sea_shipment` / `transport_job` when the request is fulfilled from a freight or transport source.

---

## 7. RORO and Multi-Modal Considerations

### 7.1 RORO (Roll-on/Roll-off)

- **Transport Job Type:** Use `Multimodal` or `Heavy Haul` for RORO.
- **Sea Shipment:** RORO cargo typically travels as sea freight; link Transport Job (port delivery) to Sea Shipment for traceability.
- **Optional:** Add `roro` (Check) on Transport Job or Transport Order when the move is specifically RORO.

### 7.2 Multi-Modal Routing

- **Routing Tab** (Air/Sea Booking and Shipment): Supports multi-leg routing with mode (SEA/AIR) per leg. Pre-carriage and on-forwarding legs can represent domestic transport.
- **Integration:** Transport Order/Job can represent the road leg; link to the Air/Sea Shipment routing leg for full multi-modal visibility.

---

## 8. Implementation Phases

### Phase 1 — Link Fields

- Add `air_shipment`, `sea_shipment` to Declaration Order and Declaration.
- Add `air_shipment`, `sea_shipment` to Transport Order and Transport Job.
- Add `air_shipment`, `sea_shipment`, `transport_job` to Inbound Order.
- Add `air_shipment`, `sea_shipment`, `transport_order` to Release Order.
- Add `air_shipment`, `sea_shipment`, `transport_job` to Warehouse Job (optional).

### Phase 2 — Create-From Actions

- “Create Transport Order” on Air Shipment and Sea Shipment.
- “Create Inbound Order” on Air Shipment, Sea Shipment, and Transport Job.
- Populate origin, destination, packages, parties from source.

### Phase 3 — Propagate-On-Link

- When link fields are set, auto-populate key fields (shipper, consignee, packages, dates).
- Validate consistency (e.g. Inbound Order ETA aligns with shipment ETA).

### Phase 4 — UI and Reports

- Connections tab / dashboard on each doctype showing linked documents.
- Reports: “Shipment Connections” (all linked declarations, transport, warehouse); “Inbound Order from Freight” list.

---

## 9. Diagram: End-to-End Integration Flow

```
                                    ┌─────────────────┐
                                    │   Sales Quote   │
                                    │ (multi-modal)   │
                                    └────────┬────────┘
                                             │
              ┌──────────────┬───────────────┼───────────────┬──────────────┐
              │              │               │               │              │
              ▼              ▼               ▼               ▼              ▼
     ┌─────────────┐ ┌─────────────┐ ┌───────────┐ ┌─────────────┐ ┌─────────────┐
     │ Air Booking │ │ Sea Booking │ │ Transport  │ │ Declaration │ │  Warehouse  │
     │             │ │             │ │   Order    │ │   Order     │ │  Contract   │
     └──────┬──────┘ └──────┬──────┘ └─────┬─────┘ └──────┬──────┘ └──────┬──────┘
            │               │              │              │               │
            ▼               ▼              │              ▼               │
     ┌─────────────┐ ┌─────────────┐      │       ┌───────────┐          │
     │ Air Shipment│ │ Sea Shipment│      │       │Declaration│          │
     └──────┬──────┘ └──────┬──────┘      │       └─────┬─────┘          │
            │               │              │             │               │
            │               │              ▼             │               │
            │               │       ┌─────────────┐      │               │
            │               │       │Transport Job │      │               │
            │               │       └──────┬──────┘      │               │
            │               │              │             │               │
            │               │              │             │               │
            ▼               ▼              ▼             ▼               ▼
     ┌─────────────────────────────────────────────────────────────────────────┐
     │                     GLOBAL MANIFEST (Customs)                             │
     │   Links: sea_shipment | air_shipment | transport_order                   │
     └─────────────────────────────────────────────────────────────────────────┘
            │               │              │
            ▼               ▼              ▼
     ┌─────────────────────────────────────────────────────────────────────────┐
     │                     INBOUND ORDER / RELEASE ORDER                        │
     │   Links: air_shipment | sea_shipment | transport_job                     │
     └─────────────────────────────────────────────────────────────────────────┘
            │
            ▼
     ┌─────────────┐
     │Warehouse Job│
     │ (Putaway)   │
     └─────────────┘
```

---

## 10. Summary

| Integration | Current State | Proposed |
|-------------|---------------|----------|
| Freight ↔ Customs | Declaration Order → Declaration flow from Sales Quote; Air/Sea Shipment have embedded customs fields; Global Manifest links to both; Declaration/Declaration Order have no direct shipment link | Add Declaration Order and Declaration.air_shipment, sea_shipment; Create Declaration from Shipment |
| Freight ↔ Transport | ODDs link to Shipment; no Transport Order/Job link to Shipment | Add Transport Order/Job.air_shipment, sea_shipment; Create Transport Order from Shipment |
| Freight ↔ Warehousing | No direct link | Add Inbound/Release Order.air_shipment, sea_shipment, transport_job; Create Inbound Order from Shipment/Transport |
| Transport ↔ Warehousing | Special Projects; no direct link | Add Inbound Order.transport_job; Warehouse Job.transport_job |
| RORO / Multimodal | transport_job_type supports Multimodal, Heavy Haul | Optional: Add shipment link for RORO traceability |

This design enables end-to-end visibility and data flow across Air Freight, Sea Freight, Transport, Customs, and Warehousing modules, supporting multi-modal supply chains from quote to delivery.
