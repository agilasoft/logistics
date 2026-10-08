# Copyright (c) 2026, www.agilasoft.com and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import random_string


class TestTransportVehicle(FrappeTestCase):
	def test_internal_dimension_fields_persist(self):
		suffix = random_string(6)
		vehicle_type = f"TV{suffix}"
		frappe.get_doc(
			{
				"doctype": "Vehicle Type",
				"code": vehicle_type,
				"description": vehicle_type,
				"is_active": 1,
			}
		).insert(ignore_permissions=True)

		code = f"TVH{suffix}"
		company = self._ensure_company(suffix)
		doc = frappe.get_doc(
			{
				"doctype": "Transport Vehicle",
				"code": code,
				"vehicle_name": f"Vehicle {suffix}",
				"license_plate_number": code,
				"vehicle_type": vehicle_type,
				"company_owned": 1,
				"company": company,
				"is_active": 1,
				"internal_length": 6.1,
				"internal_width": 2.4,
				"internal_height": 2.5,
				"internal_dimension_uom": "Meter",
			}
		)
		doc.insert(ignore_permissions=True)

		reloaded = frappe.get_doc("Transport Vehicle", doc.name)
		self.assertEqual(reloaded.internal_length, 6.1)
		self.assertEqual(reloaded.internal_width, 2.4)
		self.assertEqual(reloaded.internal_height, 2.5)
		self.assertEqual(reloaded.internal_dimension_uom, "Meter")

	def _ensure_company(self, suffix: str) -> str:
		name = f"TV Co {suffix}"
		if frappe.db.exists("Company", name):
			return name
		frappe.get_doc(
			{
				"doctype": "Company",
				"company_name": name,
				"abbr": suffix[:4].upper(),
				"default_currency": "PHP",
				"country": "Philippines",
			}
		).insert(ignore_permissions=True)
		return name
