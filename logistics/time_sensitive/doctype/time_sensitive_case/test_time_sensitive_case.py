# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import annotations

from datetime import timedelta

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import now_datetime

from logistics.time_sensitive.notifications import notify_case_event
from logistics.time_sensitive.sla import compute_sla_status, format_countdown, seconds_until_deadline


class TestTimeSensitiveSLA(FrappeTestCase):
	def test_compute_sla_on_track_at_risk_breached(self):
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
		self.assertEqual(
			compute_sla_status(
				now - timedelta(minutes=1),
				at_risk_hours=4,
				breach_grace_minutes=5,
				now=now,
			),
			"At Risk",
		)

	def test_countdown_and_overdue_format(self):
		now = now_datetime()
		secs = seconds_until_deadline(now + timedelta(hours=1, minutes=2, seconds=3), now=now)
		self.assertIsNotNone(secs)
		self.assertGreater(secs, 0)
		label = format_countdown(secs)
		self.assertIn("h", label)
		self.assertFalse(label.startswith("OVERDUE"))

		over = seconds_until_deadline(now - timedelta(minutes=5), now=now)
		self.assertLess(over, 0)
		self.assertTrue(format_countdown(over).startswith("OVERDUE"))


class TestTimeSensitiveCaseLifecycle(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		from logistics.time_sensitive.doctype.time_sensitive_case_type.time_sensitive_case_type import (
			seed_default_case_types,
		)

		seed_default_case_types()

	def _make_case(self, **kwargs):
		doc = frappe.get_doc(
			{
				"doctype": "Time Sensitive Case",
				"case_title": kwargs.get("case_title") or "Test AOG Case",
				"case_type": kwargs.get("case_type") or "AOG",
				"critical_deadline": kwargs.get("critical_deadline")
				or (now_datetime() + timedelta(hours=6)),
				"status": kwargs.get("status") or "Draft",
				"severity": "Critical",
				"coordinator": kwargs.get("coordinator") or "Administrator",
				"contact_24x7_name": "Ops Desk",
				"contact_24x7_phone": "+10000000000",
			}
		)
		doc.insert()
		if kwargs.get("add_linked_service", True):
			from logistics.time_sensitive.service_linking import create_linked_service_for_case

			create_linked_service_for_case(doc, "Air")
		return doc

	def test_activation_requires_legs_and_coordinator(self):
		doc = frappe.get_doc(
			{
				"doctype": "Time Sensitive Case",
				"case_title": "Incomplete",
				"case_type": "AOG",
				"critical_deadline": now_datetime() + timedelta(hours=2),
				"status": "Draft",
			}
		)
		doc.insert()
		doc.status = "Activated"
		self.assertRaises(frappe.ValidationError, doc.save)

	def test_allowed_transition_and_activate(self):
		doc = self._make_case(status="Triage")
		doc.status = "Activated"
		doc.save()
		self.assertEqual(doc.status, "Activated")
		self.assertTrue(doc.activated_on)
		self.assertIn(doc.sla_status, ("On Track", "At Risk", "Breached"))

	def test_invalid_transition_blocked(self):
		doc = self._make_case(status="Draft")
		doc.status = "Delivered"
		self.assertRaises(frappe.ValidationError, doc.save)

	def test_alert_deduplication(self):
		doc = self._make_case(status="Triage")
		doc.status = "Activated"
		doc.save()
		sent1 = notify_case_event(
			doc,
			event_type="At Risk",
			subject="test",
			message="msg",
			severity="impending",
			bucket="At Risk",
			force=False,
		)
		sent2 = notify_case_event(
			doc,
			event_type="At Risk",
			subject="test",
			message="msg",
			severity="impending",
			bucket="At Risk",
			force=False,
		)
		self.assertGreaterEqual(sent1, 0)
		self.assertEqual(sent2, 0)

	def test_canonical_linked_service_creates_ordered_leg(self):
		from logistics.time_sensitive.service_linking import (
			create_linked_service_for_case,
		)
		from logistics.utils.linked_service_usage import get_linked_services_used_by

		doc = self._make_case()
		linked = create_linked_service_for_case(doc, "Transport")
		doc.reload()

		self.assertEqual(linked.parent_booking_type, "Time Sensitive Case")
		self.assertEqual(linked.parent_booking_name, doc.name)
		self.assertIn(
			linked.name,
			get_linked_services_used_by("Time Sensitive Case", doc.name),
		)
		self.assertIn(linked.name, [row.linked_service for row in doc.linked_services])

	def test_remove_linked_service_api_deletes_owned(self):
		from logistics.time_sensitive.doctype.time_sensitive_case.time_sensitive_case import (
			list_case_linked_services,
			remove_linked_service,
		)
		from logistics.utils.internal_job_persistence import _linked_service_names_from_db
		from logistics.utils.linked_service_compat import linked_service_doctype

		doc = self._make_case()
		names = _linked_service_names_from_db("Time Sensitive Case", doc.name)
		self.assertEqual(len(names), 1)
		ls_name = list(names)[0]

		listed = list_case_linked_services(doc.name)
		self.assertEqual(len(listed["linked_services"]), 1)
		self.assertEqual(listed["linked_services"][0]["linked_service"], ls_name)

		result = remove_linked_service(doc.name, ls_name)
		self.assertEqual(result["action"], "removed")
		self.assertFalse(frappe.db.exists(linked_service_doctype(), ls_name))
		self.assertEqual(len(list_case_linked_services(doc.name)["linked_services"]), 0)

	def test_remove_shared_linked_service_unlinks_only(self):
		from logistics.time_sensitive.doctype.time_sensitive_case.time_sensitive_case import (
			remove_linked_service,
		)
		from logistics.time_sensitive.service_linking import record_case_usage
		from logistics.utils.linked_service_compat import linked_service_doctype
		from logistics.utils.linked_service_usage import get_linked_services_used_by

		doc = self._make_case(add_linked_service=False)
		shared = frappe.new_doc(linked_service_doctype())
		shared.service_type = "Sea"
		shared.parent_booking_type = "Sales Quote"
		shared.parent_booking_name = "SQ-FAKE-TS"
		shared.flags.ignore_links = True
		shared.insert(ignore_permissions=True)
		try:
			record_case_usage(doc, shared.name)
			result = remove_linked_service(doc.name, shared.name)
			self.assertEqual(result["action"], "unlinked")
			self.assertTrue(frappe.db.exists(linked_service_doctype(), shared.name))
			self.assertNotIn(
				shared.name,
				get_linked_services_used_by("Time Sensitive Case", doc.name),
			)
		finally:
			if frappe.db.exists(linked_service_doctype(), shared.name):
				frappe.delete_doc(
					linked_service_doctype(), shared.name, force=True, ignore_permissions=True
				)

	def test_unrelated_save_keeps_linked_services(self):
		doc = self._make_case()
		doc2 = frappe.get_doc("Time Sensitive Case", doc.name)
		doc2.case_title = (doc2.case_title or "") + " updated"
		doc2.save(ignore_permissions=True)
		reloaded = frappe.get_doc("Time Sensitive Case", doc.name)
		self.assertEqual(len(reloaded.linked_services), 1)


class TestTimeSensitivePropagation(FrappeTestCase):
	def test_stamp_and_apply_from_source(self):
		from logistics.time_sensitive.propagation import (
			apply_time_sensitive_from_source,
			stamp_document_from_case,
		)

		# Minimal in-memory docs — only exercise helper logic
		src = frappe._dict(
			is_time_sensitive=1,
			time_sensitive_case="TSC-TEST",
			ts_case_type="AOG",
			critical_deadline=now_datetime(),
		)
		tgt = frappe._dict()
		# Simulate attributes present
		tgt.is_time_sensitive = 0
		tgt.time_sensitive_case = None
		tgt.ts_case_type = None
		tgt.critical_deadline = None
		apply_time_sensitive_from_source(src, tgt)
		self.assertEqual(tgt.is_time_sensitive, 1)
		self.assertEqual(tgt.time_sensitive_case, "TSC-TEST")
		self.assertEqual(tgt.ts_case_type, "AOG")
		self.assertTrue(tgt.critical_deadline)


class TestTimeSensitiveBookingCreation(FrappeTestCase):
	"""Test booking creation from Time Sensitive Cases with complete parameters."""
	
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		from logistics.time_sensitive.doctype.time_sensitive_case_type.time_sensitive_case_type import (
			seed_default_case_types,
		)
		seed_default_case_types()
	
	def _make_test_case_with_parameters(self):
		"""Create a Time Sensitive Case with comprehensive parameters."""
		deadline = now_datetime() + timedelta(hours=24)
		doc = frappe.get_doc({
			"doctype": "Time Sensitive Case",
			"case_title": "Test Critical Shipment",
			"case_type": "AOG",
			"critical_deadline": deadline,
			"status": "Triage",
			"severity": "Critical",
			"priority": "Urgent",
			"coordinator": "Administrator",
			"contact_24x7_name": "Emergency Ops",
			"contact_24x7_phone": "+1234567890",
			"contact_24x7_email": "emergency@example.com",
			"customer": "_Test Customer",
			"company": "_Test Company",
			"origin": "USNYC",
			"destination": "CNSHA",
			"cargo_summary": "Critical aircraft parts - handle with extreme care",
			"notes": "Customer requires immediate notification on any delays",
		})
		doc.insert(ignore_permissions=True)
		return doc
	
	def test_air_booking_parameters_from_case(self):
		"""Test that Air Booking receives all parameters from Time Sensitive Case."""
		from logistics.time_sensitive.service_linking import create_linked_service_for_case
		from logistics.time_sensitive.doctype.time_sensitive_case.time_sensitive_case import (
			create_service_document,
		)
		
		# Create case with parameters
		case = self._make_test_case_with_parameters()
		
		# Create linked service for Air
		linked_service = create_linked_service_for_case(case, "Air")
		
		# Create Air Booking from the case
		result = create_service_document(case.name, linked_service.name)
		
		# Verify booking was created
		self.assertEqual(result["doctype"], "Air Booking")
		self.assertTrue(result["name"])
		
		# Load the created booking
		booking = frappe.get_doc("Air Booking", result["name"])
		
		# Verify basic organizational fields
		self.assertEqual(booking.customer, case.customer)
		self.assertEqual(booking.company, case.company)
		
		# Verify origin/destination mapping
		self.assertEqual(booking.origin_port, case.origin)
		self.assertEqual(booking.destination_port, case.destination)
		
		# Verify time-sensitive fields
		self.assertEqual(booking.is_time_sensitive, 1)
		self.assertEqual(booking.time_sensitive_case, case.name)
		self.assertEqual(booking.critical_deadline, case.critical_deadline)
		self.assertEqual(booking.priority, case.priority)
		
		# Clean up
		frappe.delete_doc("Air Booking", booking.name, force=True, ignore_permissions=True)
		frappe.delete_doc("Time Sensitive Case", case.name, force=True, ignore_permissions=True)
	
	def test_transport_order_parameters_from_case(self):
		"""Test that Transport Order receives all parameters from Time Sensitive Case."""
		from logistics.time_sensitive.service_linking import create_linked_service_for_case
		from logistics.time_sensitive.doctype.time_sensitive_case.time_sensitive_case import (
			create_service_document,
		)
		
		# Create case with parameters
		case = self._make_test_case_with_parameters()
		
		# Create linked service for Transport
		linked_service = create_linked_service_for_case(case, "Transport")
		
		# Create Transport Order from the case
		result = create_service_document(case.name, linked_service.name)
		
		# Verify order was created
		self.assertEqual(result["doctype"], "Transport Order")
		self.assertTrue(result["name"])
		
		# Load the created order
		order = frappe.get_doc("Transport Order", result["name"])
		
		# Verify basic organizational fields
		self.assertEqual(order.customer, case.customer)
		self.assertEqual(order.company, case.company)
		
		# Verify origin/destination mapping (Transport Order uses location_from/location_to)
		self.assertEqual(order.location_from, case.origin)
		self.assertEqual(order.location_to, case.destination)
		self.assertEqual(order.location_type, "UNLOCO")
		
		# Verify time-sensitive fields
		self.assertEqual(order.is_time_sensitive, 1)
		self.assertEqual(order.time_sensitive_case, case.name)
		self.assertEqual(order.critical_deadline, case.critical_deadline)
		self.assertEqual(order.priority, case.priority)
		
		# Clean up
		frappe.delete_doc("Transport Order", order.name, force=True, ignore_permissions=True)
		frappe.delete_doc("Time Sensitive Case", case.name, force=True, ignore_permissions=True)
	
	def test_charges_copied_from_case_to_booking(self):
		"""Test that charges are properly filtered and copied from case to booking."""
		from logistics.time_sensitive.service_linking import create_linked_service_for_case
		from logistics.time_sensitive.doctype.time_sensitive_case.time_sensitive_case import (
			create_service_document,
		)
		
		# Create case with parameters
		case = self._make_test_case_with_parameters()
		
		# Add charges to the case
		case.append("charges", {
			"item_code": "AIR-FREIGHT",
			"description": "Air Freight Charge",
			"qty": 100,
			"rate": 5.50,
			"service_type": "Air",
			"charge_scope": "Main",
			"currency": "USD",
		})
		case.append("charges", {
			"item_code": "SEA-FREIGHT",
			"description": "Sea Freight Charge",
			"qty": 50,
			"rate": 2.00,
			"service_type": "Sea",
			"charge_scope": "Main",
			"currency": "USD",
		})
		case.save(ignore_permissions=True)
		
		# Create linked service for Air
		linked_service = create_linked_service_for_case(case, "Air")
		
		# Create Air Booking from the case
		result = create_service_document(case.name, linked_service.name)
		
		# Load the created booking
		booking = frappe.get_doc("Air Booking", result["name"])
		
		# Verify only Air charges were copied (Sea should be filtered out)
		air_charges = [ch for ch in booking.get("charges", []) if ch.item_code == "AIR-FREIGHT"]
		sea_charges = [ch for ch in booking.get("charges", []) if ch.item_code == "SEA-FREIGHT"]
		
		self.assertEqual(len(air_charges), 1)
		self.assertEqual(len(sea_charges), 0)
		
		# Verify charge details
		air_charge = air_charges[0]
		self.assertEqual(air_charge.description, "Air Freight Charge")
		self.assertEqual(air_charge.qty, 100)
		self.assertEqual(air_charge.rate, 5.50)
		
		# Clean up
		frappe.delete_doc("Air Booking", booking.name, force=True, ignore_permissions=True)
		frappe.delete_doc("Time Sensitive Case", case.name, force=True, ignore_permissions=True)
