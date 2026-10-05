# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from logistics.doc_event_hooks import DOC_EVENTS
from logistics.utils.credit_management import _ensure_print_validation_patch
from frappe import append_hook

from logistics.sea_freight.alert_schedule import DAILY_SEA_ALERT_TASKS, HOURLY_SEA_ALERT_TASKS
from logistics.utils.credit_management import merge_credit_hooks
from logistics.utils.invoice_dispute import merge_invoice_dispute_hooks

# App dependencies
app_dependencies = ["erpnext"]

# App configuration
app_name = "logistics"
app_title = "CargoNext"
app_publisher = "Agilasoft Cloud Technologies Inc."
app_description = "CargoNext"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "info@agilasoft.com"
app_license = "AGPL-3.0-or-later"

# bench migrate imports every fixtures/*.json, not only this list.
# Do not add Custom DocPerm here or as fixtures/custom_docperm.json:
# that import overwrites Role Permission Manager changes on every migrate.
fixtures = [
	"role.json",
	"custom_html_block.json",
	{"dt": "Workspace", "filters": [["module", "=", "Control Tower"]]},
	{"dt": "Dashboard", "filters": [["module", "=", "Control Tower"]]},
	{"dt": "Dashboard Chart", "filters": [["module", "=", "Control Tower"]]},
	{"dt": "Number Card", "filters": [["module", "=", "Control Tower"]]},
	{"dt": "Custom Field", "filters": [["module", "=", "Control Tower"]]},
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_css = [
	"/assets/logistics/css/print_footer_fix.css",
	"/assets/logistics/css/get_charges_from_quotation.css?v=9",
	"/assets/logistics/css/gcfq_settings_dashboard.css?v=2",
	"/assets/logistics/css/charges_grid_no_row_check.css?v=2",
	"/assets/logistics/css/density_factor.css?v=1",
	"/assets/logistics/css/workflow_center.css?v=1",
	"/assets/logistics/css/change_request_summary.css?v=4",
	"/assets/logistics/css/linked_services_dialog.css?v=9",
	"/assets/logistics/css/ts_sq_fetch_dialog.css?v=6",
	"/assets/logistics/css/role_permission_matrix.css?v=6",
]
app_include_js = [
	"/assets/logistics/js/company_dimension_filters.js?v=1",
	"/assets/logistics/js/address_link_query.js?v=1",
	"/assets/logistics/js/party_address_contact.js?v=1",
	"/assets/logistics/js/linked_service_link_query.js?v=2",
	"/assets/logistics/js/virtual_linked_services_grid.js?v=2",
	"/assets/logistics/js/linked_services_dialog.js?v=6",
	"/assets/logistics/js/ts_sq_fetch_dialog.js?v=6",
	"/assets/logistics/js/freight_agent_service.js?v=4",
	"/assets/logistics/js/charge_bill_to.js?v=4",
	"/assets/logistics/js/desk_main_sidebar_visibility_fix.js?v=2",
	"/assets/logistics/js/mice_project_manifest_print_preview.js?v=2",
	"/assets/logistics/js/form_desk_title_route_guard.js?v=4",
	"/assets/logistics/js/user_quick_entry.js?v=1",
	"/assets/logistics/js/grid_cannot_add_rows_toolbar_fix.js",
	# Desk-wide: form refresh can run before doctype_js bundles finish; define dialog globals early.
	"/assets/logistics/js/menu_permission.js?v=10",
	"/assets/logistics/js/linked_posting_actions.js?v=2",
	"/assets/logistics/js/submitted_child_doc_toolbar.js?v=1",
	"/assets/logistics/js/internal_job_create_from_source.js?v=22",
	"/assets/logistics/js/one_off_sales_quote_order_standard.js?v=2",
	"/assets/logistics/js/main_service_internal_job_mutual_exclusive.js?v=7",
	"/assets/logistics/js/service_role.js?v=3",
	"/assets/logistics/js/internal_job_detail_grid_delete_fix.js",
	"/assets/logistics/js/get_charges_from_quotation.js?v=21",
	"/assets/logistics/js/gcfq_settings_dashboard.js?v=1",
	"/assets/logistics/js/get_charges_from_tariff.js?v=1",
	"/assets/logistics/js/sea_consolidation_matching_shipments.js?v=3",
	"/assets/logistics/js/air_consolidation_matching_shipments.js?v=5",
	"/assets/logistics/js/charges_disbursement_sync.js",
	"/assets/logistics/js/charge_type_cleanup.js",
	"/assets/logistics/js/charge_break_dialogs.js?v=10",
	"/assets/logistics/js/specified_charges_html.js?v=3",
	"/assets/logistics/js/volume_from_dimensions.js",
	"/assets/logistics/js/density_factor.js?v=2",
	"/assets/logistics/js/document_alerts_dialog.js?v=2",
	"/assets/logistics/js/documents_tab_utils.js",
	"/assets/logistics/js/logistics_lifecycle_stepper.js",
	"/assets/logistics/js/opportunity_dashboard_boot.js?v=3",
	"/assets/logistics/js/crm_sales_quote_actions.js?v=2",
	"/assets/logistics/js/profitability_form.js?v=5",
	"/assets/logistics/js/purchase_invoice_dialog.js",
	"/assets/logistics/js/invoice_billing_currency.js",
	"/assets/logistics/js/sales_invoice_dialog.js",
	"/assets/logistics/js/sales_invoice_job_dimension_cleanup.js",
	"/assets/logistics/js/job_change_lock.js?v=4",
	"/assets/logistics/js/change_request_visibility.js?v=2",
	"/assets/logistics/js/change_request_summary.js?v=5",
	"/assets/logistics/js/time_sensitive_timer.js?v=2",
	"/assets/logistics/js/time_sensitive_form.js?v=3",
	"/assets/logistics/js/time_sensitive_list.js?v=2",
]

# include js, css files in header of web template
# web_include_css = "/assets/logistics/css/logistics.css"
# web_include_js = "/assets/logistics/js/logistics.js"

# include js in page
page_js = {
	"workflow-center": "public/js/workflow_center.js",
	"air-freight-control-tower": "public/js/air_freight_control_tower_page.js",
	"sea-freight-control-tower": "public/js/sea_freight_control_tower_page.js",
	"role-permission-matrix": "public/js/role_permission_matrix_page.js",
}

# include js in doctype views
doctype_js = {
	"Address": "public/js/address_eza.js",
	"Time Sensitive Case": [
		"public/js/time_sensitive_timer.js",
		"public/js/time_sensitive_services_dialog.js",
		"public/js/time_sensitive_create_service_dialog.js",
		"public/js/ts_sq_fetch_dialog.js",
		"public/js/operational_exchange_rate_grid.js",
		"public/js/charge_break_dialogs.js",
		"time_sensitive/doctype/time_sensitive_case_charge/time_sensitive_case_charge.js",
		"public/js/charge_break_buttons.js",
		"time_sensitive/doctype/time_sensitive_case/time_sensitive_case.js",
	],
	"Internal Job Detail": "logistics/doctype/internal_job_detail/internal_job_detail.js",
	"Linked Service Detail": "logistics/doctype/linked_service_detail/linked_service_detail.js",
	"Container": "logistics/doctype/container/container.js",
	"UNLOCO": [
		"logistics/doctype/unloco/unloco.js",
		"logistics/doctype/unloco/unloco_list.js",
	],
	# Sales Quote: dialogs first, break row/grid handlers, then air/sea freight scripts.
	# Paths are module-relative (no leading "logistics/") — see NOTE below for Special Project.
	# sales_quote.js is omitted: it loads via the DocType's own __js; listing it here would double-bind.
	"Sales Quote": [
		"public/js/operational_exchange_rate_grid.js",
		"public/js/charge_type_cleanup.js",
		"public/js/charge_break_dialogs.js",
		"public/js/charge_break_buttons.js",
		"public/js/ts_sq_fetch_dialog.js",
		"pricing_center/doctype/sales_quote_charge/sales_quote_charge.js",
		"pricing_center/doctype/sales_quote_air_freight/sales_quote_air_freight.js",
		"pricing_center/doctype/sales_quote_sea_freight/sales_quote_sea_freight.js",
		"public/js/sales_quote_booking_dialog.js",
		"public/js/initialize_tariff_schedule.js",
	],
	"Sales Quote Pack": "pricing_center/doctype/sales_quote_pack/sales_quote_pack.js",
	"Opportunity": [
		"pricing_center/doctype/opportunity_service_scope/opportunity_service_scope.js",
		"public/js/opportunity_services.js",
	],
	"Tariff": [
		"public/js/charge_break_dialogs.js",
		"public/js/charge_break_buttons.js",
		"pricing_center/doctype/tariff_charge/tariff_charge.js",
		"pricing_center/doctype/tariff/tariff.js",
	],
	# Charge parent doctypes: dialogs first, then charge script + handlers
	# Air Booking Packages script first so logistics_calculate_volume_from_dimensions is defined before form handlers run
	"Air Booking": [
		"public/js/operational_exchange_rate_grid.js",
		"public/js/routing_leg_transport_mode_flags.js",
		"public/js/shipper_consignee_defaults.js",
		"air_freight/doctype/air_booking_packages/air_booking_packages.js",
		"public/js/charge_break_dialogs.js",
		"air_freight/doctype/air_booking_charges/air_booking_charges.js",
		"public/js/charge_break_buttons.js",
	],
	"Air Shipment": [
		"public/js/operational_exchange_rate_grid.js",
		"public/js/routing_leg_transport_mode_flags.js",
		"public/js/shipper_consignee_defaults.js",
		"air_freight/doctype/air_booking_packages/air_booking_packages.js",
		"public/js/charge_break_dialogs.js",
		"air_freight/doctype/air_shipment_charges/air_shipment_charges.js",
		"public/js/charge_break_buttons.js",
		"job_management/recognition_client.js",
		"job_management/recognition_policy_fields.js",
		"job_management/job_charge_reopen.js",
		"job_management/job_readiness.js",
	],
	"Air Consolidation": [
		"public/js/charge_break_dialogs.js",
		"public/js/charge_break_buttons.js",
	],
	"Sea Booking": [
		"public/js/operational_exchange_rate_grid.js",
		"public/js/routing_leg_transport_mode_flags.js",
		"public/js/sea_freight_accounting_defaults.js",
		"public/js/shipper_consignee_defaults.js",
		"air_freight/doctype/air_booking_packages/air_booking_packages.js",
		"public/js/charge_break_dialogs.js",
		"sea_freight/doctype/sea_booking_charges/sea_booking_charges.js",
		"public/js/charge_break_buttons.js",
	],
	"Sea Shipment": [
		"public/js/operational_exchange_rate_grid.js",
		"public/js/routing_leg_transport_mode_flags.js",
		"public/js/sea_freight_accounting_defaults.js",
		"public/js/shipper_consignee_defaults.js",
		"air_freight/doctype/air_booking_packages/air_booking_packages.js",
		"public/js/charge_break_dialogs.js",
		"sea_freight/doctype/sea_shipment_charges/sea_shipment_charges.js",
		"public/js/charge_break_buttons.js",
		"job_management/recognition_client.js",
		"job_management/recognition_policy_fields.js",
		"job_management/job_charge_reopen.js",
		"job_management/job_readiness.js",
		"logistics/public/js/profitability_form.js",
		"logistics/job_management/recognition_client.js",
		"logistics/job_management/recognition_policy_fields.js",
		"logistics/job_management/job_charge_reopen.js",
		"logistics/job_management/job_readiness.js",
		"sea_freight/doctype/sea_shipment/sea_shipment_lalamove.js",
	],
	"Sea Consolidation": [
		"public/js/charge_break_dialogs.js",
		"public/js/charge_break_buttons.js",
	],
	"Declaration": [
		"public/js/transport_mode_default_document_type.js",
		"public/js/shipper_consignee_defaults.js",
		"public/js/commercial_invoice_totals.js",
		"public/js/charge_break_dialogs.js",
		"customs/doctype/declaration_charges/declaration_charges.js",
		"public/js/charge_break_buttons.js",
		"job_management/recognition_client.js",
		"job_management/recognition_policy_fields.js",
		"job_management/job_charge_reopen.js",
		"job_management/job_readiness.js",
	],
	"Declaration Order": [
		"public/js/transport_mode_default_document_type.js",
		"public/js/shipper_consignee_defaults.js",
		"public/js/commercial_invoice_totals.js",
		"public/js/charge_break_dialogs.js",
		"customs/doctype/declaration_order_charges/declaration_order_charges.js",
		"public/js/charge_break_buttons.js",
	],
	"Transport Order": [
		"public/js/shipper_consignee_defaults.js",
		"air_freight/doctype/air_booking_packages/air_booking_packages.js",
		"public/js/charge_break_dialogs.js",
		"pricing_center/doctype/transport_order_charges/transport_order_charges.js",
		"public/js/charge_break_buttons.js",
	],
	"Transport Job": [
		"public/js/shipper_consignee_defaults.js",
		"air_freight/doctype/air_booking_packages/air_booking_packages.js",
		"public/js/charge_break_dialogs.js",
		"pricing_center/doctype/transport_job_charges/transport_job_charges.js",
		"public/js/charge_break_buttons.js",
		"job_management/recognition_client.js",
		"job_management/recognition_policy_fields.js",
		"job_management/job_charge_reopen.js",
		"job_management/job_readiness.js",
	],
	"Warehouse Job": [
		"warehousing/warehouse_order_contract_accounts.js",
		"job_management/recognition_client.js",
		"job_management/recognition_policy_fields.js",
		"job_management/job_charge_reopen.js",
		"job_management/job_readiness.js",
	],
	"Warehouse Contract": [
		"public/js/charge_break_dialogs.js",
	],
	"Inbound Order": "warehousing/warehouse_order_contract_accounts.js",
	"Release Order": "warehousing/warehouse_order_contract_accounts.js",
	"Cross-Docking Order": "warehousing/warehouse_order_contract_accounts.js",
	"Transfer Order": "warehousing/warehouse_order_contract_accounts.js",
	"VAS Order": "warehousing/warehouse_order_contract_accounts.js",
	"Stocktake Order": "warehousing/warehouse_order_contract_accounts.js",
	"General Job": [
		"job_management/recognition_client.js",
		"job_management/recognition_policy_fields.js",
	],
	"Project Job": [
		"special_projects/doctype/project_task_job_resource/project_task_job_resource.js",
		"public/js/charge_break_dialogs.js",
		"pricing_center/doctype/transport_job_charges/transport_job_charges.js",
		"public/js/charge_break_buttons.js",
		"public/js/operational_exchange_rate_grid.js",
		"job_management/recognition_client.js",
		"job_management/recognition_policy_fields.js",
	],
	# NOTE: doctype_js paths are MODULE-relative (resolved via frappe.get_app_path(app, *parts)).
	# For this app, that means paths must start with "public/..." or "<sub_module>/...", NOT
	# "logistics/...". A leading "logistics/" causes a doubled path segment and the file
	# silently fails to load (no error). See get_code_files_via_hooks in
	# apps/frappe/frappe/desk/form/meta.py.
	"Special Project": [
		"public/js/profitability_project_form.js",
		# Module-relative paths only (no leading logistics/ — see comment above Docket entry).
		"job_management/recognition_client.js",
		"job_management/recognition_policy_fields.js",
	],
	"Exhibit": [
		"public/js/profitability_project_form.js",
	],
	"MICE Project": [
		"public/js/profitability_project_form.js",
		"public/js/purchase_invoice_dialog.js",
		"public/js/charge_break_dialogs.js",
		"public/js/charge_break_buttons.js",
		"public/js/operational_exchange_rate_grid.js",
		# istable DocTypes do not load their own .js via FormMeta; attach child handlers here.
		"mice/doctype/mice_project_consolidation_charges/mice_project_consolidation_charges.js",
	],
	"Docket": [
		"job_management/recognition_client.js",
		"job_management/recognition_policy_fields.js",
	],
	"Account": "public/js/account_job_profit.js",
	"Recognition Policy Settings": "job_management/doctype/recognition_policy_settings/recognition_policy_settings.js",
	"Purchase Invoice": "public/js/purchase_invoice_container_deposit.js",
	"Credit Hold Lift Request": "logistics/doctype/credit_hold_lift_request/credit_hold_lift_request.js",
	"Cash Advance Request": "cash_advance/doctype/cash_advance_request/cash_advance_request.js",
	"Cash Advance Liquidation": "cash_advance/doctype/cash_advance_liquidation/cash_advance_liquidation.js",
	"Cash Advance Settings": "cash_advance/doctype/cash_advance_settings/cash_advance_settings.js",
	"Cash Acknowledgment": "cash_advance/doctype/cash_acknowledgment/cash_acknowledgment.js",
	"Outlook Calendar Settings": "logistics/doctype/outlook_calendar_settings/outlook_calendar_settings.js",
	"Account": "logistics/public/js/account_job_profit.js",
	"Recognition Policy Settings": "logistics/job_management/doctype/recognition_policy_settings/recognition_policy_settings.js",
	"Purchase Invoice": "logistics/public/js/purchase_invoice_container_deposit.js",
	"Credit Hold Lift Request": "logistics/logistics/doctype/credit_hold_lift_request/credit_hold_lift_request.js",
	"Dispute": "logistics/logistics/doctype/dispute/dispute.js",
	"Cash Advance Request": "logistics/cash_advance/doctype/cash_advance_request/cash_advance_request.js",
	"Cash Advance Liquidation": "logistics/cash_advance/doctype/cash_advance_liquidation/cash_advance_liquidation.js",
	"Cash Advance Settings": "logistics/cash_advance/doctype/cash_advance_settings/cash_advance_settings.js",
	"Cash Acknowledgment": "logistics/cash_advance/doctype/cash_acknowledgment/cash_acknowledgment.js",
	"Outlook Calendar Settings": "logistics/logistics/doctype/outlook_calendar_settings/outlook_calendar_settings.js",
	"User": [
		"public/js/user.js",
		"integrations/outlook/user_outlook.js",
	],
}
doctype_list_js = {
	"Time Sensitive Case": "time_sensitive/doctype/time_sensitive_case/time_sensitive_case_list.js",
}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
#	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

jinja = {
	"methods": [
		"logistics.print_format.sales_invoice.dsb_line_items.get_disbursement_bill_context",
		"logistics.print_format.sales_invoice.dsb_line_items.get_non_disbursement_line_items",
		"logistics.print_format.sales_invoice.dsb_line_items.get_sales_invoice_print_items",
		"logistics.print_format.sales_invoice.dsb_line_items.is_freight_95_main_line",
		"logistics.print_format.sales_invoice.vat_sales_summary.get_vat_sales_summary",
		"logistics.print_format.sales_invoice.vat_sales_summary.item_is_zero_rated_or_exempt",
		"logistics.mice.print_format.mice_project_manifest.mice_project_manifest.get_mice_project_manifest_rows",
		"logistics.mice.print_format.mice_project_manifest.mice_project_manifest.format_mice_manifest_show_dates",
		"logistics.mice.print_format.consol_job_profit_html.consol_job_profit_html.get_consol_job_profit_context",
		"logistics.mice.print_format.consol_job_profit_html.consol_job_profit_html.format_consol_job_profit_amount",
		"logistics.print_format.purchase_invoice.header_address.header_address_from_registration",
		"logistics.print_format.purchase_invoice.tax_amount.printed_tax_amount",
	]
}

# Installation
# ------------

before_install = "logistics.integrations.outlook.install.before_install"
# after_install = "logistics.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "logistics.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

permission_query_conditions = {
	"Control Tower Organization": "logistics.control_tower.permissions.organization",
	"Control Tower GP Target": "logistics.control_tower.permissions.gp_target",
	"Pipeline Entry": "logistics.control_tower.permissions.pipeline_entry",
	"Risk Register Entry": "logistics.control_tower.permissions.risk_register_entry",
	"Returned Billing": "logistics.control_tower.permissions.returned_billing",
}
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Resolved handler list: logistics.doc_event_hooks.DOC_EVENTS.
# Handler order inside each event is the order Frappe runs them.
# Credit control still patches print permission when this module is imported.

boot_session = [
	"logistics.utils.specified_charges_meta.extend_bootinfo_with_specified_charges_meta",
]

doc_events = DOC_EVENTS
_ensure_print_validation_patch()

merge_credit_hooks(doc_events)
merge_invoice_dispute_hooks(doc_events)

# Order Management: after a Pick Warehouse Job submits, push fulfillment and stock.
_ORDER_MANAGEMENT_ON_PICK = "logistics.order_management.tasks.on_warehouse_job_submit"
_wj_events = doc_events.setdefault("Warehouse Job", {})
_wj_on_submit = _wj_events.get("on_submit")
if not _wj_on_submit:
	_wj_events["on_submit"] = _ORDER_MANAGEMENT_ON_PICK
elif isinstance(_wj_on_submit, list):
	if _ORDER_MANAGEMENT_ON_PICK not in _wj_on_submit:
		_wj_events["on_submit"] = list(_wj_on_submit) + [_ORDER_MANAGEMENT_ON_PICK]
elif _wj_on_submit != _ORDER_MANAGEMENT_ON_PICK:
	_wj_events["on_submit"] = [_wj_on_submit, _ORDER_MANAGEMENT_ON_PICK]

# Scheduled Tasks
# ---------------

scheduler_events = {
	"cron": {
		# Live flight position sync from OpenSky (1 bulk /states/all call per run,
		# well under the free anonymous quota of ~400 req/day).
		"*/10 * * * *": [
			"logistics.air_freight.flight_schedules.tasks.sync_active_flights",
			"logistics.order_management.tasks.pull_orders",
		],
		# Time Sensitive: deadline / checkpoint / unacked monitoring every 5 minutes.
		"*/5 * * * *": [
			"logistics.time_sensitive.tasks.monitor_time_sensitive_cases",
		],
	},
	"hourly": [
		"logistics.status_update.tasks.update_milestone_statuses",
		"logistics.air_freight.flight_schedules.tasks.update_air_freight_jobs_with_flight_status",
		"logistics.integrations.outlook.tasks.reconcile_failed_syncs",
		"logistics.integrations.outlook.tasks.sync_recent_task_changes",
		"logistics.transport.tasks.update_sla_statuses",
		"logistics.order_management.tasks.push_stock",
		*HOURLY_SEA_ALERT_TASKS,
	],
	"daily": [
		"logistics.status_update.tasks.update_document_statuses",
		"logistics.status_update.tasks.update_permit_statuses",
		"logistics.status_update.tasks.update_exemption_statuses",
		"logistics.container_management.api.reconcile_containers_from_terminal_sea_shipments",
		"logistics.air_freight.flight_schedules.tasks.cleanup_old_schedules",
		"logistics.air_freight.flight_schedules.tasks.cleanup_old_sync_logs",
		"logistics.air_freight.casslink.sftp_client.pull_configured_companies",
		"logistics.job_management.auto_recognition.process_auto_recognition",
		"logistics.order_management.tasks.cleanup_sync_logs",
		*DAILY_SEA_ALERT_TASKS,
	],
}

# Testing
# -------

# before_tests = "logistics.install.before_tests"

# Overriding Methods
# ------------------------------
#
override_whitelisted_methods = {
	"frappe.utils.print_format.download_pdf": (
		"logistics.print_format.payment_entry.bank_forms_pdf.download_pdf"
	),
	"frappe.desk.query_report.export_query": (
		"logistics.bir_cas.export_query.export_query"
	),
}

override_doctype_class = {
	"Transaction Deletion Record": (
		"logistics.overrides.transaction_deletion_record.LogisticsTransactionDeletionRecord"
	),
}

pdf_generator = [
	"logistics.print_format.payment_entry.bank_forms_pdf.pdf_generator_hook",
]
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
override_doctype_dashboards = {
	"Opportunity": "logistics.pricing_center.dashboards.opportunity_dashboard.get_data",
	"Lead": "logistics.pricing_center.dashboards.lead_dashboard.get_data",
	"Customer": "logistics.pricing_center.dashboards.customer_dashboard.get_data",
	"Prospect": "logistics.pricing_center.dashboards.prospect_dashboard.get_data",
}

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]


