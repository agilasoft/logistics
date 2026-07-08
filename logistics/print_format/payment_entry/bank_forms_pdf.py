"""Vector BDO Telegraphic Transfer PDF for Payment Entry Bank Forms print format."""

from __future__ import annotations

import base64
import json
import os
import shutil
from typing import Any

import frappe
from frappe.translate import print_language
from frappe.utils.print_format import validate_print_permission

PRINT_FORMAT_NAME = "Bank Forms"
BLANK_PRINT_FORMAT_NAME = "BDO Form Blank"
LEGACY_PRINT_FORMAT_NAME = "BDO FORM HTML"
LEGACY_BLANK_PRINT_FORMAT_NAME = "BDO FORM BLANK HTML"
BDO_PRINT_FORMATS = {
	PRINT_FORMAT_NAME,
	BLANK_PRINT_FORMAT_NAME,
	LEGACY_PRINT_FORMAT_NAME,
	LEGACY_BLANK_PRINT_FORMAT_NAME,
}
DOC_TYPE = "Payment Entry"

APP_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
IMAGES_DIR = os.path.join(APP_ROOT, "logistics", "public", "images")
TEMPLATE_PDF = os.path.join(IMAGES_DIR, "bdo_telegraphic_transfer_source.pdf")
SOURCE_CANDIDATES = [
	TEMPLATE_PDF,
	"/home/kitler/Documents/ATN Print Format/BDO Telegraphic Transfer.pdf",
	os.path.join(IMAGES_DIR, "BDO Telegraphic Transfer.pdf"),
]
FALLBACK_PNG = os.path.join(IMAGES_DIR, "bdo_telegraphic_transfer.png")
RASTER_BACKUP = os.path.join(IMAGES_DIR, "bdo_telegraphic_transfer_source.raster.pdf")

# Calibrated against the 791×1024 reference layout (percent of page width/height).
REF_WIDTH = 791
REF_HEIGHT = 1024
FONT_SIZE = 7
CHECK_FONT_SIZE = 6

# PDF uses the "fi" ligature in Beneficiary field names.
BENEFICIARY_BANK = "Bene\uFB01ciary Bank"
BENEFICIARY_ACCOUNT = "Bene\uFB01ciary Account No"
BENEFICIARY_NAME = "Bene\uFB01ciary Name"


def _template_quality(pdf_path: str) -> str:
	"""Return 'vector' or 'raster' for a one-page BDO template PDF."""
	import fitz

	doc = fitz.open(pdf_path)
	try:
		page = doc[0]
		image_count = len(page.get_images(full=True))
		text_chars = len(page.get_text().strip())
		drawing_count = len(page.get_drawings())
	finally:
		doc.close()

	# PNG-wrapped PDFs: one full-page image and almost no native text/paths.
	if image_count >= 1 and text_chars < 80 and drawing_count < 20:
		return "raster"
	return "vector"


def _install_instructions() -> str:
	return (
		"Install the original BDO Telegraphic Transfer PDF (vector, not PNG export):\n"
		f"  scp \"BDO Telegraphic Transfer.pdf\" frappe@<server>:{TEMPLATE_PDF}\n"
		"Then run:\n"
		"  bench --site <site> execute "
		"logistics.print_format.payment_entry.bank_forms_pdf.install_bdo_template_pdf"
	)


def _bootstrap_template_from_png() -> str | None:
	"""Build a one-page PDF from the PNG when the vector source PDF is not on disk."""
	if not os.path.isfile(FALLBACK_PNG):
		return None

	import fitz

	os.makedirs(IMAGES_DIR, exist_ok=True)
	page_w = 595.28
	page_h = page_w * REF_HEIGHT / REF_WIDTH

	doc = fitz.open()
	page = doc.new_page(width=page_w, height=page_h)
	page.insert_image(fitz.Rect(0, 0, page_w, page_h), filename=FALLBACK_PNG)
	doc.save(TEMPLATE_PDF, garbage=4, deflate=True)
	doc.close()

	frappe.logger("logistics").warning(
		"BDO bank form: PNG-derived raster template saved to %s. "
		"Replace with the original vector PDF for sharp print quality.",
		TEMPLATE_PDF,
	)
	return TEMPLATE_PDF


