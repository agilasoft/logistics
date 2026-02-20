# Multimodal Quotation Design

## 1. Overview

This document describes the design for **multimodal** logistics flows where **one quotation represents one billing** but involves **multiple jobs and legs from different modules** (Air Freight, Sea Freight, Transport, Customs, Warehousing). The different legs/jobs are captured in **routing details** and linked to the quotation, booking, or shipment/job level.

---

## 2. Current State Analysis

### 2.1 What Exists Today

| Component | Current Implementation | Multimodal Support |
|-----------|------------------------|-------------------|
| **Sales Quote** | Tabs: Sea, Air, Transport, Customs, Warehousing. Each mode has its own child table. User can check multiple (is_sea, is_air, is_transport). | **Partial** – Multiple modes in one quote, but no unified routing sequence or leg-to-job linkage. |
| **Freight Routing** | Standalone doctype with `routes` (Freight Routing Items). Each leg has: mode (Air/Sea/Road/Rail/Inland Waterway/Other), job_type (DocType), job_no (Dynamic Link). | **Yes** – Designed for multi-mode legs with job linkage. Not linked to Sales Quote. |
| **Freight Routing Items** | Child table: mode, job_type, job_no, loading_port, discharge_port, etd, eta, type (Main/Pre-carriage/On-forwarding), status. | **Yes** – Can reference Transport Job, Air Shipment, Sea Shipment per leg. |
| **Air/Sea Booking Routing Leg** | Child table on Air/Sea Booking: mode (SEA/AIR), vessel, voyage, flight_no, load_port, discharge_port, etd, eta. | **Partial** – SEA/AIR only. No job_type/job_no link. No Road/Rail. |
| **Transport "multimodal"** | Load type flag (Multimodal/Heavy Haul) for RORO-style transport jobs. | **Different meaning** – Refers to vehicle capability, not cross-module routing. |

### 2.2 Gaps

1. **No unified routing at quotation level** – Sales Quote has separate tabs per mode; no single "routing details" showing leg sequence across modes.
2. **No leg-to-job linkage at quote/booking** – When jobs are created from a quote, there is no structured way to link each routing leg to its corresponding Air Shipment, Sea Shipment, or Transport Job.
3. **Freight Routing is standalone** – Not linked to Sales Quote; used for route templates, not per-quote routing.
4. **Create-from flows are per-mode** – "Create Air Booking", "Create Sea Booking", "Create Transport Order" are separate actions. No orchestrated "Create Multimodal Jobs" that respects routing sequence.

---

## 3. Design Goals

1. **One quotation = one billing** – A single Sales Quote (or Multimodal Quote) represents the commercial agreement; all legs roll up to it for invoicing.
2. **Routing details hold legs/jobs** – A routing table lists legs in sequence; each leg has mode and optionally links to the created job/shipment.
3. **Placement** – Design supports implementation at **Quotation**, **Booking**, or **Shipment/Job** level (or a combination).
4. **Reuse existing structures** – Align with Freight Routing Items (mode, job_type, job_no) and Air/Sea Booking Routing Legs.

---

## 4. Recommended Placement

| Level | Pros | Cons |
|-------|------|------|
| **Quotation (Sales Quote)** | Single source of truth; routing defined at quote time; billing reference. | Quote may be created before jobs exist; job_no filled later. |
| **Booking** | Air/Sea Booking have routing tabs; closer to operations. | Multiple bookings (Air, Sea) per quote; no single "multimodal booking". |
| **Shipment/Job** | Jobs exist; can link legs to actual documents. | Shipments/jobs are created after quote; routing would be downstream. |

**Recommendation:** Implement at **all three levels** with clear responsibilities:

| Level | Responsibility |
|-------|----------------|
| **Sales Quote** | Define **intended routing** (leg sequence, mode, origin/destination per leg). Optional: link to jobs once created. |
| **Booking** | Per-mode routing (Air/Sea) as today; add **job_type/job_no** to link to Transport Job, Air Shipment, Sea Shipment when applicable. |
| **Shipment/Job** | **Actual routing** – each leg links to the real job/shipment. Used for traceability and reporting. |

---

## 5. Main Job, Sub-Jobs, and Billing Model

### 5.1 Main Job

One routing leg is designated as the **Main Job**. The Main Job:

- **Does customer billing** — The Sales Invoice is created from the Main Job.
- **Holds the Job Costing Number** — Revenue and profitability are tracked at the Main Job level.
- **Receives internal charges from Sub-Jobs** — Sub-jobs bill the Main Job using tariffs (internal transfer pricing).

