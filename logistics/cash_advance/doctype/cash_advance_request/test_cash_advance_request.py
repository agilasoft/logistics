# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, getdate

from logistics.cash_advance.doctype.cash_advance_settings.cash_advance_settings import (
	compute_liquidation_due_date,
)


class TestCashAdvanceLiquidationDueDate(FrappeTestCase):
	def test_compute_liquidation_due_date_uses_offset(self):
		company = "_Test CA Due Date Co"
		if not frappe.db.exists("Company", company):
			company_doc = frappe.get_doc(
				{
					"doctype": "Company",
					"company_name": company,
					"abbr": "TCAD",
					"default_currency": frappe.defaults.get_global_default("currency") or "USD",
					"country": frappe.defaults.get_global_default("country") or "United States",
				}
			)
			company_doc.insert(ignore_permissions=True)

		settings_name = frappe.db.get_value("Cash Advance Settings", {"company": company}, "name")
		if settings_name:
			settings = frappe.get_doc("Cash Advance Settings", settings_name)
		else:
			settings = frappe.get_doc({"doctype": "Cash Advance Settings", "company": company})
			settings.insert(ignore_permissions=True)

		settings.liquidation_due_date_offset_days = 7
		settings.save(ignore_permissions=True)

		request_date = "2026-01-15"
		expected = add_days(getdate(request_date), 7)
		self.assertEqual(compute_liquidation_due_date(request_date, company), expected)
