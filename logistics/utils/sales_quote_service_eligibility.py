# Copyright (c) 2026, Agilasoft and contributors
# Licensed under the MIT License. See license.txt

"""Which operational modules a Sales Quote authorizes, based only on its charge lines (unified + legacy)."""

from __future__ import annotations

import frappe
from frappe import _

# Legacy child tables (pre–Sales Quote Charge); a row still counts as that service.
SERVICE_LEGACY_TABLE: dict[str, str] = {
	"Transport": "Sales Quote Transport",
	"Air": "Sales Quote Air Freight",
	"Sea": "Sales Quote Sea Freight",
	"Customs": "Sales Quote Customs",
	"Warehousing": "Sales Quote Warehouse",
}

# Reserved name pattern for Link filters when no one-off quote matches (no rows returned).
_ONE_OFF_PICKER_EMPTY_SENTINEL = "__NO_ELIGIBLE_ONE_OFF_QUOTE__"


def get_one_off_sales_quote_names_for_service(
	service_type: str,
	excluded_names: list[str] | None = None,
) -> list[str]:
	"""Submitted One-off Sales Quotes that have charge lines for ``service_type`` (unified or legacy).

	Respects validity and one-off status. ``excluded_names`` should include quotes already linked
	elsewhere or converted — same single-use rules as operational validators.
	"""
	if service_type not in SERVICE_LEGACY_TABLE:
		return []
	excluded = [x for x in (excluded_names or []) if x]

	legacy_dt = SERVICE_LEGACY_TABLE.get(service_type)
	legacy_sql = ""
	if legacy_dt and frappe.db.table_exists(legacy_dt):
		legacy_sql = f"""
			OR EXISTS (
				SELECT 1 FROM `tab{legacy_dt}` leg
				WHERE leg.parent = sq.name AND leg.parenttype = 'Sales Quote'
			)"""

	not_in_clause = ""
	params: list = []
	if excluded:
		placeholders = ",".join(["%s"] * len(excluded))
		not_in_clause = f"AND sq.name NOT IN ({placeholders})"
		params.extend(excluded)

	params.append(service_type)

	sql = f"""
		SELECT sq.name
		FROM `tabSales Quote` sq
		WHERE sq.quotation_type = 'One-off'
		AND sq.docstatus = 1
		AND IFNULL(sq.status,'') NOT IN ('Converted','Lost','Expired')
		AND (sq.valid_until IS NULL OR sq.valid_until >= CURDATE())
		{not_in_clause}
		AND (
			EXISTS (
				SELECT 1 FROM `tabSales Quote Charge` sqc
				WHERE sqc.parent = sq.name AND sqc.parenttype = 'Sales Quote'
				AND sqc.service_type = %s
			)
			{legacy_sql}
		)
		ORDER BY sq.modified DESC
	"""
	rows = frappe.db.sql(sql, tuple(params), as_dict=False)
	return [r[0] for r in rows]


def one_off_sales_quote_link_filters_for_service(
	service_type: str,
	excluded_names: list[str] | None = None,
) -> dict:
	"""Filters dict for a Sales Quote Link field: eligible one-off quotes by service charges (not ``main_service``)."""
	eligible = get_one_off_sales_quote_names_for_service(service_type, excluded_names)
	if not eligible:
		return {"name": ["=", _ONE_OFF_PICKER_EMPTY_SENTINEL]}
	return {"name": ["in", eligible]}


def converted_one_off_sales_quote_names() -> list[str]:
	"""One-off Sales Quotes already marked converted (lifecycle), for exclusion from pickers."""
	names = set(
		frappe.get_all(
			"Sales Quote",
			filters={"quotation_type": "One-off", "status": "Converted"},
			pluck="name",
		)
	)
	names.update(
		frappe.get_all(
			"Sales Quote",
			filters={"quotation_type": "One-off", "converted_to_doc": ["is", "set"]},
			pluck="name",
		)
	)
	return list(names)


def sales_quote_has_service_charges(sales_quote: str, service_type: str) -> bool:
	"""True if the quote has at least one unified charge row or legacy child row for service_type."""
	if not sales_quote or service_type not in SERVICE_LEGACY_TABLE:
		return False
	if not frappe.db.exists("Sales Quote", sales_quote):
		return False
	n = frappe.db.count(
		"Sales Quote Charge",
		{"parent": sales_quote, "parenttype": "Sales Quote", "service_type": service_type},
	)
	if n > 0:
		return True
	child_dt = SERVICE_LEGACY_TABLE.get(service_type)
	if child_dt and frappe.db.table_exists(child_dt):
		return (
			frappe.db.count(child_dt, {"parent": sales_quote, "parenttype": "Sales Quote"}) > 0
		)
	return False


def require_sales_quote_service_charges(
	sales_quote: str | None,
	service_type: str,
	*,
	module_label: str,
) -> None:
	"""Throw if the quote is missing or has no charge lines for service_type (Warehousing / Customs / …)."""
	if not sales_quote:
		frappe.throw(
			_(
				"{0} is only available when a Sales Quote is linked and that quote includes {1} charges."
			).format(module_label, service_type),
			title=_("Sales Quote charges required"),
		)
	if not frappe.db.exists("Sales Quote", sales_quote):
		frappe.throw(
			_("Sales Quote {0} does not exist.").format(sales_quote),
			title=_("Invalid Sales Quote"),
		)
	if not sales_quote_has_service_charges(sales_quote, service_type):
		frappe.throw(
			_(
				"{0} is only allowed when Sales Quote {1} includes {2} charge lines. Add those charges on the quote or use a different quote."
			).format(module_label, sales_quote, service_type),
			title=_("Sales Quote charges required"),
		)


@frappe.whitelist()
def get_quote_module_flags(
	sales_quote: str | None = None,
	source_doctype: str | None = None,
	source_name: str | None = None,
) -> dict[str, bool]:
	"""For forms: whether Warehousing (inbound) and Customs (declaration) are allowed from this quote.

	When ``source_doctype`` / ``source_name`` are an Air or Sea Shipment, **Declaration Order** is also
	allowed for **internal jobs** (Customs charges live on the Main Job, not on the Sales Quote).
	"""
	from frappe.utils import cint

	allow_inbound = False
	allow_declaration = False

	if sales_quote and frappe.db.exists("Sales Quote", sales_quote):
		allow_inbound = sales_quote_has_service_charges(sales_quote, "Warehousing")
		allow_declaration = sales_quote_has_service_charges(sales_quote, "Customs")
		if not allow_declaration:
			main_sv = frappe.db.get_value("Sales Quote", sales_quote, "main_service")
			if main_sv == "Customs":
				allow_declaration = True

	if source_doctype and source_name and frappe.db.exists(source_doctype, source_name):
		src = frappe.get_cached_doc(source_doctype, source_name)
		if source_doctype in ("Air Shipment", "Sea Shipment"):
			sq_on_src = getattr(src, "sales_quote", None)
			internal_job_declaration = (
				sq_on_src
				and cint(getattr(src, "is_internal_job", 0))
				and getattr(src, "main_job_type", None)
				and getattr(src, "main_job", None)
				and frappe.db.exists(src.main_job_type, src.main_job)
			)
			if internal_job_declaration:
				allow_declaration = True

	return {"allow_inbound": allow_inbound, "allow_declaration": allow_declaration}
