# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Purchase and sales invoices take dimensions that belong to the invoice company.

A linked Transport Job posts in the operating company. The main job's profit
center must not be copied onto that invoice, and a session default from the
main company must not remain on item lines.

Intercompany invoices split the source. The Sales Invoice follows the Linked
Service company, branch, cost center, and profit center. The Purchase Invoice
follows the Main job.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import UnitTestCase

from logistics.invoice_integration.purchase_invoice_api import create_purchase_invoice
from logistics.invoice_integration.purchase_invoice_dimensions import (
	align_invoice_dimensions_to_company,
	dimensions_belonging_to_company,
	dimensions_for_operational_job,
	intercompany_purchase_invoice_dimensions,
	intercompany_sales_invoice_dimensions,
)

FAST_PRIME = "FAST PRIME TRANSPORT CORP."
MAIN_PC = "ATN-SALES"
LINKED_PC = "FPT-HAU"


def _belongs_to_fast_prime(fieldname, value, company):
	return company == FAST_PRIME and value == LINKED_PC


class TestPurchaseInvoiceDimensions(UnitTestCase):
	def test_linked_service_profit_center_replaces_main_job_value(self):
		job = frappe._dict(
			doctype="Transport Job",
			name="TRJ000000016",
			company=FAST_PRIME,
			profit_center=MAIN_PC,
			branch="PNS - FPT",
			cost_center="Main - FPT",
		)
		with (
			patch(
				"logistics.utils.service_role_rules.is_linked_service_satellite",
				return_value=True,
			),
			patch(
				"logistics.utils.service_role_rules.get_linked_service_name",
				return_value="LS-FPT",
			),
			patch(
				"logistics.utils.linked_service_compat.linked_service_doctype",
				return_value="Linked Service",
			),
			patch(
				"logistics.utils.linked_service_company.accounting_dimensions_from_linked_service",
				return_value={
					"profit_center": LINKED_PC,
					"branch": "PNS - FPT",
					"cost_center": "Main - FPT",
				},
			),
			patch(
				"logistics.invoice_integration.purchase_invoice_dimensions.dimension_belongs",
				side_effect=_belongs_to_fast_prime,
			),
		):
			dims = dimensions_for_operational_job(job)

		self.assertEqual(dims.get("profit_center"), LINKED_PC)
		self.assertNotEqual(dims.get("profit_center"), MAIN_PC)

	def test_standalone_job_keeps_profit_center_that_belongs(self):
		job = frappe._dict(
			doctype="Transport Job",
			name="TJ-OWN",
			company=FAST_PRIME,
			profit_center=LINKED_PC,
		)
		with patch(
			"logistics.invoice_integration.purchase_invoice_dimensions.dimension_belongs",
			side_effect=_belongs_to_fast_prime,
		):
			dims = dimensions_for_operational_job(job)
		self.assertEqual(dims.get("profit_center"), LINKED_PC)

	def test_value_from_another_company_is_omitted(self):
		job = frappe._dict(
			doctype="Transport Job",
			name="TJ-FOREIGN",
			company=FAST_PRIME,
			profit_center=MAIN_PC,
		)
		with patch(
			"logistics.invoice_integration.purchase_invoice_dimensions.dimension_belongs",
			side_effect=_belongs_to_fast_prime,
		):
			dims = dimensions_for_operational_job(job)
		self.assertNotIn("profit_center", dims)

	def test_intercompany_pi_keeps_main_profit_center_when_it_belongs(self):
		def belongs(fieldname, value, company):
			return company == "ALL TRANSPORT" and value == MAIN_PC

		with patch(
			"logistics.invoice_integration.purchase_invoice_dimensions.dimension_belongs",
			side_effect=belongs,
		):
			dims = dimensions_belonging_to_company(
				"ALL TRANSPORT",
				{"profit_center": MAIN_PC},
				{"profit_center": LINKED_PC},
				frappe._dict(profit_center=LINKED_PC),
			)
		self.assertEqual(dims.get("profit_center"), MAIN_PC)

	def test_intercompany_pi_uses_linked_service_when_main_does_not_belong(self):
		"""The generic walker still falls back. Intercompany purchase invoices do not use that fallback."""
		with patch(
			"logistics.invoice_integration.purchase_invoice_dimensions.dimension_belongs",
			side_effect=_belongs_to_fast_prime,
		):
			dims = dimensions_belonging_to_company(
				FAST_PRIME,
				{"profit_center": MAIN_PC},
				{"profit_center": LINKED_PC},
				frappe._dict(profit_center=MAIN_PC),
			)
		self.assertEqual(dims.get("profit_center"), LINKED_PC)


