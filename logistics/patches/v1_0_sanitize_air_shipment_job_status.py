# Copyright (c) 2026, Agilasoft and contributors
# License: MIT. See LICENSE

"""
Post-sync safety pass: clear invalid `job_status` on Air Shipment (Select).
`v1_0_prepare_air_shipment_job_status_select` runs before migrate; this catches
edge cases. Next save re-syncs via `sync_air_shipment_job_status`.
"""

import frappe

from logistics.job_management.logistics_job_status import ALLOWED_JOB_STATUS_VALUES

_MAX_LEN = 64


def execute():
	doctype = "Air Shipment"
	if not frappe.db.has_column(doctype, "job_status"):
		return True

	rows = frappe.db.sql(
		"SELECT name, job_status FROM `tabAir Shipment` WHERE job_status IS NOT NULL AND job_status != ''",
		as_dict=True,
	)
	cleared = 0
	for row in rows or []:
		raw = row.get("job_status")
		if raw is None:
			continue
		val = str(raw).strip()
		if len(val) > _MAX_LEN or val not in ALLOWED_JOB_STATUS_VALUES:
			frappe.db.set_value("Air Shipment", row.name, "job_status", None, update_modified=False)
			cleared += 1

	if cleared:
		print(f"Cleared invalid job_status on {cleared} Air Shipment row(s)")
	return True
