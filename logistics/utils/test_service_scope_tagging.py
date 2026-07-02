# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Tests for Sales Quote charge scope / linked service tagging."""

from __future__ import unicode_literals

import frappe
from frappe.tests import IntegrationTestCase

from logistics.utils.internal_job_persistence import sync_internal_job_details_to_internal_jobs
from logistics.utils.linked_service_compat import linked_service_doctype


class TestServiceScopeTagging(IntegrationTestCase):
	def test_linked_charge_scope_requires_linked_service(self):
		sq = frappe.new_doc("Sales Quote")
		sq.name = "OOQ-TEST-SCOPE-002"
		sq.append("charges", {"service_type": "Transport", "charge_scope": "Linked"})
		with self.assertRaises(frappe.ValidationError):
			sq.validate_linked_service_charge_tagging()

	def test_linked_charge_rejects_service_type_mismatch(self):
		if not frappe.db.exists("DocType", "Sales Quote"):
			self.skipTest("Sales Quote not installed")
		if not frappe.db.exists("DocType", linked_service_doctype()):
			self.skipTest("Linked Service not installed")

		sq = frappe.new_doc("Sales Quote")
		sq.quotation_type = "Project"
		sq.main_service = "Special Project"
		sq.naming_series = "PQ.#####"
		sq.project_name = "SQ Scope Mismatch Test"
		sq.customer = frappe.db.get_value("Customer", {}, "name")
		if not sq.customer:
			self.skipTest("No Customer in system")
		sq.date = frappe.utils.today()
		sq.valid_until = frappe.utils.add_days(frappe.utils.today(), 30)
		sq.flags.ignore_mandatory = True
		sq.insert(ignore_permissions=True)
		try:
			sq.append("linked_services", {"service_type": "Transport"})
			sq.flags._linked_services_from_form = True
			sync_internal_job_details_to_internal_jobs(sq)
			ls_name = frappe.get_all(
				linked_service_doctype(),
				filters={
					"parent_booking_type": "Sales Quote",
					"parent_booking_name": sq.name,
				},
				pluck="name",
				limit=1,
			)[0]
			sq.append(
				"charges",
				{
					"service_type": "Air",
					"charge_scope": "Linked",
					"linked_service": ls_name,
				},
			)
			with self.assertRaises(frappe.ValidationError):
				sq.validate_linked_service_charge_tagging()
		finally:
			frappe.delete_doc("Sales Quote", sq.name, force=True, ignore_permissions=True)