Typically the **Main** leg (type = Main) is the Main Job — e.g. the Sea Shipment or Air Shipment for ocean/air freight, or the primary Transport Job for domestic-only moves.

### 5.2 Sub-Jobs

All other legs are **Sub-Jobs**. Sub-Jobs:

- **Bill internally** — They do not invoice the customer directly. Instead, they charge the Main Job using tariffs (internal rates).
- **Use tariffs** — Charges are calculated via Tariff against the Main Job (or a shared cost center/profit center).
- **Support cost allocation** — Costs flow into the Main Job for consolidated profitability.

### 5.3 Billing Option (User Choice)

A user-configurable option on the Sales Quote (or Main Job) controls how the customer is billed:

| Option | Description | Result |
|--------|--------------|--------|
| **Consolidated billing** | All charges from Main Job + Sub-Jobs roll up into a single Sales Invoice. One invoice to the customer. | Single invoice; profitability at Main Job level. |
| **Bill separately per product** | Each leg/product is billed on its own Sales Invoice (or as separate line items). Customer receives multiple invoices or a split invoice. | Multiple invoices or split lines; profitability can be per leg or consolidated. |

**Field:** `billing_mode` (Select) on Sales Quote or Main Job:
- **Consolidated** — One invoice from Main Job, aggregating all leg charges.
- **Per Product** — Separate invoice(s) per leg/product.

---

## 6. Data Model

### 6.1 Sales Quote: Multimodal Routing Tab

Add a new tab **"Routing"** (or **"Multimodal Routing"**) to Sales Quote, visible when more than one mode is selected (is_sea + is_air, or is_sea + is_transport, etc.).

**Child DocType:** `Sales Quote Routing Leg` (new)

| Field | Type | Description |
|-------|------|-------------|
| `leg_order` | Int | Sequence (1, 2, 3, …). |
| `mode` | Select | Air, Sea, Road, Rail, Inland Waterway, Other. |
| `type` | Select | Main, Pre-carriage, On-forwarding, Other. |
| `status` | Select | Confirmed, Planned, On-hold. |
| `origin` | Link (UNLOCO) | Origin port/location. |
| `destination` | Link (UNLOCO) | Destination port/location. |
| `etd` | Date | Estimated departure. |
| `eta` | Date | Estimated arrival. |
| `job_type` | Link (DocType) | Transport Job, Air Shipment, Sea Shipment, Air Booking, Sea Booking, Transport Order. |
| `job_no` | Dynamic Link | Link to job_type. Filled when job is created from quote. |
| `notes` | Small Text | Free-form notes. |

**Behaviour:**
- When user creates Air Booking / Sea Booking / Transport Order from Sales Quote, the create-from logic can optionally populate `job_no` on the matching routing leg (by mode and sequence).
- Billing: Sales Invoice can reference Sales Quote; all charges from linked jobs/shipments roll up to that quote for unified billing.

### 6.2 Main Job Designation

Add to Sales Quote Routing Leg (or equivalent):

| Field | Type | Description |
|-------|------|-------------|
| `is_main_job` | Check | When set, this leg is the Main Job. Exactly one leg per quote should be Main. The Main Job does customer billing. |

Add to Sales Quote (or Main Job doctype):

| Field | Type | Description |
|-------|------|-------------|
| `billing_mode` | Select | **Consolidated** — One invoice aggregating all legs. **Per Product** — Separate invoice(s) per leg/product. |

### 6.3 Extend Freight Routing Items (or Booking Routing Legs)

**Option A – Extend Air/Sea Booking Routing Leg:**
- Add `job_type` (Link to DocType) and `job_no` (Dynamic Link).
- Add `mode` option: Road, Rail (in addition to SEA, AIR) for pre-carriage/on-forwarding legs.
- When mode = Road, `job_no` can link to Transport Job.

**Option B – Reuse Freight Routing Items pattern:**
- Create a generic **Multimodal Routing Leg** child table used by Sales Quote and optionally by a "Multimodal Shipment" or "General Job" doctype.
- Same fields as Freight Routing Items: mode, job_type, job_no, origin, destination, etd, eta, type, status.

### 6.4 Shipment/Job Level: Link Back to Quote and Routing

Ensure downstream documents link back:
- **Air Shipment**, **Sea Shipment**, **Transport Job** already have `sales_quote` (or similar).
- Add optional `sales_quote_routing_leg` (Link) on each to indicate which leg of the multimodal quote this job fulfils. (Phase 2; can defer.)

---

## 7. Routing Details Structure (Unified)

The **routing details** table (whether on Sales Quote, Freight Routing, or a new Multimodal Shipment) should support:

