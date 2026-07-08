"""Render BDO Telegraphic Transfer PDF to PNG (legacy fallback).

The Bank Forms print format now stamps fields directly onto the vector PDF
via bank_forms_pdf.py. This script is only needed if you still want a raster
preview asset.
"""

from __future__ import annotations

import os
import shutil

import frappe

APP_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
IMAGES_DIR = os.path.join(APP_ROOT, "logistics", "public", "images")
OUTPUT_PATH = os.path.join(IMAGES_DIR, "bdo_telegraphic_transfer.png")
SOURCE_CANDIDATES = [
	os.path.join(IMAGES_DIR, "bdo_telegraphic_transfer_source.pdf"),
	"/home/kitler/Documents/ATN Print Format/BDO Telegraphic Transfer.pdf",
	"/home/frappe/frappe-bench/apps/logistics/logistics/public/images/BDO Telegraphic Transfer.pdf",
]


def _find_pdf(pdf_path: str | None = None) -> str:
	if pdf_path and os.path.isfile(pdf_path):
		return pdf_path
	for candidate in SOURCE_CANDIDATES:
		if os.path.isfile(candidate):
			return candidate
	frappe.throw(
		"BDO PDF not found. Copy the original PDF to either:\n"
		f"  {SOURCE_CANDIDATES[0]}\n"
		f"  {SOURCE_CANDIDATES[1]}\n"
		"Then run:\n"
		"  bench --site <site> execute "
		"logistics.print_format.payment_entry.generate_bdo_background.render\n"
		"  bench build --app logistics"
	)


@frappe.whitelist()
def render(pdf_path: str | None = None, dpi: int = 300) -> dict:
	"""Render page 1 of the BDO form PDF to a print-quality PNG background."""
	import fitz

	source = _find_pdf(pdf_path)
	os.makedirs(IMAGES_DIR, exist_ok=True)

	archive = os.path.join(IMAGES_DIR, "bdo_telegraphic_transfer_source.pdf")
	if os.path.abspath(source) != os.path.abspath(archive):
		shutil.copy2(source, archive)

	doc = fitz.open(archive)
	page = doc[0]
	# 300 DPI: zoom = dpi / 72
	pix = page.get_pixmap(matrix=fitz.Matrix(dpi / 72, dpi / 72), alpha=False)
	pix.save(OUTPUT_PATH)

	return {
		"source": archive,
		"output": OUTPUT_PATH,
		"dpi": dpi,
		"width": pix.width,
		"height": pix.height,
		"size_kb": round(os.path.getsize(OUTPUT_PATH) / 1024),
	}
