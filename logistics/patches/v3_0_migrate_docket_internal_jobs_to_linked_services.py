# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Migrate Docket ``internal_jobs`` child rows to virtual ``linked_services`` grid.

``Docket.linked_services`` is a read-only virtual ``Linked Service Detail`` grid backed by
``Linked Service`` documents parented via ``parent_booking_type`` / ``parent_booking_name``.
Persisted child-table rows must not remain on Docket after this migration.
"""

from __future__ import annotations

import frappe

from logistics.utils.internal_job_persistence import (
	_linked_service_names_from_db,
	sync_internal_job_details_to_internal_jobs,
)
from logistics.utils.linked_service_compat import linked_service_doctype


def execute():
	child_doctypes: list[str] = []
	for name in ("Internal Job Detail", "Linked Service Detail"):
		if frappe.db.table_exists(f"tab{name}") and name not in child_doctypes:
			child_doctypes.append(name)
	if not child_doctypes:
		return

	for child_dt in child_doctypes:
		if not frappe.db.has_column(child_dt, "parenttype"):
			continue
		rows = frappe.get_all(
			child_dt,
			filters={"parenttype": "Docket"},
			fields=["parent"],
			distinct=True,
		)
		for row in rows:
			parent = (row.get("parent") or "").strip()
			if not parent or not frappe.db.exists("Docket", parent):
				continue
			try:
				child_rows = list(
					frappe.get_all(
						child_dt,
						filters={
							"parent": parent,
							"parenttype": "Docket",
							"parentfield": ["in", ("internal_jobs", "linked_services")],
						},
						fields=["*"],
					)
				)
				if not child_rows:
					continue
				doc = frappe.get_doc("Docket", parent)
				frappe.local._logistics_dk_ij_client_rows = [
					frappe._dict(r) for r in child_rows
				]
				sync_internal_job_details_to_internal_jobs(doc)
			except Exception:
				frappe.log_error(
					title=f"Docket virtual linked services migration failed for {parent}",
					message=frappe.get_traceback(),
				)
			finally:
				if hasattr(frappe.local, "_logistics_dk_ij_client_rows"):
					delattr(frappe.local, "_logistics_dk_ij_client_rows")
		frappe.db.delete(child_dt, {"parenttype": "Docket"})

	_backfill_docket_linked_services_from_sales_quote()
	frappe.db.commit()


def _backfill_docket_linked_services_from_sales_quote() -> None:
	if not frappe.db.table_exists("Docket"):
		return
	ls_dt = linked_service_doctype()
	if not ls_dt:
		return

	from logistics.pricing_center.doctype.sales_quote.sales_quote import (
		_propagate_linked_services_to_docket,
	)

	for row in frappe.get_all(
		"Docket",
		filters={"sales_quote": ["is", "set"], "docstatus": ["<", 2]},
		fields=["name", "sales_quote"],
	):
		docket_name = (row.get("name") or "").strip()
		sq_name = (row.get("sales_quote") or "").strip()
		if not docket_name or not sq_name or not frappe.db.exists("Sales Quote", sq_name):
			continue
		if _linked_service_names_from_db("Docket", docket_name):
			continue
		try:
			docket_doc = frappe.get_doc("Docket", docket_name)
			sq_doc = frappe.get_doc("Sales Quote", sq_name)
			_propagate_linked_services_to_docket(sq_doc, docket_doc)
		except Exception:
			frappe.log_error(
				title=f"Docket linked services backfill failed for {docket_name}",
				message=frappe.get_traceback(),
			)
