"""Push company-safe Jinja from repo fixtures/files into Print Format records."""

from __future__ import annotations

import json
import os

import frappe

UNSAFE_COMPANY_LOOKUP = 'get_doc("Company", doc.company)'
SAFE_COMPANY_GUARD = 'frappe.db.exists("Company", doc.company)'

# Print formats stored as HTML only (no JSON fixture in repo).
HTML_FILE_SYNC = {
	"Journal Entry HTML": "print_format/journal_entry/journal_entry.html",
	"Payment Entry HTML": "print_format/payment_entry/payment_entry.html",
	"Bank Forms": "print_format/payment_entry/bdo_form.html",
	"BDO Form Blank": "print_format/payment_entry/bdo_form_blank.html",
	"Bank Cheque": "print_format/payment_entry/bank_cheque.html",
	"UBP Bank Form": "print_format/payment_entry/ubp_bank_form.html",
	"UBP Form Blank": "print_format/payment_entry/ubp_bank_form_blank.html",
	"MAWB": "logistics/air_freight/print_format/mawb/mawb.html",
	"MAWB Forwarder Copy": "logistics/air_freight/doctype/master_air_waybill/mawb.html",
	"HAWB": "logistics/air_freight/print_format/hawb/hawb.html",
}


def _logistics_app_root() -> str:
	return os.path.dirname(frappe.get_app_path("logistics"))


def _is_company_safe(html: str) -> bool:
	if UNSAFE_COMPANY_LOOKUP not in html:
		return True
	return SAFE_COMPANY_GUARD in html


def _collect_json_fixture_html() -> dict[str, str]:
	sources: dict[str, str] = {}
	app_path = frappe.get_app_path("logistics")
	for root, _dirs, files in os.walk(app_path):
		if "print_format" not in root.replace("\\", "/"):
			continue
		for filename in files:
			if not filename.endswith(".json"):
				continue
			path = os.path.join(root, filename)
			try:
				with open(path, encoding="utf-8") as handle:
					data = json.load(handle)
			except (OSError, json.JSONDecodeError):
				continue
			if data.get("doctype") != "Print Format":
				continue
			name = data.get("name")
			html = data.get("html")
			if name and html and _is_company_safe(html):
				sources[name] = html
	return sources


def _collect_html_file_sources() -> dict[str, str]:
	sources: dict[str, str] = {}
	app_root = _logistics_app_root()
	for name, rel_path in HTML_FILE_SYNC.items():
		path = os.path.join(app_root, rel_path)
		if not os.path.exists(path):
			continue
		with open(path, encoding="utf-8") as handle:
			html = handle.read()
		if _is_company_safe(html):
			sources[name] = html
	return sources


def sync_company_safe_print_formats() -> list[str]:
	"""Update Print Format HTML when the DB copy still uses unsafe Company lookup."""
	sources = _collect_json_fixture_html()
	sources.update(_collect_html_file_sources())

	updated: list[str] = []
	for name, html in sources.items():
		if not frappe.db.exists("Print Format", name):
			continue
		current = frappe.db.get_value("Print Format", name, "html") or ""
		if current == html:
			continue
		if not _is_company_safe(current) or name in HTML_FILE_SYNC:
			frappe.db.set_value("Print Format", name, "html", html, update_modified=False)
			updated.append(name)

	return updated
