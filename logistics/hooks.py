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
]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_css = [
	"/assets/logistics/css/print_footer_fix.css",
	"/assets/logistics/css/get_charges_from_quotation.css?v=5",
	"/assets/logistics/css/charges_grid_no_row_check.css?v=2",
]
app_include_js = [
	"/assets/logistics/js/grid_cannot_add_rows_toolbar_fix.js",
	# Desk-wide: form refresh can run before doctype_js bundles finish; define dialog globals early.
	"/assets/logistics/js/internal_job_create_from_source.js?v=17",
	"/assets/logistics/js/one_off_sales_quote_order_standard.js",
	"/assets/logistics/js/main_service_internal_job_mutual_exclusive.js?v=7",
	"/assets/logistics/js/get_charges_from_quotation.js?v=8",
	"/assets/logistics/js/charges_disbursement_sync.js",
	"/assets/logistics/js/charge_break_dialogs.js",
	"/assets/logistics/js/volume_from_dimensions.js",
	"/assets/logistics/js/document_alerts_dialog.js?v=2",
	"/assets/logistics/js/documents_tab_utils.js",
	"/assets/logistics/js/profitability_form.js?v=4",
	"/assets/logistics/js/purchase_invoice_dialog.js",
	"/assets/logistics/js/sales_invoice_dialog.js",
	"/assets/logistics/js/sales_invoice_job_dimension_cleanup.js",
]

