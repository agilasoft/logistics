# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Drop persisted internal-job child rows for MICE Project.

``MICE Project.linked_services`` is now a virtual ``Linked Service Detail`` grid.
Rows are a live view of ``Linked Service`` documents parented via
``parent_booking_type`` / ``parent_booking_name``; child-table rows must not be
persisted on MICE Project.
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
			filters={"parenttype": "MICE Project"},
			fields=["parent"],
			distinct=True,
		)
		for row in rows:
			parent = (row.get("parent") or "").strip()
			if not parent or not frappe.db.exists("MICE Project", parent):
				continue
			try:
				doc = frappe.get_doc("MICE Project", parent)
				doc.flags._linked_services_from_form = True
				doc.__dict__["linked_services"] = list(
					frappe.get_all(
						child_dt,
						filters={
							"parent": parent,
							"parenttype": "MICE Project",
							"parentfield": "internal_jobs",
						},
						fields=["*"],
					)
				)
				sync_internal_job_details_to_internal_jobs(doc)
			except Exception:
				frappe.log_error(
					title=f"MICE Project virtual linked services migration failed for {parent}",
					message=frappe.get_traceback(),
				)
		frappe.db.delete(child_dt, {"parenttype": "MICE Project"})
	frappe.db.commit()
