# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Bill To defaults and eligible customer resolution for operational charge rows."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Sequence, Set

import frappe

SHIPPER_FIELDS: Sequence[str] = ("shipper", "exporter_shipper")
CONSIGNEE_FIELDS: Sequence[str] = ("consignee", "importer_consignee")
FREIGHT_AGENT_FIELDS: Sequence[str] = ("freight_agent", "freight_agent_sea")
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


def _party_customer(party_doctype: str, party_name: Optional[str]) -> Optional[str]:
	party_name = (party_name or "").strip()
	if not party_name or not frappe.db.exists(party_doctype, party_name):
		return None
	meta = frappe.get_meta(party_doctype)
	if not meta.has_field("customer"):
		return None
	return (frappe.db.get_value(party_doctype, party_name, "customer") or "").strip() or None


def _freight_agent_customer(agent_name: Optional[str]) -> Optional[str]:
	agent_name = (agent_name or "").strip()
	if not agent_name or not frappe.db.exists("Freight Agent", agent_name):
		return None
	return (frappe.db.get_value("Freight Agent", agent_name, "customer") or "").strip() or None


def _is_enabled_customer(customer: str) -> bool:
	if not customer or not frappe.db.exists("Customer", customer):
		return False
	return not frappe.db.get_value("Customer", customer, "disabled")


def _add_customer(customers: List[str], seen: Set[str], customer: Optional[str]) -> None:
	customer = (customer or "").strip()
	if not customer or customer in seen or not _is_enabled_customer(customer):
		return
	seen.add(customer)
	customers.append(customer)


def get_eligible_bill_to_customers(doc: Any) -> List[str]:
	"""
	Return distinct enabled Customer names selectable as Bill To on charge rows.

	Eligible customers are the parent document customer plus customers linked to
	the document's shipper, consignee, and freight agent(s).
	"""
	if _doc_value(doc, "doctype") == "Change Request":
		job_type = (_doc_value(doc, "job_type") or "").strip()
		job_name = (_doc_value(doc, "job") or "").strip()
		if job_type and job_name and not job_name.startswith("new-"):
			try:
				return get_eligible_bill_to_customers(frappe.get_doc(job_type, job_name))
			except Exception:
				pass

	customers: List[str] = []
	seen: Set[str] = set()

	_add_customer(customers, seen, get_parent_customer(doc))

	for field in SHIPPER_FIELDS:
		_add_customer(customers, seen, _party_customer("Shipper", _doc_value(doc, field)))

	for field in CONSIGNEE_FIELDS:
		_add_customer(customers, seen, _party_customer("Consignee", _doc_value(doc, field)))

	for field in FREIGHT_AGENT_FIELDS:
		_add_customer(customers, seen, _freight_agent_customer(_doc_value(doc, field)))

	return customers


@frappe.whitelist()
def get_eligible_bill_to_customers_for_doc(
	doctype: Optional[str] = None,
	docname: Optional[str] = None,
	doc_data: Optional[str] = None,
) -> List[str]:
	"""Desk API: resolve eligible Bill To customers from a parent document."""
	doc: Any
	if doc_data:
		doc = frappe.parse_json(doc_data)
		if isinstance(doc, dict) and doctype and not doc.get("doctype"):
			doc["doctype"] = doctype
	elif doctype and docname and not str(docname).startswith("new-"):
		doc = frappe.get_doc(doctype, docname)
	else:
		return []

	return get_eligible_bill_to_customers(doc)


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
