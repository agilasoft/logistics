# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Create Purchase Invoice from logistics job/shipment costs.
"""

import frappe
from frappe import _
from frappe.model.naming import get_default_naming_series
from frappe.utils import flt, today
from typing import Dict, Any, Optional, List, Tuple
import json

from logistics.job_management.gl_reference_dimension import reference_dimension_row_dict
from logistics.job_management.recognition_engine import resolve_charge_row_cost
from logistics.special_projects.special_project_si_job_number import (
    resolve_job_number_for_special_project_charge,
)
from logistics.invoice_integration.consolidation_pi_allocation import (
    _attached_shipment_rows,
    allocation_factor_for_attached_job,
    distribute_amounts_with_rounding,
    count_attached_jobs,
)
from logistics.invoice_integration.billing_currency import (
    charge_to_company_rate_buying,
    company_currency,
    convert_amount_to_billing_currency,
    invoice_billing_context,
    resolve_cost_charge_currency,
    supplier_default_billing_currency,
)
from logistics.mice.doctype.mice_project.mice_project_charge_copy import (
    push_consolidation_charges_to_dockets,
)

JOB_DOCTYPES = (
    "Transport Job",
    "Air Shipment",
    "Sea Shipment",
    "Warehouse Job",
    "Declaration",
    "Special Project",
    "Docket",
    "MICE Project",
)

CONSOLIDATION_DOCTYPES = ("Air Consolidation", "Sea Consolidation")

CONSOLIDATION_CHARGES_CHILD_DOCTYPE = {
    "Air Consolidation": "Air Consolidation Charges",
    "Sea Consolidation": "Sea Consolidation Charges",
}

CONSOLIDATION_PLANNING_STATUS_FIELD = {
    "Air Consolidation": "air_planning_status",
    "Sea Consolidation": "sea_planning_status",
}

_PLANNING_SUBMITTED_FOR_PI_MSG = _(
    "Submit the planned shipment list (Planning status) before creating a Purchase Invoice."
)

# Child table doctype for charges (used to tag rows as Requested)
CHARGES_CHILD_DOCTYPE = {
    "Transport Job": "Transport Job Charges",
    "Air Shipment": "Air Shipment Charges",
    "Sea Shipment": "Sea Shipment Charges",
    "Warehouse Job": "Warehouse Job Charges",
    "Declaration": "Declaration Charges",
    "Special Project": "Special Project Charges",
    "Docket": "MICE Project Charges",
    "MICE Project": "MICE Project Consolidation Charges",
}

# Charge table and cost field mapping: (charges_field, cost_field, rate_field, qty_field, item_field, supplier_field)
CHARGE_CONFIG = {
    "Transport Job": ("charges", "estimated_cost", "unit_cost", "cost_quantity", "item_code", "pay_to"),
    "Air Shipment": ("charges", "estimated_cost", "estimated_cost", "quantity", "item_code", "pay_to"),
    # Sea Shipment Charges primarily use item_code (legacy rows may still have charge_item).
    "Sea Shipment": ("charges", "estimated_cost", "unit_cost", "cost_quantity", "item_code", "pay_to"),
    "Warehouse Job": ("charges", "total", "unit_rate", "quantity", "item_code", None),
    "Declaration": ("charges", "estimated_cost", "unit_cost", "quantity", "item_code", "pay_to"),
    # Special Project Charges share the cost layout with Sea Shipment (unit_cost / cost_quantity).
    "Special Project": ("charges", "estimated_cost", "unit_cost", "cost_quantity", "item_code", "pay_to"),
    # Exhibit Charges share the cost layout with Sea Shipment / Special Project.
    "Docket": ("charges", "estimated_cost", "unit_cost", "cost_quantity", "item_code", "pay_to"),
    # MICE Project programme cost lines live on consolidation_charges (total_amount).
    "MICE Project": ("consolidation_charges", "total_amount", "unit_rate", "quantity", "item_code", "pay_to"),
}

# Statuses that mean the charge is already in a PI or further along - exclude from eligibility (avoid duplicate posting)
PI_EXCLUDED_STATUSES = ("Requested", "Invoiced", "Posted", "Paid")


def _purchase_invoice_naming_context() -> Dict[str, Any]:
    """Describe Purchase Invoice naming so the client can collect series/name before insert (draft)."""
    meta = frappe.get_meta("Purchase Invoice")
    autoname = (meta.autoname or "").lower()
    options = [o for o in meta.get_naming_series_options() if o]
    return {
        "autoname": meta.autoname,
        "needs_purchase_invoice_name": autoname.startswith("prompt"),
        "naming_series_options": options,
        "default_naming_series": get_default_naming_series("Purchase Invoice") if autoname.startswith("naming_series:") else None,
        "show_naming_series": autoname.startswith("naming_series:") and len(options) > 1,
    }


def _sea_shipment_row_cost(ch) -> float:
    """Sea Shipment / Docket / Special Project charge cost — aligned with accrual rollup."""
    return resolve_charge_row_cost(ch, prefer_actual=True)


def _sea_consolidation_charge_cost(ch) -> float:
    """Sea Consolidation Charges: same resolution as Sea Shipment Charges."""
    return _sea_shipment_row_cost(ch)


def _air_consolidation_charge_cost(ch) -> float:
    """Air Consolidation Charges: prefer actual_cost, else total_amount."""
    c = flt(getattr(ch, "actual_cost", None) or 0)
    if c > 0:
        return c
    return flt(getattr(ch, "total_amount", None) or 0)


def _get_eligible_cost_rows(job, config):
    """Build list of (index, ch, cost, item_code, pay_to) for charges with cost > 0, item set, and not already requested/posted/paid."""
    charges_field, cost_field, rate_field, qty_field, item_field, supplier_field = config
    charges = list(job.get(charges_field) or [])
    rows = []
    for idx, ch in enumerate(charges):
        status = getattr(ch, "purchase_invoice_status", None)
        if status in PI_EXCLUDED_STATUSES or getattr(ch, "purchase_invoice", None):
            continue
        if job.doctype in ("Sea Shipment", "Special Project", "Docket"):
            cost = _sea_shipment_row_cost(ch)
        elif job.doctype == "MICE Project":
            # Consolidation charge lines: use total_amount (already net of discount/tax/surcharge).
            cost = flt(getattr(ch, cost_field, None) or 0)
            if cost <= 0:
                cost = flt(
                    flt(getattr(ch, rate_field, 0)) * flt(getattr(ch, qty_field or "quantity", 1) or 1),
                    0,
                )
        else:
            # Use actual_cost for PI when present and > 0, else estimated/cost_field
            cost = flt(getattr(ch, "actual_cost", None) or 0)
            if cost <= 0:
                cost = flt(
                    getattr(ch, cost_field, None)
                    or (flt(getattr(ch, rate_field, 0)) * flt(getattr(ch, qty_field or "quantity", 1) or 1)),
                    0,
                )
        if cost <= 0:
            continue
        item_code = getattr(ch, item_field, None)
        # Backward compatibility for historical Sea Shipment rows that used charge_item.
        if not item_code and job.doctype == "Sea Shipment":
            item_code = getattr(ch, "charge_item", None)
        if not item_code:
            continue
        sup = getattr(ch, supplier_field, None) if supplier_field else None
        rows.append((idx, ch, cost, item_code, sup))
    return rows


def _consolidation_item_and_supplier(consolidation_doctype: str, ch) -> Tuple[Optional[str], Optional[str]]:
    if consolidation_doctype == "Air Consolidation":
        item_code = getattr(ch, "item_code", None)
        sup = getattr(ch, "pay_to", None)
        return item_code, sup
    item_code = getattr(ch, "charge_item", None) or getattr(ch, "item_code", None)
    sup = getattr(ch, "pay_to", None)
    return item_code, sup


def _consolidation_charge_cost(consolidation_doctype: str, ch) -> float:
    if consolidation_doctype == "Air Consolidation":
        return _air_consolidation_charge_cost(ch)
    return _sea_consolidation_charge_cost(ch)


def _get_eligible_consolidation_cost_rows(c_doc) -> List[Tuple[int, Any, float, str, Optional[str]]]:
    """Eligible consolidation charges: cost > 0, item set, not locked; at least one positive allocation factor."""
    charges = list(c_doc.get("consolidation_charges") or [])
    if not charges:
        return []
    if not count_attached_jobs(c_doc):
        return []

    attached_list = _consolidation_attached_rows(c_doc)
    rows = []
    for idx, ch in enumerate(charges):
        status = getattr(ch, "purchase_invoice_status", None)
        if status in PI_EXCLUDED_STATUSES or getattr(ch, "purchase_invoice", None):
            continue
        cost = _consolidation_charge_cost(c_doc.doctype, ch)
        if cost <= 0:
            continue
        item_code, sup = _consolidation_item_and_supplier(c_doc.doctype, ch)
        if not item_code:
            continue
        any_positive = False
        for att in attached_list:
            if allocation_factor_for_attached_job(c_doc, ch, att) > 0:
                any_positive = True
                break
        if not any_positive:
            continue
        rows.append((idx, ch, cost, item_code, sup))
    return rows


def _consolidation_attached_rows(c_doc):
    """Per-shipment rows for PI splitting.

    Rows are derived from ``consolidation_packages`` (Air: ``air_freight_job``, Sea: ``sea_shipment``);
    Sea falls back to ``attached_sea_shipments`` when packages have no shipment links.
    """
    return _attached_shipment_rows(c_doc)


def _shipment_doctype_and_name_from_attached(c_doc, attached_row) -> Tuple[str, str]:
    if c_doc.doctype == "Air Consolidation":
        return "Air Shipment", getattr(attached_row, "air_freight_job", None) or ""
    return "Sea Shipment", getattr(attached_row, "sea_shipment", None) or ""


def _apply_job_number_on_pi_item(row, job_number: Optional[str]):
    if not job_number:
        return
    for k, v in reference_dimension_row_dict("Purchase Invoice Item", "Job Number", job_number).items():
        setattr(row, k, v)


def _line_job_number_for_purchase_invoice(job_type: str, job, charge) -> Optional[str]:
    """Job Number for a PI item line: leg job JCN on Special Project, else job header."""
    line_jcn = getattr(job, "job_number", None)
    if job_type == "Special Project":
        line_jcn = resolve_job_number_for_special_project_charge(job, charge) or line_jcn
    return line_jcn


def _apply_project_on_pi_item(row, project: Optional[str]):
    """Set the Project accounting dimension on a PI Item row.

    Required on consolidation PIs whose shipments belong to different ERPNext Projects:
    the header-level project would only carry one value, so the per-line value is what lets
    GL Entry tag each cost line with the correct Special Project / Exhibit project.
    """
    if not project:
        return
    try:
        if not frappe.get_meta("Purchase Invoice Item").get_field("project"):
            return
    except Exception:
        return
    setattr(row, "project", project)


def _require_consolidation_planning_submitted(c_doc) -> None:
    """Block consolidation PI until the planned shipment list is submitted."""
    field = CONSOLIDATION_PLANNING_STATUS_FIELD.get(c_doc.doctype)
    if not field:
        return
    if (c_doc.get(field) or "Draft") != "Submitted":
        frappe.throw(_PLANNING_SUBMITTED_FOR_PI_MSG)


@frappe.whitelist()
def get_eligible_charges_for_consolidation_purchase_invoice(consolidation_doctype: str, consolidation_name: str) -> Dict[str, Any]:
    if consolidation_doctype not in CONSOLIDATION_DOCTYPES:
        frappe.throw(_("Invalid consolidation type: {0}").format(consolidation_doctype))
    if not frappe.db.exists(consolidation_doctype, consolidation_name):
        frappe.throw(_("{0} {1} does not exist.").format(consolidation_doctype, consolidation_name))

    c_doc = frappe.get_doc(consolidation_doctype, consolidation_name)
    from logistics.utils.menu_permission import assert_create_from_source

    assert_create_from_source("Purchase Invoice", source_doc=c_doc)
    _require_consolidation_planning_submitted(c_doc)
    cost_rows = _get_eligible_consolidation_cost_rows(c_doc)
    if not cost_rows:
        return {
            "eligible_charges": [],
            "default_supplier": None,
            "default_posting_date": today(),
            "company": c_doc.company,
            "company_currency": company_currency(c_doc.company),
            "default_billing_currency": supplier_default_billing_currency(None, c_doc.company),
            "pi_naming": _purchase_invoice_naming_context(),
            "split_per_shipment": True,
        }

    eligible = []
    default_supplier = None
    for row_idx, (_doc_idx, ch, cost, item_code, sup) in enumerate(cost_rows):
        item_name = frappe.db.get_value("Item", item_code, "item_name") or item_code
        if sup and default_supplier is None:
            default_supplier = sup
        eligible.append({
            "index": row_idx,
            "item_code": item_code,
            "item_name": item_name,
            "cost": cost,
            "quantity": 1,
            "pay_to": sup,
            "currency": resolve_cost_charge_currency(ch, c_doc.company, c_doc.doctype),
        })
    if not default_supplier:
        default_supplier = frappe.db.get_single_value("Logistics Settings", "default_cost_supplier")
    return {
        "eligible_charges": eligible,
        "default_supplier": default_supplier,
        "default_posting_date": today(),
        "company": c_doc.company,
        "company_currency": company_currency(c_doc.company),
        "default_billing_currency": supplier_default_billing_currency(default_supplier, c_doc.company),
        "pi_naming": _purchase_invoice_naming_context(),
        "split_per_shipment": True,
    }


@frappe.whitelist()
def create_consolidation_purchase_invoice(
    consolidation_doctype: str,
    consolidation_name: str,
    supplier: Optional[str] = None,
    posting_date: Optional[str] = None,
    due_date: Optional[str] = None,
    bill_no: Optional[str] = None,
    bill_date: Optional[str] = None,
    selected_charge_indices: Optional[str] = None,
    naming_series: Optional[str] = None,
    purchase_invoice_name: Optional[str] = None,
    billing_currency: Optional[str] = None,
    exchange_rate: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Create Purchase Invoice from Air or Sea Consolidation charges.
    Each selected charge becomes one PI Item row per attached shipment, with amount split by allocation method
    and Job Number on each line.
    """
    if consolidation_doctype not in CONSOLIDATION_DOCTYPES:
        frappe.throw(_("Invalid consolidation type: {0}").format(consolidation_doctype))
    if not frappe.db.exists(consolidation_doctype, consolidation_name):
        frappe.throw(_("{0} {1} does not exist.").format(consolidation_doctype, consolidation_name))

    c_doc = frappe.get_doc(consolidation_doctype, consolidation_name)
    from logistics.utils.menu_permission import assert_create_from_source

    assert_create_from_source("Purchase Invoice", source_doc=c_doc)
    _require_consolidation_planning_submitted(c_doc)
    cost_rows_raw = _get_eligible_consolidation_cost_rows(c_doc)
    if not cost_rows_raw:
        frappe.throw(_("No eligible consolidation charges with items and allocation."))

    if selected_charge_indices is not None:
        try:
            indices = json.loads(selected_charge_indices) if isinstance(selected_charge_indices, str) else selected_charge_indices
            indices = [int(x) for x in indices]
            cost_rows = [cost_rows_raw[i] for i in indices if 0 <= i < len(cost_rows_raw)]
        except (TypeError, ValueError, IndexError):
            cost_rows = cost_rows_raw
    else:
        cost_rows = cost_rows_raw

    if not cost_rows:
        frappe.throw(_("No charges selected for Purchase Invoice."))

    resolved_supplier = supplier
    for _doc_idx, _ch, _cost, _item_code, sup in cost_rows:
        if sup:
            resolved_supplier = sup
            break
    if not resolved_supplier:
        resolved_supplier = frappe.db.get_single_value("Logistics Settings", "default_cost_supplier")
    if not resolved_supplier:
        frappe.throw(_("Supplier is required. Set pay_to on charges or pass supplier or configure default_cost_supplier in Logistics Settings."))

    mismatched = []
    for _doc_idx, _ch, _cost, _item_code, sup in cost_rows:
        if sup and sup != resolved_supplier:
            mismatched.append(sup)
    if mismatched:
        suppliers = ", ".join(sorted(set(mismatched)))
        frappe.throw(
            _(
                "Selected charges include a different supplier ({0}). "
                "Please select only charges for supplier {1}."
            ).format(suppliers, resolved_supplier)
        )

    attached_list = _consolidation_attached_rows(c_doc)
    pi_naming = _purchase_invoice_naming_context()

    pi = frappe.new_doc("Purchase Invoice")
    pi.supplier = resolved_supplier
    pi.company = c_doc.company
    pi.posting_date = posting_date or today()

    billing_ctx = invoice_billing_context(
        c_doc.company,
        billing_currency,
        exchange_rate,
        pi.posting_date,
        purpose="for_buying",
    )
    pi.currency = billing_ctx["billing_currency"]
    pi.conversion_rate = billing_ctx["billing_exchange_rate"]
    pi.ignore_pricing_rule = 1

    if due_date:
        pi.due_date = due_date
    if naming_series and (pi_naming["autoname"] or "").lower().startswith("naming_series:"):
        pi.naming_series = naming_series
    if bill_no:
        pi.bill_no = bill_no
    if bill_date:
        pi.bill_date = bill_date

    pi_meta = frappe.get_meta("Purchase Invoice")
    for dim in ("branch", "cost_center", "profit_center", "project"):
        if pi_meta.get_field(dim) and getattr(c_doc, dim, None):
            setattr(pi, dim, getattr(c_doc, dim))

    if pi_meta.get_field("reference_doctype"):
        pi.reference_doctype = consolidation_doctype
        pi.reference_name = consolidation_name

    job_numbers_for_header = []
    projects_for_header = []
    for att in attached_list:
        sh_dt, sh_name = _shipment_doctype_and_name_from_attached(c_doc, att)
        if not sh_name:
            continue
        sh_dims = frappe.db.get_value(
            sh_dt, sh_name, ["job_number", "project"], as_dict=True
        ) or {}
        if sh_dims.get("job_number"):
            job_numbers_for_header.append(sh_dims["job_number"])
        if sh_dims.get("project"):
            projects_for_header.append(sh_dims["project"])

    if pi_meta.get_field("job_number") and len(set(job_numbers_for_header)) == 1:
        pi.job_number = job_numbers_for_header[0]
    # If every linked shipment shares the same Project (Special Project / Exhibit), pin it on
    # the PI header too — the per-line value still wins inside GL Entry rows.
    if not getattr(pi, "project", None) and pi_meta.get_field("project") and len(set(projects_for_header)) == 1:
        pi.project = projects_for_header[0]

    base_remarks = pi.remarks or ""
    note = _("Auto-created from {0} {1} (allocated per shipment).").format(consolidation_doctype, consolidation_name)
    pi.remarks = f"{base_remarks}\n{note}" if base_remarks else note

    pi_item_meta = frappe.get_meta("Purchase Invoice Item")
    has_ref = pi_item_meta.get_field("reference_doctype") and pi_item_meta.get_field("reference_name")

    company_currency_code = billing_ctx["company_currency"]
    billing_cur = billing_ctx["billing_currency"]
    billing_xr = billing_ctx["billing_exchange_rate"]

    for _doc_idx, ch, charge_total, item_code, _sup in cost_rows:
        charge_currency = resolve_cost_charge_currency(ch, c_doc.company, consolidation_doctype)
        charge_to_company = charge_to_company_rate_buying(
            ch, charge_currency, company_currency_code, pi.posting_date
        )
        charge_total_billing = convert_amount_to_billing_currency(
            charge_total,
            charge_currency,
            billing_cur,
            company_currency_code,
            billing_xr,
            charge_to_company,
        )

        raw_rates = []
        for att in attached_list:
            f = allocation_factor_for_attached_job(c_doc, ch, att)
            raw_rates.append(flt(charge_total_billing) * f)
        rates = distribute_amounts_with_rounding(raw_rates, charge_total_billing)

        for att, rate in zip(attached_list, rates):
            if flt(rate, 2) <= 0:
                continue
            sh_dt, sh_name = _shipment_doctype_and_name_from_attached(c_doc, att)
            if not sh_name:
                continue
            item_payload = {
                "item_code": item_code,
                "qty": 1,
                "rate": rate,
            }
            desc_parts = []
            calc_notes = getattr(ch, "cost_calc_notes", None) or getattr(ch, "description", None)
            if calc_notes:
                desc_parts.append(calc_notes)
            desc_parts.append(_("Shipment {0}").format(sh_name))
            item_payload["description"] = "\n".join(desc_parts)

            row = pi.append("items", item_payload)
            sh_dims = frappe.db.get_value(
                sh_dt, sh_name, ["job_number", "project"], as_dict=True
            ) or {}
            _apply_job_number_on_pi_item(row, sh_dims.get("job_number"))
            _apply_project_on_pi_item(row, sh_dims.get("project"))
            if has_ref:
                row.reference_doctype = sh_dt
                row.reference_name = sh_name

    if not pi.items:
        frappe.throw(_("No Purchase Invoice lines could be built. Check allocation factors and consolidation packages."))

    pi.set_missing_values()

    insert_kw: Dict[str, Any] = {"ignore_permissions": True}
    if pi_naming["needs_purchase_invoice_name"]:
        doc_name = (purchase_invoice_name or "").strip()
        if not doc_name:
            frappe.throw(
                _(
                    "Purchase Invoice name is required with your current naming rule. "
                    "Enter it in the dialog before creating the draft; you can submit the invoice later from the form."
                )
            )
        insert_kw["set_name"] = doc_name
    pi.insert(**insert_kw)

    child_doctype = CONSOLIDATION_CHARGES_CHILD_DOCTYPE.get(consolidation_doctype)
    if child_doctype and frappe.db.table_exists(child_doctype):
        child_meta = frappe.get_meta(child_doctype)
        if child_meta.get_field("purchase_invoice_status"):
            for _doc_idx, ch, _cost, _item_code, _sup in cost_rows:
                ch_name = getattr(ch, "name", None)
                if ch_name and not (isinstance(ch_name, str) and ch_name.startswith("new")):
                    frappe.db.set_value(
                        child_doctype,
                        ch_name,
                        {
                            "purchase_invoice_status": "Requested",
                            "purchase_invoice": pi.name,
                        },
                        update_modified=False,
                    )
            frappe.db.commit()

    return {
        "ok": True,
        "message": _("Purchase Invoice {0} created successfully.").format(pi.name),
        "purchase_invoice": pi.name,
    }


