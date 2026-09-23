# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""DocType permission asserts for custom form menu actions.

Custom Actions / Create / Post buttons are not permissioned by Frappe. Bind each
action to standard DocType perms and call these helpers from whitelist methods.
"""

from __future__ import annotations

from typing import Any

import frappe


def assert_perm(doctype: str, ptype: str = "read", doc: Any = None) -> None:
	"""Require ``ptype`` on ``doctype`` (optionally a specific document)."""
	if not doctype:
		frappe.throw(frappe._("DocType is required for permission check."))
	if doc is not None and isinstance(doc, str):
		doc = frappe.get_doc(doctype, doc)
	frappe.has_permission(doctype, ptype, doc=doc, throw=True)


def assert_source_read(doctype: str, name: str | None = None, doc: Any = None) -> Any:
	"""Load source document if needed and require read. Returns the document."""
	if doc is None:
		if not doctype or not name:
			frappe.throw(frappe._("Source document is required."))
		doc = frappe.get_doc(doctype, name)
	frappe.has_permission(doc.doctype, "read", doc=doc, throw=True)
	return doc


def assert_create_from_source(
	target_doctype: str,
	source_doctype: str | None = None,
	source_name: str | None = None,
	source_doc: Any = None,
) -> Any:
	"""Require read on the source document and create on the target DocType.

	Returns the source document when one was provided or loaded.
	"""
	src = None
	if source_doc is not None:
		src = source_doc
	elif source_doctype and source_name:
		src = frappe.get_doc(source_doctype, source_name)
	if src is not None:
		frappe.has_permission(src.doctype, "read", doc=src, throw=True)
	frappe.has_permission(target_doctype, "create", throw=True)
	return src


def can_create(doctype: str) -> bool:
	"""True when the session user may create ``doctype`` (no throw)."""
	if not doctype:
		return False
	return bool(frappe.has_permission(doctype, "create"))
