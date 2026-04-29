# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and Contributors
# See license.txt

# import frappe
from frappe.tests import IntegrationTestCase


# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]



class IntegrationTestSeaFreightSettings(IntegrationTestCase):
	"""
	Integration tests for SeaFreightSettings.
	Use this class for testing interactions between multiple components.
	"""

	def test_get_settings_returns_none_without_company_match(self):
		from logistics.sea_freight.doctype.sea_freight_settings.sea_freight_settings import SeaFreightSettings

		self.assertIsNone(SeaFreightSettings.get_settings("__nonexistent_company_for_sf_settings_test__"))
