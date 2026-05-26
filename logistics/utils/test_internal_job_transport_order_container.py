# Copyright (c) 2026, Agilasoft and contributors
# Licensed under the MIT License. See license.txt

import unittest

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from logistics.utils.container_validation import calculate_iso6346_check_digit, normalize_container_number
from logistics.utils.internal_job_from_source import _create_transport_order_from_transport_job
from logistics.utils.transport_job_type import (
	apply_container_transport_context_to_order,
	internal_job_detail_indicates_container,
)


def _iso_container(serial6: str) -> str:
	base = "MSCU" + serial6
	return base + str(calculate_iso6346_check_digit(base + "0"))


def _ensure_container_type() -> str:
	ct = frappe.db.get_value("Container Type", {"active": 1}, "name")
	if ct:
		return ct
	return frappe.get_doc(
		{
			"doctype": "Container Type",
			"code": "TST-IJ-CT",
			"description": "Test container type for IJ transport order tests",
			"active": 1,
		}
	).insert(ignore_permissions=True).name


def _existing_logistics_master():
	"""Reuse site master data (avoid creating Company/Cost Center in tests)."""
	company = frappe.defaults.get_defaults().get("company")
	if not company:
		company = frappe.db.get_value("Company", {}, "name")
	customer = frappe.db.get_value("Customer", {}, "name")
	shipper = frappe.db.get_value("Shipper", {}, "name")
	consignee = frappe.db.get_value("Consignee", {}, "name")
	branch = frappe.db.get_value("Branch", {"custom_company": company}, "name") if company else None
	cost_center = (
		frappe.db.get_value("Cost Center", {"company": company, "is_group": 0}, "name")
		if company
		else None
	)
	profit_center = frappe.db.get_value("Profit Center", {}, "name")
	if not all([company, customer, shipper, consignee]):
		raise unittest.SkipTest("Site missing Company/Customer/Shipper/Consignee for integration tests")
	return {
		"company": company,
		"customer": customer,
		"shipper": shipper,
		"consignee": consignee,
		"branch": branch,
		"cost_center": cost_center,
		"profit_center": profit_center,
	}


def _ensure_transport_template() -> str:
	tpl = frappe.db.get_value("Transport Template", {}, "name")
	if tpl:
		return tpl
	sfx = frappe.generate_hash(length=4)
	return frappe.get_doc(
		{
			"doctype": "Transport Template",
			"template_code": f"TST-TPL-{sfx}",
			"description": "Test transport template",
			"is_active": 1,
		}
	).insert(ignore_permissions=True).name


def _ensure_vehicle_type() -> str:
	vt = frappe.db.get_value("Vehicle Type", {"is_active": 1}, "name")
	if vt:
		return vt
	sfx = frappe.generate_hash(length=4)
	return frappe.get_doc(
		{
			"doctype": "Vehicle Type",
			"code": f"TST-VT-{sfx}",
			"description": "Test vehicle type",
			"is_active": 1,
		}
	).insert(ignore_permissions=True).name


def _ensure_load_type_allows_container() -> str:
	lt = frappe.db.get_value("Load Type", {"container": 1, "is_active": 1}, "name")
	if lt:
		return lt
	sfx = frappe.generate_hash(length=6)
	return frappe.get_doc(
		{
			"doctype": "Load Type",
			"load_type_name": f"TST-Cntr-LT-{sfx}",
			"description": "Test load type (container allowed)",
			"is_active": 1,
			"transport": 1,
			"container": 1,
			"non_container": 1,
		}
	).insert(ignore_permissions=True).name


