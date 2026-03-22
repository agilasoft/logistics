# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Create intercompany Sales and Purchase Invoices when a customer Sales Invoice
(from a Sales Quote) is submitted. For each routing leg where the job's company
differs from the quote's billing company, the operating company invoices the
billing company (intercompany SI + PI).
"""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import flt, today
from typing import Dict, Any, Optional, List, Tuple

# Job types that can be intercompany legs (must have company and charges)
INTERCOMPANY_JOB_TYPES = ("Transport Job", "Air Shipment", "Sea Shipment", "Warehouse Job", "Declaration", "Declaration Order")


def is_intercompany_enabled() -> bool:
	"""Return True if Intercompany Settings has enable_intercompany_invoicing checked."""
	try:
		return bool(frappe.db.get_single_value("Intercompany Settings", "enable_intercompany_invoicing"))
	except Exception:
		return False


def get_relationship(billing_company: str, operating_company: str) -> Optional[Dict[str, str]]:
	"""
	Get internal_customer and internal_supplier for a billing/operating company pair.
	Returns None if not configured.
	"""
	settings = frappe.get_single("Intercompany Settings")
	for row in settings.get("relationships") or []:
		if row.get("billing_company") == billing_company and row.get("operating_company") == operating_company:
			return {
				"internal_customer": row.get("internal_customer"),
				"internal_supplier": row.get("internal_supplier"),
			}
	return None


def get_invoice_items_from_job(
	job_type: str, job_name: str, customer_for_sea: Optional[str] = None
) -> List[Dict[str, Any]]:
	"""
	Extract invoice line items from a job (selling/revenue side). Unified with billing module.
	Used for intercompany SI and PI so amounts match the customer invoice for that leg.
	"""
	from logistics.billing.cross_module_billing import get_invoice_items_from_job as billing_get_items
	return billing_get_items(job_type, job_name, customer=customer_for_sea)


@frappe.whitelist()
def create_intercompany_invoices_for_quote(
	sales_quote_name: str,
	billing_company: str,
	trigger_si: Optional[str] = None,
	posting_date: Optional[str] = None,
) -> Dict[str, Any]:
	"""
	For each routing leg where job.company != billing_company, create
	intercompany Sales Invoice (operating company -> billing company) and
	Purchase Invoice (billing company <- operating company).
	"""
	if not is_intercompany_enabled():
		return {"success": True, "created": 0, "message": _("Intercompany invoicing is disabled.")}

	sales_quote = frappe.get_doc("Sales Quote", sales_quote_name)
	legs = getattr(sales_quote, "routing_legs", None) or []
	if not legs:
		return {"success": True, "created": 0, "message": _("No routing legs.")}

	posting_date = posting_date or today()
	end_customer = sales_quote.customer
	created_logs = []
	errors = []

	# Cross-module billing: include every job (anchor + contributors) from each leg
	from logistics.billing.cross_module_billing import get_all_billing_jobs_from_sales_quote
	all_jobs = get_all_billing_jobs_from_sales_quote(sales_quote)

	for job_type, job_no in all_jobs:
		if job_type not in INTERCOMPANY_JOB_TYPES:
			continue

		try:
			job_doc = frappe.get_doc(job_type, job_no)
		except Exception as e:
			errors.append(_("Job {0} {1}: {2}").format(job_type, job_no, str(e)))
			continue

		operating_company = getattr(job_doc, "company", None)
		if not operating_company or operating_company == billing_company:
			continue

		rel = get_relationship(billing_company, operating_company)
		if not rel or not rel.get("internal_customer") or not rel.get("internal_supplier"):
			errors.append(_("Job {0} {1}: no Intercompany Relationship for Billing Company {2} and Operating Company {3}.").format(
				job_type, job_no, billing_company, operating_company
			))
			continue

		existing = frappe.db.exists(
			"Intercompany Invoice Log",
			{
				"sales_quote": sales_quote_name,
				"job_type": job_type,
				"job_no": job_no,
				"status": "Created",
			},
		)
		if existing:
			continue

		items = get_invoice_items_from_job(job_type, job_no, customer_for_sea=end_customer)
		if not items:
			errors.append(_("Job {0} {1}: no charge items.").format(job_type, job_no))
			continue

		# Leg for log/display (first leg that references this job, or None)
		leg_for_log = next((l for l in legs if getattr(l, "job_type") == job_type and getattr(l, "job_no") == job_no), None)
		if not leg_for_log:
			for l in legs:
				contrib = getattr(l, "bill_with_contributors", None) or []
				for c in contrib:
					if getattr(c, "contributor_job_type", None) == job_type and getattr(c, "contributor_job_no", None) == job_no:
						leg_for_log = l
						break
				if leg_for_log:
					break
		if not leg_for_log and legs:
			leg_for_log = legs[0]

		try:
			si_name, pi_name = _create_intercompany_pair(
				leg=leg_for_log,
				job_doc=job_doc,
				billing_company=billing_company,
				operating_company=operating_company,
				internal_customer=rel["internal_customer"],
				internal_supplier=rel["internal_supplier"],
				sales_quote_name=sales_quote_name,
				trigger_si=trigger_si,
				posting_date=posting_date,
				items=items,
			)
		except Exception as e:
			frappe.log_error(
				title="Intercompany Invoice Creation Failed",
				message=frappe.get_traceback(),
			)
			errors.append(_("Job {0} {1}: {2}").format(job_type, job_no, str(e)))
			_create_log_entry(
				sales_quote_name=sales_quote_name,
				trigger_si=trigger_si,
				leg=leg_for_log,
				job_type=job_type,
				job_no=job_no,
				billing_company=billing_company,
				operating_company=operating_company,
				status="Failed",
			)
			continue

		_create_log_entry(
			sales_quote_name=sales_quote_name,
			trigger_si=trigger_si,
			leg=leg_for_log,
			job_type=job_type,
			job_no=job_no,
			billing_company=billing_company,
			operating_company=operating_company,
			status="Created",
			intercompany_sales_invoice=si_name,
			intercompany_purchase_invoice=pi_name,
		)
		created_logs.append({"job": f"{job_type} {job_no}", "si": si_name, "pi": pi_name})

	if errors:
		frappe.msgprint(
			_("Intercompany invoices created: {0}. Some legs had errors: {1}").format(
				len(created_logs), " | ".join(errors[:5])
			),
			indicator="orange",
		)

	return {
		"success": True,
		"created": len(created_logs),
		"logs": created_logs,
		"errors": errors,
		"message": _("Created {0} intercompany invoice pair(s).").format(len(created_logs)) if created_logs else (errors[0] if errors else _("No intercompany legs to invoice.")),
	}


def _create_log_entry(
	sales_quote_name: str,
	trigger_si: Optional[str],
	leg,
	job_type: str,
	job_no: str,
	billing_company: str,
	operating_company: str,
	status: str,
	intercompany_sales_invoice: Optional[str] = None,
	intercompany_purchase_invoice: Optional[str] = None,
) -> None:
	log = frappe.new_doc("Intercompany Invoice Log")
	log.sales_quote = sales_quote_name
	log.customer_sales_invoice = trigger_si or ""
	log.leg_order = getattr(leg, "idx", None)
	log.job_type = job_type
	log.job_no = job_no
	log.billing_company = billing_company
	log.operating_company = operating_company
	log.status = status
	if intercompany_sales_invoice:
		log.intercompany_sales_invoice = intercompany_sales_invoice
	if intercompany_purchase_invoice:
		log.intercompany_purchase_invoice = intercompany_purchase_invoice
	log.insert(ignore_permissions=True)


def _create_intercompany_pair(
	leg,
	job_doc,
	billing_company: str,
	operating_company: str,
	internal_customer: str,
	internal_supplier: str,
	sales_quote_name: str,
	trigger_si: Optional[str],
	posting_date: str,
	items: List[Dict[str, Any]],
) -> Tuple[str, str]:
	"""Create one intercompany Sales Invoice (operating co) and one Purchase Invoice (billing co). Returns (si_name, pi_name)."""
	leg_order = getattr(leg, "idx", "")
	job_type = job_doc.doctype
	job_no = job_doc.name
	desc_suffix = _("{0} {1} (Leg {2}) - Intercompany").format(job_type, job_no, leg_order)

	# 1) Sales Invoice: operating company -> billing company (internal_customer)
	si = frappe.new_doc("Sales Invoice")
	si.company = operating_company
	si.customer = internal_customer
	si.posting_date = posting_date
	si.quotation_no = sales_quote_name
	si.remarks = _("Intercompany: from Sales Quote {0}. Trigger SI: {1}").format(sales_quote_name, trigger_si or "-")
	if getattr(job_doc, "branch", None):
		si.branch = job_doc.branch
	if getattr(job_doc, "cost_center", None):
		si.cost_center = job_doc.cost_center
	if getattr(job_doc, "profit_center", None):
		si.profit_center = job_doc.profit_center

	for it in items:
		row = si.append("items", {
			"item_code": it.get("item_code"),
			"item_name": it.get("item_name"),
			"qty": flt(it.get("qty"), 2),
			"rate": flt(it.get("rate"), 2),
			"uom": it.get("uom"),
			"description": it.get("description") or desc_suffix,
		})
		# Link to job if Sales Invoice Item has reference fields
		si_item_meta = frappe.get_meta("Sales Invoice Item")
		if si_item_meta.get_field("reference_doctype") and si_item_meta.get_field("reference_name"):
			row.reference_doctype = job_type
			row.reference_name = job_no

	si.set_missing_values()
	si.insert(ignore_permissions=True)
	si.submit()

	# 2) Purchase Invoice: billing company <- operating company (internal_supplier)
	pi = frappe.new_doc("Purchase Invoice")
	pi.company = billing_company
	pi.supplier = internal_supplier
	pi.posting_date = posting_date
	pi.remarks = _("Intercompany: from Sales Quote {0}. Trigger SI: {1}").format(sales_quote_name, trigger_si or "-")
	# Use quote for branch/cost_center if needed
	sales_quote = frappe.get_doc("Sales Quote", sales_quote_name)
	if getattr(sales_quote, "branch", None):
		pi.branch = sales_quote.branch
	if getattr(sales_quote, "cost_center", None):
		pi.cost_center = sales_quote.cost_center
	if getattr(sales_quote, "profit_center", None):
		pi.profit_center = sales_quote.profit_center

	for it in items:
		row = pi.append("items", {
			"item_code": it.get("item_code"),
			"qty": flt(it.get("qty"), 2),
			"rate": flt(it.get("rate"), 2),
			"uom": it.get("uom"),
			"description": it.get("description") or desc_suffix,
		})
		pi_item_meta = frappe.get_meta("Purchase Invoice Item")
		if pi_item_meta.get_field("reference_doctype") and pi_item_meta.get_field("reference_name"):
			row.reference_doctype = job_type
			row.reference_name = job_no

	pi.set_missing_values()
	pi.insert(ignore_permissions=True)
	pi.submit()

	return (si.name, pi.name)


@frappe.whitelist()
def create_intercompany_invoices_from_sales_invoice(sales_invoice_name: str) -> Dict[str, Any]:
	"""
	Manually trigger intercompany invoice creation for the Sales Quote linked to this Sales Invoice.
	Called from UI or when automatic trigger was skipped.
	"""
	si = frappe.get_doc("Sales Invoice", sales_invoice_name)
	quote_name = getattr(si, "quotation_no", None)
	if not quote_name or not frappe.db.exists("Sales Quote", quote_name):
		frappe.throw(_("Sales Invoice {0} is not linked to a Sales Quote.").format(sales_invoice_name))
	billing_company = si.company
	return create_intercompany_invoices_for_quote(
		sales_quote_name=quote_name,
		billing_company=billing_company,
		trigger_si=sales_invoice_name,
		posting_date=si.posting_date,
	)
