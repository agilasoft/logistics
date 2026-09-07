# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from datetime import timedelta
from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase
from frappe.utils import now_datetime

from logistics.time_sensitive.propagation import (
	apply_time_sensitive_from_linked_sales_quote,
	apply_time_sensitive_from_source,
	is_time_sensitive_operational_doc,
	sales_quote_to_stamp,
	stamp_document_from_case,
)
from logistics.time_sensitive.sla import compute_sla_status, format_countdown, seconds_until_deadline


class UnitTestTimeSensitivePropagation(UnitTestCase):
	def test_apply_from_source_sets_flag_case_and_deadline(self):
		deadline = now_datetime() + timedelta(hours=3)
		src = frappe._dict(
			is_time_sensitive=1,
			time_sensitive_case="TSC-1",
			ts_case_type="AOG",
			critical_deadline=deadline,
		)
		tgt = frappe._dict(
			is_time_sensitive=0,
			time_sensitive_case=None,
			ts_case_type=None,
			critical_deadline=None,
		)
		apply_time_sensitive_from_source(src, tgt)
		self.assertEqual(tgt.is_time_sensitive, 1)
		self.assertEqual(tgt.time_sensitive_case, "TSC-1")
		self.assertEqual(tgt.ts_case_type, "AOG")
		self.assertEqual(tgt.critical_deadline, deadline)

	def test_apply_from_sales_quote(self):
		booking = frappe.get_doc(
			{"doctype": "Air Booking", "sales_quote": "SQ-TS-1", "is_time_sensitive": 0}
		)
		deadline = now_datetime()
		with patch(
			"logistics.time_sensitive.propagation.frappe.db.get_value",
			return_value=frappe._dict(
				is_time_sensitive=1,
				time_sensitive_case="TSC-9",
				critical_deadline=deadline,
				ts_case_type="ORGAN",
			),
		):
			apply_time_sensitive_from_linked_sales_quote(booking)
		self.assertEqual(booking.is_time_sensitive, 1)
		self.assertEqual(booking.time_sensitive_case, "TSC-9")
		self.assertEqual(booking.ts_case_type, "ORGAN")

	def test_is_time_sensitive_operational_doc(self):
		self.assertFalse(is_time_sensitive_operational_doc(None))
		self.assertFalse(
			is_time_sensitive_operational_doc(
				frappe._dict(is_time_sensitive=1, time_sensitive_case=None, name="TRO-1", doctype="Transport Order")
			)
		)
		self.assertTrue(
			is_time_sensitive_operational_doc(
				frappe._dict(
					is_time_sensitive=1,
					time_sensitive_case="TSC-00008",
					name="TRO000001289",
					doctype="Transport Order",
				)
			)
		)
		with patch(
			"logistics.utils.linked_service_usage.get_linked_services_used_by",
			return_value=["IJ-1"],
		), patch(
			"frappe.db.exists",
			side_effect=lambda dt, filters: dt == "Linked Service"
			and filters.get("parent_booking_type") == "Time Sensitive Case",
		):
			self.assertTrue(
				is_time_sensitive_operational_doc(
					frappe._dict(
						is_time_sensitive=0,
						time_sensitive_case=None,
						name="TRO-LS",
						doctype="Transport Order",
					)
				)
				)


