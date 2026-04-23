# Copyright (c) 2026, www.agilasoft.com and contributors
# License: MIT. See LICENSE

"""
When both Accounting Dimensions **Job Number** and **Job Costing Number** exist (e.g. after
partial renames), Sales Invoice shows two fields. Remove the legacy dimension and any
remaining ``job_costing_number`` custom fields on Sales Invoice / Sales Invoice Item, then
re-apply the Job Number dimension so layout stays consistent.
"""

import frappe

_DT_SI = "Sales Invoice"
_DT_SII = "Sales Invoice Item"
_STALE_AD = "Job Costing Number"


def execute():
	from erpnext.accounts.doctype.accounting_dimension.accounting_dimension import (
		delete_accounting_dimension,
		make_dimension_in_accounting_doctypes,
	)

	if frappe.db.exists("Accounting Dimension", "Job Number") and frappe.db.exists(
		"Accounting Dimension", _STALE_AD
	):
		stale = frappe.get_doc("Accounting Dimension", _STALE_AD)
		delete_accounting_dimension(stale)
		frappe.delete_doc(
			"Accounting Dimension",
			stale.name,
			force=True,
			ignore_permissions=True,
			ignore_on_trash=True,
			delete_permanently=True,
		)
		frappe.db.commit()

	# Do not strip job_costing_number custom fields if "Job Costing Number" is still the only
	# active dimension (sites not yet on Job Number).
	remove_jcn_custom_fields = frappe.db.exists(
		"Accounting Dimension", "Job Number"
	) or not frappe.db.exists("Accounting Dimension", _STALE_AD)
	if remove_jcn_custom_fields:
		for dt in (_DT_SI, _DT_SII):
			for cf in frappe.get_all(
				"Custom Field",
				filters={"dt": dt, "fieldname": "job_costing_number"},
				pluck="name",
			):
				frappe.delete_doc("Custom Field", cf, force=True, ignore_permissions=True)
			legacy_cf = f"{dt}-job_costing_number"
			if frappe.db.exists("Custom Field", legacy_cf):
				frappe.delete_doc("Custom Field", legacy_cf, force=True, ignore_permissions=True)

		frappe.db.sql(
			"""
			DELETE FROM `tabProperty Setter`
			WHERE doc_type IN (%s, %s) AND field_name = 'job_costing_number'
			""",
			(_DT_SI, _DT_SII),
		)
		frappe.db.commit()

	if frappe.db.exists("Accounting Dimension", "Job Number"):
		doc = frappe.get_doc("Accounting Dimension", "Job Number")
		make_dimension_in_accounting_doctypes(doc=doc)
		frappe.db.commit()

	frappe.clear_cache(doctype=_DT_SI)
	frappe.clear_cache(doctype=_DT_SII)
	return True
