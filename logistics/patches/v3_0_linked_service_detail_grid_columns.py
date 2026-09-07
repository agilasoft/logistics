# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Services grid columns: Linked Service + Service Type only.

Job Type / Order No / Job No / Job Description stay on the child DocType for
the row form and virtual view, but must not appear as ``in_list_view`` columns.
Customize Form Property Setters can pin the old six-column layout after JSON
sync, so this patch reloads the DocType, drops those setters, and writes DocField.
"""

from __future__ import unicode_literals

import frappe

_DOCTYPE = "Linked Service Detail"
_KEEP = ("linked_service", "service_type")
_DROP = ("job_type", "order_no", "job_no", "job_description")


def execute():
	if not frappe.db.exists("DocType", _DOCTYPE):
		return

	frappe.reload_doc("logistics", "doctype", "linked_service_detail", force=True)

	_clear_in_list_view_property_setters()
	_sync_in_list_view()

	frappe.clear_cache(doctype=_DOCTYPE)
	frappe.db.commit()


def _clear_in_list_view_property_setters():
	names = frappe.get_all(
		"Property Setter",
		filters={
			"doc_type": _DOCTYPE,
			"field_name": ["in", list(_KEEP + _DROP)],
			"property": "in_list_view",
		},
		pluck="name",
	)
	for name in names:
		frappe.delete_doc("Property Setter", name, force=1, ignore_permissions=True)


def _sync_in_list_view():
	for fieldname in _KEEP:
		_set_in_list_view(fieldname, 1)
	for fieldname in _DROP:
		_set_in_list_view(fieldname, 0)


def _set_in_list_view(fieldname, value):
	row_name = frappe.db.get_value(
		"DocField",
		{"parent": _DOCTYPE, "fieldname": fieldname},
		"name",
	)
	if not row_name:
		return
	frappe.db.set_value("DocField", row_name, "in_list_view", value, update_modified=False)
