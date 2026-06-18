"""Install / refresh Master Air Waybill print formats from repo HTML."""

from __future__ import annotations

import os

import frappe

MAWB_CARRIER = "MAWB"
MAWB_FORWARDER = "MAWB Forwarder Copy"

MAWB_CARRIER_HTML = os.path.join(os.path.dirname(__file__), "mawb.html")
MAWB_FORWARDER_HTML = os.path.join(
	frappe.get_app_path("logistics"),
	"air_freight",
	"doctype",
	"master_air_waybill",
	"mawb.html",
)


def _read_html(path: str) -> str:
	with open(path, encoding="utf-8") as handle:
		return handle.read()


def _upsert_print_format(name: str, doc_type: str, html: str) -> None:
	if frappe.db.exists("Print Format", name):
		frappe.db.set_value("Print Format", name, "html", html, update_modified=False)
		return

	doc = frappe.get_doc(
		{
			"doctype": "Print Format",
			"name": name,
			"doc_type": doc_type,
			"module": "Air Freight",
			"standard": "No",
			"custom_format": 1,
			"print_format_type": "Jinja",
			"html": html,
			"font_size": 10,
			"disabled": 0,
			"align_labels_right": 0,
			"line_breaks": 0,
			"print_format_builder": 0,
			"raw_printing": 0,
			"show_section_headings": 0,
		}
	)
	doc.insert(ignore_permissions=True)


def _is_unsafe_company_html(html: str) -> bool:
	"""True when template may call get_doc('Company', None) on Master Air Waybill."""
	if 'get_doc("Company", doc.company)' in html and 'frappe.db.exists("Company", doc.company)' not in html:
		return True
	if 'get_doc("Company", linked_company)' in html and 'frappe.db.exists("Company", linked_company)' not in html:
		return True
	return False


def _pick_replacement_html(current_html: str, carrier_html: str, forwarder_html: str) -> str:
	"""Use forwarder face for HAWB-style site formats (e.g. MAWB HTML on cloud benches)."""
	hawb_markers = ("hawb_raw", "mawb-form-head", "Original 2 (for Consignee)", "FREIGHT PREPAID")
	if any(marker in current_html for marker in hawb_markers):
		return forwarder_html
	return carrier_html


def patch_unsafe_master_awb_print_formats(carrier_html: str, forwarder_html: str) -> list[str]:
	"""Fix custom Master Air Waybill print formats still stored in the site database."""
	patched: list[str] = []
	for row in frappe.get_all(
		"Print Format",
		filters={"doc_type": "Master Air Waybill"},
		fields=["name"],
	):
		name = row.name
		if name in {MAWB_CARRIER, MAWB_FORWARDER}:
			continue
		current = frappe.db.get_value("Print Format", name, "html") or ""
		if not _is_unsafe_company_html(current):
			continue
		replacement = _pick_replacement_html(current, carrier_html, forwarder_html)
		frappe.db.set_value("Print Format", name, "html", replacement, update_modified=False)
		patched.append(name)
	return patched


def install_mawb_print_formats() -> list[str]:
	"""Push carrier + forwarder MAWB templates into Print Format records."""
	updated: list[str] = []

	carrier_html = _read_html(MAWB_CARRIER_HTML)
	_upsert_print_format(MAWB_CARRIER, "Master Air Waybill", carrier_html)
	updated.append(MAWB_CARRIER)

	forwarder_html = ""
	if os.path.exists(MAWB_FORWARDER_HTML):
		forwarder_html = _read_html(MAWB_FORWARDER_HTML)
		_upsert_print_format(MAWB_FORWARDER, "Master Air Waybill", forwarder_html)
		updated.append(MAWB_FORWARDER)

	if forwarder_html:
		updated.extend(patch_unsafe_master_awb_print_formats(carrier_html, forwarder_html))

	return updated
