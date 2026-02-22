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
| document_management.md | Document Management | Introduction |
| milestone_tracking.md | Milestone Tracking | Introduction |
| document_list_template.md | Document List Template | Introduction |
| logistics_document_type.md | Logistics Document Type | Introduction |
| customer_portal.md | Customer Portal | Introduction |
| logistics_settings.md | Logistics Settings | Setup |
| sea_freight_settings.md | Sea Freight Settings | Setup |
| air_freight_settings.md | Air Freight Settings | Setup |
| transport_settings.md | Transport Settings | Setup |
| warehouse_settings.md | Warehouse Settings | Setup |
| customs_settings.md | Customs Settings | Setup |
| sea_booking.md | Sea Booking | Sea Freight |
| sea_shipment.md | Sea Shipment | Sea Freight |
| air_booking.md | Air Booking | Air Freight |
| air_shipment.md | Air Shipment | Air Freight |
| transport_order.md | Transport Order | Transport |
| transport_job.md | Transport Job | Transport |
| declaration_order.md | Declaration Order | Customs |
| declaration.md | Declaration | Customs |
| inbound_order.md | Inbound Order | Warehousing |
| release_order.md | Release Order | Warehousing |
| transfer_order.md | Transfer Order | Warehousing |
| warehouse_job.md | Warehouse Job | Warehousing |
| sales_quote.md | Sales Quote | Pricing Center |
| one_off_quote.md | One Off Quote | Pricing Center |
| container_type.md | Container Type | Sea Freight |
| uld_type.md | ULD Type | Air Freight |
| load_type.md | Load Type | Transport |
| transport_template.md | Transport Template | Transport |
| storage_location.md | Storage Location | Warehousing |
| handling_unit_type.md | Handling Unit Type | Warehousing |
| logistics_milestone.md | Logistics Milestone | Logistics |
| special_projects_module.md | Special Projects Module | Special Projects |
| reports_overview.md | Reports Overview | Reports |

## Adding New Pages

1. Create a new `.md` file in this folder following the ERPNext style.
2. Add the file to `WIKI_PAGES_CONFIG` in `logistics/setup/install_wiki_pages.py` (for cargonext.io).
3. Add the file to `PAGE_MAP` in `scripts/sync_wiki_to_github.py` (for GitHub Wiki).
4. Update `_sidebar.md` in the sync script if needed.
5. Push to trigger GitHub Wiki sync, or run the cargonext.io install script.
