# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and Contributors
"""Remove desk overrides on UNLOCO Function-mapped checkboxes.

Customize Form / Property Setter can pin old descriptions (e.g. \"Has road transport facilities\")
and insert_after, so the form and DocType Editor no longer match ``unloco.json``. App JSON is
the source of truth for these standard fields.
"""

import frappe


_HAS_FIELDNAMES = (
	"has_post",
	"has_customs",
	"has_unload",
	"has_airport",
	"has_rail",
	"has_road",
	"has_store",
	"has_terminal",
	"has_discharge",
	"has_seaport",
	"has_outport",
)

_PROPS = ("description", "insert_after", "label")


def execute():
	if not frappe.db.exists("DocType", "UNLOCO"):
		return

	names = frappe.get_all(
		"Property Setter",
		filters={
			"doc_type": "UNLOCO",
			"field_name": ["in", _HAS_FIELDNAMES],
			"property": ["in", _PROPS],
		},
		pluck="name",
	)
	for name in names:
		frappe.delete_doc("Property Setter", name, force=True, ignore_missing=True)

	# Re-sync DocField rows from app JSON (covers sites where DB drifted from git).
	frappe.reload_doc("logistics", "doctype", "unloco")
	frappe.clear_cache(doctype="UNLOCO")
