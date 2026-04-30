# -*- coding: utf-8 -*-
# Copyright (c) 2026, Logistics Team and contributors
"""
Purchase Invoice UX for container-deposit items: pick job containers (checkboxes), split lines, set dimensions.
"""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import flt

from logistics.invoice_integration.container_deposit_pi import (
	JOB_DOCTYPES_CONTAINER_DEPOSIT,
	item_is_container_deposit,
)
from logistics.invoice_integration.container_deposit_sync import _job_containers


def _job_for_pi_item(doc, row):
	header_dt = doc.get("reference_doctype") or ""
	header_nm = doc.get("reference_name") or ""
	job_dt = row.get("reference_doctype") or header_dt
	job_nm = row.get("reference_name") or header_nm
	if job_dt not in JOB_DOCTYPES_CONTAINER_DEPOSIT or not job_nm:
		return None, None
	if not frappe.db.exists(job_dt, job_nm):
		return None, None
	return job_dt, job_nm


@frappe.whitelist()
def get_container_deposit_checkbox_context(pi_name):
	"""Containers available for allocation on this draft PI (union across referenced jobs)."""
	if not pi_name or not frappe.db.exists("Purchase Invoice", pi_name):
		return {"eligible": False, "reason": _("Purchase Invoice not found."), "containers": [], "deposit_line_count": 0}

	doc = frappe.get_doc("Purchase Invoice", pi_name)
	if doc.docstatus != 0:
		return {"eligible": False, "reason": _("Only draft Purchase Invoices can be allocated."), "containers": [], "deposit_line_count": 0}

	seen_jobs = set()
	containers_out = []
	deposit_lines = 0
	for row in doc.get("items") or []:
		if not row.get("item_code") or not item_is_container_deposit(row.item_code):
			continue
		deposit_lines += 1
		job_dt, job_nm = _job_for_pi_item(doc, row)
		if not job_nm:
			continue
		k = (job_dt, job_nm)
		if k in seen_jobs:
			continue
		seen_jobs.add(k)
		for cname in _job_containers(job_dt, job_nm) or []:
			if not cname:
				continue
			label = frappe.db.get_value("Container", cname, "container_number") or cname
			job_label = "{0} {1}".format(job_dt, job_nm)
			containers_out.append(
				{
					"value": cname,
					"label": "{0} — {1}".format(label, job_label),
					"container_number": label,
					"job_doctype": job_dt,
					"job_name": job_nm,
				}
			)

	# de-dupe by container value (same box on multiple jobs rare)
	by_val = {}
	for c in containers_out:
		by_val[c["value"]] = c
	containers_out = list(by_val.values())
	containers_out.sort(key=lambda x: (x.get("container_number") or "", x.get("value") or ""))

	reason = ""
	if not deposit_lines:
		reason = _("Add at least one container-deposit item.")
	elif not containers_out:
		reason = _("Link the lines to a Sea Shipment or Declaration that lists containers (Container Management).")

	return {
		"eligible": deposit_lines > 0 and len(containers_out) > 0,
		"reason": reason,
		"containers": containers_out,
		"deposit_line_count": deposit_lines,
		"multi_container_job": len(containers_out) > 1,
	}


@frappe.whitelist()
def apply_selected_containers_to_deposit_lines(pi_name, container_names):
	"""
	Split each container-deposit line without `logistics_container` into one row per selected container,
	splitting amount/qty evenly. Sets `logistics_container` on each new row (dimensions applied on save).
	"""
	if isinstance(container_names, str):
		import json

		try:
			container_names = json.loads(container_names)
		except Exception:
			container_names = [container_names]

	container_names = [c for c in (container_names or []) if c]
	if not container_names:
		frappe.throw(_("Select at least one container."), title=_("Container deposit"))

	doc = frappe.get_doc("Purchase Invoice", pi_name)
	if doc.docstatus != 0:
		frappe.throw(_("Only draft Purchase Invoices can be allocated."), title=_("Container deposit"))

	n = len(container_names)
	header_dt = doc.get("reference_doctype") or ""
	header_nm = doc.get("reference_name") or ""

	out_rows = []
	for row in doc.get("items") or []:
		if not row.get("item_code") or not item_is_container_deposit(row.item_code):
			out_rows.append(row.as_dict())
			continue

		job_dt = row.get("reference_doctype") or header_dt
		job_nm = row.get("reference_name") or header_nm
		if job_dt not in JOB_DOCTYPES_CONTAINER_DEPOSIT or not job_nm:
			out_rows.append(row.as_dict())
			continue

		if row.get("logistics_container"):
			out_rows.append(row.as_dict())
			continue

		job_containers = list(_job_containers(job_dt, job_nm) or [])
		for cn in container_names:
			if cn not in job_containers:
				frappe.throw(
					_("Container {0} is not linked to job {1} {2}.").format(cn, job_dt, job_nm),
					title=_("Invalid container"),
				)

		amt = flt(row.amount)
		base_amt = flt(row.base_amount) if row.base_amount is not None else None
		qty = flt(row.qty) or 1

		for cn in container_names:
			d = row.as_dict()
			for pop in ("name", "idx"):
				d.pop(pop, None)
			d["logistics_container"] = cn
			d["amount"] = amt / n
			if base_amt is not None:
				d["base_amount"] = base_amt / n
			d["qty"] = qty / n
			if flt(row.rate):
				d["rate"] = flt(d["amount"]) / flt(d["qty"]) if flt(d["qty"]) else flt(row.rate)
			out_rows.append(d)

	doc.items = []
	for d in out_rows:
		doc.append("items", d)

	try:
		doc.run_method("calculate_taxes_and_totals")
	except Exception:
		pass

	doc.save()

	return {"name": doc.name, "items_count": len(doc.items)}


def validate_container_deposit_lines_have_container_before_submit(doc, method=None):
	"""Require explicit Container per line when the job lists multiple containers (runs before submit)."""
	if doc.doctype != "Purchase Invoice":
		return

	header_dt = doc.get("reference_doctype") or ""
	header_nm = doc.get("reference_name") or ""

	for row in doc.get("items") or []:
		if not row.get("item_code") or not item_is_container_deposit(row.item_code):
			continue
		job_dt = row.get("reference_doctype") or header_dt
		job_nm = row.get("reference_name") or header_nm
		if job_dt not in JOB_DOCTYPES_CONTAINER_DEPOSIT or not job_nm:
			continue
		if not frappe.db.exists(job_dt, job_nm):
			continue
		containers = _job_containers(job_dt, job_nm) or []
		if len(containers) <= 1:
			continue
		meta = frappe.get_meta("Purchase Invoice Item")
		if not meta.get_field("logistics_container"):
			continue
		if not row.get("logistics_container"):
			frappe.throw(
				_(
					"Container-deposit line for item {0}: select containers via **Allocate container deposits** "
					"(or set the Container field on each line) when the job has multiple containers."
				).format(row.item_code),
				title=_("Container required"),
			)
