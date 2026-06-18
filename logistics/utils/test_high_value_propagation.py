# Copyright (c) 2026, www.agilasoft.com and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from logistics.utils.module_integration import apply_high_value_from_linked_sales_quote


class UnitTestHighValuePropagation(UnitTestCase):
	def test_apply_high_value_from_linked_sales_quote_sets_flag(self):
		booking = frappe.get_doc(
			{"doctype": "Air Booking", "sales_quote": "SQ-TEST-HV", "is_high_value": 0}
		)
		with patch(
			"logistics.utils.module_integration.frappe.db.get_value",
			return_value=1,
		):
			apply_high_value_from_linked_sales_quote(booking)
		self.assertEqual(booking.is_high_value, 1)

	def test_apply_high_value_from_linked_sales_quote_noop_when_quote_not_high(self):
		booking = frappe.get_doc(
			{"doctype": "Air Booking", "sales_quote": "SQ-TEST-HV", "is_high_value": 0}
		)
		with patch(
			"logistics.utils.module_integration.frappe.db.get_value",
			return_value=0,
		):
			apply_high_value_from_linked_sales_quote(booking)
		self.assertEqual(booking.is_high_value, 0)

	def test_apply_high_value_skipped_on_duplicate_pricing_cleared(self):
		booking = frappe.get_doc(
			{"doctype": "Air Booking", "sales_quote": "SQ-TEST-HV", "is_high_value": 0}
		)
		booking.flags.logistics_duplicate_pricing_cleared = True
		with patch(
			"logistics.utils.module_integration.frappe.db.get_value",
			return_value=1,
		) as mock_get:
			apply_high_value_from_linked_sales_quote(booking)
		mock_get.assert_not_called()
		self.assertEqual(booking.is_high_value, 0)
