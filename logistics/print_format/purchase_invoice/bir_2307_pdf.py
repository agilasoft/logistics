"""Vector BIR Form 2307 PDF for Purchase Invoice print format."""

from __future__ import annotations

import base64
import json
import os
import re
import shutil
from typing import Any

import frappe
from frappe.utils import getdate

PRINT_FORMAT_NAME = "BIR 2307"
BIR_2307_PRINT_FORMATS = {PRINT_FORMAT_NAME}
DOC_TYPE = "Purchase Invoice"

APP_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
IMAGES_DIR = os.path.join(APP_ROOT, "logistics", "public", "images")
TEMPLATE_PDF = os.path.join(IMAGES_DIR, "bir_form_2307_source.pdf")
FIELD_MAP_PATH = os.path.join(os.path.dirname(__file__), "bir_2307_field_map.json")
def _source_candidates() -> list[str]:
	candidates = [TEMPLATE_PDF]
	try:
		candidates.append(
			os.path.join(
				frappe.get_app_path("phtax"),
				"public",
				"pdf",
				"bir_form_2307_jan_2018_encs_v3.pdf",
			)
		)
	except Exception:
		pass
	return candidates

FONT_SIZE = 8
TABLE_FONT_SIZE = 7
CHAR_BOX_SIZE = 10


def _install_instructions() -> str:
	return (
		"Install the official BIR Form 2307 PDF (vector, not PNG export):\n"
		f"  scp \"bir_form_2307_jan_2018_encs_v3.pdf\" frappe@<server>:{TEMPLATE_PDF}\n"
		"Then run:\n"
		"  bench --site <site> execute "
		"logistics.print_format.purchase_invoice.bir_2307_pdf.install_bir_template_pdf"
	)


def _load_field_map() -> dict[str, Any]:
	with open(FIELD_MAP_PATH, encoding="utf-8") as handle:
		return json.load(handle)


def _find_pdf(pdf_path: str | None = None) -> str:
	if pdf_path and os.path.isfile(pdf_path):
		return pdf_path
	if os.path.isfile(TEMPLATE_PDF):
		return TEMPLATE_PDF
	for candidate in _source_candidates()[1:]:
		if os.path.isfile(candidate):
			return candidate
	frappe.throw("BIR Form 2307 vector PDF template not found.\n" f"{_install_instructions()}")


def _get_bir_context(doc):
	try:
		from phtax.cas.utils.bir_2307_print import get_bir_2307_print_context
	except ImportError:
		frappe.throw(
			"The phtax app is required for BIR Form 2307 printing. "
			"Install phtax and run bench migrate."
		)
	return get_bir_2307_print_context(doc)


def _format_amount(amount, blank_if_zero: bool = False) -> str:
	from phtax.cas.utils.bir_2307_print import format_money

	return format_money(amount, blank_if_zero)


def _insert_char(page, x_pt: float, y_pt: float, char: str, font_size: int = FONT_SIZE) -> None:
	import fitz

	if not str(char).strip():
		return
	rect = fitz.Rect(x_pt, y_pt, x_pt + CHAR_BOX_SIZE, y_pt + CHAR_BOX_SIZE + 2)
	page.insert_textbox(
		rect,
		str(char),
		fontname="helv",
		fontsize=font_size,
		color=(0, 0, 0),
		align=fitz.TEXT_ALIGN_CENTER,
	)


def _insert_boxed_chars(page, boxes: list[list[float]], value: str, font_size: int = FONT_SIZE) -> None:
	chars = list(str(value or ""))
	for idx, (x_pt, y_pt) in enumerate(boxes):
		char = chars[idx] if idx < len(chars) else ""
		_insert_char(page, x_pt, y_pt, char, font_size)


