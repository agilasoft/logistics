# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Backfill ``lifecycle_stage`` on existing Special Project Site Receipt rows.

The Fulfillment summary on ``Special Project`` was redesigned into a per-Lifecycle-Stage
delivery funnel. Each Site Receipt row now carries a ``lifecycle_stage`` link so the
summary can group delivered quantities by stage.

For existing data we backfill ``lifecycle_stage`` per receipt by:

1. Loading the parent ``Special Project``'s ``lifecycle_jobs`` table once.
2. Looking up the originating ``Lifecycle Job`` row whose ``(job_type, job_no)`` matches
   the receipt's ``(source_job_type, source_job_no)`` and copying that row's stage.
3. Falling back to the parent's current ``lifecycle_stage`` if no link is found.
4. Final fallback: the seeded ``"Logistics"`` stage.

The patch is idempotent: rows that already have a non-empty ``lifecycle_stage`` are skipped.
"""

from __future__ import annotations

import frappe

DEFAULT_STAGE = "Logistics"


def execute() -> None:
	receipts_doctype = "Special Project Site Receipt"
	if not frappe.db.table_exists("tab" + receipts_doctype):
		return

	frappe.reload_doc("special_projects", "doctype", "special_project_site_receipt", force=True)

	default_stage = DEFAULT_STAGE if frappe.db.exists("Lifecycle Stage", DEFAULT_STAGE) else None
	rows = frappe.db.sql(
		"""
		SELECT name, parent, source_job_type, source_job_no
		FROM `tabSpecial Project Site Receipt`
		WHERE COALESCE(lifecycle_stage, '') = ''
		""",
		as_dict=True,
	)
	if not rows:
		return

	by_parent: dict[str, list[dict]] = {}
	for r in rows:
		by_parent.setdefault(r["parent"], []).append(r)

	updated = 0
	for sp_name, items in by_parent.items():
		try:
			sp_stage = frappe.db.get_value("Special Project", sp_name, "lifecycle_stage") or ""
		except Exception:
			sp_stage = ""
		fallback = sp_stage if sp_stage and frappe.db.exists("Lifecycle Stage", sp_stage) else default_stage

		jobs = frappe.db.sql(
			"""
			SELECT job_type, job_no, lifecycle_stage
			FROM `tabLifecycle Job`
			WHERE parent = %s AND parenttype = 'Special Project'
			""",
			(sp_name,),
			as_dict=True,
		)
		job_stage_by_key: dict[tuple[str, str], str] = {}
		for j in jobs:
			key = ((j.get("job_type") or "").strip(), (j.get("job_no") or "").strip())
			stage = (j.get("lifecycle_stage") or "").strip()
			if key[0] and key[1] and stage and key not in job_stage_by_key:
				job_stage_by_key[key] = stage

		for r in items:
			key = ((r.get("source_job_type") or "").strip(), (r.get("source_job_no") or "").strip())
			stage = job_stage_by_key.get(key) or fallback
			if not stage:
				continue
			frappe.db.set_value(
				receipts_doctype,
				r["name"],
				"lifecycle_stage",
				stage,
				update_modified=False,
			)
			updated += 1

	if updated:
		frappe.db.commit()
		print(f"[v1_1_special_project_receipt_lifecycle_stage] backfilled {updated} receipt row(s)")
