# Copyright (c) 2026, Agilasoft and contributors
"""Ensure Table MultiSelect option doctypes (e.g. on charge child rows) are loaded in meta bundles."""

from __future__ import annotations


def apply_recursive_meta_bundle_patch() -> None:
	"""Extend ``get_meta_bundle`` so nested Table / Table MultiSelect doctypes are included."""
	import frappe
	import frappe.desk.form.load as form_load

	if getattr(form_load, "_logistics_recursive_meta_bundle", False):
		return

	_original = form_load.get_meta_bundle

	def get_meta_bundle(doctype: str):
		from frappe.desk.form import meta as form_meta

		bundle = []
		queue = [doctype]
		seen: set[str] = set()
		while queue:
			dt = queue.pop(0)
			if not dt or dt in seen:
				continue
			seen.add(dt)
			bundle.append(form_meta.get_meta(dt))
			for df in bundle[-1].fields:
				if df.fieldtype in frappe.model.table_fields and df.options:
					queue.append(df.options)
		return bundle

	form_load.get_meta_bundle = get_meta_bundle
	form_load._logistics_recursive_meta_bundle = True


def extend_bootinfo_with_specified_charges_meta(bootinfo) -> None:
	"""Preload istable meta used by charge-row Table MultiSelect fields (desk boot)."""
	from frappe.desk.form.load import get_meta_bundle

	names = {getattr(d, "name", None) for d in bootinfo.docs}
	for dt in ("Charge Specified Item", "Charge Specified Charge Group"):
		if dt in names:
			continue
		for doc in get_meta_bundle(dt):
			if doc.name not in names:
				bootinfo.docs.append(doc)
				names.add(doc.name)
