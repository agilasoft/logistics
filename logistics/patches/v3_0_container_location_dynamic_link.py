# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Align Container location fields with Logistics Dynamic Link pattern.

- Location Type: Link to DocType (UNLOCO / Transport Zone)
- Current / Return Location: Dynamic Link scoped by type field

Backfills legacy rows where a Transport Zone code (e.g. LZN-NRTS) was stored in the
type field while the location held a UNLOCO code (e.g. MQMPT).
"""

from __future__ import unicode_literals

import json
import os

import frappe

from logistics.logistics.doctype.container.container import normalize_container_location_pair

_DOCTYPE = "Container"

_FIELDNAMES = (
	"current_location_type",
	"current_location",
	"return_location_type",
	"return_location",
)

_PROPS = (
	"fieldtype",
	"options",
	"link_filters",
)


def execute():
	if not frappe.db.exists("DocType", _DOCTYPE):
		return

	_clear_overriding_property_setters()
	frappe.reload_doc("logistics", "doctype", "container", force=True)
	_sync_docfields(_load_field_defs())
	_backfill_container_locations()

	frappe.clear_cache(doctype=_DOCTYPE)
	frappe.db.commit()


def _json_path():
	return os.path.join(
		frappe.get_app_path("logistics"),
		"logistics",
		"doctype",
		"container",
		"container.json",
	)


def _load_field_defs():
	path = _json_path()
	if not os.path.exists(path):
		return {}
	with open(path) as f:
		data = json.load(f)
	wanted = set(_FIELDNAMES)
	out = {}
	for field in data.get("fields") or []:
		fn = field.get("fieldname")
		if fn in wanted:
			out[fn] = field
	return out


def _clear_overriding_property_setters():
	names = frappe.get_all(
		"Property Setter",
		filters={
			"doc_type": _DOCTYPE,
			"field_name": ["in", list(_FIELDNAMES)],
			"property": ["in", list(_PROPS)],
		},
		pluck="name",
	)
	for name in names:
		frappe.delete_doc("Property Setter", name, force=1, ignore_permissions=True)


def _sync_docfields(field_defs):
	for fieldname, fdef in field_defs.items():
		row_name = frappe.db.get_value(
			"DocField",
			{"parent": _DOCTYPE, "fieldname": fieldname},
			"name",
		)
		if not row_name:
			continue
		values = {}
		for prop in _PROPS:
			if prop in fdef:
				values[prop] = fdef.get(prop)
			elif prop == "link_filters":
				values[prop] = None
		if not values:
			continue
		frappe.db.set_value("DocField", row_name, values, update_modified=False)


def _backfill_container_locations():
	rows = frappe.db.sql(
		"""
		SELECT name, current_location_type, current_location, return_location_type, return_location
		FROM `tabContainer`
		WHERE IFNULL(current_location_type, '') != ''
			OR IFNULL(current_location, '') != ''
			OR IFNULL(return_location_type, '') != ''
			OR IFNULL(return_location, '') != ''
		""",
		as_dict=True,
	)
	for row in rows:
		current_type, current_location = normalize_container_location_pair(
			row.current_location_type,
			row.current_location,
		)
		return_type, return_location = normalize_container_location_pair(
			row.return_location_type,
			row.return_location,
		)
		if (
			current_type == (row.current_location_type or "")
			and current_location == (row.current_location or "")
			and return_type == (row.return_location_type or "")
			and return_location == (row.return_location or "")
		):
			continue
		frappe.db.set_value(
			"Container",
			row.name,
			{
				"current_location_type": current_type or None,
				"current_location": current_location or None,
				"return_location_type": return_type or None,
				"return_location": return_location or None,
			},
			update_modified=False,
		)