class TestAlignInvoiceDimensions(UnitTestCase):
	def _meta(self):
		meta = MagicMock()

		def get_field(fieldname):
			if fieldname in ("branch", "cost_center", "profit_center", "project"):
				return object()
			return None

		meta.get_field.side_effect = get_field
		return meta

	def _invoice(self, header, *item_values):
		items = [
			frappe._dict(doctype="Purchase Invoice Item", profit_center=value)
			for value in item_values
		]
		return frappe._dict(
			doctype="Purchase Invoice",
			company=FAST_PRIME,
			profit_center=header,
			items=items,
			taxes=[],
		)

	def test_child_session_default_is_replaced_from_header(self):
		doc = self._invoice(LINKED_PC, MAIN_PC, LINKED_PC)
		with (
			patch(
				"logistics.invoice_integration.purchase_invoice_dimensions.frappe.get_meta",
				return_value=self._meta(),
			),
			patch(
				"logistics.invoice_integration.purchase_invoice_dimensions.dimension_belongs",
				side_effect=_belongs_to_fast_prime,
			),
			patch(
				"logistics.invoice_integration.purchase_invoice_dimensions.frappe.db.exists",
				return_value=False,
			),
		):
			align_invoice_dimensions_to_company(doc)

		self.assertEqual(doc.profit_center, LINKED_PC)
		self.assertEqual(doc["items"][0].profit_center, LINKED_PC)
		self.assertEqual(doc["items"][1].profit_center, LINKED_PC)

	def test_blank_child_is_left_blank(self):
		doc = self._invoice(LINKED_PC, None)
		with (
			patch(
				"logistics.invoice_integration.purchase_invoice_dimensions.frappe.get_meta",
				return_value=self._meta(),
			),
			patch(
				"logistics.invoice_integration.purchase_invoice_dimensions.dimension_belongs",
				side_effect=_belongs_to_fast_prime,
			),
		):
			align_invoice_dimensions_to_company(doc)
		self.assertFalse(doc["items"][0].profit_center)

	def test_invalid_header_and_child_are_cleared_without_a_replacement(self):
		doc = self._invoice(MAIN_PC, MAIN_PC)
		with (
			patch(
				"logistics.invoice_integration.purchase_invoice_dimensions.frappe.get_meta",
				return_value=self._meta(),
			),
			patch(
				"logistics.invoice_integration.purchase_invoice_dimensions.dimension_belongs",
				side_effect=_belongs_to_fast_prime,
			),
			patch(
				"logistics.invoice_integration.purchase_invoice_dimensions.frappe.db.exists",
				return_value=False,
			),
		):
			align_invoice_dimensions_to_company(doc)
		self.assertIsNone(doc.profit_center)
		self.assertIsNone(doc["items"][0].profit_center)

	def test_invalid_header_is_replaced_from_referenced_job(self):
		doc = self._invoice(MAIN_PC, MAIN_PC)
		doc.reference_doctype = "Transport Job"
		doc.reference_name = "TRJ000000016"
		job = frappe._dict(
			doctype="Transport Job",
			name="TRJ000000016",
			company=FAST_PRIME,
			profit_center=LINKED_PC,
		)
		with (
			patch(
				"logistics.invoice_integration.purchase_invoice_dimensions.frappe.get_meta",
				return_value=self._meta(),
			),
			patch(
				"logistics.invoice_integration.purchase_invoice_dimensions.dimension_belongs",
				side_effect=_belongs_to_fast_prime,
			),
			patch(
				"logistics.invoice_integration.purchase_invoice_dimensions.frappe.db.exists",
				return_value=True,
			),
			patch(
				"logistics.invoice_integration.purchase_invoice_dimensions.frappe.get_doc",
				return_value=job,
			),
		):
			align_invoice_dimensions_to_company(doc)
		self.assertEqual(doc.profit_center, LINKED_PC)
		self.assertEqual(doc["items"][0].profit_center, LINKED_PC)


