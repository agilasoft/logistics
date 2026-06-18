# Copyright (c) 2026, Agilasoft and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, cint, today

from logistics.air_freight.tests.test_helpers import (
	create_test_consignee,
	create_test_item,
	create_test_shipper,
	create_test_unloco,
)


class TestBlanketCallOff(FrappeTestCase):
	def setUp(self):
		self.company = (frappe.get_all("Company", limit=1, pluck="name") or [None])[0]
		self.customer = (frappe.get_all("Customer", limit=1, pluck="name") or [None])[0]
		if not self.company or not self.customer:
			self.skipTest("Site needs at least one Company and Customer")
		self.shipper = create_test_shipper()
		self.consignee = create_test_consignee()
		create_test_unloco("USLAX", "Los Angeles", "LAX", "US", "Airport")
		create_test_unloco("USJFK", "New York JFK", "JFK", "US", "Airport")
		self.item_code = create_test_item()

	def tearDown(self):
		frappe.db.rollback()

	def _blanket_sea_quote(self, charge_count=2):
		sq = frappe.get_doc(
			{
				"doctype": "Sales Quote",
				"quotation_type": "Regular",
				"naming_series": "SQU.#########",
				"blanket_quotation": 1,
				"company": self.company,
				"customer": self.customer,
				"date": today(),
				"valid_until": add_days(today(), 30),
				"shipper": self.shipper,
				"consignee": self.consignee,
				"main_service": "Sea",
				"origin_port": "USLAX",
				"destination_port": "USJFK",
			}
		)
		for i in range(charge_count):
			sq.append(
				"charges",
				{
					"service_type": "Sea",
					"charge_group": "Freight",
					"item_code": self.item_code,
					"origin_port": "USLAX",
					"destination_port": "USJFK",
					"direction": "Export",
					"calculation_method": "Fixed Amount",
					"unit_rate": 100 + i,
					"currency": "USD",
				},
			)
		sq.flags.ignore_mandatory = True
		sq.insert()
		sq.submit()
		return sq

	def test_blanket_blocked_on_one_off(self):
		sq = frappe.get_doc(
			{
				"doctype": "Sales Quote",
				"quotation_type": "One-off",
				"naming_series": "OOQ.#####",
				"blanket_quotation": 1,
				"company": self.company,
				"customer": self.customer,
				"date": today(),
				"valid_until": add_days(today(), 30),
				"shipper": self.shipper,
				"consignee": self.consignee,
				"main_service": "Sea",
			}
		)
		sq.append(
			"charges",
			{
				"service_type": "Sea",
				"origin_port": "USLAX",
				"destination_port": "USJFK",
			},
		)
		with self.assertRaises(frappe.ValidationError):
			sq.validate_blanket_quotation()

	def test_preview_returns_charge_rows(self):
		from logistics.utils.blanket_call_off import preview_blanket_call_off

		sq = self._blanket_sea_quote(charge_count=2)
		out = preview_blanket_call_off(sq.name, "Sea Booking")
		self.assertEqual(out["target_doctype"], "Sea Booking")
		self.assertEqual(len(out["charge_rows"]), 2)
		self.assertTrue(all(r["selectable"] for r in out["charge_rows"]))

	def test_create_call_off_with_selected_charges(self):
		from logistics.utils.blanket_call_off import create_blanket_call_off

		sq = self._blanket_sea_quote(charge_count=3)
		row_names = [c.name for c in sq.charges[:2]]
		result = create_blanket_call_off(
			sq.name,
			"Sea Booking",
			{
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"local_customer": self.customer,
			},
			row_names,
		)
		self.assertTrue(result.get("success"))
		sb = frappe.get_doc("Sea Booking", result["name"])
		self.assertEqual(sb.sales_quote, sq.name)
		self.assertEqual(len(sb.charges), 2)

	def test_second_call_off_allowed(self):
		from logistics.utils.blanket_call_off import create_blanket_call_off

		sq = self._blanket_sea_quote(charge_count=2)
		n1 = sq.charges[0].name
		n2 = sq.charges[1].name
		r1 = create_blanket_call_off(
			sq.name,
			"Sea Booking",
			{"origin_port": "USLAX", "destination_port": "USJFK", "local_customer": self.customer},
			[n1],
		)
		r2 = create_blanket_call_off(
			sq.name,
			"Sea Booking",
			{"origin_port": "USLAX", "destination_port": "USJFK", "local_customer": self.customer},
			[n2],
		)
		self.assertNotEqual(r1["name"], r2["name"])

	def test_expired_blanket_blocked(self):
		from logistics.utils.blanket_call_off import create_blanket_call_off

		sq = self._blanket_sea_quote(charge_count=1)
		frappe.db.set_value("Sales Quote", sq.name, "valid_until", add_days(today(), -1))
		with self.assertRaises(frappe.ValidationError):
			create_blanket_call_off(
				sq.name,
				"Sea Booking",
				{"origin_port": "USLAX", "destination_port": "USJFK"},
				[sq.charges[0].name],
			)

	def test_special_project_charge_on_sea_call_off(self):
		from logistics.utils.blanket_call_off import create_blanket_call_off

		sq = frappe.get_doc(
			{
				"doctype": "Sales Quote",
				"quotation_type": "Regular",
				"naming_series": "SQU.#########",
				"blanket_quotation": 1,
				"company": self.company,
				"customer": self.customer,
				"date": today(),
				"valid_until": add_days(today(), 30),
				"shipper": self.shipper,
				"consignee": self.consignee,
				"main_service": "Sea",
				"origin_port": "USLAX",
				"destination_port": "USJFK",
			}
		)
		sq.append(
			"charges",
			{
				"service_type": "Special Project",
				"item_code": self.item_code,
				"sp_site": "Test Site",
				"unit_rate": 250,
				"currency": "USD",
			},
		)
		sq.flags.ignore_mandatory = True
		sq.insert()
		sq.submit()
		row_name = sq.charges[0].name
		result = create_blanket_call_off(
			sq.name,
			"Sea Booking",
			{
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"local_customer": self.customer,
			},
			[row_name],
		)
		self.assertTrue(result.get("success"))
		sb = frappe.get_doc("Sea Booking", result["name"])
		self.assertEqual(len(sb.charges), 1)
		self.assertEqual(sb.charges[0].service_type, "Sea")
		self.assertEqual(cint(sb.charges[0].is_other_service), 1)

	def test_cross_service_charge_allowed_on_main_booking(self):
		from logistics.utils.blanket_call_off import create_blanket_call_off

		sq = frappe.get_doc(
			{
				"doctype": "Sales Quote",
				"quotation_type": "Regular",
				"naming_series": "SQU.#########",
				"blanket_quotation": 1,
				"company": self.company,
				"customer": self.customer,
				"date": today(),
				"valid_until": add_days(today(), 30),
				"shipper": self.shipper,
				"consignee": self.consignee,
				"main_service": "Sea",
				"origin_port": "USLAX",
				"destination_port": "USJFK",
			}
		)
		sq.append(
			"charges",
			{
				"service_type": "Sea",
				"item_code": self.item_code,
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"unit_rate": 100,
				"currency": "USD",
			},
		)
		sq.append(
			"charges",
			{
				"service_type": "Air",
				"item_code": self.item_code,
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"unit_rate": 50,
				"currency": "USD",
			},
		)
		sq.flags.ignore_mandatory = True
		sq.insert()
		sq.submit()
		air_row = sq.charges[1].name
		result = create_blanket_call_off(
			sq.name,
			"Sea Booking",
			{
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"local_customer": self.customer,
			},
			[air_row],
		)
		self.assertTrue(result.get("success"))
		sb = frappe.get_doc("Sea Booking", result["name"])
		self.assertEqual(len(sb.charges), 1)

	def test_handling_unit_cost_unit_type_maps_on_call_off(self):
		from logistics.utils.blanket_call_off import create_blanket_call_off

		sq = self._blanket_sea_quote(charge_count=1)
		ch = sq.charges[0]
		ch.db_set("unit_type", "Handling Unit")
		ch.db_set("cost_unit_type", "Handling Unit")
		result = create_blanket_call_off(
			sq.name,
			"Sea Booking",
			{
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"local_customer": self.customer,
			},
			[ch.name],
		)
		self.assertTrue(result.get("success"))
		sb = frappe.get_doc("Sea Booking", result["name"])
		self.assertEqual(len(sb.charges), 1)
		self.assertEqual(sb.charges[0].unit_type, "Package")
		self.assertEqual(sb.charges[0].cost_unit_type, "Package")
