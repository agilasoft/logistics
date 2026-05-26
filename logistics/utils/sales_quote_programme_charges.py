# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""Copy Sales Quote Charge rows onto Special Project / Exhibit programme charge tables."""

from __future__ import annotations

import frappe
from frappe import _

from logistics.utils.charge_service_type import (
	apply_sales_quote_charge_service_type_to_filters,
	implied_service_type_for_doctype,
	operational_booking_charge_service_type_label,
)
from logistics.utils.sales_quote_charge_parameters import (
	SALES_QUOTE_CHARGE_PARAMETER_FIELDS,
	extract_sales_quote_charge_parameters,
	filter_fields_existing_in_doctype,
)

_PROGRAMME_PARENT_DOCTYPES = frozenset(
	("Special Project", "Exhibit", "Project Job", "Exhibit Job", "Exhibit Order")
)

_PROGRAMME_CHARGE_CHILD = {
	"Special Project": "Special Project Charges",
	"Exhibit": "Exhibit Charges",
	"Project Job": "Special Project Charges",
	"Exhibit Job": "Exhibit Charges",
	"Exhibit Order": "Exhibit Charges",
}

# Sales Quote Charge → programme charge row (programme tables use ``rate`` not ``unit_rate``).
_SQC_TO_PROGRAMME_CHARGE_FIELDS = (
	"item_code",
	"item_name",
	"charge_type",
	"charge_category",
	"revenue_calculation_method",
	"quantity",
	"uom",
	"currency",
	"unit_type",
	"minimum_quantity",
	"minimum_charge",
	"maximum_charge",
	"base_amount",
	"estimated_revenue",
	"revenue_calc_notes",
	"cost_calculation_method",
	"cost_quantity",
	"cost_uom",
	"cost_currency",
	"unit_cost",
	"cost_unit_type",
	"cost_minimum_quantity",
	"cost_minimum_charge",
	"cost_maximum_charge",
	"cost_base_amount",
	"estimated_cost",
	"cost_calc_notes",
	"bill_to",
	"pay_to",
	"bill_to_exchange_rate",
	"pay_to_exchange_rate",
	"bill_to_exchange_rate_source",
	"pay_to_exchange_rate_source",
	"use_tariff_in_revenue",
	"use_tariff_in_cost",
	"revenue_tariff",
	"cost_tariff",
	"apply_95_5_rule",
	"taxable_freight_item",
	"taxable_freight_item_tax_template",
)


def _sqc_val(row, fieldname):
	if isinstance(row, dict):
		return row.get(fieldname)
	return getattr(row, fieldname, None)


def map_sales_quote_charge_to_programme_charge_dict(sq_row, sales_quote_name: str, charge_doctype: str) -> dict:
	"""Build a child-table row dict for Special Project Charges / Exhibit Charges."""
	out: dict = {"sales_quote_link": sales_quote_name}
	allowed = set(filter_fields_existing_in_doctype(charge_doctype, list(_SQC_TO_PROGRAMME_CHARGE_FIELDS)))
	for fn in _SQC_TO_PROGRAMME_CHARGE_FIELDS:
		if fn not in allowed:
			continue
		val = _sqc_val(sq_row, fn)
		if val is not None and val != "":
			out[fn] = val
	if "rate" in filter_fields_existing_in_doctype(charge_doctype, ["rate"]):
		unit_rate = _sqc_val(sq_row, "unit_rate")
		if unit_rate is not None and unit_rate != "" and "rate" not in out:
			out["rate"] = unit_rate
	if "service_type" in filter_fields_existing_in_doctype(charge_doctype, ["service_type"]):
		st = _sqc_val(sq_row, "service_type")
		out["service_type"] = operational_booking_charge_service_type_label(st, default=st or "Other")
	for fn, val in extract_sales_quote_charge_parameters(sq_row).items():
		if fn in allowed and val is not None and val != "":
			out[fn] = val
	return out


