# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Re-sync charge child tables whose ``field_order`` still referenced ``internal_job`` after rename."""

from __future__ import unicode_literals

import frappe

_RELOADS = (
	("logistics", "air_freight", "air_booking_charges"),
	("logistics", "air_freight", "air_shipment_charges"),
	("logistics", "pricing_center", "transport_order_charges"),
	("logistics", "pricing_center", "transport_job_charges"),
	("logistics", "customs", "declaration_charges"),
	("logistics", "customs", "declaration_order_charges"),
	("logistics", "warehousing", "warehouse_job_charges"),
	("logistics", "warehousing", "inbound_order_charges"),
	("logistics", "warehousing", "release_order_charges"),
	("logistics", "mice", "mice_project_charges"),
)


def execute():
	for app, module, name in _RELOADS:
		if frappe.db.exists("DocType", frappe.unscrub(name)):
			frappe.reload_doc(app, module, name, force=True)
	frappe.db.commit()
