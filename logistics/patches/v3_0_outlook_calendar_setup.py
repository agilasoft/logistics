# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Seed Microsoft Outlook Connected App skeleton and User opt-in custom fields."""

from __future__ import unicode_literals

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from logistics.integrations.outlook.install import create_connected_app
from logistics.integrations.outlook.utils import OUTLOOK_PROVIDER_NAME

CONNECTED_APP_NAME = OUTLOOK_PROVIDER_NAME


def execute():
	connected_app_name = create_connected_app()
	_create_user_custom_fields()
	_create_default_settings(connected_app_name)
	frappe.clear_cache(doctype="User")
	frappe.db.commit()


def _create_user_custom_fields():
	create_custom_fields(
		{
			"User": [
				{
					"fieldname": "outlook_calendar_section",
					"fieldtype": "Section Break",
					"label": "Outlook Calendar Sync",
					"insert_after": "time_zone",
					"collapsible": 1,
				},
				{
					"fieldname": "sync_erpnext_tasks_to_outlook",
					"fieldtype": "Check",
					"label": "Sync ERPNext Tasks to Outlook",
					"default": "0",
					"description": "When enabled, all ERPNext Tasks with expected dates sync to your Outlook calendar.",
					"insert_after": "outlook_calendar_section",
				},
			]
		},
		update=True,
	)


def _create_default_settings(connected_app_name: str):
	if frappe.db.exists("Outlook Calendar Settings", "Outlook Calendar Settings"):
		frappe.db.set_value(
			"Outlook Calendar Settings",
			"Outlook Calendar Settings",
			"connected_app",
			connected_app_name,
			update_modified=False,
		)
		return

	doc = frappe.new_doc("Outlook Calendar Settings")
	doc.enable_sync = 0
	doc.connected_app = connected_app_name
	doc.azure_tenant_id = "common"
	doc.sync_on_save = 1
	doc.delete_outlook_event_on_task_delete = 1
	doc.mark_completed_tasks_as_free = 1
	doc.insert(ignore_permissions=True)
