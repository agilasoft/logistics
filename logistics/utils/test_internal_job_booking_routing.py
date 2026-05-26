# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Internal Air/Sea Booking create: Sales Quote routing_legs must populate (#926, #936)."""

import unittest

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import cint, today

from logistics.air_freight.tests.test_helpers import create_test_item, create_test_unloco
from logistics.utils.test_internal_job_transport_order_container import (
	_existing_logistics_master,
	_ensure_transport_template,
)
from logistics.utils.internal_job_from_source import (
	_create_air_booking_from_sea_shipment,
	_create_air_booking_from_transport_job,
	_create_sea_booking_from_air_shipment,
)


def _ensure_sea_transport_mode():
	name = frappe.db.get_value(
		"Transport Mode",
		{"sea": 1, "is_active": 1},
		"name",
		order_by="name asc",
	)
	if name:
		return name
	suffix = frappe.generate_hash(length=6)
	doc = frappe.new_doc("Transport Mode")
	doc.mode_code = f"TSM-{suffix}"
	doc.mode_name = f"Test Sea Mode {suffix}"
	doc.primary_document = f"TSM-DOC-{suffix}"
	doc.sea = 1
	doc.is_active = 1
	doc.insert(ignore_permissions=True)
	return doc.name


def _ensure_air_transport_mode():
	name = frappe.db.get_value(
		"Transport Mode",
		{"air": 1, "is_active": 1},
		"name",
		order_by="name asc",
	)
	if name:
		return name
	suffix = frappe.generate_hash(length=6)
	doc = frappe.new_doc("Transport Mode")
	doc.mode_code = f"TAM-{suffix}"
	doc.mode_name = f"Test Air Mode {suffix}"
	doc.primary_document = f"TAM-DOC-{suffix}"
	doc.air = 1
	doc.is_active = 1
	doc.insert(ignore_permissions=True)
	return doc.name


def _ensure_sea_load_type():
	sfx = frappe.generate_hash(length=6)
	name = f"TST-IJ-SEA-LT-{sfx}"
	if frappe.db.exists("Load Type", name):
		return name
	lt = frappe.get_doc(
		{
			"doctype": "Load Type",
			"load_type_name": name,
			"description": "Test sea load type for IJ routing tests",
			"is_active": 1,
			"sea": 1,
		}
	)
	lt.insert(ignore_permissions=True)
	return lt.name


def _ensure_air_freight_settings(company, branch, cost_center, profit_center):
	if frappe.db.exists("Air Freight Settings", company):
		doc = frappe.get_doc("Air Freight Settings", company)
	else:
		doc = frappe.get_doc({"doctype": "Air Freight Settings", "company": company})
	doc.default_branch = branch
	doc.default_cost_center = cost_center
	doc.default_profit_center = profit_center
	doc.save(ignore_permissions=True)


def _ensure_sea_freight_settings(company, cost_center, profit_center):
	if frappe.db.exists("Sea Freight Settings", company):
		doc = frappe.get_doc("Sea Freight Settings", company)
	else:
		doc = frappe.get_doc({"doctype": "Sea Freight Settings", "company": company})
		doc.flags.ignore_validate = True
		doc.insert(ignore_permissions=True)
	doc.default_cost_center = cost_center
	doc.default_profit_center = profit_center
	doc.save(ignore_permissions=True)


def _charge_row(item_code, service_type):
	return {
		"service_type": service_type,
		"item_code": item_code,
		"origin_port": "USLAX",
		"destination_port": "USJFK",
		"direction": "Export",
		"quantity": 1,
		"unit_rate": 100,
		"cost_quantity": 1,
		"unit_cost": 50,
	}


