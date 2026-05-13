# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import get_table_name

# After v1_0_normalize_unified_charge_service_type_lowercase, unified charge rows use lowercase keys.
# DocType Select options use Title Case labels (Air, Sea, Transport, Customs, Warehousing).

_LOWER_TO_TITLE = (
	("air", "Air"),
	("sea", "Sea"),
	("transport", "Transport"),
	("custom", "Customs"),
	("warehousing", "Warehousing"),
)

# Resolve duplicate labels after lowercase migration (Custom was used briefly; Customs is canonical).
_LEGACY_CUSTOM_TITLE_TO_CUSTOMS = ("Customs", "Custom")

_OPERATIONAL_CHARGE_DOCTYPES = (
	"Sea Booking Charges",
	"Air Booking Charges",
	"Sea Shipment Charges",
	"Air Shipment Charges",
	"Declaration Charges",
	"Declaration Order Charges",
	"Transport Order Charges",
	"Transport Job Charges",
	"Warehouse Job Charges",
)


def execute():
	for dt in ("Sales Quote Charge", "Change Request Charge", "Cost Sheet Charge"):
		if not frappe.db.exists("DocType", dt):
			continue
		table = get_table_name(dt)
		for old, new in _LOWER_TO_TITLE:
			frappe.db.sql(
				"UPDATE `{}` SET `service_type`=%s WHERE `service_type`=%s".format(table),
				(new, old),
			)
		frappe.db.sql(
			"UPDATE `{}` SET `service_type`=%s WHERE `service_type`=%s".format(table),
			_LEGACY_CUSTOM_TITLE_TO_CUSTOMS,
		)

	for dt in _OPERATIONAL_CHARGE_DOCTYPES:
		if not frappe.db.exists("DocType", dt):
			continue
		table = get_table_name(dt)
		frappe.db.sql(
			"UPDATE `{}` SET `service_type`=%s WHERE `service_type`=%s".format(table),
			_LEGACY_CUSTOM_TITLE_TO_CUSTOMS,
		)

	if frappe.db.exists("DocType", "Sales Quote"):
		frappe.db.sql(
			"UPDATE `tabSales Quote` SET `main_service`=%s WHERE `main_service`=%s",
			_LEGACY_CUSTOM_TITLE_TO_CUSTOMS,
		)

	if frappe.db.exists("DocType", "Internal Job Detail"):
		frappe.db.sql(
			"UPDATE `tabInternal Job Detail` SET `service_type`=%s WHERE `service_type`=%s",
			_LEGACY_CUSTOM_TITLE_TO_CUSTOMS,
		)
