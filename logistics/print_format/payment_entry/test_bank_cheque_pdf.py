"""Tests for vector BDO bank cheque PDF generation."""

from __future__ import annotations

import os
import unittest

import fitz

from logistics.print_format.payment_entry import bank_cheque_pdf


class TestBankChequePdf(unittest.TestCase):
	def _fake_doc(self):
		class FakeDoc:
			def __init__(self):
				self.__dict__.update(
					{
						"payment_type": "Pay",
						"party_name": "Acme Trading Corp",
						"party": "Acme Trading Corp",
						"paid_amount": 12500.50,
						"received_amount": None,
						"cheque_date": "2026-07-06",
						"posting_date": "2026-07-06",
						"paid_from_account_currency": "PHP",
						"paid_to_account_currency": "PHP",
						"company_currency": "PHP",
					}
				)

		return FakeDoc()

	def test_build_pdf_fills_widgets(self):
		template = "/home/frappe/frappe-bench/apps/logistics/logistics/public/images/bdo_cheque_source.pdf"
		if not os.path.isfile(template) or not bank_cheque_pdf._template_has_widgets(template):
			self.skipTest("Vector BDO cheque template with form fields not installed")

		pdf_bytes = bank_cheque_pdf.build_pdf(self._fake_doc(), pdf_path=template)
		doc = fitz.open(stream=pdf_bytes, filetype="pdf")
		widgets = {w.field_name: w.field_value for w in doc[0].widgets() or []}
		doc.close()

		self.assertEqual(widgets.get("Textbox1"), "07 06 2026")
		self.assertEqual(widgets.get("Textbox3"), "Acme Trading Corp")
		self.assertIn("12,500.50", widgets.get("Textbox2", ""))
		self.assertIn("Twelve Thousand", widgets.get("Textbox4", ""))

	def test_build_blank_pdf_stamps_text_only(self):
		template = "/home/frappe/frappe-bench/apps/logistics/logistics/public/images/bdo_cheque_source.pdf"
		if not os.path.isfile(template) or not bank_cheque_pdf._template_has_widgets(template):
			self.skipTest("Vector BDO cheque template with form fields not installed")

		pdf_bytes = bank_cheque_pdf.build_blank_pdf(self._fake_doc(), pdf_path=template)
		doc = fitz.open(stream=pdf_bytes, filetype="pdf")
		text = doc[0].get_text()
		doc.close()

		self.assertIn("Acme Trading Corp", text)
		self.assertIn("12,500.50", text)
