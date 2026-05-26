# Copyright (c) 2026, www.agilasoft.com and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from logistics.transport.doctype.transport_order.transport_order import (
	get_vehicle_types_for_transport_order,
)

from logistics.air_freight.tests.test_helpers import (
	setup_basic_master_data,
	create_test_shipper,
	create_test_consignee,
	create_test_unloco,
	create_test_branch,
	create_test_cost_center,
	create_test_profit_center,
)


class TestTransportOrder(FrappeTestCase):
	"""Test cases for Transport Order doctype"""

	def setUp(self):
		"""Set up test data"""
		data = setup_basic_master_data()
		self.company = data["company"]
		self.customer = data["customer"]
		self.shipper = create_test_shipper()
		self.consignee = create_test_consignee()
		create_test_unloco("USLAX", "Los Angeles", "LAX", "US", "Airport")
		create_test_unloco("USJFK", "New York JFK", "JFK", "US", "Airport")
		try:
			self.branch = create_test_branch(self.company)
			self.cost_center = create_test_cost_center(self.company)
			self.profit_center = create_test_profit_center(self.company)
		except Exception:
			self.branch = frappe.db.get_value("Branch", {"custom_company": self.company}, "name")
			self.cost_center = frappe.db.get_value("Cost Center", {"company": self.company, "is_group": 0}, "name")
			self.profit_center = frappe.db.get_value("Profit Center", {"company": self.company}, "name")

	def tearDown(self):
		frappe.db.rollback()

	def test_transport_order_creation(self):
		"""Test creating a basic Transport Order"""
		order = frappe.get_doc({
			"doctype": "Transport Order",
			"company": self.company,
			"customer": self.customer,
			"booking_date": today(),
			"scheduled_date": today(),
			"location_type": "UNLOCO",
			"location_from": "USLAX",
			"location_to": "USJFK",
			"transport_job_type": "Non-Container",
			"branch": self.branch,
			"cost_center": self.cost_center,
			"profit_center": self.profit_center,
		})
		order.append("legs", {
			"facility_type_from": "Shipper",
			"facility_from": self.shipper,
			"facility_type_to": "Consignee",
			"facility_to": self.consignee,
			"scheduled_date": today(),
			"transport_job_type": "Non-Container",
		})
		order.insert()

		self.assertIsNotNone(order.name)
		self.assertEqual(order.company, self.company)
		self.assertEqual(order.customer, self.customer)
		self.assertEqual(len(order.legs), 1)

	def test_transport_order_required_fields(self):
		"""Test that required fields are enforced"""
		order = frappe.get_doc({"doctype": "Transport Order", "booking_date": today()})
		with self.assertRaises((frappe.ValidationError, frappe.MandatoryError)):
			order.insert()

	def test_transport_template_required_before_submit(self):
		"""Transport Template must be set before submit (required for Transport Job creation)."""
		order = frappe.get_doc({
			"doctype": "Transport Order",
			"company": self.company,
			"customer": self.customer,
			"booking_date": today(),
			"scheduled_date": today(),
			"location_type": "UNLOCO",
			"location_from": "USLAX",
			"location_to": "USJFK",
			"transport_job_type": "Non-Container",
			"branch": self.branch,
			"cost_center": self.cost_center,
			"profit_center": self.profit_center,
		})
		order.insert()
		with self.assertRaises(frappe.ValidationError) as ctx:
			order.before_submit()
		self.assertIn("Transport Template", str(ctx.exception))

	def test_transport_order_validate_leg_facilities(self):
		"""Test that legs with same from/to facilities are rejected"""
		order = frappe.get_doc({
			"doctype": "Transport Order",
			"company": self.company,
			"customer": self.customer,
			"booking_date": today(),
			"scheduled_date": today(),
			"location_type": "UNLOCO",
			"location_from": "USLAX",
			"location_to": "USJFK",
			"transport_job_type": "Non-Container",
			"branch": self.branch,
			"cost_center": self.cost_center,
			"profit_center": self.profit_center,
		})
		order.append("legs", {
			"facility_type_from": "Shipper",
			"facility_from": self.shipper,
			"facility_type_to": "Shipper",
			"facility_to": self.shipper,
			"scheduled_date": today(),
			"transport_job_type": "Non-Container",
		})
		with self.assertRaises((frappe.ValidationError, Exception)):
			order.insert()