class TestInternalJobTransportOrderContainer(FrappeTestCase):
	def test_internal_job_detail_indicates_container_requires_both_fields(self):
		ct = _ensure_container_type()
		cn = _iso_container("111111")
		self.assertTrue(
			internal_job_detail_indicates_container(
				{"container_type": ct, "container_no": cn}
			)
		)
		self.assertFalse(internal_job_detail_indicates_container({"container_type": ct}))
		self.assertFalse(internal_job_detail_indicates_container({"container_no": cn}))

	def test_apply_container_context_upgrades_transport_order(self):
		ct = _ensure_container_type()
		cn = _iso_container("222222")
		lt = _ensure_load_type_allows_container()
		order = frappe.new_doc("Transport Order")
		order.transport_job_type = "Non-Container"
		order.load_type = lt
		ij = {"container_type": ct, "container_no": cn, "load_type": lt}
		apply_container_transport_context_to_order(order, ij)
		self.assertEqual(order.transport_job_type, "Container")
		self.assertEqual(order.container_type, ct)
		self.assertEqual(normalize_container_number(order.container_no), normalize_container_number(cn))

	def test_transport_job_to_transport_order_container_from_ij_row(self):
		ct = _ensure_container_type()
		cn = _iso_container("333333")
		lt = _ensure_load_type_allows_container()
		m = _existing_logistics_master()
		vehicle_type = _ensure_vehicle_type()

		job = frappe.get_doc(
			{
				"doctype": "Transport Job",
				"customer": m["customer"],
				"company": m["company"],
				"shipper": m["shipper"],
				"consignee": m["consignee"],
				"booking_date": today(),
				"scheduled_date": today(),
				"transport_job_type": "Non-Container",
				"transport_template": _ensure_transport_template(),
				"vehicle_type": vehicle_type,
				"branch": m["branch"],
				"cost_center": m["cost_center"],
				"profit_center": m["profit_center"],
			}
		)
		job.append(
			"internal_job_details",
			{
				"service_type": "Transport",
				"job_type": "Transport Order",
				"container_type": ct,
				"container_no": cn,
				"load_type": lt,
			},
		)
		job.insert(ignore_permissions=True)
		frappe.db.commit()

		res = _create_transport_order_from_transport_job(job.name, internal_job_detail_idx=1)
		to = frappe.get_doc("Transport Order", res["transport_order"])
		self.assertEqual(to.transport_job_type, "Container")
		self.assertEqual(to.container_type, ct)
		self.assertEqual(normalize_container_number(to.container_no), normalize_container_number(cn))
		self.assertEqual(to.is_internal_job, 1)
		self.assertEqual(to.main_job_type, "Transport Job")
		self.assertEqual(to.main_job, job.name)

	def test_transport_job_ij_container_type_only_stays_non_container(self):
		ct = _ensure_container_type()
		m = _existing_logistics_master()
		job = frappe.get_doc(
			{
				"doctype": "Transport Job",
				"customer": m["customer"],
				"company": m["company"],
				"booking_date": today(),
				"scheduled_date": today(),
				"transport_job_type": "Non-Container",
				"transport_template": _ensure_transport_template(),
				"vehicle_type": _ensure_vehicle_type(),
				"branch": m["branch"],
				"cost_center": m["cost_center"],
				"profit_center": m["profit_center"],
			}
		)
		job.append(
			"internal_job_details",
			{
				"service_type": "Transport",
				"job_type": "Transport Order",
				"container_type": ct,
			},
		)
		job.insert(ignore_permissions=True)
		frappe.db.commit()

		res = _create_transport_order_from_transport_job(job.name, internal_job_detail_idx=1)
		to = frappe.get_doc("Transport Order", res["transport_order"])
		self.assertEqual(to.transport_job_type, "Non-Container")

	def test_sea_shipment_ij_container_type_and_no_without_header_container_type(self):
		from logistics.air_freight.tests.test_helpers import create_test_unloco
		from logistics.utils.module_integration import create_transport_order_from_sea_shipment

		ct = _ensure_container_type()
		cn = _iso_container("444444")
		m = _existing_logistics_master()
		company = m["company"]
		customer = m["customer"]
		shipper = m["shipper"]
		consignee = m["consignee"]
		branch = m["branch"]
		cost_center = m["cost_center"]
		profit_center = m["profit_center"]
		create_test_unloco("USLAX", "Los Angeles", "LAX", "US", "Airport")
		create_test_unloco("USJFK", "New York JFK", "JFK", "US", "Airport")

		uom = frappe.db.get_value("UOM", {"enabled": 1}, "name")
		comm = frappe.db.get_value("Commodity", {"active": 1}, "name")
		if not comm:
			comm = frappe.get_doc(
				{"doctype": "Commodity", "commodity_name": "TST-IJ-COMM", "active": 1}
			).insert(ignore_permissions=True).name

		booking = frappe.get_doc(
			{
				"doctype": "Sea Booking",
				"booking_date": today(),
				"company": company,
				"local_customer": customer,
				"direction": "Export",
				"shipper": shipper,
				"consignee": consignee,
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"branch": branch,
				"cost_center": cost_center,
				"profit_center": profit_center,
			}
		)
		booking.insert(ignore_permissions=True)

		shipment = frappe.get_doc(
			{
				"doctype": "Sea Shipment",
				"booking_date": today(),
				"company": company,
				"local_customer": customer,
				"shipper": shipper,
				"consignee": consignee,
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"direction": "Export",
				"sea_booking": booking.name,
				"branch": branch,
				"cost_center": cost_center,
				"profit_center": profit_center,
			}
		)
		shipment.append(
			"packages",
			{"commodity": comm, "no_of_packs": 1, "uom": uom, "container": cn},
		)
		shipment.append("routing_legs", {"type": "Pre-carriage"})
		shipment.append(
			"internal_job_details",
			{
				"service_type": "Transport",
				"job_type": "Transport Order",
				"container_type": ct,
				"container_no": cn,
			},
		)
		shipment.insert(ignore_permissions=True)
		frappe.db.commit()

		res = create_transport_order_from_sea_shipment(
			shipment.name, internal_job_detail_idx=1
		)
		to = frappe.get_doc("Transport Order", res["transport_order"])
		self.assertEqual(to.transport_job_type, "Container")
		self.assertEqual(to.container_type, ct)
		self.assertEqual(normalize_container_number(to.container_no), normalize_container_number(cn))

	def tearDown(self):
		frappe.db.rollback()
