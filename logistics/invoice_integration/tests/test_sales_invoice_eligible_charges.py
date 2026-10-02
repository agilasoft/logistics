# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.tests import UnitTestCase

from logistics.invoice_integration.sales_invoice_api import (
	SALES_CHARGE_CONFIG,
	_default_invoice_customer,
	_get_eligible_revenue_rows,
)


def _satellite(**kwargs):
	data = {
		"service_role": "Linked",
		"main_service_type": "Sea Shipment",
		"main_service": "SS-MAIN",
		"local_customer": "Brand X",
		"customer": "Brand X",
	}
	data.update(kwargs)
	return frappe._dict(data)


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

	def test_linked_service_satellite_defaults_customer_to_bill_to(self):
		job = _satellite(
			charges=[
				frappe._dict(charge_type="Revenue", bill_to="ATN"),
				frappe._dict(charge_type="Cost", bill_to="Brand X"),
			]
		)
		self.assertEqual(_default_invoice_customer(job), "ATN")

	def test_linked_service_uses_most_common_bill_to_then_first_seen(self):
		job = _satellite(
			charges=[
				frappe._dict(charge_type="Revenue", bill_to="OTHER"),
				frappe._dict(charge_type="Margin", bill_to="ATN"),
				frappe._dict(charge_type="Disbursement", bill_to="ATN"),
			]
		)
		self.assertEqual(_default_invoice_customer(job), "ATN")
		tie = _satellite(
			charges=[
				frappe._dict(charge_type="Revenue", bill_to="FIRST"),
				frappe._dict(charge_type="Revenue", bill_to="SECOND"),
			]
		)
		self.assertEqual(_default_invoice_customer(tie), "FIRST")

	def test_linked_service_without_bill_to_keeps_header_customer(self):
		job = _satellite(
			charges=[frappe._dict(charge_type="Revenue", bill_to="")]
		)
		self.assertEqual(_default_invoice_customer(job), "Brand X")

	def test_main_job_keeps_header_customer(self):
		job = frappe._dict(
			service_role="Main",
			local_customer="Brand X",
			charges=[frappe._dict(charge_type="Revenue", bill_to="ATN")],
		)
		self.assertEqual(_default_invoice_customer(job), "Brand X")

	def test_air_shipment_bill_to_does_not_filter_charges(self):
		config = SALES_CHARGE_CONFIG["Air Shipment"]
		job = frappe._dict(
			charges=[
				frappe._dict(
					item_code="FREIGHT",
					estimated_revenue=100,
					bill_to="ATN",
					sales_invoice_status=None,
					sales_invoice=None,
				),
				frappe._dict(
					item_code="HANDLING",
					estimated_revenue=50,
					bill_to=None,
					sales_invoice_status=None,
					sales_invoice=None,
				),
				frappe._dict(
					item_code="DOCS",
					estimated_revenue=25,
					bill_to="Brand X",
					sales_invoice_status=None,
					sales_invoice=None,
				),
			]
		)
		rows = _get_eligible_revenue_rows(job, config, customer="ATN")
		self.assertEqual([row[3] for row in rows], ["FREIGHT", "HANDLING", "DOCS"])
