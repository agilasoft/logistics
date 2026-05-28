# Copyright (c) 2026, logistics.agilasoft.com and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from logistics.utils.shipper_consignee_defaults import apply_shipper_consignee_defaults


class TestShipperConsigneeDefaults(FrappeTestCase):
	def test_air_booking_uses_freight_agent_for_air_default_broker(self):
		"""air_default_broker on Shipper is Freight Agent; Air Booking.broker is Broker."""
		booking = frappe.new_doc("Air Booking")
		booking.shipper = "TEST-SHIPPER-FA"
		shipper = frappe._dict(
			air_default_broker="ALLTRAMNL",
			air_default_sending_agent=None,
			air_default_receiving_agent=None,
		)

		with patch(
			"logistics.utils.shipper_consignee_defaults.frappe.get_cached_doc",
			return_value=shipper,
		):
			apply_shipper_consignee_defaults(booking)

		self.assertEqual(booking.freight_agent, "ALLTRAMNL")
		self.assertFalse(booking.broker)

	def test_air_shipment_still_maps_air_default_broker_to_broker(self):
		"""Air Shipment.broker links Freight Agent (same as master air_default_broker)."""
		shipment = frappe.new_doc("Air Shipment")
		shipment.shipper = "TEST-SHIPPER-FA"
		shipper = frappe._dict(
			air_default_broker="ALLTRAMNL",
			air_default_sending_agent=None,
			air_default_receiving_agent=None,
		)

		with patch(
			"logistics.utils.shipper_consignee_defaults.frappe.get_cached_doc",
			return_value=shipper,
		):
			apply_shipper_consignee_defaults(shipment)

		self.assertEqual(shipment.broker, "ALLTRAMNL")
