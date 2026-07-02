# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import json
from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase
from frappe.utils import now_datetime


def _mock_charge(**fields):
	"""Lightweight stand-in for a Special Project Charges child row.

	Supports both attribute access (used by ``getattr`` in the matcher) and a callable
	``as_dict`` (used by ``_scrub_main_row_to_child_dict``). Using ``frappe._dict`` here
	doesn't work because its ``__getattr__`` returns ``None`` for missing keys, which
	makes ``hasattr(main_ch, "as_dict")`` True with ``as_dict = None``.
	"""
	sn = SimpleNamespace(**fields)
	sn.as_dict = lambda: dict(fields)
	return sn


def _linked_mock_charge(**fields):
	"""Programme charge row eligible for copy onto operational bookings (scope=Linked)."""
	fields.setdefault("charge_scope", "Linked")
	fields.setdefault("linked_service", "LS-TEST")
	return _mock_charge(**fields)


def _linked_charge_dict(**fields):
	"""Dict programme charge row for booking-copy / preview tests (scope=Linked)."""
	fields.setdefault("charge_scope", "Linked")
	fields.setdefault("linked_service", "LS-TEST")
	return frappe._dict(**fields)

from logistics.special_projects.special_project_booking_creation import (
	_apply_air_sea_corridor_ports_from_context,
	_apply_sales_quote_parties_to_target,
	_dialog_creatable_job_type,
	_link_planning_service_row,
	_set_main_service_for_one_off_quote_target,
	LIFECYCLE_JOB_QUOTE_PARAMETER_MISMATCH_MESSAGE,
	create_booking_or_order_from_special_project,
	get_lifecycle_job_parameter_field_specs,
	get_programme_charge_parameter_field_specs,
	get_special_project_booking_choices,
	get_special_project_booking_preview,
	lifecycle_job_params_match_quotation,
	validate_lifecycle_job_params_match_quotation,
)
from logistics.special_projects.test_special_project_helpers import (
	new_special_project_for_test,
)
from logistics.special_projects.doctype.project_order.project_order import (
	_build_project_job_from_order,
)
from logistics.special_projects.project_order_copy import build_project_order_from_special_project
from logistics.special_projects.special_project_charge_copy import (
	populate_operational_charges_from_special_project,
)


def _ensure_test_sp_charge_item() -> str:
	"""Ensure a sales-item exists for use in SP charge copy unit tests, and return its code."""
	item = "TEST-ITEM-SP-CHG"
	if frappe.db.exists("Item", item):
		return item
	item_group = frappe.db.get_value("Item Group", {"is_group": 0}, "name")
	if not item_group:
		item_group = frappe.db.get_value("Item Group", {}, "name")
	frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": item,
			"item_name": item,
			"item_group": item_group,
			"is_sales_item": 1,
		}
	).insert(ignore_permissions=True)
	return item


