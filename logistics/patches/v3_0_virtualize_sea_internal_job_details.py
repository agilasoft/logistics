# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Virtualize ``internal_job_details`` on operational parents (Linked Service only)."""

from __future__ import annotations

import frappe

from logistics.utils.internal_job_persistence import sync_internal_job_details_to_internal_jobs
from logistics.utils.linked_service_compat import linked_service_doctype, row_linked_service_link
from logistics.utils.virtual_internal_job_details import VIRTUAL_INTERNAL_JOB_DETAILS_PARENTS

_PARENTS = tuple(sorted(VIRTUAL_INTERNAL_JOB_DETAILS_PARENTS))
_PARENT_FIELD = {dt: "internal_job_details" for dt in _PARENTS}


def execute():
	child_doctypes: list[str] = []
	for name in ("Internal Job Detail", "Linked Service Detail"):
		table = f"tab{name}"
		if frappe.db.table_exists(table) and name not in child_doctypes:
			child_doctypes.append(name)
	if not child_doctypes:
		return

	ls_dt = linked_service_doctype()

	for child_dt in child_doctypes:
		if not frappe.db.has_column(child_dt, "parenttype"):
			continue
		for parenttype in _PARENTS:
			parentfield = _PARENT_FIELD[parenttype]
			rows = frappe.get_all(
				child_dt,
				filters={"parenttype": parenttype},
				fields=["parent"],
				distinct=True,
			)
			for row in rows:
				parent = (row.get("parent") or "").strip()
				if not parent or not frappe.db.exists(parenttype, parent):
					continue
				try:
					doc = frappe.get_doc(parenttype, parent)
					doc.flags._internal_job_details_from_form = True
					doc.__dict__[parentfield] = list(
						frappe.get_all(
							child_dt,
							filters={
								"parent": parent,
								"parenttype": parenttype,
								"parentfield": parentfield,
							},
							fields=["*"],
						)
					)
					sync_internal_job_details_to_internal_jobs(doc)
					for ij_row in doc.__dict__.get(parentfield) or []:
						ls_name = row_linked_service_link(ij_row)
						if not ls_name or not frappe.db.exists(ls_dt, ls_name):
							continue
						ls = frappe.get_doc(ls_dt, ls_name)
						changed = False
						if (ls.parent_booking_type or "") != parenttype:
							ls.parent_booking_type = parenttype
							changed = True
						if (ls.parent_booking_name or "") != parent:
							ls.parent_booking_name = parent
							changed = True
						if changed:
							ls.flags.ignore_permissions = True
							ls.flags.skip_internal_job_detail_sync = True
							ls.save(ignore_permissions=True)
				except Exception:
					frappe.log_error(
						title=f"Virtual IJ migration failed for {parenttype} {parent}",
						message=frappe.get_traceback(),
					)
			frappe.db.delete(child_dt, {"parenttype": parenttype})
	frappe.db.commit()