@frappe.whitelist()
def get_eligible_charges_for_purchase_invoice(job_type: str, job_name: str) -> Dict[str, Any]:
    """
    Return list of eligible charges for PI creation so the user can select which to include.
    Used by the Create Purchase Invoice dialog.
    """
    if job_type not in JOB_DOCTYPES:
        frappe.throw(_("Invalid job type: {0}").format(job_type))
    if not frappe.db.exists(job_type, job_name):
        frappe.throw(_("{0} {1} does not exist.").format(job_type, job_name))
    job = frappe.get_doc(job_type, job_name)
    from logistics.utils.menu_permission import assert_create_from_source

    assert_create_from_source("Purchase Invoice", source_doc=job)
    config = CHARGE_CONFIG.get(job_type)
    if not config:
        frappe.throw(_("Purchase Invoice creation not supported for {0}.").format(job_type))

    charges_field, cost_field, rate_field, qty_field, item_field, supplier_field = config
    cost_rows = _get_eligible_cost_rows(job, config)
    if not cost_rows:
        return {
            "eligible_charges": [],
            "default_supplier": None,
            "default_posting_date": today(),
            "company": job.company,
            "company_currency": company_currency(job.company),
            "default_billing_currency": supplier_default_billing_currency(None, job.company),
            "pi_naming": _purchase_invoice_naming_context(),
        }

    # Build list for dialog: use position in cost_rows as the index we pass back (0, 1, 2, ...)
    # Invoice uses qty=1 with estimated cost as unit rate
    eligible = []
    default_supplier = None
    for row_idx, (doc_idx, ch, cost, item_code, sup) in enumerate(cost_rows):
        item_name = frappe.db.get_value("Item", item_code, "item_name") or item_code
        if sup and default_supplier is None:
            default_supplier = sup
        eligible.append({
            "index": row_idx,
            "item_code": item_code,
            "item_name": item_name,
            "cost": cost,
            "quantity": 1,
            "pay_to": sup,
            "currency": resolve_cost_charge_currency(ch, job.company),
        })
    if not default_supplier:
        default_supplier = frappe.db.get_single_value("Logistics Settings", "default_cost_supplier")
    return {
        "eligible_charges": eligible,
        "default_supplier": default_supplier,
        "default_posting_date": today(),
        "company": job.company,
        "company_currency": company_currency(job.company),
        "default_billing_currency": supplier_default_billing_currency(default_supplier, job.company),
        "pi_naming": _purchase_invoice_naming_context(),
    }


