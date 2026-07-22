# Copyright (c) 2026, AgilaSoft and contributors
# See license.txt

"""Unit tests for Get Charges from Tariff helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

from frappe.tests.utils import FrappeTestCase

from logistics.utils.tariff_charge_copy import (
	_customer_matches_job,
	_tariff_matches_job_customer,
	tariff_charge_row_as_quote_like_dict,
	tariff_charge_row_matches_booking_corridor,
)


class TestTariffChargeCopyHelpers(FrappeTestCase):
	def test_customer_match_case_insensitive(self):
		self.assertTrue(_customer_matches_job("CUST-1", "cust-1"))

	def test_tariff_all_customers_matches_any_customer(self):
		tariff = MagicMock()
		tariff.tariff_type = "All Customers"
		self.assertTrue(_tariff_matches_job_customer(tariff, "ACME"))

	def test_tariff_customer_type_requires_match(self):
		tariff = MagicMock()
		tariff.tariff_type = "Customer"
		tariff.customer = "ACME"
		self.assertTrue(_tariff_matches_job_customer(tariff, "acme"))
		self.assertFalse(_tariff_matches_job_customer(tariff, "OTHER"))

	def test_corridor_blank_tariff_row_is_wildcard(self):
		row = {"origin_port": "", "destination_port": "", "shipping_line": ""}
		self.assertTrue(
			tariff_charge_row_matches_booking_corridor(
				row,
				doctype="Sea Booking",
				origin="SGSIN",
				destination="USLAX",
				shipping_line="MAEU",
			)
		)

	def test_corridor_requires_match_when_row_is_set(self):
		row = {"origin_port": "SGSIN", "destination_port": "USLAX", "shipping_line": ""}
		self.assertTrue(
			tariff_charge_row_matches_booking_corridor(
				row,
				doctype="Sea Booking",
				origin="SGSIN",
				destination="USLAX",
			)
		)
		self.assertFalse(
			tariff_charge_row_matches_booking_corridor(
				row,
				doctype="Sea Booking",
				origin="HKHKG",
				destination="USLAX",
			)
		)

	def test_tariff_row_adapter_sets_tariff_links(self):
		row = MagicMock()
		row.as_dict.return_value = {
			"item_code": "FRT-SEA",
			"service_type": "Sea",
			"revenue_calculation_method": "Per Unit",
			"unit_rate": 100,
		}
		out = tariff_charge_row_as_quote_like_dict(row, "TAR-001")
		self.assertEqual(out["revenue_tariff"], "TAR-001")
		self.assertEqual(out["cost_tariff"], "TAR-001")
		self.assertEqual(out["use_tariff_in_revenue"], 0)