def _find_pdf(pdf_path: str | None = None, *, allow_raster_fallback: bool = False) -> str:
	if pdf_path and os.path.isfile(pdf_path):
		return pdf_path
	# Use the installed template when present (vector or explicitly installed raster).
	if os.path.isfile(TEMPLATE_PDF):
		return TEMPLATE_PDF
	for candidate in SOURCE_CANDIDATES[1:]:
		if os.path.isfile(candidate) and _template_quality(candidate) == "vector":
			return candidate
	if allow_raster_fallback:
		for candidate in (RASTER_BACKUP, *SOURCE_CANDIDATES[1:]):
			if os.path.isfile(candidate):
				return candidate
		bootstrapped = _bootstrap_template_from_png()
		if bootstrapped:
			return bootstrapped
	frappe.throw(
		"BDO vector PDF template not found.\n" f"{_install_instructions()}"
	)


def _pct_rect(left: float, top: float, width: float, height: float, page_rect):
	import fitz

	x0 = page_rect.width * left / 100
	y0 = page_rect.height * top / 100
	x1 = page_rect.width * (left + width) / 100
	y1 = page_rect.height * (top + height) / 100
	return fitz.Rect(x0, y0, x1, y1)


def _company_address(company_name: str) -> str:
	if not company_name:
		return ""
	addresses = frappe.get_all(
		"Address",
		filters=[
			["Dynamic Link", "link_doctype", "=", "Company"],
			["Dynamic Link", "link_name", "=", company_name],
		],
		fields=["name"],
		limit=1,
	)
	if not addresses:
		return ""
	addr = frappe.get_doc("Address", addresses[0].name)
	parts = [p for p in (addr.address_line1, addr.address_line2) if p]
	city_line = f"{addr.city or ''}{(', ' + addr.state) if addr.state else ''}{(', ' + addr.country) if addr.country else ''}".strip(
		", "
	)
	if city_line.strip():
		parts.append(city_line.strip())
	return ", ".join(parts)


def _party_address(party_type: str, party: str) -> tuple[str, str]:
	if not party or party_type not in ("Customer", "Supplier"):
		return "", ""
	if not frappe.db.exists(party_type, party):
		return "", ""
	party_doc = frappe.get_doc(party_type, party)
	address_name = _doc_value(party_doc, "customer_primary_address", "", "supplier_primary_address")
	if not address_name or not frappe.db.exists("Address", address_name):
		return "", ""
	addr = frappe.get_doc("Address", address_name)
	parts = [p for p in (addr.address_line1, addr.address_line2) if p]
	city_line = f"{addr.city or ''}{(', ' + addr.state) if addr.state else ''}{(', ' + addr.country) if addr.country else ''}".strip(
		", "
	)
	if city_line.strip():
		parts.append(city_line.strip())
	return ", ".join(parts), addr.country or ""


def _doc_value(doc, fieldname: str, default="", *aliases: str):
	"""Read a field without triggering AttributeError on missing Payment Entry fields."""
	for name in (fieldname, *aliases):
		if hasattr(doc, "__dict__"):
			value = doc.__dict__.get(name)
		else:
			value = getattr(doc, name, None)
		if value not in (None, ""):
			return value
	return default


