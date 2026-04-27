# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Freight 95/5 rule: validate charge rows and build Sales Invoice item payloads."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

import frappe
from frappe import _
from frappe.utils import cint, flt

FREIGHT_CATEGORY = "Freight"


def _meta_has(doctype: str, fieldname: str) -> bool:
    return bool(frappe.get_meta(doctype).get_field(fieldname))


def clear_freight_95_5_if_not_freight(doc) -> None:
    if getattr(doc, "charge_category", None) == FREIGHT_CATEGORY:
        return
    if _meta_has(doc.doctype, "apply_95_5_rule"):
        doc.apply_95_5_rule = 0
    if _meta_has(doc.doctype, "taxable_freight_item"):
        doc.taxable_freight_item = None
    if _meta_has(doc.doctype, "taxable_freight_item_tax_template"):
        doc.taxable_freight_item_tax_template = None


def _main_charge_item_code(doc) -> Optional[str]:
    return getattr(doc, "item_code", None) or getattr(doc, "charge_item", None)


def validate_freight_95_5_row(doc, main_item_field: Optional[str] = None) -> None:
    if not _meta_has(doc.doctype, "apply_95_5_rule"):
        return
    clear_freight_95_5_if_not_freight(doc)
    if getattr(doc, "charge_category", None) != FREIGHT_CATEGORY:
        return
    if not getattr(doc, "apply_95_5_rule", 0):
        return
    main_item = getattr(doc, main_item_field, None) if main_item_field else None
    main_item = main_item or _main_charge_item_code(doc)
    taxable = getattr(doc, "taxable_freight_item", None)
    if not taxable:
        frappe.throw(_("Taxable Freight Item is required when Apply 95/5 rule is checked."))
    item_cat = frappe.db.get_value("Item", taxable, "custom_charge_category")
    if item_cat != FREIGHT_CATEGORY:
        frappe.throw(
            _("Taxable Freight Item must have Charge Category (Item) set to Freight."),
            title=_("Invalid Taxable Freight Item"),
        )
    if main_item and taxable == main_item:
        frappe.throw(_("Taxable Freight Item must be different from the charge Item."))


def freight_split_applies(ch) -> bool:
    return (
        getattr(ch, "charge_category", None) == FREIGHT_CATEGORY
        and getattr(ch, "apply_95_5_rule", 0)
        and getattr(ch, "taxable_freight_item", None)
    )


def _rate_precision(company: Optional[str] = None) -> int:
    try:
        p = frappe.get_meta("Sales Invoice Item").get_field("rate")
        if p and p.precision is not None:
            return cint(p.precision)
    except Exception:
        pass
    if company:
        ccy = frappe.db.get_value("Company", company, "default_currency")
        if ccy:
            frac = frappe.db.get_value("Currency", ccy, "fraction")
            if frac is not None:
                return cint(frac)
    return 2


def split_freight_amounts(total: float, company: Optional[str] = None) -> Tuple[float, float]:
    prec = _rate_precision(company)
    total = flt(total, prec)
    amt_95 = flt(total * 0.95, prec)
    amt_5 = flt(total - amt_95, prec)
    return amt_95, amt_5


def _taxable_template(ch) -> Optional[str]:
    return getattr(ch, "taxable_freight_item_tax_template", None) or None


def _main_tax_template(ch, job_type: str) -> Optional[str]:
    # Match legacy sales_invoice_api: only Sea Shipment passes charge row item_tax_template.
    if job_type != "Sea Shipment":
        return None
    return getattr(ch, "item_tax_template", None) or None


