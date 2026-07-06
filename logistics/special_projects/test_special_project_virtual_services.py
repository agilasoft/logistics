# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Tests for Special Project virtual ``special_project_services`` grid."""

from __future__ import annotations

import frappe
from frappe.tests import IntegrationTestCase

from logistics.special_projects.doctype.special_project.special_project import (
	get_cost_revenue_summary,
)
from logistics.special_projects.special_project_service_persistence import (
	_special_project_service_names_from_db,
	sync_special_project_services_to_documents,
)


from logistics.special_projects.test_special_project_helpers import (
	new_special_project_for_test,
)


class TestSpecialProjectVirtualServices(IntegrationTestCase):
	def _cleanup_special_project(self, sp_name: str) -> None:
		if not sp_name or not frappe.db.exists("Special Project", sp_name):
			return
		project = frappe.db.get_value("Special Project", sp_name, "project")
		frappe.delete_doc("Special Project", sp_name, force=True, ignore_permissions=True)
		if project and frappe.db.exists("Project", project):
			try:
				frappe.delete_doc("Project", project, force=True, ignore_permissions=True)
			except Exception:
				pass

	def _minimal_special_project(self, project_name: str):
		sp = new_special_project_for_test(project_name)
		if not sp:
			self.skipTest("Company, Customer, and Cost Center required")
		sp.status = "Draft"
		sp.flags.ignore_mandatory = True
		sp.insert(ignore_permissions=True)
		return sp

	def test_sync_creates_special_project_service_document(self):
		sp = self._minimal_special_project("SP Virtual Services Create")
		try:
			stage = frappe.db.get_value("Lifecycle Stage", {}, "name")
			if not stage:
				self.skipTest("no lifecycle stage")
			sp.append(
				"special_project_services",
				{"service_type": "Transport", "lifecycle_stage": stage},
			)
			sp.flags._special_project_services_from_form = True
			sync_special_project_services_to_documents(sp)
			names = _special_project_service_names_from_db(sp.name)
			self.assertEqual(len(names), 1)
			service = frappe.get_doc("Special Project Service", list(names)[0])
			self.assertEqual(service.service_type, "Transport")
			self.assertEqual(service.parent_booking_type, "Special Project")
			self.assertEqual(service.parent_booking_name, sp.name)
		finally:
			self._cleanup_special_project(sp.name)

	def test_save_with_virtual_services_reloads_grid(self):
		sp = self._minimal_special_project("SP Virtual Services Save")
		try:
			stage = frappe.db.get_value("Lifecycle Stage", {}, "name")
			if not stage:
				self.skipTest("no lifecycle stage")
			doc = frappe.get_doc("Special Project", sp.name)
			doc.append(
				"special_project_services",
				{"service_type": "Air", "lifecycle_stage": stage},
			)
			doc.flags.ignore_mandatory = True
			doc.save(ignore_permissions=True)
			reloaded = frappe.get_doc("Special Project", sp.name)
			self.assertIsInstance(reloaded.special_project_services, list)
			self.assertEqual(len(reloaded.special_project_services), 1)
			self.assertEqual(reloaded.special_project_services[0].get("service_type"), "Air")
		finally:
			self._cleanup_special_project(sp.name)

	def test_clearing_grid_deletes_owned_services(self):
		sp = self._minimal_special_project("SP Virtual Services Delete")
		try:
			stage = frappe.db.get_value("Lifecycle Stage", {}, "name")
			if not stage:
				self.skipTest("no lifecycle stage")
			doc = frappe.get_doc("Special Project", sp.name)
			doc.append(
				"special_project_services",
				{"service_type": "Sea", "lifecycle_stage": stage},
			)
			doc.flags.ignore_mandatory = True
			doc.save(ignore_permissions=True)
			self.assertEqual(len(_special_project_service_names_from_db(sp.name)), 1)

			doc2 = frappe.get_doc("Special Project", sp.name)
			doc2.__dict__["special_project_services"] = []
			doc2.flags._special_project_services_from_form = True
			doc2.flags.ignore_mandatory = True
			doc2.save(ignore_permissions=True)

			self.assertEqual(len(_special_project_service_names_from_db(sp.name)), 0)
			reloaded = frappe.get_doc("Special Project", sp.name)
			self.assertEqual(len(reloaded.special_project_services), 0)
		finally:
			self._cleanup_special_project(sp.name)

	def test_cost_revenue_summary_handles_virtual_service_grid_rows(self):
		sp = self._minimal_special_project("SP Virtual Services Cost Summary")
		try:
			stage = frappe.db.get_value("Lifecycle Stage", {}, "name")
			if not stage:
				self.skipTest("no lifecycle stage")
			doc = frappe.get_doc("Special Project", sp.name)
			doc.append(
				"special_project_services",
				{
					"service_type": "Transport",
					"lifecycle_stage": stage,
					"planned_cost": 100,
					"planned_revenue": 250,
				},
			)
			doc.flags.ignore_mandatory = True
			doc.save(ignore_permissions=True)

			html = get_cost_revenue_summary(sp.name)
			self.assertIn("Planned Cost", html)
			self.assertIn("Planned Revenue", html)
			self.assertNotIn("AttributeError", html)
		finally:
			self._cleanup_special_project(sp.name)

	def test_save_heals_charge_service_line_temp_grid_names(self):
		"""Desk save must not fail when charges reference unsaved virtual service row names."""
		sp = self._minimal_special_project("SP Virtual Services Charge Link")
		try:
			stage = frappe.db.get_value("Lifecycle Stage", {}, "name")
			if not stage:
				self.skipTest("no lifecycle stage")
			doc = frappe.get_doc("Special Project", sp.name)
			temp_name = "new-special-project-service-detail-testrow"
			doc.append(
				"special_project_services",
				{
					"name": temp_name,
					"service_type": "Air",
					"lifecycle_stage": stage,
				},
			)
			doc.append(
				"charges",
				{
					"service_type": "Air",
					"description": "Air freight",
					"estimated_cost": 100,
					"special_project_service_line": temp_name,
				},
			)
			doc.flags._special_project_services_from_form = True
			doc.flags.ignore_mandatory = True
			doc.save(ignore_permissions=True)

			reloaded = frappe.get_doc("Special Project", sp.name)
			self.assertEqual(len(reloaded.special_project_services), 1)
			service_name = reloaded.special_project_services[0].get("special_project_service")
			self.assertTrue(service_name)
			self.assertFalse(service_name.startswith("new-"))
			self.assertEqual(len(reloaded.charges), 1)
			self.assertEqual(reloaded.charges[0].special_project_service_line, service_name)
		finally:
			self._cleanup_special_project(sp.name)