def _purpose(doc) -> str:
	if doc.references:
		ref_names = [ref.reference_name for ref in doc.references if ref.reference_name]
		if ref_names:
			purpose = "Payment for " + ", ".join(ref_names)
			return purpose[:42] + "..." if len(purpose) > 45 else purpose
	remarks = frappe.utils.strip_html(_doc_value(doc, "remarks")).strip()
	return remarks[:42] + "..." if len(remarks) > 45 else remarks


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

	party_address_text, party_country = _party_address(_doc_value(doc, "party_type"), _doc_value(doc, "party"))
	mode_lower = _doc_value(doc, "mode_of_payment").lower()
	cheque_no = _doc_value(doc, "custom_cheque_no", "", "cheque_no")
	posting_date = _doc_value(doc, "posting_date")
	reference_date = _doc_value(doc, "reference_date")

	return {
		"posting_date": frappe.utils.formatdate(posting_date, "yyyy/MM/dd") if posting_date else "",
		"branch": _doc_value(doc, "branch", "", "custom_branch"),
		"is_domestic": currency == "PHP",
		"is_foreign": currency != "PHP",
		"domestic_usd": currency == "USD",
		"domestic_php": currency == "PHP",
		"beneficiary_bank_name": (beneficiary_bank.get("bank") if beneficiary_bank else _doc_value(doc, "bank")) or "",
		"reference_no": _doc_value(doc, "reference_no") or _doc_value(doc, "name"),
		"remitter_account_no": _doc_value(doc, "bank_account_no") or (remitter_bank.get("bank_account_no") if remitter_bank else "") or "",
		"reference_date": (
			frappe.utils.formatdate(reference_date, "yy/MM/dd")
			if reference_date
			else (frappe.utils.formatdate(posting_date, "yy/MM/dd") if posting_date else "")
		),
		"amount_figures": f"{frappe.utils.fmt_money(payment_amount, precision=2)} {currency}",
		"applicant_name": (company_doc.company_name if company_doc else company_name) or "",
		"company_address_text": _company_address(company_name),
		"company_phone": frappe.db.get_value("Company", company_name, "phone_no") if company_name else "",
		"company_fax": frappe.db.get_value("Company", company_name, "fax") if company_name else "",
		"company_tax_id": (
			(frappe.db.get_value("Company", company_name, "tax_id") or frappe.db.get_value("Company", company_name, "tin") or "")
			if company_name
			else ""
		),
		"ordering_bank": (remitter_bank.get("bank") if remitter_bank else "") or "",
		"swift_code": (
			(beneficiary_bank.get("branch_code") or beneficiary_bank.get("iban") or "")
			if beneficiary_bank
			else ""
		),
		"party_country": party_country,
		"beneficiary_account_no": (beneficiary_bank.get("bank_account_no") if beneficiary_bank else "") or "",
		"beneficiary_name": _doc_value(doc, "party_name") or _doc_value(doc, "party"),
		"party_address_text": party_address_text,
		"purpose": _purpose(doc),
		"cheque_no": cheque_no,
		"is_cash": "cash" in mode_lower,
		"is_check": "cheque" in mode_lower or "check" in mode_lower or bool(cheque_no),
		"is_debit": "bank" in mode_lower or "transfer" in mode_lower or "debit" in mode_lower,
	}


def _split_lines(text: str, count: int = 2, max_len: int = 55) -> list[str]:
	text = (text or "").strip()
	lines: list[str] = []
	remaining = text
	while remaining and len(lines) < count:
		if len(remaining) <= max_len:
			lines.append(remaining)
			remaining = ""
			continue
		cut = remaining.rfind(" ", 0, max_len)
		if cut < max_len // 2:
			cut = max_len
		lines.append(remaining[:cut].strip())
		remaining = remaining[cut:].strip()
	while len(lines) < count:
		lines.append("")
	return lines[:count]


def _template_has_widgets(pdf_path: str) -> bool:
	import fitz

	doc = fitz.open(pdf_path)
	try:
		return bool(list(doc[0].widgets() or []))
	finally:
		doc.close()


def _set_radio_field(page, field_name: str, export_value: str) -> bool:
	for widget in page.widgets() or []:
		if widget.field_name != field_name:
			continue
		states = (widget.button_states() or {}).get("normal", [])
		if export_value in states and export_value != "Off":
			widget.field_value = export_value
			widget.update()
			return True
	return False


