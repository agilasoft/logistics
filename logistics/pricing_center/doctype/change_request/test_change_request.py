# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and Contributors
# See license.txt

from unittest.mock import MagicMock, patch

import frappe
from frappe.tests import UnitTestCase

from logistics.pricing_center.additional_charge_to_job import (
	INTERNAL_JOB_SATELLITE_JOB_TYPES,
	MAIN_JOB_TYPES_FOR_CHANGE_REQUEST,
	_charge_row_service_type_matches_job,
)
from logistics.pricing_center.change_request_to_job import (
	_resolve_main_and_default_internal_job,
	apply_change_request_charges_to_job,
	change_request_cost_rows_missing_on_main_job,
	ensure_change_request_cost_rows_on_job,
	merge_sales_quote_revenue_into_change_request_job_rows,
)


class TestChangeRequestToJob(UnitTestCase):
	def test_change_request_does_not_seed_linked_services_from_job(self):
		"""Services tab stays empty on create — CR is for new additional services only."""
		cr = frappe.new_doc("Change Request")
		cr.job_type = "Air Shipment"
		cr.job = "ASP-TEST"
		cr.validate()
		self.assertEqual(list(cr.linked_services or []), [])
	def test_charge_row_service_type_matches_job_accepts_canonical_aliases(self):
		self.assertTrue(_charge_row_service_type_matches_job("Air Shipment", "air"))
		self.assertTrue(_charge_row_service_type_matches_job("Air Shipment", "Air"))
		self.assertTrue(_charge_row_service_type_matches_job("Air Shipment", "Warehousing"))
		self.assertTrue(_charge_row_service_type_matches_job("Air Shipment", "Transport"))
		self.assertTrue(_charge_row_service_type_matches_job("Sea Shipment", "sea"))
		self.assertTrue(_charge_row_service_type_matches_job("Sea Shipment", "Customs"))
		self.assertFalse(_charge_row_service_type_matches_job("Transport Job", "Air"))

	@patch("logistics.pricing_center.change_request_to_job.frappe.msgprint")
	@patch("logistics.pricing_center.change_request_to_job.frappe.get_doc")
	@patch("logistics.pricing_center.change_request_to_job.frappe.db.exists", return_value=True)
	def test_apply_change_request_accepts_lowercase_air_service_type(
		self, _exists, mock_get_doc, _msgprint
	):
		job_doc = MagicMock()
		job_doc.charges = []
		job_doc.append = MagicMock()
		mock_get_doc.return_value = job_doc

		cr_doc = frappe._dict(
			name="CR-TEST",
			job_type="Air Shipment",
			job="ASP-TEST",
			charges=[
				frappe._dict(
					name="crc-1",
					item_code="EXTRA-FEE",
					service_type="air",
					estimated_cost=100,
					cost_quantity=1,
				),
			],
		)

		apply_change_request_charges_to_job(cr_doc)

		self.assertEqual(job_doc.append.call_count, 1)
		charge_data = job_doc.append.call_args[0][1]
		self.assertEqual(charge_data["item_code"], "EXTRA-FEE")
		self.assertEqual(charge_data["change_request"], "CR-TEST")
		job_doc.save.assert_called_once()

	@patch("logistics.pricing_center.change_request_to_job.frappe.msgprint")
	@patch("logistics.pricing_center.change_request_to_job.frappe.get_doc")
	@patch("logistics.pricing_center.change_request_to_job.frappe.db.exists", return_value=True)
	def test_apply_change_request_accepts_non_matching_service_type_on_job_scoped_cr(
		self, _exists, mock_get_doc, _msgprint
	):
		job_doc = MagicMock()
		job_doc.charges = []
		job_doc.append = MagicMock()
		mock_get_doc.return_value = job_doc

		cr_doc = frappe._dict(
			name="CR-TEST",
			job_type="Air Shipment",
			job="ASP-TEST",
			charges=[
				frappe._dict(
					name="crc-1",
					item_code="AMBRACK",
					service_type="Warehousing",
					estimated_cost=78390,
					cost_quantity=1,
				),
			],
		)

		apply_change_request_charges_to_job(cr_doc)

		self.assertEqual(job_doc.append.call_count, 1)
		charge_data = job_doc.append.call_args[0][1]
		self.assertEqual(charge_data["item_code"], "AMBRACK")
		self.assertEqual(charge_data["service_type"], "Warehousing")

	@patch("logistics.pricing_center.change_request_to_job.frappe.msgprint")
	@patch("logistics.pricing_center.change_request_to_job.frappe.get_doc")
	@patch("logistics.pricing_center.change_request_to_job.frappe.db.exists", return_value=True)
	def test_merge_sq_revenue_updates_row_matched_by_change_request_charge(
		self, _exists, mock_get_doc, _msgprint
	):
		job_row = frappe._dict(
			change_request="CR-TEST",
			change_request_charge="crc-1",
			estimated_revenue=0,
			unit_rate=0,
		)
		job_doc = frappe._dict(charges=[job_row])
		job_doc.flags = frappe._dict()
		job_doc.save = MagicMock()
		mock_get_doc.return_value = job_doc

		sq_doc = frappe._dict(
			name="OOQ-TEST",
			job_type="Air Shipment",
			job="ASP-TEST",
			change_request="CR-TEST",
			charges=[
				frappe._dict(
					item_code="AMBRACK",
					service_type="Warehousing",
					change_request_charge="crc-1",
					charge_type="Margin",
					calculation_method="Flat Rate",
					quantity=1,
					unit_rate=197650,
					estimated_revenue=197650,
				),
			],
		)

		updated = merge_sales_quote_revenue_into_change_request_job_rows(sq_doc)

		self.assertEqual(updated, 1)
		self.assertEqual(job_row.sales_quote_link, "OOQ-TEST")
		job_doc.save.assert_called_once()

	@patch("logistics.pricing_center.change_request_to_job.apply_change_request_charges_to_job")
	def test_ensure_change_request_cost_rows_on_job_applies_when_missing(self, mock_apply):
		cr_doc = frappe._dict(
			name="CR-TEST",
			job_type="Air Shipment",
			job="ASP-TEST",
			charges=[frappe._dict(name="crc-1", item_code="AMBRACK")],
		)
		job_doc = frappe._dict(charges=[])
		with patch(
			"logistics.pricing_center.change_request_to_job._resolve_main_and_default_internal_job",
			return_value=("Air Shipment", "ASP-TEST", None),
		), patch("logistics.pricing_center.change_request_to_job.frappe.db.exists", return_value=True), patch(
			"logistics.pricing_center.change_request_to_job.frappe.get_doc",
			return_value=job_doc,
		):
			self.assertTrue(change_request_cost_rows_missing_on_main_job(cr_doc))
			ensure_change_request_cost_rows_on_job(cr_doc)
		mock_apply.assert_called_once_with(cr_doc)

	@patch("logistics.pricing_center.change_request_to_job.apply_change_request_charges_to_job")
	def test_ensure_change_request_cost_rows_on_job_skips_when_present(self, mock_apply):
		cr_doc = frappe._dict(
			name="CR-TEST",
			job_type="Air Shipment",
			job="ASP-TEST",
			charges=[frappe._dict(name="crc-1", item_code="AMBRACK")],
		)
		job_doc = frappe._dict(
			charges=[
				frappe._dict(
					change_request="CR-TEST",
					change_request_charge="crc-1",
				),
			]
		)
		with patch(
			"logistics.pricing_center.change_request_to_job._resolve_main_and_default_internal_job",
			return_value=("Air Shipment", "ASP-TEST", None),
		), patch("logistics.pricing_center.change_request_to_job.frappe.db.exists", return_value=True), patch(
			"logistics.pricing_center.change_request_to_job.frappe.get_doc",
			return_value=job_doc,
		):
			self.assertFalse(change_request_cost_rows_missing_on_main_job(cr_doc))
			ensure_change_request_cost_rows_on_job(cr_doc)
		mock_apply.assert_not_called()

	# -----------------------------------------------------------------------------------
	# Bidirectional Main ↔ Internal Job satellite mirror
	# -----------------------------------------------------------------------------------

	def test_main_and_satellite_constants_cover_expected_job_types(self):
		"""Sanity: the constants used by the resolver list the doctypes Change Request supports."""
		self.assertIn("Sea Shipment", MAIN_JOB_TYPES_FOR_CHANGE_REQUEST)
		self.assertIn("Air Shipment", MAIN_JOB_TYPES_FOR_CHANGE_REQUEST)
		self.assertIn("Transport Job", MAIN_JOB_TYPES_FOR_CHANGE_REQUEST)
		self.assertIn("Warehouse Job", MAIN_JOB_TYPES_FOR_CHANGE_REQUEST)
		self.assertIn("Declaration", MAIN_JOB_TYPES_FOR_CHANGE_REQUEST)
		self.assertIn("Special Project", MAIN_JOB_TYPES_FOR_CHANGE_REQUEST)
		self.assertIn("Docket", MAIN_JOB_TYPES_FOR_CHANGE_REQUEST)
		self.assertIn("Sea Booking", INTERNAL_JOB_SATELLITE_JOB_TYPES)
		self.assertIn("Air Booking", INTERNAL_JOB_SATELLITE_JOB_TYPES)
		self.assertIn("Transport Order", INTERNAL_JOB_SATELLITE_JOB_TYPES)
		self.assertIn("Declaration Order", INTERNAL_JOB_SATELLITE_JOB_TYPES)
		self.assertIn("Inbound Order", INTERNAL_JOB_SATELLITE_JOB_TYPES)
		self.assertIn("Release Order", INTERNAL_JOB_SATELLITE_JOB_TYPES)
		self.assertIn("Cross-Docking Order", INTERNAL_JOB_SATELLITE_JOB_TYPES)
		# A doctype must be in exactly one set (Main vs Satellite) — never both.
		self.assertEqual(
			MAIN_JOB_TYPES_FOR_CHANGE_REQUEST & INTERNAL_JOB_SATELLITE_JOB_TYPES,
			set(),
		)

	def test_resolve_main_for_change_request_on_main_returns_target_directly(self):
		"""CR filed on a Main job → resolver returns the target itself with no default IJ."""
		cr = frappe._dict(job_type="Sea Shipment", job="SS-001")
		mt, mn, ij = _resolve_main_and_default_internal_job(cr)
		self.assertEqual(mt, "Sea Shipment")
		self.assertEqual(mn, "SS-001")
		self.assertIsNone(ij)

	@patch("logistics.pricing_center.change_request_to_job.frappe.db.exists", return_value=True)
	@patch("logistics.pricing_center.change_request_to_job.frappe.db.get_value")
	def test_resolve_main_for_change_request_on_ij_satellite_walks_back_links(
		self, mock_get_value, _exists
	):
		"""CR filed on an IJ satellite → resolver walks main_job_type/main_job back-links."""
		mock_get_value.return_value = {
			"main_job_type": "Sea Shipment",
			"main_job": "SS-002",
			"internal_job": "IJ-2026-000001",
			"is_internal_job": 1,
		}
		cr = frappe._dict(job_type="Sea Booking", job="SB-9")
		mt, mn, ij = _resolve_main_and_default_internal_job(cr)
		self.assertEqual(mt, "Sea Shipment")
		self.assertEqual(mn, "SS-002")
		self.assertEqual(ij, "IJ-2026-000001")

	@patch("logistics.pricing_center.change_request_to_job.frappe.db.exists", return_value=True)
	@patch("logistics.pricing_center.change_request_to_job.frappe.db.get_value")
	def test_resolve_main_returns_none_when_satellite_is_not_flagged_as_ij(
		self, mock_get_value, _exists
	):
		"""Satellite with ``is_internal_job=0`` is treated as standalone — no Main mirroring."""
		mock_get_value.return_value = {
			"main_job_type": "",
			"main_job": "",
			"internal_job": "",
			"is_internal_job": 0,
		}
		cr = frappe._dict(job_type="Sea Booking", job="SB-LEGACY")
		mt, mn, ij = _resolve_main_and_default_internal_job(cr)
		self.assertIsNone(mt)
		self.assertIsNone(mn)
		self.assertIsNone(ij)

	@patch("logistics.pricing_center.change_request_to_job.frappe.msgprint")
	@patch("logistics.pricing_center.change_request_to_job._safe_append_charge_to_doc")
	@patch("logistics.pricing_center.change_request_to_job._satellite_for_internal_job")
	@patch("logistics.pricing_center.change_request_to_job.frappe.get_doc")
	@patch("logistics.pricing_center.change_request_to_job.frappe.db.exists", return_value=True)
	def test_apply_cr_on_main_with_ij_tagged_row_mirrors_to_satellite(
		self,
		_exists,
		mock_get_doc,
		mock_sat_lookup,
		mock_safe_append,
		_msgprint,
	):
		"""CR on Main with an Internal Job tag on a row → row mirrored to the IJ's satellite booking."""
		main_doc = MagicMock(name="main_doc")
		main_doc.charges = []
		main_doc.doctype = "Sea Shipment"
		sat_doc = MagicMock(name="sat_doc")
		sat_doc.charges = []
		sat_doc.doctype = "Sea Booking"

		def get_doc_side_effect(doctype, name):
			if doctype == "Sea Shipment":
				return main_doc
			if doctype == "Sea Booking":
				return sat_doc
			return MagicMock()

		mock_get_doc.side_effect = get_doc_side_effect
		mock_sat_lookup.return_value = ("Sea Booking", "SB-001")
		mock_safe_append.return_value = True

		cr_doc = frappe._dict(
			name="CR-IJ",
			job_type="Sea Shipment",
			job="SS-100",
			charges=[
				frappe._dict(
					name="crc-1",
					item_code="EXTRA",
					service_type="Sea",
					linked_service="IJ-X",
					estimated_cost=50,
					cost_quantity=1,
				),
			],
		)
		apply_change_request_charges_to_job(cr_doc)

		# Both Main and Satellite should have received an appended row.
		# _safe_append_charge_to_doc is called twice: once for main, once for satellite.
		self.assertEqual(mock_safe_append.call_count, 2)
		target_docs_appended_to = {call.args[0] for call in mock_safe_append.call_args_list}
		self.assertIn(main_doc, target_docs_appended_to)
		self.assertIn(sat_doc, target_docs_appended_to)
		# Main row should carry the Linked Service scope tag.
		main_call = next(c for c in mock_safe_append.call_args_list if c.args[0] is main_doc)
		main_payload = main_call.args[1]
		self.assertEqual(main_payload.get("change_request"), "CR-IJ")
		self.assertEqual(main_payload.get("charge_scope"), "Linked")
		self.assertEqual(main_payload.get("linked_service"), "IJ-X")
		# Same expectation on the satellite side — the row mirror must persist as linked-scoped.
		sat_call = next(c for c in mock_safe_append.call_args_list if c.args[0] is sat_doc)
		sat_payload = sat_call.args[1]
		self.assertEqual(sat_payload.get("charge_scope"), "Linked")
		self.assertEqual(sat_payload.get("linked_service"), "IJ-X")
		main_doc.save.assert_called_once()
		sat_doc.save.assert_called_once()

	def test_decorate_charge_dict_overrides_existing_main_scope(self):
		"""Decoration must overwrite a pre-existing ``charge_scope='Main'`` with ``Linked``.

		This guards the regression where the Sales Quote Charge (created from a CR Charge) was
		showing as ``Main`` on the linked-service satellite booking because the default ``Main``
		scope was never overwritten.
		"""
		from logistics.pricing_center.change_request_to_job import (
			_decorate_charge_dict_with_linked_service_scope,
		)

		target = frappe._dict(doctype="Sea Booking")
		payload = {"item_code": "EXTRA", "charge_scope": "Main", "linked_service": "OLD"}
		_decorate_charge_dict_with_linked_service_scope(payload, target, "IJ-X")
		self.assertEqual(payload["charge_scope"], "Linked")
		self.assertEqual(payload["linked_service"], "IJ-X")

	def test_sales_quote_dict_from_linked_service_tagged_cr_charge_sets_linked_scope(self):
		"""Sales Quote Charge produced from a linked-service-tagged CR Charge must carry Linked scope.

		Without this, the SQ Charge inherits the schema default ``charge_scope='Main'`` and
		any downstream copy reads ``Main`` and writes ``Main`` on the satellite booking.
		"""
		from logistics.pricing_center.doctype.change_request.change_request import (
			_charge_row_as_sales_quote_dict,
		)

		def _fake_charge_row(**kw):
			data = dict(kw)
			row = MagicMock()
			row.as_dict = MagicMock(return_value=data)
			return row

		row = _fake_charge_row(
			name="crc-1",
			item_code="EXTRA",
			service_type="Sea",
			linked_service="IJ-X",
			estimated_cost=100,
			cost_quantity=1,
		)
		out = _charge_row_as_sales_quote_dict(row, "Sea")
		self.assertEqual(out["charge_scope"], "Linked")
		self.assertEqual(out["linked_service"], "IJ-X")
		self.assertEqual(out["item_code"], "EXTRA")

		row2 = _fake_charge_row(
			name="crc-2",
			item_code="EXTRA2",
			service_type="Sea",
			estimated_cost=100,
			cost_quantity=1,
		)
		out2 = _charge_row_as_sales_quote_dict(row2, "Sea")
		self.assertEqual(out2.get("charge_scope"), "Main")

	def test_sales_quote_dict_from_main_scoped_cr_charge_uses_default_linked_service(self):
		"""CR Charge rows left at schema-default Main must inherit the CR default Linked Service.

		Regression for issue #1036: additional-charge Sales Quotes showed Scope=Main instead of
		Linked when CR charges were created before the desk UI stamped linked_service.
		"""
		from logistics.pricing_center.doctype.change_request.change_request import (
			_charge_row_as_sales_quote_dict,
		)

		def _fake_charge_row(**kw):
			data = dict(kw)
			row = MagicMock()
			row.as_dict = MagicMock(return_value=data)
			return row

		row = _fake_charge_row(
			name="crc-3",
			item_code="CUSTOMS",
			service_type="Customs",
			charge_scope="Main",
			estimated_cost=100,
			cost_quantity=1,
		)
		out = _charge_row_as_sales_quote_dict(row, "Customs", "LS-DECL-001")
		self.assertEqual(out["charge_scope"], "Linked")
		self.assertEqual(out["linked_service"], "LS-DECL-001")

	def test_linked_service_for_row_uses_cr_default_over_schema_main_scope(self):
		from logistics.pricing_center.change_request_to_job import _linked_service_for_row

		row = frappe._dict(charge_scope="Main", linked_service=None)
		self.assertEqual(_linked_service_for_row(row, "LS-SAT-001"), "LS-SAT-001")
		self.assertIsNone(_linked_service_for_row(row, None))

	@patch("logistics.pricing_center.change_request_to_job.frappe.db.get_value", return_value="Extra Handling")
	def test_map_cr_charge_to_docket_cost_defaults_mice_and_tags(self, _mock_item_name):
		from logistics.pricing_center.change_request_to_job import _map_cr_charge_to_docket_cost

		row = frappe._dict(
			item_code="MICE-EXTRA",
			cost_quantity=2,
			quantity=1,
			currency="USD",
			cost_currency="USD",
			unit_cost=50,
			estimated_cost=100,
		)
		out = _map_cr_charge_to_docket_cost(row, "CR-DOCKET", "crc-dk-1")
		self.assertEqual(out["service_type"], "MICE")
		self.assertEqual(out["change_request"], "CR-DOCKET")
		self.assertEqual(out["change_request_charge"], "crc-dk-1")
		self.assertEqual(out["estimated_revenue"], 0)
		self.assertEqual(out["description"], "Extra Handling")

	def test_docket_is_registered_in_cost_and_revenue_appliers(self):
		from logistics.pricing_center.change_request_to_job import _cost_mappers, _revenue_appliers

		self.assertIn("Docket", _cost_mappers())
		self.assertIn("Docket", _revenue_appliers())


