# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""
Sync Container `deposits` child rows when a container-deposit Purchase Invoice is submitted or cancelled.
"""

from __future__ import unicode_literals

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

from logistics.container_management.api import get_container_by_number, is_container_management_enabled
from logistics.invoice_integration.container_deposit_pi import (
	JOB_DOCTYPES_CONTAINER_DEPOSIT,
	item_is_container_deposit,
)
from logistics.logistics.deposit_processing.container_deposit_gl import sync_deposit_header_from_child_rows
from logistics.utils.container_validation import normalize_container_number


def _debtor_for_job(job_dt, job_name):
	job = frappe.get_doc(job_dt, job_name)
	if job_dt == "Sea Shipment":
		return getattr(job, "local_customer", None) or getattr(job, "booking_party", None)
	if job_dt == "Declaration":
		return getattr(job, "customer", None)
	return None


def _containers_for_sea_shipment(job_name):
	doc = frappe.get_doc("Sea Shipment", job_name)
	out = []
	for row in doc.get("containers") or []:
		c = getattr(row, "container", None)
		if c and frappe.db.exists("Container", c):
			out.append(c)
	return out


def _containers_for_declaration(job_name):
	doc = frappe.get_doc("Declaration", job_name)
	raw = (getattr(doc, "container_numbers", None) or "").strip()
	if not raw:
		return []
	parts = [p.strip() for p in raw.replace("\n", ",").split(",") if p.strip()]
	out = []
	for p in parts:
		eq = normalize_container_number(p)
		if not eq:
			continue
		if is_container_management_enabled():
			name = get_container_by_number(eq)
			if name:
				out.append(name)
		elif frappe.db.exists("Container", eq):
			out.append(eq)
	return out


def _job_containers(job_dt, job_name):
	if job_dt == "Sea Shipment":
		return _containers_for_sea_shipment(job_name)
	if job_dt == "Declaration":
		return _containers_for_declaration(job_name)
	return []


def _line_amount_company_currency(pi_doc, row):
	base = flt(getattr(row, "base_amount", None) or 0)
	if base:
		return base
	return flt(row.amount or 0) * flt(pi_doc.conversion_rate or 1)


def sync_container_deposits_on_purchase_invoice_submit(pi_doc):
	"""Create/update Container Deposit rows for CD items on a submitted PI."""
	if pi_doc.docstatus != 1:
		return
	header_ref_dt = pi_doc.get("reference_doctype") or ""
	header_ref_name = pi_doc.get("reference_name") or ""

	aggregates = defaultdict(lambda: {"amount": 0.0, "item_code": None})
	meta = frappe.get_meta("Purchase Invoice Item")
	has_lc = bool(meta.get_field("logistics_container"))

	cd_items = []
	for row in pi_doc.get("items") or []:
		if not row.get("item_code") or not item_is_container_deposit(row.item_code):
			continue
		job_dt = row.get("reference_doctype") or header_ref_dt
		job_nm = row.get("reference_name") or header_ref_name
		if job_dt not in JOB_DOCTYPES_CONTAINER_DEPOSIT or not job_nm:
			continue
		if not frappe.db.exists(job_dt, job_nm):
			continue
		cd_items.append((row, job_dt, job_nm))

	if not cd_items:
		return

	job_keyed_containers = {}
	for _row, job_dt, job_nm in cd_items:
		k = (job_dt, job_nm)
		if k not in job_keyed_containers:
			job_keyed_containers[k] = _job_containers(job_dt, job_nm)

	for idx, (row, job_dt, job_nm) in enumerate(cd_items):
		containers = job_keyed_containers.get((job_dt, job_nm)) or []
		container_name = None
		if has_lc and row.get("logistics_container"):
			container_name = row.logistics_container
		elif len(containers) == 1:
			container_name = containers[0]
		elif len(containers) > 1:
			container_name = containers[idx % len(containers)]

		if not container_name:
			frappe.log_error(
				title="Container deposit PI sync",
				message=_(
					"Purchase Invoice {0}: could not resolve Container for job {1} {2}. "
					"Set logistics_container on PI line or ensure job lists container(s)."
				).format(pi_doc.name, job_dt, job_nm),
			)
			continue

		amt = _line_amount_company_currency(pi_doc, row)
		if amt <= 0:
			continue
		key = (container_name, job_dt, job_nm)
		aggregates[key]["amount"] += amt
		if not aggregates[key]["item_code"]:
			aggregates[key]["item_code"] = row.item_code

	for (container_name, job_dt, job_nm), agg in aggregates.items():
		_upsert_deposit_row_for_pi(
			container_name=container_name,
			pi_doc=pi_doc,
			job_dt=job_dt,
			job_nm=job_nm,
			amount=agg["amount"],
			item_code=agg.get("item_code"),
		)


def _upsert_deposit_row_for_pi(container_name, pi_doc, job_dt, job_nm, amount, item_code=None):
	if not frappe.db.exists("Container", container_name):
		return
	job = frappe.get_doc(job_dt, job_nm)
	job_number = getattr(job, "job_number", None)
	company = pi_doc.company or getattr(job, "company", None)
	debtor = _debtor_for_job(job_dt, job_nm)

	container_doc = frappe.get_doc("Container", container_name)
	found = None
	for line in container_doc.get("deposits") or []:
		if line.get("purchase_invoice") == pi_doc.name:
			found = line
			break

	payload = {
		"event_type": "Pay Carrier",
		"job_number": job_number,
		"item_code": item_code,
		"container": container_name,
		"company": company,
		"debtor_party": debtor,
		"deposit_amount": amount,
		"deposit_currency": pi_doc.currency,
		"deposit_date": getdate(pi_doc.posting_date or nowdate()),
		"reference": pi_doc.name,
		"purchase_invoice": pi_doc.name,
	}

	if found:
		for k, v in payload.items():
			setattr(found, k, v)
	else:
		container_doc.append("deposits", payload)

	sync_deposit_header_from_child_rows(container_doc)
	container_doc.save(ignore_permissions=True)


def clear_container_deposits_on_purchase_invoice_cancel(pi_doc):
	"""Remove deposit lines created for this Purchase Invoice."""
	if pi_doc.doctype != "Purchase Invoice":
		return
	linked = frappe.get_all(
		"Container Deposit",
		filters={"purchase_invoice": pi_doc.name},
		fields=["name", "refund_request_journal_entry", "parent"],
	)
	if not linked:
		return
	blocked = [r for r in linked if r.get("refund_request_journal_entry")]
	if blocked:
		je_list = ", ".join(
			{r.get("refund_request_journal_entry") for r in blocked if r.get("refund_request_journal_entry")}
		)
		frappe.throw(
			_(
				"Cannot cancel Purchase Invoice while Request Deposit Refund Journal Entries exist. "
				"Cancel or reverse them first: {0}"
			).format(je_list),
			title=_("Container deposit"),
		)
	parents = list({r.parent for r in linked if r.get("parent")})
	for parent in parents:
		doc = frappe.get_doc("Container", parent)
		doc.deposits = [r for r in doc.get("deposits") or [] if r.get("purchase_invoice") != pi_doc.name]
		sync_deposit_header_from_child_rows(doc)
		doc.save(ignore_permissions=True)
