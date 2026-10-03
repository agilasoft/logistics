# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Bill To / Pay To on charges of a Linked Service booking created from the Main."""

from __future__ import annotations

from typing import Any

import frappe

from logistics.utils.service_role_rules import (
	get_main_service_name,
	get_main_service_type,
	is_linked_service_satellite,
)

LINKED_SERVICE_CHARGE_PARTY_DOCTYPES = (
	"Air Booking",
	"Sea Booking",
	"Transport Order",
	"Declaration Order",
)


def _norm(value: Any) -> str:
	if value is None:
		return ""
	return str(value).strip()


def _row_value(row: Any, fieldname: str) -> Any:
	if row is None:
		return None
	if isinstance(row, dict):
		return row.get(fieldname)
	return getattr(row, fieldname, None)


def _row_set(row: Any, fieldname: str, value: Any) -> None:
	if isinstance(row, dict):
		row[fieldname] = value
		return
	if hasattr(row, "set"):
		row.set(fieldname, value)
		return
	setattr(row, fieldname, value)


def customer_representing_company(company: str) -> str:
	"""Enabled Customer whose Represents Company is *company*."""
	company = _norm(company)
	if not company:
		return ""
	return _norm(
		frappe.db.get_value(
			"Customer",
			{"represents_company": company, "disabled": 0},
			"name",
		)
	)


def supplier_representing_company(company: str) -> str:
	"""Enabled internal Supplier whose Represents Company is *company*."""
	company = _norm(company)
	if not company:
		return ""
	return _norm(
		frappe.db.get_value(
			"Supplier",
			{"represents_company": company, "is_internal_supplier": 1, "disabled": 0},
			"name",
		)
	)


def apply_linked_service_charge_parties(doc: Any) -> None:
	"""Rewrite charge Bill To / Pay To on a Linked Service booking created from the Main.

	Bill To becomes the Customer that represents the Main job's company. Cost-only rows
	are left alone. Pay To already copied from the Main is kept. An empty Pay To is filled
	with the Supplier that represents this document's company, except on Revenue-only rows.
	Missing Customer or Supplier masters leave the copied value in place.
	"""
	if not doc or getattr(doc, "doctype", None) not in LINKED_SERVICE_CHARGE_PARTY_DOCTYPES:
		return
	if not is_linked_service_satellite(doc):
		return

	main_type = get_main_service_type(doc)
	main_name = get_main_service_name(doc)
	if not main_type or not main_name or not frappe.db.exists(main_type, main_name):
		return

	main_company = _norm(frappe.db.get_value(main_type, main_name, "company"))
	bill_to = customer_representing_company(main_company) if main_company else ""
	pay_to = supplier_representing_company(_norm(getattr(doc, "company", None)))

	charges = doc.get("charges") if hasattr(doc, "get") else getattr(doc, "charges", None)
	for row in charges or []:
		charge_type = _norm(_row_value(row, "charge_type"))
		if bill_to and charge_type != "Cost":
			_row_set(row, "bill_to", bill_to)
		if pay_to and charge_type != "Revenue" and not _norm(_row_value(row, "pay_to")):
			_row_set(row, "pay_to", pay_to)


def on_before_save_linked_service_charge_parties(doc: Any, method: str | None = None) -> None:
	"""First save only, so later manual Bill To / Pay To edits are kept."""
	if not doc or getattr(doc, "doctype", None) not in LINKED_SERVICE_CHARGE_PARTY_DOCTYPES:
		return
	is_new = getattr(doc, "is_new", None)
	if not callable(is_new) or not is_new():
		return
	apply_linked_service_charge_parties(doc)
