"""Tests for vector BIR Form 2307 PDF generation."""

from __future__ import annotations

import os
import tempfile
import unittest
from unittest.mock import patch

import fitz

from logistics.print_format.purchase_invoice import bir_2307_pdf


SAMPLE_BIR = {
	"period_from": "2026-01-01",
	"period_to": "2026-03-31",
	"certificate_date": "2026-03-15",
	"payee": {
		"name": "Acme Supplies Inc.",
		"tin": "123-456-789-000",
		"address": "123 Main St, Manila",
		"zip": "1000",
	},
	"payor": {
		"name": "Test Company",
		"tin": "987-654-321-000",
		"address": "456 Business Ave, Makati",
		"zip": "1200",
	},
	"expanded_rows": [
		{
			"nature_of_income": "Professional fees",
			"atc_code": "WI010",
			"month_1": 10000,
			"month_2": 0,
			"month_3": 0,
			"income_payment": 10000,
			"tax_withheld": 1000,
		}
	],
	"business_rows": [],
	"expanded_totals": {
		"month_1": 10000,
		"month_2": 0,
		"month_3": 0,
		"total_income": 10000,
		"total_tax_withheld": 1000,
	},
	"business_totals": {
		"month_1": 0,
		"month_2": 0,
		"month_3": 0,
		"total_income": 0,
		"total_tax_withheld": 0,
	},
	"total_tax_withheld": 1000,
}


class TestBir2307Pdf(unittest.TestCase):
	def setUp(self):
		self._tmpdir = tempfile.TemporaryDirectory()
		self.template_path = os.path.join(self._tmpdir.name, "bir_template.pdf")
		doc = fitz.open()
		page = doc.new_page(width=612, height=936)
		page.insert_text((24, 40), "BIR Form 2307", fontsize=12)
		doc.save(self.template_path)
		doc.close()

	def tearDown(self):
		self._tmpdir.cleanup()

	def test_build_pdf_stamps_payee_and_payor(self):
		class FakeDoc:
			doctype = "Purchase Invoice"
			name = "PI-TEST-001"

		with patch.object(bir_2307_pdf, "_find_pdf", return_value=self.template_path):
			with patch.object(bir_2307_pdf, "_get_bir_context", return_value=SAMPLE_BIR):
				pdf_bytes = bir_2307_pdf.build_pdf(FakeDoc())

		reader = fitz.open(stream=pdf_bytes, filetype="pdf")
		try:
			text = reader[0].get_text()
		finally:
			reader.close()

		self.assertIn("Acme Supplies Inc.", text)
		self.assertIn("Test Company", text)
		self.assertIn("WI010", text)

	def test_ensure_template_pdf_uses_installed_source(self):
		with patch.object(bir_2307_pdf, "_find_pdf", return_value=self.template_path):
			result = bir_2307_pdf.ensure_template_pdf()
		self.assertEqual(result["path"], self.template_path)
		self.assertEqual(result["page_width"], 612.0)
		self.assertEqual(result["page_height"], 936.0)
