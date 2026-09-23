# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

import frappe
from frappe.tests import UnitTestCase
from frappe.utils import today

from logistics.air_freight.casslink.awb import format_awb_display, normalize_awb
from logistics.air_freight.casslink.invoice import group_lines_for_invoice
from logistics.air_freight.casslink.matcher import find_airline, find_mawb
from logistics.air_freight.casslink.parser import (
	parse_csv_text,
	parse_file,
	parse_hot_text,
	parse_spreadsheet_rows,
	unwrap_cass_payload,
)
from logistics.air_freight.casslink.pdf_parser import parse_pdf_text
from logistics.air_freight.iata_cargo_xml.integrations.cass_client import submit_cass_settlement
from logistics.air_freight.tests.test_helpers import create_test_airline, create_test_company


class TestCASSLinkParser(UnitTestCase):
	def test_normalize_awb(self):
		self.assertEqual(normalize_awb("180-00000123"), "18000000123")
		self.assertEqual(normalize_awb("00000123", "180"), "18000000123")
		self.assertEqual(format_awb_display("18000000123"), "180-00000123")

	def test_parse_hot_awb_record(self):
		# Record ID 3 | Agent 11 | Prefix 3 | Serial 8 | Currency 3 | Amount 12 (implied 2 decimals)
		hot = "\n".join(
			[
				"ALAPH8147158",
				"AWB8147158007218000000123USD000000125000",
				"ZZZunknown",
			]
		)
		result = parse_hot_text(hot)
		self.assertEqual(result["skipped"], 2)
		self.assertEqual(len(result["lines"]), 1)
		line = result["lines"][0]
		self.assertEqual(line["awb_number"], "18000000123")
		self.assertEqual(line["airline_prefix"], "180")
		self.assertEqual(line["agent_code"], "81471580072")
		self.assertEqual(line["currency"], "USD")
		self.assertEqual(line["amount"], 1250.00)

	def test_parse_spreadsheet_rows(self):
		rows = [
			["AWB", "Prefix", "Amount", "Currency", "Invoice"],
			["180-00000123", "180", "99.50", "USD", "INV-9"],
		]
		result = parse_spreadsheet_rows(rows)
		self.assertEqual(len(result["lines"]), 1)
		line = result["lines"][0]
		self.assertEqual(line["awb_number"], "18000000123")
		self.assertEqual(line["amount"], 99.5)
		self.assertEqual(line["billing_reference"], "INV-9")

	def test_parse_csv_text(self):
		csv_text = "awb_number,amount,currency\n18000000123,10,USD\n"
		result = parse_csv_text(csv_text)
		self.assertEqual(len(result["lines"]), 1)
		self.assertEqual(result["lines"][0]["awb_number"], "18000000123")

	def test_unwrap_zip_prefers_hot_over_pdf(self):
		import io
		import zipfile

		hot = "AWB8147158007218000000123USD000000125000\n"
		buf = io.BytesIO()
		with zipfile.ZipFile(buf, "w") as zf:
			zf.writestr("statement.pdf", b"%PDF-fake")
			zf.writestr("period.hot", hot.encode("utf-8"))
		inner, name = unwrap_cass_payload(buf.getvalue(), "period.zip")
		self.assertEqual(name, "period.hot")
		self.assertIn(b"AWB", inner)

	def test_unwrap_leaves_xlsx_intact(self):
		import io
		import zipfile

		buf = io.BytesIO()
		with zipfile.ZipFile(buf, "w") as zf:
			zf.writestr("[Content_Types].xml", b"<Types/>")
			zf.writestr("xl/workbook.xml", b"<workbook/>")
		payload = buf.getvalue()
		inner, name = unwrap_cass_payload(payload, "statement.xlsx")
		self.assertEqual(name, "statement.xlsx")
		self.assertEqual(inner, payload)

	def test_parse_pdf_invoice_text(self):
		text = """
CASSLink Cargo Sales Invoice/Adjustment
Currency: USD
IATA Code: 81471580072
Invoice No: INV-9

AWB Number     Orig Dest   Net Payable
180-00000123   MNL  SIN    1,250.00
160-00000999   MNL  NRT       99.50

Recapitulation
Total                          1,349.50
"""
		result = parse_pdf_text(text, filename="2830124-0004_202614_Cargo Sales Report.pdf")
		self.assertEqual(len(result["lines"]), 2)
		self.assertEqual(result["lines"][0]["awb_number"], "18000000123")
		self.assertEqual(result["lines"][0]["amount"], 1250.0)
		self.assertEqual(result["lines"][0]["currency"], "USD")
		self.assertEqual(result["lines"][0]["agent_code"], "81471580072")
		self.assertEqual(result["lines"][1]["awb_number"], "16000000999")
		self.assertEqual(result["lines"][1]["amount"], 99.5)

	def test_parse_pdf_export_billing_statement(self):
		text = """
EXPORT BILLING STATEMENT - AGENT
CURRENCY: USD
DL UA QR
006 016 157
PX-006-111111 PX-016-222222 PX-157-333333
100.00 200.50 50.00- DUE AIRLINE
"""
		result = parse_pdf_text(text)
		self.assertEqual(len(result["lines"]), 3)
		self.assertEqual(result["lines"][0]["airline_code"], "DL")
		self.assertEqual(result["lines"][0]["airline_prefix"], "006")
		self.assertEqual(result["lines"][0]["amount"], 100.0)
		self.assertEqual(result["lines"][0]["billing_reference"], "PX-006-111111")
		self.assertEqual(result["lines"][2]["amount"], -50.0)
		self.assertIsNone(result["lines"][0]["awb_number"])

	def test_parse_pdf_joins_split_awb_rows(self):
		text = "180-00000123\nMNL\nSIN\n1,250.00\n160-00000999\n99.50\n"
		result = parse_pdf_text(text)
		self.assertEqual(len(result["lines"]), 2)
		self.assertEqual(result["lines"][0]["amount"], 1250.0)
		self.assertEqual(result["lines"][1]["awb_number"], "16000000999")

	def test_parse_pdf_bytes_roundtrip(self):
		import fitz

		doc = fitz.open()
		page = doc.new_page()
		page.insert_text(
			(50, 50),
			"CASSLink Cargo Sales Invoice\nCurrency: USD\n"
			"180-00000123 MNL SIN 100.00 1,250.00 15/03/26\n"
			"160-00000999 MNL NRT 20.00 99.50 16/03/26\n",
		)
		content = doc.tobytes()
		doc.close()
		result = parse_file(content, filename="cargo-sales.pdf", file_type="PDF")
		self.assertEqual(len(result["lines"]), 2)
		self.assertEqual(result["lines"][0]["amount"], 1250.0)
		self.assertEqual(result["lines"][1]["awb_number"], "16000000999")


