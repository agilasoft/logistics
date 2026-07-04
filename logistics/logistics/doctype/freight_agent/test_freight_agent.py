# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase

from logistics.utils.test_freight_agent_location_validation import create_test_freight_agent


class IntegrationTestFreightAgent(IntegrationTestCase):
	"""Integration tests for Freight Agent."""

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
	def test_freight_agent_covered_unlocs_persist(self):
		agent = create_test_freight_agent(
			code="INT-FA-001",
			freight_agent_name="Integration Freight Agent",
			covered_unlocs=["PHMNL"],
			default_unloco="PHMNL",
		)
		doc = frappe.get_doc("Freight Agent", agent)
		self.assertEqual(len(doc.covered_unlocs), 1)
		self.assertEqual(doc.covered_unlocs[0].unloco, "PHMNL")