@frappe.whitelist()
def create_purchase_invoice(
    job_type: str,
    job_name: str,
    supplier: Optional[str] = None,
    posting_date: Optional[str] = None,
    due_date: Optional[str] = None,
    bill_no: Optional[str] = None,
    bill_date: Optional[str] = None,
    selected_charge_indices: Optional[str] = None,
    naming_series: Optional[str] = None,
    purchase_invoice_name: Optional[str] = None,
    billing_currency: Optional[str] = None,
    exchange_rate: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Create Purchase Invoice from job/shipment costs.

    Args:
        job_type: Transport Job, Air Shipment, Sea Shipment, Warehouse Job, or Declaration
        job_name: Name of the job document
        supplier: Optional default supplier (used when charges have no pay_to)
        posting_date: Optional posting date (default: today)
        due_date: Optional due date for the Purchase Invoice
        bill_no: Optional supplier bill / reference number
        bill_date: Optional supplier bill date
        selected_charge_indices: Optional JSON list of integers (indices into eligible charges).
            If provided, only these charges are included; otherwise all eligible charges are included.
        naming_series: Optional Naming Series (when Purchase Invoice uses naming_series autoname and multiple series exist).
        purchase_invoice_name: Required when Purchase Invoice uses Prompt naming — same as entering the name on the
            standard form before save/submit.

    Returns:
        dict with ok, message, purchase_invoice
    """
    if job_type not in JOB_DOCTYPES:
        frappe.throw(_("Invalid job type: {0}").format(job_type))

    if not frappe.db.exists(job_type, job_name):
        frappe.throw(_("{0} {1} does not exist.").format(job_type, job_name))

    job = frappe.get_doc(job_type, job_name)
    from logistics.utils.menu_permission import assert_create_from_source

    assert_create_from_source("Purchase Invoice", source_doc=job)
    config = CHARGE_CONFIG.get(job_type)
    if not config:
        frappe.throw(_("Purchase Invoice creation not supported for {0}.").format(job_type))

    charges_field, cost_field, rate_field, qty_field, item_field, supplier_field = config
    cost_rows_raw = _get_eligible_cost_rows(job, config)
    # cost_rows_raw: list of (doc_idx, ch, cost, item_code, sup)

    if not cost_rows_raw:
        frappe.throw(_("No charges with cost amount found in {0}.").format(job_type))

    # Filter by selected indices if provided (indices are 0-based into cost_rows_raw)
    if selected_charge_indices is not None:
        try:
            indices = json.loads(selected_charge_indices) if isinstance(selected_charge_indices, str) else selected_charge_indices
            indices = [int(x) for x in indices]
            cost_rows = [cost_rows_raw[i] for i in indices if 0 <= i < len(cost_rows_raw)]
        except (TypeError, ValueError, IndexError):
            cost_rows = cost_rows_raw
    else:
        cost_rows = cost_rows_raw

    if not cost_rows:
        frappe.throw(_("No charges selected for Purchase Invoice."))

    # Resolve supplier: from first row with pay_to, or argument, or settings
    resolved_supplier = supplier
    for _doc_idx, _ch, _cost, _item_code, sup in cost_rows:
        if sup:
            resolved_supplier = sup
            break
    if not resolved_supplier:
        resolved_supplier = frappe.db.get_single_value("Logistics Settings", "default_cost_supplier")
    if not resolved_supplier:
        frappe.throw(_("Supplier is required. Set pay_to on charges or pass supplier or configure default_cost_supplier in Logistics Settings."))

    # Ensure selected rows belong to a single supplier to prevent mixed-supplier invoices.
    mismatched = []
    for _doc_idx, _ch, _cost, _item_code, sup in cost_rows:
        if sup and sup != resolved_supplier:
            mismatched.append(sup)
    if mismatched:
        suppliers = ", ".join(sorted(set(mismatched)))
        frappe.throw(
            _(
                "Selected charges include a different supplier ({0}). "
                "Please select only charges for supplier {1}."
            ).format(suppliers, resolved_supplier)
        )

    pi_naming = _purchase_invoice_naming_context()

    # Create Purchase Invoice
    pi = frappe.new_doc("Purchase Invoice")
    pi.supplier = resolved_supplier
    pi.company = job.company
    pi.posting_date = posting_date or today()

    billing_ctx = invoice_billing_context(
        job.company,
        billing_currency,
        exchange_rate,
        pi.posting_date,
        purpose="for_buying",
    )
    pi.currency = billing_ctx["billing_currency"]
    pi.conversion_rate = billing_ctx["billing_exchange_rate"]
    pi.ignore_pricing_rule = 1

    if due_date:
        pi.due_date = due_date
    if naming_series and (pi_naming["autoname"] or "").lower().startswith("naming_series:"):
        pi.naming_series = naming_series
    if bill_no:
        pi.bill_no = bill_no
    if bill_date:
        pi.bill_date = bill_date

    # Copy accounting dimensions only when both job and PI have the field (design §4.2)
    pi_meta = frappe.get_meta("Purchase Invoice")
    for dim in ("branch", "cost_center", "profit_center", "project"):
        if pi_meta.get_field(dim) and getattr(job, dim, None):
            setattr(pi, dim, getattr(job, dim))

    # Set reference to job (custom fields)
    if pi_meta.get_field("reference_doctype"):
        pi.reference_doctype = job_type
        pi.reference_name = job_name
    # Job costing number for GL/profitability (design §6.3)
    if pi_meta.get_field("job_number") and getattr(job, "job_number", None):
        pi.job_number = job.job_number

    base_remarks = pi.remarks or ""
    note = _("Auto-created from {0} {1}").format(job_type, job_name)
    pi.remarks = f"{base_remarks}\n{note}" if base_remarks else note

    pi_item_meta = frappe.get_meta("Purchase Invoice Item")
    has_ref = pi_item_meta.get_field("reference_doctype") and pi_item_meta.get_field("reference_name")

    company_currency_code = billing_ctx["company_currency"]
    billing_cur = billing_ctx["billing_currency"]
    billing_xr = billing_ctx["billing_exchange_rate"]

    for _doc_idx, ch, cost, item_code, _sup in cost_rows:
        charge_currency = resolve_cost_charge_currency(ch, job.company)
        charge_to_company = charge_to_company_rate_buying(
            ch, charge_currency, company_currency_code, pi.posting_date
        )
        cost = convert_amount_to_billing_currency(
            cost,
            charge_currency,
            billing_cur,
            company_currency_code,
            billing_xr,
            charge_to_company,
        )
        # Quantity = 1, estimated cost as unit rate
        item_payload = {
            "item_code": item_code,
            "qty": 1,
            "rate": cost,
        }
        # Description: include Calc Notes (cost_calc_notes or calculation_notes)
        calc_notes = getattr(ch, "cost_calc_notes", None) or getattr(ch, "calculation_notes", None)
        if calc_notes:
            item_payload["description"] = calc_notes
        row = pi.append("items", item_payload)
        _apply_job_number_on_pi_item(row, _line_job_number_for_purchase_invoice(job_type, job, ch))
        # Project accounting dimension (Special Project / Exhibit profitability rolls up GL lines
        # by this field). Already set on the PI header; copying it onto the item row is what
        # makes the value visible on GL Entry for line-level reporting too.
        _apply_project_on_pi_item(row, getattr(job, "project", None))
        if has_ref:
            row.reference_doctype = job_type
            row.reference_name = job_name

    pi.set_missing_values()

    insert_kw: Dict[str, Any] = {"ignore_permissions": True}
    if pi_naming["needs_purchase_invoice_name"]:
        doc_name = (purchase_invoice_name or "").strip()
        if not doc_name:
            frappe.throw(
                _(
                    "Purchase Invoice name is required with your current naming rule. "
                    "Enter it in the dialog before creating the draft; you can submit the invoice later from the form."
                )
            )
        insert_kw["set_name"] = doc_name
    pi.insert(**insert_kw)

    # Update job
    frappe.db.set_value(job_type, job_name, "purchase_invoice", pi.name, update_modified=False)
    frappe.db.set_value(job_type, job_name, "date_purchase_invoice_requested", pi.posting_date, update_modified=False)

    # Tag selected charge rows as Requested (so they become read-only)
    child_doctype = CHARGES_CHILD_DOCTYPE.get(job_type)
    if child_doctype and frappe.db.table_exists(child_doctype):
        child_meta = frappe.get_meta(child_doctype)
        if child_meta.get_field("purchase_invoice_status"):
            for _doc_idx, ch, cost, item_code, _sup in cost_rows:
                ch_name = getattr(ch, "name", None)
                if ch_name and not (isinstance(ch_name, str) and ch_name.startswith("new")):
                    frappe.db.set_value(
                        child_doctype,
                        ch_name,
                        {
                            "purchase_invoice_status": "Requested",
                            "purchase_invoice": pi.name,
                        },
                        update_modified=False,
                    )
            frappe.db.commit()

    if job_type == "MICE Project":
        push_consolidation_charges_to_dockets(
            job,
            selected_charges=[ch for _doc_idx, ch, _cost, _item_code, _sup in cost_rows],
            purchase_invoice=pi.name,
        )

    return {
        "ok": True,
        "message": _("Purchase Invoice {0} created successfully.").format(pi.name),
        "purchase_invoice": pi.name,
    }