class TestSpecialProjectChargeCopy(UnitTestCase):
	def test_populate_air_booking_filters_by_lifecycle_service_type(self):
		item = _ensure_test_sp_charge_item()

		sp = frappe._dict(
			charges=[
				_linked_mock_charge(
					service_type="Air",
					item_code=item,
					estimated_revenue=100,
					rate=100,
					quantity=1,
				),
				_linked_mock_charge(service_type="Transport", item_code=item, rate=50),
			]
		)
		row = frappe._dict(service_type="Air")
		booking = frappe.new_doc("Air Booking")
		n = populate_operational_charges_from_special_project(sp, booking, row)
		self.assertEqual(n, 1)
		self.assertEqual(len(booking.charges), 1)
		self.assertEqual((booking.charges[0].service_type or "").strip(), "Air")

	def test_service_type_match_copies_regardless_of_lifecycle_pin(self):
		item = _ensure_test_sp_charge_item()

		# Programme charges are budget lines by service type; lifecycle_job_line is legacy metadata.
		sp = frappe._dict(
			charges=[
				_linked_mock_charge(
					service_type="Air",
					lifecycle_job_line="ROW-1",
					item_code=item,
					rate=100,
					quantity=1,
				),
			]
		)
		row = frappe._dict(service_type="Air", idx=6, name="ROW-6")
		booking = frappe.new_doc("Air Booking")
		n = populate_operational_charges_from_special_project(sp, booking, row)
		self.assertEqual(n, 1)

	def test_ignore_pin_falls_back_to_service_type_match(self):
		item = _ensure_test_sp_charge_item()

		# Mirrors the user's screenshot: Air charges pinned to row 1, Air Booking created from
		# row 6. The strict pass returns 0; ignore_pin=True must pick them up by service type.
		sp = frappe._dict(
			charges=[
				_linked_mock_charge(
					service_type="Air",
					lifecycle_job_line="ROW-1",
					item_code=item,
					rate=100,
					quantity=1,
				),
				_linked_mock_charge(
					service_type="Sea",
					lifecycle_job_line="ROW-2",
					item_code=item,
					rate=200,
					quantity=1,
				),
				_linked_mock_charge(
					service_type="Transport",
					lifecycle_job_line="ROW-3",
					item_code=item,
					rate=300,
					quantity=1,
				),
			]
		)
		row = frappe._dict(service_type="Air", idx=6, name="ROW-6")
		booking = frappe.new_doc("Air Booking")
		n = populate_operational_charges_from_special_project(
			sp, booking, row, ignore_pin=True
		)
		self.assertEqual(n, 1)
		self.assertEqual(len(booking.charges), 1)
		self.assertEqual((booking.charges[0].service_type or "").strip(), "Air")

	@patch("logistics.special_projects.special_project_charge_copy.programme_charge_matches_creation_parameters")
	def test_creation_parameters_filter_programme_charges(self, mock_match):
		item = _ensure_test_sp_charge_item()
		sp = frappe._dict(
			sales_quote="SQ-1",
			charges=[
				_linked_mock_charge(service_type="Transport", item_code=item + "-A", rate=100, quantity=1),
				_linked_mock_charge(service_type="Transport", item_code=item + "-B", rate=200, quantity=1),
			],
		)
		row = frappe._dict(service_type="Transport")
		params = {"transport_template": "TPL-1", "vehicle_type": "20FT"}

		def _side_effect(ch, _params):
			return ch.item_code.endswith("-A")

		mock_match.side_effect = _side_effect
		order = frappe.new_doc("Transport Order")
		n = populate_operational_charges_from_special_project(
			sp, order, row, creation_parameters=params
		)
		self.assertEqual(n, 1)
		self.assertEqual(order.charges[0].item_code, item + "-A")

	def test_main_scope_charges_are_not_copied(self):
		item = _ensure_test_sp_charge_item()
		other = item + "-MAIN"
		sp = frappe._dict(
			charges=[
				_linked_mock_charge(
					service_type="Transport",
					item_code=item,
					rate=100,
					quantity=1,
				),
				_mock_charge(
					service_type="Transport",
					item_code=other,
					charge_scope="Main",
					rate=50,
					quantity=1,
				),
			]
		)
		row = frappe._dict(service_type="Transport")
		order = frappe.new_doc("Transport Order")
		n = populate_operational_charges_from_special_project(sp, order, row)
		self.assertEqual(n, 1)
		self.assertEqual(order.charges[0].item_code, item)
		self.assertEqual((order.charges[0].charge_scope or "").strip(), "Linked")


class TestAirSeaCorridorPortsFromContext(UnitTestCase):
	def test_fills_ports_from_sales_quote_when_lifecycle_row_blank(self):
		sp = frappe._dict(sales_quote="SQ-CORRIDOR-TEST")
		booking = frappe.new_doc("Air Booking")
		booking.direction = ""
		sq = frappe._dict(
			name="SQ-CORRIDOR-TEST",
			origin_port="USLAX",
			destination_port="USJFK",
			direction="Export",
			charges=[],
			routing_legs=[],
			air_freight=[],
		)
		with (
			patch("frappe.db.exists", return_value=True),
			patch("frappe.get_doc", return_value=sq),
		):
			_apply_air_sea_corridor_ports_from_context(booking, sp, frappe._dict())
		self.assertEqual(booking.origin_port, "USLAX")
		self.assertEqual(booking.destination_port, "USJFK")
		self.assertEqual(booking.direction, "Export")

	def test_lifecycle_row_ports_take_precedence(self):
		sp = frappe._dict(sales_quote="SQ-CORRIDOR-TEST")
		booking = frappe.new_doc("Air Booking")
		row = frappe._dict(origin_port="SGSIN", destination_port="HKHKG")
		sq = frappe._dict(
			name="SQ-CORRIDOR-TEST",
			origin_port="USLAX",
			destination_port="USJFK",
			charges=[],
			routing_legs=[],
			air_freight=[],
		)
		with (
			patch("frappe.db.exists", return_value=True),
			patch("frappe.get_doc", return_value=sq),
		):
			_apply_air_sea_corridor_ports_from_context(booking, sp, row)
		self.assertEqual(booking.origin_port, "SGSIN")
		self.assertEqual(booking.destination_port, "HKHKG")

	def test_fills_air_ports_from_sales_quote_location_fields(self):
		sp = frappe._dict(sales_quote="SQ-LOC-TEST")
		booking = frappe.new_doc("Air Booking")
		sq = frappe._dict(
			name="SQ-LOC-TEST",
			origin_port=None,
			destination_port=None,
			location_from="USLAX",
			location_to="USJFK",
			charges=[],
			routing_legs=[],
			air_freight=[],
		)
		with (
			patch("frappe.db.exists", return_value=True),
			patch("frappe.get_doc", return_value=sq),
		):
			_apply_air_sea_corridor_ports_from_context(booking, sp, frappe._dict())
		self.assertEqual(booking.origin_port, "USLAX")
		self.assertEqual(booking.destination_port, "USJFK")

	def test_fills_air_ports_from_lifecycle_row_location_fields(self):
		sp = frappe._dict(sales_quote="")
		booking = frappe.new_doc("Air Booking")
		row = frappe._dict(location_from="SGSIN", location_to="HKHKG")
		_apply_air_sea_corridor_ports_from_context(booking, sp, row)
		self.assertEqual(booking.origin_port, "SGSIN")
		self.assertEqual(booking.destination_port, "HKHKG")


