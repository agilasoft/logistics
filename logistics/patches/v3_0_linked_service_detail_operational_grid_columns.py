# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Linked Service Detail grid: canvas columns, not the two-column SQ layout.

Operational / CR / TSC grids show Linked Service, Service Type, Order No,
Job No, and Job Description. Job Type stays off the grid. Sales Quote hides
the extra columns in client JS (``apply_sales_quote_linked_services_columns``).
"""

from __future__ import unicode_literals

import frappe

_DOCTYPE = "Linked Service Detail"
_KEEP = (
	"linked_service",
	"service_type",
	"order_no",
	"job_no",
	"job_description",
)
_DROP = ("job_type",)


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
