# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import uuid

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from logistics.air_freight.tests.test_helpers import (
	create_test_currency,
	create_test_item,
	create_test_unloco,
	setup_basic_master_data,
)


def _minimal_air_tariff_charge_row(**extra):
	row = {
		"service_type": "Air",
		"charge_type": "Revenue",
		"revenue_calculation_method": "Per Unit",
		"cost_calculation_method": "Per Unit",
		"item_code": "Test Air Freight Item",
		"unit_rate": 100.0,
		"unit_cost": 100.0,
		"quantity": 1,
		"cost_quantity": 1,
		"currency": "USD",
		"cost_currency": "USD",
		"tariff_valid_from": today(),
		"tariff_rate_active": 1,
	}
	row.update(extra)
	return row


class TestAirFreightRate(FrappeTestCase):
	"""Tariff air lines are modeled as ``Tariff Charge`` rows with service_type Air."""

	def setUp(self):
		data = setup_basic_master_data()
		self.company = data["company"]
		create_test_item()
		create_test_currency("USD")
		create_test_unloco("USLAX", "Los Angeles", "LAX", "US", "Airport")
		create_test_unloco("USJFK", "New York JFK", "JFK", "US", "Airport")

		tariff_name = f"Test-AF-Tariff-{uuid.uuid4().hex[:8]}"
		tariff = frappe.get_doc(
			{
				"doctype": "Tariff",
				"tariff_name": tariff_name,
				"tariff_type": "All Customers",
				"currency": "USD",
				"valid_from": today(),
				"valid_to": add_days(today(), 365),
			}
		)
		tariff.flags.ignore_mandatory = True
		tariff.insert(ignore_permissions=True)
		self.tariff_name = tariff.name

	def tearDown(self):
		frappe.db.rollback()

	def _create_rate_in_tariff(self, rate_data):
		tariff = frappe.get_doc("Tariff", self.tariff_name)
		rate = tariff.append("rates", rate_data)
		tariff.flags.ignore_mandatory = True
		tariff.save()
		return rate

	def test_air_freight_rate_creation(self):
		tariff = frappe.get_doc("Tariff", self.tariff_name)
		tariff.append("rates", _minimal_air_tariff_charge_row())
		tariff.flags.ignore_mandatory = True
		tariff.save()

		row = tariff.rates[-1]
		self.assertEqual(row.item_code, "Test Air Freight Item")
		self.assertEqual(row.revenue_calculation_method, "Per Unit")
		self.assertEqual(row.unit_rate, 100.0)
		self.assertEqual(row.currency, "USD")

	def test_air_freight_rate_required_fields(self):
		tariff = frappe.get_doc("Tariff", self.tariff_name)
		tariff.append("rates", {})
		tariff.flags.ignore_mandatory = True
		with self.assertRaises((frappe.ValidationError, frappe.MandatoryError)):
			tariff.save()

	def test_air_freight_rate_with_route(self):
		tariff = frappe.get_doc("Tariff", self.tariff_name)
		tariff.append(
			"rates",
			_minimal_air_tariff_charge_row(
				unit_rate=150.0,
				unit_cost=150.0,
				origin_port="USLAX",
				destination_port="USJFK",
			),
		)
		tariff.flags.ignore_mandatory = True
		tariff.save()
		row = tariff.rates[-1]
		self.assertEqual(row.origin_port, "USLAX")
		self.assertEqual(row.destination_port, "USJFK")

	def test_air_freight_rate_active_inactive(self):
		tariff = frappe.get_doc("Tariff", self.tariff_name)
		tariff.append("rates", _minimal_air_tariff_charge_row(tariff_rate_active=0))
		tariff.flags.ignore_mandatory = True
		tariff.save()
		tariff.reload()
		row = tariff.rates[-1]
		self.assertEqual(row.tariff_rate_active, 0)
		row.tariff_rate_active = 1
		tariff.flags.ignore_mandatory = True
		tariff.save()
		tariff.reload()
		self.assertEqual(tariff.rates[-1].tariff_rate_active, 1)
