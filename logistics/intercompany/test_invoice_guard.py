# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Intercompany invoice creation can tell its own Sales Invoice from the customer invoice."""

from __future__ import annotations

import unittest

from logistics.intercompany.invoice_guard import (
	INTERCOMPANY_JOB_TYPES,
	intercompany_sales_invoice_marked,
	relationship_for_companies,
)


class TestIntercompanyGuard(unittest.TestCase):
	def test_customer_invoice_is_not_the_intercompany_leg(self):
		self.assertFalse(intercompany_sales_invoice_marked(False, "Customer invoice"))
		self.assertFalse(intercompany_sales_invoice_marked(False, None))
		self.assertFalse(intercompany_sales_invoice_marked(None, " intercompany: lower case"))

	def test_creation_flag_marks_the_operating_company_invoice(self):
		self.assertTrue(intercompany_sales_invoice_marked(True, ""))
		self.assertTrue(intercompany_sales_invoice_marked(True, None))

	def test_remarks_prefix_marks_a_saved_intercompany_invoice(self):
		self.assertTrue(
			intercompany_sales_invoice_marked(False, "  Intercompany: from Sales Quote SQ-1.")
		)

	def test_relationship_uses_billing_company_and_operating_company(self):
		rows = [
			{
				"billing_company": "Main Co",
				"operating_company": "Ops Co",
				"internal_customer": "Main as Customer",
				"internal_supplier": "Ops as Supplier",
			},
			{
				"billing_company": "Other",
				"operating_company": "Ops Co",
				"internal_customer": "Wrong",
				"internal_supplier": "Wrong",
			},
		]
		self.assertEqual(
			relationship_for_companies(rows, "Main Co", "Ops Co"),
			{"internal_customer": "Main as Customer", "internal_supplier": "Ops as Supplier"},
		)
		self.assertIsNone(relationship_for_companies(rows, "Ops Co", "Main Co"))
		self.assertIsNone(relationship_for_companies(None, "Main Co", "Ops Co"))

	def test_a_matched_row_keeps_blank_parties(self):
		rows = [{"billing_company": "Main Co", "operating_company": "Ops Co"}]
		self.assertEqual(
			relationship_for_companies(rows, "Main Co", "Ops Co"),
			{"internal_customer": None, "internal_supplier": None},
		)

	def test_eligible_job_types(self):
		self.assertIn("Warehouse Job", INTERCOMPANY_JOB_TYPES)
		self.assertIn("Declaration Order", INTERCOMPANY_JOB_TYPES)
		self.assertNotIn("Transport Order", INTERCOMPANY_JOB_TYPES)
		self.assertNotIn("Sales Quote", INTERCOMPANY_JOB_TYPES)


if __name__ == "__main__":
	unittest.main()