# User Data Protection
# --------------------
# Empty until a privacy pass names real DocTypes (customer contacts, driver
# phone, portal users). Do not restore the framework placeholders
# ({doctype_1}, {field_1}); Frappe would look those names up literally.

user_data_fields = []

# Company → Delete Transactions: keep company-scoped setup/masters.
# Do not list issingle DocTypes: ERPNext already excludes them, and missing
# names (not yet migrated) fail Transaction Deletion Record link validation.
company_data_to_be_ignored = [
	"Air Freight Settings",
	"Cash Advance Settings",
	"Customs Settings",
	"IATA Settings",
	"Manifest Settings",
	"Pricing Center Settings",
	"Recognition Policy Settings",
	"Sea Freight Settings",
	"Sustainability Settings",
	"Warehouse Settings",
	"CASS Settlement Period",
	"Client Credit Line",
	"Dock Door",
	"Handling Unit",
	"MAWB Stock Range",
	"Profit Center",
	"Settlement Group",
	"Storage Location",
	"Sustainability Compliance",
	"Sustainability Goals",
	"Sustainability Metrics",
	"Transport Vehicle",
]

# Database migrations (after schema sync)
# ---------------------------------------
after_migrate = [
	"logistics.job_management.recognition_migrate.after_migrate",
	"logistics.analytics_reports.sync_cnx_reports.after_migrate",
	"logistics.cash_advance.install.after_migrate",
	"logistics.control_tower.install.after_migrate",
	"logistics.sea_freight.install.after_migrate",
]

after_install = "logistics.control_tower.install.after_install"

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"logistics.auth.validate"
# ]

# Translation
# --------------------------------

# Make link fields search translated document names for these DocTypes
# Recommended only for DocTypes which have limited documents with untranslated names
# For example: Role, Gender, etc.
# translated_search_doctypes = []

from logistics.utils.internal_job_link_validation import apply_internal_job_link_validation_patch
from logistics.utils.specified_charges_meta import apply_recursive_meta_bundle_patch

apply_internal_job_link_validation_patch()
apply_recursive_meta_bundle_patch()