def fetch_sales_quote_charges_for_programme(parent_doc, sales_quote_doc, service_types=None):
	"""Return Sales Quote Charge rows for programme populate (no corridor routing filter)."""
	if isinstance(sales_quote_doc, str):
		sales_quote_doc = frappe.get_doc("Sales Quote", sales_quote_doc)
	base = {"parent": sales_quote_doc.name, "parenttype": "Sales Quote"}
	implied = implied_service_type_for_doctype(getattr(parent_doc, "doctype", None))
	copy_all = service_types == "__all__"
	if copy_all:
		service_types = None
	if service_types:
		variants = []
		for st in service_types:
			from logistics.utils.charge_service_type import (
				iter_sales_quote_charge_service_type_db_values_for_canonical,
			)

			variants.extend(iter_sales_quote_charge_service_type_db_values_for_canonical(st))
		variants = list(dict.fromkeys(v for v in variants if v))
		if len(variants) == 1:
			base["service_type"] = variants[0]
		elif variants:
			base["service_type"] = ["in", variants]
	elif implied and not copy_all:
		apply_sales_quote_charge_service_type_to_filters(base, implied, parent_doc)
	fields = ["name", "service_type", "unit_rate"] + list(
		dict.fromkeys(_SQC_TO_PROGRAMME_CHARGE_FIELDS + SALES_QUOTE_CHARGE_PARAMETER_FIELDS)
	)
	sqc_fields = filter_fields_existing_in_doctype("Sales Quote Charge", fields)
	return frappe.get_all(
		"Sales Quote Charge",
		filters=base,
		fields=sqc_fields,
		order_by="idx",
	)


def populate_programme_charges_from_sales_quote(
	parent_doc,
	sales_quote_name: str | None = None,
	*,
	clear_existing: bool = True,
	service_types=None,
) -> int:
	"""service_types: list of labels, or ``\"__all__\"`` to copy every charge line on the quote."""
	"""
	Append charge lines from a Sales Quote onto a programme document's charges child table.

	Returns the number of rows appended.
	"""
	sq_name = sales_quote_name or getattr(parent_doc, "sales_quote", None)
	if not sq_name or not frappe.db.exists("Sales Quote", sq_name):
		return 0
	sales_quote = frappe.get_doc("Sales Quote", sq_name)
	parent_dt = getattr(parent_doc, "doctype", None)
	charge_dt = _PROGRAMME_CHARGE_CHILD.get(parent_dt)
	if not charge_dt or not parent_doc.meta.has_field("charges"):
		return 0

	if clear_existing:
		parent_doc.set("charges", [])

	rows = fetch_sales_quote_charges_for_programme(parent_doc, sales_quote, service_types=service_types)
	added = 0
	for sq_row in rows:
		mapped = map_sales_quote_charge_to_programme_charge_dict(sq_row, sales_quote.name, charge_dt)
		if not mapped.get("item_code") and not mapped.get("rate"):
			continue
		parent_doc.append("charges", mapped)
		added += 1
	return added


def preview_programme_charges_from_sales_quote(docname: str, doctype: str, sales_quote: str) -> dict:
	"""Preview charge rows for Get Charges from Quotation (no save)."""
	doc = frappe.get_doc(doctype, docname)
	sq = frappe.get_doc("Sales Quote", sales_quote)
	charge_dt = _PROGRAMME_CHARGE_CHILD.get(doctype) or "Special Project Charges"
	rows = fetch_sales_quote_charges_for_programme(doc, sq)
	charges = []
	for sq_row in rows:
		mapped = map_sales_quote_charge_to_programme_charge_dict(sq_row, sq.name, charge_dt)
		if mapped.get("item_code") or mapped.get("rate"):
			charges.append(mapped)
	msg = (
		_("{0} charge line(s) will be applied.").format(len(charges))
		if charges
		else _("No matching charge lines on this quotation.")
	)
	return {"charges": charges, "message": msg}


def populate_programme_charges_from_sales_quote_and_save(parent_doc, sales_quote_name: str | None = None, **kwargs) -> int:
	"""Populate programme charges and save the parent document."""
	n = populate_programme_charges_from_sales_quote(parent_doc, sales_quote_name, **kwargs)
	if n:
		parent_doc.save(ignore_permissions=True)
	return n