def _ensure_test_load_type_for_vehicle_filter() -> str:
	sfx = frappe.generate_hash(length=6)
	name = f"TST-VT-LT-{sfx}"
	return frappe.get_doc(
		{
			"doctype": "Load Type",
			"load_type_name": name,
			"description": "Test load type for vehicle filter",
			"is_active": 1,
			"transport": 1,
			"non_container": 1,
			"container": 1,
		}
	).insert(ignore_permissions=True).name


def _ensure_vehicle_type_for_filter(
	code_suffix: str,
	*,
	containerized: int = 0,
	load_type: str | None = None,
) -> str:
	sfx = frappe.generate_hash(length=4)
	code = f"TST-{code_suffix}-{sfx}"
	doc = frappe.get_doc(
		{
			"doctype": "Vehicle Type",
			"code": code,
			"description": f"Test vehicle {code_suffix}",
			"is_active": 1,
			"containerized": containerized,
		}
	)
	if load_type:
		doc.append("allowed_load_types", {"load_type": load_type})
	return doc.insert(ignore_permissions=True).name


class TestTransportOrderChargeSubmitGate(FrappeTestCase):
	"""Submit charge gate tests (no master-data setUp)."""

	def tearDown(self):
		frappe.db.rollback()

	def test_before_submit_blocked_without_transport_charges(self):
		"""Main-service Transport Order cannot submit without a Transport charge line."""
		from logistics.utils.charge_service_type import (
			assert_destination_service_charges_on_submit_unless_internal_job,
		)

		order = frappe.get_doc({"doctype": "Transport Order"})
		with self.assertRaises(frappe.ValidationError) as ctx:
			assert_destination_service_charges_on_submit_unless_internal_job(order)
		self.assertIn("Transport", str(ctx.exception))

	def test_before_submit_allowed_with_transport_charge(self):
		"""At least one Transport service_type charge satisfies the submit gate."""
		from logistics.utils.charge_service_type import (
			assert_destination_service_charges_on_submit_unless_internal_job,
		)

		order = frappe.get_doc({"doctype": "Transport Order"})
		order.append("charges", {"service_type": "Transport"})
		assert_destination_service_charges_on_submit_unless_internal_job(order)

	def test_before_submit_allowed_internal_job_without_charges(self):
		"""Internal jobs may submit without Transport charge rows."""
		from logistics.utils.charge_service_type import (
			assert_destination_service_charges_on_submit_unless_internal_job,
		)

		order = frappe.get_doc({"doctype": "Transport Order", "is_internal_job": 1})
		assert_destination_service_charges_on_submit_unless_internal_job(order)


class TestTransportOrderVehicleTypeFilter(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_non_container_excludes_containerized_vehicle_types(self):
		load_type = _ensure_test_load_type_for_vehicle_filter()
		vt_cnt = _ensure_vehicle_type_for_filter("CNT", containerized=1, load_type=load_type)
		vt_nc = _ensure_vehicle_type_for_filter("NC", containerized=0, load_type=load_type)

		result = get_vehicle_types_for_transport_order(
			transport_job_type="Non-Container",
			load_type=load_type,
		)
		names = result["vehicle_types"]
		self.assertIn(vt_nc, names)
		self.assertNotIn(vt_cnt, names)

	def test_container_excludes_non_containerized_vehicle_types(self):
		load_type = _ensure_test_load_type_for_vehicle_filter()
		vt_cnt = _ensure_vehicle_type_for_filter("CNT", containerized=1, load_type=load_type)
		vt_nc = _ensure_vehicle_type_for_filter("NC", containerized=0, load_type=load_type)

		result = get_vehicle_types_for_transport_order(
			transport_job_type="Container",
			load_type=load_type,
		)
		names = result["vehicle_types"]
		self.assertIn(vt_cnt, names)
		self.assertNotIn(vt_nc, names)

	def test_job_type_only_without_load_type(self):
		vt_cnt = _ensure_vehicle_type_for_filter("CNT", containerized=1)
		vt_nc = _ensure_vehicle_type_for_filter("NC", containerized=0)

		result = get_vehicle_types_for_transport_order(transport_job_type="Non-Container")
		names = result["vehicle_types"]
		self.assertIn(vt_nc, names)
		self.assertNotIn(vt_cnt, names)

	def test_empty_when_no_job_type_and_no_load_type(self):
		self.assertEqual(
			get_vehicle_types_for_transport_order()["vehicle_types"],
			[],
		)
