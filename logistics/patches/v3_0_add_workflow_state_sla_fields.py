# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Add Workflow Center SLA fields on Workflow State.

The dashboard reads wc_sla_enabled, wc_sla_unit, and wc_sla_value. Sites that
loaded Workflow Center before these fields existed failed with
Unknown column 'wc_sla_enabled'.
"""

from __future__ import unicode_literals

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields

from logistics.workflow_center.sla import WORKFLOW_STATE_SLA_FIELDS


def execute():
	if not frappe.db.exists("DocType", "Workflow State"):
		return

	create_custom_fields({"Workflow State": WORKFLOW_STATE_SLA_FIELDS}, update=True)
	frappe.clear_cache(doctype="Workflow State")
