# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and Contributors
# See license.txt

from __future__ import unicode_literals

from frappe.tests.utils import FrappeTestCase

from logistics.container_management.api import (
	_shipping_status_to_container_status,
	_transport_status_to_container_status,
	movement_type_to_container_status,
)


class TestContainerStatusMapping(FrappeTestCase):
	def test_shipping_closed_maps_to_closed(self):
		self.assertEqual(_shipping_status_to_container_status("Closed"), "Closed")

	def test_shipping_unmapped_returns_none(self):
		self.assertIsNone(_shipping_status_to_container_status("Booking Received"))
		self.assertIsNone(_shipping_status_to_container_status("Future Milestone XYZ"))

	def test_shipping_customs_hold(self):
		self.assertEqual(_shipping_status_to_container_status("Customs Hold"), "Customs Hold")

	def test_transport_unmapped_returns_none(self):
		self.assertIsNone(_transport_status_to_container_status("Submitted"))
		self.assertIsNone(_transport_status_to_container_status("Draft"))

	def test_transport_completed_maps_empty_returned(self):
		self.assertEqual(_transport_status_to_container_status("Completed"), "Empty Returned")

	def test_movement_returned_maps_empty_returned(self):
		self.assertEqual(movement_type_to_container_status("Returned"), "Empty Returned")

	def test_movement_other_returns_none(self):
		self.assertIsNone(movement_type_to_container_status("Other"))
