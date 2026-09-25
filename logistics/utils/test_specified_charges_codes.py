# Copyright (c) 2026, Agilasoft and contributors

from frappe.tests import UnitTestCase

from logistics.utils.specified_charges_codes import parse_code_list


class TestSpecifiedChargesCodes(UnitTestCase):
	def test_parse_json_list(self):
		self.assertEqual(parse_code_list('["A","B"]'), ["A", "B"])

	def test_parse_empty(self):
		self.assertEqual(parse_code_list(None), [])
		self.assertEqual(parse_code_list(""), [])
