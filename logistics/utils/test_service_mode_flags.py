# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from logistics.utils.service_mode_flags import (
	get_service_mode_flags_bulk,
	module_flag_for_charge_service_type,
	validate_service_mode_link,
)


class TestServiceModeFlags(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_module_flag_for_charge_service_type(self):
		self.assertEqual(module_flag_for_charge_service_type("Air"), "air")
		self.assertEqual(module_flag_for_charge_service_type("Customs"), "customs")
		self.assertIsNone(module_flag_for_charge_service_type("Special Project"))

	def test_validate_service_mode_link_rejects_mismatch(self):
		sfx = frappe.generate_hash(length=6)
		lt = frappe.get_doc(
			{
				"doctype": "Load Type",
				"load_type_name": f"TST-SMF-LT-{sfx}",
				"sea": 1,
				"air": 0,
			}
		).insert(ignore_permissions=True).name
		with self.assertRaises(frappe.ValidationError):
			validate_service_mode_link(
				"Load Type",
				lt,
				"Air",
				context="test",
			)

	def test_validate_service_mode_link_accepts_match(self):
		sfx = frappe.generate_hash(length=6)
		tm = frappe.get_doc(
			{
				"doctype": "Transport Mode",
				"mode_code": f"TST-SMF-{sfx}",
				"mode_name": f"TST Air {sfx}",
				"primary_document": "Air Shipment",
				"air": 1,
			}
		).insert(ignore_permissions=True).name
		validate_service_mode_link(
			"Transport Mode",
			tm,
			"Air",
			context="test",
		)

	def test_get_service_mode_flags_bulk(self):
		sfx = frappe.generate_hash(length=6)
		tm = frappe.get_doc(
			{
				"doctype": "Transport Mode",
				"mode_code": f"TST-SMF2-{sfx}",
				"mode_name": f"TST Sea {sfx}",
				"primary_document": "Sea Shipment",
				"sea": 1,
			}
		).insert(ignore_permissions=True).name
		flags = get_service_mode_flags_bulk("Transport Mode", [tm])
		self.assertEqual(flags[tm]["sea"], 1)
		self.assertEqual(flags[tm]["air"], 0)