# include js, css files in header of web template
# web_include_css = "/assets/logistics/css/logistics.css"
# web_include_js = "/assets/logistics/js/logistics.js"

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
	"Internal Job Detail": "logistics/logistics/doctype/internal_job_detail/internal_job_detail.js",
	"Container": "logistics/logistics/doctype/container/container.js",
	"UNLOCO": [
		"logistics/logistics/doctype/unloco/unloco.js",
		"logistics/logistics/doctype/unloco/unloco_list.js",
	],
	# Sales Quote: dialogs first, then air/sea freight scripts
	"Sales Quote": [
		"logistics/public/js/charge_break_dialogs.js",
		"logistics/pricing_center/doctype/sales_quote_charge/sales_quote_charge.js",
		"logistics/pricing_center/doctype/sales_quote_air_freight/sales_quote_air_freight.js",
		"logistics/pricing_center/doctype/sales_quote_sea_freight/sales_quote_sea_freight.js",
	],
	# Charge parent doctypes: dialogs first, then charge script + handlers
	# Air Booking Packages script first so logistics_calculate_volume_from_dimensions is defined before form handlers run
	"Air Booking": [
		"logistics/public/js/routing_leg_transport_mode_flags.js",
		"logistics/public/js/shipper_consignee_defaults.js",
		"logistics/air_freight/doctype/air_booking_packages/air_booking_packages.js",
		"logistics/public/js/charge_break_dialogs.js",
		"logistics/public/js/document_alerts_dialog.js",
		"logistics/air_freight/doctype/air_booking_charges/air_booking_charges.js",
		"logistics/public/js/charge_break_buttons.js",
		# Same Get Charges from Quotation UI as Sea Booking / Transport Order (list criteria, search, cards, Apply).
		"logistics/public/js/get_charges_from_quotation.js",
	],
	"Air Shipment": [
		"logistics/public/js/routing_leg_transport_mode_flags.js",
		"logistics/public/js/internal_job_create_from_source.js",
		"logistics/public/js/shipper_consignee_defaults.js",
		"logistics/air_freight/doctype/air_booking_packages/air_booking_packages.js",
		"logistics/public/js/charge_break_dialogs.js",
		"logistics/public/js/document_alerts_dialog.js",
		"logistics/air_freight/doctype/air_shipment_charges/air_shipment_charges.js",
		"logistics/public/js/charge_break_buttons.js",
		"logistics/public/js/profitability_form.js",
		"logistics/public/js/purchase_invoice_dialog.js",
		"logistics/job_management/recognition_client.js",
		"logistics/job_management/recognition_policy_fields.js",
		"logistics/job_management/job_charge_reopen.js",
	],
	"Air Consolidation": [
		"logistics/public/js/charge_break_dialogs.js",
		"logistics/public/js/document_alerts_dialog.js",
		"logistics/public/js/charge_break_buttons.js",
	],
	"Sea Booking": [
		"logistics/public/js/routing_leg_transport_mode_flags.js",
		"logistics/public/js/sea_freight_accounting_defaults.js",
		"logistics/public/js/shipper_consignee_defaults.js",
		"logistics/air_freight/doctype/air_booking_packages/air_booking_packages.js",
		"logistics/public/js/charge_break_dialogs.js",
		"logistics/public/js/document_alerts_dialog.js",
		"logistics/sea_freight/doctype/sea_booking_charges/sea_booking_charges.js",
		"logistics/public/js/charge_break_buttons.js",
	],
	"Sea Shipment": [
		"logistics/public/js/routing_leg_transport_mode_flags.js",
		"logistics/public/js/internal_job_create_from_source.js",
		"logistics/public/js/sea_freight_accounting_defaults.js",
		"logistics/public/js/shipper_consignee_defaults.js",
		"logistics/air_freight/doctype/air_booking_packages/air_booking_packages.js",
		"logistics/public/js/purchase_invoice_dialog.js",
		"logistics/public/js/charge_break_dialogs.js",
		"logistics/public/js/document_alerts_dialog.js",
		"logistics/sea_freight/doctype/sea_shipment_charges/sea_shipment_charges.js",
		"logistics/public/js/charge_break_buttons.js",
		"logistics/public/js/profitability_form.js",
		"logistics/job_management/recognition_client.js",
		"logistics/job_management/recognition_policy_fields.js",
		"logistics/job_management/job_charge_reopen.js",
	],
	"Sea Consolidation": [
		"logistics/public/js/charge_break_dialogs.js",
		"logistics/public/js/document_alerts_dialog.js",
		"logistics/public/js/charge_break_buttons.js",
	],
	"Declaration": [
		"logistics/public/js/internal_job_create_from_source.js",
		"logistics/public/js/transport_mode_default_document_type.js",
		"logistics/public/js/shipper_consignee_defaults.js",
		"logistics/public/js/sales_invoice_dialog.js",
		"logistics/public/js/purchase_invoice_dialog.js",
		"logistics/public/js/charge_break_dialogs.js",
		"logistics/public/js/document_alerts_dialog.js",
		"logistics/customs/doctype/declaration_charges/declaration_charges.js",
		"logistics/public/js/charge_break_buttons.js",
		"logistics/public/js/profitability_form.js",
		"logistics/job_management/recognition_client.js",
		"logistics/job_management/recognition_policy_fields.js",
		"logistics/job_management/job_charge_reopen.js",
	],
	"Declaration Order": [
		"logistics/public/js/transport_mode_default_document_type.js",
		"logistics/public/js/shipper_consignee_defaults.js",
		"logistics/public/js/charge_break_dialogs.js",
		"logistics/public/js/document_alerts_dialog.js",
		"logistics/customs/doctype/declaration_order_charges/declaration_order_charges.js",
		"logistics/public/js/charge_break_buttons.js",
		# Same Get Charges from Quotation UI as Air / Sea / Transport (list, preview, Apply).
		"logistics/public/js/get_charges_from_quotation.js",
	],
	"Transport Order": [
		"logistics/public/js/shipper_consignee_defaults.js",
		"logistics/air_freight/doctype/air_booking_packages/air_booking_packages.js",
		"logistics/public/js/charge_break_dialogs.js",
		"logistics/public/js/document_alerts_dialog.js",
		"logistics/pricing_center/doctype/transport_order_charges/transport_order_charges.js",
		"logistics/public/js/charge_break_buttons.js",
	],
	"Transport Job": [
		"logistics/public/js/internal_job_create_from_source.js",
		"logistics/public/js/shipper_consignee_defaults.js",
		"logistics/air_freight/doctype/air_booking_packages/air_booking_packages.js",
		"logistics/public/js/charge_break_dialogs.js",
		"logistics/public/js/document_alerts_dialog.js",
		"logistics/public/js/purchase_invoice_dialog.js",
		"logistics/pricing_center/doctype/transport_job_charges/transport_job_charges.js",
		"logistics/public/js/charge_break_buttons.js",
		"logistics/public/js/profitability_form.js",
		"logistics/job_management/recognition_client.js",
		"logistics/job_management/recognition_policy_fields.js",
		"logistics/job_management/job_charge_reopen.js",
	],
	"Transport Consolidation": [
		"logistics/public/js/document_alerts_dialog.js",
	],
	"Warehouse Job": [
		"logistics/public/js/purchase_invoice_dialog.js",
		"logistics/public/js/profitability_form.js",
		"logistics/job_management/recognition_client.js",
		"logistics/job_management/recognition_policy_fields.js",
		"logistics/job_management/job_charge_reopen.js",
	],
	"Warehouse Contract": [
		"logistics/public/js/charge_break_dialogs.js",
	],
	"General Job": [
		"logistics/public/js/profitability_form.js",
		"logistics/job_management/recognition_client.js",
		"logistics/job_management/recognition_policy_fields.js",
	],
	"Special Project": [
		"logistics/public/js/document_alerts_dialog.js",
	],
	"Account": "logistics/public/js/account_job_profit.js",
	"Recognition Policy Settings": "logistics/job_management/doctype/recognition_policy_settings/recognition_policy_settings.js",
	"Credit Hold Lift Request": "logistics/logistics/doctype/credit_hold_lift_request/credit_hold_lift_request.js",
	"Cash Advance Request": "logistics/cash_advance/doctype/cash_advance_request/cash_advance_request.js",
	"Cash Advance Liquidation": "logistics/cash_advance/doctype/cash_advance_liquidation/cash_advance_liquidation.js",
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

