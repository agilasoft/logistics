# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Transport Document Type default from Transport Mode (server-side; see transport_mode_default_document_type.js)."""

from __future__ import annotations

import frappe

CUSTOMS_DOCTYPES = frozenset({"Declaration Order", "Declaration"})


def _is_empty(value) -> bool:
	if value is None:
		return True
	if isinstance(value, str) and not value.strip():
		return True
	return False


def apply_default_transport_document_type(doc) -> None:
	"""If transport_mode is set and transport_document_type is empty, set from the Transport Mode master."""
	if doc.doctype not in CUSTOMS_DOCTYPES:
		return
	if not doc.meta.get_field("transport_mode") or not doc.meta.get_field("transport_document_type"):
		return
	mode = (doc.get("transport_mode") or "").strip()
	if not mode:
		return
	if not _is_empty(doc.get("transport_document_type")):
		return
	if not frappe.db.exists("Transport Mode", mode):
		return
	default_type = frappe.db.get_value("Transport Mode", mode, "default_transport_document_type")
	if default_type:
		doc.set("transport_document_type", default_type)


# Alias for imports expecting a short name (e.g. parity with client `logistics.transport_mode_defaults.apply`).
apply = apply_default_transport_document_type
