# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

from frappe.tests import UnitTestCase
from frappe.utils import flt

from logistics.sea_freight.sea_container_row_utils import (
	BOOKING_TO_SHIPMENT_CONTAINER_FIELDS,
	SALES_QUOTE_TO_BOOKING_CONTAINER_FIELDS,
	container_row_to_dict,
	copy_booking_containers_to_shipment,
	copy_sales_quote_containers_to_booking,
	effective_row_free_time_days,
)


class UnitTestSeaContainerRowUtils(UnitTestCase):
	def test_effective_row_free_time_days(self):
		self.assertIsNone(effective_row_free_time_days(type("R", (), {"free_time_days": 0})()))
		self.assertIsNone(effective_row_free_time_days(type("R", (), {"free_time_days": None})()))
		self.assertEqual(flt(effective_row_free_time_days(type("R", (), {"free_time_days": 14})())), 14)

	def test_container_row_to_dict_includes_free_time(self):
		row = type(
			"Row",
			(),
			{
				"type": "40HC",
				"size": "40ft",
				"mode": "FCL",
				"delivery_modes": "CY/CY",
				"free_time_days": 10,
				"demurrage_free_time_days": 5,
				"detention_free_time_days": 8,
				"container_no": None,
			},
		)()
		data = container_row_to_dict(row, SALES_QUOTE_TO_BOOKING_CONTAINER_FIELDS)
		self.assertEqual(data["free_time_days"], 10)
		self.assertEqual(data["demurrage_free_time_days"], 5)
		self.assertEqual(data["detention_free_time_days"], 8)
		self.assertEqual(data["size"], "40ft")
		self.assertNotIn("container_no", data)

	def test_copy_sales_quote_containers_to_booking(self):
		sq_row = type(
			"Row",
			(),
			{
				"type": "20GP",
				"size": "20ft",
				"mode": "FCL",
				"delivery_modes": "CY/CY",
				"free_time_days": 7,
				"demurrage_free_time_days": 3,
				"detention_free_time_days": 4,
			},
		)()
		sales_quote = type("SQ", (), {"containers": [sq_row]})()
		booking = type("BK", (), {"containers": []})()
		booking.append = lambda table, data: booking.containers.append(type("C", (), data)())

		copy_sales_quote_containers_to_booking(sales_quote, booking)

		self.assertEqual(len(booking.containers), 1)
		self.assertEqual(booking.containers[0].free_time_days, 7)
		self.assertEqual(booking.containers[0].demurrage_free_time_days, 3)
		self.assertEqual(booking.containers[0].detention_free_time_days, 4)

	def test_copy_booking_containers_to_shipment_includes_free_time(self):
		bk_row = type(
			"Row",
			(),
			{
				"container_no": "CONT-001",
				"seal_no": "SEAL1",
				"type": "40HC",
				"mode": "FCL",
				"delivery_modes": "CY/CY",
				"sealed_by": None,
				"other_references": None,
				"size": "40ft",
				"packages_in_container": None,
				"weight_in_container": None,
				"volume_in_container": None,
				"max_weight": None,
				"max_volume": None,
				"utilization_percentage": None,
				"free_time_days": 14,
				"demurrage_free_time_days": 6,
				"detention_free_time_days": 9,
			},
		)()
		booking = type("BK", (), {"containers": [bk_row]})()
		shipment = type("SS", (), {"containers": []})()
		shipment.append = lambda table, data: shipment.containers.append(type("C", (), data)())

		copy_booking_containers_to_shipment(booking, shipment)

		self.assertEqual(len(shipment.containers), 1)
		self.assertEqual(shipment.containers[0].free_time_days, 14)
		self.assertEqual(shipment.containers[0].demurrage_free_time_days, 6)
		self.assertEqual(shipment.containers[0].detention_free_time_days, 9)
		self.assertIn("free_time_days", BOOKING_TO_SHIPMENT_CONTAINER_FIELDS)
		self.assertIn("demurrage_free_time_days", BOOKING_TO_SHIPMENT_CONTAINER_FIELDS)
		self.assertIn("detention_free_time_days", BOOKING_TO_SHIPMENT_CONTAINER_FIELDS)
		self.assertIn("demurrage_free_time_days", SALES_QUOTE_TO_BOOKING_CONTAINER_FIELDS)
		self.assertIn("detention_free_time_days", SALES_QUOTE_TO_BOOKING_CONTAINER_FIELDS)