class TestSalesQuotePartiesOnBookingCreate(UnitTestCase):
	def test_copies_shipper_consignee_from_linked_sales_quote(self):
		shipper = frappe.db.get_value("Shipper", {"is_active": 1}, "name")
		consignee = frappe.db.get_value("Consignee", {"is_active": 1}, "name")
		sq_name = frappe.db.get_value(
			"Sales Quote",
			{"shipper": ["is", "set"], "consignee": ["is", "set"]},
			"name",
		)
		if not shipper or not consignee or not sq_name:
			self.skipTest("Shipper, Consignee, and Sales Quote with parties required")

		sp = frappe._dict(sales_quote=sq_name)
		booking = frappe.new_doc("Air Booking")
		_apply_sales_quote_parties_to_target(booking, sp)
		sq = frappe.get_cached_doc("Sales Quote", sq_name)
		self.assertEqual(booking.shipper, sq.shipper)
		self.assertEqual(booking.consignee, sq.consignee)


class TestMainServiceForOneOffQuoteOnSpecialProjectCreate(UnitTestCase):
	def test_sets_main_service_for_one_off_quote_primary_leg(self):
		sp = frappe._dict(sales_quote="OOQ-TEST-001")
		booking = frappe.new_doc("Air Booking")
		with (
			patch("frappe.db.exists", return_value=True),
			patch("frappe.db.get_value", return_value="One-off"),
		):
			_set_main_service_for_one_off_quote_target(booking, sp)
		self.assertEqual(booking.is_main_service, 1)

	def test_does_not_set_main_service_for_project_quote(self):
		sp = frappe._dict(sales_quote="PQ-TEST-001")
		booking = frappe.new_doc("Air Booking")
		with (
			patch("frappe.db.exists", return_value=True),
			patch("frappe.db.get_value", return_value="Project"),
		):
			_set_main_service_for_one_off_quote_target(booking, sp)
		self.assertEqual(booking.is_main_service, 0)

	def test_skips_when_internal_job(self):
		sp = frappe._dict(sales_quote="OOQ-TEST-002")
		booking = frappe.new_doc("Transport Order")
		booking.is_internal_job = 1
		with (
			patch("frappe.db.exists", return_value=True),
			patch("frappe.db.get_value", return_value="One-off"),
		):
			_set_main_service_for_one_off_quote_target(booking, sp)
		self.assertEqual(booking.is_main_service, 0)


