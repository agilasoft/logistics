# Copyright (c) 2026, Agilasoft and contributors
# Licensed under the MIT License. See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase

from logistics.utils.transport_template_rules import (
	classify_leg_pattern,
	get_allowed_load_types_from_doc,
	suggest_allowed_load_types_from_legs,
	validate_against_transport_template,
	validate_template_allowed_load_types_vs_legs,
)


class TestTransportTemplateRules(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_classify_leg_pattern_container(self):
		legs = [{"facility_type_from": "Terminal", "facility_type_to": "Container Yard"}]
		self.assertEqual(classify_leg_pattern(legs), "container")

	def test_classify_leg_pattern_land(self):
		legs = [
			{
				"facility_type_from": "Container Freight Station",
				"facility_type_to": "Storage Facility",
			}
		]
		self.assertEqual(classify_leg_pattern(legs), "land")

	def test_classify_leg_pattern_mixed(self):
		legs = [
			{
				"facility_type_from": "Container Yard",
				"facility_type_to": "Storage Facility",
			}
		]
		self.assertEqual(classify_leg_pattern(legs), "mixed")

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

	def test_suggest_load_types_for_land_legs(self):
		self._ensure_load_type("FTL", transport=1, non_container=1)
		self._ensure_load_type("LTL", transport=1, non_container=1)
		self._ensure_load_type("FCL", transport=1, container=1, sea=1)

		legs = [
			{
				"facility_type_from": "Container Freight Station",
				"facility_type_to": "Storage Facility",
			}
		]
		suggested = suggest_allowed_load_types_from_legs(legs)
		self.assertIn("FTL", suggested)
		self.assertIn("LTL", suggested)
		self.assertNotIn("FCL", suggested)

	def test_validate_against_template_rejects_disallowed_load_type(self):
		ftl = self._ensure_load_type("FTL", transport=1, non_container=1)
		ltl = self._ensure_load_type("LTL", transport=1, non_container=1)
		fcl = self._ensure_load_type("FCL", transport=1, container=1, sea=1)

		tpl = frappe.get_doc(
			{
				"doctype": "Transport Template",
				"code": "TEST-CFS-WHS",
				"description": "Test CFS WHS",
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
		tpl.insert(ignore_permissions=True)

		validate_against_transport_template(
			template_name=tpl.name,
			load_type=ftl,
			vehicle_type=None,
		)

		with self.assertRaises(frappe.ValidationError):
			validate_against_transport_template(
				template_name=tpl.name,
				load_type=fcl,
				vehicle_type=None,
			)

	def test_template_save_rejects_mixed_lane_allowed_types(self):
		ftl = self._ensure_load_type("FTL", transport=1, non_container=1)
		fcl = self._ensure_load_type("FCL", transport=1, container=1, sea=1)

		doc = frappe.get_doc(
			{
				"doctype": "Transport Template",
				"code": "TEST-MIXED",
				"description": "Mixed",
				"legs": [
					{
						"facility_type_from": "Container Yard",
						"facility_type_to": "Storage Facility",
					}
				],
				"allowed_load_types": [{"load_type": ftl}, {"load_type": fcl}],
			}
		)
		with self.assertRaises(frappe.ValidationError):
			validate_template_allowed_load_types_vs_legs(doc)

	def test_get_allowed_load_types_from_doc(self):
		doc = frappe._dict(
			allowed_load_types=[
				frappe._dict(load_type="FTL"),
				frappe._dict(load_type="LTL"),
				frappe._dict(load_type="FTL"),
			]
		)
		self.assertEqual(get_allowed_load_types_from_doc(doc), ["FTL", "LTL"])
