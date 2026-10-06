# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import today

from logistics.logistics.doctype.turnover_charges_template.turnover_charges_template import (
	charge_rows_from_template,
	copy_turnover_shipment_fields,
	sync_turnover_shipment_charges,
)


class _PreviousDoc:
	def __init__(self, template_name):
		self.template_name = template_name

	def get(self, fieldname):
		if fieldname == "turnover_charges_template":
			return self.template_name
		return None


class IntegrationTestTurnoverChargesTemplate(IntegrationTestCase):
	def setUp(self):
		super().setUp()
		self.item_code = self._ensure_item()
		self.air_template = self._make_template("Air Turnover Test", "Air", 25)
		self.sea_template = self._make_template("Sea Turnover Test", "Sea", 40)

	def _ensure_item(self):
		item_code = "_Test Turnover Freight"
		if frappe.db.exists("Item", item_code):
			return item_code
		item_group = frappe.db.get_value("Item Group", {"is_group": 0}, "name") or "All Item Groups"
		stock_uom = frappe.db.get_value("UOM", {}, "name") or "Nos"
		frappe.get_doc(
			{
				"doctype": "Item",
				"item_code": item_code,
				"item_name": "Test Turnover Freight",
				"item_group": item_group,
				"stock_uom": stock_uom,
				"is_stock_item": 0,
			}
		).insert(ignore_permissions=True)
		return item_code

	def _make_template(self, name, service, rate):
		if frappe.db.exists("Turnover Charges Template", name):
			frappe.delete_doc("Turnover Charges Template", name, force=1, ignore_permissions=True)
		currency = frappe.db.get_value("Currency", {}, "name") or "USD"
		doc = frappe.get_doc(
			{
				"doctype": "Turnover Charges Template",
				"template_name": name,
				"service": service,
				"is_active": 1,
				"charges": [
					{
						"item_code": self.item_code,
						"charge_type": "Revenue",
						"revenue_calculation_method": "Flat Rate",
						"currency": currency,
						"unit_rate": rate,
					}
				],
			}
		)
		doc.insert(ignore_permissions=True)
		return doc

	def test_template_rows_use_parent_service(self):
		air_rows = charge_rows_from_template(self.air_template.name, "Air Booking")
		self.assertEqual(len(air_rows), 1)
		self.assertEqual(air_rows[0]["service_type"], "Air")
		self.assertEqual(air_rows[0]["item_code"], self.item_code)
		self.assertEqual(air_rows[0]["unit_rate"], 25)

		sea_rows = charge_rows_from_template(self.sea_template.name, "Sea Shipment")
		self.assertEqual(sea_rows[0]["service_type"], "Sea")

	def test_air_template_rejected_for_sea_document(self):
		with self.assertRaises(frappe.ValidationError):
			charge_rows_from_template(self.air_template.name, "Sea Booking")

	def test_new_booking_without_charges_loads_template(self):
		booking = frappe.new_doc("Air Booking")
		booking.is_turnover_shipment = 1
		booking.turnover_charges_template = self.air_template.name
		sync_turnover_shipment_charges(booking)
		self.assertEqual(len(booking.charges), 1)
		self.assertEqual(booking.charges[0].item_code, self.item_code)
		self.assertEqual(booking.charges[0].service_type, "Air")

	def test_template_change_replaces_charges(self):
		other = self._make_template("Air Turnover Replacement", "Air", 80)
		booking = frappe.new_doc("Air Booking")
		booking.is_turnover_shipment = 1
		booking.turnover_charges_template = other.name
		booking.append("charges", {"item_code": self.item_code, "unit_rate": 1, "service_type": "Air"})
		booking._doc_before_save = _PreviousDoc(self.air_template.name)
		sync_turnover_shipment_charges(booking)
		self.assertEqual(len(booking.charges), 1)
		self.assertEqual(booking.charges[0].unit_rate, 80)

	def test_unchecking_turnover_keeps_charges(self):
		booking = frappe.new_doc("Air Booking")
		booking.is_turnover_shipment = 0
		booking.turnover_charges_template = self.air_template.name
		booking.append("charges", {"item_code": self.item_code, "service_type": "Air", "unit_rate": 25})
		sync_turnover_shipment_charges(booking)
		self.assertFalse(booking.turnover_charges_template)
		self.assertEqual(len(booking.charges), 1)

	def test_turnover_submit_skips_sales_quote(self):
		booking = self._booking_ready_for_quote_check()
		with self.assertRaises(frappe.ValidationError) as ctx:
			booking.before_submit()
		self.assertIn("Quote is required", str(ctx.exception))

		booking.is_turnover_shipment = 1
		booking.turnover_charges_template = self.air_template.name
		booking.append(
			"charges",
			{"item_code": self.item_code, "service_type": "Air", "charge_type": "Revenue", "unit_rate": 25},
		)
		with self.assertRaises(frappe.ValidationError) as ctx:
			booking.before_submit()
		self.assertNotIn("Quote is required", str(ctx.exception))

	def test_conversion_copies_turnover_fields(self):
		source = frappe._dict(is_turnover_shipment=1, turnover_charges_template=self.air_template.name)
		target = frappe.new_doc("Air Shipment")
		copy_turnover_shipment_fields(source, target)
		self.assertEqual(target.is_turnover_shipment, 1)
		self.assertEqual(target.turnover_charges_template, self.air_template.name)

		sea_target = frappe.new_doc("Sea Shipment")
		copy_turnover_shipment_fields(
			frappe._dict(is_turnover_shipment=1, turnover_charges_template=self.sea_template.name),
			sea_target,
		)
		self.assertEqual(sea_target.turnover_charges_template, self.sea_template.name)

	def test_saved_booking_keeps_fetched_charges(self):
		company = frappe.db.get_value("Company", {}, "name")
		branch = frappe.db.get_value("Branch", {"custom_company": company}, "name") or frappe.db.get_value(
			"Branch", {}, "name"
		)
		cost_center = frappe.db.get_value("Cost Center", {"company": company, "is_group": 0}, "name")
		profit_center = frappe.db.get_value("Profit Center", {}, "name")
		if not all([company, branch, cost_center, profit_center]):
			self.skipTest("Company accounting masters are not available")

		booking = frappe.new_doc("Air Booking")
		booking.booking_date = today()
		booking.company = company
		booking.branch = branch
		booking.cost_center = cost_center
		booking.profit_center = profit_center
		booking.is_turnover_shipment = 1
		booking.turnover_charges_template = self.air_template.name
		booking.insert(ignore_permissions=True)
		booking.reload()
		self.assertEqual(len(booking.charges), 1)
		self.assertEqual(booking.charges[0].item_code, self.item_code)
		self.assertFalse(booking.sales_quote)

	def _booking_ready_for_quote_check(self):
		booking = frappe.new_doc("Air Booking")
		booking.booking_date = today()
		booking.local_customer = "_Test Turnover Customer"
		booking.direction = "Export"
		booking.shipper = "_Test Turnover Shipper"
		booking.consignee = "_Test Turnover Consignee"
		booking.origin_port = "USNYC"
		booking.destination_port = "PHMNL"
		booking.volume = 1
		return booking
