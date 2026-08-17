# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Tests for Address Pick / Drop Windows schedule resolution and validation."""

from datetime import datetime, timedelta, time as time_type

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import getdate, get_time

from logistics.transport.address_windows import (
	is_operation_allowed,
	resolve_address_window,
)
from logistics.transport.constraint_validator import (
	_check_address_day_availability,
	check_time_window_constraints,
)
from logistics.transport.doctype.transport_leg.transport_leg import TransportLeg


def _hour(value) -> int:
	t = get_time(value)
	if isinstance(t, timedelta):
		return int(t.total_seconds()) // 3600
	if isinstance(t, time_type):
		return t.hour
	return int(str(t).split(":")[0])


def _ensure_schedule_field():
	if not frappe.db.exists("DocType", "Address Window Schedule"):
		frappe.throw("Address Window Schedule DocType missing — run migrate")
	if not frappe.get_meta("Address").has_field("custom_window_schedule"):
		from logistics.patches.v3_0_address_window_schedule import execute

		execute()
		frappe.clear_cache(doctype="Address")


class TestAddressWindowSchedule(FrappeTestCase):
	def setUp(self):
		_ensure_schedule_field()
		self.address = frappe.get_doc(
			{
				"doctype": "Address",
				"address_title": f"AWS Test {frappe.generate_hash(length=6)}",
				"address_type": "Shipping",
				"address_line1": "1 Test Street",
				"city": "Manila",
				"country": "Philippines",
				"custom_window_schedule": [
					{
						"day": "Monday",
						"operation": "Pick",
						"window_start": "08:00:00",
						"window_end": "12:00:00",
					},
					{
						"day": "Monday",
						"operation": "Drop",
						"window_start": "13:00:00",
						"window_end": "17:00:00",
					},
					{
						"day": "Tuesday",
						"operation": "Pick",
						"window_start": "14:00:00",
						"window_end": "18:00:00",
					},
				],
			}
		)
		self.address.insert(ignore_permissions=True)

	def tearDown(self):
		if getattr(self, "address", None) and self.address.name:
			frappe.delete_doc("Address", self.address.name, force=1, ignore_permissions=True)

	def test_resolve_monday_pick_vs_tuesday_pick(self):
		monday = getdate("2026-08-03")  # Monday
		tuesday = getdate("2026-08-04")  # Tuesday

		mon = resolve_address_window(self.address.name, "Pick", monday)
		tue = resolve_address_window(self.address.name, "Pick", tuesday)

		self.assertIsNotNone(mon)
		self.assertIsNotNone(tue)
		self.assertEqual(_hour(mon[0]), 8)
		self.assertEqual(_hour(tue[0]), 14)

	def test_missing_day_unavailable(self):
		wednesday = getdate("2026-08-05")
		self.assertIsNone(resolve_address_window(self.address.name, "Pick", wednesday))
		self.assertFalse(is_operation_allowed(self.address.name, "pick", wednesday))

	def test_duplicate_day_operation_blocked(self):
		doc = frappe.copy_doc(self.address)
		doc.address_title = f"AWS Dup {frappe.generate_hash(length=6)}"
		doc.append(
			"custom_window_schedule",
			{
				"day": "Monday",
				"operation": "Pick",
				"window_start": "09:00:00",
				"window_end": "11:00:00",
			},
		)
		self.assertRaises(frappe.ValidationError, doc.insert, ignore_permissions=True)

	def test_end_before_start_blocked(self):
		doc = frappe.get_doc(
			{
				"doctype": "Address",
				"address_title": f"AWS Bad {frappe.generate_hash(length=6)}",
				"address_type": "Shipping",
				"address_line1": "2 Test Street",
				"city": "Manila",
				"country": "Philippines",
				"custom_window_schedule": [
					{
						"day": "Friday",
						"operation": "Pick",
						"window_start": "12:00:00",
						"window_end": "08:00:00",
					}
				],
			}
		)
		self.assertRaises(frappe.ValidationError, doc.insert, ignore_permissions=True)

	def test_day_availability_uses_schedule(self):
		monday = datetime(2026, 8, 3, 10, 0, 0)
		wednesday = datetime(2026, 8, 5, 10, 0, 0)

		ok, _ = _check_address_day_availability(
			self.address.name, "monday", "Monday", "pick", [], monday
		)
		self.assertTrue(ok)

		blocked, reason = _check_address_day_availability(
			self.address.name, "wednesday", "Wednesday", "pick", [], wednesday
		)
		self.assertFalse(blocked)
		self.assertIn("does not allow pick", reason or "")

	def test_time_window_constraint_uses_tuesday_schedule(self):
		leg = {
			"pick_address": self.address.name,
			"drop_address": None,
			"date": "2026-08-04",
			"distance_km": 0,
		}
		vehicle = {"avg_speed": 50}
		scheduled = datetime(2026, 8, 4, 10, 0, 0)

		valid, reason, _ = check_time_window_constraints(vehicle, leg, scheduled, [])
		self.assertFalse(valid)
		self.assertIn("pick window", (reason or "").lower())

	def test_leg_fills_window_from_schedule(self):
		leg = frappe.new_doc("Transport Leg")
		leg.pick_address = self.address.name
		leg.pick_datetime = "2026-08-04 10:00:00"
		TransportLeg.apply_address_window_schedule(leg)
		self.assertEqual(_hour(leg.pick_window_start), 14)
		self.assertEqual(_hour(leg.pick_window_end), 18)


def run_inline_checks():
	"""bench execute logistics.transport.test_address_windows.run_inline_checks"""
	suite = TestAddressWindowSchedule()
	methods = [
		"test_resolve_monday_pick_vs_tuesday_pick",
		"test_missing_day_unavailable",
		"test_duplicate_day_operation_blocked",
		"test_end_before_start_blocked",
		"test_day_availability_uses_schedule",
		"test_time_window_constraint_uses_tuesday_schedule",
		"test_leg_fills_window_from_schedule",
	]
	failed = []
	for name in methods:
		suite.setUp()
		try:
			getattr(suite, name)()
			print(f"OK {name}")
		except Exception as exc:
			failed.append((name, str(exc)))
			print(f"FAIL {name}: {exc}")
		finally:
			suite.tearDown()
			frappe.db.rollback()
	if failed:
		frappe.throw(f"{len(failed)} check(s) failed: {failed}")
	return "ALL PASSED"
