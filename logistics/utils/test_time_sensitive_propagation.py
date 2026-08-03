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