class TestChangeRequestVisibility(UnitTestCase):
	"""Job-type field visibility + immutable Job Type / Job."""

	def test_air_shipment_hides_run_sheet_and_cutoffs(self):
		from logistics.pricing_center.change_request_field_apply import (
			applicable_header_fields,
			header_fields_for_job_type,
			job_type_supports_charges,
			job_type_supports_packages,
		)

		fields = header_fields_for_job_type("Air Shipment")
		self.assertIn("origin_port", fields)
		self.assertIn("shipper", fields)
		self.assertNotIn("run_date", fields)
		self.assertNotIn("cargo_cut_off", fields)
		self.assertNotIn("dispatcher", fields)
		self.assertTrue(job_type_supports_packages("Air Shipment"))
		self.assertTrue(job_type_supports_charges("Air Shipment"))

		charges_only = applicable_header_fields("Air Shipment", {"Charges"})
		self.assertEqual(charges_only, frozenset())

	def test_sea_shipment_includes_cutoffs_not_run_sheet(self):
		from logistics.pricing_center.change_request_field_apply import header_fields_for_job_type

		fields = header_fields_for_job_type("Sea Shipment")
		self.assertIn("cargo_cut_off", fields)
		self.assertIn("origin_port", fields)
		self.assertNotIn("run_date", fields)

	def test_run_sheet_has_no_charges_or_packages(self):
		from logistics.pricing_center.change_request_field_apply import (
			header_fields_for_job_type,
			job_type_supports_charges,
			job_type_supports_packages,
			job_type_supports_services,
		)

		fields = header_fields_for_job_type("Run Sheet")
		self.assertIn("run_date", fields)
		self.assertIn("dispatcher", fields)
		self.assertNotIn("customer", fields)
		self.assertNotIn("origin_port", fields)
		self.assertFalse(job_type_supports_packages("Run Sheet"))
		self.assertFalse(job_type_supports_charges("Run Sheet"))
		self.assertFalse(job_type_supports_services("Run Sheet"))

	def test_declaration_has_no_package_table(self):
		"""Declaration.packages is a Float count, not a child table — CR must not iterate it."""
		from logistics.pricing_center.change_request_field_apply import (
			build_baseline_snapshot,
			default_sections_for_job_type,
			filter_sections_for_job_type,
			job_type_supports_packages,
			seed_change_request_from_job,
		)

		self.assertFalse(job_type_supports_packages("Declaration"))
		self.assertFalse(job_type_supports_packages("Declaration Order"))
		self.assertNotIn("Packages", default_sections_for_job_type("Declaration"))
		self.assertNotIn(
			"Packages",
			filter_sections_for_job_type("Declaration", {"Parties", "Packages", "Charges"}),
		)

		job = frappe._dict(
			doctype="Declaration",
			name="DEC-TEST",
			customer="C-1",
			packages=12.0,  # Float count — must not raise TypeError
		)
		baseline = build_baseline_snapshot(job, {"Parties", "Packages", "Charges"})
		self.assertEqual(baseline["packages"], [])

		cr = frappe.new_doc("Change Request")
		cr.job_type = "Declaration"
		cr.job = "DEC-TEST"
		cr.status = "Draft"
		# Avoid DB fetch: pass job_doc explicitly
		seed_change_request_from_job(
			cr,
			job_doc=job,
			sections=["Parties", "Packages", "Charges"],
			reason="Test amendment",
		)
		self.assertNotIn("Packages", cr.change_sections or "")
		self.assertFalse(cr.get("package_changes"))

	def test_transport_job_shows_transport_places_not_ports(self):
		from logistics.pricing_center.change_request_field_apply import header_fields_for_job_type

		fields = header_fields_for_job_type("Transport Job")
		self.assertIn("vehicle_type", fields)
		self.assertIn("container_no", fields)
		self.assertIn("customer", fields)
		self.assertNotIn("origin_port", fields)
		self.assertNotIn("cargo_cut_off", fields)

	def test_count_section_changes_ignores_inapplicable_fields(self):
		from logistics.pricing_center.change_request_field_apply import count_section_changes

		cr = frappe._dict(
			job_type="Warehouse Job",
			change_sections="Parties\nNotes",
			customer="C-1",
			shipper="S-1",
			# Noise that exists on CR but not on Warehouse Job:
			origin_port="PHMNL",
			run_date="2026-01-01",
			charges=[],
			package_changes=[],
			baseline_json='{"header": {"customer": "C-0", "shipper": "S-1", "origin_port": "", "run_date": ""}}',
		)
		counts = count_section_changes(cr)
		self.assertEqual(counts["Parties"], 1)  # customer only
		self.assertEqual(counts["Places & Dates"], 0)
		self.assertEqual(counts["Packages"], 0)