class TestProjectJobSalesQuoteFromOrder(UnitTestCase):
	def test_project_job_inherits_sales_quote_from_order(self):
		company = frappe.db.get_value("Company", {}, "name")
		customer = frappe.db.get_value("Customer", {"disabled": 0}, "name")
		if not company or not customer:
			self.skipTest("Company and Customer required")

		sq_name = frappe.db.get_value(
			"Sales Quote",
			{"docstatus": 1, "quotation_type": "Project"},
			"name",
		)
		if not sq_name:
			sq_name = frappe.db.get_value("Sales Quote", {"docstatus": 1}, "name")
		if not sq_name:
			self.skipTest("Submitted Sales Quote required")

		sp = frappe.new_doc("Special Project")
		sp.project_name = f"Test SP PJ Sales Quote {now_datetime()}"
		sp.customer = customer
		sp.company = company
		sp.sales_quote = sq_name

		order = build_project_order_from_special_project(sp, "Order with quote")
		order.sales_quote = sq_name
		job = _build_project_job_from_order(order, "Job with quote")
		self.assertEqual(job.sales_quote, sq_name)

	def test_project_job_falls_back_to_special_project_sales_quote(self):
		company = frappe.db.get_value("Company", {}, "name")
		customer = frappe.db.get_value("Customer", {"disabled": 0}, "name")
		if not company or not customer:
			self.skipTest("Company and Customer required")

		sq_name = frappe.db.get_value("Sales Quote", {"docstatus": 1}, "name")
		if not sq_name:
			self.skipTest("Submitted Sales Quote required")

		sp = frappe.new_doc("Special Project")
		sp.project_name = f"Test SP PJ SQ Fallback {now_datetime()}"
		sp.customer = customer
		sp.company = company
		sp.sales_quote = sq_name
		sp.insert(ignore_permissions=True)

		order = build_project_order_from_special_project(sp, "Order no quote field")
		self.assertFalse(getattr(order, "sales_quote", None))
		job = _build_project_job_from_order(order, "Job fallback quote")
		self.assertEqual(job.sales_quote, sq_name)


