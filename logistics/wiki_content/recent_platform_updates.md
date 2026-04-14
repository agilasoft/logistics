# Recent Platform Updates

**This page summarizes major behaviour and documentation changes** in the Logistics (CargoNext) app on the current development line. Use it with the linked deep-dive articles for billing, recognition, and pricing.

**Navigation:** Home > Introduction > Recent Platform Updates

## 1. Sales Quote → bookings and orders (charge lines)

When you create **Sea Booking**, **Air Booking**, or **Transport Order** from a [Sales Quote](welcome/sales-quote), charge rows now carry through more completely from **Sales Quote Charge**:

- Correct item identity on booking/order charge tables (**Item Code** / **Item Name** mapping).
- **Charge category**, **description**, **Item Tax Template**, and **Invoice Type** (from the Item where applicable).
- **Bill To** and **Pay To** on Sea Booking and Transport Order charges where the child table supports them.

Air Booking charge category resolution prefers the quote line, then the Item, then a default. See also [Sales Quote – Separate Billings and Internal Job](welcome/sales-quote-separate-billings-and-internal-job).

## 2. Internal and intercompany billing

**Unified rules** apply: the **Main Job** holds customer-facing charges; **Internal Jobs** hold service-specific charges with revenue tied to the main job’s cost allocation. The only difference is the document: **Journal Entry** (same company) vs **Sales Invoice / Purchase Invoice** (intercompany).

- User guide: [Internal and Intercompany Billing](welcome/internal-and-intercompany-billing)
- Code layer: `cross_module_billing.py` (invoice line extraction, anchor + contributor jobs).

## 3. Revenue recognition and GL

- **Recognition Policy Settings** is **one document per company**. Parameters include dimensions and a single **Recognition Date Basis** for both WIP and accrual posting dates.  
  Details: [Revenue Recognition Policy — Accounts, Dates, and Charges](welcome/revenue-recognition-policy-accounts-and-dates)
- **Profitability (from GL)** and expected postings: [Proforma GL Entries](welcome/proforma-gl-entries)
- **WIP / accrual reversal** when real invoices and internal billing post: design and hook behaviour in [WIP and Accrual Reversal on Invoicing](welcome/wip-accrual-reversal-on-invoicing-design)
- **Job Management** overview: [Job Management Module](welcome/job-management-module)

Migrations may reset recognition custom fields on Air Shipment (see patches `v1_0_cleanup_air_shipment_recognition_custom_fields`, `v1_0_recognition_date_basis_migration`).

## 4. Sea and air freight (bookings and shipments)

- **Volume and weight totals** can be consolidated at **shipment** level (patches align booking/shipment fields and totals). Packages still hold line detail; parent documents expose rolled-up totals where configured.
- **Charges** on shipments continue to use **estimated** amounts (from the booking) for WIP/accrual and **actual** amounts when recalculated for invoicing.

## 5. Transport

- The flag previously framed as “hazardous” is now **Contains Dangerous Goods** on Transport Order, Transport Job, legs, and packages (patch `v1_0_rename_transport_hazardous_to_contains_dangerous_goods`). Dependent fields (e.g. dangerous goods details) show when this is set.
- **Inter-module field copy**: when a Transport Order is created from other logistics documents, key shipment/booking fields are copied for consistency.  
  Reference: [Transport Order — Inter-module Field Copy](welcome/transport-order-intermodule-field-copy)

## 6. Customs (declaration order and declaration)

- **Permit requirements** and **exemptions** are modelled on Declaration Order and flow through to Declaration with aligned child tables and validation.
- **Status** and product-code related migrations are handled via patches (declaration status, product code / item code alignment). See [Declaration Order](welcome/declaration-order) and [Declaration](welcome/declaration).

## 7. Pricing center and jobs

- [Sales Quote](welcome/sales-quote): separate billings per service type, main vs internal job routing, unified charge calculation across modules.
- **General Job** and workspace updates align with costing and recognition where applicable.

## 8. Integrations and utilities

- **Invoice integration** hooks tie Sales Invoice / Purchase Invoice / internal billing to job lifecycle, GL dimensions, and recognition reversal helpers under `logistics/invoice_integration/`.
- **Lalamove** mapping and **customer portal** transport views may be updated alongside Transport Job behaviour; check release notes in your deployment branch for API-specific changes.

## 9. Patches and upgrades

Database patches in `logistics/patches.txt` cover charge break buttons, sales quote service migration, recognition cleanup, transport field rename, declaration migrations, and more. After `bench migrate`, validate:

- Recognition policy per company
- One-off converted quotes and charge lines on existing bookings/orders
- Transport documents for **Contains Dangerous Goods**


<!-- wiki-field-reference:start -->

## Complete field reference

_Features listed here touch many DocTypes. Open the relevant guide; each includes a **Complete field reference** where the document is a logistics DocType (e.g. [Sales Quote](welcome/sales-quote), [Air Booking](welcome/air-booking), [Transport Order](welcome/transport-order))._

<!-- wiki-field-reference:end -->

## 10. Related articles

| Topic | Article |
|--------|---------|
| Separate billings / internal job | [Sales Quote – Separate Billings and Internal Job](welcome/sales-quote-separate-billings-and-internal-job) |
| Internal vs intercompany billing | [Internal and Intercompany Billing](welcome/internal-and-intercompany-billing) |
| Recognition accounts and dates | [Revenue Recognition Policy — Accounts, Dates, and Charges](welcome/revenue-recognition-policy-accounts-and-dates) |
| GL / profitability | [Proforma GL Entries](welcome/proforma-gl-entries) |
| Reversal on invoice | [WIP and Accrual Reversal on Invoicing](welcome/wip-accrual-reversal-on-invoicing-design) |
| Transport field copy | [Transport Order — Inter-module Field Copy](welcome/transport-order-intermodule-field-copy) |
| Product news | [CargoNext v1 — Astraea Press Release](welcome/cargonext-v1-astraea-press-release) |
