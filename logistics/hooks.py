# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from frappe import append_hook

from logistics.utils.credit_management import merge_credit_hooks

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
	"/assets/logistics/css/get_charges_from_quotation.css?v=8",
	"/assets/logistics/css/charges_grid_no_row_check.css?v=2",
	"/assets/logistics/css/density_factor.css?v=1",
	"/assets/logistics/css/workflow_center.css?v=1",
]
app_include_js = [
	"/assets/logistics/js/address_link_query.js?v=1",
	"/assets/logistics/js/party_address_contact.js?v=1",
	"/assets/logistics/js/linked_service_link_query.js?v=1",
	"/assets/logistics/js/virtual_linked_services_grid.js?v=1",
	"/assets/logistics/js/freight_agent_service.js?v=4",
	"/assets/logistics/js/charge_bill_to.js?v=2",
	"/assets/logistics/js/desk_main_sidebar_visibility_fix.js?v=2",
	"/assets/logistics/js/form_desk_title_route_guard.js?v=3",
	"/assets/logistics/js/grid_cannot_add_rows_toolbar_fix.js",
	# Desk-wide: form refresh can run before doctype_js bundles finish; define dialog globals early.
	"/assets/logistics/js/internal_job_create_from_source.js?v=20",
	"/assets/logistics/js/one_off_sales_quote_order_standard.js?v=2",
	"/assets/logistics/js/main_service_internal_job_mutual_exclusive.js?v=7",
	"/assets/logistics/js/service_role.js?v=3",
	"/assets/logistics/js/internal_job_detail_grid_delete_fix.js",
	"/assets/logistics/js/get_charges_from_quotation.js?v=18",
	"/assets/logistics/js/sea_consolidation_matching_shipments.js?v=3",
	"/assets/logistics/js/air_consolidation_matching_shipments.js?v=5",
	"/assets/logistics/js/charges_disbursement_sync.js",
	"/assets/logistics/js/charge_break_dialogs.js",
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
]

# include js, css files in header of web template
# web_include_css = "/assets/logistics/css/logistics.css"
# web_include_js = "/assets/logistics/js/logistics.js"

# include js in page
page_js = {
	"workflow-center": "public/js/workflow_center.js",
}

