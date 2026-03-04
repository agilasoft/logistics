# Migrate Declaration and Declaration Order status to simplified workflow
# Declaration: Lodged->Submitted, Assessment on Hold/PAN/FAN->Under Review, Paid->Cleared
# Declaration Order: Confirmed->Submitted, In Progress->Under Review, Completed->Cleared
from __future__ import unicode_literals

import frappe


def execute():
	# Declaration: map old customs workflow to new
	decl_map = {
		"Lodged": "Submitted",
		"Assessment on Hold": "Under Review",
		"PAN Issued": "Under Review",
		"FAN Issued": "Under Review",
		"Paid": "Cleared",
	}
	for old_status, new_status in decl_map.items():
		frappe.db.sql(
			"UPDATE `tabDeclaration` SET status = %s WHERE status = %s",
			(new_status, old_status),
		)
	# Declaration Order: map old to new
	order_map = {
		"Confirmed": "Submitted",
		"In Progress": "Under Review",
		"Completed": "Cleared",
	}
	for old_status, new_status in order_map.items():
		frappe.db.sql(
			"UPDATE `tabDeclaration Order` SET status = %s WHERE status = %s",
			(new_status, old_status),
		)
	frappe.db.commit()
