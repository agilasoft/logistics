# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Copy logistics programme rows from legacy ``tabEvent`` into ``tabExhibit``."""

from __future__ import annotations

import frappe


def execute():
	if not frappe.db.table_exists("tabEvent") or not frappe.db.has_column("Event", "project_name"):
		return
	if not frappe.db.table_exists("tabExhibit"):
		return

	meta = frappe.get_meta("Exhibit")
	fields = {f.fieldname for f in meta.fields if not f.fieldtype in ("Table", "Section Break", "Column Break", "Tab Break", "HTML")}

	rows = frappe.db.sql("SELECT * FROM `tabEvent` WHERE IFNULL(project_name, '') != ''", as_dict=True)
	for row in rows:
		if frappe.db.exists("Exhibit", row.name):
			continue
		doc = frappe.new_doc("Exhibit")  # not get_doc — name is assigned below
		for fieldname in fields:
			if fieldname in row and row.get(fieldname) is not None:
				doc.set(fieldname, row.get(fieldname))
		doc.name = row.name
		doc.insert(ignore_permissions=True)
		_migrate_child_rows(row.name)

	frappe.db.commit()


def _migrate_child_rows(parent: str):
	child_map = (
		("tabEvent Participant", "exhibit_participants", "Exhibit Participant"),
		("tabEvent Service Activity", "service_activities", "Exhibit Service Activity"),
	)
	for table, parentfield, doctype in child_map:
		if not frappe.db.table_exists(table):
			continue
		rows = frappe.db.sql(
			f"SELECT * FROM `{table}` WHERE parent = %s AND parenttype IN ('Event', 'Exhibit')",
			parent,
			as_dict=True,
		)
		if not rows:
			continue
		if frappe.db.exists("Exhibit", parent):
			doc = frappe.get_doc("Exhibit", parent)
			for row in rows:
				child = doc.append(parentfield, {})
				child_meta = frappe.get_meta(doctype)
				for f in child_meta.fields:
					if f.fieldname in row and row.get(f.fieldname) is not None:
						child.set(f.fieldname, row.get(f.fieldname))
			doc.save(ignore_permissions=True)
