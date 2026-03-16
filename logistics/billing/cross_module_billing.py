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
from typing import Dict, List, Any, Optional, Tuple

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
            est_rev = flt(getattr(ch, "estimated_revenue", 0))
            rate = est_rev / qty if (est_rev > 0 and qty > 0) else unit_rate
            items.append({
                "item_code": item_code,
                "item_name": getattr(ch, "item_name", None) or item_code,
                "qty": qty,
                "rate": rate,
                "uom": getattr(ch, "uom", None),
                "description": None,
            })

    elif job_type == "Sea Shipment":
        from logistics.utils.charges_calculation import get_charge_bill_to_customers
        charges = doc.get("charges") or []
        for ch in charges:
            if customer and customer not in get_charge_bill_to_customers(ch):
                continue
            items.append({
                "item_code": getattr(ch, "charge_item", None),
                "item_name": getattr(ch, "charge_name", None),
                "qty": 1,
                "rate": flt(getattr(ch, "selling_amount", 0)),
                "uom": None,
                "description": getattr(ch, "charge_description", None),
            })

    elif job_type == "Air Shipment":
        charges = doc.get("charges") or []
        for ch in charges:
            item_code = getattr(ch, "item_code", None)
            if not item_code:
                continue
            qty = flt(getattr(ch, "quantity", 1))
            rate = flt(getattr(ch, "rate", 0))
            total = flt(getattr(ch, "total_amount", 0))
            if total > 0 and qty > 0:
                rate = total / qty
            items.append({
                "item_code": item_code,
                "item_name": getattr(ch, "item_name", None) or item_code,
                "qty": qty,
                "rate": rate,
                "uom": getattr(ch, "uom", None),
                "description": None,
            })

    elif job_type == "Warehouse Job":
        charges = doc.get("charges") or []
        for ch in charges:
            item_code = getattr(ch, "item_code", None) or getattr(ch, "item", None)
            if not item_code:
                continue
            qty = flt(getattr(ch, "quantity", 1))
            rate = flt(getattr(ch, "rate", 0))
            est_rev = flt(getattr(ch, "estimated_revenue", 0))
            if est_rev > 0 and qty > 0:
                rate = est_rev / qty
            items.append({
                "item_code": item_code,
                "item_name": getattr(ch, "item_name", None) or item_code,
                "qty": qty,
                "rate": rate,
                "uom": getattr(ch, "uom", None),
                "description": None,
            })

    elif job_type in ("Declaration", "Declaration Order"):
        charges = doc.get("charges") or []
        for ch in charges:
            item_code = getattr(ch, "item_code", None)
            if not item_code:
                continue
            qty = flt(getattr(ch, "quantity", 1)) or 1
            rate = flt(getattr(ch, "unit_rate", 0)) or flt(getattr(ch, "rate", 0))
            total = flt(getattr(ch, "total_amount", 0))
            est_rev = flt(getattr(ch, "estimated_revenue", 0))
            if total > 0 and qty > 0:
                rate = total / qty
            elif est_rev > 0 and qty > 0:
                rate = est_rev / qty
            items.append({
                "item_code": item_code,
                "item_name": getattr(ch, "item_name", None) or item_code,
                "qty": qty,
                "rate": rate,
                "uom": getattr(ch, "uom", None),
                "description": None,
            })

    return items


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
	each leg's anchor + each leg's contributors. Used for intercompany (one pair per job).
	"""
	legs = getattr(sales_quote, "routing_legs", None) or []
	seen = set()
	out = []
	for leg in legs:
		job_type = getattr(leg, "job_type", None)
		job_no = getattr(leg, "job_no", None)
		if job_type and job_no and (job_type, job_no) not in seen:
			seen.add((job_type, job_no))
			out.append((job_type, job_no))
		# Contributors
		contrib_list = getattr(leg, "bill_with_contributors", None)
		if contrib_list:
			for c in contrib_list:
				ct = getattr(c, "contributor_job_type", None)
				cn = getattr(c, "contributor_job_no", None)
				if ct and cn and (ct, cn) not in seen:
					seen.add((ct, cn))
					out.append((ct, cn))
		else:
			leg_name = getattr(leg, "name", None)
			if leg_name:
				for c in frappe.get_all(
					"Sales Quote Routing Leg Contributor",
					filters={"parent": leg_name, "parenttype": "Sales Quote Routing Leg"},
					fields=["contributor_job_type", "contributor_job_no"],
				):
					ct, cn = c.get("contributor_job_type"), c.get("contributor_job_no")
					if ct and cn and (ct, cn) not in seen:
						seen.add((ct, cn))
						out.append((ct, cn))
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
