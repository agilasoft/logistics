# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, see license.txt
"""
Cross-module billing: unified get_invoice_items_from_job and contributor discovery.
Used by Sales Quote invoice creation and intercompany invoicing.
"""
from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import flt
from typing import Dict, List, Any, Optional, Tuple, Iterator

# Parent booking/order carries Internal Job + Main Job when the operational job does not.
INTERNAL_JOB_PARENT_LINKS = {
    "Transport Job": ("Transport Order", "transport_order"),
    "Air Shipment": ("Air Booking", "air_booking"),
    "Sea Shipment": ("Sea Booking", "sea_booking"),
}

# Registry: for each anchor DocType, list (Contributor DocType, link_field_name) to find jobs linked to that anchor.
BILLING_CONTRIBUTOR_QUERIES = {
    "Air Shipment": [
        ("Transport Job", "air_shipment"),
        ("Warehouse Job", "air_shipment"),
    ],
    "Sea Shipment": [
        ("Transport Job", "sea_shipment"),
        ("Warehouse Job", "sea_shipment"),
    ],
    "Transport Job": [
        ("Warehouse Job", "transport_job"),
    ],
    "Air Booking": [
        ("Transport Job", "air_shipment"),  # Transport Jobs linked via air_shipment (from same booking flow)
    ],
    "Sea Booking": [],
}

# Job types that can supply invoice items (anchor or contributor).
BILLING_JOB_TYPES = (
    "Transport Job",
    "Air Shipment",
    "Sea Shipment",
    "Warehouse Job",
    "Declaration",
    "Declaration Order",
)


