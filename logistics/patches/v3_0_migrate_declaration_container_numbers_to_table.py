# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Migrate comma-separated ``container_numbers`` into Containers child tables.

Runs after Declaration Order Containers / Declaration Containers exist.
Unresolved tokens (no matching Container master) are skipped with a warning.
"""

from __future__ import unicode_literals

import frappe

from logistics.container_management.api import get_container_by_number, is_container_management_enabled
from logistics.utils.container_validation import normalize_container_number

_PARENTS = (
	("Declaration Order", "Declaration Order Containers"),
	("Declaration", "Declaration Containers"),
)


def _split_container_numbers(raw):
	if not raw:
		return []
	return [p.strip() for p in str(raw).replace("\n", ",").split(",") if p.strip()]


def _resolve_container_name(token):
	eq = normalize_container_number(token)
	if not eq:
		return None
	if is_container_management_enabled():
		name = get_container_by_number(eq)
		if name:
			return name
	if frappe.db.exists("Container", eq):
		return eq
	if frappe.db.exists("Container", token):
		return token
	return None


def _has_child_rows(child_doctype, parent):
	return bool(frappe.db.exists(child_doctype, {"parent": parent}))


def _migrate_parent(parent_doctype, child_doctype):
	if not frappe.db.table_exists(f"tab{parent_doctype}"):
		return
	columns = set(frappe.db.get_table_columns(parent_doctype) or [])
	if "container_numbers" not in columns:
		return

	rows = frappe.db.sql(
		f"""
		SELECT name, container_numbers
		FROM `tab{parent_doctype}`
		WHERE container_numbers IS NOT NULL AND TRIM(container_numbers) != ''
		""",
		as_dict=True,
	)
	for row in rows:
		if _has_child_rows(child_doctype, row.name):
			continue
		idx = 1
		for token in _split_container_numbers(row.container_numbers):
			container_name = _resolve_container_name(token)
			if not container_name:
				frappe.logger("migrate_container_numbers").warning(
					f"Skip unresolved container {token!r} on {parent_doctype} {row.name}"
				)
				continue
			child = frappe.get_doc(
				{
					"doctype": child_doctype,
					"parent": row.name,
					"parenttype": parent_doctype,
					"parentfield": "containers",
					"idx": idx,
					"container_no": container_name,
				}
			)
			child.db_insert()
			idx += 1

	frappe.db.sql(
		f"""
		UPDATE `tab{parent_doctype}`
		SET container_numbers = NULL
		WHERE container_numbers IS NOT NULL AND container_numbers != ''
		"""
	)


def execute():
	frappe.reload_doc("customs", "doctype", "declaration_order_containers")
	frappe.reload_doc("customs", "doctype", "declaration_containers")
	frappe.reload_doc("customs", "doctype", "declaration_order")
	frappe.reload_doc("customs", "doctype", "declaration")

	for parent_doctype, child_doctype in _PARENTS:
		_migrate_parent(parent_doctype, child_doctype)

	frappe.db.commit()
