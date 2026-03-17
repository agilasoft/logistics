# Migrate Declaration status from old values to customs workflow (legacy - already run)
# Old: Draft, Submitted, In Progress, Approved, Rejected, Cancelled
# New (at time of patch): Draft, Lodged, Assessment on Hold, PAN Issued, FAN Issued, Paid, Released, Rejected, Cancelled
from __future__ import unicode_literals

import frappe


def execute():
	status_map = {
		"Submitted": "Lodged",
		"In Progress": "Assessment on Hold",
		"Approved": "Released",
	}
	for old_status, new_status in status_map.items():
		frappe.db.sql(
			"UPDATE `tabDeclaration` SET status = %s WHERE status = %s",
			(new_status, old_status),
		)
	frappe.db.commit()
