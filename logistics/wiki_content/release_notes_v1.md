# CargoNext v1 — Astraea: Release Notes

**Codename:** Astraea  
**Product:** CargoNext (logistics app for Frappe / ERPNext)  
**Partners:** Agilasoft Cloud Technologies Inc. · BlueCore Solutions Corp.

This document summarizes **CargoNext version 1** as the first generally available release line: integrated logistics operations on **Frappe Framework** and **ERPNext**, with finance-aware job costing, pricing, and billing across modules.

**Navigation:** Home > Introduction > CargoNext v1 — Release Notes

For ongoing behaviour changes after upgrade, see also [Recent Platform Updates](welcome/recent-platform-updates). Announcement context: [CargoNext v1 — Astraea Press Release](welcome/cargonext-v1-astraea-press-release).

---

## 1. Platform requirements

| Component | Version |
|-----------|---------|
| Frappe Framework | v16+ |
| ERPNext | v16+ |
| Python | 3.14+ |

Install and migrate with `bench install-app logistics` and `bench migrate` on your site. See [Getting Started](welcome/getting-started) for setup order.

---

## 2. What’s in v1 (scope)

CargoNext v1 delivers an **end-to-end logistics layer** on ERPNext masters, including:

- **Sea freight** — bookings, shipments, consolidations, master bills, containers  
- **Air freight** — bookings, shipments, consolidations, master air waybills, ULD  
- **Transport** — orders, jobs, consolidations, legs, plans, run sheets, proof of delivery  
- **Customs** — declaration orders, declarations, commodities, authorities, permits and exemptions  
- **Warehousing** — inbound, release, transfer, VAS, stocktake, warehouse jobs, contracts, gate pass, periodic billing, locations  
- **Pricing Center** — sales quotes, change requests, charge calculation aligned across modules  
- **Job Management** — costing, revenue recognition policies, WIP/accrual behaviour, profitability views  
- **Intercompany** — internal and intercompany billing rules shared with execution documents  
- **Sustainability** — environmental metrics attached to operations  
- **Special Projects** — multi-mode project scaffolding where enabled  
- **Credit management** — holds by DocType or apply-all, integration with ERPNext credit limits, **Credit Hold Lift Request** workflow  
- **Customer & warehouse portals** — transport and warehouse job views (configure permissions and Logistics Settings)  
- **Integrations** — third-party transport (e.g. Lalamove, Transportify); API behaviour may vary by deployment branch  

---

## 3. Highlights and behaviour (v1 release line)

### 3.1 Sales Quote → operational documents

Creating **Sea Booking**, **Air Booking**, or **Transport Order** from a [Sales Quote](welcome/sales-quote) carries **Sales Quote Charge** data through more completely:

- Item identity (**Item Code** / **Item Name**), **charge category**, description, **Item Tax Template**, **Invoice Type** where applicable  
- **Bill To** and **Pay To** on Sea Booking and Transport Order charges where supported  
- Air Booking resolves charge category from the quote line, then Item, then default  

See [Sales Quote — Separate Billings and Internal Job](welcome/sales-quote-separate-billings-and-internal-job) for main vs internal job routing.

### 3.2 Internal and intercompany billing

Unified rules: the **Main Job** holds customer-facing charges; **Internal Jobs** hold service-specific charges with revenue tied to the main job’s cost allocation. Same-company flows use **Journal Entry**; intercompany flows use **Sales Invoice** / **Purchase Invoice**. Guide: [Internal and Intercompany Billing](welcome/internal-and-intercompany-billing).

### 3.3 Revenue recognition and GL

- **Recognition Policy Settings** — one document per company; dimensions and a single **Recognition Date Basis** for WIP and accrual posting dates ([Revenue Recognition Policy — Accounts, Dates, and Charges](welcome/revenue-recognition-policy-accounts-and-dates))  
- **Proforma GL** and profitability: [Proforma GL Entries](welcome/proforma-gl-entries)  
- **WIP / accrual reversal** when real invoices and internal billing post: [WIP and Accrual Reversal on Invoicing](welcome/wip-accrual-reversal-on-invoicing-design)  

Migrations may reset recognition-related custom fields on Air Shipment (see patches such as `v1_0_cleanup_air_shipment_recognition_custom_fields`, `v1_0_recognition_date_basis_migration`).

### 3.4 Sea and air freight

- **Volume and weight** can roll up at **shipment** level; packages retain line detail where configured  
- Shipment **charges** use **estimated** amounts (from booking) for WIP/accrual and **actual** amounts when recalculated for invoicing  

### 3.5 Transport

- Hazardous cargo is flagged as **Contains Dangerous Goods** on Transport Order, Transport Job, legs, and packages (migration from legacy “hazardous” labelling)  
- **Inter-module field copy** when creating Transport Orders from other logistics documents: [Transport Order — Inter-module Field Copy](welcome/transport-order-intermodule-field-copy)  

### 3.6 Customs

- **Permit requirements** and **exemptions** modelled on Declaration Order and flowing into Declaration with aligned child tables and validation  
- Status and product-code migrations delivered via patches; see [Declaration Order](welcome/declaration-order) and [Declaration](welcome/declaration)  

### 3.7 Pricing center and jobs

- Sales Quote supports **separate billings** per service type and **main vs internal job** routing with unified charge calculation  
- **General Job** and workspace behaviour align with costing and recognition where applicable  

### 3.8 Integrations

- Invoice integration connects Sales Invoice / Purchase Invoice / internal billing to job lifecycle, GL dimensions, and recognition helpers  
- **Lalamove** mapping and **customer portal** transport views may change alongside Transport Job behaviour—confirm API-specific notes on your deployment branch  

### 3.9 Credit control

Cross-module enforcement via **Logistics Settings → Credit Control**: warnings, holds on create/submit/print, optional **Apply hold to all DocTypes**, per-row **Subject DocTypes**, and **Credit Hold Lift Request** approved by **Credit Manager**. Details: [Credit Management](welcome/credit-management).

---

## 4. Upgrading to v1

1. **Backup** your site and database.  
2. **Upgrade** Frappe / ERPNext to supported versions (see §1).  
3. Run **`bench migrate`** for the logistics app.  
4. **Validate** after migrate:  
   - Recognition policy **per company**  
   - Sample quotes → bookings/orders (charge lines and tax templates)  
   - Transport documents for **Contains Dangerous Goods**  
   - Customs declarations after permit/exemption migrations  

Patches are listed in `logistics/patches.txt` (charge breaks, quote migration, recognition cleanup, transport field rename, customs migrations, and others).

---

## 5. Documentation and resources

| Resource | Link |
|----------|------|
| User guide (wiki) | [Getting Started](welcome/getting-started) |
| Release-line deltas | [Recent Platform Updates](welcome/recent-platform-updates) |
| Repository | [github.com/agilasoft/logistics](https://github.com/agilasoft/logistics) |
| Docs site | [docs.cargonext.com](https://docs.cargonext.com) |

**Support:** info@agilasoft.com · [www.agilasoft.com](https://www.agilasoft.com)

---

<!-- wiki-field-reference:start -->

## Complete field reference

_Release notes are a summary document. For form-level fields, open the wiki page for each DocType (e.g. [Sales Quote](welcome/sales-quote), [Sea Booking](welcome/sea-booking), [Transport Order](welcome/transport-order))._

<!-- wiki-field-reference:end -->