def _pdf_form_data(values: dict[str, Any]) -> dict[str, str]:
	company_addr1, company_addr2 = _split_lines(values.get("company_address_text"))
	party_addr1, party_addr2 = _split_lines(values.get("party_address_text"))
	purpose1, purpose2 = _split_lines(values.get("purpose"))
	applicant1, applicant2 = _split_lines(values.get("applicant_name"))

	data = {
		"Date": values.get("posting_date"),
		"Branch": values.get("branch"),
		"Correspondent  Receiving Bank": values.get("beneficiary_bank_name"),
		"Reference No": values.get("reference_no"),
		"Remitters Account No": values.get("remitter_account_no"),
		"Value Date": values.get("reference_date"),
		"Amount and Currency": values.get("amount_figures"),
		"Applicant Name Last Name First Name Middle Name": applicant1,
		"aplnam2": applicant2,
		"Present Address": company_addr1,
		"preadd2": company_addr2,
		"Permanent Address": company_addr1,
		"peradd2": company_addr2,
		"Telephone Nos": values.get("company_phone"),
		"Fax Nos": values.get("company_fax"),
		"Tax ID No": values.get("company_tax_id"),
		"Ordering Bank": values.get("ordering_bank"),
		"Intermediary Bank FWCH No or SWIFT Code": values.get("swift_code"),
		BENEFICIARY_BANK: values.get("beneficiary_bank_name"),
		"Name_2": values.get("beneficiary_bank_name"),
		"Country of Destination": values.get("party_country"),
		BENEFICIARY_ACCOUNT: values.get("beneficiary_account_no"),
		BENEFICIARY_NAME: values.get("beneficiary_name"),
		"bennam2": values.get("beneficiary_name"),
		"Address_3": party_addr1,
		"add3": party_addr2,
		"Remittance Info": purpose1,
		"reminf1": purpose2,
		"Charges for": "SHA",
		"Source of Funds": "Trade / Business",
		"Industry Type": "Trade / Business",
		"Nationality": "Philippines",
		"PurposeReason": values.get("purpose"),
	}

	if values.get("is_debit") and values.get("remitter_account_no"):
		data["DebitAcctNo"] = values.get("remitter_account_no")
	if values.get("is_check") and values.get("cheque_no"):
		data["Sender to Receiver info"] = values.get("cheque_no")

	return {key: str(value) for key, value in data.items() if value}


def _fill_pdf_radios(page, values: dict[str, Any]) -> None:
	if values.get("is_foreign"):
		_set_radio_field(page, "Transfer", "Foreign")
	elif values.get("is_domestic"):
		_set_radio_field(page, "Transfer", "Domestic")
		if values.get("domestic_php"):
			_set_radio_field(page, "Domestic Transfer", "RTGS")
		elif values.get("domestic_usd"):
			_set_radio_field(page, "Domestic Transfer", "PDDTS")

	if values.get("is_cash"):
		_set_radio_field(page, "ModeOfPay", "Cash")
	elif values.get("is_check"):
		_set_radio_field(page, "ModeOfPay", "OnUsCheck")
	elif values.get("is_debit"):
		_set_radio_field(page, "ModeOfPay", "Debit")


def _radio_selections(values: dict[str, Any]) -> dict[str, str]:
	selections: dict[str, str] = {}
	if values.get("is_foreign"):
		selections["Transfer"] = "Foreign"
	elif values.get("is_domestic"):
		selections["Transfer"] = "Domestic"
		if values.get("domestic_php"):
			selections["Domestic Transfer"] = "RTGS"
		elif values.get("domestic_usd"):
			selections["Domestic Transfer"] = "PDDTS"

	if values.get("is_cash"):
		selections["ModeOfPay"] = "Cash"
	elif values.get("is_check"):
		selections["ModeOfPay"] = "OnUsCheck"
	elif values.get("is_debit"):
		selections["ModeOfPay"] = "Debit"
	return selections


def _widget_matches_radio(widget, field_name: str, export_value: str) -> bool:
	if widget.field_name != field_name:
		return False
	states = (widget.button_states() or {}).get("normal", [])
	return export_value in states and export_value != "Off"


def _fill_pdf_widgets(page, form_data: dict[str, str]) -> None:
	widgets = {widget.field_name: widget for widget in (page.widgets() or [])}
	for field_name, value in form_data.items():
		widget = widgets.get(field_name)
		if not widget or widget.field_type_string == "RadioButton":
			continue
		widget.field_value = value
		widget.update()


def _stamp_widget_rects_on_page(
	page,
	widgets,
	form_data: dict[str, str],
	selections: dict[str, str] | None = None,
) -> None:
	"""Stamp values at widget rectangles onto any page (template or blank)."""
	import fitz

	selections = selections or {}
	for widget in widgets:
		if widget.field_type_string == "RadioButton":
			continue
		text = form_data.get(widget.field_name)
		if not text:
			continue
		rect = widget.rect
		if rect.height > 12:
			page.insert_textbox(
				rect,
				text,
				fontname="helv",
				fontsize=FONT_SIZE,
				color=(0, 0, 0),
				align=fitz.TEXT_ALIGN_LEFT,
			)
			continue
		baseline_y = rect.y1 - 1.2
		page.insert_text(
			(rect.x0, baseline_y),
			text,
			fontname="helv",
			fontsize=FONT_SIZE,
			color=(0, 0, 0),
		)

	for widget in widgets:
		if widget.field_type_string != "RadioButton":
			continue
		selected = selections.get(widget.field_name)
		if not selected or not _widget_matches_radio(widget, widget.field_name, selected):
			continue
		page.insert_textbox(
			widget.rect,
			"X",
			fontname="hebo",
			fontsize=CHECK_FONT_SIZE,
			color=(0, 0, 0),
			align=fitz.TEXT_ALIGN_CENTER,
		)


