# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""Copy Sales Quote Charge rows onto Special Project / Exhibit programme charge tables."""

from __future__ import annotations

from typing import Any, Iterator

import frappe
from frappe import _
from frappe.utils import flt

from logistics.utils.charge_service_type import (
	apply_sales_quote_charge_service_type_to_filters,
	implied_service_type_for_doctype,
	programme_charge_service_type_label,
)
from logistics.utils.sales_quote_charge_parameters import (
	SALES_QUOTE_CHARGE_PARAMETER_FIELDS,
	extract_sales_quote_charge_parameters,
	filter_fields_existing_in_doctype,
)

_PROGRAMME_PARENT_DOCTYPES = frozenset(
	("Special Project", "MICE Project", "Project Job", "MICE Job", "MICE Order", "Docket")
)

_PROGRAMME_CHARGE_CHILD = {
	"Special Project": "Special Project Charges",
	"MICE Project": "MICE Project Charges",
	"Project Job": "Special Project Charges",
	"MICE Job": "MICE Project Charges",
	"MICE Order": "MICE Project Charges",
	"Docket": "MICE Project Charges",
}

# Docket is the main job for the exhibitor; child bookings/orders are internal legs.
_DOCKET_COPY_ALL_SALES_QUOTE_CHARGES = "__all__"

