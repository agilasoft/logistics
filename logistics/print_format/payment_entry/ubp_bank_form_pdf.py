"""Vector Union Bank Telegraphic Transfer PDF for Payment Entry UBP bank form print formats."""

from __future__ import annotations

import base64
import os
import shutil
from typing import Any

import frappe

from logistics.print_format.payment_entry.bank_forms_pdf import (
	_doc_value,
	_company_address,
	_fill_pdf_widgets,
	_party_address,
	_purpose,
	_set_radio_field,
	_template_has_widgets,
	_widget_matches_radio,
)

PRINT_FORMAT_NAME = "UBP Bank Form"
BLANK_PRINT_FORMAT_NAME = "UBP Form Blank"
UBP_PRINT_FORMATS = {PRINT_FORMAT_NAME, BLANK_PRINT_FORMAT_NAME}
DOC_TYPE = "Payment Entry"

APP_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
IMAGES_DIR = os.path.join(APP_ROOT, "logistics", "public", "images")
TEMPLATE_PDF = os.path.join(IMAGES_DIR, "ubp_telegraphic_transfer_source.pdf")
SOURCE_CANDIDATES = [TEMPLATE_PDF]
FALLBACK_PNG = os.path.join(IMAGES_DIR, "ubp_telegraphic_transfer.png")


def _install_instructions() -> str:
	return (
		"Install the original Union Bank Telegraphic Transfer PDF:\n"
		f"  scp \"UBP Telegraphic Transfer.pdf\" frappe@<server>:{TEMPLATE_PDF}\n"
		"Then run:\n"
		"  bench --site <site> execute "
		"logistics.print_format.payment_entry.ubp_bank_form_pdf.install_ubp_template_pdf"
	)


def _find_pdf(pdf_path: str | None = None) -> str:
	if pdf_path and os.path.isfile(pdf_path):
		return pdf_path
	if os.path.isfile(TEMPLATE_PDF):
		return TEMPLATE_PDF
	frappe.throw("Union Bank PDF template not found.\n" f"{_install_instructions()}")


def _company_contact(company_name: str) -> tuple[str, str]:
	email = phone = ""
	if not company_name:
		return email, phone
	addresses = frappe.get_all(
		"Address",
		filters=[
			["Dynamic Link", "link_doctype", "=", "Company"],
			["Dynamic Link", "link_name", "=", company_name],
		],
		fields=["name"],
		limit=1,
	)
	if addresses:
		addr = frappe.get_doc("Address", addresses[0].name)
		email = addr.email_id or ""
		phone = addr.phone or ""
	if company_name and frappe.db.exists("Company", company_name):
		company_doc = frappe.get_doc("Company", company_name)
		email = email or _doc_value(company_doc, "email")
		phone = phone or _doc_value(company_doc, "phone_no", "", "mobile_no")
	return email, phone


