# -*- coding: utf-8 -*-
from __future__ import unicode_literals

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

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
app_include_css = "/assets/logistics/css/print_footer_fix.css"
app_include_js = [
	"/assets/logistics/js/charge_break_dialogs.js",
	"/assets/logistics/js/volume_from_dimensions.js",
	"/assets/logistics/js/document_alerts_dialog.js?v=2",
	"/assets/logistics/js/documents_tab_utils.js",
	"/assets/logistics/js/profitability_form.js?v=4",
	"/assets/logistics/js/purchase_invoice_dialog.js",
	"/assets/logistics/js/sales_invoice_dialog.js",
]

# include js, css files in header of web template
# web_include_css = "/assets/logistics/css/logistics.css"
# web_include_js = "/assets/logistics/js/logistics.js"

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
doctype_js = {
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
		"logistics/air_freight/doctype/air_booking_packages/air_booking_packages.js",
		"logistics/public/js/charge_break_dialogs.js",
		"logistics/public/js/document_alerts_dialog.js",
		"logistics/air_freight/doctype/air_booking_charges/air_booking_charges.js",
		"logistics/public/js/charge_break_buttons.js",
	],
	"Air Shipment": [
		"logistics/air_freight/doctype/air_booking_packages/air_booking_packages.js",
		"logistics/public/js/charge_break_dialogs.js",
		"logistics/public/js/document_alerts_dialog.js",
		"logistics/air_freight/doctype/air_shipment_charges/air_shipment_charges.js",
		"logistics/public/js/charge_break_buttons.js",
		"logistics/public/js/profitability_form.js",
		"logistics/public/js/purchase_invoice_dialog.js",
		"logistics/job_management/recognition_client.js",
		"logistics/job_management/recognition_policy_fields.js",
	],
	"Air Consolidation": [
		"logistics/public/js/charge_break_dialogs.js",
		"logistics/public/js/document_alerts_dialog.js",
		"logistics/public/js/charge_break_buttons.js",
	],
	"Sea Booking": [
		"logistics/air_freight/doctype/air_booking_packages/air_booking_packages.js",
		"logistics/public/js/charge_break_dialogs.js",
		"logistics/public/js/document_alerts_dialog.js",
		"logistics/sea_freight/doctype/sea_booking_charges/sea_booking_charges.js",
		"logistics/public/js/charge_break_buttons.js",
	],
	"Sea Shipment": [
		"logistics/air_freight/doctype/air_booking_packages/air_booking_packages.js",
		"logistics/public/js/purchase_invoice_dialog.js",
		"logistics/public/js/charge_break_dialogs.js",
		"logistics/public/js/document_alerts_dialog.js",
		"logistics/sea_freight/doctype/sea_shipment_charges/sea_shipment_charges.js",
		"logistics/public/js/charge_break_buttons.js",
		"logistics/public/js/profitability_form.js",
		"logistics/job_management/recognition_client.js",
		"logistics/job_management/recognition_policy_fields.js",
	],
	"Sea Consolidation": [
		"logistics/public/js/charge_break_dialogs.js",
		"logistics/public/js/document_alerts_dialog.js",
		"logistics/public/js/charge_break_buttons.js",
	],
	"Declaration": [
		"logistics/public/js/charge_break_dialogs.js",
		"logistics/public/js/document_alerts_dialog.js",
		"logistics/customs/doctype/declaration_charges/declaration_charges.js",
		"logistics/public/js/charge_break_buttons.js",
		"logistics/public/js/profitability_form.js",
		"logistics/public/js/purchase_invoice_dialog.js",
		"logistics/job_management/recognition_client.js",
		"logistics/job_management/recognition_policy_fields.js",
	],
	"Declaration Order": [
		"logistics/public/js/charge_break_dialogs.js",
		"logistics/public/js/document_alerts_dialog.js",
		"logistics/customs/doctype/declaration_order_charges/declaration_order_charges.js",
		"logistics/public/js/charge_break_buttons.js",
	],
	"Transport Order": [
		"logistics/air_freight/doctype/air_booking_packages/air_booking_packages.js",
		"logistics/public/js/charge_break_dialogs.js",
		"logistics/public/js/document_alerts_dialog.js",
		"logistics/pricing_center/doctype/transport_order_charges/transport_order_charges.js",
		"logistics/public/js/charge_break_buttons.js",
	],
	"Transport Job": [
		"logistics/air_freight/doctype/air_booking_packages/air_booking_packages.js",
		"logistics/public/js/charge_break_dialogs.js",
		"logistics/public/js/document_alerts_dialog.js",
		"logistics/public/js/purchase_invoice_dialog.js",
		"logistics/pricing_center/doctype/transport_job_charges/transport_job_charges.js",
		"logistics/public/js/charge_break_buttons.js",
		"logistics/public/js/profitability_form.js",
		"logistics/job_management/recognition_client.js",
		"logistics/job_management/recognition_policy_fields.js",
	],
	"Transport Consolidation": [
		"logistics/public/js/document_alerts_dialog.js",
	],
	"Warehouse Job": [
		"logistics/public/js/purchase_invoice_dialog.js",
		"logistics/public/js/profitability_form.js",
		"logistics/job_management/recognition_client.js",
		"logistics/job_management/recognition_policy_fields.js",
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
	"Accounting Dimension": {
		"after_insert": "logistics.job_management.gl_item_dimension.on_accounting_dimension_changed",
		"on_update": "logistics.job_management.gl_item_dimension.on_accounting_dimension_changed",
		"on_trash": "logistics.job_management.gl_item_dimension.on_accounting_dimension_changed",
	},
	"Account": {
		"validate": "logistics.logistics.account_job_profit.validate_account_job_profit",
	},
	"Purchase Invoice": {
		"validate": "logistics.invoice_integration.gl_item_dimension_sync.sync_item_accounting_dimension_from_invoice_items",
		"before_submit": "logistics.invoice_integration.gl_item_dimension_sync.sync_item_accounting_dimension_from_invoice_items",
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
	}
	# Exclude Declaration Order from automatic on_update hook to prevent timestamp mismatches
	# Declaration Order uses user-initiated template population (like Air Booking and Sea Booking)
	if _dt != "Declaration Order":
		doc_events[_dt]["on_update"] = "logistics.document_management.api.ensure_documents_and_milestones_from_template"

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
after_migrate = ["logistics.job_management.recognition_migrate.after_migrate"]

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
