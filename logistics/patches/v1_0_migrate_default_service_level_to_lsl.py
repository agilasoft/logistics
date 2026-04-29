import frappe


def execute():
	"""Clear default_service_level on mode settings when not a valid Logistics Service Level name.

	Covers: former Air Freight link to Service Level Agreement, and Sea Freight Select text values.
	"""
	for settings_dt in ("Air Freight Settings", "Sea Freight Settings"):
		meta = frappe.get_meta(settings_dt)
		if not getattr(meta, "issingle", 0):
			for name in frappe.get_all(settings_dt, pluck="name"):
				val = frappe.db.get_value(settings_dt, name, "default_service_level")
				if not val:
					continue
				if not frappe.db.exists("Logistics Service Level", val):
					frappe.db.set_value(settings_dt, name, "default_service_level", None)
			continue
		val = frappe.db.get_single_value(settings_dt, "default_service_level")
		if not val:
			continue
		if not frappe.db.exists("Logistics Service Level", val):
			frappe.db.set_single_value(settings_dt, "default_service_level", None)
