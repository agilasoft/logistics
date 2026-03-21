# CargoNext Wiki User Guide Content

This folder contains markdown source files for the CargoNext user guide wiki. The content follows **ERPNext documentation style** with:

## GitHub Wiki (Automatic Sync)

When you push changes to `develop` or `main`, a GitHub Action automatically syncs this content to the [GitHub Wiki](https://github.com/agilasoft/logistics/wiki).

**Trigger:** Push to `logistics/wiki_content/**`, `scripts/sync_wiki_to_github.py`, or `.github/workflows/sync-wiki.yml`

**Manual run:** Go to Actions → "Sync Wiki to GitHub" → Run workflow

**First-time setup:** Create at least one wiki page manually on GitHub to initialize the wiki repo, then the workflow can push updates.

- **H1**: DocType/Feature name
- **Bold one-line definition** followed by introductory paragraphs
- **Navigation**: Home > Module > Page
- **Prerequisites** (with links)
- **How to Create** (numbered steps)
- **Features** (subsections)
- **Related Topics** (links)

## Installing Wiki Pages

To create or update wiki pages on your CargoNext site (e.g., cargonext.io):

```bash
# From your bench directory
bench --site your-site-name execute logistics.setup.install_wiki_pages.install_wiki_pages
```

With optional parameters:

```bash
# Use a different wiki space route (default is "welcome")
bench --site your-site-name execute logistics.setup.install_wiki_pages.install_wiki_pages --kwargs '{"wiki_space_route": "welcome"}'

# Skip updating existing pages (only create new ones)
bench --site your-site-name execute logistics.setup.install_wiki_pages.install_wiki_pages --kwargs '{"update_existing": false}'
```

**Prerequisites:** The [Wiki app](https://github.com/frappe/wiki) must be installed on the site, and a Wiki Space with route `welcome` (or your specified route) must exist.

## Managing the Wiki

- **View wiki:** https://cargonext.io/welcome (or your site URL + wiki space route)
- **Admin interface:** https://cargonext.io/desk/wiki
- **Wiki Settings:** Set default wiki space, sidebar, navbar, search, feedback

## Pages Included

| File | Title | Sidebar Group |
|------|-------|---------------|
| getting_started.md | Getting Started | Introduction |
| recent_platform_updates.md | Recent Platform Updates | Introduction |
| cargonext_v1_astraea_press_release.md | CargoNext v1 — Astraea Press Release | Introduction |
| document_management.md | Document Management | Introduction |
| milestone_tracking.md | Milestone Tracking | Introduction |
| document_list_template.md | Document List Template | Introduction |
| logistics_document_type.md | Logistics Document Type | Introduction |
| customer_portal.md | Customer Portal | Introduction |
| logistics_settings.md | Logistics Settings | Setup |
| default_details_and_relationships.md | Default Details and Relationships | Setup |
| sea_freight_settings.md | Sea Freight Settings | Setup |
| air_freight_settings.md | Air Freight Settings | Setup |
| transport_settings.md | Transport Settings | Setup |
| warehouse_settings.md | Warehouse Settings | Setup |
| customs_settings.md | Customs Settings | Setup |
| sea_freight_module.md | Sea Freight Module | Sea Freight |
| air_freight_module.md | Air Freight Module | Air Freight |
| transport_module.md | Transport Module | Transport |
| customs_module.md | Customs Module | Customs |
| warehousing_module.md | Warehousing Module | Warehousing |
| sea_booking.md | Sea Booking | Sea Freight |
| sea_shipment.md | Sea Shipment | Sea Freight |
| sea_consolidation.md | Sea Consolidation | Sea Freight |
| air_booking.md | Air Booking | Air Freight |
| air_shipment.md | Air Shipment | Air Freight |
| air_consolidation.md | Air Consolidation | Air Freight |
| master_bill.md | Master Bill | Sea Freight |
| master_air_waybill.md | Master Air Waybill | Air Freight |
| shipper.md | Shipper | Sea Freight |
| consignee.md | Consignee | Sea Freight |
| container_type.md | Container Type | Sea Freight |
| uld_type.md | ULD Type | Air Freight |
| transport_order.md | Transport Order | Transport |
| transport_job.md | Transport Job | Transport |
| transport_consolidation.md | Transport Consolidation | Transport |
| transport_leg.md | Transport Leg | Transport |
| transport_plan.md | Transport Plan | Transport |
| transport_order_intermodule_field_copy.md | Transport Order — Inter-module Field Copy | Transport |
| run_sheet.md | Run Sheet | Transport |
| proof_of_delivery.md | Proof of Delivery | Transport |
| transport_template.md | Transport Template | Transport |
| load_type.md | Load Type | Transport |
| declaration_order.md | Declaration Order | Customs |
| declaration.md | Declaration | Customs |
| customs_workflow_guide.md | Customs Workflow Guide | Customs |
| commodity.md | Commodity | Customs |
| customs_authority.md | Customs Authority | Customs |
| inbound_order.md | Inbound Order | Warehousing |
| release_order.md | Release Order | Warehousing |
| transfer_order.md | Transfer Order | Warehousing |
| vas_order.md | VAS Order | Warehousing |
| stocktake_order.md | Stocktake Order | Warehousing |
| warehouse_job.md | Warehouse Job | Warehousing |
| warehouse_contract.md | Warehouse Contract | Warehousing |
| gate_pass.md | Gate Pass | Warehousing |
| periodic_billing.md | Periodic Billing | Warehousing |
| storage_location.md | Storage Location | Warehousing |
| handling_unit_type.md | Handling Unit Type | Warehousing |
| sales_quote.md | Sales Quote | Pricing Center |
| sales_quote_separate_billings_and_internal_job.md | Sales Quote — Separate Billings and Internal Job | Pricing Center |
| change_request.md | Change Request | Pricing Center |
| sales_quote_calculation_method.md | Sales Quote – Calculation Method | Pricing Center |
| charges_tariff_revenue_cost_pattern.md | Charges, Tariff, Revenue & Cost Pattern | Pricing Center |
| general_job.md | General Job | Logistics |
| logistics_milestone.md | Logistics Milestone | Logistics |
| job_management_module.md | Job Management Module | Job Management |
| revenue_recognition_policy_accounts_and_dates.md | Revenue Recognition Policy — Accounts, Dates, and Charges | Job Management |
| proforma_gl_entries.md | Proforma GL Entries (Job Costing) | Job Management |
| wip_accrual_reversal_on_invoicing_design.md | WIP and Accrual Reversal on Invoicing | Job Management |
| sustainability_module.md | Sustainability Module | Sustainability |
| intercompany_module.md | Intercompany Module | Intercompany |
| internal_and_intercompany_billing.md | Internal and Intercompany Billing | Intercompany |
| special_projects_module.md | Special Projects Module | Special Projects |
| pages_overview.md | Pages Overview | Pages |
| reports_overview.md | Reports Overview | Reports |
| glossary.md | Glossary | Glossary |

## Adding New Pages

1. Create a new `.md` file in this folder following the ERPNext style.
2. Add the file to `WIKI_PAGES_CONFIG` in `logistics/setup/install_wiki_pages.py` (for cargonext.io).
3. Add the file to `PAGE_MAP` in `scripts/sync_wiki_to_github.py` (for GitHub Wiki).
4. Update `_sidebar.md` in the sync script if needed.
5. Push to trigger GitHub Wiki sync, or run the cargonext.io install script.
