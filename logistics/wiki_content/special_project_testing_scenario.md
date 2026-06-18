# Special Project — End-to-End Testing Scenario

Use this guide as a **real-world customer walkthrough** when testing [Special Project](welcome/special-projects-module), linked [Sales Quote](welcome/sales-quote), charges, shipper/consignee, and fulfillment. It is based on a telecom infrastructure rollout in the Philippines.

---

## 1. Customer profile

| Field | Value |
| --- | --- |
| **Company** | Solara Telecom Infrastructure Pte Ltd |
| **Industry** | Telecom / renewable energy (off-grid tower sites) |
| **Contact** | Maria Elena Santos — Head of Supply Chain |
| **Email** | maria.santos@solara-telecom.ph |
| **Phone** | +63 917 482 3391 |
| **Billing entity** | Solara Telecom Infrastructure Pte Ltd (Singapore HQ) |
| **Operating region** | Luzon, Philippines |

### Customer inquiry (summary)

Solara won a contract with **Globe Rural Connect** to upgrade **14 off-grid cell tower sites** in Northern Luzon. Each site receives a solar micro-grid kit (panels, lithium battery racks, inverters, mounting hardware, cabling). Kits vary: 3 sites are “heavy load” (larger battery banks), 11 are standard.

**Scope:** Import customs, Manila staging warehouse, road surveys for difficult access roads, phased site-by-site delivery, proof-of-delivery at each tower compound. Some batteries are **Class 9 DG (lithium)**; panels and steel are oversized. Several sites are **4×4 access only**.

| Milestone | Date |
| --- | --- |
| Programme kickoff | 15 Jul 2026 |
| All sites delivered | 31 Oct 2026 |
| Delivery pattern | 4 waves (~3–4 sites every 3 weeks) |
| Wave 1 priority | **Urgent** (live revenue sites) |
| Remaining waves | **Normal** |

---

## 2. Special Project — header fields

**Project name:**  
`Globe Rural Connect — Northern Luzon Solar Micro-Grid Rollout (14 Sites)`

**Project type:** Infrastructure / Energy (or nearest **Project Type** master)

**Customer:** Solara Telecom Infrastructure Pte Ltd (or your test Customer)

**Description:**  
Supply-chain and last-mile delivery programme for 14 remote telecom tower solar upgrades. Scope includes customs clearance at Manila port, bonded staging, road-access verification for 6 difficult sites, DG-compliant transport, and site receipt sign-off at each tower compound.

**Special handling instructions:**

- Lithium battery racks: Class 9 DG, keep upright, max ambient 35°C during staging
- Solar panels: fragile, no stack > 2 pallets high
- Deliveries to tower compounds only **06:00–14:00** (security gate closes 15:00)
- Driver must present Solara site access pass + Globe contractor ID
- 6 sites require **4×4 truck** — do not send standard rigid truck

**Client notes:**  
“We will nominate one site supervisor per wave (contact list to follow). Please confirm 48 hours before each wave dispatch.”

**Planned start / end:** 15 Jul 2026 → 31 Oct 2026

---

## 3. Sales Quote — Shipper and Consignee

On the **Sales Quote**, **Shipper** and **Consignee** are links to the **Shipper** and **Consignee** masters (not free text). Create or select masters first, then pick them on the quote.

### Quick rule

| Party | Meaning | Who to use (this scenario) |
| --- | --- | --- |
| **Shipper** | Party physically handing cargo to the carrier (origin / exporter) | **Supplier in China** (e.g. SolarTech Manufacturing Co., Ltd., Shanghai) if equipment is ex-factory overseas |
| **Consignee** | Party receiving cargo at destination (importer / receiver of record) | **Customer’s Philippines entity** (Solara or their nominated importer) |

### Variations

| Movement | Shipper | Consignee |
| --- | --- | --- |
| **Import** (China → Philippines) | Overseas manufacturer / seller | Customer (Philippines importer of record) |
| **Domestic** (Manila warehouse → sites) | Customer warehouse or your staging hub | Customer (same entity; delivery address = site) |
| **Export** (Philippines → abroad) | Customer or Philippine supplier | Overseas buyer |

**Delivery address / site** is separate from Consignee — use **Location From / Location To**, routing legs, or operational job addresses for each tower site.

### Sales Quote routing (import leg)

| Field | Example value |
| --- | --- |
| **Direction** | Import |
| **Origin Port** | `CNSHA` (Shanghai) or supplier’s port |
| **Destination Port** | `PHMNL` (Manila) |
| **Customer** | Solara Telecom Infrastructure Pte Ltd |
| **Shipper** | Link to Shipper master (supplier) |
| **Consignee** | Link to Consignee master (customer PH entity) |

