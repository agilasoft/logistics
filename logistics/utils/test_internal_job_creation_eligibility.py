# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase

from logistics.utils.internal_job_creation_eligibility import (
	charges_exist_for_service,
	evaluate_internal_job_creation_eligibility,
	has_matching_internal_job_setup,
	internal_job_matches_charges,
)


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

	def test_eligibility_message_uses_lifecycle_tab_for_special_project(self):
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
		self.assertIn("lifecycle", msg)
		self.assertNotIn("internal jobs tab", msg)

	def test_parent_ij_fieldname_uses_lifecycle_jobs_on_special_project(self):
		from logistics.utils.internal_job_creation_eligibility import _parent_ij_fieldname

		self.assertEqual(_parent_ij_fieldname("Special Project"), "lifecycle_jobs")
		self.assertEqual(_parent_ij_fieldname("Exhibit"), "lifecycle_jobs")
