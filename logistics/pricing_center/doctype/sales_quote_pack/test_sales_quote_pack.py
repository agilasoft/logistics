# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Tests for Sales Quote Pack submit → submit linked Sales Quotes."""

from __future__ import unicode_literals

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from logistics.air_freight.tests.test_helpers import (
	setup_basic_master_data,
	create_test_shipper,
	create_test_consignee,
	create_test_unloco,
	create_test_branch,
	create_test_cost_center,
	create_test_profit_center,
)


class TestSalesQuotePack(FrappeTestCase):
	def setUp(self):
		data = setup_basic_master_data()
		self.company = data["company"]
		self.customer = data["customer"]
		self.shipper = create_test_shipper()
		self.consignee = create_test_consignee()
		self.branch = create_test_branch(self.company)
		self.cost_center = create_test_cost_center(self.company)
		self.profit_center = create_test_profit_center(self.company)
		self.employee = frappe.db.get_value("Employee", {"status": "Active"}, "name")
		if not self.employee:
			self.employee = frappe.db.get_value("Employee", {}, "name")
		create_test_unloco("USLAX", "Los Angeles", "LAX", "US", "Airport")
		create_test_unloco("USJFK", "New York JFK", "JFK", "US", "Airport")

	def tearDown(self):
		frappe.db.rollback()

	def test_pack_doctype_exists_and_is_submittable(self):
		self.assertTrue(frappe.db.exists("DocType", "Sales Quote Pack"))
		self.assertTrue(frappe.db.exists("DocType", "Sales Quote Pack Line"))
		meta = frappe.get_meta("Sales Quote Pack")
		self.assertTrue(meta.is_submittable)

	def test_manual_accepted_status_blocked_on_draft(self):
		pack = frappe.new_doc("Sales Quote Pack")
		pack.status = "Accepted"
		pack.docstatus = 0
		with self.assertRaises(frappe.ValidationError):
			pack._validate_manual_accepted_status()

	def test_manual_accepted_allowed_on_submit_action(self):
		pack = frappe.new_doc("Sales Quote Pack")
		pack.status = "Accepted"
		pack._action = "submit"
		pack._validate_manual_accepted_status()

	def test_direct_submit_blocked_when_pack_linked(self):
		sq = frappe.new_doc("Sales Quote")
		sq.name = "SQ-PACK-GATE-TEST"
		sq.sales_quote_pack = "SQP-FAKE"
		with self.assertRaises(frappe.ValidationError) as ctx:
			sq.validate_submit_via_sales_quote_pack()
		self.assertIn("Sales Quote Pack", str(ctx.exception))

	def test_direct_submit_allowed_with_pack_flag(self):
		sq = frappe.new_doc("Sales Quote")
		sq.name = "SQ-PACK-GATE-OK"
		sq.sales_quote_pack = "SQP-FAKE"
		sq.flags.submit_from_sales_quote_pack = True
		sq.validate_submit_via_sales_quote_pack()

	def test_direct_submit_allowed_without_pack(self):
		sq = frappe.new_doc("Sales Quote")
		sq.name = "SQ-NO-PACK"
		sq.sales_quote_pack = None
		sq.validate_submit_via_sales_quote_pack()

	def _quote_defaults(self, sales_quote_pack=None):
		defaults = {
			"doctype": "Sales Quote",
			"quotation_type": "Regular",
			"company": self.company,
			"customer": self.customer,
			"date": today(),
			"valid_until": today(),
			"shipper": self.shipper,
			"consignee": self.consignee,
			"main_service": "Air",
			"origin_port": "USLAX",
			"destination_port": "USJFK",
			"branch": self.branch,
			"cost_center": self.cost_center,
			"profit_center": self.profit_center,
			"sales_quote_pack": sales_quote_pack,
		}
		if self.employee:
			defaults["sales_rep"] = self.employee
			defaults["customer_service_rep"] = self.employee
		return defaults

	def _make_air_quote(self, sales_quote_pack=None, with_charges=True):
		sq = frappe.get_doc(self._quote_defaults(sales_quote_pack))
		if with_charges:
			sq.append(
				"charges",
				{
					"service_type": "Air",
					"origin_port": "USLAX",
					"destination_port": "USJFK",
					"direction": "Export",
				},
			)
		sq.insert()
		return sq

	def _make_pack(self, quotes):
		pack = frappe.get_doc(
			{
				"doctype": "Sales Quote Pack",
				"naming_series": "SQP-.YYYY.-.#####",
				"title": "Test Pack Submit",
				"status": "Draft",
				"customer": self.customer,
				"company": self.company,
				"date": today(),
				"branch": self.branch,
				"cost_center": self.cost_center,
				"profit_center": self.profit_center,
			}
		)
		if self.employee:
			pack.sales_rep = self.employee
			pack.customer_service_rep = self.employee
		for i, sq_name in enumerate(quotes, start=1):
			pack.append(
				"quotations",
				{
					"line_sequence": i,
					"sales_quote": sq_name,
					"include_in_total": 1,
				},
			)
		pack.insert()
		# First insert skips link sync (is_new); save again to sync sales_quote_pack.
		pack.reload()
		pack.save()
		return pack

	def test_pack_submit_submits_linked_quotes_and_sets_accepted(self):
		sq = self._make_air_quote()
		pack = self._make_pack([sq.name])
		sq.reload()
		self.assertEqual(sq.sales_quote_pack, pack.name)
		self.assertEqual(sq.docstatus, 0)

		with self.assertRaises(frappe.ValidationError):
			sq.submit()

		pack.submit()
		pack.reload()
		sq.reload()

		self.assertEqual(pack.docstatus, 1)
		self.assertEqual(pack.status, "Accepted")
		self.assertEqual(sq.docstatus, 1)

	def test_pack_submit_skips_already_submitted_quote(self):
		sq = self._make_air_quote()
		sq.submit()
		self.assertEqual(sq.docstatus, 1)

		pack = self._make_pack([sq.name])
		pack.submit()
		pack.reload()
		sq.reload()

		self.assertEqual(pack.docstatus, 1)
		self.assertEqual(pack.status, "Accepted")
		self.assertEqual(sq.docstatus, 1)

	def test_pack_submit_fails_when_quote_invalid_leaves_pack_draft(self):
		# Insertable but not submittable: Air main with no matching charges.
		sq = self._make_air_quote(with_charges=False)
		pack = self._make_pack([sq.name])

		with self.assertRaises(frappe.ValidationError):
			pack.submit()

		pack.reload()
		sq.reload()
		self.assertEqual(pack.docstatus, 0)
		self.assertNotEqual(pack.status, "Accepted")
		self.assertEqual(sq.docstatus, 0)

	def test_free_sales_quote_still_submits(self):
		sq = self._make_air_quote()
		self.assertFalse(sq.sales_quote_pack)
		sq.submit()
		self.assertEqual(sq.docstatus, 1)

	def test_pack_cancel_sets_cancelled_without_cancelling_quotes(self):
		sq = self._make_air_quote()
		pack = self._make_pack([sq.name])
		pack.submit()
		sq.reload()
		self.assertEqual(sq.docstatus, 1)

		pack.cancel()
		pack.reload()
		sq.reload()

		self.assertEqual(pack.docstatus, 2)
		self.assertEqual(pack.status, "Cancelled")
		self.assertEqual(sq.docstatus, 1)
