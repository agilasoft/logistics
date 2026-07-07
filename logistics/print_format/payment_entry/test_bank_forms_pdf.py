"""Tests for vector BDO bank forms PDF generation."""

from __future__ import annotations

import os
import tempfile
import unittest

import fitz

from logistics.print_format.payment_entry import bank_forms_pdf


class TestBankFormsPdf(unittest.TestCase):
	def setUp(self):
		self._tmpdir = tempfile.TemporaryDirectory()
		self.template_path = os.path.join(self._tmpdir.name, "bdo_template.pdf")
		doc = fitz.open()
		# Match the reference form aspect ratio (791:1024).
		page = doc.new_page(width=595, height=595 * 1024 / 791)
		page.insert_text((24, 40), "BDO Telegraphic Transfer", fontsize=12)
		doc.save(self.template_path)
		doc.close()

	def tearDown(self):
		self._tmpdir.cleanup()

	def test_template_quality_detects_raster_wrap(self):
		raster_path = os.path.join(self._tmpdir.name, "raster_wrap.pdf")
		doc = fitz.open()
		page = doc.new_page(width=595, height=595 * 1024 / 791)
		png = "/home/frappe/frappe-bench/apps/logistics/logistics/public/images/bdo_telegraphic_transfer.png"
		if os.path.isfile(png):
			page.insert_image(page.rect, filename=png)
		else:
			page.insert_text((24, 40), "placeholder", fontsize=12)
		doc.save(raster_path)
		doc.close()
		self.assertEqual(bank_forms_pdf._template_quality(raster_path), "raster")
		self.assertEqual(bank_forms_pdf._template_quality(self.template_path), "vector")

	def test_build_blank_pdf_shows_values_only(self):
		class FakeDoc:
			def __init__(self):
				self.__dict__.update(
					{
						"doctype": "Payment Entry",
						"name": "PE-TEST-001",
						"company": None,
						"paid_from_account_currency": "PHP",
						"paid_to_account_currency": None,
						"company_currency": "PHP",
						"paid_amount": 1500,
						"received_amount": None,
						"posting_date": "2026-07-06",
						"branch": "Makati",
						"party_type": None,
						"party": None,
						"party_name": None,
						"bank_account": None,
						"bank_account_no": "1234567890",
						"party_bank_account": None,
						"bank": "BDO Unibank",
						"reference_no": "REF-001",
						"reference_date": None,
						"remarks": None,
						"references": [],
						"mode_of_payment": "Bank Transfer",
						"custom_cheque_no": "CHK-001",
					}
				)

		template = "/home/frappe/frappe-bench/apps/logistics/logistics/public/images/bdo_telegraphic_transfer_source.pdf"
		if not os.path.isfile(template) or not bank_forms_pdf._template_has_widgets(template):
			self.skipTest("Vector BDO template with form fields not installed")

		pdf_bytes = bank_forms_pdf.build_blank_pdf(FakeDoc(), pdf_path=template)
		output = fitz.open(stream=pdf_bytes, filetype="pdf")
		page = output[0]
		self.assertEqual(len(page.get_images(full=True)), 0)
		self.assertIn("Makati", page.get_text())
		self.assertNotIn("Telegraphic Transfer Application", page.get_text())
		output.close()

	def test_build_pdf_fills_pdf_form_fields(self):
		class FakeDoc:
			def __init__(self):
				self.__dict__.update(
					{
						"doctype": "Payment Entry",
						"name": "PE-TEST-001",
						"company": None,
						"paid_from_account_currency": "PHP",
						"paid_to_account_currency": None,
						"company_currency": "PHP",
						"paid_amount": 1500,
						"received_amount": None,
						"posting_date": "2026-07-06",
						"branch": "Makati",
						"party_type": None,
						"party": None,
						"party_name": None,
						"bank_account": None,
						"bank_account_no": "1234567890",
						"party_bank_account": None,
						"bank": "BDO Unibank",
						"reference_no": "REF-001",
						"reference_date": None,
						"remarks": None,
						"references": [],
						"mode_of_payment": "Bank Transfer",
						"custom_cheque_no": "CHK-001",
					}
				)

		template = "/home/frappe/frappe-bench/apps/logistics/logistics/public/images/bdo_telegraphic_transfer_source.pdf"
		if not os.path.isfile(template) or not bank_forms_pdf._template_has_widgets(template):
			self.skipTest("Vector BDO template with form fields not installed")

		pdf_bytes = bank_forms_pdf.build_pdf(FakeDoc(), pdf_path=template)
		output = fitz.open(stream=pdf_bytes, filetype="pdf")
		fields = {w.field_name: w.field_value for w in output[0].widgets() or [] if w.field_value}
		self.assertEqual(fields.get("Branch"), "Makati")
		self.assertEqual(fields.get("Amount and Currency"), "1,500.00 PHP")
		self.assertEqual(fields.get("Remitters Account No"), "1234567890")
		output.close()

	def test_build_pdf_stamps_text_on_template(self):
		class FakeDoc:
			doctype = "Payment Entry"
			name = "PE-TEST-001"
			company = None
			paid_from_account_currency = "PHP"
			paid_to_account_currency = None
			company_currency = "PHP"
			paid_amount = 1500
			received_amount = None
			posting_date = "2026-07-06"
			branch = "Makati"
			party_type = None
			party = None
			party_name = None
			bank_account = None
			bank_account_no = "1234567890"
			party_bank_account = None
			bank = "BDO Unibank"
			reference_no = "REF-001"
			reference_date = None
			remarks = None
			references = []
			mode_of_payment = "Bank Transfer"
			custom_cheque_no = "CHK-001"

			def __init__(self):
				self.__dict__.update({k: v for k, v in self.__class__.__dict__.items() if not k.startswith("_") and k != "doctype"})
				self.doctype = "Payment Entry"

		pdf_bytes = bank_forms_pdf.build_pdf(FakeDoc(), pdf_path=self.template_path)
		self.assertTrue(pdf_bytes.startswith(b"%PDF"))

		output = fitz.open(stream=pdf_bytes, filetype="pdf")
		text = output[0].get_text()
		self.assertIn("Makati", text)
		self.assertIn("1,500.00 PHP", text)
		self.assertIn("BDO Unibank", text)
		output.close()


if __name__ == "__main__":
	unittest.main()
