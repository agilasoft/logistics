"""Render Union Bank Telegraphic Transfer PDF to a high-DPI PNG for UBP bank form print format."""

from __future__ import annotations

import os
import shutil

import frappe

APP_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
IMAGES_DIR = os.path.join(APP_ROOT, "logistics", "public", "images")
OUTPUT_PATH = os.path.join(IMAGES_DIR, "ubp_telegraphic_transfer.png")
SOURCE_CANDIDATES = [
	os.path.join(IMAGES_DIR, "ubp_telegraphic_transfer_source.pdf"),
]


def _find_pdf(pdf_path: str | None = None) -> str:
	if pdf_path and os.path.isfile(pdf_path):
		return pdf_path
	for candidate in SOURCE_CANDIDATES:
		if os.path.isfile(candidate):
			return candidate
	frappe.throw(
		"Union Bank PDF not found. Copy the original PDF to "
		f"{SOURCE_CANDIDATES[0]} or pass pdf_path, then run:\n"
		"bench --site <site> execute "
		"logistics.print_format.payment_entry.generate_ubp_background.render"
	)


@frappe.whitelist()
def render(pdf_path: str | None = None, dpi: int = 300) -> dict:
	"""Render page 1 of the Union Bank form PDF to a print-quality PNG background."""
	import fitz

	source = _find_pdf(pdf_path)
	os.makedirs(IMAGES_DIR, exist_ok=True)

	archive = os.path.join(IMAGES_DIR, "ubp_telegraphic_transfer_source.pdf")
	if os.path.abspath(source) != os.path.abspath(archive):
		shutil.copy2(source, archive)

	doc = fitz.open(archive)
	page = doc[0]
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
