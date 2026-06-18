# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Tests for the per-scope alignment of the Create > Internal Job charge selection.

The Create flow used to copy every parent charge whose ``service_type`` matched the new internal
job's service. After alignment with the per-scope Sales-Quote-to-booking extractor, the create
helpers also filter parent charges by the Internal Job Detail row's parameters: only rows whose
parameters match the IJ row's service-scoped parameters (with the same blank-as-wildcard semantics
used by ``sales_quote_charge_row_matches_internal_job_detail_params``) make it onto the new IJ.
"""

from __future__ import annotations

from unittest.mock import MagicMock

from frappe.tests.utils import FrappeTestCase

from logistics.utils.module_integration import _filter_charges_by_internal_job_detail_params
from logistics.utils.sales_quote_charge_parameters import SALES_QUOTE_CHARGE_PARAMETER_FIELDS


def _blank_charge(**overrides):
	"""A MagicMock that mirrors a shipment charge row with every parameter blank by default.

	Auto-generated MagicMock children would otherwise be treated as meaningful parameter values
	by ``extract_sales_quote_charge_parameters``; explicit "" defaults sidestep that.
	"""
	blanks = {fn: "" for fn in SALES_QUOTE_CHARGE_PARAMETER_FIELDS}
	blanks.update(overrides)
	return MagicMock(**blanks)


def _blank_ij(**overrides):
	blanks = {fn: "" for fn in SALES_QUOTE_CHARGE_PARAMETER_FIELDS}
	blanks.update(overrides)
	return MagicMock(**blanks)


class TestFilterChargesByInternalJobDetailParams(FrappeTestCase):
	def test_no_ij_row_returns_input_unchanged(self):
		rows = [_blank_charge(service_type="Transport")]
		self.assertEqual(
			_filter_charges_by_internal_job_detail_params(rows, None, "Transport"),
			rows,
		)

	def test_ij_row_with_blank_params_does_not_narrow(self):
		# When the IJ row carries no service-scoped parameters, every shipment row passes through.
		rows = [
			_blank_charge(service_type="Transport", vehicle_type="20FT"),
			_blank_charge(service_type="Transport", vehicle_type="40FT"),
		]
		ij = _blank_ij(service_type="Transport")
		self.assertEqual(
			_filter_charges_by_internal_job_detail_params(rows, ij, "Transport"),
			rows,
		)

	def test_ij_row_param_filters_matching_charges(self):
		match = _blank_charge(service_type="Transport", vehicle_type="20FT")
		mismatch = _blank_charge(service_type="Transport", vehicle_type="40FT")
		wildcard = _blank_charge(service_type="Transport")  # blank vehicle_type = wildcard
		ij = _blank_ij(service_type="Transport", vehicle_type="20FT")

		filtered = _filter_charges_by_internal_job_detail_params(
			[match, mismatch, wildcard], ij, "Transport"
		)
		# 20FT charge and the wildcard charge match; 40FT charge is dropped.
		self.assertEqual(len(filtered), 2)
		self.assertIn(match, filtered)
		self.assertIn(wildcard, filtered)
		self.assertNotIn(mismatch, filtered)

	def test_customs_scope_uses_customs_params_only(self):
		# Customs scope only extracts customs_* params, so transport_template on the IJ is ignored.
		match = _blank_charge(service_type="Customs", customs_authority="BOC")
		mismatch = _blank_charge(service_type="Customs", customs_authority="OTHER")
		ij = _blank_ij(
			service_type="Customs", customs_authority="BOC", transport_template="TPL-IGNORED"
		)

		filtered = _filter_charges_by_internal_job_detail_params(
			[match, mismatch], ij, "Customs"
		)
		self.assertEqual(filtered, [match])

	def test_empty_rows_short_circuits(self):
		ij = _blank_ij(service_type="Transport", vehicle_type="20FT")
		self.assertEqual(
			_filter_charges_by_internal_job_detail_params([], ij, "Transport"),
			[],
		)
