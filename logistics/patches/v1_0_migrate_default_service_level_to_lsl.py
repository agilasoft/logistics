import frappe


def execute():
	"""Clear default_service_level on mode settings when not a valid Logistics Service Level name.

	Covers: former Air Freight link to Service Level Agreement, and Sea Freight Select text values.
	"""
	for settings_dt in ("Air Freight Settings", "Sea Freight Settings"):
		val = frappe.db.get_single_value(settings_dt, "default_service_level")
		if not val:
			continue
		if not frappe.db.exists("Logistics Service Level", val):
			frappe.db.set_single_value(settings_dt, "default_service_level", None)