class TestCASSLinkInvoiceGrouping(UnitTestCase):
	def test_group_lines_for_invoice(self):
		lines = [
			{"match_status": "Matched", "supplier": "S1", "currency": "USD", "amount": 10},
			{"match_status": "Matched", "supplier": "S1", "currency": "USD", "amount": 5},
			{"match_status": "Matched", "supplier": "S2", "currency": "EUR", "amount": 7},
			{"match_status": "Unmatched", "supplier": "S1", "currency": "USD", "amount": 3},
			{"match_status": "Matched", "supplier": None, "currency": "USD", "amount": 4},
			{
				"match_status": "Matched",
				"supplier": "S1",
				"currency": "USD",
				"amount": 1,
				"purchase_invoice": "PI-1",
			},
		]
		batches, skipped = group_lines_for_invoice(lines)
		self.assertEqual(len(batches[("S1", "USD")]), 2)
		self.assertEqual(len(batches[("S2", "EUR")]), 1)
		reasons = [reason for _line, reason in skipped]
		self.assertEqual(reasons.count("unmatched"), 1)
		self.assertEqual(reasons.count("no_supplier"), 1)
		self.assertEqual(reasons.count("already_invoiced"), 1)


class TestCASSLinkSettingsAndMatch(UnitTestCase):
	def setUp(self):
		create_test_company()
		create_test_airline("TA", "Test Airline")

	def tearDown(self):
		frappe.db.rollback()

	def test_cass_validation_without_ccs_hub(self):
		company = "Test Air Freight Company"
		settings = _get_or_create_iata_settings(company)
		settings.cargo_xml_enabled = 0
		settings.cass_enabled = 1
		settings.cass_participant_code = None
		settings.cass_api_endpoint = None
		with self.assertRaises(frappe.ValidationError):
			settings.save()

	def test_cass_enable_without_api_endpoint(self):
		company = "Test Air Freight Company"
		settings = _get_or_create_iata_settings(company)
		settings.cargo_xml_enabled = 0
		settings.cass_enabled = 1
		settings.cass_participant_code = "81471580072"
		settings.cass_api_endpoint = None
		settings.save()
		self.assertEqual(settings.cass_participant_code, "81471580072")

	def test_find_mawb_by_normalized_awb(self):
		airline = create_test_airline("ZX", "CASS Test Airline")
		prefix = _unused_airline_prefix()
		frappe.db.set_value("Airline", airline, "airline_numeric_code", prefix)
		awb = f"{prefix}-00000123"
		mawb = frappe.get_doc(
			{
				"doctype": "Master Air Waybill",
				"master_awb_no": awb,
				"airline": airline,
				"flight_date": today(),
			}
		)
		mawb.insert()
		found = find_mawb(prefix + "00000123")
		self.assertIsNotNone(found)
		self.assertEqual(found.name, mawb.name)
		self.assertEqual(find_airline(prefix), airline)


def _unused_airline_prefix():
	for n in range(870, 999):
		prefix = f"{n:03d}"
		if not frappe.db.exists("Airline", {"airline_numeric_code": prefix}):
			return prefix
	return "869"


class TestCASSLinkClient(UnitTestCase):
	def test_legacy_submit_cass_settlement_is_retired(self):
		result = submit_cass_settlement(None, None)
		self.assertFalse(result["success"])
		self.assertIn("CASS Settlement Period", result["error"])


def _get_or_create_iata_settings(company):
	if frappe.db.exists("IATA Settings", company):
		return frappe.get_doc("IATA Settings", company)
	doc = frappe.get_doc({"doctype": "IATA Settings", "company": company, "cass_enabled": 0})
	doc.flags.ignore_permissions = True
	doc.insert(ignore_permissions=True)
	return doc
