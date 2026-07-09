# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from logistics.utils.internal_job_creation_eligibility import (
	_quote_has_matching_linked_service_row,
	apply_eligibility_to_preview_flags,
	charges_exist_for_service,
	evaluate_internal_job_creation_eligibility,
	has_matching_internal_job_setup,
	internal_job_matches_charges,
)
from logistics.utils.module_integration import _require_internal_job_eligible_for_parent_row
from logistics.utils.internal_job_persistence import sync_internal_job_details_to_internal_jobs
from logistics.utils.linked_service_compat import linked_service_doctype


class TestInternalJobCreationEligibility(FrappeTestCase):
	def test_charges_exist_from_sales_quote(self):
		with patch(
			"logistics.utils.internal_job_creation_eligibility.frappe.db.exists",
			return_value=True,
		):
			with patch(
				"logistics.utils.internal_job_creation_eligibility.sales_quote_has_service_charges",
				return_value=True,
			):
				self.assertTrue(charges_exist_for_service("SQ-1", None, "Transport"))

	def test_charges_exist_from_programme_parent(self):
		parent = MagicMock(doctype="Docket", sales_quote=None)
		with patch(
			"logistics.utils.internal_job_creation_eligibility.sales_quote_has_service_charges",
			return_value=False,
		):
			with patch(
				"logistics.utils.internal_job_creation_eligibility._programme_charges_for_service",
				return_value=[MagicMock()],
			):
				self.assertTrue(charges_exist_for_service(None, parent, "Air"))

	def test_no_charges_not_eligible(self):
		parent = MagicMock(doctype="Docket", sales_quote=None, internal_jobs=[])
		ij_row = MagicMock(service_type="Transport", internal_job="IJ-1")
		with patch(
			"logistics.utils.internal_job_creation_eligibility.charges_exist_for_service",
			return_value=False,
		):
			with patch(
				"logistics.utils.internal_job_creation_eligibility.has_matching_internal_job_setup",
				return_value=False,
			):
				result = evaluate_internal_job_creation_eligibility(
					parent_doc=parent, ij_row=ij_row, service_type_label="Transport"
				)
		self.assertFalse(result["eligible"])
		self.assertFalse(result["has_charges"])
		self.assertIn("charge lines", (result["message"] or "").lower())

	def test_charges_only_not_eligible(self):
		parent = MagicMock(doctype="Docket", sales_quote="SQ-1")
		ij_row = MagicMock(service_type="Transport", internal_job="IJ-1")
		with patch(
			"logistics.utils.internal_job_creation_eligibility.charges_exist_for_service",
			return_value=True,
		):
			with patch(
				"logistics.utils.internal_job_creation_eligibility.has_matching_internal_job_setup",
				return_value=False,
			):
				result = evaluate_internal_job_creation_eligibility(
					sales_quote="SQ-1",
					parent_doc=parent,
					ij_row=ij_row,
					service_type_label="Transport",
				)
		self.assertFalse(result["eligible"])
		self.assertTrue(result["has_charges"])
		self.assertFalse(result["has_matching_ij"])

	def test_both_present_eligible(self):
		parent = MagicMock(doctype="Docket", sales_quote="SQ-1")
		ij_row = MagicMock(service_type="Transport", internal_job="IJ-1")
		with patch(
			"logistics.utils.internal_job_creation_eligibility.charges_exist_for_service",
			return_value=True,
		):
			with patch(
				"logistics.utils.internal_job_creation_eligibility.has_matching_internal_job_setup",
				return_value=True,
			):
				result = evaluate_internal_job_creation_eligibility(
					sales_quote="SQ-1",
					parent_doc=parent,
					ij_row=ij_row,
					service_type_label="Transport",
				)
		self.assertTrue(result["eligible"])
		self.assertIsNone(result["message"])

	@patch("logistics.utils.internal_job_creation_eligibility.frappe.db.exists", return_value=True)
	def test_internal_job_matches_charges_empty_params_with_programme_rows(self, _exists):
		parent = MagicMock(doctype="Docket", sales_quote=None)
		ij_row = MagicMock(service_type="Transport")
		with patch(
			"logistics.utils.internal_job_creation_eligibility.extract_service_scoped_quote_parameters",
			return_value={},
		):
			with patch(
				"logistics.utils.internal_job_creation_eligibility.any_sales_quote_charge_matches_internal_job_detail_params",
				return_value=False,
			):
				with patch(
					"logistics.utils.internal_job_creation_eligibility._programme_charges_for_service",
					return_value=[MagicMock()],
				):
					self.assertTrue(
						internal_job_matches_charges("SQ-1", parent, ij_row, "Transport")
					)

	@patch("logistics.utils.internal_job_creation_eligibility.frappe.db.exists", return_value=True)
	@patch("logistics.utils.internal_job_creation_eligibility.frappe.get_meta")
	@patch("logistics.utils.internal_job_creation_eligibility.frappe.get_cached_doc")
	def test_has_matching_setup_requires_parent_row(self, mock_doc, mock_meta, _exists):
		mock_meta.return_value.get_field.return_value = None
		parent = MagicMock(doctype="Docket")
		parent.internal_jobs = [MagicMock(service_type="Transport", internal_job="IJ-1")]
		ij_row = parent.internal_jobs[0]
		with patch(
			"logistics.utils.internal_job_creation_eligibility.internal_job_matches_charges",
			return_value=True,
		):
			self.assertTrue(
				has_matching_internal_job_setup(None, parent, ij_row, "Transport")
			)

	@patch("logistics.utils.internal_job_creation_eligibility.frappe.db.exists", return_value=True)
	@patch("logistics.utils.internal_job_creation_eligibility.frappe.get_meta")
	@patch("logistics.utils.internal_job_creation_eligibility.frappe.get_cached_doc")
	def test_has_matching_setup_accepts_lifecycle_job_row_on_special_project(
		self, mock_cached_doc, mock_meta, _exists
	):
		mock_meta.return_value.get_field.return_value = MagicMock()
		mock_cached_doc.return_value.get.return_value = []
		ij_row = MagicMock(service_type="Transport", name="lj-transport-1", vehicle_type="10W-WV")
		parent = MagicMock(doctype="Special Project", sales_quote="SQ-1")
		parent.lifecycle_jobs = [ij_row]
		with patch(
			"logistics.utils.internal_job_creation_eligibility.internal_job_matches_charges",
			return_value=True,
		):
			self.assertTrue(has_matching_internal_job_setup("SQ-1", parent, ij_row, "Transport"))

	@patch("logistics.utils.internal_job_creation_eligibility.frappe.db.exists", return_value=False)
	def test_evaluate_eligible_for_special_project_lifecycle_row(self, _exists):
		ij_row = frappe._dict(
			service_type="Transport",
			name="lj-transport-1",
			vehicle_type="10W-WV",
		)
		parent = frappe._dict(
			doctype="Special Project",
			sales_quote=None,
			charges=[
				frappe._dict(service_type="Transport", vehicle_type="10W-WV"),
			],
			lifecycle_jobs=[ij_row],
		)
		result = evaluate_internal_job_creation_eligibility(
			parent_doc=parent,
			ij_row=ij_row,
			service_type_label="Transport",
		)
		self.assertTrue(result["eligible"])
		self.assertIsNone(result["message"])

	def test_eligibility_message_uses_services_tab_for_special_project(self):
		parent = MagicMock(doctype="Special Project")
		ij_row = MagicMock(service_type="Transport", name="lj-1")
		with patch(
			"logistics.utils.internal_job_creation_eligibility.charges_exist_for_service",
			return_value=True,
		):
			with patch(
				"logistics.utils.internal_job_creation_eligibility.has_matching_internal_job_setup",
				return_value=False,
			):
				result = evaluate_internal_job_creation_eligibility(
					parent_doc=parent,
					ij_row=ij_row,
					service_type_label="Transport",
				)
		msg = (result.get("message") or "").lower()
		self.assertIn("services", msg)
		self.assertNotIn("internal jobs tab", msg)

	def test_parent_ij_fieldname_uses_special_project_services(self):
		from logistics.utils.internal_job_creation_eligibility import _parent_ij_fieldname

		self.assertEqual(_parent_ij_fieldname("Special Project"), "special_project_services")
		self.assertEqual(_parent_ij_fieldname("Exhibit"), "lifecycle_jobs")
		self.assertEqual(_parent_ij_fieldname("MICE Project"), "linked_services")
		self.assertEqual(_parent_ij_fieldname("Docket"), "internal_jobs")

	@patch("logistics.utils.internal_job_creation_eligibility.frappe.db.exists", return_value=True)
	@patch("logistics.utils.internal_job_creation_eligibility.frappe.get_meta")
	@patch("logistics.utils.internal_job_creation_eligibility.frappe.get_cached_doc")
	def test_has_matching_setup_accepts_internal_job_row_on_mice_project(
		self, mock_cached_doc, mock_meta, _exists
	):
		mock_meta.return_value.get_field.return_value = None
		ij_row = MagicMock(service_type="MICE", name="ij-mice-1")
		parent = MagicMock(doctype="MICE Project", sales_quote="SQ-1")
		parent.linked_services = [ij_row]
		with patch(
			"logistics.utils.internal_job_creation_eligibility.internal_job_matches_charges",
			return_value=True,
		):
			self.assertTrue(has_matching_internal_job_setup("SQ-1", parent, ij_row, "MICE"))

	@patch("logistics.utils.internal_job_creation_eligibility.frappe.db.exists", return_value=False)
	def test_evaluate_eligible_for_mice_project_internal_job_row(self, _exists):
		ij_row = frappe._dict(service_type="MICE", name="ij-mice-1")
		parent = frappe._dict(
			doctype="MICE Project",
			sales_quote=None,
			linked_services=[ij_row],
		)
		with patch(
			"logistics.utils.internal_job_creation_eligibility.charges_exist_for_service",
			return_value=True,
		):
			with patch(
				"logistics.utils.internal_job_creation_eligibility.has_matching_internal_job_setup",
				return_value=True,
			):
				result = evaluate_internal_job_creation_eligibility(
					parent_doc=parent,
					ij_row=ij_row,
					service_type_label="MICE",
				)
		self.assertTrue(result["eligible"])
		self.assertIsNone(result["message"])

	def test_eligibility_message_uses_services_tab_for_mice_project(self):
		parent = MagicMock(doctype="MICE Project")
		ij_row = MagicMock(service_type="Air", name="ij-air-1")
		with patch(
			"logistics.utils.internal_job_creation_eligibility.charges_exist_for_service",
			return_value=True,
		):
			with patch(
				"logistics.utils.internal_job_creation_eligibility.has_matching_internal_job_setup",
				return_value=False,
			):
				result = evaluate_internal_job_creation_eligibility(
					parent_doc=parent,
					ij_row=ij_row,
					service_type_label="Air",
				)
		msg = (result.get("message") or "").lower()
		self.assertIn("services", msg)
		self.assertNotIn("lifecycle", msg)

	def test_quote_has_matching_linked_service_row_uses_virtual_grid(self):
		"""Regression: eligibility must not read ``sq_doc.get('linked_services')`` (always empty after save)."""
		if not frappe.db.exists("DocType", "Sales Quote"):
			self.skipTest("Sales Quote not installed")
		if not frappe.db.exists("DocType", linked_service_doctype()):
			self.skipTest("Linked Service not installed")

		sq = frappe.new_doc("Sales Quote")
		sq.quotation_type = "Project"
		sq.main_service = "Special Project"
		sq.naming_series = "PQ.#####"
		sq.project_name = "SQ Eligibility Virtual LS"
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
			reloaded = frappe.get_cached_doc("Sales Quote", sq.name)
			self.assertEqual(reloaded.get("linked_services") or [], [])
			self.assertEqual(len(reloaded.linked_services), 1)
			ls_name = reloaded.linked_services[0].get("linked_service")
			ls_doc = frappe.get_doc(linked_service_doctype(), ls_name)
			self.assertTrue(
				_quote_has_matching_linked_service_row(sq.name, ls_doc, "Transport")
			)
		finally:
			frappe.delete_doc("Sales Quote", sq.name, force=True, ignore_permissions=True)

	def test_apply_eligibility_to_preview_flags_uses_virtual_linked_services(self):
		"""Preview must use linked-service eligibility for Air/Sea Shipment sources."""
		if not frappe.db.exists("DocType", "Sales Quote"):
			self.skipTest("Sales Quote not installed")
		if not frappe.db.exists("DocType", linked_service_doctype()):
			self.skipTest("Linked Service not installed")

		sq = frappe.new_doc("Sales Quote")
		sq.quotation_type = "Project"
		sq.main_service = "Special Project"
		sq.naming_series = "PQ.#####"
		sq.project_name = "SQ Preview Virtual LS"
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
			reloaded = frappe.get_cached_doc("Sales Quote", sq.name)
			ls_name = reloaded.linked_services[0].get("linked_service")
			charge_row = frappe._dict(
				service_type="Transport",
				linked_service=ls_name,
				charge_scope="Linked",
			)
			preview = apply_eligibility_to_preview_flags(
				{"creatable": True},
				sales_quote=reloaded.name,
				parent_doc=reloaded,
				ij_row=charge_row,
				service_type_label="Transport",
				uses_linked_charge_create=True,
			)
			self.assertTrue(preview.get("creatable"), msg=preview.get("not_creatable_message"))
			self.assertIsNone(preview.get("not_creatable_message"))
		finally:
			frappe.delete_doc("Sales Quote", sq.name, force=True, ignore_permissions=True)

	def test_require_internal_job_eligible_for_parent_row_uses_virtual_linked_services(self):
		"""Create-time validation must use linked-service eligibility for freight shipments."""
		if not frappe.db.exists("DocType", "Sales Quote"):
			self.skipTest("Sales Quote not installed")
		if not frappe.db.exists("DocType", linked_service_doctype()):
			self.skipTest("Linked Service not installed")
		if not frappe.db.exists("DocType", "Air Shipment"):
			self.skipTest("Air Shipment not installed")

		sq = frappe.new_doc("Sales Quote")
		sq.quotation_type = "Project"
		sq.main_service = "Special Project"
		sq.naming_series = "PQ.#####"
		sq.project_name = "SQ Create Eligibility LS"
		sq.customer = frappe.db.get_value("Customer", {}, "name")
		if not sq.customer:
			self.skipTest("No Customer in system")
		sq.date = frappe.utils.today()
		sq.valid_until = frappe.utils.add_days(frappe.utils.today(), 30)
		sq.flags.ignore_mandatory = True
		sq.insert(ignore_permissions=True)
		asp = None
		try:
			sq.append("linked_services", {"service_type": "Transport"})
			sq.flags._linked_services_from_form = True
			sync_internal_job_details_to_internal_jobs(sq)
			reloaded_sq = frappe.get_cached_doc("Sales Quote", sq.name)
			ls_name = reloaded_sq.linked_services[0].get("linked_service")
			charge_row = frappe._dict(
				service_type="Transport",
				linked_service=ls_name,
				charge_scope="Linked",
			)
			asp = frappe.new_doc("Air Shipment")
			asp.sales_quote = sq.name
			asp.flags.ignore_mandatory = True
			asp.insert(ignore_permissions=True)
			asp.append(
				"charges",
				{
					"service_type": "Transport",
					"linked_service": ls_name,
					"charge_scope": "Linked",
				},
			)
			asp.flags.ignore_mandatory = True
			asp.save(ignore_permissions=True)
			_require_internal_job_eligible_for_parent_row(asp, charge_row, "Transport Order")
		finally:
			if asp and frappe.db.exists("Air Shipment", asp.name):
				frappe.delete_doc("Air Shipment", asp.name, force=True, ignore_permissions=True)
			frappe.delete_doc("Sales Quote", sq.name, force=True, ignore_permissions=True)
