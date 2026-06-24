# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

from unittest.mock import MagicMock, patch

from frappe.tests.utils import FrappeTestCase

from logistics.utils.internal_job_from_source import (
	INTERNAL_JOB_QUOTE_PARAMETER_MISMATCH_MESSAGE,
	internal_job_detail_params_match_quotation,
	validate_internal_job_detail_params_match_quotation,
)
from logistics.utils.sales_quote_charge_parameters import (
	any_sales_quote_charge_matches_internal_job_detail_params,
	extract_service_scoped_quote_parameters,
	sales_quote_charge_row_matches_internal_job_detail_params,
)
from logistics.utils.internal_job_persistence import (
	INTERNAL_JOB_DETAIL_PARENTS,
	internal_job_detail_fieldname,
)


class TestSalesQuoteChargeParameterMatch(FrappeTestCase):
	def test_row_match_blank_charge_field_is_wildcard(self):
		charge = MagicMock(
			transport_template="TPL-1",
			vehicle_type="",
			location_from="A",
			location_to="B",
		)
		ij_params = {"transport_template": "TPL-1", "vehicle_type": "20FT", "location_from": "A", "location_to": "B"}
		self.assertTrue(sales_quote_charge_row_matches_internal_job_detail_params(charge, ij_params))

	def test_row_mismatch_on_set_field(self):
		charge = MagicMock(
			transport_template="TPL-1",
			vehicle_type="20FT",
			location_from="A",
			location_to="B",
		)
		ij_params = {"transport_template": "TPL-2", "vehicle_type": "20FT"}
		self.assertFalse(sales_quote_charge_row_matches_internal_job_detail_params(charge, ij_params))

	def test_empty_ij_params_always_match(self):
		charge = MagicMock(transport_template="TPL-1")
		self.assertTrue(sales_quote_charge_row_matches_internal_job_detail_params(charge, {}))

	def test_wildcard_fields_for_param_match(self):
		from logistics.utils.sales_quote_charge_parameters import (
			SALES_QUOTE_CHARGE_PARAMETER_FIELDS,
			collect_wildcard_fields_for_param_set,
			wildcard_fields_for_param_match,
		)

		# A real Sales Quote Charge row exposes every parameter field. Mirror that with a dict
		# so unset fields are blank (None), not auto-generated Mock children.
		charge = {fn: "" for fn in SALES_QUOTE_CHARGE_PARAMETER_FIELDS}
		charge.update(
			{
				"transport_template": "TPL-1",
				"vehicle_type": "",
				"location_from": "A",
				"location_to": "B",
			}
		)
		params = {"transport_template": "TPL-1", "vehicle_type": "20FT"}
		self.assertEqual(wildcard_fields_for_param_match(charge, params), ["vehicle_type"])

		sq = MagicMock()
		sq.get.return_value = [MagicMock(service_type="Transport", **charge)]
		with patch("logistics.utils.sales_quote_charge_parameters.frappe.db.exists", return_value=True):
			with patch("logistics.utils.sales_quote_charge_parameters.frappe.get_doc", return_value=sq):
				wildcards = collect_wildcard_fields_for_param_set("SQ-1", "Transport", params)
		self.assertEqual(wildcards, ["vehicle_type"])

	@patch("logistics.utils.sales_quote_charge_parameters.frappe.db.exists", return_value=True)
	def test_any_match_requires_service_type_row(self, _exists):
		from logistics.utils.sales_quote_charge_parameters import SALES_QUOTE_CHARGE_PARAMETER_FIELDS

		blank_charge = {fn: "" for fn in SALES_QUOTE_CHARGE_PARAMETER_FIELDS}
		transport_row = MagicMock(
			service_type="Transport",
			**{**blank_charge, "transport_template": "TPL-1", "vehicle_type": "20FT"},
		)
		customs_row = MagicMock(
			service_type="Customs",
			**{**blank_charge, "customs_authority": "CA-1"},
		)
		sq = MagicMock()
		sq.get.return_value = [transport_row, customs_row]
		# Blank-by-default IJ row so only the explicitly set service-scoped fields participate.
		# customs_authority is set to a value that the customs charge row does NOT carry, so the
		# Customs scope match fails while the Transport scope match succeeds.
		blank_ij = {fn: "" for fn in SALES_QUOTE_CHARGE_PARAMETER_FIELDS}
		ij_row = MagicMock(
			**{
				**blank_ij,
				"transport_template": "TPL-1",
				"vehicle_type": "20FT",
				"customs_authority": "OTHER-AUTHORITY",
			},
		)
		with patch("logistics.utils.sales_quote_charge_parameters.frappe.get_doc", return_value=sq):
			self.assertTrue(
				any_sales_quote_charge_matches_internal_job_detail_params("SQ-1", ij_row, "Transport")
			)
			self.assertFalse(
				any_sales_quote_charge_matches_internal_job_detail_params("SQ-1", ij_row, "Customs")
			)

	@patch(
		"logistics.utils.internal_job_from_source.resolve_internal_job_detail_row_for_create",
		return_value=(MagicMock(transport_template="TPL-X"), 1),
	)
	def test_validate_throws_on_mismatch(self, _resolve):
		import frappe

		parent = MagicMock(sales_quote="SQ-1")
		with patch(
			"logistics.utils.internal_job_creation_eligibility.require_internal_job_creation_eligible",
			side_effect=frappe.ValidationError("blocked"),
		):
			with self.assertRaises(frappe.ValidationError):
				validate_internal_job_detail_params_match_quotation(parent, "Transport Order", 1)

	def test_internal_job_detail_params_match_quotation_skips_without_row(self):
		parent = MagicMock(sales_quote="SQ-1")
		self.assertTrue(internal_job_detail_params_match_quotation(parent, "Transport Order", None))

	@patch("logistics.utils.sales_quote_charge_parameters.frappe.db.exists", return_value=True)
	def test_customs_match_ignores_hidden_air_sea_fields_on_row(self, _exists):
		sq = MagicMock()
		sq.get.return_value = [
			MagicMock(
				service_type="Customs",
				customs_authority="BOC",
				declaration_type="Import",
				customs_broker="ABC Brokerage",
				customs_charge_category="Customs Clearance",
				air_house_type="Standard House",
				direction="Import",
			),
		]
		ij_row = MagicMock(
			service_type="Customs",
			customs_authority="BOC",
			declaration_type="Import",
			customs_broker="ABC Brokerage",
			customs_charge_category="Customs Clearance",
			air_house_type="Other House",
			sea_house_type="Other House",
			direction="Export",
		)
		with patch("logistics.utils.sales_quote_charge_parameters.frappe.get_doc", return_value=sq):
			self.assertTrue(
				any_sales_quote_charge_matches_internal_job_detail_params("SQ-1", ij_row, "Customs")
			)
		scoped = extract_service_scoped_quote_parameters(ij_row, "Customs")
		self.assertEqual(
			set(scoped.keys()),
			{"customs_authority", "declaration_type", "customs_broker", "customs_charge_category"},
		)

	@patch("logistics.utils.sales_quote_charge_parameters.frappe.db.exists", return_value=True)
	def test_customs_mismatch_on_user_visible_field(self, _exists):
		sq = MagicMock()
		sq.get.return_value = [
			MagicMock(
				service_type="Customs",
				customs_authority="BOC",
				declaration_type="Import",
				customs_broker="ABC Brokerage",
				customs_charge_category="Customs Clearance",
			),
		]
		ij_row = MagicMock(
			service_type="Customs",
			customs_authority="BOC",
			declaration_type="Export",
			customs_broker="ABC Brokerage",
			customs_charge_category="Customs Clearance",
		)
		with patch("logistics.utils.sales_quote_charge_parameters.frappe.get_doc", return_value=sq):
			self.assertFalse(
				any_sales_quote_charge_matches_internal_job_detail_params("SQ-1", ij_row, "Customs")
			)


class TestInternalJobDetailParentRegistry(FrappeTestCase):
	"""Sanity check that the persistence module recognises every booking with an IJD child."""

	EXPECTED_DOCTYPES = frozenset({
		"Sea Booking", "Air Booking",
		"Sea Shipment", "Air Shipment",
		"Transport Order", "Transport Job",
		"Declaration", "Declaration Order",
		"Warehouse Job", "Inbound Order", "Release Order",
		"General Job", "Project Job",
		"MICE Job", "MICE Project", "Docket",
	})

	def test_all_expected_doctypes_are_registered(self):
		self.assertEqual(set(INTERNAL_JOB_DETAIL_PARENTS.keys()), self.EXPECTED_DOCTYPES)

	def test_field_lookup_handles_mice_alias(self):
		self.assertEqual(internal_job_detail_fieldname("MICE Project"), "internal_jobs")
		self.assertEqual(internal_job_detail_fieldname("Docket"), "internal_jobs")
		self.assertEqual(internal_job_detail_fieldname("Special Project"), "lifecycle_jobs")
		self.assertEqual(internal_job_detail_fieldname("Sea Booking"), "internal_job_details")
		self.assertIsNone(internal_job_detail_fieldname("Customer"))
