# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Drop persisted internal-job child rows for Docket.

``Docket.internal_jobs`` is now a virtual ``Linked Service Detail`` grid (same
pattern as Sales Quote ``linked_services``). Rows are a live view of
``Linked Service`` documents parented via ``parent_booking_type`` /
``parent_booking_name``; child-table rows must not be persisted on Docket.
"""

from __future__ import annotations

import frappe

from logistics.utils.internal_job_persistence import sync_internal_job_details_to_internal_jobs


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
				doc = frappe.get_doc("Docket", parent)
				doc.flags._internal_jobs_from_form = True
				doc.__dict__["internal_jobs"] = list(
					frappe.get_all(
						child_dt,
						filters={
							"parent": parent,
							"parenttype": "Docket",
							"parentfield": "internal_jobs",
						},
						fields=["*"],
					)
				)
				sync_internal_job_details_to_internal_jobs(doc)
			except Exception:
				frappe.log_error(
					title=f"Docket virtual IJ migration failed for {parent}",
					message=frappe.get_traceback(),
				)
		frappe.db.delete(child_dt, {"parenttype": "Docket"})
	frappe.db.commit()
