# Copyright (c) 2026, Agilasoft and contributors
# License: MIT. See LICENSE

"""
Before schema sync, clear `job_status` on Air Shipment when the value is not a
valid option or is too long for the Select column (Frappe uses varchar(>=64) for
Select on MariaDB). Prevents ALTER failures and bad data after conversion from
Small Text / legacy text.
"""

import frappe

from logistics.job_management.logistics_job_status import ALLOWED_JOB_STATUS_VALUES

# Frappe minimum varchar width for Select with explicit length < 64 (see frappe.database.schema.get_definition)
_MAX_SELECT_STORAGE_LEN = 64


def execute():
	if not frappe.db.has_table("Air Shipment"):
		return True
	if not frappe.db.has_column("Air Shipment", "job_status"):
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
		if not val or len(val) > _MAX_SELECT_STORAGE_LEN or val not in ALLOWED_JOB_STATUS_VALUES:
			frappe.db.set_value("Air Shipment", row.name, "job_status", None, update_modified=False)
			cleared += 1

	if cleared:
		frappe.db.commit()
		print(f"Prepared Air Shipment job_status (Select): cleared {cleared} invalid/non-option row(s)")
	return True
