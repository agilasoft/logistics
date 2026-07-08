# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from logistics.air_freight.iata_cargo_xml.eawb_utils import map_fsu_status, resolve_special_handling_codes


class TestEAWBPhases(FrappeTestCase):
	def test_fsu_status_mapping_includes_rcs_foh(self):
		self.assertEqual(map_fsu_status("RCS"), "Ready for Carriage")
		self.assertEqual(map_fsu_status("FOH"), "Freight on Hand")
		self.assertEqual(map_fsu_status("SPL"), "Split Arrival")

	def test_special_handling_codes_default_ecc(self):
		codes = resolve_special_handling_codes()
		self.assertIn("ECC", codes)

	def test_special_handling_codes_paper_awb(self):
		codes = resolve_special_handling_codes(paper_awb_required=True)
		self.assertIn("ECP", codes)

	def tearDown(self):
		frappe.db.rollback()
