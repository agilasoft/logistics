# CargoNext Logistics App: Module Feature Analysis & Competitive Benchmark

**Document Purpose:** Review current functions and features of each module, compare with industry practices and leading competitor systems, and suggest improvements to align or lead the market.

**Date:** February 2025  
**App:** CargoNext (Frappe-based logistics ERP)  
**Publisher:** Agilasoft

---

## Executive Summary

CargoNext is a comprehensive freight forwarding ERP covering air freight, sea freight, transport, warehousing, customs, pricing, job management, sustainability, netting, and special projects. The platform has strong foundational coverage across modes but shows gaps in **digital sales**, **AI/automation**, **real-time carrier integration**, **customer self-service**, and **advanced compliance tooling** compared to leaders like CargoWise, Magaya, and Freightos/WebCargo.

---

## 1. Module-by-Module Analysis

### 1.1 Logistics (Core Module)

| Current Features | Industry Practice | Competitors | Gap |
|------------------|-------------------|-------------|-----|
| Logistics Settings, Container Type, CFS, ULD Type | Central master data management | All major platforms | ✓ Aligned |
| Freight Routing, General Job | Multi-mode job orchestration | CargoWise, Magaya | ✓ Aligned |
| Logistics Service Level, Economic Zone | Service tier management | CargoWise | ✓ Aligned |
| Custom Sales Invoice Item fields | ERP integration | Standard | ✓ Aligned |

**Assessment:** Core module is well-structured. No major gaps.

---

### 1.2 Air Freight

| Current Features | Industry Practice | Competitors | Gap |
|------------------|-------------------|-------------|-----|
| Quote → Booking → Shipment → Consolidation → MAWB → Invoice | End-to-end lifecycle | All | ✓ Aligned |
| Flight schedule sync (Aviation Edge, AviationStack, OpenSky) | Real-time flight data | CargoWise, Magaya | ✓ Aligned |
| IATA Cargo XML messaging | Standard messaging | CargoWise, IBS | ✓ Aligned |
| Dangerous Goods Declaration, DG Compliance Report | IATA DGR compliance | DG AutoCheck, Hazcheck | **Partial** – No automated DGD validation vs IATA DGR |
| Hourly job status updates | Proactive tracking | Industry standard | ✓ Aligned |
| On-Time Performance, Revenue/Cost Analysis, Billing Status | Operational analytics | Standard | ✓ Aligned |
| **Missing:** Live carrier rate search | Real-time rate comparison | WebCargo, CargoWise | **Gap** |
| **Missing:** Electronic booking to airlines | eBookings | CargoWise, WebCargo | **Gap** |
| **Missing:** Predictive delay alerts | Proactive problem-solving | Leading platforms | **Gap** |
| **Missing:** AI document ingestion (AWB, invoices) | Automated document processing | CargoWise, Trax, Cambrion | **Gap** |

**Assessment:** Strong operational flow and flight sync. Gaps in **digital sales**, **carrier connectivity**, and **AI document automation**.

---

### 1.3 Sea Freight

| Current Features | Industry Practice | Competitors | Gap |
|------------------|-------------------|-------------|-----|
| Quote → Booking → Shipment → Consolidation → Master Bill → Invoice | Full lifecycle | All | ✓ Aligned |
| Delay/penalty checks (hourly, daily) | Proactive management | Standard | ✓ Aligned |
| Container Utilization, On-Time Performance, Route Analysis | Analytics | Standard | ✓ Aligned |
| Shipping Line Performance Report | Carrier benchmarking | CargoWise | ✓ Aligned |
| Freight Agent, Shipping Line, CTO, CFS, Incoterm, Freight Routing | Master data | Standard | ✓ Aligned |
| **Missing:** Electronic B/L creation & transmission | Automated B/L workflows | CargoWise, Magaya | **Gap** |
| **Missing:** Direct carrier booking integration | eBookings to shipping lines | CargoWise, WebCargo | **Gap** |
| **Missing:** Container ship mapping / vessel tracking | Real-time vessel visibility | CargoWise | **Gap** |
| **Missing:** Port connectivity (Hamburg, Rotterdam, etc.) | Automated port communications | CargoSoft, CargoWise | **Gap** |
| **Missing:** IMDG dangerous goods validation | Sea DG compliance | Hazcheck | **Gap** |

**Assessment:** Solid process and reporting. Gaps in **carrier/port connectivity** and **automated documentation**.

---

### 1.4 Transport

