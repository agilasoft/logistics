# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Backfill Job Status on shipments/jobs for charge reopen standardization."""

from __future__ import unicode_literals

import frappe

from logistics.job_management.logistics_job_status import (
	sync_air_shipment_job_status,
	sync_declaration_job_status,
	sync_sea_shipment_job_status,
	validate_warehouse_job_defaults,
)


def execute():
	for doctype, fn in (
		("Sea Shipment", sync_sea_shipment_job_status),
		("Air Shipment", sync_air_shipment_job_status),
		("Declaration", sync_declaration_job_status),
		("Warehouse Job", validate_warehouse_job_defaults),
	):
		_backfill_doctype(doctype, fn)


def _backfill_doctype(doctype, sync_fn):
	if not frappe.db.has_column(doctype, "job_status"):
		return
	names = frappe.get_all(doctype, pluck="name")
	for i, name in enumerate(names):
		doc = frappe.get_doc(doctype, name)
		before = (getattr(doc, "job_status", None) or "").strip()
		sync_fn(doc)
		after = (getattr(doc, "job_status", None) or "").strip()
		if after and after != before:
			frappe.db.set_value(doctype, name, "job_status", after, update_modified=False)
		if i % 100 == 99:
			frappe.db.commit()
	frappe.db.commit()
