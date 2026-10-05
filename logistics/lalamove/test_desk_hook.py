# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import pathlib
import unittest


class TestLalamoveSeaShipmentHook(unittest.TestCase):
	def test_sea_shipment_loads_the_lalamove_form_script(self):
		hooks = pathlib.Path(__file__).resolve().parents[1] / "hooks.py"
		text = hooks.read_text(encoding="utf-8")
		start = text.index('\t"Sea Shipment": [')
		end = text.index('\t"Sea Consolidation": [')
		block = text[start:end]
		self.assertIn("sea_freight/doctype/sea_shipment/sea_shipment_lalamove.js", block)
		script = (
			pathlib.Path(__file__).resolve().parents[1]
			/ "sea_freight/doctype/sea_shipment/sea_shipment_lalamove.js"
		)
		self.assertTrue(script.is_file())
		assets = pathlib.Path(__file__).resolve().parents[1] / "public" / "lalamove"
		self.assertTrue((assets / "utils.js").is_file())
		self.assertTrue((assets / "lalamove_form.js").is_file())