# include js in doctype views
doctype_js = {
	"Internal Job Detail": "logistics/logistics/doctype/internal_job_detail/internal_job_detail.js",
	"Linked Service Detail": "logistics/logistics/doctype/linked_service_detail/linked_service_detail.js",
	"Container": "logistics/logistics/doctype/container/container.js",
	"UNLOCO": [
		"logistics/logistics/doctype/unloco/unloco.js",
		"logistics/logistics/doctype/unloco/unloco_list.js",
	],
	# Sales Quote: dialogs first, break row/grid handlers, then air/sea freight scripts.
	# Paths are module-relative (no leading "logistics/") — see NOTE below for Special Project.
	# sales_quote.js is omitted: it loads via the DocType's own __js; listing it here would double-bind.
	"Sales Quote": [
		"public/js/operational_exchange_rate_grid.js",
		"public/js/charge_break_dialogs.js",
		"public/js/charge_break_buttons.js",
		"pricing_center/doctype/sales_quote_charge/sales_quote_charge.js",
		"pricing_center/doctype/sales_quote_air_freight/sales_quote_air_freight.js",
		"pricing_center/doctype/sales_quote_sea_freight/sales_quote_sea_freight.js",
		"public/js/sales_quote_booking_dialog.js",
	],
	"Sales Quote Pack": "logistics/pricing_center/doctype/sales_quote_pack/sales_quote_pack.js",
	"Opportunity": [
		"pricing_center/doctype/opportunity_service_scope/opportunity_service_scope.js",
		"public/js/opportunity_services.js",
	],
	"Tariff": [
		"public/js/charge_break_dialogs.js",
		"public/js/charge_break_buttons.js",
		"logistics/pricing_center/doctype/tariff_charge/tariff_charge.js",
		"logistics/pricing_center/doctype/tariff/tariff.js",
	],
	# Charge parent doctypes: dialogs first, then charge script + handlers
	# Air Booking Packages script first so logistics_calculate_volume_from_dimensions is defined before form handlers run
	"Air Booking": [
		"logistics/public/js/operational_exchange_rate_grid.js",
		"logistics/public/js/routing_leg_transport_mode_flags.js",
		"logistics/public/js/shipper_consignee_defaults.js",
		"logistics/air_freight/doctype/air_booking_packages/air_booking_packages.js",
		"public/js/charge_break_dialogs.js",
		"logistics/public/js/document_alerts_dialog.js",
		"logistics/air_freight/doctype/air_booking_charges/air_booking_charges.js",
		"public/js/charge_break_buttons.js",
		# Same Get Charges from Quotation UI as Sea Booking / Transport Order (list criteria, search, cards, Apply).
		"logistics/public/js/get_charges_from_quotation.js",
	],
	"Air Shipment": [
		"logistics/public/js/operational_exchange_rate_grid.js",
		"logistics/public/js/routing_leg_transport_mode_flags.js",
		"logistics/public/js/internal_job_create_from_source.js",
		"logistics/public/js/shipper_consignee_defaults.js",
		"logistics/air_freight/doctype/air_booking_packages/air_booking_packages.js",
		"public/js/charge_break_dialogs.js",
		"logistics/public/js/document_alerts_dialog.js",
		"logistics/air_freight/doctype/air_shipment_charges/air_shipment_charges.js",
		"public/js/charge_break_buttons.js",
		"logistics/public/js/profitability_form.js",
		"logistics/public/js/sales_invoice_dialog.js",
		"logistics/public/js/purchase_invoice_dialog.js",
		"logistics/job_management/recognition_client.js",
		"logistics/job_management/recognition_policy_fields.js",
		"logistics/job_management/job_charge_reopen.js",
	],
	"Air Consolidation": [
		"public/js/charge_break_dialogs.js",
		"logistics/public/js/document_alerts_dialog.js",
		"logistics/public/js/air_consolidation_matching_shipments.js",
		"public/js/charge_break_buttons.js",
		"logistics/public/js/purchase_invoice_dialog.js",
	],
	"Sea Booking": [
		"logistics/public/js/operational_exchange_rate_grid.js",
		"logistics/public/js/routing_leg_transport_mode_flags.js",
		"logistics/public/js/sea_freight_accounting_defaults.js",
		"logistics/public/js/shipper_consignee_defaults.js",
		"logistics/air_freight/doctype/air_booking_packages/air_booking_packages.js",
		"public/js/charge_break_dialogs.js",
		"logistics/public/js/document_alerts_dialog.js",
		"logistics/sea_freight/doctype/sea_booking_charges/sea_booking_charges.js",
		"public/js/charge_break_buttons.js",
	],
	"Sea Shipment": [
		"logistics/public/js/operational_exchange_rate_grid.js",
		"logistics/public/js/routing_leg_transport_mode_flags.js",
		"logistics/public/js/internal_job_create_from_source.js",
		"logistics/public/js/sea_freight_accounting_defaults.js",
		"logistics/public/js/shipper_consignee_defaults.js",
		"logistics/air_freight/doctype/air_booking_packages/air_booking_packages.js",
		"logistics/public/js/sales_invoice_dialog.js",
		"logistics/public/js/purchase_invoice_dialog.js",
		"public/js/charge_break_dialogs.js",
		"logistics/public/js/document_alerts_dialog.js",
		"logistics/sea_freight/doctype/sea_shipment_charges/sea_shipment_charges.js",
		"public/js/charge_break_buttons.js",
		"logistics/public/js/profitability_form.js",
		"logistics/job_management/recognition_client.js",
		"logistics/job_management/recognition_policy_fields.js",
		"logistics/job_management/job_charge_reopen.js",
	],
	"Sea Consolidation": [
		"public/js/charge_break_dialogs.js",
		"logistics/public/js/document_alerts_dialog.js",
		"logistics/public/js/sea_consolidation_matching_shipments.js",
		"public/js/charge_break_buttons.js",
		"logistics/public/js/purchase_invoice_dialog.js",
	],
	"Declaration": [
		"logistics/public/js/internal_job_create_from_source.js",
		"logistics/public/js/transport_mode_default_document_type.js",
		"logistics/public/js/shipper_consignee_defaults.js",
		"logistics/public/js/sales_invoice_dialog.js",
		"logistics/public/js/purchase_invoice_dialog.js",
		"logistics/public/js/commercial_invoice_totals.js",
		"public/js/charge_break_dialogs.js",
		"logistics/public/js/document_alerts_dialog.js",
		"logistics/customs/doctype/declaration_charges/declaration_charges.js",
		"public/js/charge_break_buttons.js",
		"logistics/public/js/profitability_form.js",
		"logistics/job_management/recognition_client.js",
		"logistics/job_management/recognition_policy_fields.js",
		"logistics/job_management/job_charge_reopen.js",
	],
	"Declaration Order": [
		"logistics/public/js/transport_mode_default_document_type.js",
		"logistics/public/js/shipper_consignee_defaults.js",
		"logistics/public/js/commercial_invoice_totals.js",
		"public/js/charge_break_dialogs.js",
		"logistics/public/js/document_alerts_dialog.js",
		"logistics/customs/doctype/declaration_order_charges/declaration_order_charges.js",
		"public/js/charge_break_buttons.js",
		# Same Get Charges from Quotation UI as Air / Sea / Transport (list, preview, Apply).
		"logistics/public/js/get_charges_from_quotation.js",
	],
	"Transport Order": [
		"logistics/public/js/shipper_consignee_defaults.js",
		"logistics/air_freight/doctype/air_booking_packages/air_booking_packages.js",
		"public/js/charge_break_dialogs.js",
		"logistics/public/js/document_alerts_dialog.js",
		"logistics/pricing_center/doctype/transport_order_charges/transport_order_charges.js",
		"public/js/charge_break_buttons.js",
	],
	"Transport Job": [
		"logistics/public/js/internal_job_create_from_source.js",
		"logistics/public/js/shipper_consignee_defaults.js",
		"logistics/air_freight/doctype/air_booking_packages/air_booking_packages.js",
		"public/js/charge_break_dialogs.js",
		"logistics/public/js/document_alerts_dialog.js",
		"logistics/public/js/sales_invoice_dialog.js",
		"logistics/public/js/purchase_invoice_dialog.js",
		"logistics/pricing_center/doctype/transport_job_charges/transport_job_charges.js",
		"public/js/charge_break_buttons.js",
		"logistics/public/js/profitability_form.js",
		"logistics/job_management/recognition_client.js",
		"logistics/job_management/recognition_policy_fields.js",
		"logistics/job_management/job_charge_reopen.js",
	],
	"Transport Consolidation": [
		"logistics/public/js/document_alerts_dialog.js",
	],
	"Warehouse Job": [
		"logistics/public/js/sales_invoice_dialog.js",
		"logistics/public/js/purchase_invoice_dialog.js",
		"logistics/public/js/profitability_form.js",
		"logistics/job_management/recognition_client.js",
		"logistics/job_management/recognition_policy_fields.js",
		"logistics/job_management/job_charge_reopen.js",
	],
	"Warehouse Contract": [
		"public/js/charge_break_dialogs.js",
	],
	"General Job": [
		"logistics/public/js/profitability_form.js",
		"logistics/job_management/recognition_client.js",
		"logistics/job_management/recognition_policy_fields.js",
	],
	"Project Task Order": [
		"logistics/special_projects/doctype/project_task_order/project_task_order.js",
		"logistics/special_projects/doctype/project_task_job_resource/project_task_job_resource.js",
		"logistics/public/js/document_alerts_dialog.js",
		"public/js/charge_break_dialogs.js",
		"logistics/pricing_center/doctype/transport_job_charges/transport_job_charges.js",
		"public/js/charge_break_buttons.js",
	],
	"Project Job": [
		"logistics/special_projects/doctype/project_task_job_resource/project_task_job_resource.js",
		"logistics/public/js/document_alerts_dialog.js",
		"public/js/charge_break_dialogs.js",
		"logistics/pricing_center/doctype/transport_job_charges/transport_job_charges.js",
		"public/js/charge_break_buttons.js",
		"logistics/public/js/purchase_invoice_dialog.js",
		"logistics/public/js/operational_exchange_rate_grid.js",
		"logistics/public/js/profitability_form.js",
		"logistics/job_management/recognition_client.js",
		"logistics/job_management/recognition_policy_fields.js",
	],
	# NOTE: doctype_js paths are MODULE-relative (resolved via frappe.get_app_path(app, *parts)).
	# For this app, that means paths must start with "public/..." or "<sub_module>/...", NOT
	# "logistics/...". A leading "logistics/" causes a doubled path segment and the file
	# silently fails to load (no error). See get_code_files_via_hooks in
	# apps/frappe/frappe/desk/form/meta.py.
	"Special Project": [
		"public/js/profitability_project_form.js",
		"logistics/public/js/sales_invoice_dialog.js",
		"logistics/public/js/purchase_invoice_dialog.js",
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
	],
	"Docket": [
		"logistics/public/js/sales_invoice_dialog.js",
		"logistics/public/js/purchase_invoice_dialog.js",
		"logistics/public/js/profitability_form.js",
		"logistics/job_management/recognition_client.js",
		"logistics/job_management/recognition_policy_fields.js",
	],
	"Account": "logistics/public/js/account_job_profit.js",
	"Recognition Policy Settings": "logistics/job_management/doctype/recognition_policy_settings/recognition_policy_settings.js",
	"Purchase Invoice": "logistics/public/js/purchase_invoice_container_deposit.js",
	"Credit Hold Lift Request": "logistics/logistics/doctype/credit_hold_lift_request/credit_hold_lift_request.js",
	"Cash Advance Request": "logistics/cash_advance/doctype/cash_advance_request/cash_advance_request.js",
	"Cash Advance Liquidation": "logistics/cash_advance/doctype/cash_advance_liquidation/cash_advance_liquidation.js",
	"Cash Advance Settings": "logistics/cash_advance/doctype/cash_advance_settings/cash_advance_settings.js",
	"Cash Acknowledgment": "logistics/cash_advance/doctype/cash_acknowledgment/cash_acknowledgment.js",
	"Outlook Calendar Settings": "logistics/logistics/doctype/outlook_calendar_settings/outlook_calendar_settings.js",
	"User": "logistics/integrations/outlook/user_outlook.js",
}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
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
# Hook on document methods and events (PI/SI lifecycle for job/shipment links)
# Auto-populate documents and milestones from template on save (doctypes with Documents/Milestones tab)
_doc_milestone_doctypes = [
	"Air Booking", "Air Shipment", "Air Consolidation",
	"Sea Booking", "Sea Shipment", "Sea Consolidation",
	"Transport Order", "Transport Job",
	"Declaration", "Declaration Order",
	"Inbound Order", "Release Order", "Transfer Order", "Cross-Docking Order",
	"Warehouse Job", "General Job", "Special Project",
	"Project Order", "Project Job",
	# MICE family: parent doctypes with a ``milestones`` child table and
	# ``milestone_template`` field. Without these hooks, Date Based sync
	# (parent date field <-> milestone actual_end) and status auto-update
	# (Planned / Started / Completed / Delayed) never run on save.
	"MICE Project", "Docket", "MICE Order", "MICE Job",
]

