# Copyright (c) 2026, AgilaSoft and contributors
# See license.txt

import frappe
from frappe.exceptions import ValidationError
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, flt, get_datetime, today

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
from logistics.utils.consolidation_plan import (
	assert_air_plan_fields_for_filter_match,
	get_filtered_air_shipment_names,
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


def _base_consolidation_dict(
	company,
	branch,
	cost_center,
	profit_center,
):
	return {
		"doctype": "Air Consolidation",
		"naming_series": "AFC.########",
		"consolidation_date": today(),
		"consolidation_type": "Direct Consolidation",
		"status": "Draft",
		"company": company,
		"branch": branch,
		"cost_center": cost_center,
		"profit_center": profit_center,
		"origin_airport": "USLAX",
		"destination_airport": "USJFK",
		"departure_date": get_datetime(add_days(today(), 1)),
		"arrival_date": get_datetime(add_days(today(), 2)),
		"airline": "TA",
		"flight_number": "TBA",
	}


class TestAirConsolidationEmbeddedPlanning(FrappeTestCase):
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

	def _append_default_route(self, consol):
		consol.append(
			"consolidation_routes",
			{
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

	def _make_air_consolidation(self):
		data = _base_consolidation_dict(
			self.company, self.branch, self.cost_center, self.profit_center
		)
		consol = frappe.get_doc(data)
		self._append_default_route(consol)
		consol.insert()
		return consol

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

	def test_cargo_air_shipment_not_on_planning_lines_fails(self):
		sh = self._make_air_shipment()
		data = _base_consolidation_dict(
			self.company, self.branch, self.cost_center, self.profit_center
		)
		consol = frappe.get_doc(data)
		consol.append(
			"consolidation_routes",
			{
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

	def test_draft_planning_allows_insert_with_cargo_when_shipment_is_planned(self):
		sh = self._make_air_shipment()
		data = _base_consolidation_dict(
			self.company, self.branch, self.cost_center, self.profit_center
		)
		consol = frappe.get_doc(data)
		consol.append(
			"consolidation_routes",
			{
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
		consol.append("consolidation_planning_lines", {"air_shipment": sh})
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
		consol.insert()
		consol.reload()
		self.assertEqual((consol.air_planning_status or "Draft"), "Draft")

	def test_cannot_submit_planning_with_only_one_air_shipment(self):
		sh = self._make_air_shipment()
		data = _base_consolidation_dict(
			self.company, self.branch, self.cost_center, self.profit_center
		)
		consol = frappe.get_doc(data)
		consol.append(
			"consolidation_routes",
			{
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
		consol.append("consolidation_planning_lines", {"air_shipment": sh})
		consol.insert()
		consol.reload()
		with self.assertRaises(frappe.ValidationError) as ctx:
			consol.submit_air_planning()
		self.assertIn("two", str(ctx.exception).lower())

	def test_cancel_planning_submit_retains_planning_lines(self):
		sh = self._make_air_shipment()
		sh2 = self._make_air_shipment()
		consol = self._make_air_consolidation()
		consol.append("consolidation_planning_lines", {"air_shipment": sh})
		consol.append("consolidation_planning_lines", {"air_shipment": sh2})
		consol.save()
		consol.reload()
		consol.submit_air_planning()
		consol.reload()
		self.assertEqual(len(consol.consolidation_planning_lines), 2)
		consol.cancel_air_planning_submit()
		consol.reload()
		self.assertEqual(consol.air_planning_status, "Draft")
		self.assertEqual(len(consol.consolidation_planning_lines or []), 2)
		planned = {r.air_shipment for r in consol.consolidation_planning_lines}
		self.assertEqual(planned, {sh, sh2})

	def test_cancel_planning_when_shipments_have_submitted_job_status(self):
		"""Shipments submitted while planning was locked must still allow planning reset."""
		sh = self._make_air_shipment()
		sh2 = self._make_air_shipment()
		consol = self._make_air_consolidation()
		consol.append("consolidation_planning_lines", {"air_shipment": sh})
		consol.append("consolidation_planning_lines", {"air_shipment": sh2})
		consol.save()
		consol.reload()
		consol.submit_air_planning()
		frappe.db.set_value("Air Shipment", sh, "job_status", "Submitted", update_modified=False)
		frappe.db.set_value("Air Shipment", sh2, "job_status", "Submitted", update_modified=False)
		consol.reload()
		consol.cancel_air_planning_submit()
		consol.reload()
		self.assertEqual(consol.air_planning_status, "Draft")
		self.assertEqual(len(consol.consolidation_planning_lines or []), 2)

	def test_cancel_planning_retains_packages(self):
		sh = self._make_air_shipment()
		sh2 = self._make_air_shipment()
		consol = self._make_air_consolidation()
		consol.append("consolidation_planning_lines", {"air_shipment": sh})
		consol.append("consolidation_planning_lines", {"air_shipment": sh2})
		consol.append(
			"consolidation_packages",
			{
				"package_reference": f"{sh}-PKGRESET",
				"air_freight_job": sh,
				"shipper": self.shipper,
				"consignee": self.consignee,
				"package_type": "Box",
				"package_count": 1,
				"package_weight": 20,
				"package_volume": 0.2,
			},
		)
		consol.save()
		consol.reload()
		consol.submit_air_planning()
		consol.reload()
		self.assertTrue(consol.get("consolidation_packages"))
		consol.cancel_air_planning_submit()
		consol.reload()
		self.assertEqual(consol.air_planning_status, "Draft")
		self.assertEqual(len(consol.consolidation_packages or []), 1)
		consol.consolidation_packages[0].package_weight = 25
		consol.save()
		consol.reload()
		self.assertEqual(consol.consolidation_packages[0].package_weight, 25)

	def test_cargo_locked_when_planning_submitted(self):
		sh = self._make_air_shipment()
		sh2 = self._make_air_shipment()
		consol = self._make_air_consolidation()
		consol.append("consolidation_planning_lines", {"air_shipment": sh})
		consol.append("consolidation_planning_lines", {"air_shipment": sh2})
		consol.append(
			"consolidation_packages",
			{
				"package_reference": f"{sh}-PKGLOCK",
				"air_freight_job": sh,
				"shipper": self.shipper,
				"consignee": self.consignee,
				"package_type": "Box",
				"package_count": 1,
				"package_weight": 20,
				"package_volume": 0.2,
			},
		)
		consol.save()
		consol.reload()
		consol.submit_air_planning()
		consol.reload()
		consol.consolidation_packages[0].package_weight = 99
		with self.assertRaises(ValidationError) as ctx:
			consol.save()
		self.assertIn("cargo", str(ctx.exception).lower())

	def test_shipment_blocked_on_second_consolidation_when_first_planning_submitted(self):
		sh = self._make_air_shipment()
		data_a = _base_consolidation_dict(
			self.company, self.branch, self.cost_center, self.profit_center
		)
		a = frappe.get_doc(data_a)
		a.append(
			"consolidation_routes",
			{
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
		sh2 = self._make_air_shipment()
		a.append("consolidation_planning_lines", {"air_shipment": sh})
		a.append("consolidation_planning_lines", {"air_shipment": sh2})
		a.insert()
		a.reload()
		a.submit_air_planning()

		data_b = _base_consolidation_dict(
			self.company, self.branch, self.cost_center, self.profit_center
		)
		b = frappe.get_doc(data_b)
		b.append(
			"consolidation_routes",
			{
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
		b.append("consolidation_planning_lines", {"air_shipment": sh})
		with self.assertRaises(frappe.ValidationError):
			b.insert()

	def test_fetch_matching_air_shipments_strict(self):
		etd_date = add_days(today(), 14)
		target_departure = get_datetime(f"{etd_date} 09:15:00")
		good = self._make_air_shipment_for_fetch(etd_date, flight_no="TA101", with_main_leg=True)
		wrong_flight = self._make_air_shipment_for_fetch(etd_date, flight_no="ZZ999", with_main_leg=True)
		no_leg = self._make_air_shipment_for_fetch(etd_date, flight_no="TA101", with_main_leg=False)
		data = _base_consolidation_dict(
			self.company, self.branch, self.cost_center, self.profit_center
		)
		data["departure_date"] = target_departure
		data["flight_number"] = "TA101"
		consol = frappe.get_doc(data)
		consol.append(
			"consolidation_routes",
			{
				"route_type": "Direct",
				"origin_airport": "USLAX",
				"destination_airport": "USJFK",
				"airline": "TA",
				"flight_number": "TA101",
				"departure_date": etd_date,
				"departure_time": "09:15:00",
				"arrival_date": add_days(etd_date, 1),
				"arrival_time": "12:00:00",
				"dangerous_goods_allowed": 1,
			},
		)
		consol.insert()
		consol.reload()
		out = consol.fetch_matching_air_shipments()
		self.assertIn(good, out["added"])
		self.assertNotIn(wrong_flight, out["added"])
		self.assertNotIn(no_leg, out["added"])
		consol.reload()
		self.assertEqual(len(consol.consolidation_planning_lines), 1)
		pkg_for = [p for p in (consol.consolidation_packages or []) if p.air_freight_job == good]
		self.assertEqual(len(pkg_for), 1)
		self.assertGreater(flt(pkg_for[0].package_weight), 0)
		self.assertTrue(pkg_for[0].package_reference)
		out2 = consol.fetch_matching_air_shipments()
		self.assertEqual(out2["added"], [])
		self.assertIn(good, out2["already_present"])
		consol.reload()
		self.assertEqual(len([p for p in (consol.consolidation_packages or []) if p.air_freight_job == good]), 1)

	def test_air_plan_filter_requires_at_least_one_criterion(self):
		with self.assertRaises(frappe.ValidationError):
			assert_air_plan_fields_for_filter_match({})

	def test_get_filtered_air_shipments_single_origin_field(self):
		"""Unset criteria are ignored; matching uses only provided filters."""
		etd = add_days(today(), 14)
		lax_ship = self._make_air_shipment_for_fetch(etd, flight_no="TA101", with_main_leg=True)
		create_test_unloco("USORD", "Chicago", "ORD", "US", "Airport")
		mode = _ensure_test_air_transport_mode()
		ord_ship = frappe.get_doc(
			{
				"doctype": "Air Shipment",
				"booking_date": today(),
				"company": self.company,
				"local_customer": self.customer,
				"shipper": self.shipper,
				"consignee": self.consignee,
				"origin_port": "USORD",
				"destination_port": "USJFK",
				"branch": self.branch,
				"cost_center": self.cost_center,
				"profit_center": self.profit_center,
				"direction": "Export",
				"weight": 10,
				"chargeable": 10,
				"volume": 0.1,
				"airline": "TA",
				"etd": etd,
			}
		)
		ord_ship.append(
			"routing_legs",
			{
				"mode": mode,
				"type": "Main",
				"flight_no": "TA202",
				"airline": "TA",
				"load_port": "USORD",
				"discharge_port": "USJFK",
			},
		)
		ord_ship.insert()

		matches = get_filtered_air_shipment_names({"origin_airport": "USLAX"})
		self.assertIn(lax_ship, matches)
		self.assertNotIn(ord_ship.name, matches)

		matches_ord = get_filtered_air_shipment_names({"origin_airport": "USORD"})
		self.assertIn(ord_ship.name, matches_ord)
		self.assertNotIn(lax_ship, matches_ord)

	def test_airline_filter_includes_main_leg_when_header_blank(self):
		"""Many Air Shipments set the carrier on the Main leg only; header `airline` is empty."""
		etd = add_days(today(), 14)
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
				"etd": etd,
			}
		)
		sh.append(
			"routing_legs",
			{
				"mode": mode,
				"type": "Main",
				"flight_no": "TA999",
				"airline": "TA",
				"load_port": "USLAX",
				"discharge_port": "USJFK",
			},
		)
		sh.insert()
		matches = get_filtered_air_shipment_names({"airline": "TA"})
		self.assertIn(sh.name, matches)
		frappe.db.set_value("Air Shipment", sh.name, "job_status", "Submitted", update_modified=False)
		matches_sub = get_filtered_air_shipment_names({"airline": "TA"})
		self.assertNotIn(sh.name, matches_sub)

	def test_merge_empty_override_clears_branch_for_filtering(self):
		"""Cleared fields in the dialog must drop Company/Branch etc., not keep document values."""
		data = _base_consolidation_dict(
			self.company, self.branch, self.cost_center, self.profit_center
		)
		consol = frappe.get_doc(data)
		m = consol._merged_air_plan_match_dict_from_dialog({"branch": ""})
		self.assertIsNone(m.get("branch"))
		self.assertEqual(m.get("company"), self.company)

	def _make_air_consolidation_without_routes(self):
		data = _base_consolidation_dict(
			self.company, self.branch, self.cost_center, self.profit_center
		)
		consol = frappe.get_doc(data)
		consol.insert()
		return consol

	def test_apply_selected_populates_consolidation_routes_from_shipment(self):
		etd_date = add_days(today(), 14)
		sh = self._make_air_shipment_for_fetch(etd_date, flight_no="TA101", with_main_leg=True)
		consol = self._make_air_consolidation_without_routes()
		self.assertFalse(consol.get("consolidation_routes"))
		out = consol.apply_selected_air_shipments_to_planning(
			[sh],
			filter_overrides={"origin_airport": "USLAX", "destination_airport": "USJFK"},
		)
		self.assertIn(sh, out["added"])
		consol.reload()
		self.assertEqual(len(consol.consolidation_routes or []), 1)
		route = consol.consolidation_routes[0]
		self.assertEqual(route.origin_airport, "USLAX")
		self.assertEqual(route.destination_airport, "USJFK")
		self.assertEqual(route.flight_number, "TA101")
		self.assertEqual(route.airline, "TA")

	def test_apply_selected_uses_header_od_not_disconnected_legs(self):
		"""Multi-leg shipments with gaps must not break planning with a single Direct route."""
		etd_date = add_days(today(), 14)
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
		sh.append(
			"routing_legs",
			{
				"mode": mode,
				"type": "Transit",
				"flight_no": "TA050",
				"airline": "TA",
				"load_port": "USLAX",
				"discharge_port": "HKHKG",
			},
		)
		sh.append(
			"routing_legs",
			{
				"mode": mode,
				"type": "Main",
				"flight_no": "TA101",
				"airline": "TA",
				"load_port": "USSFO",
				"discharge_port": "USJFK",
			},
		)
		sh.insert()
		consol = self._make_air_consolidation_without_routes()
		out = consol.apply_selected_air_shipments_to_planning(
			[sh.name],
			filter_overrides={"origin_airport": "USLAX", "destination_airport": "USJFK"},
		)
		self.assertIn(sh.name, out["added"])
		consol.reload()
		self.assertEqual(len(consol.consolidation_routes or []), 1)
		route = consol.consolidation_routes[0]
		self.assertEqual(route.origin_airport, "USLAX")
		self.assertEqual(route.destination_airport, "USJFK")
		self.assertEqual(route.flight_number, "TA101")

	def test_apply_selected_rejects_mismatched_routing(self):
		etd_date = add_days(today(), 14)
		first = self._make_air_shipment_for_fetch(etd_date, flight_no="TA101", with_main_leg=True)
		second = self._make_air_shipment_for_fetch(etd_date, flight_no="ZZ999", with_main_leg=True)
		consol = self._make_air_consolidation_without_routes()
		consol.apply_selected_air_shipments_to_planning(
			[first],
			filter_overrides={"origin_airport": "USLAX", "destination_airport": "USJFK"},
		)
		consol.reload()
		with self.assertRaises(frappe.ValidationError) as ctx:
			consol.apply_selected_air_shipments_to_planning(
				[second],
				filter_overrides={"origin_airport": "USLAX", "destination_airport": "USJFK"},
			)
		self.assertIn("routing", str(ctx.exception).lower())

	def test_populate_routing_from_airports(self):
		consol = self._make_air_consolidation_without_routes()
		out = consol.populate_routing_from_airports()
		consol.reload()
		self.assertIn("Routing leg", out["message"])
		self.assertEqual(len(consol.consolidation_routes or []), 1)
		self.assertEqual(consol.consolidation_routes[0].route_type, "Direct")
		self.assertEqual(consol.consolidation_routes[0].origin_airport, "USLAX")
