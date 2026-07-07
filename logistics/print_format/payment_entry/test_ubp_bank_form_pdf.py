"""Tests for vector Union Bank bank forms PDF generation."""

from __future__ import annotations

import os
import unittest

import fitz

from logistics.print_format.payment_entry import ubp_bank_form_pdf
from logistics.print_format.payment_entry.bank_forms_pdf import _template_has_widgets


class TestUbpBankFormPdf(unittest.TestCase):
	def _fake_doc(self):
		class FakeDoc:
			def __init__(self):
				self.__dict__.update(
					{
						"doctype": "Payment Entry",
						"name": "PE-TEST-UBP",
						"company": None,
						"paid_from_account_currency": "USD",
						"paid_to_account_currency": None,
						"company_currency": "PHP",
						"paid_amount": 2500,
						"received_amount": None,
						"posting_date": "2026-07-06",
						"party_type": None,
						"party": None,
						"party_name": "Test Beneficiary",
						"bank_account": None,
						"bank_account_no": "9876543210",
						"party_bank_account": None,
						"bank": "Union Bank",
						"reference_no": None,
						"reference_date": None,
						"remarks": "Test remittance",
						"references": [],
						"source_exchange_rate": 56.5,
					}
				)

		return FakeDoc()

	def test_build_pdf_fills_pdf_form_fields(self):
		template = "/home/frappe/frappe-bench/apps/logistics/logistics/public/images/ubp_telegraphic_transfer_source.pdf"
		if not os.path.isfile(template) or not _template_has_widgets(template):
			self.skipTest("Union Bank template with form fields not installed")

		pdf_bytes = ubp_bank_form_pdf.build_pdf(self._fake_doc(), pdf_path=template)
		output = fitz.open(stream=pdf_bytes, filetype="pdf")
		fields = {w.field_name: w.field_value for w in output[0].widgets() or [] if w.field_value}
		self.assertEqual(fields.get("Account No"), "9876543210")
		self.assertEqual(fields.get("Amount in Figures"), "2,500.00 USD")
		self.assertEqual(fields.get("Text2_31_31_21"), "Test Beneficiary")
		output.close()

	def test_build_blank_pdf_shows_values_only(self):
		template = "/home/frappe/frappe-bench/apps/logistics/logistics/public/images/ubp_telegraphic_transfer_source.pdf"
		if not os.path.isfile(template) or not _template_has_widgets(template):
			self.skipTest("Union Bank template with form fields not installed")

		pdf_bytes = ubp_bank_form_pdf.build_blank_pdf(self._fake_doc(), pdf_path=template)
		output = fitz.open(stream=pdf_bytes, filetype="pdf")
		page = output[0]
		self.assertEqual(len(page.get_images(full=True)), 0)
		self.assertIn("9876543210", page.get_text())
		self.assertNotIn("APPLICATION FOR TELEGRAPHIC TRANSFER", page.get_text())
		output.close()


if __name__ == "__main__":
	unittest.main()