def _stamp_form_values_on_page(page, form_data: dict[str, str], selections: dict[str, str] | None = None) -> None:
	"""Stamp values onto the visual form using widget rectangles.

	AcroForm widgets on the BDO PDF sit on field labels; filling widget.field_value
	renders text at the top of each rect and overlaps labels. Bottom-align text
	within each widget rect so values land in the input boxes below the labels.
	"""
	_stamp_widget_rects_on_page(page, page.widgets() or [], form_data, selections)


def _build_pdf_from_form(doc, pdf_path: str | None = None) -> bytes:
	import fitz

	source = _find_pdf(pdf_path)
	values = _field_values(doc)
	form_data = _pdf_form_data(values)
	selections = _radio_selections(values)
	template = fitz.open(source)
	page = template[0]
	_stamp_form_values_on_page(page, form_data, selections)
	return template.tobytes(garbage=4, deflate=True)


def _overlay_specs(values: dict[str, Any]) -> list[dict[str, Any]]:
	"""Return overlay rectangles and text for the BDO form."""
	specs: list[dict[str, Any]] = []

	def text(left, top, width, height, key=None, bold=False, wrap=False, static=None):
		value = static if static is not None else values.get(key) or ""
		if not value:
			return
		specs.append(
			{
				"type": "text",
				"left": left,
				"top": top,
				"width": width,
				"height": height,
				"text": value,
				"bold": bold,
				"wrap": wrap,
			}
		)

	def check(left, top, width, height, condition):
		if condition:
			specs.append({"type": "check", "left": left, "top": top, "width": width, "height": height})

	text(79.014, 6.543, 18.963, 1.172, "posting_date")
	text(79.014, 10.254, 18.963, 1.172, "branch")
	check(6.068, 11.035, 1.770, 1.367, values["is_domestic"])
	check(11.125, 12.012, 1.770, 1.367, values["is_domestic"] and values["domestic_usd"])
	check(27.560, 12.012, 1.770, 1.367, values["is_domestic"] and values["domestic_php"])
	check(6.068, 13.379, 1.770, 1.367, values["is_foreign"])
	text(7.332, 12.305, 44.248, 1.172, "beneficiary_bank_name", bold=True)
	text(7.332, 14.648, 44.248, 1.172, "reference_no")
	text(7.332, 16.992, 44.248, 1.172, "remitter_account_no", bold=True)
	text(7.332, 21.680, 44.248, 1.172, "reference_date")
	text(7.332, 24.023, 44.248, 1.172, "amount_figures", bold=True)
	text(7.332, 28.613, 44.248, 1.172, "applicant_name", bold=True)
	text(7.332, 33.301, 44.248, 2.344, "company_address_text", wrap=True)
	text(7.332, 37.988, 44.248, 2.344, "company_address_text", wrap=True)
	text(7.332, 42.578, 19.595, 1.172, "company_phone")
	text(29.077, 42.578, 22.124, 1.172, "company_fax")
	text(7.332, 44.922, 19.595, 1.172, "company_tax_id")
	text(7.332, 49.609, 44.248, 1.172, "ordering_bank")
	text(7.332, 58.887, 44.248, 1.172, "swift_code")
	text(11.125, 61.230, 40.455, 1.172, "beneficiary_bank_name", bold=True)
	text(11.125, 63.574, 40.455, 1.172, "party_country")
	text(7.332, 70.508, 44.248, 1.172, "beneficiary_account_no", bold=True)
	text(7.332, 72.852, 44.248, 1.172, "beneficiary_name", bold=True)
	text(7.332, 77.539, 44.248, 2.344, "party_address_text", wrap=True)
	text(7.332, 84.473, 44.248, 2.344, "purpose", wrap=True)
	text(7.332, 86.719, 7.585, 1.172, static="SHA")
	text(7.332, 88.770, 44.248, 1.172, "cheque_no")
	text(52.465, 12.305, 44.248, 1.172, static="Trade / Business")
	text(75.853, 21.680, 20.228, 1.172, static="Philippines")
	text(52.465, 28.516, 44.248, 1.172, "applicant_name")
	check(52.845, 36.328, 1.770, 1.367, values["is_cash"])
	check(52.845, 37.207, 1.770, 1.367, values["is_check"])
	check(52.845, 38.086, 1.770, 1.367, values["is_debit"])
	if values["is_debit"] and values["remitter_account_no"]:
		text(70.164, 38.281, 25.284, 1.172, "remitter_account_no")

	return specs