doc_events = {
	"Opportunity": {
		"onload": "logistics.pricing_center.utils.opportunity_scopes.on_opportunity_onload",
		"validate": "logistics.pricing_center.utils.opportunity_scopes.on_opportunity_validate",
	},
	"Lead": {
		"onload": "logistics.pricing_center.crm_sales_quote_onload.lead_onload",
	},
	"Prospect": {
		"onload": "logistics.pricing_center.crm_sales_quote_onload.prospect_onload",
	},
	"Customer": {
		"validate": "logistics.utils.party_code.validate_customer_supplier_party_code",
	},
	"Supplier": {
		"validate": "logistics.utils.party_code.validate_customer_supplier_party_code",
	},
	"Accounting Dimension": {
		"after_insert": "logistics.job_management.gl_item_dimension.on_accounting_dimension_changed",
		"on_update": "logistics.job_management.gl_item_dimension.on_accounting_dimension_changed",
		"on_trash": "logistics.job_management.gl_item_dimension.on_accounting_dimension_changed",
	},
	"Cost Center": {
		"validate": "logistics.job_management.cost_center_defaults.set_cost_center_branch_default",
	},
	"Account": {
		"validate": "logistics.logistics.account_job_profit.validate_account_job_profit",
	},
	"Purchase Invoice": {
		"validate": [
			"logistics.invoice_integration.container_deposit_pi.apply_container_deposit_expense_account",
			"logistics.invoice_integration.container_deposit_dimensions.sync_container_deposit_pi_accounting_dimensions",
			"logistics.invoice_integration.job_number_dimension_sync.sync_job_number_dimension_on_purchase_invoice_items",
			"logistics.invoice_integration.gl_item_dimension_sync.sync_item_accounting_dimension_from_invoice_items",
		],
		"before_submit": [
			"logistics.invoice_integration.container_deposit_pi.apply_container_deposit_expense_account",
			"logistics.invoice_integration.container_deposit_dimensions.sync_container_deposit_pi_accounting_dimensions",
			"logistics.invoice_integration.job_number_dimension_sync.sync_job_number_dimension_on_purchase_invoice_items",
			"logistics.invoice_integration.gl_item_dimension_sync.sync_item_accounting_dimension_from_invoice_items",
			"logistics.invoice_integration.container_deposit_pi_ui.validate_container_deposit_lines_have_container_before_submit",
		],
		"before_update_after_submit": "logistics.invoice_integration.gl_item_dimension_sync.sync_item_accounting_dimension_from_invoice_items",
		"on_submit": "logistics.invoice_integration.invoice_hooks.on_purchase_invoice_submit",
		"on_cancel": "logistics.invoice_integration.invoice_hooks.on_purchase_invoice_cancel",
	},
	"Sales Invoice": {
		"validate": "logistics.invoice_integration.gl_item_dimension_sync.sync_item_accounting_dimension_from_invoice_items",
		"before_submit": "logistics.invoice_integration.gl_item_dimension_sync.sync_item_accounting_dimension_from_invoice_items",
		"before_update_after_submit": "logistics.invoice_integration.gl_item_dimension_sync.sync_item_accounting_dimension_from_invoice_items",
		"on_submit": "logistics.invoice_integration.invoice_hooks.on_sales_invoice_submit",
		"on_cancel": "logistics.invoice_integration.invoice_hooks.on_sales_invoice_cancel",
	},
	"Task": {
		"after_insert": "logistics.integrations.outlook.task_sync.on_task_change",
		"on_update": "logistics.integrations.outlook.task_sync.on_task_change",
		"on_trash": "logistics.integrations.outlook.task_sync.on_task_delete",
	},
}
for _dt in _doc_milestone_doctypes:
	_before_save = [
		"logistics.document_management.api.update_milestone_status_on_parent_before_save",
		"logistics.document_management.api.update_job_document_status_on_parent_before_save",
	]
	# Populate documents/milestones in before_save (same transaction) — not on_update, which
	# nested-saved and bumped modified after the client received the save response (TimestampMismatchError).
	if _dt != "Declaration Order":
		_before_save.insert(0, "logistics.document_management.api.ensure_documents_and_milestones_from_template")
	doc_events[_dt] = {
		"before_save": _before_save,
		"before_submit": "logistics.document_management.api.enforce_required_job_documents_before_submit",
	}

