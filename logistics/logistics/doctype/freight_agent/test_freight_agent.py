# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase


# On IntegrationTestCase, the doctype test records and all
# link-field test record dependencies are recursively loaded
# Use these module variables to add/remove to/from that list
EXTRA_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]
IGNORE_TEST_RECORD_DEPENDENCIES = []  # eg. ["User"]



class IntegrationTestFreightAgent(IntegrationTestCase):
	"""
	Integration tests for FreightAgent.
	Use this class for testing interactions between multiple components.
	"""

	def test_new_freight_agent_requires_service_type(self):
		sfx = frappe.generate_hash(length=6)
		with self.assertRaises(frappe.ValidationError):
			frappe.get_doc(
				{
					"doctype": "Freight Agent",
					"code": f"IT-FA-{sfx}",
					"freight_agent_name": f"Integration Agent {sfx}",
				}
			).insert(ignore_permissions=True)