---

## 4. Shipper master — UNLOCO (Philippines)

On the **Shipper** master, set **Default UNLOCO** (and optionally **Default Seaport** / **Default Airport**) to the **city or port where pickup actually happens** — not “Philippines” as a country code.

| Shipper location | UNLOCO | Notes |
| --- | --- | --- |
| Metro Manila / Pasig staging | `PHMNL` | Manila — common for warehouse pickup |
| Port of Manila (sea) | `PHMNL` | Use **Default Seaport** |
| Cebu | `PHCEB` | |
| Davao | `PHDVO` | |
| Clark (air / logistics zone) | `PHCRK` | Use **Default Airport** if air-only |

**Rule:** Match UNLOCO to the **physical pickup point** (factory, warehouse, port, airport). If cargo is picked up from Pasig warehouse but cleared through Manila port, warehouse pickup → `PHMNL` or nearest valid code for that address; sea leg origin on the quote may still be `CNSHA` → `PHMNL`.

---

## 5. Scoping activities

Add on **Scoping Activities** tab before status moves to Booked:

| Activity | Scope | Requested date | Notes |
| --- | --- | --- | --- |
| Ocular Inspection | Wave 1 — all 4 sites | 20 Jun 2026 | Gate width & turning radius |
| Road Inspection | TWR-07, TWR-09, TWR-11, TWR-13 | 25 Jun 2026 | Unpaved access; 4×4 feasibility |
| Technical Consultation | Manila staging warehouse | 01 Jul 2026 | DG segregation + panel storage |

---

## 6. Fulfillment — packages (sample rows)

Use customer-linked **Address** records as **Site**. See [Special Project — Fulfillment](welcome/special-project-packages) for funnel and receipt behaviour.

### Wave 1 — Urgent (target delivery 25 Jul 2026)

| Site | Commodity / description | Qty required | Packs | L×W×H (cm) | Weight (kg) | DG? |
| --- | --- | --- | --- | --- | --- | --- |
| TWR-01 — Baguio | Standard Micro-Grid Kit | 1 | 8 | 240×120×180 | 4,200 | Yes |
| TWR-02 — La Trinidad | Standard Micro-Grid Kit | 1 | 8 | 240×120×180 | 4,200 | Yes |
| TWR-03 — Bontoc | Heavy Load Kit | 1 | 10 | 260×120×190 | 5,800 | Yes |
| TWR-04 — Tabuk | Standard Micro-Grid Kit | 1 | 8 | 240×120×180 | 4,200 | Yes |

### Wave 2 — Normal (target 15 Aug 2026)

| Site | Commodity | Qty | Notes |
| --- | --- | --- | --- |
| TWR-05 — Lagawe | Standard Kit | 1 | Paved access |
| TWR-06 — Banaue | Standard Kit | 1 | Narrow barangay road |
| TWR-07 — Mayoyao | Standard Kit | 1 | Road inspection required — 4×4 only |

### Always-on package (**Include on Create** = ticked)

| Description | Qty | Purpose |
| --- | --- | --- |
| Site Safety & PPE Crate | 14 | Auto-attaches to every booking; excluded from receipt balances |

---

## 7. Lifecycle jobs (operational legs)

Maria expects these legs under **Lifecycle**:

| # | Service type | Purpose |
| --- | --- | --- |
| 1 | Sea | 2×40ft HC, Shanghai → Manila |
| 2 | Customs | Import clearance (inverters, lithium batteries) |
| 3 | Warehousing | 3-week staging — Pasig Logistics Hub |
| 4 | Transport | Per-wave linehaul Manila → site |
| 5 | Special Project | Site supervisors / rigging (no shipment job link) |

Set **Project** on each operational document to the programme’s ERPNext **Project** (same name as the Special Project).

---

## 8. Charges rows — what to enter

Each charge row is **one billable service line**. Use **Special Project Charges** on the programme (or **Sales Quote Charge** on the quote before conversion).

### Key fields (Special Project Charges)

| Field | What to enter |
| --- | --- |
| **Service Type** | Air, Sea, Transport, Customs, Warehousing, or Special Project — match the lifecycle leg |
| **Lifecycle Job** | Row `idx` from Lifecycle Jobs when multiple lines share the same service type |
| **Item Code** | Service item from Item master (e.g. trucking, customs clearance) |
| **Charge Type** | `Margin` (sell + buy), `Revenue` (sell only), `Cost` (buy only), `Disbursement` (pass-through fees) |
| **Charge Category** | Freight, Customs Clearance, Storage, Documentation, Other, etc. |
| **Description** | Plain-language line label for invoices |
| **Estimated Revenue** | Amount to bill customer |
| **Estimated Cost** | Amount you expect to pay |
| **Quantity / UOM / Rate** | When using calculated methods |

