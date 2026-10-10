# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""One Periodic Billing action creates the customer invoice and optional linked postings.

Internal billing and intercompany transactions use the selected Periodic Billing
charge amounts. They are offered only for Warehouse Jobs that are linked services.
"""

from __future__ import annotations

import json
from typing import Any, Optional

import frappe
from frappe import _
from frappe.utils import flt, today

from logistics.intercompany.invoice_guard import INTERCOMPANY_SI_REMARKS_PREFIX
from logistics.warehousing.periodic_billing_posting_rules import (
	classify_periodic_billing_charges,
	groups_for_selection,
)


@frappe.whitelist()
def get_periodic_billing_posting_options(periodic_billing: str) -> dict:
	"""Charges and which optional postings the Create Billing dialog can offer."""
	pb = _load_periodic_billing(periodic_billing)
	classified = _classify_doc(pb)
	charges = []
	for row in classified["charges"]:
		charges.append(
			{
				"idx": row.get("idx"),
				"item_code": row.get("item_code") or "",
				"item_name": row.get("item_name") or row.get("item_code") or "",
				"quantity": row.get("quantity") or 0,
				"amount": row.get("amount") or 0,
				"warehouse_job": row.get("warehouse_job") or "",
				"posting": row.get("posting") or "",
			}
		)
	return {
		"customer": pb.customer,
		"company": pb.company,
		"default_posting_date": pb.date or today(),
		"charges": charges,
		"show_internal_billing": classified["show_internal_billing"],
		"show_intercompany": classified["show_intercompany"],
		"intercompany_disabled": classified["intercompany_disabled"],
	}


@frappe.whitelist()
def create_billing(
	periodic_billing: str,
	posting_date: Optional[str] = None,
	customer: Optional[str] = None,
	selected_charge_idxs: Optional[str] = None,
	internal_billing: int = 0,
	intercompany: int = 0,
) -> dict:
	"""Create the customer Sales Invoice and any checked linked postings."""
	pb = _load_periodic_billing(periodic_billing)
	from logistics.utils.menu_permission import assert_perm

	assert_perm("Sales Invoice", "create")
	run_internal = _truthy(internal_billing)
	run_intercompany = _truthy(intercompany)
	if run_internal:
		assert_perm("Journal Entry", "create")
	if run_intercompany:
		assert_perm("Sales Invoice", "create")
		assert_perm("Purchase Invoice", "create")

	selected = _parse_idxs(selected_charge_idxs)
	if not selected:
		frappe.throw(_("Select at least one charge."))

	classified = _classify_doc(pb)
	groups = groups_for_selection(classified["charges"], selected)
	if not groups["customer_lines"]:
		frappe.throw(_("Select at least one charge with an item and an amount."))

	customer = (customer or pb.customer or "").strip()
	if not customer:
		frappe.throw(_("Customer is required."))
	posting_date = posting_date or pb.date or today()

	sales_invoice = _create_customer_sales_invoice(
		pb,
		groups["customer_lines"],
		selected,
		customer=customer,
		posting_date=posting_date,
	)
	journal_entries = []
	intercompany_logs = []
	errors = []

	if run_internal:
		for group in groups["internal"]:
			try:
				journal_name = _create_internal_billing_journal(
					pb, group, customer=customer, posting_date=posting_date
				)
				if journal_name:
					journal_entries.append(
						{"job": group["warehouse_job"], "journal_entry": journal_name}
					)
			except frappe.ValidationError as exc:
				errors.append(_("Warehouse Job {0}: {1}").format(group["warehouse_job"], str(exc)))
			except Exception as exc:
				frappe.log_error(title="Periodic Billing Internal Billing", message=frappe.get_traceback())
				errors.append(_("Warehouse Job {0}: {1}").format(group["warehouse_job"], str(exc)))

	if run_intercompany:
		for group in groups["intercompany"]:
			try:
				pair = _create_intercompany_for_group(
					pb,
					group,
					customer_sales_invoice=sales_invoice,
					posting_date=posting_date,
				)
				if pair:
					intercompany_logs.append(pair)
			except frappe.ValidationError as exc:
				errors.append(_("Warehouse Job {0}: {1}").format(group["warehouse_job"], str(exc)))
			except Exception as exc:
				frappe.log_error(title="Periodic Billing Intercompany", message=frappe.get_traceback())
				errors.append(_("Warehouse Job {0}: {1}").format(group["warehouse_job"], str(exc)))

	if run_internal and not groups["internal"] and not journal_entries:
		errors.append(_("No selected charge is an internal billing line."))
	if run_intercompany and not groups["intercompany"] and not intercompany_logs:
		errors.append(_("No selected charge is an intercompany line."))

	return {
		"ok": True,
		"sales_invoice": sales_invoice,
		"journal_entries": journal_entries,
		"intercompany": intercompany_logs,
		"errors": errors,
		"message": _("Sales Invoice {0} created.").format(sales_invoice),
	}


def _load_periodic_billing(name: str):
	from logistics.utils.menu_permission import assert_source_read

	if not name or not frappe.db.exists("Periodic Billing", name):
		frappe.throw(_("Periodic Billing {0} does not exist.").format(name))
	return assert_source_read("Periodic Billing", name)


def _classify_doc(pb) -> dict:
	from logistics.billing.cross_module_billing import (
		get_main_job_company,
		resolve_internal_job_main_job,
	)
	from logistics.intercompany.intercompany_invoice import is_intercompany_enabled

	charges = [_charge_dict(row) for row in (pb.charges or [])]
	job_names = sorted({row["warehouse_job"] for row in charges if row["warehouse_job"]})
	jobs = {}
	for job_name in job_names:
		if not frappe.db.exists("Warehouse Job", job_name):
			continue
		job = frappe.get_doc("Warehouse Job", job_name)
		main_type, main_name = resolve_internal_job_main_job("Warehouse Job", job_name)
		main_company = get_main_job_company(main_type, main_name) if main_type and main_name else None
		jobs[job_name] = {
			"company": getattr(job, "company", None) or "",
			"is_linked": bool(main_type and main_name and main_company),
			"main_service_type": main_type or "",
			"main_service": main_name or "",
			"main_company": main_company or "",
		}
	settings = []
	try:
		settings = frappe.get_single("Intercompany Settings").get("relationships") or []
	except Exception:
		settings = []
	return classify_periodic_billing_charges(
		charges,
		jobs,
		intercompany_enabled=is_intercompany_enabled(),
		relationships=settings,
	)


def _charge_dict(row) -> dict:
	return {
		"idx": int(getattr(row, "idx", 0) or 0),
		"item_code": getattr(row, "item", None) or getattr(row, "item_code", None) or "",
		"item_name": getattr(row, "item_name", None) or "",
		"description": getattr(row, "description", None) or "",
		"uom": getattr(row, "uom", None) or None,
		"quantity": flt(getattr(row, "quantity", 0)),
		"rate": flt(getattr(row, "unit_rate", 0)),
		"total": flt(getattr(row, "total", 0)),
		"warehouse_job": getattr(row, "warehouse_job", None) or "",
	}


def _create_customer_sales_invoice(pb, lines, selected_idxs, *, customer: str, posting_date: str) -> str:
	from logistics.invoice_integration.sales_invoice_api import ensure_invoice_name_for_server_insert
	from logistics.warehousing.api import _safe_meta_fieldnames

	company = getattr(pb, "company", None)
	if not company:
		frappe.throw(_("Company is required on Periodic Billing."))
	si = frappe.new_doc("Sales Invoice")
	si.customer = customer
	si.company = company
	si.posting_date = posting_date
	header_fields = _safe_meta_fieldnames("Sales Invoice")
	for fieldname in ("branch", "cost_center", "profit_center", "job_number"):
		value = getattr(pb, fieldname, None)
		if value and fieldname in header_fields:
			setattr(si, fieldname, value)
	if "periodic_billing" in header_fields:
		si.periodic_billing = pb.name
	note = _("Auto-created from Periodic Billing {0}").format(pb.name)
	if pb.date_from and pb.date_to:
		note = "{0}\n{1}".format(note, _("Period: {0} to {1}").format(pb.date_from, pb.date_to))
	si.remarks = note
	item_fields = _safe_meta_fieldnames("Sales Invoice Item")
	for line in lines:
		payload = {
			"item_code": line["item_code"],
			"qty": line["qty"] or 0,
			"rate": line["rate"] or 0,
		}
		if line.get("uom") and "uom" in item_fields:
			payload["uom"] = line["uom"]
		if line.get("item_name") and "item_name" in item_fields:
			payload["item_name"] = line["item_name"]
		if line.get("description") and "description" in item_fields:
			payload["description"] = line["description"]
		if getattr(pb, "cost_center", None) and "cost_center" in item_fields:
			payload["cost_center"] = pb.cost_center
		si.append("items", payload)
	ensure_invoice_name_for_server_insert(si)
	si.insert()
	_mark_selected_charges_invoiced(pb, selected_idxs, si.name)
	return si.name


def _mark_selected_charges_invoiced(pb, selected_idxs, sales_invoice: str) -> None:
	selected = {int(idx) for idx in selected_idxs}
	for row in pb.charges or []:
		if int(getattr(row, "idx", 0) or 0) not in selected:
			continue
		row.invoiced = 1
		row.sales_invoice = sales_invoice
	pb.sales_invoice = sales_invoice
	pb.flags.ignore_permissions = True
	pb.save()


def _create_internal_billing_journal(pb, group, *, customer: str, posting_date: str) -> Optional[str]:
	from logistics.billing.internal_billing import (
		_append_revenue_transfer_rows,
		_submit_internal_billing_journal_entry,
	)

	job_name = group["warehouse_job"]
	remark = _("Internal Billing - Periodic Billing {0} - Warehouse Job {1}").format(pb.name, job_name)
	if frappe.db.exists("Journal Entry", {"user_remark": remark, "docstatus": 1}):
		frappe.throw(_("Internal billing for this Periodic Billing was already posted."))
	main_type = group["main_service_type"]
	main_name = group["main_service"]
	if not frappe.db.exists(main_type, main_name):
		frappe.throw(_("Main Service {0} {1} was not found.").format(main_type, main_name))
	main_job = frappe.get_doc(main_type, main_name)
	linked_job = frappe.get_doc("Warehouse Job", job_name)
	je_row_has_jcn = bool(frappe.get_meta("Journal Entry Account").get_field("job_number"))
	company = group["operating_company"]
	entries = []
	for line in group["lines"]:
		amount = flt(line.get("qty")) * flt(line.get("rate"))
		_append_revenue_transfer_rows(
			entries,
			main_job,
			linked_job,
			amount,
			line["item_code"],
			company,
			je_row_has_jcn,
		)
	if not entries:
		return None
	return _submit_internal_billing_journal_entry(
		entries,
		company,
		posting_date,
		remark,
		pb,
		customer,
		billing_main_job=main_job,
	)


def _create_intercompany_for_group(pb, group, *, customer_sales_invoice: str, posting_date: str) -> Optional[dict]:
	job_name = group["warehouse_job"]
	if not group.get("internal_customer") or not group.get("internal_supplier"):
		frappe.throw(
			_(
				"No Intercompany Relationship for Main Job Company {0} and Operating Company {1}."
			).format(group.get("main_company"), group.get("operating_company"))
		)
	existing_filters = {
		"job_type": "Warehouse Job",
		"job_no": job_name,
		"status": "Created",
		"periodic_billing": pb.name,
	}
	if frappe.get_meta("Intercompany Invoice Log").get_field("periodic_billing") and frappe.db.exists(
		"Intercompany Invoice Log", existing_filters
	):
		frappe.throw(_("Intercompany invoices for this Periodic Billing were already created."))

	frappe.flags.creating_intercompany_invoices = True
	try:
		si_name, pi_name = _create_intercompany_pair(
			pb,
			group,
			posting_date=posting_date,
		)
	finally:
		frappe.flags.creating_intercompany_invoices = False

	_create_periodic_log(
		pb.name,
		job_name,
		group,
		customer_sales_invoice=customer_sales_invoice,
		sales_invoice=si_name,
		purchase_invoice=pi_name,
	)
	return {"job": job_name, "sales_invoice": si_name, "purchase_invoice": pi_name}


def _create_intercompany_pair(pb, group, *, posting_date: str) -> tuple[str, str]:
	from logistics.invoice_integration.sales_invoice_api import ensure_invoice_name_for_server_insert

	job_name = group["warehouse_job"]
	job = frappe.get_doc("Warehouse Job", job_name)
	main_type = group["main_service_type"]
	main_name = group["main_service"]
	main_job = frappe.get_doc(main_type, main_name) if frappe.db.exists(main_type, main_name) else None
	desc = _("Warehouse Job {0} - Periodic Billing {1} - Intercompany").format(job_name, pb.name)

	si = frappe.new_doc("Sales Invoice")
	si.company = group["operating_company"]
	si.customer = group["internal_customer"]
	si.posting_date = posting_date
	si.remarks = "{0} {1}".format(
		INTERCOMPANY_SI_REMARKS_PREFIX,
		_("from Periodic Billing {0}.").format(pb.name),
	)
	si.flags.is_intercompany_invoice = True
	_copy_dimensions(si, job)
	for line in group["lines"]:
		row = si.append("items", _invoice_item_payload(line, desc))
		_link_invoice_row(row, "Warehouse Job", job_name)
	si.set_missing_values()
	ensure_invoice_name_for_server_insert(si)
	si.insert(ignore_permissions=True)
	si.submit()

	pi = frappe.new_doc("Purchase Invoice")
	pi.company = group["main_company"]
	pi.supplier = group["internal_supplier"]
	pi.posting_date = posting_date
	pi.remarks = _("Intercompany: from Periodic Billing {0}.").format(pb.name)
	if main_job:
		_copy_dimensions(pi, main_job)
	for line in group["lines"]:
		row = pi.append("items", _invoice_item_payload(line, desc))
		_link_invoice_row(row, "Warehouse Job", job_name)
	pi.set_missing_values()
	ensure_invoice_name_for_server_insert(pi)
	pi.insert(ignore_permissions=True)
	pi.submit()
	return si.name, pi.name


def _copy_dimensions(doc, source) -> None:
	meta = frappe.get_meta(doc.doctype)
	for fieldname in ("branch", "cost_center", "profit_center", "job_number"):
		value = getattr(source, fieldname, None)
		if value and meta.get_field(fieldname):
			setattr(doc, fieldname, value)


def _invoice_item_payload(line, description: str) -> dict:
	return {
		"item_code": line.get("item_code"),
		"item_name": line.get("item_name"),
		"qty": flt(line.get("qty"), 2),
		"rate": flt(line.get("rate"), 2),
		"uom": line.get("uom"),
		"description": line.get("description") or description,
	}


def _link_invoice_row(row, doctype: str, name: str) -> None:
	meta = frappe.get_meta(row.parenttype)
	if meta.get_field("reference_doctype") and meta.get_field("reference_name"):
		row.reference_doctype = doctype
		row.reference_name = name


def _create_periodic_log(
	periodic_billing: str,
	job_name: str,
	group: dict,
	*,
	customer_sales_invoice: str,
	sales_invoice: str,
	purchase_invoice: str,
) -> None:
	from logistics.invoice_integration.sales_invoice_api import ensure_invoice_name_for_server_insert

	log = frappe.new_doc("Intercompany Invoice Log")
	if not log.get("naming_series"):
		from frappe.model.naming import get_default_naming_series

		log.naming_series = get_default_naming_series("Intercompany Invoice Log") or "ICL-.YYYY.-"
	log.customer_sales_invoice = customer_sales_invoice
	log.job_type = "Warehouse Job"
	log.job_no = job_name
	log.main_job_company = group.get("main_company")
	log.operating_company = group.get("operating_company")
	log.status = "Created"
	log.intercompany_sales_invoice = sales_invoice
	log.intercompany_purchase_invoice = purchase_invoice
	if log.meta.get_field("periodic_billing"):
		log.periodic_billing = periodic_billing
	ensure_invoice_name_for_server_insert(log)
	log.insert(ignore_permissions=True)


def _parse_idxs(value: Any) -> set[int]:
	if value in (None, ""):
		return set()
	if isinstance(value, str):
		value = json.loads(value)
	return {int(idx) for idx in (value or [])}


def _truthy(value: Any) -> bool:
	return str(value).strip().lower() in {"1", "true", "yes", "on"}
