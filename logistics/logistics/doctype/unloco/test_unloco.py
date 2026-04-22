# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase


# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]



class IntegrationTestUNLOCO(IntegrationTestCase):
	"""
	Integration tests for UNLOCO.
	Use this class for testing interactions between multiple components.
	"""

	def test_external_refresh_survives_save_autopopulate(self):
		"""Update All merges DataHub then save(); validate must not re-read stale DB over checkboxes."""
		from logistics.air_freight.utils.datahub_unlocode import function_field_to_unloco_capabilities

		code = "QQQQQ"
		if frappe.db.exists("UNLOCO", code):
			frappe.delete_doc("UNLOCO", code, force=True)

		stale = {
			"unlocode": code,
			"location_name": "Stale Name",
			"country": "Test Country",
			"country_code": "QQ",
			"data_source": "Internal Database",
			**{k: 0 for k in function_field_to_unloco_capabilities("")},
		}
		fresh = {
			**stale,
			"location_name": "Fresh Name",
			"data_source": "DataHub.io",
			**function_field_to_unloco_capabilities("1-------"),
		}

		def fake_get_unlocode_data(unlocode, refresh_external=False):
			if refresh_external:
				return fresh
			return stale

		with patch(
			"logistics.air_freight.utils.unlocode_utils.get_unlocode_data",
			side_effect=fake_get_unlocode_data,
		):
			doc = frappe.get_doc(
				{
					"doctype": "UNLOCO",
					"unlocode": code,
					"auto_populate": 1,
				}
			)
			doc.insert()
			doc.reload()
			self.assertEqual(doc.has_seaport, 0)

			doc.populate_unlocode_details(refresh_external=True)
			self.assertEqual(doc.has_seaport, 1)
			self.assertEqual(doc.location_name, "Fresh Name")

			doc.save()
			doc.reload()

		self.assertEqual(doc.has_seaport, 1)
		self.assertEqual(doc.location_name, "Fresh Name")
