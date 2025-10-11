# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from . import __version__ as app_version

app_name = "logistics"
app_title = "Logistics"
app_publisher = "www.agilasoft.com"
app_description = "Logistics"
app_icon = "octicon octicon-file-directory"
app_color = "grey"
app_email = "info@agilasoft.com"
app_license = "MIT"

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/logistics/css/logistics.css"
# app_include_js = "/assets/logistics/js/logistics.js"

# include js, css files in header of web template
# web_include_css = "/assets/logistics/css/logistics.css"
# web_include_js = "/assets/logistics/js/logistics.js"

# Portal Menu Items
# -----------------
portal_menu_items = [
    {
        "title": "Warehousing Portal",
        "route": "/warehousing-portal",
        "reference_doctype": "Warehouse Job",
        "icon": "fa fa-warehouse"
    },
    {
        "title": "Transport Jobs",
        "route": "/transport-jobs",
        "reference_doctype": "Transport Job",
        "icon": "fa fa-truck"
    },
    {
        "title": "Stock Balance",
        "route": "/stock-balance",
        "reference_doctype": "Item",
        "icon": "fa fa-chart-line"
    },
    {
        "title": "Warehouse Jobs",
        "route": "/warehouse-jobs",
        "reference_doctype": "Warehouse Job",
        "icon": "fa fa-tasks"
    }
]

# Portal Page Context
# -------------------
get_portal_page_context = "logistics.transport.portal_config.get_portal_page_context"

# Website Routes
# --------------
website_route_rules = [
    {"from_route": "/simple-test", "to_route": "simple_test"},
    {"from_route": "/customer-debug", "to_route": "customer_debug"},
    {"from_route": "/transport-debug", "to_route": "transport_debug"},
    {"from_route": "/warehousing-test", "to_route": "warehousing_test"},
    {"from_route": "/warehousing-debug", "to_route": "warehousing_debug"},
    {"from_route": "/test-transport", "to_route": "test_portal"},
    {"from_route": "/transport-jobs", "to_route": "transport_jobs"},
    {"from_route": "/stock-balance", "to_route": "stock_balance"},
    {"from_route": "/warehouse-jobs", "to_route": "warehouse_jobs"},
    {"from_route": "/warehousing-portal", "to_route": "warehousing_portal"},
    {"from_route": "/customer-debug-portal", "to_route": "customer_debug_portal"},
    {
        "from_route": "/transport-jobs/<path:name>",
        "to_route": "transport_job_detail",
        "defaults": {"doctype": "Transport Job", "parents": [{"label": "Transport Jobs", "route": "transport-jobs"}]},
    },
]

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
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

# Website user home page (by function)
# get_website_user_home_page = "logistics.utils.get_home_page"

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# Installation
# ------------

# before_install = "logistics.install.before_install"
after_install = "logistics.install.after_install.after_install"

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
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
#	}
# }

# Scheduled Tasks
# ---------------

scheduler_events = {
	"hourly": [
		"logistics.air_freight.flight_schedules.tasks.sync_active_flights",
		"logistics.air_freight.flight_schedules.tasks.update_air_freight_jobs_with_flight_status"
	],
	"daily": [
		"logistics.air_freight.flight_schedules.tasks.sync_airport_master",
		"logistics.air_freight.flight_schedules.tasks.sync_airline_master",
		"logistics.air_freight.flight_schedules.tasks.cleanup_old_schedules"
	],
	"weekly": [
		"logistics.air_freight.flight_schedules.tasks.sync_route_data",
		"logistics.air_freight.flight_schedules.tasks.cleanup_old_sync_logs"
	]
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

doc_events = {
    "Warehouse Job": {
        # keep your existing validate hook(s) if any
        "before_submit": "logistics.warehousing.api.warehouse_job_before_submit",
    },
    "Sales Invoice": {
        "validate": [
            "logistics.setup.dimension_hooks.update_dimensions_on_item_change",
            "logistics.setup.bir_2307_hooks.validate_bir_2307_fields",
            "logistics.setup.bir_2307_hooks.auto_populate_tin_fields",
            "logistics.setup.bir_2307_hooks.auto_populate_atc_details"
        ],
    },
    "Purchase Invoice": {
        "validate": [
            "logistics.setup.dimension_hooks.update_dimensions_on_item_change",
            "logistics.setup.bir_2307_hooks.validate_bir_2307_fields",
            "logistics.setup.bir_2307_hooks.auto_populate_tin_fields",
            "logistics.setup.bir_2307_hooks.auto_populate_atc_details"
        ],
    },
    "Journal Entry": {
        "validate": "logistics.setup.dimension_hooks.update_dimensions_on_item_change",
    },
    "ATC Code": {
        "validate": "logistics.setup.bir_2307_hooks.validate_atc_code",
    }
}