| Current Features | Industry Practice | Competitors | Gap |
|------------------|-------------------|-------------|-----|
| Order → Job → Consolidation → Leg → Run Sheet → Invoice | Full lifecycle | Standard | ✓ Aligned |
| ODDS: Lalamove, Transportify, GrabExpress, NinjaVan | On-demand delivery | Magaya Final Mile | ✓ Aligned |
| Capacity management, vehicle utilization | Fleet optimization | Standard | ✓ Aligned |
| Hourly SLA checks | Proactive SLA monitoring | Standard | ✓ Aligned |
| Portal: Transport Jobs, Stock Balance | Customer visibility | Standard | ✓ Aligned |
| Reports: Vehicle Utilization, Fuel Consumption, Route Cost, Consolidation Savings | Analytics | Standard | ✓ Aligned |
| Proof of Delivery, Road Compliance | Compliance | Standard | ✓ Aligned |
| **Missing:** Telematics integration (GPS, fuel, driver behavior) | Real-time fleet visibility | Magaya LiveTrack, nShift | **Partial** – API exists but limited |
| **Missing:** Route optimization (AI/algorithmic) | Dynamic route planning | Oracle TMS, SAP TM | **Gap** |
| **Missing:** White-label customer portal for booking | Self-service booking | Freightify, Shipthis | **Gap** |

**Assessment:** Strong ODDS and capacity features. Gaps in **telematics**, **route optimization**, and **self-service booking**.

---

### 1.5 Warehousing

| Current Features | Industry Practice | Competitors | Gap |
|------------------|-------------------|-------------|-----|
| Inbound, Release, Transfer, VAS, Stocktake Orders | Full WMS workflows | Magaya, CargoWise | ✓ Aligned |
| Warehouse Job, Storage Location, Handling Unit | Inventory & storage | Standard | ✓ Aligned |
| Mobile: Job Card, Plate Scanner, Count Sheet | Mobile operations | Magaya LiveTrack | ✓ Aligned |
| Portal: Warehousing Portal, Stock Balance, Warehouse Jobs | Customer visibility | Standard | ✓ Aligned |
| Web forms for Release, Transfer, VAS, Stocktake | Self-service orders | ShipHero | ✓ Aligned |
| Reports: Stock Balance, ABC, Labor/Machine Productivity | Analytics | Standard | ✓ Aligned |
| **Missing:** Dimensioner / automated DIM weight capture | Automated cargo measurement | Magaya Dimensioner | **Gap** |
| **Missing:** Pick/pack optimization | Warehouse optimization | Magaya, CargoWise | **Gap** |
| **Missing:** Cross-docking workflows | Cross-dock automation | Magaya | **Gap** |

**Assessment:** Solid WMS with mobile and portal. Gaps in **automation** (dimensioner, pick/pack) and **cross-docking**.

---

### 1.6 Customs

| Current Features | Industry Practice | Competitors | Gap |
|------------------|-------------------|-------------|-----|
| Declaration, Declaration Order, Permit, Exemption | Full customs lifecycle | Standard | ✓ Aligned |
| US AMS, US ISF, CA eManifest, JP AFR | Country-specific APIs | Magaya ACE, CargoWise | ✓ Aligned |
| Base API for extensibility | Multi-country support | Standard | ✓ Aligned |
| Reports: Declaration Status, Filing Compliance, Customs Dashboard | Compliance analytics | Standard | ✓ Aligned |
| **Missing:** Denied party screening (OFAC, etc.) | Trade compliance | CargoWise ComplianceWise, Magaya | **Gap** |
| **Missing:** AI document extraction for customs docs | Automated data entry | Trax, Cambrion | **Gap** |
| **Missing:** ACE certification (US customs broker) | US broker compliance | Magaya | **Gap** – Verify if applicable |
| **Missing:** HS code auto-classification | Intelligent classification | CargoWise | **Gap** |

**Assessment:** Good country-specific integrations. Gaps in **denied party screening** and **AI document processing**.

---

### 1.7 Pricing Center

