# Copyright (c) 2026, www.agilasoft.com and contributors
# License: MIT. See LICENSE

"""
Rename DocType Job Costing Number → Job Number and align ERPNext Accounting Dimension.

Runs before model sync so `bench migrate` loads the new doctype path (`job_number`).
"""

import frappe

_OLD_DT = "Job Costing Number"
_NEW_DT = "Job Number"
_OLD_AD = "Job Costing Number"
_NEW_AD = "Job Number"


def execute():
	if frappe.db.exists("DocType", _OLD_DT) and not frappe.db.exists("DocType", _NEW_DT):
		frappe.rename_doc(
			"DocType",
			_OLD_DT,
			_NEW_DT,
			force=True,
			merge=False,
		)
		frappe.db.commit()

	_sync_accounting_dimension()
	return True


def _sync_accounting_dimension():
	if frappe.db.exists("Accounting Dimension", _OLD_AD) and not frappe.db.exists(
		"Accounting Dimension", _NEW_AD
	):
		frappe.rename_doc(
			"Accounting Dimension",
			_OLD_AD,
			_NEW_AD,
			force=True,
			merge=False,
		)
		frappe.db.commit()

	if frappe.db.exists("Accounting Dimension", _NEW_AD):
		ad = frappe.get_doc("Accounting Dimension", _NEW_AD)
		if ad.document_type != _NEW_DT:
			ad.db_set("document_type", _NEW_DT, update_modified=False)
			frappe.db.commit()
