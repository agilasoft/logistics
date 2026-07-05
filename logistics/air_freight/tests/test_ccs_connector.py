# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

import random
from unittest.mock import MagicMock, patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today

from logistics.air_freight.iata_cargo_xml.base_connector import IATAConnector
from logistics.air_freight.iata_cargo_xml.ccs.base import ChampTraxonConnector
from logistics.air_freight.iata_cargo_xml.ccs.factory import get_ccs_connector, uses_ccs_hub
from logistics.air_freight.iata_cargo_xml.ccs.routing import resolve_airline_pima
from logistics.air_freight.iata_cargo_xml.message_builder import MessageBuilder
from logistics.air_freight.tests.test_helpers import create_test_airline


class TestCCSConnector(FrappeTestCase):
	def setUp(self):
		create_test_airline("TA", "Test Airline")
		frappe.db.set_value("Airline", "TA", "ccs_pima_code", "TAFFWD")
		self._ensure_ccs_provider()
		self._ensure_iata_settings_ccs()
		self.mawb = self._create_mawb()

	def tearDown(self):
		frappe.db.rollback()

	def _ensure_ccs_provider(self):
		if not frappe.db.exists("CCS Provider", "CHAMP_TRAXON"):
			frappe.get_doc(
				{
					"doctype": "CCS Provider",
					"provider_code": "CHAMP_TRAXON",
					"provider_name": "CHAMP TRAXON cargoHUB",
					"connector_type": "champ_traxon",
					"default_endpoint": "https://ccs.example/champ",
					"test_endpoint": "https://ccs-sandbox.example/champ",
					"requires_pima_routing": 1,
					"is_active": 1,
				}
			).insert(ignore_permissions=True)

	def _ensure_iata_settings_ccs(self):
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

		settings.cargo_xml_enabled = 1
		settings.connection_mode = "CCS Hub"
		settings.ccs_provider = "CHAMP_TRAXON"
		settings.ccs_participant_code = "FFWD01"
		settings.ccs_username = "ccs-user"
		settings.ccs_password = "ccs-pass"
		settings.test_mode = 0
		settings.flags.ignore_permissions = True
		settings.flags.ignore_validate = True
		settings.save(ignore_permissions=True)

	def _create_mawb(self):
		mawb_no = f"12345{random.randint(100000, 999999)}"
		doc = frappe.get_doc(
			{
				"doctype": "Master Air Waybill",
				"master_awb_no": mawb_no,
				"airline": "TA",
				"flight_no": "TA100",
				"flight_date": today(),
				"origin_airport_iata": "SIN",
				"destination_airport_iata": "LHR",
			}
		)
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
		return doc

	def test_resolve_airline_pima_prefers_ccs_code(self):
		self.assertEqual(resolve_airline_pima("TA"), "TAFFWD")

	def test_uses_ccs_hub(self):
		from logistics.air_freight.utils.iata_settings_utils import get_settings

		settings = get_settings(company=self.mawb.company if hasattr(self.mawb, "company") else None)
		self.assertTrue(uses_ccs_hub(settings))

	def test_ccs_connector_builds_pima_headers(self):
		from logistics.air_freight.utils.iata_settings_utils import get_settings

		settings = get_settings()
		connector = get_ccs_connector(settings)
		self.assertIsInstance(connector, ChampTraxonConnector)

		headers = connector.build_headers(
			"XFWB",
			"<XFWB/>",
			{"airline_pima": "TAFFWD", "awb_number": "12345678901"},
		)
		self.assertEqual(headers["X-Sender-PIMA"], "FFWD01")
		self.assertEqual(headers["X-Recipient-PIMA"], "TAFFWD")
		self.assertEqual(headers["X-CHAMP-Provider"], "TRAXON")

	def test_send_message_routes_through_ccs_hub(self):
		builder = MessageBuilder()
		xml = builder.build_mawb_eawb_message(self.mawb.name)

		mock_response = MagicMock()
		mock_response.status_code = 200
		mock_response.text = '<Acknowledgement Status="Accepted" />'

		with patch.object(builder.session, "post", return_value=mock_response) as mock_post:
			result = builder.send_message(
				"XFWB",
				xml,
				reference_doctype="Master Air Waybill",
				reference_name=self.mawb.name,
				airline="TA",
			)

		self.assertTrue(result["success"])
		self.assertEqual(result["ccs_provider"], "CHAMP_TRAXON")
		self.assertEqual(mock_post.call_args[0][0], "https://ccs.example/champ")
		headers = mock_post.call_args[1]["headers"]
		self.assertEqual(headers["X-Recipient-PIMA"], "TAFFWD")

	def test_ccs_test_endpoint_used_in_test_mode(self):
		from logistics.air_freight.utils.iata_settings_utils import get_settings

		settings = get_settings()
		settings.test_mode = 1
		settings.flags.ignore_validate = True
		settings.save(ignore_permissions=True)

		connector = IATAConnector(company=settings.company)
		endpoint, mode = connector._resolve_endpoint()
		self.assertEqual(endpoint, "https://ccs-sandbox.example/champ")
		self.assertIn("ccs", mode)