class TestCreatePurchaseInvoiceStampsLinkedProfitCenter(UnitTestCase):
	def _mock_job(self):
		charge = frappe._dict(
			name="ch-1",
			item_code="LOCTRK",
			estimated_cost=100,
			actual_cost=0,
			cost_currency="PHP",
			currency="PHP",
			purchase_invoice_status=None,
			purchase_invoice=None,
			pay_to="FAST",
		)
		return frappe._dict(
			doctype="Transport Job",
			name="TRJ000000016",
			company=FAST_PRIME,
			customer="ALL TRANSPORT",
			job_number="TRJ000000016",
			profit_center=MAIN_PC,
			service_role="Linked",
			charges=[charge],
		)

	@patch(
		"logistics.invoice_integration.purchase_invoice_api.reference_dimension_row_dict",
		return_value={},
	)
	@patch("logistics.invoice_integration.purchase_invoice_api.frappe.db.commit")
	@patch("logistics.invoice_integration.purchase_invoice_api.frappe.db.set_value")
	@patch("logistics.invoice_integration.purchase_invoice_api.frappe.db.table_exists", return_value=True)
	@patch("logistics.invoice_integration.purchase_invoice_api.frappe.get_meta")
	@patch("logistics.invoice_integration.purchase_invoice_api.frappe.new_doc")
	@patch("logistics.invoice_integration.purchase_invoice_api.frappe.get_doc")
	@patch("logistics.invoice_integration.purchase_invoice_api.frappe.db.exists", return_value=True)
	@patch(
		"logistics.invoice_integration.purchase_invoice_api._purchase_invoice_naming_context",
		return_value={
			"autoname": "naming_series:",
			"needs_purchase_invoice_name": False,
			"naming_series_options": [],
			"default_naming_series": None,
			"show_naming_series": False,
		},
	)
	@patch(
		"logistics.invoice_integration.purchase_invoice_api.invoice_billing_context",
		return_value={"company_currency": "PHP", "billing_currency": "PHP", "billing_exchange_rate": 1},
	)
	@patch("logistics.invoice_integration.purchase_invoice_api.charge_to_company_rate_buying", return_value=1)
	def test_item_uses_linked_service_profit_center(
		self,
		_mock_chr,
		_mock_bctx,
		_mock_naming,
		_mock_exists,
		mock_get_doc,
		mock_new_doc,
		mock_get_meta,
		_mock_tbl,
		_mock_sv,
		_mock_commit,
		_mock_ref,
	):
		job = self._mock_job()
		mock_get_doc.return_value = job

		pi = MagicMock()
		pi.items = []
		pi.remarks = ""
		pi.doctype = "Purchase Invoice"
		pi.append = lambda field, row: pi.items.append(frappe._dict(row))
		mock_new_doc.return_value = pi

		meta = MagicMock()

		def get_field(fieldname):
			if fieldname == "profit_center":
				return object()
			return None

		meta.get_field.side_effect = get_field
		mock_get_meta.return_value = meta

		with (
			patch(
				"logistics.utils.service_role_rules.is_linked_service_satellite",
				return_value=True,
			),
			patch(
				"logistics.utils.service_role_rules.get_linked_service_name",
				return_value="LS-FPT",
			),
			patch(
				"logistics.utils.linked_service_compat.linked_service_doctype",
				return_value="Linked Service",
			),
			patch(
				"logistics.utils.linked_service_company.accounting_dimensions_from_linked_service",
				return_value={"profit_center": LINKED_PC},
			),
			patch(
				"logistics.invoice_integration.purchase_invoice_dimensions.dimension_belongs",
				side_effect=_belongs_to_fast_prime,
			),
		):
			result = create_purchase_invoice(
				job_type="Transport Job",
				job_name="TRJ000000016",
				supplier="FAST",
				posting_date="2026-10-12",
				selected_charge_indices=json.dumps([0]),
			)

		self.assertTrue(result["ok"])
		self.assertEqual(pi.profit_center, LINKED_PC)
		self.assertEqual(pi.items[0].profit_center, LINKED_PC)
		self.assertNotEqual(pi.items[0].profit_center, MAIN_PC)


