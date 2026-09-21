# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import UnitTestCase

from logistics.invoice_integration.job_number_dimension_sync import (
	copy_job_number_from_return_against,
	sync_job_number_dimension_on_sales_invoice_items,
)


class TestCopyJobNumberFromReturnAgainst(UnitTestCase):
	def _credit_note(self, job_number=None, item_job_number=None):
		return frappe._dict(
			doctype="Sales Invoice",
			is_return=1,
			return_against="ASL-MNL-INV-0000000001",
			job_number=job_number,
			items=[
				frappe._dict(
					sales_invoice_item="orig-item-1",
					job_number=item_job_number,
				)
			],
		)

	@patch("logistics.invoice_integration.job_number_dimension_sync.frappe.get_meta")
	@patch("logistics.invoice_integration.job_number_dimension_sync.frappe.db.exists", return_value=True)
	@patch(
		"logistics.invoice_integration.job_number_dimension_sync.frappe.db.get_value",
		return_value="SF000000484",
	)
	@patch("logistics.invoice_integration.job_number_dimension_sync.frappe.get_all")
	@patch(
		"logistics.invoice_integration.job_number_dimension_sync.reference_dimension_row_dict",
		return_value={"job_number": "SF000000484"},
	)
	def test_copies_header_and_item_from_original_invoice(
		self, _mock_dim, mock_get_all, _mock_get_value, _mock_exists, mock_meta
	):
		mock_meta.return_value.get_field.return_value = MagicMock()
		mock_get_all.return_value = [
			frappe._dict(name="orig-item-1", job_number="SF000000484"),
		]
		doc = self._credit_note()
		copy_job_number_from_return_against(doc)
		self.assertEqual(doc.job_number, "SF000000484")
		self.assertEqual(doc.items[0].job_number, "SF000000484")

	@patch("logistics.invoice_integration.job_number_dimension_sync.frappe.get_meta")
	@patch("logistics.invoice_integration.job_number_dimension_sync.frappe.db.exists", return_value=True)
	@patch(
		"logistics.invoice_integration.job_number_dimension_sync.frappe.db.get_value",
		return_value="SF000000484",
	)
	@patch("logistics.invoice_integration.job_number_dimension_sync.frappe.get_all")
	@patch(
		"logistics.invoice_integration.job_number_dimension_sync.reference_dimension_row_dict",
		return_value={"job_number": "SF000000484"},
	)
	def test_does_not_overwrite_existing_job_number(
		self, _mock_dim, mock_get_all, _mock_get_value, _mock_exists, mock_meta
	):
		mock_meta.return_value.get_field.return_value = MagicMock()
		mock_get_all.return_value = [
			frappe._dict(name="orig-item-1", job_number="SF000000484"),
		]
		doc = self._credit_note(job_number="KEEP-ME", item_job_number="KEEP-LINE")
		copy_job_number_from_return_against(doc)
		self.assertEqual(doc.job_number, "KEEP-ME")
		self.assertEqual(doc.items[0].job_number, "KEEP-LINE")

	def test_skips_non_return_invoices(self):
		doc = frappe._dict(
			doctype="Sales Invoice",
			is_return=0,
			return_against="ASL-MNL-INV-0000000001",
			job_number=None,
			items=[],
		)
		copy_job_number_from_return_against(doc)
		self.assertIsNone(doc.job_number)

	@patch(
		"logistics.invoice_integration.job_number_dimension_sync.copy_job_number_from_return_against"
	)
	@patch(
		"logistics.invoice_integration.job_number_dimension_sync._apply_job_number_dimension_on_item"
	)
	def test_si_hook_copies_header_onto_items(self, mock_apply, mock_copy):
		doc = frappe._dict(
			doctype="Sales Invoice",
			docstatus=0,
			job_number="SF000000484",
			items=[frappe._dict(job_number=None)],
		)
		sync_job_number_dimension_on_sales_invoice_items(doc)
		mock_copy.assert_called_once_with(doc)
		mock_apply.assert_called_once()
		self.assertEqual(mock_apply.call_args[0][1], "Sales Invoice Item")
		self.assertEqual(mock_apply.call_args[0][2], "SF000000484")
