# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Backfill Programme Lifecycle Jobs and charge lifecycle tags from legacy lifecycle_job_row."""

from __future__ import annotations

import frappe
from frappe.utils import cint


def execute():
	if not frappe.db.table_exists("tabProgramme Lifecycle Job"):
		return
	if not frappe.db.has_column("Special Project Charges", "lifecycle_job_row"):
		return

	for sp_name in frappe.get_all("Special Project", pluck="name"):
		sp = frappe.get_doc("Special Project", sp_name)
		from logistics.special_projects.special_project_programme_lifecycle import (
			sync_programme_lifecycle_jobs_from_lifecycle_jobs,
		)

		sync_programme_lifecycle_jobs_from_lifecycle_jobs(sp)
		registry_by_idx = {
			cint(r.lifecycle_jobs_idx): r
			for r in sp.get("programme_lifecycle_jobs") or []
			if cint(getattr(r, "lifecycle_jobs_idx", 0) or 0)
		}
		existing_tag_charges = set()
		for t in sp.get("charge_lifecycle_tags") or []:
			ch_row = cint(getattr(t, "charge_row", 0) or 0)
			if ch_row:
				existing_tag_charges.add(ch_row)
				continue
			tag_name = (getattr(t, "charge_lifecycle_tag", None) or "").strip()
			if tag_name:
				existing_tag_charges.add(
					cint(
						frappe.db.get_value(
							"Special Project Charge Lifecycle Tag",
							tag_name,
							"charge_row",
						)
						or 0
					)
				)
		changed = False
		from logistics.special_projects.special_project_programme_lifecycle import (
			append_charge_lifecycle_tag_for_test,
		)

		for charge in sp.get("charges") or []:
			ch_idx = cint(getattr(charge, "idx", 0) or 0)
			if not ch_idx or ch_idx in existing_tag_charges:
				continue
			legacy_idx = cint(getattr(charge, "lifecycle_job_row", 0) or 0)
			if not legacy_idx:
				continue
			reg = registry_by_idx.get(legacy_idx)
			if not reg:
				continue
			if frappe.get_meta("Special Project Charge Lifecycle Tag").has_field("special_project"):
				append_charge_lifecycle_tag_for_test(
					sp,
					ch_idx,
					reg.name,
					cost_allocation_percentage=100,
					is_primary=1,
				)
			else:
				sp.append(
					"charge_lifecycle_tags",
					{
						"charge_row": ch_idx,
						"programme_lifecycle_job": reg.name,
						"lifecycle_jobs_idx": legacy_idx,
						"cost_allocation_percentage": 100,
						"is_primary": 1,
					},
				)
			if not getattr(charge, "allocation_method", None):
				charge.allocation_method = "Equal"
			changed = True
		if changed or sp.get("programme_lifecycle_jobs"):
			sp.save(ignore_permissions=True)

	frappe.db.commit()