def _insert_text(
	page,
	x_pt: float,
	y_pt: float,
	width_pt: float,
	value: str,
	*,
	align: str = "left",
	font_size: int = FONT_SIZE,
) -> None:
	import fitz

	text = str(value or "").strip()
	if not text:
		return
	rect = fitz.Rect(x_pt, y_pt, x_pt + width_pt, y_pt + font_size + 4)
	page.insert_textbox(
		rect,
		text,
		fontname="helv",
		fontsize=font_size,
		color=(0, 0, 0),
		align=fitz.TEXT_ALIGN_RIGHT if align == "right" else fitz.TEXT_ALIGN_LEFT,
	)


def _overlay_table(
	page,
	table_key: str,
	rows: list[dict[str, Any]],
	totals: dict[str, Any],
	field_map: dict[str, Any],
) -> None:
	table = field_map[table_key]
	columns = table["columns"]
	row_positions = table["row_y"]

	for idx, row in enumerate(rows):
		if idx >= len(row_positions):
			break
		y_pt = row_positions[idx]
		_insert_text(page, columns["nature"]["x"], y_pt, columns["nature"]["width"], row["nature_of_income"])
		_insert_text(page, columns["atc"]["x"], y_pt, columns["atc"]["width"], row["atc_code"])
		_insert_text(
			page,
			columns["month_1"]["x"],
			y_pt,
			columns["month_1"]["width"],
			_format_amount(row["month_1"], True),
			align=columns["month_1"]["align"],
			font_size=TABLE_FONT_SIZE,
		)
		_insert_text(
			page,
			columns["month_2"]["x"],
			y_pt,
			columns["month_2"]["width"],
			_format_amount(row["month_2"], True),
			align=columns["month_2"]["align"],
			font_size=TABLE_FONT_SIZE,
		)
		_insert_text(
			page,
			columns["month_3"]["x"],
			y_pt,
			columns["month_3"]["width"],
			_format_amount(row["month_3"], True),
			align=columns["month_3"]["align"],
			font_size=TABLE_FONT_SIZE,
		)
		_insert_text(
			page,
			columns["total"]["x"],
			y_pt,
			columns["total"]["width"],
			_format_amount(row["income_payment"]),
			align=columns["total"]["align"],
			font_size=TABLE_FONT_SIZE,
		)
		_insert_text(
			page,
			columns["tax_withheld"]["x"],
			y_pt,
			columns["tax_withheld"]["width"],
			_format_amount(row["tax_withheld"]),
			align=columns["tax_withheld"]["align"],
			font_size=TABLE_FONT_SIZE,
		)

	total_y = table["total_y"]
	_insert_text(
		page,
		columns["month_1"]["x"],
		total_y,
		columns["month_1"]["width"],
		_format_amount(totals["month_1"], True),
		align=columns["month_1"]["align"],
		font_size=TABLE_FONT_SIZE,
	)
	_insert_text(
		page,
		columns["month_2"]["x"],
		total_y,
		columns["month_2"]["width"],
		_format_amount(totals["month_2"], True),
		align=columns["month_2"]["align"],
		font_size=TABLE_FONT_SIZE,
	)
	_insert_text(
		page,
		columns["month_3"]["x"],
		total_y,
		columns["month_3"]["width"],
		_format_amount(totals["month_3"], True),
		align=columns["month_3"]["align"],
		font_size=TABLE_FONT_SIZE,
	)
	_insert_text(
		page,
		columns["total"]["x"],
		total_y,
		columns["total"]["width"],
		_format_amount(totals["total_income"], True),
		align=columns["total"]["align"],
		font_size=TABLE_FONT_SIZE,
	)
	_insert_text(
		page,
		columns["tax_withheld"]["x"],
		total_y,
		columns["tax_withheld"]["width"],
		_format_amount(totals["total_tax_withheld"], True),
		align=columns["tax_withheld"]["align"],
		font_size=TABLE_FONT_SIZE,
	)