class TestChangeRequestFetchFromApply(UnitTestCase):
	"""CR header apply must not lose values re-fetched from linked parents on save."""

	def test_sync_fetch_from_sources_updates_transport_order(self):
		from logistics.pricing_center.change_request_field_apply import (
			_sync_fetch_from_sources_for_applied_fields,
		)

		job = frappe._dict(
			doctype="Transport Job",
			transport_order="TRO-TEST",
			transport_company="TRC-NEW",
		)
		with patch(
			"logistics.pricing_center.change_request_field_apply.frappe.get_meta"
		) as mock_meta, patch(
			"logistics.pricing_center.change_request_field_apply.frappe.db.exists",
			return_value=True,
		), patch(
			"logistics.pricing_center.change_request_field_apply.frappe.db.get_value",
			return_value="TRC-OLD",
		), patch(
			"logistics.pricing_center.change_request_field_apply.frappe.db.set_value"
		) as mock_set:
			tj_meta = MagicMock()
			tc_df = MagicMock(
				fetch_from="transport_order.transport_company",
				fieldtype="Link",
			)
			to_df = MagicMock(fieldtype="Link", options="Transport Order")
			tj_meta.get_field.side_effect = lambda fn: {
				"transport_company": tc_df,
				"transport_order": to_df,
			}.get(fn)
			to_meta = MagicMock()
			to_meta.has_field.return_value = True
			mock_meta.side_effect = lambda dt: tj_meta if dt == "Transport Job" else to_meta

			_sync_fetch_from_sources_for_applied_fields(
				job, {"transport_company": "TRC-NEW"}
			)
			mock_set.assert_called_once_with(
				"Transport Order", "TRO-TEST", "transport_company", "TRC-NEW"
			)

	def test_reassert_applied_header_values_rewrites_overwritten_field(self):
		from logistics.pricing_center.change_request_field_apply import (
			_reassert_applied_header_values,
		)

		with patch(
			"logistics.pricing_center.change_request_field_apply.frappe.db.get_value",
			return_value="TRC-OLD",
		), patch(
			"logistics.pricing_center.change_request_field_apply.frappe.db.set_value"
		) as mock_set:
			_reassert_applied_header_values(
				"Transport Job", "TRJ-TEST", {"transport_company": "TRC-NEW"}
			)
			mock_set.assert_called_once_with(
				"Transport Job",
				"TRJ-TEST",
				"transport_company",
				"TRC-NEW",
				update_modified=False,
			)
