# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Desk hook script paths must resolve from the logistics package root.

Frappe joins each doctype_js path onto the app package. A leading
"logistics/" on a public or submodule path points at a missing file.
"""

from __future__ import annotations

import ast
import unittest
from pathlib import Path


PACKAGE = Path(__file__).resolve().parents[1]
HOOKS = PACKAGE / "hooks.py"


def _hook_map(name):
	module = ast.parse(HOOKS.read_text())
	for node in module.body:
		if not isinstance(node, ast.Assign):
			continue
		for target in node.targets:
			if isinstance(target, ast.Name) and target.id == name:
				return ast.literal_eval(node.value)
	raise AssertionError(f"{name} is missing from hooks.py")


def _files(value):
	if isinstance(value, str):
		return [value]
	return list(value)


class TestDoctypeJsPaths(unittest.TestCase):
	def test_doctype_and_page_scripts_exist(self):
		for hook in ("doctype_js", "doctype_list_js", "page_js"):
			for key, value in _hook_map(hook).items():
				for relative in _files(value):
					self.assertTrue(
						(PACKAGE / relative).is_file(),
						f"{hook}[{key}] -> {relative}",
					)

	def test_warehouse_job_keeps_contract_and_recognition_scripts(self):
		scripts = _files(_hook_map("doctype_js")["Warehouse Job"])
		self.assertIn("warehousing/warehouse_order_contract_accounts.js", scripts)
		self.assertIn("job_management/recognition_client.js", scripts)
		self.assertEqual(len(scripts), len(set(scripts)))

	def test_removed_doctype_names_are_not_hook_keys(self):
		doctype_js = _hook_map("doctype_js")
		self.assertNotIn("Project Task Order", doctype_js)
		self.assertNotIn("Dispute", doctype_js)
		self.assertNotIn("Lead", doctype_js)
		self.assertNotIn("Lead", _hook_map("doctype_list_js"))

	def test_hooks_do_not_load_invoice_dispute(self):
		text = HOOKS.read_text()
		self.assertNotIn("invoice_dispute", text)
		self.assertNotIn("validate_payment_entry_against_disputes", text)
		self.assertNotIn("validate_settlement_entry_against_disputes", text)

	def test_app_does_not_query_dispute_doctype(self):
		needles = (
			"tabDispute",
			'get_value("Dispute"',
			"get_value('Dispute'",
			'get_all("Dispute"',
			"get_all('Dispute'",
			'get_doc("Dispute"',
			"get_doc('Dispute'",
			"invoice_dispute",
			"get_active_dispute",
		)
		hits = []
		for path in PACKAGE.rglob("*"):
			if not path.is_file() or path.suffix not in {".py", ".js", ".json"}:
				continue
			if path.name == "test_doctype_js_paths.py":
				continue
			text = path.read_text(errors="ignore")
			for needle in needles:
				if needle in text:
					hits.append(f"{path.relative_to(PACKAGE)}: {needle}")
			if '"Dispute"' in text or "'Dispute'" in text:
				hits.append(f"{path.relative_to(PACKAGE)}: Dispute DocType literal")
		self.assertEqual(hits, [])


if __name__ == "__main__":
	unittest.main()