def _sales_quote_with_air_routing(
	company,
	customer,
	shipper,
	consignee,
	air_mode,
	item_code,
	*,
	branch=None,
	cost_center=None,
	profit_center=None,
	sea_mode=None,
):
	"""Sales Quote with one Air routing leg and air+sea charges (multimodal-style)."""
	rep = frappe.db.get_value("Employee", {"custom_sales_rep": 1}, "name") or frappe.db.get_value(
		"Employee", {}, "name"
	)
	sq = frappe.get_doc(
		{
			"doctype": "Sales Quote",
			"quotation_type": "Regular",
			"naming_series": "SQU.#########",
			"company": company,
			"customer": customer,
			"date": today(),
			"valid_until": today(),
			"shipper": shipper,
			"consignee": consignee,
			"main_service": "Sea",
			"origin_port": "USLAX",
			"destination_port": "USJFK",
			"branch": branch,
			"cost_center": cost_center,
			"profit_center": profit_center,
			"sales_rep": rep,
			"operations_rep": rep,
			"customer_service_rep": rep,
		}
	)
	sq.append(
		"routing_legs",
		{
			"mode": air_mode,
			"type": "Main",
			"is_main_job": 0 if sea_mode else 1,
			"origin": "USLAX",
			"destination": "USJFK",
		},
	)
	if sea_mode:
		sq.append(
			"routing_legs",
			{
				"mode": sea_mode,
				"type": "Main",
				"is_main_job": 1,
				"origin": "USLAX",
				"destination": "USJFK",
			},
		)
	sq.append("charges", _charge_row(item_code, "Air"))
	sq.append("charges", _charge_row(item_code, "Sea"))
	sq.flags.ignore_validate = True
	sq.insert(ignore_permissions=True)
	return sq.name


