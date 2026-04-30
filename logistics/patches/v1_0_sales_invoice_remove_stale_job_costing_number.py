# Copyright (c) 2026, www.agilasoft.com and contributors
# License: MIT. See LICENSE

"""
Remove legacy ``job_costing_number`` on Sales Invoice (and line items) where it still
exists after restores or DB copies. Job Number is the accounting dimension field
(``job_number``) and must not duplicate the old dimension name.

Also drops Property Setters still targeting ``job_costing_number`` on those doctypes,
then re-applies the Job Number dimension so ERPNext (re)creates the dimension field
cleanly when needed (same pattern as Purchase Invoice).
"""

import frappe

_DT_SALES_INVOICE = "Sales Invoice"
_DT_SALES_INVOICE_ITEM = "Sales Invoice Item"


def execute():
	for dt in (_DT_SALES_INVOICE, _DT_SALES_INVOICE_ITEM):
		for cf in frappe.get_all(
			"Custom Field",
			filters={"dt": dt, "fieldname": "job_costing_number"},
			pluck="name",
		):
			frappe.delete_doc("Custom Field", cf, force=True, ignore_permissions=True)

	legacy_name = f"{dt}-job_costing_number"
	if frappe.db.exists("Custom Field", legacy_name):
		frappe.delete_doc("Custom Field", legacy_name, force=True, ignore_permissions=True)

	frappe.db.sql(
		"""
		DELETE FROM `tabProperty Setter`
		WHERE doc_type IN (%s, %s) AND field_name = 'job_costing_number'
		""",
		(_DT_SALES_INVOICE, _DT_SALES_INVOICE_ITEM),
	)

	frappe.db.commit()

	dim_name = None
	if frappe.db.exists("Accounting Dimension", "Job Number"):
		dim_name = "Job Number"
	elif frappe.db.exists("Accounting Dimension", "Job Costing Number"):
		dim_name = "Job Costing Number"

	if dim_name:
		from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
			make_dimension_in_accounting_doctypes,
		)

		doc = frappe.get_doc("Accounting Dimension", dim_name)
		make_dimension_in_accounting_doctypes(doc=doc)
		frappe.db.commit()

	frappe.clear_cache(doctype=_DT_SALES_INVOICE)
	frappe.clear_cache(doctype=_DT_SALES_INVOICE_ITEM)
	return True
