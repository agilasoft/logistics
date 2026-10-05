# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Bill To defaults for operational charge rows.

Bill To is a Customer link with no header-customer filter. New rows still
default to the parent document customer.
"""

from __future__ import annotations

from typing import Any, Optional, Sequence

import frappe

PARENT_CUSTOMER_FIELDS: Sequence[str] = ("local_customer", "customer")

CHARGE_PARENT_DOCTYPES: Sequence[str] = (
	"Sea Booking",
	"Sea Shipment",
	"Air Booking",
	"Air Shipment",
	"Transport Order",
	"Transport Job",
	"Declaration",
	"Declaration Order",
	"Sales Quote",
	"Change Request",
	"Special Project",
)


def _doc_value(doc: Any, fieldname: str) -> Any:
	if doc is None:
		return None
	if isinstance(doc, dict):
		return doc.get(fieldname)
	return getattr(doc, fieldname, None)


def get_parent_customer(doc: Any) -> Optional[str]:
	"""Return the header customer on an operational document."""
	for field in PARENT_CUSTOMER_FIELDS:
		value = (_doc_value(doc, field) or "").strip()
		if value:
			return value
	return None


def get_default_bill_to(doc: Any) -> Optional[str]:
	"""Default Bill To on a new charge row is the parent document customer."""
	return get_parent_customer(doc)


def charge_parent_has_bill_to(doctype: str) -> bool:
	"""True when parent doctype has a charges child table with bill_to."""
	if doctype not in CHARGE_PARENT_DOCTYPES:
		return False
	meta = frappe.get_meta(doctype)
	charges_df = meta.get_field("charges")
	if not charges_df or charges_df.fieldtype != "Table":
		return False
	child_meta = frappe.get_meta(charges_df.options)
	return child_meta.has_field("bill_to")
