"""Vector BDO Bank Cheque PDF for Payment Entry Bank Cheque print format."""

from __future__ import annotations

import base64
import os
import shutil
from typing import Any

import frappe

from logistics.print_format.payment_entry.bank_forms_pdf import (
	_doc_value,
	_fill_pdf_widgets,
	_template_has_widgets,
)

PRINT_FORMAT_NAME = "Bank Cheque"
CHEQUE_PRINT_FORMATS = {PRINT_FORMAT_NAME}
DOC_TYPE = "Payment Entry"

# AcroForm field names on bdo_cheque_source.pdf
WIDGET_DATE = "Textbox1"
WIDGET_AMOUNT_FIGURES = "Textbox2"
WIDGET_PAYEE = "Textbox3"
WIDGET_AMOUNT_WORDS = "Textbox4"

APP_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
IMAGES_DIR = os.path.join(APP_ROOT, "logistics", "public", "images")
TEMPLATE_PDF = os.path.join(IMAGES_DIR, "bdo_cheque_source.pdf")
SOURCE_CANDIDATES = [
	TEMPLATE_PDF,
	"/home/kitler/Documents/ATN Print Format/BDO Cheque.pdf",
	os.path.join(IMAGES_DIR, "BDO Cheque.pdf"),
]
FONT_SIZE = 8


def _install_instructions() -> str:
	return (
		"Install the original BDO Bank Cheque PDF (vector, with form fields):\n"
		f"  scp \"BDO Cheque.pdf\" frappe@<server>:{TEMPLATE_PDF}\n"
		"Then run:\n"
		"  bench --site <site> execute "
		"logistics.print_format.payment_entry.bank_cheque_pdf.install_cheque_template_pdf"
	)


def _find_pdf(pdf_path: str | None = None) -> str:
	if pdf_path and os.path.isfile(pdf_path):
		return pdf_path
	if os.path.isfile(TEMPLATE_PDF):
		return TEMPLATE_PDF
	for candidate in SOURCE_CANDIDATES[1:]:
		if os.path.isfile(candidate):
			return candidate
	frappe.throw("BDO cheque PDF template not found.\n" f"{_install_instructions()}")


def _field_values(doc) -> dict[str, Any]:
	currency = (
		_doc_value(doc, "paid_from_account_currency")
		or _doc_value(doc, "paid_to_account_currency")
		or _doc_value(doc, "company_currency")
		or "PHP"
	)
	payment_type = _doc_value(doc, "payment_type")
	payment_amount = _doc_value(doc, "paid_amount", 0) if payment_type == "Pay" else (
		_doc_value(doc, "received_amount", 0) or _doc_value(doc, "paid_amount", 0) or 0
	)
	cheque_date = _doc_value(doc, "cheque_date") or _doc_value(doc, "posting_date")

	return {
		"payee_name": _doc_value(doc, "party_name") or _doc_value(doc, "party"),
		"cheque_date": frappe.utils.formatdate(cheque_date, "MM dd yyyy") if cheque_date else "",
		"amount_words": frappe.utils.money_in_words(payment_amount, currency) if payment_amount else "",
		"amount_figures": frappe.utils.fmt_money(payment_amount, precision=2) if payment_amount else "",
	}


def _pdf_form_data(values: dict[str, Any]) -> dict[str, str]:
	data = {
		WIDGET_DATE: values.get("cheque_date"),
		WIDGET_PAYEE: values.get("payee_name"),
		WIDGET_AMOUNT_FIGURES: values.get("amount_figures"),
		WIDGET_AMOUNT_WORDS: values.get("amount_words"),
	}
	return {key: str(value) for key, value in data.items() if value}


def _build_pdf_from_form(doc, pdf_path: str | None = None) -> bytes:
	import fitz

	source = _find_pdf(pdf_path)
	values = _field_values(doc)
	template = fitz.open(source)
	page = template[0]
	_fill_pdf_widgets(page, _pdf_form_data(values))
	return template.tobytes(garbage=4, deflate=True)


def _build_blank_pdf_from_widgets(doc, pdf_path: str | None = None) -> bytes:
	"""Render only filled values on a white page (for pre-printed cheque stock)."""
	import fitz

	source = _find_pdf(pdf_path)
	values = _field_values(doc)
	form_data = _pdf_form_data(values)

	template = fitz.open(source)
	src_page = template[0]
	page_rect = src_page.rect

	output = fitz.open()
	page = output.new_page(width=page_rect.width, height=page_rect.height)

	for widget in src_page.widgets() or []:
		text = form_data.get(widget.field_name)
		if not text:
			continue
		rect = widget.rect
		baseline_y = rect.y1 - 1.2
		fontname = "hebo" if widget.field_name in (WIDGET_DATE, WIDGET_PAYEE, WIDGET_AMOUNT_FIGURES) else "helv"
		page.insert_text(
			(rect.x0, baseline_y),
			text,
			fontname=fontname,
			fontsize=FONT_SIZE,
			color=(0, 0, 0),
		)

	template.close()
	return output.tobytes(garbage=4, deflate=True)


def build_blank_pdf(doc, pdf_path: str | None = None) -> bytes:
	source = _find_pdf(pdf_path)
	if _template_has_widgets(source):
		return _build_blank_pdf_from_widgets(doc, pdf_path)
	frappe.throw("BDO cheque template has no form fields.\n" f"{_install_instructions()}")


def build_pdf(doc, pdf_path: str | None = None) -> bytes:
	source = _find_pdf(pdf_path)
	if _template_has_widgets(source):
		return _build_pdf_from_form(doc, pdf_path)
	frappe.throw("BDO cheque template has no form fields.\n" f"{_install_instructions()}")


@frappe.whitelist()
def install_cheque_template_pdf(source_path: str | None = None) -> dict:
	source = source_path
	if not source:
		for candidate in SOURCE_CANDIDATES[1:]:
			if os.path.isfile(candidate):
				source = candidate
				break
	if not source or not os.path.isfile(source):
		source = TEMPLATE_PDF if os.path.isfile(TEMPLATE_PDF) else None
	if not source or not os.path.isfile(source):
		frappe.throw("BDO cheque template PDF not found.\n" f"{_install_instructions()}")

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
