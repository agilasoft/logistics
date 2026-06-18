# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Rename Internal Job / Internal Job Detail DocTypes to Linked Service variants (pre model sync)."""

from __future__ import unicode_literals

import frappe


def execute():
	_rename_doctype("Internal Job", "Linked Service")
	_rename_doctype("Internal Job Detail", "Linked Service Detail")
	frappe.db.commit()


def _rename_doctype(old_name: str, new_name: str) -> None:
	if not frappe.db.exists("DocType", old_name):
		return
	if frappe.db.exists("DocType", new_name):
		return
	frappe.rename_doc("DocType", old_name, new_name, force=True, merge=False)
