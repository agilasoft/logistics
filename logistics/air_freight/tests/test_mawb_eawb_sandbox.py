# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

import random

import frappe
from unittest.mock import patch, MagicMock

from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from logistics.air_freight.iata_cargo_xml.base_connector import IATAConnector
from logistics.air_freight.iata_cargo_xml.message_builder import MessageBuilder
from logistics.air_freight.tests.test_helpers import create_test_airline


class TestMAWBeAWBSandbox(FrappeTestCase):
	"""Tests for MAWB e-AWB sandbox and submit flow."""

	def setUp(self):
		create_test_airline("TA", "Test Airline")
		self.MAWB_NO = f"12345{random.randint(100000, 999999)}"
		self._ensure_iata_settings(test_mode=1, test_endpoint=None)
		self.mawb = self._create_mawb()

	def tearDown(self):
		frappe.db.rollback()

	def _ensure_iata_settings(self, test_mode=0, test_endpoint=None):
		from logistics.air_freight.utils.iata_settings_utils import get_settings

		company = frappe.defaults.get_user_default("Company") or frappe.db.get_single_value(
			"Global Defaults", "default_company"
		)
		if not company:
			company = frappe.db.get_value("Company", {}, "name")

		settings = get_settings(company=company)
		if not settings:
			settings = frappe.new_doc("IATA Settings")
			settings.company = company
			settings.flags.ignore_permissions = True
			settings.flags.ignore_validate = True
			settings.insert(ignore_permissions=True)

		settings.test_mode = test_mode
		settings.test_endpoint = test_endpoint or ""
		settings.cargo_xml_enabled = 0
		settings.flags.ignore_permissions = True
		settings.flags.ignore_validate = True
		settings.save()

	def _create_mawb(self, **overrides):
		data = {
			"doctype": "Master Air Waybill",
			"master_awb_no": self.MAWB_NO,
			"airline": "TA",
			"flight_no": "TA123",
			"flight_date": today(),
			"origin_airport_iata": "SIN",
			"destination_airport_iata": "LAX",
		}
		data.update(overrides)
		doc = frappe.get_doc(data)
		doc.insert(ignore_permissions=True)
		return doc

	def test_sandbox_mode_resolution(self):
		connector = IATAConnector()
		connector.settings = frappe._dict(test_mode=1, test_endpoint=None)
		self.assertEqual(connector.get_sandbox_mode(), "sandbox_mock")

		connector.settings = frappe._dict(test_mode=1, test_endpoint="https://sandbox.example/iata")
		self.assertEqual(connector.get_sandbox_mode(), "sandbox_endpoint")

		connector.settings = frappe._dict(test_mode=0, test_endpoint=None)
		self.assertEqual(connector.get_sandbox_mode(), "production")

	def test_sandbox_mock_does_not_call_http(self):
		builder = MessageBuilder()
		builder.settings = frappe._dict(test_mode=1, test_endpoint=None, debug_logging=0)
		xml = builder.build_mawb_eawb_message(self.mawb.name)

		with patch.object(builder.session, "post") as mock_post:
			result = builder.send_message(
				"XFWB",
				xml,
				reference_doctype="Master Air Waybill",
				reference_name=self.mawb.name,
			)

		mock_post.assert_not_called()
		self.assertTrue(result["success"])
		self.assertTrue(result["accepted"])
		self.assertEqual(result["sandbox_mode"], "sandbox_mock")

	def test_mawb_xfwb_message_content(self):
		builder = MessageBuilder()
		builder.settings = frappe._dict(test_mode=1, test_endpoint=None, debug_logging=0)
		xml = builder.build_mawb_eawb_message(self.mawb.name)

		self.assertIn("XFWB", xml)
		self.assertIn(self.MAWB_NO, xml)
		self.assertIn('AWBType="M"', xml)
		self.assertIn('AirportCode="SIN"', xml)
		self.assertIn('AirportCode="LAX"', xml)

		validation = builder.validate_message(xml, "XFWB")
		self.assertTrue(validation["valid"], validation.get("errors"))

	def test_submit_eawb_validation_missing_airline(self):
		mawb = self._create_mawb(master_awb_no=f"98765{random.randint(100000, 999999)}")
		mawb.airline = None
		with self.assertRaises(frappe.exceptions.ValidationError):
			mawb.validate_eawb_submission()

	def test_submit_eawb_validation_invalid_awb_format(self):
		mawb = self._create_mawb(master_awb_no="BAD-AWB")
		with self.assertRaises(frappe.exceptions.ValidationError):
			mawb.validate_eawb_submission()

	def test_submit_eawb_sandbox_success(self):
		builder = MessageBuilder()
		builder.settings = frappe._dict(test_mode=1, test_endpoint=None, debug_logging=0)
		with patch.object(builder.session, "post") as mock_post:
			with patch(
				"logistics.air_freight.iata_cargo_xml.message_builder.MessageBuilder",
				return_value=builder,
			):
				result = self.mawb.submit_eawb()

		mock_post.assert_not_called()
		self.assertTrue(result["success"])
		self.assertEqual(result["eawb_status"], "Accepted")
		self.assertEqual(result["sandbox_mode"], "sandbox_mock")

		self.mawb.reload()
		self.assertEqual(self.mawb.eawb_status, "Accepted")
		self.assertEqual(self.mawb.eawb_sandbox_mode, "sandbox_mock")
		self.assertTrue(self.mawb.eawb_submitted_date)
		self.assertTrue(self.mawb.eawb_message_id)

		queue = frappe.get_all(
			"IATA Message Queue",
			filters={
				"message_type": "XFWB",
				"reference_name": self.mawb.name,
				"direction": "Outbound",
			},
			limit=1,
		)
		self.assertTrue(queue)

	def test_test_endpoint_routing(self):
		builder = MessageBuilder()
		builder.settings = frappe._dict(
			test_mode=1,
			test_endpoint="https://sandbox.example/iata",
			debug_logging=0,
			cargo_xml_enabled=0,
		)
		xml = builder.build_mawb_eawb_message(self.mawb.name)

		mock_response = MagicMock()
		mock_response.status_code = 200
		mock_response.text = '<Acknowledgement Status="Accepted" MessageId="EXT-001" />'

		with patch.object(builder.session, "post", return_value=mock_response) as mock_post:
			result = builder.send_message("XFWB", xml)

		mock_post.assert_called_once()
		self.assertEqual(mock_post.call_args[0][0], "https://sandbox.example/iata")
		self.assertTrue(result["success"])
		self.assertEqual(result["sandbox_mode"], "sandbox_endpoint")

	def test_cannot_resubmit_accepted_eawb(self):
		self.mawb.eawb_status = "Accepted"
		self.mawb.save(ignore_permissions=True)
		with self.assertRaises(frappe.exceptions.ValidationError):
			self.mawb.validate_eawb_submission()