# Main Service vs Internal Job: internal jobs cannot be flagged as main service
_MAIN_SERVICE_VALIDATE = "logistics.utils.charge_service_type.on_validate_main_service_internal_job"
for _dt in (
	"Air Booking",
	"Air Shipment",
	"Sea Booking",
	"Sea Shipment",
	"Transport Order",
	"Transport Job",
	"Declaration",
	"Declaration Order",
	"Warehouse Job",
	"VAS Order",
	"Inbound Order",
	"Release Order",
	"Cross-Docking Order",
	"Project Job",
	"MICE Job",
	"Exhibit Job",
):
	if _dt not in doc_events:
		doc_events[_dt] = {}
	_v = doc_events[_dt].get("validate")
	if not _v:
		doc_events[_dt]["validate"] = _MAIN_SERVICE_VALIDATE
	elif isinstance(_v, list):
		if _MAIN_SERVICE_VALIDATE not in _v:
			doc_events[_dt]["validate"] = list(_v) + [_MAIN_SERVICE_VALIDATE]
	elif _v != _MAIN_SERVICE_VALIDATE:
		doc_events[_dt]["validate"] = [_v, _MAIN_SERVICE_VALIDATE]

# Header estimated revenue / costs: roll up from charge lines on validate (persists to DB)
_JOB_HEADER_ESTIMATE_FROM_CHARGES = "logistics.job_management.doc_events.on_job_validate_estimates"
for _dt in (
	"Air Shipment",
	"Sea Shipment",
	"Transport Job",
	"Warehouse Job",
	"Declaration",
	"General Job",
	"Project Job",
	"Special Project",
	"Docket",
):
	if _dt not in doc_events:
		doc_events[_dt] = {}
	_v = doc_events[_dt].get("validate")
	if not _v:
		doc_events[_dt]["validate"] = _JOB_HEADER_ESTIMATE_FROM_CHARGES
	elif isinstance(_v, list):
		if _JOB_HEADER_ESTIMATE_FROM_CHARGES not in _v:
			doc_events[_dt]["validate"] = list(_v) + [_JOB_HEADER_ESTIMATE_FROM_CHARGES]
	elif _v != _JOB_HEADER_ESTIMATE_FROM_CHARGES:
		doc_events[_dt]["validate"] = [_v, _JOB_HEADER_ESTIMATE_FROM_CHARGES]