class TestLifecycleJobQuoteParameterMatch(UnitTestCase):
	def test_lifecycle_row_matches_programme_charge(self):
		parent = frappe._dict(
			sales_quote="SQ-1",
			charges=[
				_linked_charge_dict(
					service_type="Transport",
					transport_template="TPL-1",
					vehicle_type="20FT",
				),
			],
		)
		row = frappe._dict(service_type="Transport", transport_template="TPL-1", vehicle_type="20FT")
		self.assertTrue(lifecycle_job_params_match_quotation(parent, "Transport Order", row))

	def test_customs_lifecycle_row_matches_when_only_customs_fields_align(self):
		parent = frappe._dict(
			sales_quote="SQ-1",
			charges=[
				frappe._dict(
					service_type="Customs",
					customs_authority="BOC",
					declaration_type="Import",
					customs_broker="ABC Brokerage",
					customs_charge_category="Customs Clearance",
					air_house_type="Standard House",
					direction="Import",
				),
			],
		)
		row = frappe._dict(
			service_type="Customs",
			customs_authority="BOC",
			declaration_type="Import",
			customs_broker="ABC Brokerage",
			customs_charge_category="Customs Clearance",
			air_house_type="Different House",
			sea_house_type="Different House",
			direction="Export",
		)
		self.assertTrue(lifecycle_job_params_match_quotation(parent, "Declaration Order", row))

	def test_lifecycle_row_mismatch_returns_false(self):
		parent = frappe._dict(
			sales_quote="SQ-1",
			charges=[
				_linked_charge_dict(
					service_type="Transport",
					transport_template="TPL-1",
					vehicle_type="20FT",
				),
			],
		)
		row = frappe._dict(
			service_type="Transport",
			transport_template="TPL-OTHER",
			vehicle_type="20FT",
		)
		self.assertFalse(lifecycle_job_params_match_quotation(parent, "Transport Order", row))

	def test_change_request_programme_charge_matches_creation_params(self):
		from logistics.special_projects.special_project_booking_creation import (
			suggested_parameters_from_programme_charges,
		)
		from logistics.utils.sales_quote_charge_parameters import (
			any_programme_charge_matches_params_dict,
		)

		parent = frappe._dict(
			charges=[
				_linked_charge_dict(
					service_type="Transport",
					transport_template="TPL-CR",
					vehicle_type="40FT",
					change_request="CR-1",
					item_code="ITEM-CR",
				),
				_linked_charge_dict(
					service_type="Transport",
					transport_template="TPL-SQ",
					vehicle_type="20FT",
					sales_quote_link="SQ-1",
					item_code="ITEM-SQ",
				),
			],
		)
		self.assertTrue(
			any_programme_charge_matches_params_dict(
				parent, {"transport_template": "TPL-CR", "vehicle_type": "40FT"}, "Transport"
			)
		)
		self.assertTrue(
			any_programme_charge_matches_params_dict(
				parent, {"transport_template": "TPL-SQ", "vehicle_type": "20FT"}, "Transport"
			)
		)
		self.assertEqual(
			suggested_parameters_from_programme_charges(parent, "Transport"),
			{"transport_template": "TPL-CR", "vehicle_type": "40FT"},
		)

	def test_resolve_programme_charge_params_from_change_request_link(self):
		from logistics.utils.sales_quote_charge_parameters import (
			resolve_programme_charge_row_parameters,
		)

		ch = frappe._dict(
			service_type="Air",
			item_code="FREIGHT",
			change_request="CR-1",
			change_request_charge="crc-1",
		)
		cr = frappe._dict(
			charges=[
				frappe._dict(
					name="crc-1",
					service_type="Air",
					air_house_type="Standard House",
					airline="5J",
					direction="Import",
					origin_port="CNSHA",
					destination_port="PHMNL",
				),
			]
		)
		with patch("frappe.db.exists", return_value=True):
			with patch("frappe.get_doc", return_value=cr):
				params = resolve_programme_charge_row_parameters(ch, "Air")
		self.assertEqual(params.get("airline"), "5J")
		self.assertEqual(params.get("destination_port"), "PHMNL")

	def test_booking_source_context_uses_charge_sales_quote_link(self):
		from logistics.special_projects.special_project_booking_creation import (
			_booking_source_context,
		)

		sp = frappe._dict(
			name="SP-1",
			customer="CUST-1",
			company="CO-1",
			sales_quote="PQ-MAIN",
			charges=[
				_linked_charge_dict(
					service_type="Air",
					sales_quote_link="PQ-AIR-ADDON",
					airline="Cebu Pacific",
				),
			],
			lifecycle_jobs=[],
		)
		row = frappe._dict(service_type="Air", idx=8)
		ctx = _booking_source_context(sp, row, "Air Booking")
		self.assertEqual(ctx.get("sales_quote"), "PQ-AIR-ADDON")

	def test_booking_source_context_resolves_sales_quote_from_change_request(self):
		from logistics.special_projects.special_project_booking_creation import (
			_booking_source_context,
		)

		sp = frappe._dict(
			name="SP-1",
			customer="CUST-1",
			company="CO-1",
			sales_quote="PQ-MAIN",
			charges=[
				_linked_charge_dict(
					service_type="Transport",
					change_request="CR-1",
					transport_template="TPL-CR",
				),
			],
			lifecycle_jobs=[],
		)
		row = frappe._dict(service_type="Transport", idx=1)

		def _get_value(doctype, name, fieldname):
			if doctype == "Change Request" and name == "CR-1" and fieldname == "sales_quote":
				return "OOQ-CR-1"
			return None

		with patch("frappe.db.exists", return_value=True):
			with patch("frappe.db.get_value", side_effect=_get_value):
				ctx = _booking_source_context(sp, row, "Transport Order")
		self.assertEqual(ctx.get("sales_quote"), "OOQ-CR-1")

	def test_cr_mapper_copies_routing_parameters_onto_special_project_charge(self):
		from logistics.pricing_center.change_request_to_job import (
			_map_cr_charge_to_special_project_cost,
		)
		from logistics.utils.sales_quote_charge_parameters import (
			SALES_QUOTE_CHARGE_PARAMETER_FIELDS,
		)

		cr_row = frappe._dict(
			service_type="Transport",
			item_code="X",
			transport_template="TPL-CR",
			vehicle_type="40FT",
		)
		with patch(
			"logistics.utils.sales_quote_charge_parameters.filter_fields_existing_in_doctype",
			return_value=list(SALES_QUOTE_CHARGE_PARAMETER_FIELDS),
		):
			mapped = _map_cr_charge_to_special_project_cost(cr_row, "CR-1", "crc-1")
		self.assertEqual(mapped.get("transport_template"), "TPL-CR")
		self.assertEqual(mapped.get("vehicle_type"), "40FT")
		self.assertEqual(mapped.get("change_request"), "CR-1")
		self.assertEqual(mapped.get("change_request_charge"), "crc-1")

	@patch(
		"logistics.special_projects.special_project_booking_creation._resolve_row_for_create",
		return_value=(SimpleNamespace(service_type="Transport", transport_template="TPL-X"), 1),
	)
	@patch(
		"logistics.special_projects.special_project_booking_creation.any_programme_charge_matches_params_dict",
		return_value=False,
	)
	def test_validate_throws_on_mismatch(self, _match, _resolve):
		parent = SimpleNamespace(sales_quote="SQ-1")
		with self.assertRaises(frappe.ValidationError) as ctx:
			validate_lifecycle_job_params_match_quotation(
				parent,
				"Transport Order",
				1,
				creation_parameters={"transport_template": "TPL-X", "vehicle_type": "20FT"},
			)
		self.assertEqual(str(ctx.exception), str(LIFECYCLE_JOB_QUOTE_PARAMETER_MISMATCH_MESSAGE))

	@patch(
		"logistics.special_projects.special_project_booking_creation._resolve_row_for_create",
		return_value=(
			frappe._dict(
				service_type="Transport",
				transport_template="TPL-WRONG",
				vehicle_type="20FT",
			),
			1,
		),
	)
	def test_validate_uses_charge_suggestions_not_lifecycle_row_defaults(self, _resolve):
		parent = frappe._dict(
			charges=[
				_linked_charge_dict(
					service_type="Transport",
					transport_template="TPL-1",
					vehicle_type="20FT",
				),
			],
		)
		validate_lifecycle_job_params_match_quotation(parent, "Transport Order", 1)

	def test_special_project_manpower_param_matches_with_numeric_coercion(self):
		from logistics.utils.sales_quote_charge_parameters import (
			any_programme_charge_matches_params_dict,
		)

		parent = frappe._dict(
			charges=[
				frappe._dict(
					service_type="Special Project",
					sp_manpower=5,
				),
			],
		)
		self.assertTrue(
			any_programme_charge_matches_params_dict(
				parent, {"sp_manpower": "5"}, "Special Project"
			)
		)

	@patch(
		"logistics.special_projects.special_project_booking_creation.lifecycle_job_params_match_quotation",
		return_value=False,
	)
	@patch(
		"logistics.special_projects.special_project_booking_creation.planning_row_is_open",
		return_value=True,
	)
	@patch("logistics.special_projects.special_project_booking_creation.frappe.db.exists", return_value=True)
	def test_booking_choices_creatable_when_line_open(self, _exists, _open, _match):
		doc = frappe._dict(
			name="SP-1",
			sales_quote="SQ-1",
			charges=[
				_linked_charge_dict(
					service_type="Transport",
					transport_template="TPL-1",
					vehicle_type="20FT",
				),
			],
			lifecycle_jobs=[
				frappe._dict(
					service_type="Transport",
					job_type="Transport Order",
					lifecycle_job_line="",
					idx=1,
				)
			],
		)
		doc.check_permission = lambda *a, **k: None
		with patch("frappe.get_doc", return_value=doc):
			out = get_special_project_booking_choices("SP-1")
		choices = out.get("choices") or []
		self.assertEqual(len(choices), 1)
		self.assertTrue(choices[0].get("creatable"))
		self.assertIn("Transport", out.get("service_type_filters") or [])
		self.assertEqual(
			choices[0].get("suggested_parameters"),
			{"transport_template": "TPL-1", "vehicle_type": "20FT"},
		)

	@patch("logistics.special_projects.special_project_booking_creation.frappe.db.exists", return_value=True)
	@patch("logistics.special_projects.special_project_booking_creation.frappe.get_doc")
	def test_booking_preview_creatable_when_lifecycle_row_matches_charges(self, mock_get_doc, _exists):
		ij_row = frappe._dict(
			name="lj-transport-1",
			idx=3,
			service_type="Transport",
			vehicle_type="10W-WV",
			job_type="",
			job_no=None,
			lifecycle_job_line="",
		)
		doc = frappe._dict(
			doctype="Special Project",
			name="SP-PROJ",
			sales_quote=None,
			charges=[
				_linked_charge_dict(
					service_type="Transport",
					vehicle_type="10W-WV",
					item_code="DELIVERY",
				),
			],
			lifecycle_jobs=[ij_row],
		)
		doc.check_permission = lambda *a, **k: None
		mock_get_doc.return_value = doc
		prev = get_special_project_booking_preview("SP-PROJ", "Transport Order", 3)
		self.assertTrue(prev.get("creatable"), prev.get("not_creatable_message"))

	def test_preview_creatable_with_empty_params_wildcard(self):
		from logistics.special_projects.special_project_booking_creation import (
			_preview_creatability_flags,
			_resolve_scoped_creation_params,
			_validate_scoped_creation_params,
		)

		parent = frappe._dict(
			charges=[
				_linked_charge_dict(
					service_type="Transport",
					item_code="DELIVERY",
				),
			],
		)
		row = frappe._dict(service_type="Transport", idx=4)
		_, scoped, merged = _resolve_scoped_creation_params(
			parent, "Transport Order", row, {}
		)
		self.assertEqual(scoped, {})
		_validate_scoped_creation_params(parent, "Transport", scoped)
		with patch(
			"logistics.utils.internal_job_creation_eligibility.evaluate_internal_job_creation_eligibility",
			return_value={"eligible": True},
		):
			flags = _preview_creatability_flags(
				parent, "Transport Order", merged, scoped, base_creatable=True
			)
		self.assertTrue(flags.get("creatable"), flags.get("not_creatable_message"))

