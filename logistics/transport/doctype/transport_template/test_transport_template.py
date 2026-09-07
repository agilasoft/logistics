# Copyright (c) 2026, Agilasoft and contributors
# Licensed under the MIT License. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from logistics.transport.doctype.transport_template.transport_template import (
	TransportTemplate,
	get_transport_template_constraints,
)


class TestTransportTemplate(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def _ensure_load_type(self, name: str, **flags):
		if frappe.db.exists("Load Type", name):
			doc = frappe.get_doc("Load Type", name)
			for key, value in flags.items():
				doc.set(key, value)
			doc.save(ignore_permissions=True)
			return doc.name

		doc = frappe.new_doc("Load Type")
		doc.load_type_name = name
		doc.description = name
		doc.is_active = 1
		for key, value in flags.items():
			doc.set(key, value)
		doc.insert(ignore_permissions=True)
		return doc.name

	def test_save_land_lane_template(self):
		ftl = self._ensure_load_type("FTL", transport=1, non_container=1)
		ltl = self._ensure_load_type("LTL", transport=1, non_container=1)

		doc = frappe.get_doc(
			{
				"doctype": "Transport Template",
				"code": "UT-CFS-WHS",
				"description": "CFS to warehouse",
				"default_load_type": ftl,
				"legs": [
					{
						"facility_type_from": "Container Freight Station",
						"facility_type_to": "Storage Facility",
					}
				],
				"allowed_load_types": [{"load_type": ftl}, {"load_type": ltl}],
			}
		)
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.default_load_type, ftl)

	def test_save_allows_fcl_on_land_lane(self):
		ftl = self._ensure_load_type("FTL", transport=1, non_container=1)
		fcl = self._ensure_load_type("FCL", transport=1, container=1, sea=1)

		doc = frappe.get_doc(
			{
				"doctype": "Transport Template",
				"code": "UT-CFS-RCVR",
				"description": "CFS to Consignee",
				"default_load_type": fcl,
				"legs": [
					{
						"facility_type_from": "Container Freight Station",
						"facility_type_to": "Consignee",
					}
				],
				"allowed_load_types": [{"load_type": fcl}, {"load_type": ftl}],
			}
		)
		doc.insert(ignore_permissions=True)
		self.assertEqual(doc.default_load_type, fcl)

	def test_get_constraints_filters_by_transport_job_type(self):
		ftl = self._ensure_load_type("FTL", transport=1, non_container=1)
		ltl = self._ensure_load_type("LTL", transport=1, non_container=1)
		fcl = self._ensure_load_type("FCL", transport=1, container=1, sea=1)

		doc = frappe.get_doc(
			{
				"doctype": "Transport Template",
				"code": "UT-JOB-FILTER",
				"description": "Job type filter test",
				"default_load_type": fcl,
				"legs": [
					{
						"facility_type_from": "Container Freight Station",
						"facility_type_to": "Consignee",
					}
				],
				"allowed_load_types": [
					{"load_type": fcl},
					{"load_type": ftl},
					{"load_type": ltl},
				],
			}
		)
		doc.insert(ignore_permissions=True)

		container_constraints = get_transport_template_constraints(doc.name, "Container")
		self.assertEqual(container_constraints["allowed_load_types"], [fcl])
		self.assertEqual(
			container_constraints["allowed_load_types_all"],
			[fcl, ftl, ltl],
		)

		non_container_constraints = get_transport_template_constraints(doc.name, "Non-Container")
		self.assertEqual(non_container_constraints["allowed_load_types"], [ftl, ltl])

	def test_transport_template_class_validate(self):
		ftl = self._ensure_load_type("FTL", transport=1, non_container=1)
		doc = TransportTemplate(
			{
				"doctype": "Transport Template",
				"code": "UT-CLASS",
				"description": "Class validate",
				"default_load_type": ftl,
				"legs": [
					{
						"facility_type_from": "Shipper",
						"facility_type_to": "Consignee",
					}
				],
				"allowed_load_types": [{"load_type": ftl}],
			}
		)
		doc.insert(ignore_permissions=True)
		self.assertTrue(frappe.db.exists("Transport Template", doc.name))