def _overlay_page(page, bir: dict[str, Any], field_map: dict[str, Any]) -> None:
	period_from = getdate(bir["period_from"]).strftime("%m%d%Y") if bir.get("period_from") else ""
	period_to = getdate(bir["period_to"]).strftime("%m%d%Y") if bir.get("period_to") else ""
	_insert_boxed_chars(page, field_map["period_from_boxes"], period_from)
	_insert_boxed_chars(page, field_map["period_to_boxes"], period_to)

	payee_tin = re.sub(r"\D", "", bir["payee"].get("tin", ""))[:12]
	payor_tin = re.sub(r"\D", "", bir["payor"].get("tin", ""))[:12]
	_insert_boxed_chars(page, field_map["tin_payee_boxes"], payee_tin)
	_insert_boxed_chars(page, field_map["tin_payor_boxes"], payor_tin)

	payee_zip = re.sub(r"\D", "", bir["payee"].get("zip", ""))[:4]
	payor_zip = re.sub(r"\D", "", bir["payor"].get("zip", ""))[:4]
	_insert_boxed_chars(page, field_map["zip_payee_boxes"], payee_zip)
	_insert_boxed_chars(page, field_map["zip_payor_boxes"], payor_zip)

	for field_name, party_key in [
		("payee_name", "payee"),
		("payee_address", "payee"),
		("payor_name", "payor"),
		("payor_address", "payor"),
	]:
		field = field_map["text_fields"][field_name]
		value_key = "name" if "name" in field_name else "address"
		_insert_text(
			page,
			field["x"],
			field["y"],
			field["width"],
			bir[party_key].get(value_key, ""),
		)

	_overlay_table(page, "expanded_table", bir["expanded_rows"], bir["expanded_totals"], field_map)
	_overlay_table(page, "business_table", bir["business_rows"], bir["business_totals"], field_map)

	certificate_date = (
		getdate(bir["certificate_date"]).strftime("%m%d%Y") if bir.get("certificate_date") else ""
	)
	_insert_boxed_chars(page, field_map["signature_date_boxes"]["payor_issue"], certificate_date)


def build_pdf(doc, pdf_path: str | None = None) -> bytes:
	import fitz

	source = _find_pdf(pdf_path)
	bir = _get_bir_context(doc)
	field_map = _load_field_map()

	template = fitz.open(source)
	page = template[0]
	_overlay_page(page, bir, field_map)
	return template.tobytes(garbage=4, deflate=True)


@frappe.whitelist()
def install_bir_template_pdf(source_path: str | None = None) -> dict:
	"""Copy the official BIR Form 2307 PDF into the template location."""
	source = source_path
	if not source:
		for candidate in _source_candidates()[1:]:
			if os.path.isfile(candidate):
				source = candidate
				break
	if not source or not os.path.isfile(source):
		frappe.throw("BIR Form 2307 template PDF not found.\n" f"{_install_instructions()}")

	os.makedirs(IMAGES_DIR, exist_ok=True)
	shutil.copy2(source, TEMPLATE_PDF)

	import fitz

	doc = fitz.open(TEMPLATE_PDF)
	page_rect = doc[0].rect
	doc.close()

	return {
		"path": TEMPLATE_PDF,
		"page_width": round(page_rect.width, 2),
		"page_height": round(page_rect.height, 2),
	}


@frappe.whitelist()
def ensure_template_pdf() -> dict:
	"""Validate that a BIR Form 2307 template PDF is installed."""
	path = _find_pdf()
	import fitz

	doc = fitz.open(path)
	page_rect = doc[0].rect
	doc.close()
	return {"path": path, "page_width": round(page_rect.width, 2), "page_height": round(page_rect.height, 2)}


@frappe.whitelist()
def get_embedded_pdf(doctype: str, name: str) -> str:
	doc = frappe.get_doc(doctype, name)
	pdf_bytes = build_pdf(doc)
	encoded = base64.b64encode(pdf_bytes).decode("ascii")
	return f"data:application/pdf;base64,{encoded}"