class TestDialogCreatableJobType(UnitTestCase):
	def test_special_project_service_maps_to_project_order(self):
		row = frappe._dict(service_type="Special Project", job_type="")
		self.assertEqual(_dialog_creatable_job_type(row), "Project Order")

	def test_air_service_maps_to_air_booking(self):
		row = frappe._dict(service_type="Air", job_type="")
		self.assertEqual(_dialog_creatable_job_type(row), "Air Booking")


class TestServiceRowParameterFieldSpecs(UnitTestCase):
	def test_programme_charge_specs_without_lifecycle_job_doctype(self):
		sp_doc = frappe._dict(
			charges=[
				_linked_charge_dict(
					service_type="Transport",
					transport_template="TPL-1",
					vehicle_type="20FT",
				),
			]
		)
		with patch(
			"logistics.special_projects.special_project_booking_creation.frappe.db.exists",
			side_effect=lambda dt, name=None: dt == "DocType" and name == "Special Project Service",
		):
			with patch(
				"logistics.special_projects.special_project_booking_creation._service_row_meta",
				return_value=frappe.get_meta("Special Project Service"),
			):
				specs = get_programme_charge_parameter_field_specs(sp_doc, "Transport")
		names = {s["fieldname"] for s in specs}
		self.assertIn("transport_template", names)
		self.assertIn("vehicle_type", names)

	def test_lifecycle_job_parameter_specs_use_special_project_service_meta(self):
		with patch(
			"logistics.special_projects.special_project_booking_creation._service_row_meta",
			return_value=frappe.get_meta("Special Project Service"),
		):
			specs = get_lifecycle_job_parameter_field_specs("Air")
		names = {s["fieldname"] for s in specs}
		self.assertIn("origin_port", names)
		self.assertIn("destination_port", names)


