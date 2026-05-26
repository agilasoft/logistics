# Copyright (c) 2026, logistics.agilasoft.com and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from logistics.air_freight.tests.test_helpers import create_test_unloco
from logistics.utils.customs_country_defaults import country_from_unloco
from logistics.utils.customs_country_defaults import (
	apply_internal_job_customs_country_defaults,
)
from logistics.utils.customs_master_transport_defaults import (
	apply_internal_job_master_transport_defaults,
)
from logistics.utils.shipper_consignee_defaults import apply_shipper_consignee_defaults


class TestCustomsMasterTransportDefaults(FrappeTestCase):
	@classmethod
	def setUpClass(cls):
		super().setUpClass()
		cls.us_country = frappe.db.get_value("Country", {"code": "US"}, "name")
		cls.cn_country = frappe.db.get_value("Country", {"code": "CN"}, "name")
		cls.sg_country = frappe.db.get_value("Country", {"code": "SG"}, "name")
		if not cls.us_country or not cls.cn_country or not cls.sg_country:
			raise cls.skipTest("Country masters US/CN/SG required for customs country tests")

	def setUp(self):
		create_test_unloco("USLAX", "Los Angeles", country_code="US")
		create_test_unloco("CNSHA", "Shanghai", country_code="CN")
		create_test_unloco("SGSIN", "Singapore", country_code="SG")

	def _patch_master_exists(self):
		return patch("frappe.db.exists", return_value=True)

	def test_country_from_unloco_by_country_code(self):
		self.assertEqual(country_from_unloco("USLAX"), self.us_country)
		self.assertEqual(country_from_unloco("CNSHA"), self.cn_country)

	def test_country_from_unloco_missing_returns_none(self):
		self.assertIsNone(country_from_unloco(None))
		self.assertIsNone(country_from_unloco("ZZZZZ"))

	def test_sea_mbl_fills_transport_and_countries(self):
		main_job = frappe._dict(
			doctype="Sea Shipment",
			name="SEA-TEST-001",
			master_bill="MBL-TEST-001",
			origin_port="SGSIN",
			destination_port="SGSIN",
		)
		mbl = frappe._dict(
			doctype="Master Bill",
			name="MBL-TEST-001",
			master_bl="MBL123456",
			vessel="OCEAN STAR",
			voyage_no="V001",
			origin_port="USLAX",
			destination_port="CNSHA",
		)
		order = frappe.new_doc("Declaration Order")
		order.is_internal_job = 1
		order.main_job_type = "Sea Shipment"
		order.main_job = main_job.name

		def _get_cached_doc(doctype, name):
			if doctype == "Master Bill" and name == "MBL-TEST-001":
				return mbl
			raise frappe.DoesNotExistError

		with (
			patch(
				"logistics.utils.customs_master_transport_defaults._load_main_job_doc",
				return_value=main_job,
			),
			patch("frappe.get_cached_doc", side_effect=_get_cached_doc),
			self._patch_master_exists(),
		):
			apply_internal_job_master_transport_defaults(order)

		self.assertEqual(order.vessel_flight_number, "OCEAN STAR / V001")
		self.assertEqual(order.transport_document_number, "MBL123456")
		self.assertEqual(order.country_of_origin, self.us_country)
		self.assertEqual(order.country_of_destination, self.cn_country)

	def test_mbl_with_blank_ports_falls_back_to_shipment_ports(self):
		main_job = frappe._dict(
			doctype="Sea Shipment",
			name="SEA-TEST-MBL-BLANK",
			master_bill="MBL-BLANK-PORTS",
			origin_port="USLAX",
			destination_port="CNSHA",
		)
		mbl = frappe._dict(
			doctype="Master Bill",
			name="MBL-BLANK-PORTS",
			master_bl="MBL000",
			vessel="VESSEL",
			voyage_no="V1",
			origin_port=None,
			destination_port=None,
		)
		order = frappe.new_doc("Declaration Order")
		order.is_internal_job = 1
		order.main_job_type = "Sea Shipment"
		order.main_job = main_job.name
		order.port_of_loading = "USLAX"
		order.port_of_discharge = "CNSHA"

		def _get_cached_doc(doctype, name):
			if doctype == "Master Bill" and name == "MBL-BLANK-PORTS":
				return mbl
			raise frappe.DoesNotExistError

		with (
			patch(
				"logistics.utils.customs_master_transport_defaults._load_main_job_doc",
				return_value=main_job,
			),
			patch(
				"logistics.utils.customs_country_defaults._load_main_job_doc",
				return_value=main_job,
			),
			patch("frappe.get_cached_doc", side_effect=_get_cached_doc),
			self._patch_master_exists(),
		):
			apply_internal_job_customs_country_defaults(order)

		self.assertEqual(order.country_of_origin, self.us_country)
		self.assertEqual(order.country_of_destination, self.cn_country)

	def test_sea_without_mbl_leaves_fields_empty(self):
		main_job = frappe._dict(
			doctype="Sea Shipment",
			name="SEA-TEST-002",
			master_bill=None,
			origin_port="USLAX",
			destination_port="CNSHA",
			routing_legs=[],
			mbl_origin_port="DEHAM",
		)
		order = frappe.new_doc("Declaration Order")
		order.is_internal_job = 1
		order.main_job_type = "Sea Shipment"
		order.main_job = main_job.name
		order.port_of_loading = "USLAX"
		order.port_of_discharge = "CNSHA"

		with (
			patch(
				"logistics.utils.customs_master_transport_defaults._load_main_job_doc",
				return_value=main_job,
			),
			patch(
				"logistics.utils.customs_country_defaults._load_main_job_doc",
				return_value=main_job,
			),
		):
			apply_internal_job_customs_country_defaults(order)

		self.assertFalse(order.vessel_flight_number)
		self.assertFalse(order.transport_document_number)
		self.assertFalse(order.country_of_origin)
		self.assertFalse(order.country_of_destination)

	def test_air_mawb_fills_transport_and_countries(self):
		main_job = frappe._dict(
			doctype="Air Shipment",
			name="AIR-TEST-001",
			master_awb="MAWB-TEST-001",
		)
		mawb = frappe._dict(
			doctype="Master Air Waybill",
			name="MAWB-TEST-001",
			master_awb_no="123-45678901",
			flight_no="CX888",
			origin_airport="USLAX",
			destination_airport="CNSHA",
		)
		order = frappe.new_doc("Declaration Order")
		order.is_internal_job = 1
		order.main_job_type = "Air Shipment"
		order.main_job = main_job.name

		def _get_cached_doc(doctype, name):
			if doctype == "Master Air Waybill" and name == "MAWB-TEST-001":
				return mawb
			raise frappe.DoesNotExistError

		with (
			patch(
				"logistics.utils.customs_master_transport_defaults._load_main_job_doc",
				return_value=main_job,
			),
			patch("frappe.get_cached_doc", side_effect=_get_cached_doc),
			self._patch_master_exists(),
		):
			apply_internal_job_master_transport_defaults(order)

		self.assertEqual(order.vessel_flight_number, "CX888")
		self.assertEqual(order.transport_document_number, "123-45678901")
		self.assertEqual(order.country_of_origin, self.us_country)
		self.assertEqual(order.country_of_destination, self.cn_country)

	def test_air_without_mawb_leaves_fields_empty(self):
		main_job = frappe._dict(
			doctype="Air Shipment",
			name="AIR-TEST-002",
			master_awb=None,
		)
		order = frappe.new_doc("Declaration Order")
		order.is_internal_job = 1
		order.main_job_type = "Air Shipment"
		order.main_job = main_job.name

		with patch(
			"logistics.utils.customs_master_transport_defaults._load_main_job_doc",
			return_value=main_job,
		):
			apply_internal_job_master_transport_defaults(order)

		self.assertFalse(order.vessel_flight_number)
		self.assertFalse(order.transport_document_number)
		self.assertFalse(order.country_of_origin)
		self.assertFalse(order.country_of_destination)

	def test_does_not_overwrite_existing_values(self):
		main_job = frappe._dict(
			doctype="Sea Shipment",
			name="SEA-TEST-003",
			master_bill="MBL-TEST-003",
		)
		mbl = frappe._dict(
			doctype="Master Bill",
			name="MBL-TEST-003",
			master_bl="MBL999",
			vessel="NEW VESSEL",
			voyage_no="V99",
			origin_port="USLAX",
			destination_port="CNSHA",
		)
		order = frappe.new_doc("Declaration Order")
		order.is_internal_job = 1
		order.main_job_type = "Sea Shipment"
		order.main_job = main_job.name
		order.country_of_origin = self.sg_country
		order.vessel_flight_number = "KEEP ME"

		def _get_cached_doc(doctype, name):
			if doctype == "Master Bill" and name == "MBL-TEST-003":
				return mbl
			raise frappe.DoesNotExistError

		with (
			patch(
				"logistics.utils.customs_master_transport_defaults._load_main_job_doc",
				return_value=main_job,
			),
			patch("frappe.get_cached_doc", side_effect=_get_cached_doc),
			self._patch_master_exists(),
		):
			apply_internal_job_master_transport_defaults(order)

		self.assertEqual(order.country_of_origin, self.sg_country)
		self.assertEqual(order.vessel_flight_number, "KEEP ME")
		self.assertEqual(order.transport_document_number, "MBL999")
		self.assertEqual(order.country_of_destination, self.cn_country)

	def test_skips_non_internal_job(self):
		main_job = frappe._dict(
			doctype="Sea Shipment",
			name="SEA-TEST-004",
			master_bill="MBL-TEST-004",
		)
		order = frappe.new_doc("Declaration Order")
		order.is_internal_job = 0

		with patch(
			"logistics.utils.customs_master_transport_defaults._load_main_job_doc",
			return_value=main_job,
		):
			apply_internal_job_master_transport_defaults(order)

		self.assertFalse(order.country_of_origin)
		self.assertFalse(order.country_of_destination)

	def test_consignee_default_after_mbl_ports_fail(self):
		consignee_code = "TEST-CUSTOMS-COO"
		if frappe.db.exists("Consignee", consignee_code):
			frappe.delete_doc("Consignee", consignee_code, force=1)

		consignee = frappe.get_doc(
			{
				"doctype": "Consignee",
				"code": consignee_code,
				"consignee_name": "Test Customs COO Consignee",
				"customs_default_country_of_origin": self.sg_country,
			}
		)
		consignee.insert(ignore_permissions=True)

		main_job = frappe._dict(
			doctype="Transport Job",
			name="TJ-TEST-001",
		)
		order = frappe.new_doc("Declaration Order")
		order.is_internal_job = 1
		order.importer_consignee = consignee_code

		with patch(
			"logistics.utils.customs_master_transport_defaults._load_main_job_doc",
			return_value=main_job,
		):
			apply_internal_job_master_transport_defaults(order)
			apply_shipper_consignee_defaults(order)

		self.assertEqual(order.country_of_origin, self.sg_country)

		frappe.delete_doc("Consignee", consignee_code, force=1)

	def test_mbl_country_wins_over_consignee_default(self):
		consignee_code = "TEST-CUSTOMS-COO-2"
		if frappe.db.exists("Consignee", consignee_code):
			frappe.delete_doc("Consignee", consignee_code, force=1)

		consignee = frappe.get_doc(
			{
				"doctype": "Consignee",
				"code": consignee_code,
				"consignee_name": "Test Customs COO Consignee 2",
				"customs_default_country_of_origin": self.sg_country,
			}
		)
		consignee.insert(ignore_permissions=True)

		main_job = frappe._dict(
			doctype="Sea Shipment",
			name="SEA-TEST-005",
			master_bill="MBL-TEST-005",
		)
		mbl = frappe._dict(
			doctype="Master Bill",
			name="MBL-TEST-005",
			master_bl="MBL555",
			vessel="VESSEL",
			voyage_no=None,
			origin_port="USLAX",
			destination_port=None,
		)
		order = frappe.new_doc("Declaration Order")
		order.is_internal_job = 1
		order.main_job_type = "Sea Shipment"
		order.main_job = main_job.name
		order.importer_consignee = consignee_code

		real_get_cached_doc = frappe.get_cached_doc

		def _get_cached_doc(doctype, name):
			if doctype == "Master Bill" and name == "MBL-TEST-005":
				return mbl
			return real_get_cached_doc(doctype, name)

		with (
			patch(
				"logistics.utils.customs_master_transport_defaults._load_main_job_doc",
				return_value=main_job,
			),
			patch("frappe.get_cached_doc", side_effect=_get_cached_doc),
			self._patch_master_exists(),
		):
			apply_internal_job_master_transport_defaults(order)
			apply_shipper_consignee_defaults(order)

		self.assertEqual(order.country_of_origin, self.us_country)

		frappe.delete_doc("Consignee", consignee_code, force=1)