def resolve_internal_job_main_job(job_type: str, job_name: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Return (main_service_type, main_service_name) when the job is a Linked service (on the job
    or on its parent Transport Order / Air Booking / Sea Booking), with a valid Main Service link.
    """
    from logistics.utils.service_role_rules import (
        get_main_service_name,
        get_main_service_type,
        is_linked_service_satellite,
    )

    if not job_type or not job_name or not frappe.db.exists(job_type, job_name):
        return (None, None)
    doc = frappe.get_doc(job_type, job_name)
    mt = get_main_service_type(doc)
    mn = get_main_service_name(doc)
    if is_linked_service_satellite(doc) and mt and mn and frappe.db.exists(mt, mn):
        return (mt, mn)
    parent = INTERNAL_JOB_PARENT_LINKS.get(job_type)
    if parent:
        pdoctype, link_field = parent
        pname = getattr(doc, link_field, None)
        if pname and frappe.db.exists(pdoctype, pname):
            parent_doc = frappe.get_doc(pdoctype, pname)
            mt = get_main_service_type(parent_doc)
            mn = get_main_service_name(parent_doc)
            if is_linked_service_satellite(parent_doc) and mt and mn and frappe.db.exists(mt, mn):
                return (mt, mn)
    return (None, None)


def get_main_job_company(main_job_type: str, main_job_name: str) -> Optional[str]:
    if not main_job_type or not main_job_name or not frappe.db.exists(main_job_type, main_job_name):
        return None
    return frappe.db.get_value(main_job_type, main_job_name, "company")


# Order/booking DocType -> (operational job DocType, link field on operational job).
BOOKING_TO_OPERATIONAL_JOB = {
    "Sea Booking": ("Sea Shipment", "sea_booking"),
    "Air Booking": ("Air Shipment", "air_booking"),
    "Transport Order": ("Transport Job", "transport_order"),
    "Declaration Order": ("Declaration", "declaration_order"),
    "Inbound Order": ("Warehouse Job", "reference_order"),
    "Release Order": ("Warehouse Job", "reference_order"),
    "Transfer Order": ("Warehouse Job", "reference_order"),
}


_LINKED_OPERATIONAL_JOB_TYPES = BILLING_JOB_TYPES + ("Transport Order",)


def _operational_job_from_booking_row(
    job_type: str,
    job_no: str,
    sales_quote_name: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """Map a booking/order row to its operational shipment/job when applicable."""
    if not job_type or not job_no:
        return (None, None)
    if job_type in BILLING_JOB_TYPES and frappe.db.exists(job_type, job_no):
        return (job_type, job_no)
    mapping = BOOKING_TO_OPERATIONAL_JOB.get(job_type)
    if not mapping:
        return (None, None)
    op_dt, link_field = mapping
    filters: Dict[str, Any] = {link_field: job_no}
    if sales_quote_name and frappe.db.has_column(op_dt, "sales_quote"):
        filters["sales_quote"] = sales_quote_name
    if op_dt == "Warehouse Job":
        filters["reference_order_type"] = job_type
        filters.pop(link_field, None)
        filters["reference_order"] = job_no
    names = frappe.get_all(op_dt, filters=filters, pluck="name", limit=1)
    if names:
        return (op_dt, names[0])
    return (None, None)


def resolve_billing_main_job_for_quote(
    sales_quote,
) -> Tuple[Optional[str], Optional[str], Optional[str], Optional[str]]:
    """
    Return (quote_main_type, quote_main_no, billing_main_type, billing_main_no).

    Quote main is often a booking/order; billing main is the operational shipment/job
    (e.g. Air Booking -> Air Shipment) used for internal billing Dr rows and linked-job matching.
    """
    from logistics.pricing_center.doctype.sales_quote.sales_quote import (
        _resolve_main_job_for_sales_quote,
    )

    sq_name = sales_quote.name if hasattr(sales_quote, "name") else sales_quote
    quote_main_type, quote_main_no = _resolve_main_job_for_sales_quote(sales_quote)
    if not quote_main_type or not quote_main_no:
        return (None, None, None, None)
    billing_main_type, billing_main_no = _operational_job_from_booking_row(
        quote_main_type,
        quote_main_no,
        sales_quote_name=sq_name,
    )
    if not billing_main_type or not billing_main_no:
        billing_main_type, billing_main_no = quote_main_type, quote_main_no
    return (quote_main_type, quote_main_no, billing_main_type, billing_main_no)


def linked_job_matches_billing_main(
    linked_main_type: Optional[str],
    linked_main_no: Optional[str],
    quote_main_type: str,
    quote_main_no: str,
    billing_main_type: str,
    billing_main_no: str,
) -> bool:
    """True when a linked job's Main Service points at the quote or billing main job."""
    if not linked_main_type or not linked_main_no:
        return False
    return (linked_main_type, linked_main_no) in (
        (billing_main_type, billing_main_no),
        (quote_main_type, quote_main_no),
    )


def resolve_operational_job_for_linked_service(
    linked_service_name: str,
    main_job_type: str,
    main_job_name: str,
    sales_quote_name: Optional[str] = None,
) -> Tuple[Optional[str], Optional[str]]:
    """
    Resolve the operational linked job for a Linked Service / Internal Job record.

    Used when main-job charge rows (charge_scope=Linked) carry revenue attributed to a linked service.
    """
    from logistics.utils.internal_job_persistence import internal_job_detail_fieldname
    from logistics.utils.linked_service_compat import (
        linked_service_doctype,
        linked_service_detail_doctype,
        linked_service_record_exists,
    )

    if not linked_service_name or not linked_service_record_exists(linked_service_name):
        return (None, None)

    detail_dt = linked_service_detail_doctype()
    fieldname = internal_job_detail_fieldname(main_job_type)
    if fieldname and main_job_type and main_job_name:
        for link_field in ("linked_service", "internal_job"):
            if not frappe.db.has_column(detail_dt, link_field):
                continue
            rows = frappe.get_all(
                detail_dt,
                filters={
                    "parent": main_job_name,
                    "parenttype": main_job_type,
                    "parentfield": fieldname,
                    link_field: linked_service_name,
                },
                fields=["job_type", "job_no"],
                limit=1,
            )
            if rows:
                return _operational_job_from_booking_row(
                    rows[0].get("job_type"),
                    rows[0].get("job_no"),
                    sales_quote_name=sales_quote_name,
                )

    try:
        ls_doc = frappe.get_doc(linked_service_doctype(), linked_service_name)
    except Exception:
        return (None, None)
    if ls_doc.get("job_type") and ls_doc.get("job_no"):
        op = _operational_job_from_booking_row(
            ls_doc.job_type,
            ls_doc.job_no,
            sales_quote_name=sales_quote_name,
        )
        if op[0] and op[1]:
            return op

    if sales_quote_name:
        from logistics.utils.internal_job_persistence import resolve_internal_job_for_internal_job_booking

        for jt in _LINKED_OPERATIONAL_JOB_TYPES:
            if not frappe.db.has_column(jt, "sales_quote"):
                continue
            for jn in frappe.get_all(
                jt,
                filters={"sales_quote": sales_quote_name, "docstatus": ["!=", 2]},
                pluck="name",
            ):
                try:
                    job_doc = frappe.get_doc(jt, jn)
                except Exception:
                    continue
                if resolve_internal_job_for_internal_job_booking(job_doc) == linked_service_name:
                    return _operational_job_from_booking_row(
                        jt, jn, sales_quote_name=sales_quote_name
                    )

    return (None, None)


def _charge_row_item_code(ch, job_type: str) -> Optional[str]:
    if job_type == "Sea Shipment":
        return getattr(ch, "charge_item", None)
    return getattr(ch, "item_code", None) or getattr(ch, "item", None)


def _charge_row_revenue(ch, job_type: str, *, include_estimated: bool = False) -> float:
    """Revenue amount for internal billing from one charge row."""
    if job_type == "Sea Shipment":
        rev = flt(getattr(ch, "actual_revenue", 0)) or flt(getattr(ch, "selling_amount", 0))
        if include_estimated and not rev:
            rev = flt(getattr(ch, "estimated_revenue", 0))
        return rev
    if job_type == "Air Shipment":
        rev = flt(getattr(ch, "actual_revenue", 0)) or flt(getattr(ch, "total_amount", 0))
        if include_estimated and not rev:
            rev = flt(getattr(ch, "estimated_revenue", 0))
        return rev
    if job_type in ("Declaration", "Declaration Order"):
        rev = flt(getattr(ch, "actual_revenue", 0)) or flt(getattr(ch, "total_amount", 0))
        if include_estimated and not rev:
            rev = flt(getattr(ch, "estimated_revenue", 0))
        return rev
    rev = flt(getattr(ch, "actual_revenue", 0))
    if include_estimated and not rev:
        rev = flt(getattr(ch, "estimated_revenue", 0))
    return rev


def _charge_row_cost(ch, job_type: str, *, include_estimated: bool = False) -> float:
    """Cost amount from one charge row."""
    cost = flt(getattr(ch, "actual_cost", 0))
    if include_estimated and not cost:
        cost = flt(getattr(ch, "estimated_cost", 0))
    return cost


def is_booking_superseded_by_operational_job(
    job_type: str,
    job_no: str,
    quote_job_keys: set,
    sales_quote_name: Optional[str] = None,
) -> bool:
    """
    True when a booking/order on the quote already has an operational job on the same quote.

    Avoids billing estimated revenue on Transport Order when Transport Job (etc.) exists.
    """
    mapping = BOOKING_TO_OPERATIONAL_JOB.get(job_type)
    if not mapping:
        return False
    op_type, link_field = mapping
    if not frappe.db.has_column(op_type, link_field):
        return False
    filters = {link_field: job_no, "docstatus": ["!=", 2]}
    if sales_quote_name and frappe.db.has_column(op_type, "sales_quote"):
        filters["sales_quote"] = sales_quote_name
    for op_name in frappe.get_all(op_type, filters=filters, pluck="name"):
        if (op_type, op_name) in quote_job_keys:
            return True
    return False


def iter_main_job_linked_scope_charge_splits(
    main_job_doc,
) -> Iterator[Dict[str, Any]]:
    """
    Yield linked-service charge splits from the main job's charges table.

    Rows must have charge_scope=Linked (or legacy Internal Job) and a linked_service link.
    Revenue uses estimated amounts when actuals are not yet posted.
    """
    from logistics.utils.linked_service_compat import (
        charge_row_linked_service_link,
        is_linked_charge_scope,
    )

    job_type = getattr(main_job_doc, "doctype", None)
    if not job_type:
        return
    if hasattr(main_job_doc, "get") and callable(main_job_doc.get):
        charges_table = main_job_doc.get("charges") or []
    else:
        charges_table = getattr(main_job_doc, "charges", None) or []
    if not charges_table:
        return
    parent_meta = frappe.get_meta(job_type)
    charges_df = parent_meta.get_field("charges")
    if not charges_df or not charges_df.options:
        return
    child_meta = frappe.get_meta(charges_df.options)
    if not child_meta.has_field("charge_scope"):
        return

    for ch in charges_table:
        if not is_linked_charge_scope(getattr(ch, "charge_scope", None)):
            continue
        linked_service = charge_row_linked_service_link(ch)
        if not linked_service:
            continue
        rev = _charge_row_revenue(ch, job_type, include_estimated=True)
        if rev <= 0:
            continue
        item_code = _charge_row_item_code(ch, job_type)
        yield {
            "revenue": rev,
            "cost": 0,
            "item_code": item_code,
            "linked_service": linked_service,
        }


def iter_internal_job_charge_splits(
    job_type: str,
    job_name: str,
    customer: Optional[str] = None,
    *,
    prefer_actual: bool = False,
) -> Iterator[Dict[str, Any]]:
    """
    Yield per charge row: revenue, cost, item_code (for Job Number / Item dimensions on JEs).

    When ``prefer_actual`` is True (internal billing JV), only posted actual revenue/cost
    amounts are used — estimated booking amounts are excluded.
    """
    if not job_type or not job_name or not frappe.db.exists(job_type, job_name):
        return
    doc = frappe.get_doc(job_type, job_name)
    customer = customer or getattr(doc, "customer", None) or getattr(doc, "local_customer", None)
    include_estimated = not prefer_actual

    if job_type == "Transport Job":
        for ch in doc.get("charges") or []:
            item_code = getattr(ch, "item_code", None)
            rev = _charge_row_revenue(ch, job_type, include_estimated=include_estimated)
            cost = _charge_row_cost(ch, job_type, include_estimated=include_estimated)
            if rev <= 0 and cost <= 0:
                continue
            yield {"revenue": rev, "cost": cost, "item_code": item_code}

    elif job_type == "Transport Order":
        for ch in doc.get("charges") or []:
            item_code = getattr(ch, "item_code", None)
            rev = _charge_row_revenue(ch, job_type, include_estimated=include_estimated)
            cost = _charge_row_cost(ch, job_type, include_estimated=include_estimated)
            if rev <= 0 and cost <= 0:
                continue
            yield {"revenue": rev, "cost": cost, "item_code": item_code}

    elif job_type == "Sea Shipment":
        from logistics.utils.charges_calculation import get_charge_bill_to_customers

        for ch in doc.get("charges") or []:
            if customer and customer not in get_charge_bill_to_customers(ch):
                continue
            item_code = getattr(ch, "charge_item", None)
            rev = _charge_row_revenue(ch, job_type, include_estimated=include_estimated)
            cost = _charge_row_cost(ch, job_type, include_estimated=include_estimated)
            if rev <= 0 and cost <= 0:
                continue
            yield {"revenue": rev, "cost": cost, "item_code": item_code}

    elif job_type == "Air Shipment":
        for ch in doc.get("charges") or []:
            item_code = getattr(ch, "item_code", None)
            rev = _charge_row_revenue(ch, job_type, include_estimated=include_estimated)
            cost = _charge_row_cost(ch, job_type, include_estimated=include_estimated)
            if rev <= 0 and cost <= 0:
                continue
            yield {"revenue": rev, "cost": cost, "item_code": item_code}

    elif job_type == "Warehouse Job":
        for ch in doc.get("charges") or []:
            item_code = getattr(ch, "item_code", None) or getattr(ch, "item", None)
            rev = _charge_row_revenue(ch, job_type, include_estimated=include_estimated)
            cost = _charge_row_cost(ch, job_type, include_estimated=include_estimated)
            if rev <= 0 and cost <= 0:
                continue
            yield {"revenue": rev, "cost": cost, "item_code": item_code}

    elif job_type in ("Declaration", "Declaration Order"):
        for ch in doc.get("charges") or []:
            item_code = getattr(ch, "item_code", None)
            rev = _charge_row_revenue(ch, job_type, include_estimated=include_estimated)
            cost = _charge_row_cost(ch, job_type, include_estimated=include_estimated)
            if rev <= 0 and cost <= 0:
                continue
            yield {"revenue": rev, "cost": cost, "item_code": item_code}


def get_invoice_items_from_job(
    job_type: str,
    job_name: str,
    customer: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Extract invoice line items from any job/shipment/declaration (selling/revenue side).
    Single implementation for Sales Quote billing and intercompany.
    Returns list of dicts with item_code, item_name, qty, rate, uom, description (optional).
    """
    if not job_type or not job_name or not frappe.db.exists(job_type, job_name):
        return []

    items = []
    doc = frappe.get_doc(job_type, job_name)
    customer = customer or getattr(doc, "customer", None) or getattr(doc, "local_customer", None)

    if job_type == "Transport Job":
        charges = doc.get("charges") or []
        for ch in charges:
            item_code = getattr(ch, "item_code", None)
            if not item_code:
                continue
            qty = flt(getattr(ch, "quantity", 1))
            unit_rate = flt(getattr(ch, "unit_rate", 0))
            rev = flt(getattr(ch, "actual_revenue", 0)) or flt(getattr(ch, "estimated_revenue", 0))
            rate = rev / qty if (rev > 0 and qty > 0) else unit_rate
            items.append({
                "item_code": item_code,
                "item_name": getattr(ch, "item_name", None) or item_code,
                "qty": qty,
                "rate": rate,
                "uom": getattr(ch, "uom", None),
                "description": getattr(ch, "description", None),
            })

    elif job_type == "Transport Order":
        charges = doc.get("charges") or []
        for ch in charges:
            item_code = getattr(ch, "item_code", None)
            if not item_code:
                continue
            qty = flt(getattr(ch, "quantity", 1))
            unit_rate = flt(getattr(ch, "unit_rate", 0))
            rev = flt(getattr(ch, "actual_revenue", 0)) or flt(getattr(ch, "estimated_revenue", 0))
            rate = rev / qty if (rev > 0 and qty > 0) else unit_rate
            items.append({
                "item_code": item_code,
                "item_name": getattr(ch, "item_name", None) or item_code,
                "qty": qty,
                "rate": rate,
                "uom": getattr(ch, "uom", None),
                "description": getattr(ch, "description", None),
            })

    elif job_type == "Sea Shipment":
        from logistics.utils.charges_calculation import get_charge_bill_to_customers
        charges = doc.get("charges") or []
        for ch in charges:
            if customer and customer not in get_charge_bill_to_customers(ch):
                continue
            rev = flt(getattr(ch, "actual_revenue", 0)) or flt(getattr(ch, "selling_amount", 0))
            items.append({
                "item_code": getattr(ch, "charge_item", None) or getattr(ch, "item_code", None),
                "item_name": getattr(ch, "charge_name", None) or getattr(ch, "item_name", None),
                "qty": 1,
                "rate": rev,
                "uom": None,
                "description": getattr(ch, "description", None) or getattr(ch, "charge_description", None),
            })

    elif job_type == "Air Shipment":
        charges = doc.get("charges") or []
        for ch in charges:
            item_code = getattr(ch, "item_code", None)
            if not item_code:
                continue
            qty = flt(getattr(ch, "quantity", 1))
            rate = flt(getattr(ch, "unit_rate", 0))
            rev = flt(getattr(ch, "actual_revenue", 0)) or flt(getattr(ch, "total_amount", 0))
            if rev > 0 and qty > 0:
                rate = rev / qty
            elif not rev and rate <= 0:
                total = flt(getattr(ch, "total_amount", 0))
                if total > 0 and qty > 0:
                    rate = total / qty
            items.append({
                "item_code": item_code,
                "item_name": getattr(ch, "item_name", None) or item_code,
                "qty": qty,
                "rate": rate,
                "uom": getattr(ch, "uom", None),
                "description": getattr(ch, "description", None),
            })

    elif job_type == "Warehouse Job":
        charges = doc.get("charges") or []
        for ch in charges:
            item_code = getattr(ch, "item_code", None) or getattr(ch, "item", None)
            if not item_code:
                continue
            qty = flt(getattr(ch, "quantity", 1))
            rate = flt(getattr(ch, "unit_rate", 0))
            rev = flt(getattr(ch, "actual_revenue", 0)) or flt(getattr(ch, "estimated_revenue", 0))
            if rev > 0 and qty > 0:
                rate = rev / qty
            items.append({
                "item_code": item_code,
                "item_name": getattr(ch, "item_name", None) or item_code,
                "qty": qty,
                "rate": rate,
                "uom": getattr(ch, "uom", None),
                "description": getattr(ch, "description", None),
            })

    elif job_type in ("Declaration", "Declaration Order"):
        charges = doc.get("charges") or []
        for ch in charges:
            item_code = getattr(ch, "item_code", None)
            if not item_code:
                continue
            qty = flt(getattr(ch, "quantity", 1)) or 1
            rate = flt(getattr(ch, "unit_rate", 0))
            rev = flt(getattr(ch, "actual_revenue", 0)) or flt(getattr(ch, "total_amount", 0)) or flt(getattr(ch, "estimated_revenue", 0))
            if rev > 0 and qty > 0:
                rate = rev / qty
            items.append({
                "item_code": item_code,
                "item_name": getattr(ch, "item_name", None) or item_code,
                "qty": qty,
                "rate": rate,
                "uom": getattr(ch, "uom", None),
                "description": getattr(ch, "description", None) or getattr(ch, "charge_description", None),
            })

    return items


def get_internal_job_revenue_and_cost(
    job_type: str,
    job_name: str,
    customer: Optional[str] = None,
    *,
    prefer_actual: bool = False,
) -> Tuple[float, float]:
    """
    Get total revenue (allocated from main job / transfer price) and total cost (tariff or actual)
    from a job's charges. Used for internal billing Journal Entry amounts.
    Returns (revenue_total, cost_total).
    """
    revenue_total = 0.0
    cost_total = 0.0
    for row in iter_internal_job_charge_splits(
        job_type, job_name, customer=customer, prefer_actual=prefer_actual
    ):
        revenue_total += flt(row.get("revenue"))
        cost_total += flt(row.get("cost"))
    return (revenue_total, cost_total)


def get_suggested_contributors(
    anchor_doctype: str,
    anchor_name: str,
    sales_quote: Optional[str] = None,
) -> List[Dict[str, str]]:
    """
    Return list of candidate contributing jobs that can be billed with the given anchor.
    Each item: {"job_type": str, "job_no": str}.
    Optionally filter by sales_quote (same quote on the job).
    """
    queries = BILLING_CONTRIBUTOR_QUERIES.get(anchor_doctype)
    if not queries:
        return []

    out = []
    seen = set()

    for contributor_doctype, link_field in queries:
        if not frappe.db.has_column(contributor_doctype, link_field):
            continue
        names = frappe.db.get_all(
            contributor_doctype,
            filters={link_field: anchor_name},
            pluck="name",
        )
        for name in names or []:
            key = (contributor_doctype, name)
            if key in seen:
                continue
            seen.add(key)
            if sales_quote:
                # Optional: only suggest jobs linked to same quote
                sq = frappe.db.get_value(contributor_doctype, name, "sales_quote")
                if sq != sales_quote:
                    continue
            out.append({"job_type": contributor_doctype, "job_no": name})

    return out


def get_all_billing_jobs_from_sales_quote(sales_quote) -> List[Tuple[str, str]]:
	"""
	Return list of (job_type, job_no) for every job that should be billed from this quote:
	each leg's anchor + each leg's contributors + operational docs linked via ``sales_quote``.

	Routing legs no longer store ``job_type`` / ``job_no``; anchors are resolved the same way
	as Sales Quote customer invoicing (``_resolve_job_for_routing_leg``).
	"""
	from logistics.pricing_center.doctype.sales_quote.sales_quote import (
		_get_contributors_for_leg,
		_iter_linked_jobs_for_sales_quote,
		_resolve_job_for_routing_leg,
	)

	sq_name = sales_quote.name if hasattr(sales_quote, "name") else sales_quote
	seen: set = set()
	out: List[Tuple[str, str]] = []

	def _add(job_type: Optional[str], job_no: Optional[str]) -> None:
		if job_type and job_no and (job_type, job_no) not in seen:
			seen.add((job_type, job_no))
			out.append((job_type, job_no))

	legs = getattr(sales_quote, "routing_legs", None) or []
	for leg in legs:
		# Legacy rows may still carry job_type / job_no
		_add(getattr(leg, "job_type", None), getattr(leg, "job_no", None))
		anchor_type, anchor_name = _resolve_job_for_routing_leg(sales_quote, leg)
		_add(anchor_type, anchor_name)
		for ct, cn in _get_contributors_for_leg(leg):
			_add(ct, cn)

	for job_type, job_no in _iter_linked_jobs_for_sales_quote(sales_quote):
		_add(job_type, job_no)

	for job_type in BILLING_JOB_TYPES:
		if not frappe.db.has_column(job_type, "sales_quote"):
			continue
		for job_no in frappe.get_all(
			job_type,
			filters={"sales_quote": sq_name, "docstatus": ["!=", 2]},
			pluck="name",
			order_by="creation asc",
		):
			_add(job_type, job_no)

	return out


@frappe.whitelist()
def get_suggested_contributors_for_anchor(anchor_doctype: str, anchor_name: str, sales_quote: Optional[str] = None) -> List[Dict[str, str]]:
	"""Return candidate contributing jobs for the given anchor (e.g. Air Shipment). For use in Sales Quote routing leg UI."""
	return get_suggested_contributors(anchor_doctype, anchor_name, sales_quote=sales_quote)


def get_billing_set_items(
    anchor_type: str,
    anchor_name: str,
    contributors: List[Tuple[str, str]],
    customer: Optional[str] = None,
    description_prefix: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """
    Build combined list of invoice items for a billing set (anchor + contributors).
    contributors: list of (job_type, job_no). Each item description can be prefixed with description_prefix (e.g. "Transport: TJ-001").
    """
    all_items = []
    # Anchor items
    anchor_items = get_invoice_items_from_job(anchor_type, anchor_name, customer)
    for it in anchor_items:
        if description_prefix and it.get("description"):
            it = dict(it)
            it["description"] = f"{description_prefix} – {it['description']}"
        elif description_prefix:
            it = dict(it)
            it["description"] = description_prefix
        all_items.append(it)

    # Contributor items
    for c_type, c_name in contributors:
        contrib_items = get_invoice_items_from_job(c_type, c_name, customer)
        prefix = f"{c_type} {c_name}"
        for it in contrib_items:
            it = dict(it)
            it["description"] = it.get("description") or prefix
            if description_prefix:
                it["description"] = f"{description_prefix} – {it['description']}"
            all_items.append(it)

    return all_items
