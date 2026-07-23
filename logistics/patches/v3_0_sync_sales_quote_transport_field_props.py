# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Force-sync Sales Quote Main Service Parameter field properties from JSON.

Transport (and other main-service) visibility lives on DocField as ``depends_on`` /
``mandatory_depends_on``. Those properties sometimes stay stale after deploy when:

- an older expression remains (e.g. One-off-only, or legacy ``is_transport``), or
- Customize Form Property Setters override DocField and are never exported.

This patch reloads Sales Quote, writes visibility props from ``sales_quote.json``,
and removes conflicting Property Setters for those fields.
"""

from __future__ import unicode_literals

import json
import os

import frappe

_DOCTYPE = "Sales Quote"

# Main Service Parameters + Transport-gated fields (and shared section helpers).
_FIELDNAMES = (
	"one_off_params_section",
	"origin_port",
	"destination_port",
	"load_type",
	"transport_mode",
	"direction",
	"customs_authority",
	"declaration_type",
	"customs_broker",
	"customs_charge_category",
	"site",
	"sp_site",
	"sp_manpower",
	"sp_skilled",
	"sp_equipment_type",
	"column_break_params",
	"location_type",
	"location_from",
	"location_to",
	"transport_template",
	"vehicle_type",
	"container_type",
	"container_no",
	"pick_mode",
	"drop_mode",
	"air_house_type",
	"airline",
	"freight_agent",
)

_PROPS = (
	"depends_on",
	"mandatory_depends_on",
	"read_only_depends_on",
	"collapsible_depends_on",
	"hidden",
	"link_filters",
)


def execute():
	if not frappe.db.exists("DocType", _DOCTYPE):
		return

	frappe.reload_doc("pricing_center", "doctype", "sales_quote", force=True)

	field_defs = _load_field_defs()
	if not field_defs:
		return

	_clear_overriding_property_setters()
	_sync_docfields(field_defs)

	frappe.clear_cache(doctype=_DOCTYPE)
	frappe.db.commit()


def _json_path():
	return os.path.join(
		frappe.get_app_path("logistics"),
		"pricing_center",
		"doctype",
		"sales_quote",
		"sales_quote.json",
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
	"""Property Setters win over DocField at meta load time and block JSON sync."""
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
			elif prop in ("depends_on", "mandatory_depends_on", "read_only_depends_on", "collapsible_depends_on", "link_filters"):
				# Clear stale expressions removed from JSON (e.g. legacy is_transport).
				values[prop] = None
		if not values:
			continue
		frappe.db.set_value("DocField", row_name, values, update_modified=False)
