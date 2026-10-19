# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Add Service choices stay the Linked Service service types, without a meta lookup."""

import ast
import json
import re
import unittest
from pathlib import Path

APP = Path(__file__).resolve().parents[1]


def _doctype_service_types() -> list[str]:
	data = json.loads(
		(APP / "logistics/doctype/linked_service/linked_service.json").read_text()
	)
	options = next(
		field["options"] for field in data["fields"] if field["fieldname"] == "service_type"
	)
	return [
		line.strip()
		for line in str(options).split("\n")
		if line.strip() and not line.strip().startswith("---")
	]


def _canonical_service_types() -> set[str]:
	tree = ast.parse((APP / "time_sensitive/service_linking.py").read_text())
	for node in tree.body:
		if not isinstance(node, ast.Assign):
			continue
		if not any(
			isinstance(target, ast.Name) and target.id == "CANONICAL_SERVICE_TYPES"
			for target in node.targets
		):
			continue
		call = node.value
		set_node = call.args[0]
		return {elt.value for elt in set_node.elts}
	raise AssertionError("CANONICAL_SERVICE_TYPES was not found")


def _dialog_fallback_service_types() -> list[str]:
	text = (APP / "public/js/linked_services_dialog.js").read_text()
	match = re.search(
		r"const LSD1_DEFAULT_SERVICE_TYPES = \[(.*?)\];",
		text,
		re.S,
	)
	if not match:
		raise AssertionError("LSD1_DEFAULT_SERVICE_TYPES was not found")
	return re.findall(r'"([^"]+)"', match.group(1))


class TestLinkedServiceTypeOptions(unittest.TestCase):
	def test_dialog_service_types_match_linked_service_doctype(self):
		types = _doctype_service_types()
		self.assertEqual(_dialog_fallback_service_types(), types)
		self.assertEqual(_canonical_service_types(), set(types))
		self.assertEqual(len(_canonical_service_types()), len(types))

		dialog = (APP / "public/js/linked_services_dialog.js").read_text()
		self.assertIn(
			"serviceTypes: opts.serviceTypes || LSD1_DEFAULT_SERVICE_TYPES",
			dialog,
		)
		self.assertNotIn("_lsd1_service_types_from_linked_service", dialog)
		self.assertNotIn('with_doctype("Linked Service"', dialog)
