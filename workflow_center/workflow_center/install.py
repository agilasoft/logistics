# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from workflow_center.sla import WORKFLOW_STATE_SLA_FIELDS


def after_install():
	if not frappe.db.exists("Workflow Center Settings"):
		doc = frappe.get_doc({"doctype": "Workflow Center Settings", "enabled": 1})
		doc.insert(ignore_permissions=True)
	ensure_workflow_state_sla_fields()


def ensure_workflow_state_sla_fields():
	if not frappe.db.exists("DocType", "Workflow State"):
		return
	create_custom_fields({"Workflow State": WORKFLOW_STATE_SLA_FIELDS}, update=True)
	frappe.clear_cache(doctype="Workflow State")
