# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import UnitTestCase

from logistics.invoice_integration.sales_invoice_api import (
	SALES_CHARGE_CONFIG,
	_get_eligible_revenue_rows,
)


class TestSalesInvoiceEligibleChargeFilters(UnitTestCase):
	def test_blank_charge_invoice_type_included_for_any_header_invoice_type(self):
		ch = frappe._dict(
			item_code="FREIGHT",
			estimated_revenue=600,
			invoice_type=None,
			sales_invoice_status=None,
			sales_invoice=None,
		)
		job = frappe._dict(charges=[ch])
		config = SALES_CHARGE_CONFIG["Sea Shipment"]
		rows = _get_eligible_revenue_rows(
			job, config, customer=None, invoice_type="Commercial Invoice"
		)
		self.assertEqual(len(rows), 1)

	def test_charge_invoice_type_must_match_when_set_on_row(self):
		ch = frappe._dict(
			item_code="FREIGHT",
			estimated_revenue=600,
			invoice_type="Import",
			sales_invoice_status=None,
			sales_invoice=None,
		)
		job = frappe._dict(charges=[ch])
		config = SALES_CHARGE_CONFIG["Sea Shipment"]
		self.assertEqual(
			len(_get_eligible_revenue_rows(job, config, customer=None, invoice_type="Import")),
			1,
		)
		self.assertEqual(
			len(_get_eligible_revenue_rows(job, config, customer=None, invoice_type="Export")),
			0,
		)
