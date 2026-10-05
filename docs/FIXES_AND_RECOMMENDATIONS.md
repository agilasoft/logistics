# Fixes and recommendations

This note follows [APP_REVIEW.md](APP_REVIEW.md). It records what was changed in the tree, and what should wait.

Two edits landed with this note. They do not change how jobs, filings, or alerts behave. Everything else is a recommendation for a later change.

## Applied

### Broken Special Project JSON symlinks

`special_project_job.json` and `special_project_order_job.json` were symlinks to `project_task_job` and `project_task_order_job`. Those folders are gone. The rename is `logistics/patches/v1_0_rename_project_task_doctypes_to_project.py` (Project Task Job to Project Job, Project Task Order to Project Order). Opening either JSON path failed.

The dangling links are removed. `logistics/special_projects/doctype/special_project_job/special_project_job.py` still subclasses `ProjectJob`, so an old import path loads. The live DocTypes are Project Job and Project Order.

### Placeholder personal-data hook

`user_data_fields` in `logistics/hooks.py` listed `{doctype_1}`, `{filter_by}`, and `{field_1}`. Frappe would look those names up literally. The list is now empty.

A later privacy pass should name real DocTypes and fields: customer contacts, driver phone, and portal users. Do not put the placeholder tokens back, and do not guess field names before that pass.

## Deferred

### Transport Job status SQL

`logistics/transport/doctype/transport_job/transport_job.py` updates ``tabTransport Job`.`status`` with `frappe.db.sql` and calls `frappe.db.commit()` inside `before_save` and `after_submit` when a submitted job is still Draft. That commits partial work while other hooks are still running.

Next change: set `status` on the document in `before_submit`, and add a test that submit leaves `status = Submitted` without a commit in the middle of the request. Do not remove the SQL until that test exists. The current writes are a workaround for status being reset during submit.

### Sea delay and penalty tasks

`logistics/sea_freight/tasks.py` defines `check_sea_shipment_delays`, `check_sea_shipment_penalties`, `check_impending_penalties`, and `check_container_penalties`. `scheduler_events` in `logistics/hooks.py` does not call them.

Do not register them until product confirms the alerts. Each run loads up to 100 Sea Shipments, calls `save`, and can send alerts. Delay checks honor Sea Freight Settings `enable_delay_alerts`. Penalty checks honor `enable_penalty_alerts`. Both default to on when the settings row exists.

When a run updates any shipment it records success with `frappe.log_error` (titles such as `Sea Shipment Delay Check Completed`). That writes an Error Log row for a normal finish. A later change should log that on the standard logger.

If the tasks are scheduled, the hourly entries would be:

- `logistics.sea_freight.tasks.check_sea_shipment_delays`
- `logistics.sea_freight.tasks.check_sea_shipment_penalties`
- `logistics.sea_freight.tasks.check_impending_penalties`
- `logistics.sea_freight.tasks.check_container_penalties`

The Sea Shipment DocType description still asks for these alerts as developer notes. Remove that text when the tasks are actually scheduled.

### Customs filing stubs

`logistics/customs/api/us_ams_api.py` `submit` builds a mock success response and writes that status, transaction number, and submission time onto the US AMS document. The same pattern is in `us_isf_api.py`, `ca_emanifest_api.py`, and `jp_afr_api.py`.

A later change should refuse to file unless Manifest Settings points at a real endpoint. It should not mark the document submitted from `get_mock_response`. Filing DocTypes and the compliance reports can stay.

### Lalamove desk button

`logistics/lalamove/` has the client, mapper, and `LalamoveService`. ODDS Settings stores Lalamove credentials. `logistics/sea_freight/doctype/sea_shipment/sea_shipment_lalamove.js` adds an Action button when `use_lalamove` and `last_mile_delivery_required` are set.

`hooks.py` does not list that script in `doctype_js` or `app_include_js`. Frappe loads `sea_shipment.js` for the form, not `sea_shipment_lalamove.js`, so the button does not appear.

Next change, if last-mile Lalamove is a supported feature: add the script to the Sea Shipment `doctype_js` entry and confirm `/assets/logistics/lalamove/utils.js` and `lalamove_form.js` are built. If it is not a supported feature, leave the script unloaded and say so in ODDS Settings.

### Debug and one-off portal files

Leave these until a pass confirms nothing calls them with `bench execute`:

- `logistics/www/transport_debug.html`, `warehousing_debug.html`, `test_portal.html`, `simple_test.html`, `transport_portal_old.html`
- `logistics/api_backup.py`
- `logistics/transport/api_telematics_debug.py`
- `logistics/transport/add_portal_items.py`, `add_portal_items_to_settings.py`, `add_to_portal_settings.py`, `create_portal_items.py`, `check_and_create_pages.py`, `check_portal_structure.py`

After that confirmation, delete the duplicate portal package under `logistics/transport/www/`. The pages that serve customers stay under `logistics/www/`.

### Empty and deprecated DocTypes

Do not drop ODDS Order, Proof of Delivery, or Plate Coding Rule in a file delete. They are installed DocTypes. Removal needs a patch that migrates or deletes site data first.

`ODDSOrder` and `ProofofDelivery` are empty controllers (`pass`). Plate Coding Rule’s description already says it is deprecated and to use Truck Ban Constraint.

### Exhibits and MICE

`logistics/modules.txt` registers MICE and does not register Exhibits. `logistics/exhibits/` still contains Exhibit, Docket, and lifecycle code. Control Tower job sources still mention exhibits.

Pick one programme module before deleting or re-registering the other. Registering Exhibits and deleting MICE, or the reverse, are both product decisions.

### Large controllers

Split later, one extract at a time:

- Warehouse Job ledger posting: `on_submit` in `logistics/warehousing/doctype/warehouse_job/warehouse_job.py` (about 5,370 lines).
- Sales Quote validation in `logistics/pricing_center/doctype/sales_quote/sales_quote.py` (about 5,160 lines).
- A shared air and sea `convert_to_shipment` helper. `air_booking.py` and `sea_booking.py` are each about 3,200 lines and follow the same structure.

Do not rewrite these files as one change.

### hooks.py event list and global JavaScript

`logistics/hooks.py` appends credit, special-project financials, freight-shipment receipts, and transport-job receipts onto `doc_events` with import-time loops. The final handler list for a DocType is not the dictionary at the top of the file.

A later cleanup should declare that final list in one place. Leave the merges as they are until that edit has a test that the same handlers still run.

`app_include_js` loads charge dialogs, invoice dialogs, profitability, and the time-sensitive timer on every desk page. Many of those files are also listed under `doctype_js`. Move the DocType-specific scripts onto `doctype_js`. Keep the early dialog globals that the comment in `hooks.py` says must load before the form bundle.

### Tests to add first

These packages have no `test_*.py` coverage for the behavior above. Add tests before changing it:

- Warehouse Job submit and the stock-ledger sign for Putaway, Pick, Move, and Stocktake.
- Intercompany Sales Invoice and Purchase Invoice creation in `logistics/intercompany/intercompany_invoice.py`.
- Sea delay and penalty tasks, including the settings gates, before any scheduler registration.

## Out of scope for the applied edits

No scheduler registration, no carrier or customs calls, no DocType deletion, and no controller rewrites.
