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
		self.assertNotIn("Lead", doctype_js)
		self.assertNotIn("Lead", _hook_map("doctype_list_js"))


if __name__ == "__main__":
	unittest.main()