class TestInternalJobBookingRouting(FrappeTestCase):
	def setUp(self):
		m = _existing_logistics_master()
		self.company = m["company"]
		self.customer = m["customer"]
		self.shipper = m["shipper"]
		self.consignee = m["consignee"]
		self.branch = m["branch"]
		self.cost_center = m["cost_center"]
		self.profit_center = m["profit_center"]
		create_test_unloco("USLAX", "Los Angeles", "LAX", "US", "Port")
		create_test_unloco("USJFK", "New York", "JFK", "US", "Port")
		self.item_code = frappe.db.get_value("Item", {}, "name") or create_test_item()
		self.air_mode = _ensure_air_transport_mode()
		self.sea_mode = _ensure_sea_transport_mode()
		self.sea_load_type = _ensure_sea_load_type()
		_ensure_air_freight_settings(
			self.company, self.branch, self.cost_center, self.profit_center
		)
		_ensure_sea_freight_settings(self.company, self.cost_center, self.profit_center)

	def tearDown(self):
		frappe.db.rollback()

	def _make_sea_shipment_with_air_charges(
		self,
		sales_quote,
		*,
		sea_routing_vessel=None,
		sea_routing_voyage_no=None,
	):
		sh = frappe.get_doc(
			{
				"doctype": "Sea Shipment",
				"booking_date": today(),
				"company": self.company,
				"local_customer": self.customer,
				"shipper": self.shipper,
				"consignee": self.consignee,
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"branch": self.branch,
				"cost_center": self.cost_center,
				"profit_center": self.profit_center,
				"direction": "Export",
				"weight": 20,
				"volume": 0.2,
				"load_type": self.sea_load_type,
				"sales_quote": sales_quote,
				"is_main_service": 1,
			}
		)
		if sea_routing_vessel or sea_routing_voyage_no:
			sh.append(
				"routing_legs",
				{
					"mode": self.sea_mode,
					"type": "Main",
					"load_port": "USLAX",
					"discharge_port": "USJFK",
					"vessel": sea_routing_vessel,
					"voyage_no": sea_routing_voyage_no,
				},
			)
		sh.append(
			"charges",
			{
				"service_type": "Air",
				"item_code": self.item_code,
				"origin_port": "USLAX",
				"destination_port": "USJFK",
			},
		)
		sh.insert(ignore_permissions=True)
		return sh.name

	def _make_transport_job_with_air_charges(self, sales_quote):
		vehicle_type = frappe.db.get_value("Vehicle Type", {"is_active": 1}, "name")
		job = frappe.get_doc(
			{
				"doctype": "Transport Job",
				"customer": self.customer,
				"company": self.company,
				"transport_job_type": "Non-Container",
				"vehicle_type": vehicle_type,
				"transport_template": _ensure_transport_template(),
				"booking_date": today(),
				"branch": self.branch,
				"cost_center": self.cost_center,
				"profit_center": self.profit_center,
				"sales_quote": sales_quote,
				"shipper": self.shipper,
				"consignee": self.consignee,
			}
		)
		job.append(
			"charges",
			{
				"service_type": "Air",
				"item_code": self.item_code,
				"rate": 100,
			},
		)
		job.flags.ignore_validate = True
		job.insert(ignore_permissions=True)
		return job.name

	def _make_air_shipment(self, sales_quote):
		sh = frappe.get_doc(
			{
				"doctype": "Air Shipment",
				"booking_date": today(),
				"company": self.company,
				"local_customer": self.customer,
				"shipper": self.shipper,
				"consignee": self.consignee,
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"branch": self.branch,
				"cost_center": self.cost_center,
				"profit_center": self.profit_center,
				"direction": "Export",
				"sales_quote": sales_quote,
			}
		)
		sh.append(
			"packages",
			{
				"package_type": "Box",
				"quantity": 1,
				"weight": 10,
				"volume": 0.1,
			},
		)
		sh.append(
			"charges",
			{
				"service_type": "Sea",
				"item_code": self.item_code,
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"rate": 100,
			},
		)
		sh.flags.ignore_validate = True
		sh.insert(ignore_permissions=True)
		return sh.name

	def _assert_booking_routing_from_quote(self, booking_name, doctype):
		booking = frappe.get_doc(doctype, booking_name)
		self.assertGreater(
			len(booking.routing_legs or []),
			0,
			f"{doctype} {booking_name} should have routing legs from Sales Quote",
		)
		leg = booking.routing_legs[0]
		self.assertEqual(leg.load_port, "USLAX")
		self.assertEqual(leg.discharge_port, "USJFK")
		self.assertEqual(getattr(leg, "transport_mode_air", 0), 1)

	def test_air_booking_from_sea_shipment_populates_routing_when_main_has_air_charges(self):
		sq = _sales_quote_with_air_routing(
			self.company,
			self.customer,
			self.shipper,
			self.consignee,
			self.air_mode,
			self.item_code,
			branch=self.branch,
			cost_center=self.cost_center,
			profit_center=self.profit_center,
		)
		sh_name = self._make_sea_shipment_with_air_charges(sq)
		res = _create_air_booking_from_sea_shipment(sh_name, internal_job_detail_idx=None)
		ab_name = res.get("air_booking")
		self.assertTrue(ab_name)
		ab = frappe.get_doc("Air Booking", ab_name)
		self.assertEqual(ab.is_internal_job, 1)
		self.assertEqual(ab.main_job_type, "Sea Shipment")
		self.assertEqual(ab.main_job, sh_name)
		self.assertGreater(len(ab.charges or []), 0, "charges should copy from main job air rows")
		self._assert_booking_routing_from_quote(ab_name, "Air Booking")

	def test_air_booking_from_sea_shipment_copies_vessel_voyage_from_main_routing(self):
		"""#936: sea operational fields on main routing legs overlay onto internal Air Booking."""
		sq = _sales_quote_with_air_routing(
			self.company,
			self.customer,
			self.shipper,
			self.consignee,
			self.air_mode,
			self.item_code,
			branch=self.branch,
			cost_center=self.cost_center,
			profit_center=self.profit_center,
			sea_mode=self.sea_mode,
		)
		sh_name = self._make_sea_shipment_with_air_charges(
			sq,
			sea_routing_vessel="TEST-VESSEL-936",
			sea_routing_voyage_no="VOY-936",
		)
		res = _create_air_booking_from_sea_shipment(sh_name, internal_job_detail_idx=None)
		ab_name = res.get("air_booking")
		self.assertTrue(ab_name)
		ab = frappe.get_doc("Air Booking", ab_name)
		sea_legs = [leg for leg in (ab.routing_legs or []) if cint(getattr(leg, "transport_mode_sea", 0))]
		self.assertGreater(len(sea_legs), 0, "multimodal quote should yield a sea routing leg on Air Booking")
		leg = sea_legs[0]
		self.assertEqual(getattr(leg, "vessel", None), "TEST-VESSEL-936")
		self.assertEqual(getattr(leg, "voyage_no", None), "VOY-936")

	def test_air_booking_from_transport_job_populates_routing_with_overlay(self):
		sq = _sales_quote_with_air_routing(
			self.company,
			self.customer,
			self.shipper,
			self.consignee,
			self.air_mode,
			self.item_code,
			branch=self.branch,
			cost_center=self.cost_center,
			profit_center=self.profit_center,
		)
		job_name = self._make_transport_job_with_air_charges(sq)
		res = _create_air_booking_from_transport_job(job_name, internal_job_detail_idx=None)
		ab_name = res.get("air_booking")
		self.assertTrue(ab_name)
		ab = frappe.get_doc("Air Booking", ab_name)
		self.assertEqual(ab.main_job_type, "Transport Job")
		self.assertGreater(len(ab.charges or []), 0)
		self._assert_booking_routing_from_quote(ab_name, "Air Booking")

	def test_sea_booking_from_air_shipment_still_populates_routing(self):
		sea_mode = frappe.db.get_value(
			"Transport Mode",
			{"sea": 1, "is_active": 1},
			"name",
			order_by="name asc",
		)
		if not sea_mode:
			suffix = frappe.generate_hash(length=6)
			tm = frappe.new_doc("Transport Mode")
			tm.mode_code = f"TSM-{suffix}"
			tm.mode_name = f"Test Sea Mode {suffix}"
			tm.primary_document = f"TSM-DOC-{suffix}"
			tm.sea = 1
			tm.is_active = 1
			tm.insert(ignore_permissions=True)
			sea_mode = tm.name

		rep = frappe.db.get_value("Employee", {"custom_sales_rep": 1}, "name") or frappe.db.get_value(
			"Employee", {}, "name"
		)
		sq = frappe.get_doc(
			{
				"doctype": "Sales Quote",
				"quotation_type": "Regular",
				"naming_series": "SQU.#########",
				"company": self.company,
				"customer": self.customer,
				"date": today(),
				"valid_until": today(),
				"shipper": self.shipper,
				"consignee": self.consignee,
				"main_service": "Air",
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"branch": self.branch,
				"cost_center": self.cost_center,
				"profit_center": self.profit_center,
				"sales_rep": rep,
				"operations_rep": rep,
				"customer_service_rep": rep,
			}
		)
		sq.append(
			"routing_legs",
			{
				"mode": sea_mode,
				"type": "Main",
				"is_main_job": 1,
				"origin": "USLAX",
				"destination": "USJFK",
			},
		)
		sq.append("charges", _charge_row(self.item_code, "Sea"))
		sq.flags.ignore_validate = True
		sq.insert(ignore_permissions=True)

		as_name = self._make_air_shipment(sq.name)
		res = _create_sea_booking_from_air_shipment(as_name, internal_job_detail_idx=None)
		sb_name = res.get("sea_booking")
		self.assertTrue(sb_name)
		sb = frappe.get_doc("Sea Booking", sb_name)
		self.assertEqual(sb.is_internal_job, 1)
		self.assertEqual(sb.main_job_type, "Air Shipment")
		self.assertGreater(len(sb.routing_legs or []), 0)
		leg = sb.routing_legs[0]
		self.assertEqual(leg.load_port, "USLAX")
		self.assertEqual(leg.discharge_port, "USJFK")
		self.assertEqual(getattr(leg, "transport_mode_sea", 0), 1)


def run_integration_tests():
	"""Entry point: bench --site SITE execute logistics.utils.test_internal_job_booking_routing.run_integration_tests"""
	frappe.flags.in_test = True
	suite = unittest.TestLoader().loadTestsFromTestCase(TestInternalJobBookingRouting)
	result = unittest.TextTestRunner(verbosity=2).run(suite)
	frappe.db.rollback()
	return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
	unittest.main()
