# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""
Sync Job Number and Container accounting dimensions on Purchase Invoice Item rows
for container-deposit lines (Sea Shipment / Declaration references).
"""

from __future__ import unicode_literals

import frappe

from logistics.job_management.gl_reference_dimension import reference_dimension_row_dict

from logistics.invoice_integration.container_deposit_pi import (
	JOB_DOCTYPES_CONTAINER_DEPOSIT,
	item_is_container_deposit,
)
from logistics.invoice_integration.container_deposit_sync import _job_containers


def sync_container_deposit_pi_accounting_dimensions(doc, method=None):
	if doc.doctype != "Purchase Invoice":
		return
	if doc.docstatus != 0:
		return

	header_ref_dt = doc.get("reference_doctype") or ""
	header_ref_name = doc.get("reference_name") or ""
	meta = frappe.get_meta("Purchase Invoice Item")
	has_lc = bool(meta.get_field("logistics_container"))

	cd_job_keys = []
	for row in doc.get("items") or []:
		if not row.get("item_code") or not item_is_container_deposit(row.item_code):
			continue
		job_dt = row.get("reference_doctype") or header_ref_dt
		job_nm = row.get("reference_name") or header_ref_name
		if job_dt not in JOB_DOCTYPES_CONTAINER_DEPOSIT or not job_nm:
			continue
		if not frappe.db.exists(job_dt, job_nm):
			continue
		cd_job_keys.append((row, job_dt, job_nm))

	job_keyed_containers = {}
	for _row, job_dt, job_nm in cd_job_keys:
		k = (job_dt, job_nm)
		if k not in job_keyed_containers:
			job_keyed_containers[k] = _job_containers(job_dt, job_nm)

	for row, job_dt, job_nm in cd_job_keys:
		job_number = frappe.db.get_value(job_dt, job_nm, "job_number")
		if job_number:
			for k, v in reference_dimension_row_dict(
				"Purchase Invoice Item", "Job Number", job_number
			).items():
				setattr(row, k, v)

		containers = job_keyed_containers.get((job_dt, job_nm)) or []
		container_name = None
		if has_lc and row.get("logistics_container"):
			container_name = row.logistics_container
		elif len(containers) == 1:
			container_name = containers[0]
		# Multiple containers: only explicit logistics_container link or allocation dialog (no round-robin).

		if container_name:
			for k, v in reference_dimension_row_dict(
				"Purchase Invoice Item", "Container", container_name
			).items():
				setattr(row, k, v)