# Block charge grid edits when job/shipment is in a closing status (Reopen Job unlocks)
_CHARGE_REOPEN_VALIDATE = "logistics.job_management.charge_reopen.validate_submitted_charges_not_locked"
for _dt in (
	"Transport Job",
	"Sea Shipment",
	"Air Shipment",
	"Warehouse Job",
	"Declaration",
):
	if _dt not in doc_events:
		doc_events[_dt] = {}
	_v = doc_events[_dt].get("validate")
	if not _v:
		doc_events[_dt]["validate"] = _CHARGE_REOPEN_VALIDATE
	elif isinstance(_v, list):
		if _CHARGE_REOPEN_VALIDATE not in _v:
			doc_events[_dt]["validate"] = list(_v) + [_CHARGE_REOPEN_VALIDATE]
	elif _v != _CHARGE_REOPEN_VALIDATE:
		doc_events[_dt]["validate"] = [_v, _CHARGE_REOPEN_VALIDATE]

append_hook(
	doc_events,
	"*",
	{"validate": "logistics.utils.load_type_active.validate_load_type_links_on_doc"},
)
append_hook(
	doc_events,
	"*",
	{"validate": "logistics.utils.freight_agent_service.validate_freight_agent_links_on_doc"},
)

# Operational exchange rates: resolve from Source Exchange Rate (date-based) and push to charge lines
_OER_BEFORE_SAVE = "logistics.utils.operational_exchange_rates.on_before_save_operational_exchange_rates"
for _dt in ("Air Booking", "Sea Booking", "Air Shipment", "Sea Shipment", "Project Job"):
	if _dt not in doc_events:
		doc_events[_dt] = {}
	_bs = doc_events[_dt].get("before_save")
	if not _bs:
		doc_events[_dt]["before_save"] = _OER_BEFORE_SAVE
	elif isinstance(_bs, list):
		if _OER_BEFORE_SAVE not in _bs:
			doc_events[_dt]["before_save"] = list(_bs) + [_OER_BEFORE_SAVE]
	elif _bs != _OER_BEFORE_SAVE:
		doc_events[_dt]["before_save"] = [_bs, _OER_BEFORE_SAVE]

