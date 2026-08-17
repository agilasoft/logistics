# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Regression: Sales Quote Cost tariff fetch must use unit_cost, not unit_rate."""

import uuid

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, flt, today

from logistics.air_freight.tests.test_helpers import (
	create_test_currency,
	create_test_item,
	setup_basic_master_data,
)
from logistics.utils.charges_calculation import _fetch_rates_from_tariff_if_needed


class TestTariffCostSideFetch(FrappeTestCase):
	def setUp(self):
		if not frappe.db.exists("DocType", "Tariff"):
			self.skipTest("Tariff DocType not installed")
		if not frappe.db.exists("DocType", "Sales Quote Charge"):
			self.skipTest("Sales Quote Charge DocType not installed")
		setup_basic_master_data()
		create_test_currency("USD")
		self.item_code = create_test_item(f"COST-SIDE-ITEM-{uuid.uuid4().hex[:8]}")

	def tearDown(self):
		frappe.db.rollback()

	def _ensure_uom(self, name):
		if not frappe.db.exists("UOM", name):
			frappe.get_doc({"doctype": "UOM", "uom_name": name, "enabled": 1}).insert(
				ignore_permissions=True
			)
		return name

	def test_fetch_rates_uses_unit_cost_not_unit_rate_for_cost_side(self):
		"""Cost tariff fetch must map Tariff Charge.unit_cost, not unit_rate."""
		self._ensure_uom("Container")
		self._ensure_uom("Trip")
		tariff = frappe.get_doc(
			{
				"doctype": "Tariff",
				"tariff_name": f"COST-SIDE-TAR-{uuid.uuid4().hex[:8]}",
				"tariff_type": "All Customers",
				"currency": "USD",
				"valid_from": today(),
				"valid_to": add_days(today(), 365),
				"is_active": 1,
			}
		)
		tariff.flags.ignore_mandatory = True
		tariff.insert(ignore_permissions=True)
		tariff.append(
			"rates",
			{
				"service_type": "Air",
				"charge_type": "Margin",
				"item_code": self.item_code,
				"revenue_calculation_method": "Per Unit",
				"unit_rate": 0,
				"quantity": 1,
				"currency": "USD",
				"uom": "Container",
				"unit_type": "TEU",
				"cost_calculation_method": "Per Unit",
				"unit_cost": 200,
				"cost_quantity": 1,
				"cost_currency": "USD",
				"cost_uom": "Trip",
				"cost_unit_type": "Trip",
				"tariff_valid_from": today(),
				"tariff_rate_active": 1,
			},
		)
		tariff.flags.ignore_mandatory = True
		tariff.save(ignore_permissions=True)

		charge_doc = frappe._dict(
			doctype="Sales Quote Charge",
			name=f"new-sqc-{uuid.uuid4().hex[:8]}",
			item_code=self.item_code,
			service_type="Air",
			charge_type="Margin",
			revenue_tariff=tariff.name,
			cost_tariff=tariff.name,
			use_tariff_in_revenue=1,
			use_tariff_in_cost=1,
			unit_rate=0,
			unit_cost=0,
			currency="USD",
			cost_currency="USD",
		)
		charge_doc.meta = frappe.get_meta("Sales Quote Charge")

		_fetch_rates_from_tariff_if_needed(charge_doc)

		self.assertEqual(flt(charge_doc.unit_rate), 0)
		self.assertEqual(flt(charge_doc.unit_cost), 200)
		self.assertEqual(charge_doc.uom, "Container")
		self.assertEqual(charge_doc.unit_type, "TEU")
		self.assertEqual(charge_doc.cost_uom, "Trip")
		self.assertEqual(charge_doc.cost_unit_type, "Trip")
		self.assertEqual(flt(charge_doc.quantity), 1)
		self.assertEqual(flt(charge_doc.cost_quantity), 1)
		self.assertEqual(int(flt(charge_doc.use_tariff_in_cost) or 0), 1)

	def test_fetch_copies_quantity_from_tariff_on_select(self):
		"""Selecting revenue/cost tariff must copy quantity and cost_quantity from the rate line."""
		self._ensure_uom("Container")
		self._ensure_uom("Trip")
		tariff = frappe.get_doc(
			{
				"doctype": "Tariff",
				"tariff_name": f"QTY-FETCH-TAR-{uuid.uuid4().hex[:8]}",
				"tariff_type": "All Customers",
				"currency": "USD",
				"valid_from": today(),
				"valid_to": add_days(today(), 365),
				"is_active": 1,
			}
		)
		tariff.flags.ignore_mandatory = True
		tariff.insert(ignore_permissions=True)
		tariff.append(
			"rates",
			{
				"service_type": "Sea",
				"charge_type": "Margin",
				"item_code": self.item_code,
				"revenue_calculation_method": "Per Unit",
				"unit_rate": 50,
				"quantity": 3,
				"currency": "USD",
				"uom": "Container",
				"unit_type": "TEU",
				"cost_calculation_method": "Per Unit",
				"unit_cost": 1000,
				"cost_quantity": 2,
				"cost_currency": "USD",
				"cost_uom": "Trip",
				"cost_unit_type": "Trip",
				"tariff_valid_from": today(),
				"tariff_rate_active": 1,
			},
		)
		tariff.flags.ignore_mandatory = True
		tariff.save(ignore_permissions=True)

		charge_doc = frappe._dict(
			doctype="Sales Quote Charge",
			name=f"new-sqc-{uuid.uuid4().hex[:8]}",
			item_code=self.item_code,
			service_type="Sea",
			charge_type="Margin",
			revenue_tariff=tariff.name,
			cost_tariff=tariff.name,
			use_tariff_in_revenue=1,
			use_tariff_in_cost=1,
			unit_rate=0,
			unit_cost=0,
			quantity=0,
			cost_quantity=0,
			currency="USD",
			cost_currency="USD",
		)
		charge_doc.meta = frappe.get_meta("Sales Quote Charge")

		_fetch_rates_from_tariff_if_needed(charge_doc)

		self.assertEqual(flt(charge_doc.unit_rate), 50)
		self.assertEqual(flt(charge_doc.unit_cost), 1000)
		self.assertEqual(flt(charge_doc.quantity), 3)
		self.assertEqual(flt(charge_doc.cost_quantity), 2)
		self.assertEqual(charge_doc.uom, "Container")
		self.assertEqual(charge_doc.cost_uom, "Trip")
		self.assertEqual(charge_doc.revenue_calculation_method, "Per Unit")
		self.assertEqual(charge_doc.cost_calculation_method, "Per Unit")
		self.assertEqual(int(flt(charge_doc.use_tariff_in_revenue) or 0), 1)
		self.assertEqual(int(flt(charge_doc.use_tariff_in_cost) or 0), 1)
