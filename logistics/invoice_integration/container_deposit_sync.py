# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""
After Purchase Invoice submit/cancel: refresh Container deposit header fields from GL Entry
(Container accounting dimension). Deposit lines are not stored on Container — they are virtual (GL).
"""

from __future__ import unicode_literals

import frappe
from frappe import _

from logistics.container_management.api import get_container_by_number, is_container_management_enabled
from logistics.invoice_integration.container_deposit_pi import (
	JOB_DOCTYPES_CONTAINER_DEPOSIT,
	item_is_container_deposit,
)
from logistics.logistics.deposit_processing.container_gl_service import sync_deposit_header_from_gl
from logistics.utils.container_validation import normalize_container_number


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


def _container_names_for_cd_purchase_invoice(pi_doc):
	"""Resolve Container document names for container-deposit lines on a PI (for GL refresh)."""
	header_ref_dt = pi_doc.get("reference_doctype") or ""
	header_ref_name = pi_doc.get("reference_name") or ""
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
		return set()
	job_keyed_containers = {}
	for _row, job_dt, job_nm in cd_items:
		k = (job_dt, job_nm)
		if k not in job_keyed_containers:
			job_keyed_containers[k] = _job_containers(job_dt, job_nm)
	affected = set()
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
		affected.add(container_name)
	return affected


def sync_container_deposits_on_purchase_invoice_submit(pi_doc):
	"""Recompute Container deposit header from GL after container-deposit PI is posted."""
	if pi_doc.docstatus != 1:
		return
	for container_name in _container_names_for_cd_purchase_invoice(pi_doc):
		if not frappe.db.exists("Container", container_name):
			continue
		doc = frappe.get_doc("Container", container_name)
		sync_deposit_header_from_gl(doc)
		doc.save(ignore_permissions=True)


def clear_container_deposits_on_purchase_invoice_cancel(pi_doc):
	"""Block cancel when refund request exists; otherwise refresh headers from GL."""
	if pi_doc.doctype != "Purchase Invoice":
		return
	linked = frappe.get_all(
		"Container Refund Link",
		filters={"purchase_invoice": pi_doc.name},
		fields=["journal_entry", "parent"],
	)
	blocked = [r for r in linked if r.get("journal_entry")]
	if blocked:
		je_list = ", ".join({r.get("journal_entry") for r in blocked if r.get("journal_entry")})
		frappe.throw(
			_(
				"Cannot cancel Purchase Invoice while Request Deposit Refund Journal Entries exist. "
				"Cancel or reverse them first: {0}"
			).format(je_list),
			title=_("Container deposit"),
		)
	for container_name in _container_names_for_cd_purchase_invoice(pi_doc):
		if not frappe.db.exists("Container", container_name):
			continue
		doc = frappe.get_doc("Container", container_name)
		sync_deposit_header_from_gl(doc)
		doc.save(ignore_permissions=True)