def build_sales_invoice_item_payloads_for_charge(
    ch,
    revenue: float,
    *,
    item_code: str,
    item_name: Optional[str],
    description: Optional[str],
    job_type: str,
    company: Optional[str],
    currency: Optional[str] = None,
    cost_center: Optional[str] = None,
    profit_center: Optional[str] = None,
    job_ref: Optional[str] = None,
    si_item_meta=None,
    reference_doctype: Optional[str] = None,
    reference_name: Optional[str] = None,
    line_qty: Optional[float] = None,
    line_rate: Optional[float] = None,
    uom: Optional[str] = None,
) -> Tuple[List[Dict[str, Any]], List[int]]:
    """
    Returns (payloads, indices_in_payloads_that_need_item_tax_template_cleared_after_set_missing_values).
    """
    if si_item_meta is None:
        si_item_meta = frappe.get_meta("Sales Invoice Item")

    def _dims(payload: Dict[str, Any]) -> None:
        if uom and si_item_meta.get_field("uom"):
            payload["uom"] = uom
        if cost_center and si_item_meta.get_field("cost_center"):
            payload["cost_center"] = cost_center
        if profit_center and si_item_meta.get_field("profit_center"):
            payload["profit_center"] = profit_center
        if job_ref:
            it_jn = si_item_meta.get_field("job_number")
            if it_jn and _link_field_writable(it_jn):
                payload["job_number"] = job_ref
            it_jc = si_item_meta.get_field("job_costing_number")
            if it_jc and _link_field_writable(it_jc):
                payload["job_costing_number"] = job_ref
        if reference_doctype and reference_name:
            if si_item_meta.get_field("reference_doctype") and si_item_meta.get_field("reference_name"):
                payload["reference_doctype"] = reference_doctype
                payload["reference_name"] = reference_name

    payloads: List[Dict[str, Any]] = []
    clear_tax_payload_indices: List[int] = []

    if freight_split_applies(ch):
        split_total = flt(revenue, _rate_precision(company))
        amt_95, amt_5 = split_freight_amounts(split_total, company)
        p1: Dict[str, Any] = {
            "item_code": item_code,
            "item_name": item_name or item_code,
            "qty": 1,
            "rate": amt_95,
            "item_tax_template": None,
        }
        if description:
            p1["description"] = description
        if currency and si_item_meta.get_field("currency"):
            p1["currency"] = currency
        _dims(p1)
        payloads.append(p1)
        clear_tax_payload_indices.append(0)

        t_item = getattr(ch, "taxable_freight_item", None)
        t_name = frappe.db.get_value("Item", t_item, "item_name") if t_item else None
        p2: Dict[str, Any] = {
            "item_code": t_item,
            "item_name": t_name or t_item,
            "qty": 1,
            "rate": amt_5,
        }
        tt = _taxable_template(ch)
        if tt and si_item_meta.get_field("item_tax_template"):
            p2["item_tax_template"] = tt
        if description:
            p2["description"] = description
        if currency and si_item_meta.get_field("currency"):
            p2["currency"] = currency
        _dims(p2)
        payloads.append(p2)
        return payloads, clear_tax_payload_indices

    prec = _rate_precision(company)
    if line_qty is not None and line_rate is not None:
        q = flt(line_qty, prec)
        r = flt(line_rate, prec)
    else:
        q = 1.0
        r = flt(revenue, prec)
    single: Dict[str, Any] = {
        "item_code": item_code,
        "item_name": item_name or item_code,
        "qty": q,
        "rate": r,
    }
    if description:
        single["description"] = description
    if currency and si_item_meta.get_field("currency"):
        single["currency"] = currency
    tmpl = _main_tax_template(ch, job_type)
    if tmpl and si_item_meta.get_field("item_tax_template"):
        single["item_tax_template"] = tmpl
    _dims(single)
    payloads.append(single)
    return payloads, []


def _link_field_writable(field) -> bool:
    if not field:
        return False
    if field.fieldtype != "Link":
        return True
    opt = (field.options or "").strip()
    if not opt:
        return True
    return bool(frappe.db.exists("DocType", opt))


def apply_freight_95_post_missing_values(si, freight_95_item_indices: List[int]) -> None:
    """Clear tax on 95% freight lines after ERPNext fills defaults from Item master."""
    if not freight_95_item_indices:
        return
    for idx in freight_95_item_indices:
        if 0 <= idx < len(si.items):
            row = si.items[idx]
            row.item_tax_template = None
            if hasattr(row, "item_tax_rate"):
                row.item_tax_rate = "{}"
    _recalculate_si_taxes(si)


def _recalculate_si_taxes(si) -> None:
    try:
        from erpnext.controllers.taxes_and_totals import calculate_taxes_and_totals

        calculate_taxes_and_totals(si)
        return
    except Exception:
        pass
    for meth in ("calculate_taxes_and_totals", "calculate_taxes"):
        if hasattr(si, meth):
            try:
                getattr(si, meth)()
                return
            except Exception:
                continue
