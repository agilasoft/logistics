# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase, UnitTestCase


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

from logistics.special_projects.special_project_booking_creation import (
	_apply_air_sea_corridor_ports_from_context,
	_apply_sales_quote_parties_to_target,
	_dialog_creatable_job_type,
	_set_main_service_for_one_off_quote_target,
	create_booking_or_order_from_special_project,
	get_special_project_booking_choices,
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
				_mock_charge(
					service_type="Air",
					item_code=item,
					estimated_revenue=100,
					rate=100,
					quantity=1,
				),
				_mock_charge(service_type="Transport", item_code=item, rate=50),
			]
		)
		row = frappe._dict(service_type="Air")
		booking = frappe.new_doc("Air Booking")
		n = populate_operational_charges_from_special_project(sp, booking, row)
		self.assertEqual(n, 1)
		self.assertEqual(len(booking.charges), 1)
		self.assertEqual((booking.charges[0].service_type or "").strip(), "Air")

	def test_strict_pin_excludes_charge_for_different_row(self):
		item = _ensure_test_sp_charge_item()

		# Air charge pinned to lifecycle row 1; creating from row 6 must NOT match strictly.
		sp = frappe._dict(
			charges=[
				_mock_charge(
					service_type="Air",
					lifecycle_job_row=1,
					item_code=item,
					rate=100,
					quantity=1,
				),
			]
		)
		row = frappe._dict(service_type="Air", idx=6)
		booking = frappe.new_doc("Air Booking")
		n = populate_operational_charges_from_special_project(sp, booking, row)
		self.assertEqual(n, 0)

	def test_ignore_pin_falls_back_to_service_type_match(self):
		item = _ensure_test_sp_charge_item()

		# Mirrors the user's screenshot: Air charges pinned to row 1, Air Booking created from
		# row 6. The strict pass returns 0; ignore_pin=True must pick them up by service type.
		sp = frappe._dict(
			charges=[
				_mock_charge(
					service_type="Air",
					lifecycle_job_row=1,
					item_code=item,
					rate=100,
					quantity=1,
				),
				_mock_charge(
					service_type="Sea",
					lifecycle_job_row=2,
					item_code=item,
					rate=200,
					quantity=1,
				),
				_mock_charge(
					service_type="Transport",
					lifecycle_job_row=3,
					item_code=item,
					rate=300,
					quantity=1,
				),
			]
		)
		row = frappe._dict(service_type="Air", idx=6)
		booking = frappe.new_doc("Air Booking")
		n = populate_operational_charges_from_special_project(
			sp, booking, row, ignore_pin=True
		)
		self.assertEqual(n, 1)
		self.assertEqual(len(booking.charges), 1)
		self.assertEqual((booking.charges[0].service_type or "").strip(), "Air")


class TestAirSeaCorridorPortsFromContext(UnitTestCase):
	def test_fills_ports_from_sales_quote_when_lifecycle_row_blank(self):
		sp = frappe._dict(sales_quote="SQ-CORRIDOR-TEST")
		booking = frappe.new_doc("Air Booking")
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
		sp.project_name = "Test SP PJ Sales Quote"
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
		sp.project_name = "Test SP PJ SQ Fallback"
		sp.customer = customer
		sp.company = company
		sp.sales_quote = sq_name
		sp.insert(ignore_permissions=True)

		order = build_project_order_from_special_project(sp, "Order no quote field")
		self.assertFalse(getattr(order, "sales_quote", None))
		job = _build_project_job_from_order(order, "Job fallback quote")
		self.assertEqual(job.sales_quote, sq_name)


class TestDialogCreatableJobType(UnitTestCase):
	def test_special_project_service_maps_to_project_order(self):
		row = frappe._dict(service_type="Special Project", job_type="")
		self.assertEqual(_dialog_creatable_job_type(row), "Project Order")

	def test_air_service_maps_to_air_booking(self):
		row = frappe._dict(service_type="Air", job_type="")
		self.assertEqual(_dialog_creatable_job_type(row), "Air Booking")


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
		sp.project_name = "Test SP Booking Choices"
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
		sp.project_name = "Test SP Project Order Create"
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
				"lifecycle_job_row": 1,
				"description": "SP line",
			},
		)
		sp.append(
			"charges",
			{
				"service_type": "Air",
				"description": "Air line",
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
		row = sp.lifecycle_jobs[0]
		self.assertEqual(row.job_type, "Project Order")
		self.assertEqual(row.job_no, order.name)

	def test_build_project_order_requires_title_or_suggestion(self):
		company = frappe.db.get_value("Company", {}, "name")
		customer = frappe.db.get_value("Customer", {"disabled": 0}, "name")
		if not company or not customer:
			self.skipTest("Company and Customer required")

		sp = frappe.new_doc("Special Project")
		sp.project_name = "Test SP Build Order"
		sp.customer = customer
		sp.company = company
		sp.insert(ignore_permissions=True)

		order = build_project_order_from_special_project(sp, "Explicit title")
		self.assertEqual(order.order_title, "Explicit title")
		self.assertEqual(order.special_project, sp.name)