| Current Features | Industry Practice | Competitors | Gap |
|------------------|-------------------|-------------|-----|
| Multi-mode Sales Quote (Air, Sea, Transport, Customs, Warehouse) | Unified quoting | CargoWise, Magaya | ✓ Aligned |
| Pricing engine, Tariff, Cost Sheet | Rate management | Standard | ✓ Aligned |
| One Off Quote, Change Request | Flexible quoting | Standard | ✓ Aligned |
| create_from_sales_quote.js | Quote-to-job conversion | Standard | ✓ Aligned |
| **Missing:** Live carrier rate integration | Real-time rate search | WebCargo, CargoWise | **Gap** |
| **Missing:** Instant online quoting for customers | Digital sales | Freightos, Freightify | **Gap** |
| **Missing:** Dynamic pricing / margin optimization | AI revenue management | IBS, CargoWise | **Gap** |
| **Missing:** Quote automation with margin logic | Automated quote generation | CargoWise | **Gap** |

**Assessment:** Strong multi-mode structure. Major gap in **digital sales** and **live rate integration**.

---

### 1.8 Job Management

| Current Features | Industry Practice | Competitors | Gap |
|------------------|-------------------|-------------|-----|
| Job Costing Number, Recognition Policy | WIP and accrual | CargoWise job-based engine | ✓ Aligned |
| Recognition engine, doc events on jobs | Revenue/cost recognition | Standard | ✓ Aligned |
| Recognition Status Report | Visibility | Standard | ✓ Aligned |
| **Missing:** Multi-entity / multi-currency job costing | Global operations | CargoWise | **Partial** – ERPNext base |
| **Missing:** Exchange rate and margin management | Multi-currency jobs | CargoWise | **Partial** |

**Assessment:** Solid recognition engine. Multi-entity capabilities depend on ERPNext.

---

### 1.9 Sustainability

| Current Features | Industry Practice | Competitors | Gap |
|------------------|-------------------|-------------|-----|
| Carbon Footprint, Energy Consumption, Emission Factors | Emissions tracking | SAP, Oracle, nShift | ✓ Aligned |
| Integration with Transport, Warehouse, Air, Sea, Declaration | Cross-module carbon | Standard | ✓ Aligned |
| Sustainability Goals, Compliance, Metrics | ESG reporting | Shipzero, DSV | ✓ Aligned |
| Reports: Dashboard, Carbon, Energy, Goals, Trend Analysis | Analytics | Standard | ✓ Aligned |
| **Missing:** ISO 14083 / GLEC Framework certification | Audit-ready emissions | Shipzero, nShift, DSV | **Gap** – Verify compliance |
| **Missing:** CO2 on customer invoices | Shipment-level visibility | DSV, nShift | **Gap** |
| **Missing:** Scope 1/2/3 categorization | GHG Protocol alignment | SAP, Oracle | **Partial** |

**Assessment:** Strong sustainability module. Gaps in **standards certification** and **invoice-level CO2**.

---

### 1.10 Netting

| Current Features | Industry Practice | Competitors | Gap |
|------------------|-------------------|-------------|-----|
| Settlement Group, Settlement Entry | Receivables/payables netting | Standard | ✓ Aligned |
| Journal entries, Sales/Purchase Invoice refs | Settlement automation | Standard | ✓ Aligned |

**Assessment:** Aligned with industry practice.

---

### 1.11 Special Projects

| Current Features | Industry Practice | Competitors | Gap |
|------------------|-------------------|-------------|-----|
| Project lifecycle, Requests, Resources, Equipment | Project-based work | Niche | ✓ Aligned |
| Billing, Deliveries | End-to-end | Standard | ✓ Aligned |

**Assessment:** Differentiated; no major gaps.

---

## 2. Cross-Cutting Capabilities

| Capability | CargoNext | Industry / Competitors | Gap |
|------------|-----------|------------------------|-----|
| **Customer Portal** | Transport Jobs, Stock Balance, Warehousing Portal, Wiki | White-label booking, tracking, docs | **Partial** – No self-service booking |
| **API-First** | Frappe REST API | Extensible integrations | ✓ Adequate |
| **Multi-language** | Frappe base | 30+ languages (CargoWise) | **Partial** |
| **Multi-currency** | ERPNext base | 162 currencies (CargoWise) | **Partial** |
| **Workflow Automation** | Limited | PAVE, agentic AI (CargoWise) | **Gap** |
| **Control Tower / Dashboard** | Workspace dashboards | Real-time control tower | **Partial** |
| **Rail Freight** | Not present | CargoWise, some TMS | **Gap** |

---

## 3. Competitor Snapshot