# before_install = "logistics.install.before_install"
# after_install = "logistics.install.after_install"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "logistics.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
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
	"Inbound Order", "Release Order", "Transfer Order",
	"Warehouse Job", "General Job", "Special Project",
]

doc_events = {
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
	"Account": {
		"validate": "logistics.logistics.account_job_profit.validate_account_job_profit",
	},
	"Purchase Invoice": {
		"validate": [
			"logistics.invoice_integration.container_deposit_pi.apply_container_deposit_expense_account",
			"logistics.invoice_integration.container_deposit_dimensions.sync_container_deposit_pi_accounting_dimensions",
			"logistics.invoice_integration.gl_item_dimension_sync.sync_item_accounting_dimension_from_invoice_items",
		],
		"before_submit": [
			"logistics.invoice_integration.container_deposit_pi.apply_container_deposit_expense_account",
			"logistics.invoice_integration.container_deposit_dimensions.sync_container_deposit_pi_accounting_dimensions",
			"logistics.invoice_integration.gl_item_dimension_sync.sync_item_accounting_dimension_from_invoice_items",
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
}
for _dt in _doc_milestone_doctypes:
	doc_events[_dt] = {
		"before_save": [
			"logistics.document_management.api.update_milestone_status_on_parent_before_save",
			"logistics.document_management.api.update_job_document_status_on_parent_before_save",
		],
		"before_submit": "logistics.document_management.api.enforce_required_job_documents_before_submit",
	}
	# Exclude Declaration Order from automatic on_update hook to prevent timestamp mismatches
	# Declaration Order uses user-initiated template population (like Air Booking and Sea Booking)
	if _dt != "Declaration Order":
		doc_events[_dt]["on_update"] = "logistics.document_management.api.ensure_documents_and_milestones_from_template"

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
	"Inbound Order",
	"Release Order",
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

merge_credit_hooks(doc_events)

# Scheduled Tasks
# ---------------

scheduler_events = {
	"hourly": [
		"logistics.status_update.tasks.update_milestone_statuses",
	],
	"daily": [
		"logistics.status_update.tasks.update_document_statuses",
		"logistics.status_update.tasks.update_permit_statuses",
		"logistics.status_update.tasks.update_exemption_statuses",
		"logistics.container_management.api.reconcile_containers_from_terminal_sea_shipments",
	],
}

# Testing
# -------

# before_tests = "logistics.install.before_tests"

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "logistics.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "logistics.task.get_dashboard_data"
# }

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
]

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
