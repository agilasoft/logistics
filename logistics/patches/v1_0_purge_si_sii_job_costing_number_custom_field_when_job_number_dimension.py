# Copyright (c) 2026, www.agilasoft.com and contributors
# License: MIT. See LICENSE

"""
Remove the legacy **job_costing_number** custom field from **Sales Invoice** and **Sales Invoice Item**
when the **Job Number** accounting dimension is present. That duplicate field is what keeps the
"Job Costing Number" label / broken Link to the removed DocType on the form.

Idempotent. Safe to skip when only the old dimension exists (no Job Number AD).
"""

import frappe

_DT_SI = "Sales Invoice"
_DT_SII = "Sales Invoice Item"


def execute():
	if not frappe.db.exists("Accounting Dimension", "Job Number"):
		return True

	for dt in (_DT_SI, _DT_SII):
		for cf in frappe.get_all(
			"Custom Field",
			filters={"dt": dt, "fieldname": "job_costing_number"},
			pluck="name",
		):
			frappe.delete_doc("Custom Field", cf, force=True, ignore_permissions=True)
		legacy = f"{dt}-job_costing_number"
		if frappe.db.exists("Custom Field", legacy):
			frappe.delete_doc("Custom Field", legacy, force=True, ignore_permissions=True)

	frappe.db.sql(
		"""
		DELETE FROM `tabProperty Setter`
		WHERE doc_type IN (%s, %s) AND field_name = 'job_costing_number'
		""",
		(_DT_SI, _DT_SII),
	)
	frappe.db.commit()

	from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
		make_dimension_in_accounting_doctypes,
	)

	doc = frappe.get_doc("Accounting Dimension", "Job Number")
	make_dimension_in_accounting_doctypes(doc=doc)
	frappe.db.commit()

	frappe.clear_cache(doctype=_DT_SI)
	frappe.clear_cache(doctype=_DT_SII)
	return True
