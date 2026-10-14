# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

import unittest

from logistics.utils.declaration_transport_locations import (
	DeclarationContainerChoiceError,
	apply_linked_service_locations,
	choose_declaration_container,
	linked_service_transport_locations,
)


class _Order:
	def __init__(self):
		self.location_type = "UNLOCO"
		self.location_from = "JPKOB"
		self.location_to = "PHMNL"


class TestLinkedServiceTransportLocations(unittest.TestCase):
	def test_blank_from_and_to_stay_blank_and_keep_zone_type(self):
		row = {
			"location_type": "Transport Zone",
			"location_from": "",
			"location_to": None,
			"origin_port": "JPKOB",
			"destination_port": "PHMNL",
		}
		self.assertEqual(
			linked_service_transport_locations(row),
			{
				"location_type": "Transport Zone",
				"location_from": None,
				"location_to": None,
			},
		)

	def test_apply_replaces_preset_unloco_ports(self):
		order = _Order()
		apply_linked_service_locations(
			order,
			{"location_type": "Transport Zone", "location_from": "ZONE-A", "location_to": "ZONE-B"},
		)
		self.assertEqual(order.location_type, "Transport Zone")
		self.assertEqual(order.location_from, "ZONE-A")
		self.assertEqual(order.location_to, "ZONE-B")

	def test_apply_clears_ports_when_service_has_no_places(self):
		order = _Order()
		apply_linked_service_locations(order, {"location_type": "Transport Zone"})
		self.assertEqual(order.location_type, "Transport Zone")
		self.assertIsNone(order.location_from)
		self.assertIsNone(order.location_to)

	def test_no_service_row_leaves_locations_empty(self):
		order = _Order()
		apply_linked_service_locations(order, None)
		self.assertIsNone(order.location_type)
		self.assertIsNone(order.location_from)
		self.assertIsNone(order.location_to)


class TestChooseDeclarationContainer(unittest.TestCase):
	def setUp(self):
		self.containers = [
			{"container": "CONT-A", "container_number": "MSCU1111115", "label": "MSCU1111115"},
			{"container": "CONT-B", "container_number": "MSCU2222220", "label": "MSCU2222220"},
		]

	def test_linked_service_container_is_left_alone(self):
		self.assertIsNone(
			choose_declaration_container(
				self.containers,
				linked_container_no="MSCU9999994",
				selected="CONT-A",
			)
		)

	def test_single_container_is_used_without_a_pick(self):
		only = [self.containers[0]]
		self.assertEqual(
			choose_declaration_container(only, linked_container_no="", selected=""),
			only[0],
		)

	def test_multiple_containers_require_a_pick(self):
		with self.assertRaises(DeclarationContainerChoiceError) as raised:
			choose_declaration_container(self.containers, linked_container_no="", selected="")
		self.assertEqual(raised.exception.code, "required")

	def test_pick_matches_container_link_or_number(self):
		by_link = choose_declaration_container(
			self.containers, linked_container_no="", selected="CONT-B"
		)
		by_number = choose_declaration_container(
			self.containers, linked_container_no="", selected="MSCU1111115"
		)
		self.assertEqual(by_link["container"], "CONT-B")
		self.assertEqual(by_number["container"], "CONT-A")

	def test_unknown_pick_is_rejected(self):
		with self.assertRaises(DeclarationContainerChoiceError) as raised:
			choose_declaration_container(
				self.containers, linked_container_no="", selected="CONT-Z"
			)
		self.assertEqual(raised.exception.code, "invalid")
