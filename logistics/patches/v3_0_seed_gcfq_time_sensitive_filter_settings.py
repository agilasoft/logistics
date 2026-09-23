# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""Append Time Sensitive Case GCFQ filter rows on sites that already have settings seeded."""

from __future__ import annotations

import frappe

_GCFQ_SETTINGS_DOCTYPE = "Get Charges from Quotation Settings"
_JOB_DOCTYPE = "Time Sensitive Case"


def execute():
	if not frappe.db.exists("DocType", _GCFQ_SETTINGS_DOCTYPE):
		return
	from logistics.utils.get_charges_from_quotation import (
		GCFQ_FILTER_CATALOG,
		seed_gcfq_filter_settings_if_empty,
	)

	seed_gcfq_filter_settings_if_empty()
	catalog = list(GCFQ_FILTER_CATALOG.get(_JOB_DOCTYPE, ()))
	if not catalog:
		return

	doc = frappe.get_single(_GCFQ_SETTINGS_DOCTYPE)
	existing = {
		((r.job_doctype or "").strip(), (r.filter_key or "").strip())
		for r in (doc.filter_settings or [])
	}
	added = False
	for entry in catalog:
		key = (entry.get("key") or "").strip()
		if not key or (_JOB_DOCTYPE, key) in existing:
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
