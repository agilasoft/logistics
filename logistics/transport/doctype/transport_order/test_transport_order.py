# Copyright (c) 2026, www.agilasoft.com and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from logistics.transport.doctype.transport_order.transport_order import (
	_apply_duplicate_pricing_clear,
	_clear_pricing_after_desk_duplicate,
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

	def test_transport_order_validate_leg_facilities(self):
		"""Test that legs with same from/to facilities are rejected on submit, not on save"""
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
		order.insert()
		with self.assertRaises((frappe.ValidationError, Exception)):
			order.before_submit()


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


class TestTransportOrderDuplicatePricingClear(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_apply_duplicate_pricing_clear_strips_quote_links(self):
		order = frappe.get_doc(
			{
				"doctype": "Transport Order",
				"sales_quote": "SQU-TEST-1109",
				"quote": "SQU-TEST-1109",
				"quote_type": "Sales Quote",
			}
		)
		order.append("charges", {"item_code": "DELIVERY", "service_type": "Transport"})

		_apply_duplicate_pricing_clear(order)

		self.assertEqual(order.sales_quote, None)
		self.assertEqual(order.quote, None)
		self.assertEqual(order.quote_type, None)
		self.assertEqual(order.get("charges"), [])

	def test_clear_pricing_after_desk_duplicate_strips_quote_links(self):
		if not frappe.db.has_column("Transport Order", "logistics_duplicate_from"):
			return

		order = frappe.get_doc(
			{
				"doctype": "Transport Order",
				"logistics_duplicate_from": "TRO-SOURCE",
				"sales_quote": "SQU-TEST-1109",
			}
		)

		_clear_pricing_after_desk_duplicate(order)

		self.assertTrue(order.flags.logistics_duplicate_pricing_cleared)
		self.assertEqual(order.sales_quote, None)
		self.assertEqual(order.logistics_duplicate_from, None)


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


class TestTransportOrderTemplateValidation(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def _ensure_load_type(self, name: str, **flags):
		if frappe.db.exists("Load Type", name):
			doc = frappe.get_doc("Load Type", name)
			for key, value in flags.items():
				doc.set(key, value)
			doc.save(ignore_permissions=True)
			return doc.name

		doc = frappe.new_doc("Load Type")
		doc.load_type_name = name
		doc.description = name
		doc.is_active = 1
		for key, value in flags.items():
			doc.set(key, value)
		doc.insert(ignore_permissions=True)
		return doc.name

	def test_transport_order_rejects_load_type_not_allowed_by_template(self):
		ftl = self._ensure_load_type("FTL", transport=1, non_container=1)
		fcl = self._ensure_load_type("FCL", transport=1, container=1, sea=1)

		tpl = frappe.get_doc(
			{
				"doctype": "Transport Template",
				"code": "TO-TEST-CFS",
				"description": "CFS lane",
				"default_load_type": ftl,
				"legs": [
					{
						"facility_type_from": "Container Freight Station",
						"facility_type_to": "Storage Facility",
					}
				],
				"allowed_load_types": [{"load_type": ftl}],
			}
		)
		tpl.insert(ignore_permissions=True)

		order = frappe.get_doc(
			{
				"doctype": "Transport Order",
				"transport_template": tpl.name,
				"load_type": fcl,
				"transport_job_type": "Container",
			}
		)
		with self.assertRaises(frappe.ValidationError):
			order._validate_transport_template_compatibility()
