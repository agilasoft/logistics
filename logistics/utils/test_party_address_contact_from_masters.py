# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from logistics.utils.party_address_contact_from_masters import (
	apply_party_address_contact_from_source_or_masters,
	contact_display_text,
	copy_party_address_contact_fields,
	populate_party_address_contact_from_masters,
)


class TestPartyAddressContactFromMasters(FrappeTestCase):
	def test_contact_display_text_formats_contact(self):
		contact = frappe._dict(
			first_name="Jane",
			last_name="Doe",
			name="Jane Doe-Jane Doe",
			designation="Ops Manager",
			phone="+1 555 0100",
			mobile_no="+1 555 0101",
			email_id="jane@example.com",
		)
		with patch(
			"logistics.utils.party_address_contact_from_masters.frappe.get_doc",
			return_value=contact,
		), patch(
			"logistics.utils.party_address_contact_from_masters.frappe.db.exists",
			return_value=True,
		):
			text = contact_display_text("CONTACT-001")

		self.assertIn("Jane Doe", text)
		self.assertIn("Ops Manager", text)
		self.assertIn("jane@example.com", text)

	def test_copy_party_address_contact_fields_respects_only_if_empty(self):
		source = frappe._dict(
			shipper_contact="SRC-SHIPPER-CONTACT",
			shipper_contact_display="Source Shipper",
			consignee_contact="SRC-CONSIGNEE-CONTACT",
		)
		target = frappe.new_doc("Transport Order")
		target.shipper_contact = "EXISTING-SHIPPER-CONTACT"

		with patch(
			"logistics.utils.party_address_contact_from_masters.frappe.get_meta"
		) as get_meta:
			get_meta.return_value.get_field.side_effect = lambda fn: frappe._dict(fieldname=fn)
			copy_party_address_contact_fields(source, target, only_if_empty=True)

		self.assertEqual(target.shipper_contact, "EXISTING-SHIPPER-CONTACT")
		self.assertEqual(target.consignee_contact, "SRC-CONSIGNEE-CONTACT")

	def test_apply_party_address_contact_prefers_source_then_masters(self):
		quote = frappe._dict(
			shipper="SHIPPER-A",
			consignee="CONSIGNEE-A",
			shipper_contact="QUOTE-SHIPPER-CONTACT",
			shipper_contact_display="Quote Shipper",
		)
		order = frappe.new_doc("Transport Order")
		order.shipper = "SHIPPER-A"
		order.consignee = "CONSIGNEE-A"
		shipper = frappe._dict(
			shipper_primary_contact="MASTER-SHIPPER-CONTACT",
			pick_address="ADDR-SHIPPER",
			shipper_primary_address=None,
		)
		consignee = frappe._dict(
			consignee_primary_contact="MASTER-CONSIGNEE-CONTACT",
			delivery_address="ADDR-CONSIGNEE",
			consignee_primary_address=None,
		)

		with patch(
			"logistics.utils.party_address_contact_from_masters.frappe.get_meta"
		) as get_meta, patch(
			"logistics.utils.party_address_contact_from_masters.frappe.db.exists",
			return_value=True,
		), patch(
			"logistics.utils.party_address_contact_from_masters.frappe.get_cached_doc",
			side_effect=lambda doctype, name: shipper if doctype == "Shipper" else consignee,
		), patch(
			"logistics.utils.party_address_contact_from_masters.get_address_display",
			side_effect=lambda addr: f"Display for {addr}",
		), patch(
			"logistics.utils.party_address_contact_from_masters.contact_display_text",
			side_effect=lambda name: f"Display for {name}",
		):
			get_meta.return_value.get_field.side_effect = lambda fn: frappe._dict(fieldname=fn)
			apply_party_address_contact_from_source_or_masters(order, quote)

		self.assertEqual(order.shipper_contact, "QUOTE-SHIPPER-CONTACT")
		self.assertEqual(order.shipper_contact_display, "Quote Shipper")
		self.assertEqual(order.consignee_contact, "MASTER-CONSIGNEE-CONTACT")
		self.assertEqual(order.consignee_address, "ADDR-CONSIGNEE")

	def test_populate_party_address_contact_from_masters_skips_unknown_doctype(self):
		doc = frappe._dict(doctype="Customer", shipper="SHIPPER-A")
		populate_party_address_contact_from_masters(doc)
		self.assertFalse(getattr(doc, "shipper_contact", None))