### Charge type guide

| Charge Type | Use when |
| --- | --- |
| **Margin** | Normal service — you have both sell and buy |
| **Revenue** | Sell-only line (rare; cost elsewhere) |
| **Cost** | Buy-only line (rare; revenue elsewhere) |
| **Disbursement** | Pass-through: tolls, government fees, port charges (often revenue = cost + optional handling fee on a separate Margin line) |

### Minimum charge set for this scenario

| # | Service Type | Description | Charge Type | Charge Category | Est. revenue | Est. cost |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | Special Project | Ocular & road scoping (14 sites) | Margin | Other | 180,000 | 95,000 |
| 2 | Special Project | Programme management / coordination | Margin | Other | 120,000 | 45,000 |
| 3 | Sea | Ocean freight — 2×40ft HC SHA–MNL | Margin | Freight | 850,000 | 720,000 |
| 4 | Customs | Import clearance & permits | Margin | Customs Clearance | 95,000 | 65,000 |
| 5 | Warehousing | Staging 21 days — Pasig (DG + panels) | Margin | Storage | 210,000 | 155,000 |
| 6 | Transport | Delivery Wave 1 (4 sites) | Margin | Freight | 320,000 | 240,000 |
| 7 | Transport | Delivery Wave 2 (3 sites) | Margin | Freight | 240,000 | 185,000 |
| 8 | Transport | Delivery Wave 3 (4 sites) | Margin | Freight | 310,000 | 235,000 |
| 9 | Transport | Delivery Wave 4 (3 sites) | Margin | Freight | 280,000 | 210,000 |
| 10 | Transport | Permits, tolls, escort fees | Disbursement | Other | 45,000 | 45,000 |

*Amounts are illustrative PHP — adjust for your test company currency.*

After save, use **Action → Calculate Charges** if tariff/rate engines apply, then **Post → WIP and Accrual** when testing recognition.

---

## 9. Status journey (customer timeline)

| Stage | Customer action | Special Project status |
| --- | --- | --- |
| Day 0 | Sends BOM + site list | Draft |
| Week 1 | Pays for scoping | Scoping |
| Week 2 | Accepts quote SQ-2026-0847 | Booked — link **Sales Quote** |
| Week 3 | Signs programme plan | Planning → Approved |
| 15 Jul | Wave 1 dispatch | In Progress |
| Mid-programme | Landslide blocks TWR-07 | On Hold |
| 31 Oct | Last site signed off | Completed |

---

## 10. Test cases (edge scenarios)

| # | Scenario | What to verify |
| --- | --- | --- |
| 1 | TWR-03 qty 8 → 12 packs | Volume/weight recalc; packages summary updates |
| 2 | Partial delivery at TWR-06 (6 of 8 pallets) | **Deliveries** row posted; **Delivered** / **Remaining** on package |
| 3 | **Create → Booking / Order** for Wave 1 | Only TWR-01…04 selected; PPE crate auto-included |
| 4 | **On Hold** during TWR-07 blockage | Dashboard status; deliveries paused per process |
| 5 | **Create → Change Request** — add TWR-15 | New package row + charge revision |
| 6 | Milestone / interim / final invoicing | **Charges** linked to Sales Invoice |
| 7 | **Refresh Delivery Funnel** | Funnel columns match lifecycle stages |
| 8 | **Get Milestones** / document template | Milestones and document checklist populated |

### Sample customer follow-up email

> **From:** Maria Elena Santos  
> **Subject:** RE: Globe Rural Connect — Wave 2 dispatch confirmation  
>
> Approved for Wave 2 dispatch **12 Aug**, but **hold TWR-07** until your road inspection report is uploaded.
>
> Please confirm: DG paperwork on file; Pasig warehouse has 2 standard kits for TWR-05 and TWR-06; PPE crates on every truck.
>
> Send POD within 24 hours of each site delivery.

---

## 11. Documents checklist

- Commercial invoice & packing list (import)
- DG declaration / MSDS (lithium modules)
- Import permit
- Delivery receipt signed by Globe site engineer
- Photo proof of battery rack area cleared

Apply **Document List Template** on the programme; confirm overdue items appear on **Dashboard**.

---

## 12. Related topics

- [Special Projects Module](welcome/special-projects-module)
- [Special Project — Fulfillment (Packages & Deliveries)](welcome/special-project-packages)
- [Sales Quote](welcome/sales-quote)
- [Document Management](welcome/document-management)
- [Milestone Tracking](welcome/milestone-tracking)
