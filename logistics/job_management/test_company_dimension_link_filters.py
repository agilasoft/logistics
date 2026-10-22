# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt
"""Branch and Cost Center links follow the Company set on the same document."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]

# Child tables whose Company lives on the parent form.
PARENT_COMPANY = {
	"Recognition Policy Parameter",
	"Gate Pass Item",
	"Sales Invoice Item",
	"Sales Taxes and Charges",
}

# Standard ERPNext doctypes that have Company, extended by a custom field here.
STANDARD_COMPANY = {
	"Cost Center",
	"Sales Invoice",
}

# Branch on these records is copied onto a booking and is not company-scoped.
BRANCH_UNFILTERED = {
	("Linked Service", "branch"),
	("Linked Service Detail", "branch"),
}


def _documents():
	for path in APP_ROOT.rglob("*.json"):
		try:
			document = json.loads(path.read_text())
		except (OSError, json.JSONDecodeError):
			continue
		if isinstance(document, dict):
			yield path, document


def _fields(document):
	doctype = document.get("doctype")
	if doctype == "DocType" or (doctype is None and isinstance(document.get("fields"), list)):
		yield document.get("name"), document.get("fields") or []
	elif doctype == "Web Form":
		yield document.get("name"), document.get("web_form_fields") or []
	elif isinstance(document.get("custom_fields"), list):
		grouped = {}
		for field in document["custom_fields"]:
			if isinstance(field, dict):
				grouped.setdefault(field.get("dt"), []).append(field)
		yield from grouped.items()


def _has_company(fields):
	for field in fields:
		if not isinstance(field, dict):
			continue
		if (
			field.get("fieldname") in ("company", "custom_company")
			and field.get("fieldtype") == "Link"
			and field.get("options") == "Company"
		):
			return True
	return False


def _expects_company_filter(parent, field):
	options = field.get("options")
	fieldname = field.get("fieldname")
	if options == "Branch" and (parent, fieldname) in BRANCH_UNFILTERED:
		return None
	return options in ("Branch", "Cost Center")


class TestCompanyDimensionLinkFilters(unittest.TestCase):
	def test_doctype_links_follow_company(self):
		missing = []
		uncovered = []
		exempt_but_filtered = []
		found = 0
		for path, document in _documents():
			# Reports are filtered in the query-report script. Web Form Field has no
			# link_filters column, so those pickers are filtered in the web form script.
			if document.get("doctype") in ("Report", "Web Form"):
				continue
			for parent, fields in _fields(document):
				has_company = _has_company(fields) or parent in STANDARD_COMPANY
				company_expr = "eval:doc.company"
				if parent in PARENT_COMPANY:
					has_company = True
					company_expr = "eval:parent.company"
				if not has_company:
					for field in fields:
						if (
							isinstance(field, dict)
							and field.get("fieldtype") == "Link"
							and field.get("options") in ("Branch", "Cost Center")
						):
							uncovered.append(
								f"{path.relative_to(APP_ROOT)}:{parent}.{field.get('fieldname')}"
							)
					continue
				for field in fields:
					if not isinstance(field, dict) or field.get("fieldtype") != "Link":
						continue
					if field.get("options") not in ("Branch", "Cost Center"):
						continue
					found += 1
					filters = field.get("link_filters") or ""
					expect = _expects_company_filter(parent, field)
					if expect is None:
						if "custom_company" in filters or '"company"' in filters:
							exempt_but_filtered.append(
								f"{path.relative_to(APP_ROOT)}:{field.get('fieldname')}"
							)
						continue
					if company_expr not in filters:
						missing.append(
							f"{path.relative_to(APP_ROOT)}:{parent}.{field.get('fieldname')}"
						)
						continue
					if field.get("options") == "Branch" and "custom_company" not in filters:
						missing.append(
							f"{path.relative_to(APP_ROOT)}:{parent}.{field.get('fieldname')} missing custom_company"
						)
					if field.get("options") == "Cost Center" and '"company"' not in filters:
						missing.append(
							f"{path.relative_to(APP_ROOT)}:{parent}.{field.get('fieldname')} missing company"
						)
		self.assertGreater(found, 0)
		self.assertEqual(missing, [])
		self.assertEqual(exempt_but_filtered, [])
		self.assertEqual(uncovered, [])

	def test_no_broken_eval_prefix(self):
		broken = []
		for path, document in _documents():
			raw = json.dumps(document)
			if "eval.doc." in raw:
				broken.append(str(path.relative_to(APP_ROOT)))
		self.assertEqual(broken, [])

	def test_web_forms_filter_branch_and_cost_center_by_company(self):
		for relative in (
			"warehousing/web_form/release_order/release_order.js",
			"warehousing/web_form/transfer_order/transfer_order.js",
			"warehousing/web_form/stocktake_order/stocktake_order.js",
		):
			script = (APP_ROOT / relative).read_text()
			self.assertIn("custom_company", script, relative)
			self.assertIn("fields_dict.cost_center", script, relative)
			self.assertIn("get_value(\"company\")", script, relative)
			raw = (APP_ROOT / relative).with_suffix(".json").read_text()
			self.assertNotIn("link_filters", raw, relative)

	def test_report_branch_and_cost_center_sit_beside_company(self):
		import re

		bare = []
		for path in APP_ROOT.rglob("*.js"):
			if "report" not in path.parts:
				continue
			text = path.read_text()
			if "query_reports" not in text:
				continue
			has_dimension = bool(
				re.search(r"""options\s*:\s*["'](?:Branch|Cost Center)["']""", text)
			)
			has_company = bool(re.search(r"""fieldname\s*:\s*["']company["']""", text)) and bool(
				re.search(r"""options\s*:\s*["']Company["']""", text)
			)
			if has_dimension and not has_company:
				bare.append(str(path.relative_to(APP_ROOT)))
		self.assertEqual(bare, [])

	def test_desk_script_filters_forms_dialogs_and_reports(self):
		script = (APP_ROOT / "public/js/company_dimension_filters.js").read_text()
		hooks = (APP_ROOT / "hooks.py").read_text()
		self.assertIn("company_dimension_filters.js", hooks)
		self.assertIn("Linked Service", script)
		self.assertIn("Linked Service Detail", script)
		self.assertIn("frappe.views.QueryReport", script)
		self.assertIn("frappe.ui.Dialog", script)
		self.assertIn("custom_company", script)
		self.assertIn('"Cost Center"', script)
		summary = APP_ROOT / "job_management/report/job_financial_summary/job_financial_summary.js"
		self.assertNotIn("filters:", summary.read_text())
