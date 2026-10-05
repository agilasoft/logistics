# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from logistics.invoice_integration.sales_invoice_api import ensure_invoice_name_for_server_insert


class TestEnsureInvoiceNameForServerInsert(UnitTestCase):
	def test_prompt_uses_naming_series_when_no_rule_matches(self):
		doc = frappe._dict(doctype="Sales Invoice", name=None, naming_series=None)
		meta = frappe._dict(autoname="prompt")

		def _assign(series_doc):
			series_doc.name = "ACC-SINV-2026-00001"

		with patch("frappe.get_meta", return_value=meta), patch(
			"frappe.model.naming.set_naming_from_document_naming_rule"
		), patch(
			"logistics.invoice_integration.sales_invoice_api.get_default_naming_series",
			return_value="ACC-SINV-.YYYY.-",
		), patch(
			"logistics.invoice_integration.sales_invoice_api.set_name_by_naming_series",
			side_effect=_assign,
		) as series:
			ensure_invoice_name_for_server_insert(doc)

		series.assert_called_once_with(doc)
		self.assertEqual(doc.name, "ACC-SINV-2026-00001")

	def test_prompt_keeps_document_naming_rule_name(self):
		doc = frappe._dict(doctype="Purchase Invoice", name=None, naming_series=None)
		meta = frappe._dict(autoname="prompt")

		def _apply_rule(rule_doc):
			rule_doc.name = "ATN-PPA-APV-0000000024"

		with patch("frappe.get_meta", return_value=meta), patch(
			"frappe.model.naming.set_naming_from_document_naming_rule",
			side_effect=_apply_rule,
		), patch(
			"logistics.invoice_integration.sales_invoice_api.set_name_by_naming_series"
		) as series:
			ensure_invoice_name_for_server_insert(doc)

		series.assert_not_called()
		self.assertEqual(doc.name, "ATN-PPA-APV-0000000024")

	def test_naming_series_autoname_is_left_for_insert(self):
		doc = frappe._dict(doctype="Sales Invoice", name=None, naming_series="ACC-SINV-.YYYY.-")
		meta = frappe._dict(autoname="naming_series:")

		with patch("frappe.get_meta", return_value=meta), patch(
			"logistics.invoice_integration.sales_invoice_api.set_name_by_naming_series"
		) as series:
			ensure_invoice_name_for_server_insert(doc)

		series.assert_not_called()
		self.assertIsNone(doc.name)

	def test_prompt_without_series_uses_hash(self):
		doc = frappe._dict(doctype="Sales Invoice", name=None, naming_series=None)
		meta = frappe._dict(autoname="prompt")

		with patch("frappe.get_meta", return_value=meta), patch(
			"frappe.model.naming.set_naming_from_document_naming_rule"
		), patch(
			"logistics.invoice_integration.sales_invoice_api.get_default_naming_series",
			return_value=None,
		), patch(
			"logistics.invoice_integration.sales_invoice_api.make_autoname",
			return_value="ab12cd34ef",
		) as hashed:
			ensure_invoice_name_for_server_insert(doc)

		hashed.assert_called_once_with("hash", "Sales Invoice")
		self.assertEqual(doc.name, "ab12cd34ef")
