# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from logistics.time_sensitive.change_request import (
	attach_case_linked_services_to_change_request,
	create_change_request_from_case,
	resolve_main_job_for_case,
)


class UnitTestChangeRequestFromCase(UnitTestCase):
	def test_resolve_throws_when_no_completed_job(self):
		case = frappe._dict(name="TSC-1", main_service_type=None, main_service=None)
		with patch(
			"logistics.time_sensitive.change_request.get_case_linked_services",
			return_value=[frappe._dict(name="IJ-1", service_type="Transport")],
		), patch(
			"logistics.time_sensitive.change_request.get_usages_for_linked_service",
			return_value=[
				{"used_on_doctype": "Transport Order", "used_on_name": "TRO-1"},
			],
		):
			with self.assertRaises(frappe.ValidationError) as ctx:
				resolve_main_job_for_case(case)
			self.assertIn("complete the main job", str(ctx.exception).lower())

	def test_resolve_completed_transport_job_from_usages(self):
		case = frappe._dict(name="TSC-1", main_service_type=None, main_service=None)
		with patch(
			"logistics.time_sensitive.change_request.get_case_linked_services",
			return_value=[frappe._dict(name="IJ-1", service_type="Transport")],
		), patch(
			"logistics.time_sensitive.change_request.get_usages_for_linked_service",
			return_value=[
				{"used_on_doctype": "Transport Order", "used_on_name": "TRO-1"},
				{"used_on_doctype": "Transport Job", "used_on_name": "TJ-1"},
			],
		), patch(
			"logistics.time_sensitive.change_request._meta_has",
			side_effect=lambda dt, fn: fn == "status",
		), patch(
			"logistics.time_sensitive.change_request.frappe.db.get_value",
			return_value="Completed",
		):
			self.assertEqual(resolve_main_job_for_case(case), ("Transport Job", "TJ-1"))

	def test_create_change_request_from_case_attaches_linked_services(self):
		case = frappe._dict(
			name="TSC-1",
			sales_quote="SQ-1",
			main_service_type=None,
			main_service=None,
		)
		ls = [frappe._dict(name="IJ-1", service_type="Transport")]
		with patch(
			"logistics.time_sensitive.change_request.frappe.db.exists",
			return_value=True,
		), patch(
			"logistics.time_sensitive.change_request.frappe.get_doc",
			return_value=case,
		), patch(
			"logistics.time_sensitive.change_request.frappe.has_permission",
			return_value=True,
		), patch(
			"logistics.time_sensitive.change_request.resolve_main_job_for_case",
			return_value=("Transport Job", "TJ-1"),
		), patch(
			"logistics.pricing_center.doctype.change_request.change_request.create_change_request",
			return_value="CR-1",
		) as create_cr, patch(
			"logistics.time_sensitive.change_request.get_case_linked_services",
			return_value=ls,
		), patch(
			"logistics.utils.linked_service_usage.record_usages_for_linked_services",
			return_value={"IJ-1": "IJ-1"},
		) as record:
			name = create_change_request_from_case("TSC-1", reason="Actuals")
			self.assertEqual(name, "CR-1")
			create_cr.assert_called_once()
			self.assertEqual(create_cr.call_args[0][0], "Transport Job")
			self.assertEqual(create_cr.call_args[0][1], "TJ-1")
			record.assert_called_once()
			self.assertEqual(record.call_args[0][0], ["IJ-1"])
			self.assertEqual(record.call_args[0][1], "Change Request")
			self.assertEqual(record.call_args[0][2], "CR-1")

	def test_attach_skips_when_no_services(self):
		case = frappe._dict(name="TSC-1", sales_quote="SQ-1")
		with patch(
			"logistics.time_sensitive.change_request.get_case_linked_services",
			return_value=[],
		), patch(
			"logistics.utils.linked_service_usage.record_usages_for_linked_services"
		) as record:
			attach_case_linked_services_to_change_request("CR-1", case)
			record.assert_not_called()