# Sales Quote Charge → programme charge row (programme tables use ``rate`` not ``unit_rate``).
_SQC_TO_PROGRAMME_CHARGE_FIELDS = (
	"item_code",
	"item_name",
	"description",
	"charge_type",
	"charge_category",
	"revenue_calculation_method",
	"unit_rate",
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

_PROGRAMME_CHARGE_LINKAGE_FIELDS = (
	"change_request",
	"change_request_charge",
	"charge_scope",
	"linked_service",
	"internal_job",
)

_SALES_QUOTE_CHARGE_DOCTYPE = "Sales Quote Charge"

_CHARGE_BREAK_SPECS = (
	(
		"Sales Quote Weight Break",
		("rate_type", "weight_break", "unit_rate", "currency"),
		"N (Normal)",
	),
	(
		"Sales Quote Qty Break",
		("rate_type", "qty_break", "unit_rate", "currency"),
		"Qty Break",
	),
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
	if "service_type" in filter_fields_existing_in_doctype(charge_doctype, ["service_type"]):
		st = _sqc_val(sq_row, "service_type")
		out["service_type"] = programme_charge_service_type_label(
			st, charge_doctype=charge_doctype, default=st or "Other"
		)
	for fn, val in extract_sales_quote_charge_parameters(sq_row).items():
		if fn in allowed and val is not None and val != "":
			out[fn] = val
	linkage_allowed = set(
		filter_fields_existing_in_doctype(charge_doctype, list(_PROGRAMME_CHARGE_LINKAGE_FIELDS))
	)
	for fn in _PROGRAMME_CHARGE_LINKAGE_FIELDS:
		if fn not in linkage_allowed:
			continue
		val = _sqc_val(sq_row, fn)
		if val is not None and val != "":
			out[fn] = val
	return out


def programme_charge_service_types_for_parent(parent_doctype: str | None, service_types=None):
	"""Docket programme docs copy every Sales Quote charge line (main job); others use implied service."""
	if service_types is not None:
		return service_types
	if parent_doctype == "Docket":
		return _DOCKET_COPY_ALL_SALES_QUOTE_CHARGES
	return None


def fetch_sales_quote_charges_for_programme(parent_doc, sales_quote_doc, service_types=None):
	"""Return Sales Quote Charge rows for programme populate (no corridor routing filter)."""
	if isinstance(sales_quote_doc, str):
		sales_quote_doc = frappe.get_doc("Sales Quote", sales_quote_doc)
	parent_dt = getattr(parent_doc, "doctype", None)
	service_types = programme_charge_service_types_for_parent(parent_dt, service_types)
	base = {"parent": sales_quote_doc.name, "parenttype": "Sales Quote"}
	implied = implied_service_type_for_doctype(parent_dt)
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
		dict.fromkeys(
			_SQC_TO_PROGRAMME_CHARGE_FIELDS
			+ SALES_QUOTE_CHARGE_PARAMETER_FIELDS
			+ _PROGRAMME_CHARGE_LINKAGE_FIELDS
		)
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

	service_types = programme_charge_service_types_for_parent(parent_dt, service_types)

	if clear_existing:
		parent_doc.set("charges", [])

	rows = fetch_sales_quote_charges_for_programme(parent_doc, sales_quote, service_types=service_types)
	added = 0
	for sq_row in rows:
		mapped = map_sales_quote_charge_to_programme_charge_dict(sq_row, sales_quote.name, charge_dt)
		if not mapped.get("item_code") and not mapped.get("unit_rate"):
			continue
		parent_doc.append("charges", mapped)
		added += 1
	return added


def copy_charge_breaks_for_reference(
	from_reference_doctype: str,
	from_reference_no: str,
	to_reference_doctype: str,
	to_reference_no: str,
) -> int:
	"""Copy weight/qty break rows from one charge reference to another."""
	if (
		not from_reference_doctype
		or not from_reference_no
		or not to_reference_doctype
		or not to_reference_no
		or str(from_reference_no).startswith("new")
		or str(to_reference_no).startswith("new")
	):
		return 0

	copied = 0
	for break_doctype, fields, default_rate_type in _CHARGE_BREAK_SPECS:
		if not frappe.db.exists("DocType", break_doctype):
			continue
		for record_type in ("Selling", "Cost"):
			rows = frappe.get_all(
				break_doctype,
				filters={
					"reference_doctype": from_reference_doctype,
					"reference_no": from_reference_no,
					"type": record_type,
				},
				fields=list(fields),
			)
			if not rows:
				continue
			frappe.db.delete(
				break_doctype,
				{
					"reference_doctype": to_reference_doctype,
					"reference_no": to_reference_no,
					"type": record_type,
				},
			)
			for row in rows:
				doc = frappe.new_doc(break_doctype)
				doc.reference_doctype = to_reference_doctype
				doc.reference_no = to_reference_no
				doc.type = record_type
				for fieldname in fields:
					val = row.get(fieldname)
					if fieldname == "rate_type":
						val = val or default_rate_type
					elif fieldname in ("weight_break", "qty_break", "unit_rate"):
						val = flt(val or 0)
					elif fieldname == "currency":
						val = val or "USD"
					setattr(doc, fieldname, val)
				doc.insert(ignore_permissions=True)
				copied += 1
	return copied


def _iter_programme_charge_sq_pairs(
	parent_doc,
	sales_quote_name: str,
	service_types=None,
) -> Iterator[tuple[Any, Any]]:
	"""Yield (sales_quote_charge_row, programme_charge_row) in populate order."""
	if not sales_quote_name or not frappe.db.exists("Sales Quote", sales_quote_name):
		return

	parent_dt = getattr(parent_doc, "doctype", None)
	charge_dt = _PROGRAMME_CHARGE_CHILD.get(parent_dt)
	if not charge_dt:
		return

	sales_quote = frappe.get_doc("Sales Quote", sales_quote_name)
	sq_rows = fetch_sales_quote_charges_for_programme(parent_doc, sales_quote, service_types=service_types)
	prog_charges = list(parent_doc.get("charges") or [])
	prog_idx = 0
	for sq_row in sq_rows:
		mapped = map_sales_quote_charge_to_programme_charge_dict(sq_row, sales_quote.name, charge_dt)
		if not mapped.get("item_code") and not mapped.get("unit_rate"):
			continue
		if prog_idx >= len(prog_charges):
			break
		yield sq_row, prog_charges[prog_idx]
		prog_idx += 1


def copy_sales_quote_charge_breaks_to_programme_parent(
	parent_doc,
	sales_quote_name: str | None = None,
	*,
	service_types=None,
) -> int:
	"""After the parent is saved, copy SQ weight/qty breaks onto programme charge rows."""
	sq_name = sales_quote_name or getattr(parent_doc, "sales_quote", None)
	if not sq_name or not parent_doc.name or str(parent_doc.name).startswith("new"):
		return 0

	parent_dt = getattr(parent_doc, "doctype", None)
	charge_dt = _PROGRAMME_CHARGE_CHILD.get(parent_dt)
	if not charge_dt:
		return 0

	if parent_doc.get("charges") and not all(getattr(ch, "name", None) for ch in parent_doc.charges):
		parent_doc.reload()

	service_types = programme_charge_service_types_for_parent(parent_dt, service_types)
	copied = 0
	for sq_row, prog_charge in _iter_programme_charge_sq_pairs(parent_doc, sq_name, service_types=service_types):
		sq_charge_name = _sqc_val(sq_row, "name")
		prog_charge_name = getattr(prog_charge, "name", None)
		if not sq_charge_name or not prog_charge_name:
			continue
		copied += copy_charge_breaks_for_reference(
			_SALES_QUOTE_CHARGE_DOCTYPE,
			sq_charge_name,
			charge_dt,
			prog_charge_name,
		)
	return copied


def preview_programme_charges_from_sales_quote(docname: str, doctype: str, sales_quote: str) -> dict:
	"""Preview charge rows for Get Charges from Quotation (no save)."""
	doc = frappe.get_doc(doctype, docname)
	sq = frappe.get_doc("Sales Quote", sales_quote)
	charge_dt = _PROGRAMME_CHARGE_CHILD.get(doctype) or "Special Project Charges"
	rows = fetch_sales_quote_charges_for_programme(
		doc, sq, service_types=programme_charge_service_types_for_parent(doctype)
	)
	charges = []
	for sq_row in rows:
		mapped = map_sales_quote_charge_to_programme_charge_dict(sq_row, sq.name, charge_dt)
		if mapped.get("item_code") or mapped.get("unit_rate"):
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
		copy_sales_quote_charge_breaks_to_programme_parent(
			parent_doc, sales_quote_name, service_types=kwargs.get("service_types")
		)
	return n


def _programme_charge_match_key(charge: Any) -> tuple[str, str]:
	item_code = (_sqc_val(charge, "item_code") or "").strip()
	service_type = (_sqc_val(charge, "service_type") or "").strip()
	return item_code, service_type


def restore_programme_charge_estimates_from_sales_quote(parent_doc) -> int:
	"""Restore estimated revenue/cost on programme charge rows from the linked Sales Quote."""
	sq_name = getattr(parent_doc, "sales_quote", None)
	if not sq_name or not frappe.db.exists("Sales Quote", sq_name):
		return 0

	sq_rows = fetch_sales_quote_charges_for_programme(
		parent_doc, sq_name, service_types="__all__"
	)
	if not sq_rows:
		return 0

	sq_by_key: dict[tuple[str, str], list[Any]] = {}
	for sq_row in sorted(sq_rows, key=lambda row: row.get("idx") or 0):
		key = _programme_charge_match_key(sq_row)
		if not key[0]:
			continue
		sq_by_key.setdefault(key, []).append(sq_row)

	usage: dict[tuple[str, str], int] = {}
	changed = 0
	for charge in sorted(parent_doc.get("charges") or [], key=lambda row: row.idx or 0):
		sq_link = (_sqc_val(charge, "sales_quote_link") or sq_name or "").strip()
		if sq_link and sq_link != sq_name:
			continue
		key = _programme_charge_match_key(charge)
		if not key[0]:
			continue
		pool = sq_by_key.get(key) or []
		pos = usage.get(key, 0)
		if pos >= len(pool):
			continue
		sq_row = pool[pos]
		usage[key] = pos + 1
		for field in ("estimated_revenue", "estimated_cost"):
			if hasattr(charge, field):
				val = _sqc_val(sq_row, field)
				if val is not None:
					setattr(charge, field, val)
					changed += 1
	return changed