```
Leg 1: Road    | Pre-carriage  | Sub-Job  | Warehouse A → Port X    | ETD 01-Mar | job_no: TJ-001 (Transport Job)
Leg 2: Sea     | Main         | Main Job | Port X → Port Y         | ETD 05-Mar | job_no: SS-001 (Sea Shipment)
Leg 3: Road    | On-forwarding| Sub-Job  | Port Y → Consignee     | ETD 12-Mar | job_no: TJ-002 (Transport Job)
```

- **leg_order** defines sequence.
- **is_main_job** marks Leg 2 (Sea) as the Main Job — it does customer billing; Legs 1 and 3 bill internally to the Main Job via tariffs.
- **mode** defines transport mode per leg.
- **job_type** + **job_no** link to the actual document (filled when created).
- **origin** / **destination** can be UNLOCO (ports) or Address/Facility for road legs.

---

## 8. Implementation Phases

### Phase 1 – Sales Quote Routing Tab
- Create `Sales Quote Routing Leg` child DocType.
- Add "Routing" tab to Sales Quote, shown when `is_multimodal` or when more than one of (is_sea, is_air, is_transport) is set.
- Add `is_multimodal` (Check) to Sales Quote for explicit flag.
- Fields: leg_order, mode, type, status, origin, destination, etd, eta, job_type, job_no, notes.

### Phase 2 – Populate job_no on Create
- When "Create Air Booking" / "Create Sea Booking" / "Create Transport Order" is run from Sales Quote, update the corresponding routing leg's `job_no` with the created document.
- Matching logic: by mode (Air→Air Booking/Shipment, Sea→Sea Booking/Shipment, Road→Transport Order/Job) and leg_order.

### Phase 3 – Extend Booking/Shipment Routing
- Add job_type, job_no to Air Booking Routing Leg, Sea Booking Routing Leg (and Shipment equivalents).
- Add Road, Rail to mode options where applicable for pre-carriage/on-forwarding.

### Phase 4 – Main Job, Sub-Jobs, and Billing
- Add `is_main_job` (Check) to Sales Quote Routing Leg; designate one leg as Main Job.
- Add `billing_mode` (Consolidated / Per Product) to Sales Quote.
- Sub-jobs bill internally to Main Job via tariffs (internal transfer pricing).
- **Consolidated:** Create Sales Invoice from Main Job, aggregating charges from all legs.
- **Per Product:** Create separate Sales Invoice(s) per leg/product as per user choice.
- Report: "Multimodal Quote Status" – Quote, legs, Main Job, linked jobs, status per leg.

---

## 9. UI/UX Considerations

1. **Routing tab on Sales Quote** – Table with columns: Leg, Mode, Type, Origin, Destination, ETD, ETA, Job No (read-only, auto-filled). Add row, reorder.
2. **Create-from actions** – Consider "Create All Jobs from Quote" that creates Air Booking, Sea Booking, Transport Order in sequence and populates job_no on routing legs.
3. **Visual** – Optional: Timeline or route map showing legs in order (Phase 2).

---

## 10. Alignment with Existing Design

- **LOGISTICS_MODULE_INTEGRATION_DESIGN.md** – This design extends the integration by adding explicit routing and job linkage at quote level.
- **ROUTING_TAB_DESIGN.md** – Air/Sea Booking Routing Legs remain; we add job_type/job_no and optional Road/Rail modes.
- **Freight Routing** – Can remain standalone for route templates; Sales Quote Routing Leg is the per-quote instance. Alternatively, link Freight Routing to Sales Quote as a "template" and copy routes to Sales Quote Routing Legs.

---

## 11. Summary

| Aspect | Design |
|--------|--------|
| **Main Job** | One routing leg designated as Main Job; does customer billing; holds Job Costing Number. |
| **Sub-Jobs** | Other legs bill internally to Main Job using tariffs (internal transfer pricing). |
| **Billing mode** | User option: **Consolidated** (one invoice) or **Per Product** (separate invoice per leg/product). |
| **Multiple jobs/legs** | Routing details table with leg_order, mode, type, is_main_job, job_type, job_no. |
| **Placement** | Sales Quote (primary), extend Booking/Shipment routing with job links. |
| **Routing details** | Child table: leg_order, mode, type, is_main_job, origin, destination, etd, eta, job_type, job_no. |
| **Create-from** | Populate job_no when creating Air/Sea/Transport documents from quote. |

This design enables **one quotation** with a **Main Job** that does customer billing, **Sub-Jobs** that bill internally via tariffs, and a user choice between **consolidated** or **per-product** billing.