class UnitTestStampSalesQuoteFromCase(UnitTestCase):
	def _quote_get_value(self, existing=None, qtype="Regular", quote_customer="CEF", target_customer="CEF"):
		def get_value(dt, name, field=None, as_dict=False, **kwargs):
			if dt == "Sales Quote":
				data = frappe._dict(quotation_type=qtype, customer=quote_customer)
				return data if as_dict else data
			if field == "sales_quote":
				return existing
			if field == "customer":
				return target_customer
			if field == "local_customer":
				return None
			return None

		return get_value

	def test_stamp_quote_when_empty_regular_and_customer_matches(self):
		case = frappe._dict(name="TSC-1", sales_quote="SQ-1", customer="CEF", case_type="CEF")
		with patch(
			"logistics.time_sensitive.propagation._meta_has",
			side_effect=lambda dt, fn: fn in ("sales_quote", "customer"),
		), patch(
			"logistics.time_sensitive.propagation.frappe.db.get_value",
			side_effect=self._quote_get_value(),
		), patch("logistics.time_sensitive.propagation.frappe.msgprint"):
			self.assertEqual(sales_quote_to_stamp("Transport Order", "TRO-1", case), "SQ-1")

	def test_no_overwrite_when_target_already_has_quote(self):
		case = frappe._dict(name="TSC-1", sales_quote="SQ-1", customer="CEF")
		with patch(
			"logistics.time_sensitive.propagation._meta_has",
			side_effect=lambda dt, fn: fn in ("sales_quote", "customer"),
		), patch(
			"logistics.time_sensitive.propagation.frappe.db.get_value",
			side_effect=self._quote_get_value(existing="SQ-OTHER"),
		), patch("logistics.time_sensitive.propagation.frappe.msgprint"):
			self.assertIsNone(sales_quote_to_stamp("Transport Order", "TRO-1", case))

	def test_skip_customer_mismatch(self):
		case = frappe._dict(name="TSC-1", sales_quote="SQ-1", customer="CEF")
		with patch(
			"logistics.time_sensitive.propagation._meta_has",
			side_effect=lambda dt, fn: fn in ("sales_quote", "customer"),
		), patch(
			"logistics.time_sensitive.propagation.frappe.db.get_value",
			side_effect=self._quote_get_value(target_customer="OTHER"),
		), patch("logistics.time_sensitive.propagation.frappe.msgprint"):
			self.assertIsNone(sales_quote_to_stamp("Transport Order", "TRO-1", case))

	def test_skip_one_off_quote(self):
		case = frappe._dict(name="TSC-1", sales_quote="SQ-1", customer="CEF")
		with patch(
			"logistics.time_sensitive.propagation._meta_has",
			side_effect=lambda dt, fn: fn in ("sales_quote", "customer"),
		), patch(
			"logistics.time_sensitive.propagation.frappe.db.get_value",
			side_effect=self._quote_get_value(qtype="One-off"),
		), patch("logistics.time_sensitive.propagation.frappe.msgprint"):
			self.assertIsNone(sales_quote_to_stamp("Transport Order", "TRO-1", case))

	def test_no_quote_on_case_does_not_stamp_sales_quote(self):
		case = frappe._dict(name="TSC-1", sales_quote=None, customer="CEF")
		with patch(
			"logistics.time_sensitive.propagation._meta_has",
			side_effect=lambda dt, fn: fn in ("sales_quote", "customer"),
		), patch(
			"logistics.time_sensitive.propagation.frappe.db.get_value",
			side_effect=self._quote_get_value(),
		):
			self.assertIsNone(sales_quote_to_stamp("Transport Order", "TRO-1", case))

	def test_stamp_document_writes_quote_and_child_job(self):
		case = frappe._dict(
			name="TSC-1",
			sales_quote="SQ-1",
			customer="CEF",
			case_type="CEF",
			critical_deadline=None,
		)
		set_calls = []

		def get_value(dt, name, field=None, as_dict=False, **kwargs):
			if dt == "Sales Quote":
				data = frappe._dict(quotation_type="Regular", customer="CEF")
				return data if as_dict else data
			if field == "sales_quote":
				return None
			if field == "customer":
				return "CEF"
			return None

		def meta_has(dt, fn):
			if fn in ("is_time_sensitive", "time_sensitive_case", "ts_case_type", "sales_quote", "customer"):
				return True
			if dt == "Transport Job" and fn == "transport_order":
				return True
			return False

		with patch("logistics.time_sensitive.propagation.frappe.db.exists", return_value=True), patch(
			"logistics.time_sensitive.propagation._meta_has",
			side_effect=meta_has,
		), patch(
			"logistics.time_sensitive.propagation.frappe.db.get_value",
			side_effect=get_value,
		), patch(
			"logistics.time_sensitive.propagation.frappe.db.set_value",
			side_effect=lambda *a, **k: set_calls.append((a, k)),
		), patch(
			"logistics.time_sensitive.propagation.frappe.get_all",
			side_effect=lambda dt, **k: ["TJ-1"] if dt == "Transport Job" else [],
		), patch("logistics.time_sensitive.propagation.frappe.msgprint"):
			stamp_document_from_case("Transport Order", "TRO-1", case)

		written = {(c[0][0], c[0][1], c[0][2]): c[0][3] for c in set_calls if len(c[0]) >= 4}
		self.assertEqual(written.get(("Transport Order", "TRO-1", "sales_quote")), "SQ-1")
		self.assertEqual(written.get(("Transport Job", "TJ-1", "sales_quote")), "SQ-1")
		self.assertEqual(written.get(("Transport Order", "TRO-1", "time_sensitive_case")), "TSC-1")


class UnitTestTimeSensitiveSubmitGates(UnitTestCase):
	def test_air_booking_case_leg_skips_destination_charge_gate(self):
		from logistics.utils.charge_service_type import throw_if_missing_destination_service_charge

		booking = frappe.get_doc(
			{
				"doctype": "Air Booking",
				"is_time_sensitive": 1,
				"time_sensitive_case": "TSC-00008",
			}
		)
		self.assertTrue(is_time_sensitive_operational_doc(booking))
		throw_if_missing_destination_service_charge(booking)

	def test_air_booking_checkbox_only_still_requires_air_charge(self):
		from logistics.utils.charge_service_type import throw_if_missing_destination_service_charge

		booking = frappe.get_doc({"doctype": "Air Booking", "is_time_sensitive": 1})
		self.assertFalse(is_time_sensitive_operational_doc(booking))
		with self.assertRaises(frappe.ValidationError) as ctx:
			throw_if_missing_destination_service_charge(booking)
		self.assertIn("Air", str(ctx.exception))


class UnitTestTimeSensitiveSLA(UnitTestCase):
	def test_sla_boundaries(self):
		now = now_datetime()
		self.assertEqual(
			compute_sla_status(now + timedelta(hours=10), at_risk_hours=4, now=now),
			"On Track",
		)
		self.assertEqual(
			compute_sla_status(now + timedelta(hours=2), at_risk_hours=4, now=now),
			"At Risk",
		)
		self.assertEqual(
			compute_sla_status(now - timedelta(minutes=1), at_risk_hours=4, now=now),
			"Breached",
		)

	def test_overdue_label(self):
		now = now_datetime()
		secs = seconds_until_deadline(now - timedelta(seconds=90), now=now)
		self.assertTrue(format_countdown(secs).startswith("OVERDUE"))
