# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Tests for Truck Ban Constraint plate coding and constraint_type enforcement."""

from datetime import datetime
from typing import Optional

import frappe
from frappe.tests.utils import FrappeTestCase

from logistics.transport.constraint_validator import check_truck_ban_constraints


class TestTruckBanPlateCoding(FrappeTestCase):
	def setUp(self):
		frappe.db.rollback()
		self._created = []
		self.address = self._make_address("TBPC Addr")
		self.other_address = self._make_address("TBPC Other")

	def tearDown(self):
		frappe.db.rollback()

	def _track(self, doc):
		self._created.append((doc.doctype, doc.name))
		return doc

	def _make_address(self, title_prefix: str):
		doc = frappe.get_doc(
			{
				"doctype": "Address",
				"address_title": f"{title_prefix} {frappe.generate_hash(length=6)}",
				"address_type": "Shipping",
				"address_line1": "1 Test Street",
				"city": "Parañaque",
				"country": "Philippines",
			}
		).insert(ignore_permissions=True)
		return self._track(doc)

	def _make_coding_ban(self, *, coding_rows=None):
		rows = coding_rows or [
			{
				"restricted_day": "Monday",
				"restricted_digit": 1,
				"ban_start": "07:00:00",
				"ban_end": "10:00:00",
			},
			{
				"restricted_day": "Monday",
				"restricted_digit": 2,
				"ban_start": "07:00:00",
				"ban_end": "10:00:00",
			},
			{
				"restricted_day": "Monday",
				"restricted_digit": 1,
				"ban_start": "17:00:00",
				"ban_end": "20:00:00",
			},
			{
				"restricted_day": "Monday",
				"restricted_digit": 2,
				"ban_start": "17:00:00",
				"ban_end": "20:00:00",
			},
		]
		doc = frappe.get_doc(
			{
				"doctype": "Truck Ban Constraint",
				"ban_name": f"TBPC-{frappe.generate_hash(length=8)}",
				"constraint_type": "Plate Coding",
				"start_date": "2026-01-01",
				"end_date": "2026-12-31",
				"all_day": 1,
				"is_active": 1,
				"plate_coding": rows,
			}
		).insert(ignore_permissions=True)
		return self._track(doc)

	def _make_area_ban(self, *, all_day=0, start_time="07:00:00", end_time="10:00:00"):
		"""Area Ban with parent time window."""
		doc = frappe.get_doc(
			{
				"doctype": "Truck Ban Constraint",
				"ban_name": f"TBPC-AREA-{frappe.generate_hash(length=8)}",
				"constraint_type": "Area Ban",
				"start_date": "2026-01-01",
				"end_date": "2026-12-31",
				"all_day": all_day,
				"start_time": None if all_day else start_time,
				"end_time": None if all_day else end_time,
				"is_active": 1,
				"restricted_addresses": [
					{"address": self.address.name, "radius_km": 0},
				],
			}
		).insert(ignore_permissions=True)
		return self._track(doc)

	def _make_time_ban(self):
		doc = frappe.get_doc(
			{
				"doctype": "Truck Ban Constraint",
				"ban_name": f"TBPC-TIME-{frappe.generate_hash(length=8)}",
				"constraint_type": "Time-Based Ban",
				"start_date": "2026-01-01",
				"end_date": "2026-12-31",
				"all_day": 0,
				"start_time": "07:00:00",
				"end_time": "10:00:00",
				"is_active": 1,
			}
		).insert(ignore_permissions=True)
		return self._track(doc)

	def _vehicle(self, plate: str, vehicle_type: Optional[str] = None, weight: float = 1000):
		return {
			"license_plate_number": plate,
			"vehicle_type": vehicle_type,
			"capacity_weight": weight,
		}

	def test_peak_morning_blocks_coded_digit(self):
		self._make_coding_ban()
		# 2026-08-03 is a Monday
		ok, reason = check_truck_ban_constraints(
			self._vehicle("ABC-1231"),
			datetime(2026, 8, 3, 8, 30),
			self.address.name,
			None,
		)
		self.assertFalse(ok)
		self.assertIn("last digit 1", reason or "")

	def test_midday_window_allows_coded_digit(self):
		self._make_coding_ban()
		ok, reason = check_truck_ban_constraints(
			self._vehicle("ABC-1231"),
			datetime(2026, 8, 3, 12, 0),
			self.address.name,
			None,
		)
		self.assertTrue(ok)
		self.assertIsNone(reason)

	def test_evening_peak_blocks_coded_digit(self):
		self._make_coding_ban()
		ok, _ = check_truck_ban_constraints(
			self._vehicle("ABC-1231"),
			datetime(2026, 8, 3, 18, 0),
			self.address.name,
			None,
		)
		self.assertFalse(ok)

	def test_night_free_hours_allow(self):
		self._make_coding_ban()
		ok, _ = check_truck_ban_constraints(
			self._vehicle("ABC-1231"),
			datetime(2026, 8, 3, 21, 0),
			self.address.name,
			None,
		)
		self.assertTrue(ok)

	def test_wrong_weekday_allows(self):
		self._make_coding_ban()
		# 2026-08-04 is Tuesday — digit 1 not coded
		ok, _ = check_truck_ban_constraints(
			self._vehicle("ABC-1231"),
			datetime(2026, 8, 4, 8, 30),
			self.address.name,
			None,
		)
		self.assertTrue(ok)

	def test_wrong_digit_allows(self):
		self._make_coding_ban()
		ok, _ = check_truck_ban_constraints(
			self._vehicle("ABC-1233"),
			datetime(2026, 8, 3, 8, 30),
			self.address.name,
			None,
		)
		self.assertTrue(ok)

	def test_plate_coding_blocks_regardless_of_address(self):
		"""Plate Coding type is coding-only — address is irrelevant."""
		self._make_coding_ban()
		ok, _ = check_truck_ban_constraints(
			self._vehicle("ABC-1231"),
			datetime(2026, 8, 3, 8, 30),
			self.other_address.name,
			None,
		)
		self.assertFalse(ok)

	def test_coding_only_ban_blocks_without_addresses(self):
		self._make_coding_ban()
		ok, reason = check_truck_ban_constraints(
			self._vehicle("ABC-1231"),
			datetime(2026, 8, 3, 8, 30),
			None,
			None,
		)
		self.assertFalse(ok)
		self.assertIn("last digit 1", reason or "")

	def test_area_ban_parent_time_window(self):
		self._make_area_ban()
		ok_in, _ = check_truck_ban_constraints(
			self._vehicle("ABC-1231"),
			datetime(2026, 8, 3, 8, 30),
			self.address.name,
			None,
		)
		self.assertFalse(ok_in)

		ok_out, _ = check_truck_ban_constraints(
			self._vehicle("ABC-1231"),
			datetime(2026, 8, 3, 12, 0),
			self.address.name,
			None,
		)
		self.assertTrue(ok_out)

		ok_other, _ = check_truck_ban_constraints(
			self._vehicle("ABC-1231"),
			datetime(2026, 8, 3, 8, 30),
			self.other_address.name,
			None,
		)
		self.assertTrue(ok_other)

	def test_time_based_ban_blocks_in_window(self):
		self._make_time_ban()
		ok_in, reason = check_truck_ban_constraints(
			self._vehicle("ABC-1231"),
			datetime(2026, 8, 3, 8, 30),
			None,
			None,
		)
		self.assertFalse(ok_in)
		self.assertIn("time-based", (reason or "").lower())

		ok_out, _ = check_truck_ban_constraints(
			self._vehicle("ABC-1231"),
			datetime(2026, 8, 3, 12, 0),
			None,
			None,
		)
		self.assertTrue(ok_out)

	def test_weight_based_ban(self):
		doc = frappe.get_doc(
			{
				"doctype": "Truck Ban Constraint",
				"ban_name": f"TBPC-WT-{frappe.generate_hash(length=8)}",
				"constraint_type": "Weight-Based Ban",
				"start_date": "2026-01-01",
				"end_date": "2026-12-31",
				"all_day": 1,
				"is_active": 1,
				"min_vehicle_weight_restriction": 5000,
			}
		).insert(ignore_permissions=True)
		self._track(doc)

		ok_heavy, _ = check_truck_ban_constraints(
			self._vehicle("ABC-1231", weight=6000),
			datetime(2026, 8, 3, 8, 30),
			None,
			None,
		)
		self.assertFalse(ok_heavy)

		ok_light, _ = check_truck_ban_constraints(
			self._vehicle("ABC-1231", weight=1000),
			datetime(2026, 8, 3, 8, 30),
			None,
			None,
		)
		self.assertTrue(ok_light)

	def test_area_ban_requires_address_on_save(self):
		doc = frappe.get_doc(
			{
				"doctype": "Truck Ban Constraint",
				"ban_name": f"TBPC-NOADDR-{frappe.generate_hash(length=8)}",
				"constraint_type": "Area Ban",
				"start_date": "2026-01-01",
				"end_date": "2026-12-31",
				"all_day": 1,
				"is_active": 1,
			}
		)
		with self.assertRaises(frappe.ValidationError):
			doc.insert(ignore_permissions=True)

	def test_invalid_digit_rejected_on_save(self):
		doc = frappe.get_doc(
			{
				"doctype": "Truck Ban Constraint",
				"ban_name": f"TBPC-BAD-{frappe.generate_hash(length=8)}",
				"constraint_type": "Plate Coding",
				"start_date": "2026-01-01",
				"end_date": "2026-12-31",
				"all_day": 1,
				"is_active": 1,
				"plate_coding": [
					{
						"restricted_day": "Monday",
						"restricted_digit": 11,
						"ban_start": "07:00:00",
						"ban_end": "10:00:00",
					}
				],
			}
		)
		with self.assertRaises(frappe.ValidationError):
			doc.insert(ignore_permissions=True)

	def test_exempt_vehicle_type_allows(self):
		vt = frappe.get_doc(
			{
				"doctype": "Vehicle Type",
				"code": f"EX-{frappe.generate_hash(length=6)}",
				"description": "Exempt test type",
				"is_active": 1,
				"exempt_from_plate_coding": 1,
			}
		).insert(ignore_permissions=True)
		self._track(vt)

		self._make_coding_ban()
		ok, _ = check_truck_ban_constraints(
			self._vehicle("ABC-1231", vehicle_type=vt.name),
			datetime(2026, 8, 3, 8, 30),
			None,
			None,
		)
		self.assertTrue(ok)