# Internal job → Main Service rollup: push planned / actual cost & revenue from an internal job's
# charges onto its Main Service's Internal Jobs row. Covers every operational doctype that can be
# flagged ``is_internal_job=1`` with a ``main_job_type`` + ``main_job`` link.
_INTERNAL_JOB_ROLLUP_MODULE = "logistics.utils.internal_job_main_rollup"
_INTERNAL_JOB_ROLLUP_EVENTS = (
	("on_update", _INTERNAL_JOB_ROLLUP_MODULE + ".on_internal_job_after_save"),
	("on_submit", _INTERNAL_JOB_ROLLUP_MODULE + ".on_internal_job_submit"),
	("on_update_after_submit", _INTERNAL_JOB_ROLLUP_MODULE + ".on_internal_job_update_after_submit"),
	("on_cancel", _INTERNAL_JOB_ROLLUP_MODULE + ".on_internal_job_cancel"),
)
for _dt in (
	"Air Booking",
	"Sea Booking",
	"Air Shipment",
	"Sea Shipment",
	"Transport Order",
	"Transport Job",
	"Declaration",
	"Declaration Order",
	"Warehouse Job",
	"Inbound Order",
	"Release Order",
	"Cross-Docking Order",
	"Project Job",
):
	if _dt not in doc_events:
		doc_events[_dt] = {}
	for _event, _handler in _INTERNAL_JOB_ROLLUP_EVENTS:
		_existing = doc_events[_dt].get(_event)
		if not _existing:
			doc_events[_dt][_event] = _handler
		elif isinstance(_existing, list):
			if _handler not in _existing:
				doc_events[_dt][_event] = list(_existing) + [_handler]
		elif _existing != _handler:
			doc_events[_dt][_event] = [_existing, _handler]

# Internal Job persistence: keep the booking's ``internal_job_details`` table in sync with backing
# ``Internal Job`` documents. ``before_save`` ensures every detail row points at a saved Internal Job
# (creating one when the row is new), pushes parameter edits back, and deletes Internal Jobs whose
# detail row was removed. ``on_trash`` cleans up every Internal Job owned by the booking.
_INTERNAL_JOB_PERSISTENCE_MODULE = "logistics.utils.internal_job_persistence"
_INTERNAL_JOB_PERSISTENCE_EVENTS = (
	("before_save", _INTERNAL_JOB_PERSISTENCE_MODULE + ".sync_internal_job_details_to_internal_jobs"),
	("on_trash", _INTERNAL_JOB_PERSISTENCE_MODULE + ".delete_internal_jobs_for_booking"),
)
for _dt in (
	"Sea Booking",
	"Air Booking",
	"Sea Shipment",
	"Air Shipment",
	"Transport Order",
	"Transport Job",
	"Declaration",
	"Declaration Order",
	"Warehouse Job",
	"Inbound Order",
	"Release Order",
	"Cross-Docking Order",
	"General Job",
	"Project Job",
	"MICE Job",
	"Exhibit Job",
	"MICE Project",
	"Docket",
	"Exhibit",
	# Sales Quote owns Linked Services that are cloned onto the Booking/Order created from the quote.
	# created from the quote. The sync is gated on quotation_type inside the handler.
	"Sales Quote",
	"Change Request",
):
	if _dt not in doc_events:
		doc_events[_dt] = {}
	for _event, _handler in _INTERNAL_JOB_PERSISTENCE_EVENTS:
		_existing = doc_events[_dt].get(_event)
		if not _existing:
			doc_events[_dt][_event] = _handler
		elif isinstance(_existing, list):
			if _handler not in _existing:
				doc_events[_dt][_event] = list(_existing) + [_handler]
		elif _existing != _handler:
			doc_events[_dt][_event] = [_existing, _handler]

