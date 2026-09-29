# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and Contributors

from __future__ import unicode_literals

import frappe
from frappe.tests.utils import FrappeTestCase


class TestBusinessPartnerCountryListView(FrappeTestCase):
	def test_country_is_list_view_column(self):
		for doctype in ("Consignee", "Customer", "Freight Agent", "Supplier"):
			if not frappe.db.exists("DocType", doctype):
				continue
			meta = frappe.get_meta(doctype)
			country = meta.get_field("country")
			self.assertIsNotNone(country, msg=f"{doctype} missing country field")
			self.assertTrue(
				country.in_list_view,
				msg=f"{doctype}.country should appear in list view (#1458)",
			)
