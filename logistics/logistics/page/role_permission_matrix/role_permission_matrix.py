# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.core.page.permission_manager.permission_manager import (
	get_permissions,
	get_roles_and_doctypes,
)
from frappe.utils import cint

not_allowed = ["DocType", "Patch Log", "Module Def"]


def _empty_row(doctype: str, role: str, module: str, is_submittable: int = 0):
	return frappe._dict(
		{
			"parent": doctype,
			"role": role,
			"permlevel": 0,
			"if_owner": 0,
			"module": module or "",
			"is_submittable": cint(is_submittable),
			"in_create": 0,
			"select": 0,
			"read": 0,
			"write": 0,
			"create": 0,
			"delete": 0,
			"submit": 0,
			"cancel": 0,
			"amend": 0,
			"report": 0,
			"import": 0,
			"export": 0,
			"print": 0,
			"email": 0,
			"share": 0,
			"_is_placeholder": 1,
		}
	)


@frappe.whitelist()
def get_matrix(role: str | None = None, module: str | None = None):
	"""Return permission rows for a role.

	If module is set, include every non-table DocType in that module
	(placeholders for DocTypes with no permission row yet).
	"""
	frappe.only_for("System Manager")
	if not role:
		return []

	perms = get_permissions(doctype=None, role=role) or []

	meta_by_name = {}

	def ensure_meta(names):
		missing = [n for n in names if n and n not in meta_by_name]
		if not missing:
			return
		for row in frappe.get_all(
			"DocType",
			filters={"name": ["in", missing]},
			fields=["name", "module", "is_submittable"],
		):
			meta_by_name[row.name] = row

	ensure_meta([p.parent for p in perms if p.get("parent")])

	out = []
	seen = set()
	for p in perms:
		if p.parent == "DocType":
			continue
		meta = meta_by_name.get(p.parent)
		p["module"] = (meta.module if meta else "") or ""
		if module and p["module"] != module:
			continue
		if meta and not p.get("is_submittable"):
			p["is_submittable"] = cint(meta.is_submittable)
		seen.add((p.parent, cint(p.get("permlevel")), cint(p.get("if_owner"))))
		out.append(p)

	if module:
		module_dts = frappe.get_all(
			"DocType",
			filters={
				"module": module,
				"istable": 0,
				"name": ["not in", not_allowed],
			},
			fields=["name", "module", "is_submittable"],
			order_by="name asc",
		)
		for row in module_dts:
			meta_by_name[row.name] = row
			key = (row.name, 0, 0)
			if key in seen:
				continue
			out.append(
				_empty_row(row.name, role, module, is_submittable=cint(row.is_submittable))
			)
			seen.add(key)

	out.sort(key=lambda r: (r.get("parent") or "").lower())
	return out


@frappe.whitelist()
def get_filter_options():
	"""Roles, DocTypes, and modules for the matrix filters."""
	frappe.only_for("System Manager")
	data = get_roles_and_doctypes()
	modules = frappe.get_all(
		"Module Def",
		fields=["name"],
		order_by="name asc",
		pluck="name",
	)
	return {
		"roles": data.get("roles") or [],
		"doctypes": data.get("doctypes") or [],
		"modules": [{"label": _(m), "value": m} for m in modules],
		"doctype_ptype_map": data.get("doctype_ptype_map") or {},
	}


@frappe.whitelist()
def get_doctypes_for_module(module: str | None = None):
	"""DocType names in a module (for Add DocType filter)."""
	frappe.only_for("System Manager")
	filters = {"istable": 0, "name": ["not in", not_allowed]}
	if module:
		filters["module"] = module
	return frappe.get_all("DocType", filters=filters, pluck="name", order_by="name asc")