| Provider | Strengths | CargoNext vs. |
|----------|------------|---------------|
| **CargoWise** | Multi-entity, ComplianceWise, AI doc ingestion, carrier connectivity, 193 countries | CargoNext: smaller scope, fewer integrations |
| **Magaya** | Dimensioner, LiveTrack, ACE customs, CRM, Final Mile | CargoNext: no dimensioner, limited telematics |
| **Freightos/WebCargo** | 10K+ offices, real-time rates, 35+ carriers, instant booking | CargoNext: no live rate/booking integration |
| **Freightify** | White-label portal, self-service booking | CargoNext: portal exists but no booking |
| **Shipzero/nShift** | ISO 14083, GLEC, audit-ready emissions | CargoNext: sustainability present, certification unclear |

---

## 4. Recommended Improvements

### 4.1 High Priority (Align with Market)

1. **Digital Sales & Instant Quoting**
   - Integrate WebCargo or similar for live air/ocean rates.
   - Add customer-facing instant quote (search → rate → book) to reduce manual quoting.
   - *Impact:* 40% conversion lift, 92% processing time reduction (industry benchmarks).

2. **Denied Party Screening**
   - Add ComplianceWise-style screening (OFAC, restricted parties, high-risk destinations).
   - Integrate with Declaration and Shipment workflows.
   - *Impact:* Regulatory risk reduction, required by many enterprise customers.

3. **Electronic Carrier Bookings**
   - eBookings for air (IATA) and ocean (shipping lines).
   - Automated confirmation and status updates.
   - *Impact:* 70% reduction in manual data entry (industry data).

4. **AI Document Processing**
   - Extract data from B/L, AWB, invoices, customs docs.
   - Auto-populate TMS records and customs declarations.
   - *Impact:* 5–7 min saved per document, 70% automation (Trax/Cambrion benchmarks).

### 4.2 Medium Priority (Competitive Parity)

5. **Dangerous Goods Compliance**
   - IATA DG AutoCheck or equivalent for air.
   - IMDG/Hazcheck-style validation for sea.
   - *Impact:* 50% faster DG processing, fewer errors.

6. **Customer Self-Service Portal**
   - White-label portal: book, track, upload docs, view invoices.
   - Branded URL, drag-and-drop documents.
   - *Impact:* 85% fewer customer interactions (industry data).

7. **Sustainability Standards**
   - Align with ISO 14083, GLEC Framework, GHG Protocol.
   - Add CO2 on customer invoices at shipment level.
   - *Impact:* ESG reporting, audit readiness.

8. **Port & Vessel Connectivity**
   - Integrate major ports (e.g., Hamburg, Rotterdam, Antwerp).
   - Container ship mapping / vessel tracking for sea.
   - *Impact:* Proactive delay management, better ETAs.

### 4.3 Strategic (Lead Competitors)

9. **Dimensioner Integration**
   - Integrate Magaya Dimensioner or similar for automated DIM/weight.
   - *Impact:* ~$40/pallet recovered, 3 min/shipment saved (Magaya data).

10. **Route Optimization**
    - Algorithmic route optimization for transport.
    - *Impact:* Lower fuel cost, better utilization.

11. **Predictive Analytics**
    - Delay prediction, demand forecasting, anomaly detection.
    - *Impact:* Proactive problem-solving, higher customer satisfaction.

12. **Workflow Automation Engine**
    - Configurable workflows (PAVE-style) without code.
    - *Impact:* Faster onboarding, lower customization cost.

---

## 5. Implementation Roadmap (Suggested)

| Phase | Focus | Timeline |
|-------|--------|----------|
| **Phase 1** | Denied party screening, DG compliance (IATA/IMDG) | 3–6 months |
| **Phase 2** | Digital sales (WebCargo or similar), customer portal enhancement | 6–12 months |
| **Phase 3** | AI document processing, eBookings | 12–18 months |
| **Phase 4** | Sustainability certification, CO2 on invoices | 6–12 months |
| **Phase 5** | Dimensioner, route optimization, predictive analytics | 18–24 months |

---

## 6. Summary

CargoNext has a strong foundation across air, sea, transport, warehousing, customs, pricing, and sustainability. The largest gaps versus CargoWise, Magaya, and Freightos are:

- **Digital sales** (live rates, instant quoting, self-service booking)
- **Carrier/port connectivity** (eBookings, vessel tracking)
- **Compliance** (denied party screening, DG validation)
- **AI/automation** (document processing, workflow engine)

Prioritizing denied party screening, DG compliance, and digital sales will bring CargoNext in line with market leaders. Adding AI document processing, dimensioner integration, and predictive analytics can position it ahead of many competitors.

---

*This document is for internal review. Verify competitor features and industry benchmarks with current vendor materials and customer feedback.*