MAIN_COMPANY = "ALL TRANSPORT"
LINKED_BRANCH = "PNS - FPT"
LINKED_CC = "Main - FPT"
MAIN_BRANCH = "ATN-BR"
MAIN_CC = "ATN-CC"


def _belongs_to_either_party(fieldname, value, company):
	"""Both profit centers pass the company check, as when the master is not company-scoped."""
	if company == FAST_PRIME and value in (LINKED_PC, MAIN_PC, LINKED_BRANCH, LINKED_CC):
		return True
	if company == MAIN_COMPANY and value in (MAIN_PC, LINKED_PC, MAIN_BRANCH, MAIN_CC):
		return True
	return False


class TestIntercompanyInvoiceDimensions(UnitTestCase):
	def _linked_service_record(self):
		return frappe._dict(
			company=FAST_PRIME,
			branch=LINKED_BRANCH,
			cost_center=LINKED_CC,
			profit_center=LINKED_PC,
		)

	def test_sales_invoice_follows_linked_service_record(self):
		job = frappe._dict(
			doctype="Transport Job",
			name="TRJ-LINKED",
			company=FAST_PRIME,
			linked_service="LS-FPT",
			branch=MAIN_BRANCH,
			cost_center=MAIN_CC,
			profit_center=MAIN_PC,
		)
		with (
			patch(
				"logistics.utils.linked_service_compat.linked_service_record_exists",
				return_value=True,
			),
			patch(
				"logistics.utils.linked_service_compat.linked_service_doctype",
				return_value="Linked Service",
			),
			patch(
				"logistics.invoice_integration.purchase_invoice_dimensions.frappe.get_cached_doc",
				return_value=self._linked_service_record(),
			),
			patch(
				"logistics.invoice_integration.purchase_invoice_dimensions.dimension_belongs",
				side_effect=_belongs_to_either_party,
			),
		):
			dims = intercompany_sales_invoice_dimensions(job, MAIN_COMPANY)

		self.assertEqual(dims.get("company"), FAST_PRIME)
		self.assertEqual(dims.get("branch"), LINKED_BRANCH)
		self.assertEqual(dims.get("cost_center"), LINKED_CC)
		self.assertEqual(dims.get("profit_center"), LINKED_PC)
		self.assertNotEqual(dims.get("profit_center"), MAIN_PC)
		self.assertNotEqual(dims.get("branch"), MAIN_BRANCH)
		self.assertNotEqual(dims.get("cost_center"), MAIN_CC)

	def test_sales_invoice_ignores_job_copy_when_linked_service_is_missing(self):
		job = frappe._dict(
			doctype="Warehouse Job",
			name="WJ-1",
			company=FAST_PRIME,
			branch=MAIN_BRANCH,
			cost_center=MAIN_CC,
			profit_center=MAIN_PC,
		)
		with patch(
			"logistics.invoice_integration.purchase_invoice_dimensions.dimension_belongs",
			side_effect=_belongs_to_either_party,
		):
			dims = intercompany_sales_invoice_dimensions(job, FAST_PRIME)

		self.assertEqual(dims.get("company"), FAST_PRIME)
		self.assertNotIn("branch", dims)
		self.assertNotIn("cost_center", dims)
		self.assertNotIn("profit_center", dims)

	def test_sales_invoice_uses_parent_booking_linked_service(self):
		job = frappe._dict(
			doctype="Transport Job",
			name="TRJ-PARENT",
			company=MAIN_COMPANY,
			transport_order="TO-1",
			profit_center=MAIN_PC,
		)
		parent = frappe._dict(doctype="Transport Order", name="TO-1", linked_service="LS-FPT")
		with (
			patch(
				"logistics.invoice_integration.purchase_invoice_dimensions._parent_booking_doc",
				return_value=parent,
			),
			patch(
				"logistics.utils.linked_service_compat.linked_service_record_exists",
				return_value=True,
			),
			patch(
				"logistics.utils.linked_service_compat.linked_service_doctype",
				return_value="Linked Service",
			),
			patch(
				"logistics.invoice_integration.purchase_invoice_dimensions.frappe.get_cached_doc",
				return_value=self._linked_service_record(),
			),
			patch(
				"logistics.invoice_integration.purchase_invoice_dimensions.dimension_belongs",
				side_effect=_belongs_to_either_party,
			),
		):
			dims = intercompany_sales_invoice_dimensions(job, MAIN_COMPANY)

		self.assertEqual(dims.get("company"), FAST_PRIME)
		self.assertEqual(dims.get("profit_center"), LINKED_PC)
		self.assertEqual(dims.get("branch"), LINKED_BRANCH)
		self.assertEqual(dims.get("cost_center"), LINKED_CC)

	def test_sales_invoice_uses_charge_row_linked_service(self):
		job = frappe._dict(
			doctype="Warehouse Job",
			name="WJ-CHARGE",
			company=FAST_PRIME,
			charges=[frappe._dict(linked_service="LS-FPT")],
			profit_center=MAIN_PC,
		)
		with (
			patch(
				"logistics.utils.linked_service_compat.linked_service_record_exists",
				return_value=True,
			),
			patch(
				"logistics.utils.linked_service_compat.linked_service_doctype",
				return_value="Linked Service",
			),
			patch(
				"logistics.invoice_integration.purchase_invoice_dimensions.frappe.get_cached_doc",
				return_value=self._linked_service_record(),
			),
			patch(
				"logistics.invoice_integration.purchase_invoice_dimensions.dimension_belongs",
				side_effect=_belongs_to_either_party,
			),
		):
			dims = intercompany_sales_invoice_dimensions(job, FAST_PRIME)

		self.assertEqual(dims.get("profit_center"), LINKED_PC)
		self.assertEqual(dims.get("branch"), LINKED_BRANCH)
		self.assertEqual(dims.get("cost_center"), LINKED_CC)

	def test_purchase_invoice_follows_main_only(self):
		main = frappe._dict(
			doctype="Air Shipment",
			name="AS-MAIN",
			company=MAIN_COMPANY,
			branch=MAIN_BRANCH,
			cost_center=MAIN_CC,
			profit_center=MAIN_PC,
		)
		with patch(
			"logistics.invoice_integration.purchase_invoice_dimensions.dimension_belongs",
			side_effect=_belongs_to_either_party,
		):
			dims = intercompany_purchase_invoice_dimensions(main, FAST_PRIME)

		self.assertEqual(dims.get("company"), MAIN_COMPANY)
		self.assertEqual(dims.get("branch"), MAIN_BRANCH)
		self.assertEqual(dims.get("cost_center"), MAIN_CC)
		self.assertEqual(dims.get("profit_center"), MAIN_PC)
		self.assertNotEqual(dims.get("profit_center"), LINKED_PC)

	def test_purchase_invoice_does_not_substitute_another_profit_center(self):
		main = frappe._dict(
			doctype="Air Shipment",
			name="AS-MAIN",
			company=MAIN_COMPANY,
			profit_center=MAIN_PC,
		)
		with patch(
			"logistics.invoice_integration.purchase_invoice_dimensions.dimension_belongs",
			return_value=False,
		):
			dims = intercompany_purchase_invoice_dimensions(main, MAIN_COMPANY)

		self.assertEqual(dims.get("company"), MAIN_COMPANY)
		self.assertNotIn("profit_center", dims)

	def test_align_sales_invoice_replaces_main_dimensions(self):
		doc = frappe._dict(
			doctype="Sales Invoice",
			company=FAST_PRIME,
			branch=MAIN_BRANCH,
			cost_center=MAIN_CC,
			profit_center=MAIN_PC,
			items=[frappe._dict(doctype="Sales Invoice Item", profit_center=MAIN_PC, branch=MAIN_BRANCH)],
			taxes=[],
			flags=frappe._dict(is_intercompany_invoice=True),
			reference_doctype="Transport Job",
			reference_name="TRJ-LINKED",
		)
		job = frappe._dict(
			doctype="Transport Job",
			name="TRJ-LINKED",
			company=FAST_PRIME,
			linked_service="LS-FPT",
			profit_center=MAIN_PC,
			branch=MAIN_BRANCH,
			cost_center=MAIN_CC,
		)
		with (
			patch(
				"logistics.invoice_integration.purchase_invoice_dimensions.frappe.get_meta",
				return_value=TestAlignInvoiceDimensions()._meta(),
			),
			patch(
				"logistics.invoice_integration.purchase_invoice_dimensions.dimension_belongs",
				side_effect=_belongs_to_either_party,
			),
			patch(
				"logistics.invoice_integration.purchase_invoice_dimensions.frappe.db.exists",
				return_value=True,
			),
			patch(
				"logistics.invoice_integration.purchase_invoice_dimensions.frappe.get_doc",
				return_value=job,
			),
			patch(
				"logistics.utils.linked_service_compat.linked_service_record_exists",
				return_value=True,
			),
			patch(
				"logistics.utils.linked_service_compat.linked_service_doctype",
				return_value="Linked Service",
			),
			patch(
				"logistics.invoice_integration.purchase_invoice_dimensions.frappe.get_cached_doc",
				return_value=self._linked_service_record(),
			),
		):
			align_invoice_dimensions_to_company(doc)

		self.assertEqual(doc.company, FAST_PRIME)
		self.assertEqual(doc.branch, LINKED_BRANCH)
		self.assertEqual(doc.cost_center, LINKED_CC)
		self.assertEqual(doc.profit_center, LINKED_PC)
		self.assertEqual(doc["items"][0].profit_center, LINKED_PC)
		self.assertEqual(doc["items"][0].branch, LINKED_BRANCH)

	def test_align_purchase_invoice_replaces_linked_service_dimensions(self):
		doc = frappe._dict(
			doctype="Purchase Invoice",
			company=MAIN_COMPANY,
			branch=LINKED_BRANCH,
			cost_center=LINKED_CC,
			profit_center=LINKED_PC,
			items=[frappe._dict(doctype="Purchase Invoice Item", profit_center=LINKED_PC)],
			taxes=[],
			flags=frappe._dict(is_intercompany_invoice=True),
			reference_doctype="Transport Job",
			reference_name="TRJ-LINKED",
		)
		job = frappe._dict(
			doctype="Transport Job",
			name="TRJ-LINKED",
			company=FAST_PRIME,
			linked_service="LS-FPT",
			main_service_type="Air Shipment",
			main_service="AS-MAIN",
			profit_center=LINKED_PC,
		)
		main = frappe._dict(
			doctype="Air Shipment",
			name="AS-MAIN",
			company=MAIN_COMPANY,
			branch=MAIN_BRANCH,
			cost_center=MAIN_CC,
			profit_center=MAIN_PC,
		)

		def get_doc(doctype, name):
			if doctype == "Transport Job":
				return job
			return main

		with (
			patch(
				"logistics.invoice_integration.purchase_invoice_dimensions.frappe.get_meta",
				return_value=TestAlignInvoiceDimensions()._meta(),
			),
			patch(
				"logistics.invoice_integration.purchase_invoice_dimensions.dimension_belongs",
				side_effect=_belongs_to_either_party,
			),
			patch(
				"logistics.invoice_integration.purchase_invoice_dimensions.frappe.db.exists",
				return_value=True,
			),
			patch(
				"logistics.invoice_integration.purchase_invoice_dimensions.frappe.get_doc",
				side_effect=get_doc,
			),
			patch(
				"logistics.billing.cross_module_billing.resolve_internal_job_main_job",
				return_value=("Air Shipment", "AS-MAIN"),
			),
		):
			align_invoice_dimensions_to_company(doc)

		self.assertEqual(doc.company, MAIN_COMPANY)
		self.assertEqual(doc.branch, MAIN_BRANCH)
		self.assertEqual(doc.cost_center, MAIN_CC)
		self.assertEqual(doc.profit_center, MAIN_PC)
		self.assertEqual(doc["items"][0].profit_center, MAIN_PC)
		self.assertNotEqual(doc.profit_center, LINKED_PC)
