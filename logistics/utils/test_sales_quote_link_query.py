# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Tests for Sales Quote corridor / eligibility SQL in sales_quote_link_query."""

from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from logistics.air_freight.tests.test_helpers import (
	create_test_airline,
	create_test_consignee,
	create_test_shipper,
	create_test_unloco,
	setup_basic_master_data,
)
from logistics.utils.linked_service_compat import linked_service_doctype
from logistics.utils.sales_quote_link_query import (
	_corridor_match_sql,
	sales_quote_matches_job_airline_only,
	sales_quote_matches_job_corridor,
)


class TestSalesQuoteLinkQueryCorridor(FrappeTestCase):
	def setUp(self):
		data = setup_basic_master_data()
		self.company = data["company"]
		self.customer = data["customer"]
		self.shipper = create_test_shipper()
		self.consignee = create_test_consignee()
		create_test_unloco("USLAX", "Los Angeles", "LAX", "US", "Airport")
		create_test_unloco("USJFK", "New York JFK", "JFK", "US", "Airport")
		create_test_unloco("USORD", "Chicago", "ORD", "US", "Airport")
		self.airline = create_test_airline()

	def tearDown(self):
		frappe.db.rollback()

	def _regular_air_quote(self, *, origin="USLAX", dest="USJFK", airline=None, charge_scope="Main", linked_service=None):
		sq = frappe.get_doc(
			{
				"doctype": "Sales Quote",
				"quotation_type": "Regular",
				"company": self.company,
				"customer": self.customer,
				"date": today(),
				"valid_until": today(),
				"shipper": self.shipper,
				"consignee": self.consignee,
				"main_service": "Air",
				"origin_port": origin,
				"destination_port": dest,
			}
		)
		if airline:
			sq.airline = airline
		row = {
			"service_type": "Air",
			"charge_scope": charge_scope,
			"direction": "Export",
		}
		if linked_service:
			row["linked_service"] = linked_service
		sq.append("charges", row)
		sq.flags.ignore_mandatory = True
		sq.insert(ignore_permissions=True)
		sq.submit()
		return sq

	def test_corridor_sql_does_not_reference_missing_sqc_columns(self):
		"""Regression: corridor match must not query sqc.origin_port when column is absent."""
		sq = self._regular_air_quote()
		sql = _corridor_match_sql("Air")
		self.assertNotIn("sqc.origin_port", sql)
		row = frappe.db.sql(
			f"""
			SELECT 1 FROM `tabSales Quote` sq
			WHERE sq.name = %(name)s
			AND {sql}
			LIMIT 1
			""",
			{
				"name": sq.name,
				"service_types": ("Air", "air"),
				"corridor_origin": "USLAX",
				"corridor_dest": "USJFK",
			},
		)
		self.assertTrue(row)

	def test_main_scope_header_ports_match_corridor(self):
		sq = self._regular_air_quote(origin="USLAX", dest="USJFK")
		self.assertTrue(
			sales_quote_matches_job_corridor(sq.name, "Air", "USLAX", "USJFK")
		)
		self.assertFalse(
			sales_quote_matches_job_corridor(sq.name, "Air", "USLAX", "USORD")
		)

	def test_linked_scope_uses_linked_service_ports(self):
		if not frappe.db.exists("DocType", linked_service_doctype()):
			self.skipTest("Linked Service not installed")

		sq = frappe.get_doc(
			{
				"doctype": "Sales Quote",
				"quotation_type": "Regular",
				"company": self.company,
				"customer": self.customer,
				"date": today(),
				"valid_until": today(),
				"shipper": self.shipper,
				"consignee": self.consignee,
				"main_service": "Air",
				"origin_port": "USORD",
				"destination_port": "USORD",
			}
		)
		sq.flags.ignore_mandatory = True
		sq.insert(ignore_permissions=True)
		ls = frappe.get_doc(
			{
				"doctype": linked_service_doctype(),
				"parent_booking_type": "Sales Quote",
				"parent_booking_name": sq.name,
				"service_type": "Air",
				"origin_port": "USLAX",
				"destination_port": "USJFK",
			}
		)
		ls.flags.ignore_mandatory = True
		ls.insert(ignore_permissions=True)

		sq.append(
			"charges",
			{
				"service_type": "Air",
				"charge_scope": "Linked",
				"linked_service": ls.name,
			},
		)
		sq.flags.ignore_mandatory = True
		sq.submit()

		self.assertTrue(
			sales_quote_matches_job_corridor(sq.name, "Air", "USLAX", "USJFK")
		)
		self.assertFalse(
			sales_quote_matches_job_corridor(sq.name, "Air", "USJFK", "USLAX")
		)

	def test_airline_only_match_without_ports(self):
		sq = self._regular_air_quote(origin="USLAX", dest="USJFK", airline=self.airline)
		self.assertTrue(
			sales_quote_matches_job_airline_only(sq.name, self.airline)
		)
