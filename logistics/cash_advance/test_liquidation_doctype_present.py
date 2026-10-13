# Copyright (c) 2026, Agilasoft and contributors
"""Cash Advance Liquidation stays a parent DocType the desk can open."""

from __future__ import annotations

import ast
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
JSON_PATH = (
	ROOT
	/ "logistics/cash_advance/doctype/cash_advance_liquidation/cash_advance_liquidation.json"
)
CONTROLLER = (
	ROOT
	/ "logistics/cash_advance/doctype/cash_advance_liquidation/cash_advance_liquidation.py"
)
HOOKS = ROOT / "logistics/hooks.py"
PATCHES = ROOT / "logistics/patches.txt"
MODULES = ROOT / "logistics/modules.txt"


def _doctype_js_paths():
	"""Last assignment wins, matching the Python dict in hooks.py."""
	tree = ast.parse(HOOKS.read_text())
	paths = {}
	for node in tree.body:
		if not isinstance(node, ast.Assign):
			continue
		target = node.targets[0]
		if not isinstance(target, ast.Name) or target.id != "doctype_js":
			continue
		for key, value in zip(node.value.keys, node.value.values, strict=True):
			if isinstance(key, ast.Constant) and isinstance(value, ast.Constant):
				paths[key.value] = value.value
	return paths


class TestCashAdvanceLiquidationDoctypePresent(unittest.TestCase):
	def test_parent_doctype_file_is_routable(self):
		doc = json.loads(JSON_PATH.read_text())
		self.assertEqual(doc["name"], "Cash Advance Liquidation")
		self.assertEqual(doc["module"], "Cash Advance")
		self.assertFalse(doc.get("istable"))
		self.assertFalse(doc.get("issingle"))
		self.assertIn("Cash Advance", MODULES.read_text().splitlines())
		self.assertIn("class CashAdvanceLiquidation", CONTROLLER.read_text())
		roles = {row["role"] for row in doc["permissions"] if row.get("read")}
		self.assertIn("System Manager", roles)

	def test_form_script_path_is_module_relative(self):
		path = _doctype_js_paths()["Cash Advance Liquidation"]
		self.assertEqual(
			path,
			"cash_advance/doctype/cash_advance_liquidation/cash_advance_liquidation.js",
		)
		self.assertFalse(path.startswith("logistics/"))

	def test_migrate_reimports_a_missing_doctype(self):
		text = PATCHES.read_text()
		self.assertIn("logistics.patches.v3_0_restore_cash_advance_liquidation_doctype", text)
		install = (ROOT / "logistics/cash_advance/install.py").read_text()
		self.assertIn("def ensure_cash_advance_liquidation_doctype", install)
		self.assertIn("ensure_cash_advance_liquidation_doctype()", install)