# Internal Job → ``Internal Job Detail`` snapshot sync: when an Internal Job document is edited
# directly (form / scripted save), push the new parameter values into every detail row that links
# to it so reports / API consumers reading ``tabInternal Job Detail`` see fresh values.
_INTERNAL_JOB_DOC_EVENTS = doc_events.setdefault("Internal Job", {})
_INTERNAL_JOB_ON_UPDATE = (
	_INTERNAL_JOB_PERSISTENCE_MODULE + ".sync_internal_job_to_detail_rows"
)
_existing_ij_on_update = _INTERNAL_JOB_DOC_EVENTS.get("on_update")
if not _existing_ij_on_update:
	_INTERNAL_JOB_DOC_EVENTS["on_update"] = _INTERNAL_JOB_ON_UPDATE
elif isinstance(_existing_ij_on_update, list):
	if _INTERNAL_JOB_ON_UPDATE not in _existing_ij_on_update:
		_INTERNAL_JOB_DOC_EVENTS["on_update"] = list(_existing_ij_on_update) + [_INTERNAL_JOB_ON_UPDATE]
elif _existing_ij_on_update != _INTERNAL_JOB_ON_UPDATE:
	_INTERNAL_JOB_DOC_EVENTS["on_update"] = [_existing_ij_on_update, _INTERNAL_JOB_ON_UPDATE]

_LINKED_SERVICE_DOC_EVENTS = doc_events.setdefault("Linked Service", {})
_existing_ls_on_update = _LINKED_SERVICE_DOC_EVENTS.get("on_update")
if not _existing_ls_on_update:
	_LINKED_SERVICE_DOC_EVENTS["on_update"] = _INTERNAL_JOB_ON_UPDATE
elif isinstance(_existing_ls_on_update, list):
	if _INTERNAL_JOB_ON_UPDATE not in _existing_ls_on_update:
		_LINKED_SERVICE_DOC_EVENTS["on_update"] = list(_existing_ls_on_update) + [_INTERNAL_JOB_ON_UPDATE]
elif _existing_ls_on_update != _INTERNAL_JOB_ON_UPDATE:
	_LINKED_SERVICE_DOC_EVENTS["on_update"] = [_existing_ls_on_update, _INTERNAL_JOB_ON_UPDATE]

# Special Project Services: virtual grid backed by Special Project Service documents.
_SP_SERVICE_PERSISTENCE_MODULE = "logistics.special_projects.special_project_service_persistence"
_SP_SERVICE_PERSISTENCE_EVENTS = (
	("before_save", _SP_SERVICE_PERSISTENCE_MODULE + ".sync_special_project_services_to_documents"),
	("on_trash", _SP_SERVICE_PERSISTENCE_MODULE + ".delete_special_project_services_for_project"),
)
for _event, _handler in _SP_SERVICE_PERSISTENCE_EVENTS:
	_existing = doc_events.setdefault("Special Project", {}).get(_event)
	if not _existing:
		doc_events["Special Project"][_event] = _handler
	elif isinstance(_existing, list):
		if _handler not in _existing:
			doc_events["Special Project"][_event] = list(_existing) + [_handler]
	elif _existing != _handler:
		doc_events["Special Project"][_event] = [_existing, _handler]

# Special Project lifecycle financials: refresh when operational job charges change.
_LIFECYCLE_FINANCIAL_REFRESH = (
	"logistics.special_projects.lifecycle_job_financial_rollup"
	".on_operational_job_update_refresh_special_project_lifecycle"
)
_LIFECYCLE_FINANCIAL_REFRESH_EVENTS = ("on_update", "on_submit", "on_update_after_submit")
for _dt in (
	"Air Booking",
	"Sea Booking",
	"Air Shipment",
	"Sea Shipment",
	"Transport Order",
	"Transport Job",
	"Declaration",
	"Declaration Order",
	"Warehouse Job",
	"Inbound Order",
	"Release Order",
	"Cross-Docking Order",
	"Project Job",
):
	if _dt not in doc_events:
		doc_events[_dt] = {}
	for _event in _LIFECYCLE_FINANCIAL_REFRESH_EVENTS:
		_existing = doc_events[_dt].get(_event)
		if not _existing:
			doc_events[_dt][_event] = _LIFECYCLE_FINANCIAL_REFRESH
		elif isinstance(_existing, list):
			if _LIFECYCLE_FINANCIAL_REFRESH not in _existing:
				doc_events[_dt][_event] = list(_existing) + [_LIFECYCLE_FINANCIAL_REFRESH]
		elif _existing != _LIFECYCLE_FINANCIAL_REFRESH:
			doc_events[_dt][_event] = [_existing, _LIFECYCLE_FINANCIAL_REFRESH]

