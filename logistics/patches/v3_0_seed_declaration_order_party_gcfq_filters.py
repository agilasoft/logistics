# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Add Shipper and Consignee to Declaration Order Get Charges from Quotation filters."""

from __future__ import annotations

import frappe

_GCFQ_SETTINGS_DOCTYPE = "Get Charges from Quotation Settings"
_JOB_DOCTYPE = "Declaration Order"
_KEYS = ("shipper", "consignee")


def execute():
	if not frappe.db.exists("DocType", _GCFQ_SETTINGS_DOCTYPE):
		return
	from logistics.utils.get_charges_from_quotation import seed_gcfq_filter_settings_if_empty

	seed_gcfq_filter_settings_if_empty()
	doc = frappe.get_single(_GCFQ_SETTINGS_DOCTYPE)
	existing = {
		((r.job_doctype or "").strip(), (r.filter_key or "").strip())
		for r in (doc.filter_settings or [])
	}
	added = False
	for key in _KEYS:
		if (_JOB_DOCTYPE, key) in existing:
			continue
		doc.append(
			"filter_settings",
			{
				"job_doctype": _JOB_DOCTYPE,
				"filter_key": key,
				"enabled": 1,
				"editable": 1,
			},
		)
		existing.add((_JOB_DOCTYPE, key))
		added = True
	if added:
		doc.save(ignore_permissions=True)
		frappe.clear_cache(doctype=_GCFQ_SETTINGS_DOCTYPE)
