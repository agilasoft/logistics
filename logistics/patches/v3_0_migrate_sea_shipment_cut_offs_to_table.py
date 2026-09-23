# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Migrate Sea Shipment flat cut-off Datetimes into Sea Freight Cut Off child rows."""

from __future__ import unicode_literals

import frappe

_FIELD_TO_CUT_OFF = (
	("cargo_cut_off", "Cargo Cut-offs"),
	("document_cut_off", "Documents Cut-offs"),
	("vgm_cut_off", "VGM Cut-offs"),
	("other_cut_off", "Other Cut-offs"),
	("gate_in_cut_off", "Gate-In Cut-offs"),
	("empty_return_cut_off", "Empty Return Cut-offs"),
)

_CHILD_DOCTYPE = "Sea Freight Cut Off"
_PARENT_DOCTYPE = "Sea Shipment"
_PARENTFIELD = "cut_offs"


def _ensure_sea_cut_off(cut_off_name):
	if frappe.db.exists("Sea Cut Off", cut_off_name):
		return cut_off_name
	doc = frappe.get_doc(
		{
			"doctype": "Sea Cut Off",
			"cut_off_name": cut_off_name,
		}
	)
	doc.insert(ignore_permissions=True)
	return doc.name


def _has_child_rows(parent):
	return bool(
		frappe.db.exists(
			_CHILD_DOCTYPE,
			{"parent": parent, "parenttype": _PARENT_DOCTYPE, "parentfield": _PARENTFIELD},
		)
	)


def execute():
	frappe.reload_doc("sea_freight", "doctype", "sea_cut_off")
	frappe.reload_doc("sea_freight", "doctype", "sea_freight_cut_off")
	frappe.reload_doc("sea_freight", "doctype", "sea_shipment")

	if not frappe.db.table_exists(f"tab{_PARENT_DOCTYPE}"):
		return

	columns = set(frappe.db.get_table_columns(_PARENT_DOCTYPE) or [])
	present_fields = [fn for fn, _ in _FIELD_TO_CUT_OFF if fn in columns]
	if not present_fields:
		return

	select_cols = ", ".join(["name"] + present_fields)
	where = " OR ".join(f"`{fn}` IS NOT NULL" for fn in present_fields)
	rows = frappe.db.sql(
		f"""
		SELECT {select_cols}
		FROM `tab{_PARENT_DOCTYPE}`
		WHERE {where}
		""",
		as_dict=True,
	)

	for row in rows:
		if _has_child_rows(row.name):
			continue
		idx = 1
		for fieldname, cut_off_name in _FIELD_TO_CUT_OFF:
			if fieldname not in present_fields:
				continue
			value = row.get(fieldname)
			if not value:
				continue
			master = _ensure_sea_cut_off(cut_off_name)
			child = frappe.get_doc(
				{
					"doctype": _CHILD_DOCTYPE,
					"parent": row.name,
					"parenttype": _PARENT_DOCTYPE,
					"parentfield": _PARENTFIELD,
					"idx": idx,
					"cut_off": master,
					"cut_off_datetime": value,
				}
			)
			child.db_insert()
			idx += 1

	frappe.db.commit()