def _field_values(doc) -> dict[str, Any]:
	company_name = _doc_value(doc, "company") or frappe.db.get_single_value("Global Defaults", "default_company") or ""
	company_doc = frappe.get_doc("Company", company_name) if company_name and frappe.db.exists("Company", company_name) else None
	currency = (
		_doc_value(doc, "paid_from_account_currency")
		or _doc_value(doc, "paid_to_account_currency")
		or _doc_value(doc, "company_currency")
		or "PHP"
	)
	payment_amount = _doc_value(doc, "paid_amount", 0) or _doc_value(doc, "received_amount", 0) or 0
	if _doc_value(doc, "references"):
		payment_amount = sum(ref.allocated_amount or 0 for ref in doc.references)

	bank_account = _doc_value(doc, "bank_account")
	party_bank_account = _doc_value(doc, "party_bank_account")
	remitter_bank = (
		frappe.get_doc("Bank Account", bank_account)
		if bank_account and frappe.db.exists("Bank Account", bank_account)
		else None
	)
	beneficiary_bank = (
		frappe.get_doc("Bank Account", party_bank_account)
		if party_bank_account and frappe.db.exists("Bank Account", party_bank_account)
		else None
	)

	party_address_text, _party_country = _party_address(_doc_value(doc, "party_type"), _doc_value(doc, "party"))
	company_email, company_phone = _company_contact(company_name)
	posting_date = _doc_value(doc, "posting_date")

	remitter_account_no = _doc_value(doc, "bank_account_no") or (remitter_bank.get("bank_account_no") if remitter_bank else "") or ""
	if not remitter_account_no:
		paid_from = _doc_value(doc, "paid_from_account")
		if paid_from and frappe.db.exists("Account", paid_from):
			from_account = frappe.get_doc("Account", paid_from)
			remitter_account_no = (
				_doc_value(from_account, "account_number")
				or _doc_value(from_account, "account_name")
				or paid_from
			)

	purpose = _purpose(doc)
	if purpose and len(purpose) > 120:
		purpose = purpose[:117] + "..."

	fx_rate = ""
	if _doc_value(doc, "source_exchange_rate"):
		fx_rate = frappe.utils.fmt_money(_doc_value(doc, "source_exchange_rate"), precision=4)

	return {
		"posting_date": frappe.utils.formatdate(posting_date, "MM-dd-yyyy") if posting_date else "",
		"applicant_name": (company_doc.company_name if company_doc else company_name) or "",
		"company_address_text": _company_address(company_name),
		"company_email": company_email,
		"company_phone": company_phone,
		"currency": currency,
		"currency_other": currency if currency not in ("PHP", "USD") else "",
		"fx_rate": fx_rate,
		"remitter_account_no": remitter_account_no,
		"amount_words": frappe.utils.money_in_words(payment_amount, currency),
		"amount_figures": f"{frappe.utils.fmt_money(payment_amount, precision=2)} {currency}",
		"purpose": purpose,
		"beneficiary_name": _doc_value(doc, "party_name") or _doc_value(doc, "party"),
		"beneficiary_account_no": (beneficiary_bank.get("bank_account_no") if beneficiary_bank else "") or "",
		"party_address_text": party_address_text,
		"beneficiary_bank_name": (beneficiary_bank.get("bank") if beneficiary_bank else _doc_value(doc, "bank")) or "",
		"swift_code": (
			(beneficiary_bank.get("branch_code") or beneficiary_bank.get("iban") or "")
			if beneficiary_bank
			else ""
		),
	}


def _pdf_form_data(values: dict[str, Any]) -> dict[str, str]:
	data = {
		"Date of Application": values.get("posting_date"),
		"Text2": values.get("applicant_name"),
		"Text2_21": values.get("company_address_text"),
		"Text2_31": values.get("company_email"),
		"Text1": values.get("company_phone"),
		"Text2_31_21_12_21_12": values.get("currency_other"),
		"FX Rate": values.get("fx_rate"),
		"Account No": values.get("remitter_account_no"),
		"Text2_31_31": values.get("amount_words"),
		"Amount in Figures": values.get("amount_figures"),
		"Text2_21_21": values.get("purpose"),
		"Text2_31_31_21": values.get("beneficiary_name"),
		"Beneficiary Account No.": values.get("beneficiary_account_no"),
		"Text5": values.get("party_address_text"),
		"Text2_31_21_21_21_21_21": values.get("beneficiary_bank_name"),
		"Text2_31_21_21_21_21_31": values.get("swift_code"),
	}
	return {key: str(value) for key, value in data.items() if value}


def _fill_pdf_radios(page, values: dict[str, Any]) -> None:
	_set_radio_field(page, "RadioButton4", "1")

	currency = values.get("currency")
	if currency == "PHP":
		_set_radio_field(page, "RadioButton2", "0")
	elif currency == "USD":
		_set_radio_field(page, "RadioButton2", "1")
	else:
		_set_radio_field(page, "RadioButton2", "2")

	_set_radio_field(page, "RadioButton1", "3")


def _radio_selections(values: dict[str, Any]) -> dict[str, str]:
	selections = {"RadioButton4": "1", "RadioButton1": "3"}
	currency = values.get("currency")
	if currency == "PHP":
		selections["RadioButton2"] = "0"
	elif currency == "USD":
		selections["RadioButton2"] = "1"
	else:
		selections["RadioButton2"] = "2"
	return selections


