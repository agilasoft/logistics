# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Fix Declarations stuck with job_status=Draft after submit.

sync_declaration_job_status previously ran in validate before before_submit
flipped customs status Draft→Submitted, leaving job_status as Draft.
"""

from __future__ import unicode_literals

import frappe

from logistics.job_management.logistics_job_status import sync_declaration_job_status


def execute():
	if not frappe.db.has_column("Declaration", "job_status"):
		return

	names = frappe.db.sql(
		"""
		SELECT name FROM `tabDeclaration`
		WHERE docstatus = 1
		  AND IFNULL(job_status, '') IN ('', 'Draft')
		""",
		pluck=True,
	)
	for i, name in enumerate(names):
		doc = frappe.get_doc("Declaration", name)
		before = (getattr(doc, "job_status", None) or "").strip()
		sync_declaration_job_status(doc)
		after = (getattr(doc, "job_status", None) or "").strip()
		if after and after != before:
			frappe.db.set_value("Declaration", name, "job_status", after, update_modified=False)
		if i % 100 == 99:
			frappe.db.commit()
	frappe.db.commit()