def _build_pdf_overlay(doc, pdf_path: str | None = None) -> bytes:
	import fitz

	source = _find_pdf(pdf_path)
	values = _field_values(doc)
	specs = _overlay_specs(values)

	template = fitz.open(source)
	page = template[0]
	page_rect = page.rect

	for spec in specs:
		fitz_rect = _pct_rect(spec["left"], spec["top"], spec["width"], spec["height"], page_rect)

		if spec["type"] == "check":
			page.insert_textbox(
				fitz_rect,
				"X",
				fontname="hebo",
				fontsize=CHECK_FONT_SIZE,
				color=(0, 0, 0),
				align=fitz.TEXT_ALIGN_CENTER,
			)
			continue

		fontname = "hebo" if spec.get("bold") else "helv"
		if spec.get("wrap"):
			page.insert_textbox(
				fitz_rect,
				spec["text"],
				fontname=fontname,
				fontsize=FONT_SIZE,
				color=(0, 0, 0),
				align=fitz.TEXT_ALIGN_LEFT,
			)
		else:
			baseline_y = fitz_rect.y1 - 1.2
			page.insert_text(
				(fitz_rect.x0, baseline_y),
				spec["text"],
				fontname=fontname,
				fontsize=FONT_SIZE,
				color=(0, 0, 0),
			)

	return template.tobytes(garbage=4, deflate=True)


def _build_blank_pdf_from_widgets(doc, pdf_path: str | None = None) -> bytes:
	"""Render only filled form values on a white page (for pre-printed BDO forms)."""
	import fitz

	source = _find_pdf(pdf_path)
	values = _field_values(doc)
	form_data = _pdf_form_data(values)
	selections = _radio_selections(values)

	template = fitz.open(source)
	src_page = template[0]
	page_rect = src_page.rect
	widgets = list(src_page.widgets() or [])

	output = fitz.open()
	page = output.new_page(width=page_rect.width, height=page_rect.height)
	_stamp_widget_rects_on_page(page, widgets, form_data, selections)

	template.close()
	return output.tobytes(garbage=4, deflate=True)


def _build_blank_pdf_overlay(doc, pdf_path: str | None = None) -> bytes:
	"""Blank-page fallback when the template has no AcroForm widgets."""
	import fitz

	source = _find_pdf(pdf_path)
	values = _field_values(doc)
	specs = _overlay_specs(values)

	template = fitz.open(source)
	page_rect = template[0].rect
	template.close()

	output = fitz.open()
	page = output.new_page(width=page_rect.width, height=page_rect.height)

	for spec in specs:
		fitz_rect = _pct_rect(spec["left"], spec["top"], spec["width"], spec["height"], page_rect)
		if spec["type"] == "check":
			page.insert_textbox(
				fitz_rect,
				"X",
				fontname="hebo",
				fontsize=CHECK_FONT_SIZE,
				color=(0, 0, 0),
				align=fitz.TEXT_ALIGN_CENTER,
			)
			continue

		fontname = "hebo" if spec.get("bold") else "helv"
		page.insert_textbox(
			fitz_rect,
			spec["text"],
			fontname=fontname,
			fontsize=FONT_SIZE,
			color=(0, 0, 0),
			align=fitz.TEXT_ALIGN_LEFT if spec.get("wrap") else fitz.TEXT_ALIGN_LEFT,
		)

	return output.tobytes(garbage=4, deflate=True)