def _build_pdf_from_form(doc, pdf_path: str | None = None) -> bytes:
	import fitz

	source = _find_pdf(pdf_path)
	values = _field_values(doc)
	template = fitz.open(source)
	page = template[0]
	_fill_pdf_widgets(page, _pdf_form_data(values))
	_fill_pdf_radios(page, values)
	return template.tobytes(garbage=4, deflate=True)


def _build_blank_pdf_from_widgets(doc, pdf_path: str | None = None) -> bytes:
	import fitz

	source = _find_pdf(pdf_path)
	values = _field_values(doc)
	form_data = _pdf_form_data(values)
	selections = _radio_selections(values)

	template = fitz.open(source)
	src_page = template[0]
	page_rect = src_page.rect

	output = fitz.open()
	page = output.new_page(width=page_rect.width, height=page_rect.height)

	for widget in src_page.widgets() or []:
		if widget.field_type_string == "RadioButton":
			continue
		text = form_data.get(widget.field_name)
		if not text:
			continue
		rect = widget.rect
		baseline_y = rect.y1 - 1.2
		page.insert_text(
			(rect.x0, baseline_y),
			text,
			fontname="helv",
			fontsize=7,
			color=(0, 0, 0),
		)

	for widget in src_page.widgets() or []:
		if widget.field_type_string != "RadioButton":
			continue
		selected = selections.get(widget.field_name)
		if not selected or not _widget_matches_radio(widget, widget.field_name, selected):
			continue
		page.insert_textbox(
			widget.rect,
			"X",
			fontname="hebo",
			fontsize=6,
			color=(0, 0, 0),
			align=fitz.TEXT_ALIGN_CENTER,
		)

	template.close()
	return output.tobytes(garbage=4, deflate=True)


def build_blank_pdf(doc, pdf_path: str | None = None) -> bytes:
	source = _find_pdf(pdf_path)
	if _template_has_widgets(source):
		return _build_blank_pdf_from_widgets(doc, pdf_path)
	frappe.throw("Union Bank template has no form fields.\n" f"{_install_instructions()}")


def build_pdf(doc, pdf_path: str | None = None) -> bytes:
	source = _find_pdf(pdf_path)
	if _template_has_widgets(source):
		return _build_pdf_from_form(doc, pdf_path)
	frappe.throw("Union Bank template has no form fields.\n" f"{_install_instructions()}")


@frappe.whitelist()
def install_ubp_template_pdf(source_path: str | None = None) -> dict:
	source = source_path or (TEMPLATE_PDF if os.path.isfile(TEMPLATE_PDF) else None)
	if not source or not os.path.isfile(source):
		frappe.throw("Union Bank template PDF not found.\n" f"{_install_instructions()}")

	os.makedirs(IMAGES_DIR, exist_ok=True)
	if os.path.abspath(source) != os.path.abspath(TEMPLATE_PDF):
		shutil.copy2(source, TEMPLATE_PDF)

	import fitz

	doc = fitz.open(TEMPLATE_PDF)
	page_rect = doc[0].rect
	widget_count = len(list(doc[0].widgets() or []))
	doc.close()

	return {
		"path": TEMPLATE_PDF,
		"page_width": round(page_rect.width, 2),
		"page_height": round(page_rect.height, 2),
		"widgets": widget_count,
	}


@frappe.whitelist()
def ensure_template_pdf() -> dict:
	path = _find_pdf()
	return {"path": path, "widgets": len(list(__import__("fitz").open(path)[0].widgets() or []))}


@frappe.whitelist()
def get_embedded_pdf(doctype: str, name: str) -> str:
	doc = frappe.get_doc(doctype, name)
	pdf_bytes = build_pdf(doc)
	encoded = base64.b64encode(pdf_bytes).decode("ascii")
	return f"data:application/pdf;base64,{encoded}"


@frappe.whitelist()
def get_embedded_blank_pdf(doctype: str, name: str) -> str:
	doc = frappe.get_doc(doctype, name)
	pdf_bytes = build_blank_pdf(doc)
	encoded = base64.b64encode(pdf_bytes).decode("ascii")
	return f"data:application/pdf;base64,{encoded}"