# Special Project: Air/Sea Shipment submit -> post deliveries to parent Special Project.
# Mirrors the Transport Order on_submit pattern. The Shipment's ``project`` field
# resolves the Special Project; rows in its Packages table are folded into the
# Special Project's Deliveries with the originating Booking's lifecycle stage.
_FREIGHT_SHIPMENT_RECEIPT_HANDLERS = (
	(
		"on_submit",
		"logistics.special_projects.special_project_packages.on_freight_shipment_submit",
	),
	(
		"on_cancel",
		"logistics.special_projects.special_project_packages.on_freight_shipment_cancel",
	),
)
for _dt in ("Air Shipment", "Sea Shipment"):
	if _dt not in doc_events:
		doc_events[_dt] = {}
	for _event, _handler in _FREIGHT_SHIPMENT_RECEIPT_HANDLERS:
		_existing = doc_events[_dt].get(_event)
		if not _existing:
			doc_events[_dt][_event] = _handler
		elif isinstance(_existing, list):
			if _handler not in _existing:
				doc_events[_dt][_event] = list(_existing) + [_handler]
		elif _existing != _handler:
			doc_events[_dt][_event] = [_existing, _handler]

# Special Project: Transport Job submit/cancel -> post deliveries (Transport Order is planning-only).
_TRANSPORT_JOB_RECEIPT_HANDLERS = (
	(
		"on_submit",
		"logistics.special_projects.special_project_packages.on_transport_job_submit",
	),
	(
		"on_cancel",
		"logistics.special_projects.special_project_packages.on_transport_job_cancel",
	),
)
if "Transport Job" not in doc_events:
	doc_events["Transport Job"] = {}
for _event, _handler in _TRANSPORT_JOB_RECEIPT_HANDLERS:
	_existing = doc_events["Transport Job"].get(_event)
	if not _existing:
		doc_events["Transport Job"][_event] = _handler
	elif isinstance(_existing, list):
		if _handler not in _existing:
			doc_events["Transport Job"][_event] = list(_existing) + [_handler]
	elif _existing != _handler:
		doc_events["Transport Job"][_event] = [_existing, _handler]

merge_credit_hooks(doc_events)

# Scheduled Tasks
# ---------------

scheduler_events = {
	"cron": {
		# Live flight position sync from OpenSky (1 bulk /states/all call per run,
		# well under the free anonymous quota of ~400 req/day).
		"*/10 * * * *": [
			"logistics.air_freight.flight_schedules.tasks.sync_active_flights",
		],
	},
	"hourly": [
		"logistics.status_update.tasks.update_milestone_statuses",
		"logistics.air_freight.flight_schedules.tasks.update_air_freight_jobs_with_flight_status",
		"logistics.integrations.outlook.tasks.reconcile_failed_syncs",
		"logistics.integrations.outlook.tasks.sync_recent_task_changes",
	],
	"daily": [
		"logistics.status_update.tasks.update_document_statuses",
		"logistics.status_update.tasks.update_permit_statuses",
		"logistics.status_update.tasks.update_exemption_statuses",
		"logistics.container_management.api.reconcile_containers_from_terminal_sea_shipments",
		"logistics.air_freight.flight_schedules.tasks.cleanup_old_schedules",
		"logistics.air_freight.flight_schedules.tasks.cleanup_old_sync_logs",
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

user_data_fields = [
	{
		"doctype": "{doctype_1}",
		"filter_by": "{filter_by}",
		"redact_fields": ["{field_1}", "{field_2}"],
		"partial": 1,
	},
	{
		"doctype": "{doctype_2}",
		"filter_by": "{filter_by}",
		"partial": 1,
	},
	{
		"doctype": "{doctype_3}",
		"strict": False,
	},
	{
		"doctype": "{doctype_4}"
	}
]

# Database migrations (after schema sync)
# ---------------------------------------
after_migrate = [
	"logistics.job_management.recognition_migrate.after_migrate",
	"logistics.analytics_reports.sync_cnx_reports.after_migrate",
	"logistics.cash_advance.install.after_migrate",
	"logistics.control_tower.install.after_migrate",
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

apply_internal_job_link_validation_patch()