def build_blank_pdf(doc, pdf_path: str | None = None) -> bytes:
	source = _find_pdf(pdf_path)
	if _template_has_widgets(source):
		return _build_blank_pdf_from_widgets(doc, pdf_path)
	return _build_blank_pdf_overlay(doc, pdf_path)


def build_pdf(doc, pdf_path: str | None = None) -> bytes:
	source = _find_pdf(pdf_path)
	if _template_has_widgets(source):
		return _build_pdf_from_form(doc, pdf_path)
	return _build_pdf_overlay(doc, pdf_path)


@frappe.whitelist()
def install_bdo_template_pdf(source_path: str | None = None, allow_raster: bool = False) -> dict:
	"""Copy a BDO Telegraphic Transfer PDF into the template location."""
	source = source_path
	if not source:
		if allow_raster and os.path.isfile(RASTER_BACKUP):
			source = RASTER_BACKUP
		else:
			for candidate in SOURCE_CANDIDATES[1:]:
				if os.path.isfile(candidate):
					source = candidate
					break
	if not source or not os.path.isfile(source):
		frappe.throw("BDO template PDF not found.\n" f"{_install_instructions()}")

	quality = _template_quality(source)
	if quality != "vector" and not allow_raster:
		frappe.throw(
			"The selected file is not a vector PDF (it looks like a PNG or scan). "
			"Use the original BDO Telegraphic Transfer PDF from your design files, "
			"or pass allow_raster=1 to install a raster fallback.\n"
			f"{_install_instructions()}"
		)

	os.makedirs(IMAGES_DIR, exist_ok=True)
	if os.path.isfile(TEMPLATE_PDF) and _template_quality(TEMPLATE_PDF) == "raster":
		shutil.copy2(TEMPLATE_PDF, RASTER_BACKUP)
	shutil.copy2(source, TEMPLATE_PDF)

	import fitz

	doc = fitz.open(TEMPLATE_PDF)
	page_rect = doc[0].rect
	doc.close()

	return {
		"path": TEMPLATE_PDF,
		"quality": quality,
		"vector": quality == "vector",
		"page_width": round(page_rect.width, 2),
		"page_height": round(page_rect.height, 2),
	}


@frappe.whitelist()
def ensure_template_pdf() -> dict:
	"""Validate that a BDO template PDF is installed."""
	path = _find_pdf()
	quality = _template_quality(path)
	return {"path": path, "quality": quality, "vector": quality == "vector"}


def _pdf_preview_data(pdf_bytes: bytes) -> dict[str, float | str]:
	"""Return a PDF data URI and exact page size for aligned browser PDF preview."""
	import fitz

	doc = fitz.open(stream=pdf_bytes, filetype="pdf")
	page = doc[0]
	rect = page.rect
	width_mm = round(rect.width / 72 * 25.4, 1)
	height_mm = round(rect.height / 72 * 25.4, 1)
	doc.close()
	encoded = base64.b64encode(pdf_bytes).decode("ascii")
	return {
		"src": f"data:application/pdf;base64,{encoded}",
		"width_mm": width_mm,
		"height_mm": height_mm,
	}


@frappe.whitelist()
def get_embedded_pdf(doctype: str, name: str) -> dict[str, float | str]:
	doc = frappe.get_doc(doctype, name)
	return _pdf_preview_data(build_pdf(doc))


@frappe.whitelist()
def get_embedded_blank_pdf(doctype: str, name: str) -> dict[str, float | str]:
	doc = frappe.get_doc(doctype, name)
	return _pdf_preview_data(build_blank_pdf(doc))


def _bank_form_pdf_bytes(print_format: str, doc):
	from logistics.print_format.payment_entry.bank_cheque_pdf import (
		CHEQUE_PRINT_FORMATS,
		build_pdf as build_cheque_pdf,
	)
	from logistics.print_format.payment_entry.ubp_bank_form_pdf import (
		BLANK_PRINT_FORMAT_NAME as UBP_BLANK_PRINT_FORMAT_NAME,
		UBP_PRINT_FORMATS,
		build_blank_pdf as build_ubp_blank_pdf,
		build_pdf as build_ubp_pdf,
	)

	if print_format in CHEQUE_PRINT_FORMATS:
		return build_cheque_pdf(doc)
	if print_format in UBP_PRINT_FORMATS:
		return build_ubp_blank_pdf(doc) if print_format == UBP_BLANK_PRINT_FORMAT_NAME else build_ubp_pdf(doc)
	blank_formats = {BLANK_PRINT_FORMAT_NAME, LEGACY_BLANK_PRINT_FORMAT_NAME}
	return build_blank_pdf(doc) if print_format in blank_formats else build_pdf(doc)


