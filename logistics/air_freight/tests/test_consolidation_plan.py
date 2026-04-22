# Copyright (c) 2026, AgilaSoft and contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, get_datetime, today

from logistics.air_freight.tests.test_helpers import (
	create_test_airline,
	setup_basic_master_data,
	create_test_branch,
	create_test_consignee,
	create_test_cost_center,
	create_test_profit_center,
	create_test_shipper,
	create_test_unloco,
)
def _ensure_test_air_transport_mode():
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


def _ensure_air_freight_settings_defaults(company, branch, cost_center, profit_center):
	if frappe.db.exists("Air Freight Settings", company):
		doc = frappe.get_doc("Air Freight Settings", company)
	else:
		doc = frappe.get_doc({"doctype": "Air Freight Settings", "company": company})
	doc.default_branch = branch
	doc.default_cost_center = cost_center
	doc.default_profit_center = profit_center
	doc.save(ignore_permissions=True)


class TestAirConsolidationPlanFlow(FrappeTestCase):
	def setUp(self):
		data = setup_basic_master_data()
		self.company = data["company"]
		self.customer = data["customer"]
		create_test_unloco("USLAX", "Los Angeles", "LAX", "US", "Airport")
		create_test_unloco("USJFK", "New York JFK", "JFK", "US", "Airport")
		self.branch = create_test_branch(self.company)
		self.cost_center = create_test_cost_center(self.company)
		self.profit_center = create_test_profit_center(self.company)
		self.shipper = create_test_shipper()
		self.consignee = create_test_consignee()
		_ensure_air_freight_settings_defaults(
			self.company, self.branch, self.cost_center, self.profit_center
		)
		create_test_airline("TA", "Test Airline")

	def tearDown(self):
		frappe.db.rollback()

	def _make_air_shipment(self):
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
				"weight": 10,
				"chargeable": 10,
				"volume": 0.1,
			}
		)
		sh.insert()
		return sh.name

	def _make_air_shipment_for_fetch(self, etd_date, flight_no="TA101", with_main_leg=True):
		mode = _ensure_test_air_transport_mode()
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
				"weight": 10,
				"chargeable": 10,
				"volume": 0.1,
				"airline": "TA",
				"etd": etd_date,
			}
		)
		if with_main_leg:
			sh.append(
				"routing_legs",
				{
					"mode": mode,
					"type": "Main",
					"flight_no": flight_no,
					"airline": "TA",
					"load_port": "USLAX",
					"discharge_port": "USJFK",
				},
			)
		sh.insert()
		return sh.name

	def test_consolidation_without_plan_fails(self):
		sh = self._make_air_shipment()
		consol = frappe.get_doc(
			{
				"doctype": "Air Consolidation",
				"naming_series": "AC-{MM}-{YYYY}-{####}",
				"consolidation_date": today(),
				"consolidation_type": "Direct Consolidation",
				"status": "Draft",
				"company": self.company,
				"branch": self.branch,
				"cost_center": self.cost_center,
				"profit_center": self.profit_center,
				"origin_airport": "USLAX",
				"destination_airport": "USJFK",
			}
		)
		consol.append(
			"consolidation_routes",
			{
				"route_sequence": 1,
				"route_type": "Direct",
				"origin_airport": "USLAX",
				"destination_airport": "USJFK",
				"airline": "TA",
				"flight_number": "TBA",
				"departure_date": today(),
				"departure_time": "10:00:00",
				"arrival_date": add_days(today(), 1),
				"arrival_time": "12:00:00",
				"dangerous_goods_allowed": 1,
			},
		)
		consol.append(
			"consolidation_packages",
			{
				"package_reference": f"{sh}-1",
				"air_freight_job": sh,
				"shipper": self.shipper,
				"consignee": self.consignee,
				"package_type": "Box",
				"package_count": 1,
				"package_weight": 10,
				"package_volume": 0.1,
			},
		)
		with self.assertRaises(frappe.ValidationError):
			consol.insert()

	def test_submit_plan_create_consolidation_links_plan(self):
		sh = self._make_air_shipment()
		plan = frappe.get_doc(
			{
				"doctype": "Air Consolidation Plan",
				"naming_series": "ACP-{YYYY}-{####}",
				"plan_date": today(),
				"company": self.company,
				"branch": self.branch,
				"origin_airport": "USLAX",
				"destination_airport": "USJFK",
				"consolidation_type": "Direct Consolidation",
				"airline": "TA",
				"flight_number": "TBA",
				"target_departure": get_datetime(add_days(today(), 1)),
				"target_arrival": get_datetime(add_days(today(), 2)),
			}
		)
		plan.append("items", {"air_shipment": sh})
		plan.insert()
		plan.submit()
		name = plan.create_air_consolidation_from_plan()
		self.assertTrue(frappe.db.exists("Air Consolidation", name))
		linked = frappe.db.get_value(
			"Air Consolidation Plan Item",
			{"parent": plan.name, "air_shipment": sh},
			"linked_air_consolidation",
		)
		self.assertEqual(linked, name)

	def test_second_consolidation_for_same_shipment_blocked(self):
		sh = self._make_air_shipment()
		plan = frappe.get_doc(
			{
				"doctype": "Air Consolidation Plan",
				"naming_series": "ACP-{YYYY}-{####}",
				"plan_date": today(),
				"company": self.company,
				"branch": self.branch,
				"origin_airport": "USLAX",
				"destination_airport": "USJFK",
				"consolidation_type": "Direct Consolidation",
				"airline": "TA",
				"flight_number": "TBA",
				"target_departure": get_datetime(add_days(today(), 1)),
				"target_arrival": get_datetime(add_days(today(), 2)),
			}
		)
		plan.append("items", {"air_shipment": sh})
		plan.insert()
		plan.submit()
		plan.create_air_consolidation_from_plan()
		plan2 = frappe.get_doc(
			{
				"doctype": "Air Consolidation Plan",
				"naming_series": "ACP-{YYYY}-{####}",
				"plan_date": today(),
				"company": self.company,
				"branch": self.branch,
				"origin_airport": "USLAX",
				"destination_airport": "USJFK",
				"consolidation_type": "Direct Consolidation",
				"airline": "TA",
				"flight_number": "TBA",
				"target_departure": get_datetime(add_days(today(), 1)),
				"target_arrival": get_datetime(add_days(today(), 2)),
			}
		)
		plan2.append("items", {"air_shipment": sh})
		with self.assertRaises(frappe.ValidationError):
			plan2.insert()

	def test_fetch_matching_air_shipments_strict(self):
		etd_date = add_days(today(), 14)
		target_departure = get_datetime(f"{etd_date} 09:15:00")
		good = self._make_air_shipment_for_fetch(etd_date, flight_no="TA101", with_main_leg=True)
		wrong_flight = self._make_air_shipment_for_fetch(etd_date, flight_no="ZZ999", with_main_leg=True)
		no_leg = self._make_air_shipment_for_fetch(etd_date, flight_no="TA101", with_main_leg=False)
		plan = frappe.get_doc(
			{
				"doctype": "Air Consolidation Plan",
				"naming_series": "ACP-{YYYY}-{####}",
				"plan_date": today(),
				"company": self.company,
				"branch": self.branch,
				"origin_airport": "USLAX",
				"destination_airport": "USJFK",
				"consolidation_type": "Direct Consolidation",
				"airline": "TA",
				"flight_number": "TA101",
				"target_departure": target_departure,
				"target_arrival": get_datetime(add_days(etd_date, 1)),
			}
		)
		plan.insert()
		out = plan.fetch_matching_air_shipments()
		self.assertIn(good, out["added"])
		self.assertNotIn(wrong_flight, out["added"])
		self.assertNotIn(no_leg, out["added"])
		plan.reload()
		self.assertEqual(len(plan.items), 1)
		out2 = plan.fetch_matching_air_shipments()
		self.assertEqual(out2["added"], [])
		self.assertIn(good, out2["already_present"])
