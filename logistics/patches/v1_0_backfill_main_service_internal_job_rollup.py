# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Backfill planned / actual cost & revenue on Main Service Internal Job Detail rows.

Before this patch existed, submitting an internal job (Transport Order, Declaration Order,
Air Booking, Sea Booking, etc.) did **not** push its charge totals onto the Main Service's
Internal Jobs row, leaving Planned/Actual columns at ``0.00`` even after the internal job had
been submitted. Going forward the rollup runs on every internal-job save/submit/cancel
(see ``logistics.utils.internal_job_main_rollup`` registered in ``hooks.py``); this patch
reconciles existing data once so historical Main Service documents show the right numbers.
"""

import frappe

from logistics.utils.internal_job_main_rollup import (
	refresh_internal_job_details_for_main_service,
)


def execute():
	if not frappe.db.exists("DocType", "Internal Job Detail"):
		return

	# Distinct (parenttype, parent) pairs of Internal Job Detail rows that reference a linked job.
	pairs = frappe.db.sql(
		"""
		SELECT DISTINCT parenttype, parent
		FROM `tabInternal Job Detail`
		WHERE COALESCE(job_no, '') != ''
		""",
		as_dict=True,
	) or []

	processed = 0
	for row in pairs:
		main_dt = (row.get("parenttype") or "").strip()
		main_name = (row.get("parent") or "").strip()
		if not main_dt or not main_name:
			continue
		if not frappe.db.exists("DocType", main_dt):
			continue
		if not frappe.db.exists(main_dt, main_name):
			continue
		try:
			refresh_internal_job_details_for_main_service(main_dt, main_name)
			processed += 1
		except Exception:
			frappe.log_error(
				title="backfill_main_service_internal_job_rollup",
				message=frappe.get_traceback(),
			)

	frappe.db.commit()
	frappe.logger().info(
		"v1_0_backfill_main_service_internal_job_rollup: refreshed %s Main Service documents."
		% processed
	)