def pdf_generator_hook(print_format, html, options, output, pdf_generator):
	from logistics.print_format.payment_entry.bank_cheque_pdf import CHEQUE_PRINT_FORMATS
	from logistics.print_format.payment_entry.ubp_bank_form_pdf import UBP_PRINT_FORMATS
	from logistics.print_format.purchase_invoice.bir_2307_pdf import BIR_2307_PRINT_FORMATS

	if (
		print_format not in BDO_PRINT_FORMATS
		and print_format not in UBP_PRINT_FORMATS
		and print_format not in CHEQUE_PRINT_FORMATS
		and print_format not in BIR_2307_PRINT_FORMATS
	):
		return None

	doctype = frappe.local.form_dict.doctype
	name = frappe.local.form_dict.name
	doc = frappe.local.form_dict.doc
	if isinstance(doc, str):
		doc = json.loads(doc) if doc else None
	if doc is None:
		doc = frappe.get_doc(doctype, name)
	elif isinstance(doc, dict):
		doc = frappe.get_doc(doc)

	if print_format in BIR_2307_PRINT_FORMATS:
		from logistics.print_format.purchase_invoice.bir_2307_pdf import build_pdf as build_bir_2307_pdf

		pdf_bytes = build_bir_2307_pdf(doc)
	else:
		pdf_bytes = _bank_form_pdf_bytes(print_format, doc)
	if output is not None:
		from io import BytesIO

		from pypdf import PdfReader

		reader = PdfReader(BytesIO(pdf_bytes))
		for page in reader.pages:
			output.add_page(page)
		return output
	return pdf_bytes


@frappe.whitelist(allow_guest=True)
def download_pdf(
	doctype: str,
	name: str,
	format=None,
	doc=None,
	no_letterhead=0,
	language=None,
	letterhead=None,
	pdf_generator=None,
):
	from logistics.print_format.payment_entry.bank_cheque_pdf import CHEQUE_PRINT_FORMATS
	from logistics.print_format.payment_entry.ubp_bank_form_pdf import UBP_PRINT_FORMATS
	from logistics.print_format.purchase_invoice.bir_2307_pdf import (
		BIR_2307_PRINT_FORMATS,
		DOC_TYPE as BIR_2307_DOC_TYPE,
		build_pdf as build_bir_2307_pdf,
	)

	if doctype == DOC_TYPE and format in (BDO_PRINT_FORMATS | UBP_PRINT_FORMATS | CHEQUE_PRINT_FORMATS):
		doc = doc or frappe.get_doc(doctype, name)
		if isinstance(doc, str):
			doc = json.loads(doc)
		if isinstance(doc, dict):
			doc = frappe.get_doc(doc)
		validate_print_permission(doc)

		with print_language(language):
			pdf_file = _bank_form_pdf_bytes(format, doc)

		frappe.local.response.filename = "{name}.pdf".format(name=name.replace(" ", "-").replace("/", "-"))
		frappe.local.response.filecontent = pdf_file
		frappe.local.response.type = "pdf"
		return

	if doctype == BIR_2307_DOC_TYPE and format in BIR_2307_PRINT_FORMATS:
		doc = doc or frappe.get_doc(doctype, name)
		if isinstance(doc, str):
			doc = json.loads(doc)
		if isinstance(doc, dict):
			doc = frappe.get_doc(doc)
		validate_print_permission(doc)

		with print_language(language):
			pdf_file = build_bir_2307_pdf(doc)

		frappe.local.response.filename = "{name}.pdf".format(name=name.replace(" ", "-").replace("/", "-"))
		frappe.local.response.filecontent = pdf_file
		frappe.local.response.type = "pdf"
		return

	from frappe.utils.print_format import download_pdf as frappe_download_pdf

	return frappe_download_pdf(
		doctype,
		name,
		format,
		doc=doc,
		no_letterhead=no_letterhead,
		language=language,
		letterhead=letterhead,
		pdf_generator=pdf_generator,
	)