class TestCreateProjectOrderFromSpecialProject(IntegrationTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls._has_lifecycle_jobs = bool(
			frappe.get_meta("Special Project").has_field("lifecycle_jobs")
		)

	def setUp(self):
		super().setUp()
		if not self._has_lifecycle_jobs:
			self.skipTest("Special Project.lifecycle_jobs not installed on this site")

	def test_booking_choices_include_creatable_project_order_row(self):
		company = frappe.db.get_value("Company", {}, "name")
		customer = frappe.db.get_value("Customer", {"disabled": 0}, "name")
		if not company or not customer:
			self.skipTest("Company and Customer required")

		sp = frappe.new_doc("Special Project")
		sp.project_name = f"Test SP Booking Choices {now_datetime()}"
		sp.customer = customer
		sp.company = company
		sp.append(
			"lifecycle_jobs",
			{"service_type": "Special Project", "activity_name": "Phase A"},
		)
		sp.insert(ignore_permissions=True)

		out = get_special_project_booking_choices(sp.name)
		choices = out.get("choices") or []
		sp_rows = [c for c in choices if c.get("job_type") == "Project Order"]
		self.assertTrue(sp_rows)
		self.assertTrue(sp_rows[0].get("creatable"))
		self.assertEqual(sp_rows[0].get("suggested_order_title"), "Phase A")

	def test_create_project_order_copies_only_special_project_charges(self):
		company = frappe.db.get_value("Company", {}, "name")
		customer = frappe.db.get_value("Customer", {"disabled": 0}, "name")
		if not company or not customer:
			self.skipTest("Company and Customer required")

		sp = frappe.new_doc("Special Project")
		sp.project_name = f"Test SP Project Order Create {now_datetime()}"
		sp.customer = customer
		sp.company = company
		sp.append(
			"lifecycle_jobs",
			{"service_type": "Special Project", "activity_name": "Site work"},
		)
		sp.append(
			"charges",
			{
				"service_type": "Special Project",
				"description": "SP line",
			},
		)
		sp.insert(ignore_permissions=True)

		result = create_booking_or_order_from_special_project(
			sp.name,
			"Project Order",
			lifecycle_job_idx=1,
			order_title="Site work order",
		)
		self.assertTrue(result.get("project_order"))
		order = frappe.get_doc("Project Order", result["project_order"])
		self.assertEqual(order.special_project, sp.name)
		self.assertEqual(order.order_title, "Site work order")
		service_types = {(c.service_type or "").strip() for c in order.charges}
		self.assertTrue(
			all(
				(st or "").lower() in ("special project",)
				or "special" in (st or "").lower()
				for st in service_types
			)
			or len(order.charges) == 1
		)
		for ch in order.charges:
			self.assertNotEqual((ch.service_type or "").strip(), "Air")

		sp.reload()
		self.assertEqual(len(sp.lifecycle_jobs), 1)
		row = sp.lifecycle_jobs[0]
		self.assertEqual(row.job_type, "Project Order")
		self.assertEqual(row.job_no, order.name)
		self.assertFalse((row.lifecycle_job_line or "").strip())

	def test_create_project_order_applies_shipment_lines(self):
		company = frappe.db.get_value("Company", {}, "name")
		customer = frappe.db.get_value("Customer", {"disabled": 0}, "name")
		if not company or not customer:
			self.skipTest("Company and Customer required")

		sp = frappe.new_doc("Special Project")
		sp.project_name = f"Test SP Project Order Shipment {now_datetime()}"
		sp.customer = customer
		sp.company = company
		sp.append(
			"lifecycle_jobs",
			{"service_type": "Special Project", "activity_name": "Install phase"},
		)
		sp.append(
			"packages",
			{
				"description": "Solar kit",
				"qty_required": 2,
				"include_on_create": 0,
			},
		)
		sp.insert(ignore_permissions=True)

		shipment_lines = json.dumps(
			[
				{
					"package_row": 1,
					"description": "Solar kit",
					"qty": 1,
				}
			]
		)
		result = create_booking_or_order_from_special_project(
			sp.name,
			"Project Order",
			lifecycle_job_idx=1,
			order_title="Install phase order",
			shipment_lines=shipment_lines,
		)
		self.assertTrue(result.get("project_order"))
		order = frappe.get_doc("Project Order", result["project_order"])
		self.assertEqual(len(order.packages), 1)
		self.assertEqual(order.packages[0].quantity, 1)
		if order.packages[0].meta.get_field("package_row"):
			self.assertEqual(order.packages[0].package_row, 1)

	def test_build_project_order_requires_title_or_suggestion(self):
		company = frappe.db.get_value("Company", {}, "name")
		customer = frappe.db.get_value("Customer", {"disabled": 0}, "name")
		if not company or not customer:
			self.skipTest("Company and Customer required")

		sp = frappe.new_doc("Special Project")
		sp.project_name = f"Test SP Build Order {now_datetime()}"
		sp.customer = customer
		sp.company = company
		sp.insert(ignore_permissions=True)

		order = build_project_order_from_special_project(sp, "Explicit title")
		self.assertEqual(order.order_title, "Explicit title")
		self.assertEqual(order.special_project, sp.name)

	def test_link_planning_service_row_updates_special_project_service_document(self):
		sp = new_special_project_for_test("SP Link Service Order")
		if not sp:
			self.skipTest("Company, Customer, and Cost Center required")
		stage = frappe.db.get_value("Lifecycle Stage", {}, "name")
		if not stage:
			self.skipTest("no lifecycle stage")

		sp.status = "Draft"
		sp.flags.ignore_mandatory = True
		sp.append(
			"special_project_services",
			{"service_type": "Transport", "lifecycle_stage": stage},
		)
		sp.insert(ignore_permissions=True)

		try:
			reloaded = frappe.get_doc("Special Project", sp.name)
			grid_row = reloaded.special_project_services[0]
			self.assertIsInstance(grid_row, dict)

			_link_planning_service_row(
				sp.name, grid_row, "Transport Order", "TO-LINK-TEST"
			)

			service_name = grid_row.get("special_project_service") or grid_row.get("name")
			service = frappe.get_doc("Special Project Service", service_name)
			self.assertEqual(service.job_type, "Transport Order")
			self.assertEqual(service.order_no, "TO-LINK-TEST")
			self.assertFalse(service.job_no)
		finally:
			if frappe.db.exists("Special Project", sp.name):
				project = frappe.db.get_value("Special Project", sp.name, "project")
				frappe.delete_doc(
					"Special Project", sp.name, force=True, ignore_permissions=True
				)
				if project and frappe.db.exists("Project", project):
					try:
						frappe.delete_doc(
							"Project", project, force=True, ignore_permissions=True
						)
					except Exception:
						pass
