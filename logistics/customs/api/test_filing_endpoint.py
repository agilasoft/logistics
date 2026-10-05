# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import sys
import types
import unittest

from logistics.customs.api.filing_endpoint import (
	filing_block_reason,
	is_configured_filing_endpoint,
)


class TestFilingEndpoint(unittest.TestCase):
	def test_empty_and_placeholder_endpoints_are_not_live(self):
		self.assertFalse(is_configured_filing_endpoint(None))
		self.assertFalse(is_configured_filing_endpoint(""))
		self.assertFalse(is_configured_filing_endpoint("  "))
		self.assertFalse(is_configured_filing_endpoint("https://api.cbp.gov/ams/v1"))
		self.assertFalse(is_configured_filing_endpoint("https://api.cbp.gov/ams/v1/"))
		self.assertFalse(is_configured_filing_endpoint("https://api.cbp.gov/isf/v1"))
		self.assertFalse(is_configured_filing_endpoint("https://api.cbsa-asfc.gc.ca/emanifest/v1"))
		self.assertFalse(is_configured_filing_endpoint("https://api.customs.go.jp/afr/v1"))

	def test_custom_endpoint_is_live(self):
		self.assertTrue(is_configured_filing_endpoint("https://filings.example.com/ams/v1"))

	def test_block_reason_distinguishes_missing_and_unsent(self):
		missing = filing_block_reason("US AMS", "")
		self.assertIn("Manifest Settings", missing)
		self.assertIn("left unchanged", missing)
		unsent = filing_block_reason("US AMS", "https://filings.example.com/ams/v1")
		self.assertIn("not sent", unsent)
		self.assertIn("not changed", unsent)


def _install_frappe_stub():
	frappe = types.ModuleType("frappe")

	class DoesNotExistError(Exception):
		pass

	frappe.DoesNotExistError = DoesNotExistError
	frappe._ = lambda message, *args, **kwargs: message
	frappe.log_error = lambda *args, **kwargs: None
	frappe.defaults = types.SimpleNamespace(get_user_default=lambda *args, **kwargs: None)
	frappe.logger = lambda: types.SimpleNamespace(info=lambda *args, **kwargs: None)
	utils = types.ModuleType("frappe.utils")
	utils.now_datetime = lambda: None
	frappe.utils = utils
	sys.modules["frappe"] = frappe
	sys.modules["frappe.utils"] = utils
	return frappe


class TestFilingClientsDoNotWriteMockStatus(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.frappe = _install_frappe_stub()
		from logistics.customs.api.ca_emanifest_api import CAeManifestAPI
		from logistics.customs.api.jp_afr_api import JPAFRAPI
		from logistics.customs.api.us_ams_api import USAMSAPI
		from logistics.customs.api.us_isf_api import USISFAPI

		cls.clients = (USAMSAPI, USISFAPI, CAeManifestAPI, JPAFRAPI)

	def _client(self, cls, settings, doc):
		def get_doc(doctype, name=None):
			if doctype == "Manifest Settings":
				if settings is None:
					raise self.frappe.DoesNotExistError
				return settings
			return doc

		self.frappe.get_doc = get_doc
		return cls(company="Test Company")

	def test_submit_leaves_draft_without_endpoint(self):
		for cls in self.clients:
			with self.subTest(cls=cls.__name__):
				doc = types.SimpleNamespace(status="Draft", saved=False)

				def save(ignore_permissions=False, _doc=doc):
					_doc.saved = True

				doc.save = save
				api = self._client(cls, None, doc)
				result = api.submit("FILING-1")
				self.assertFalse(result["success"])
				self.assertIn("Manifest Settings", result["message"])
				self.assertEqual(doc.status, "Draft")
				self.assertFalse(doc.saved)
				self.assertEqual(api.endpoint, "")

	def test_submit_leaves_draft_when_only_placeholder_is_set(self):
		doc = types.SimpleNamespace(status="Draft", saved=False)
		doc.save = lambda ignore_permissions=False: setattr(doc, "saved", True)
		settings = types.SimpleNamespace(cbp_api_endpoint="https://api.cbp.gov/ams/v1/")
		from logistics.customs.api.us_ams_api import USAMSAPI

		api = self._client(USAMSAPI, settings, doc)
		result = api.submit("AMS-1")
		self.assertFalse(result["success"])
		self.assertIn("Manifest Settings", result["message"])
		self.assertEqual(doc.status, "Draft")
		self.assertFalse(doc.saved)

	def test_submit_does_not_mark_accepted_when_live_endpoint_is_set(self):
		doc = types.SimpleNamespace(status="Draft", saved=False)
		doc.save = lambda ignore_permissions=False: setattr(doc, "saved", True)
		settings = types.SimpleNamespace(cbp_api_endpoint="https://filings.example.com/ams/v1")
		from logistics.customs.api.us_ams_api import USAMSAPI

		api = self._client(USAMSAPI, settings, doc)
		result = api.submit("AMS-1")
		self.assertFalse(result["success"])
		self.assertIn("not sent", result["message"])
		self.assertEqual(doc.status, "Draft")
		self.assertFalse(doc.saved)
		self.assertEqual(api.endpoint, "https://filings.example.com/ams/v1")

	def test_isf_endpoint_is_derived_only_from_a_live_cbp_url(self):
		doc = types.SimpleNamespace(status="Draft", saved=False)
		doc.save = lambda ignore_permissions=False: setattr(doc, "saved", True)
		settings = types.SimpleNamespace(cbp_api_endpoint="https://filings.example.com/ams/v1")
		from logistics.customs.api.us_isf_api import USISFAPI

		api = self._client(USISFAPI, settings, doc)
		self.assertEqual(api.endpoint, "https://filings.example.com/isf/v1")
		placeholder = types.SimpleNamespace(cbp_api_endpoint="https://api.cbp.gov/ams/v1")
		blocked = self._client(USISFAPI, placeholder, doc)
		self.assertEqual(blocked.endpoint, "")
		self.assertFalse(blocked.submit("ISF-1")["success"])
		self.assertFalse(doc.saved)

	def test_non_draft_is_rejected_before_filing(self):
		doc = types.SimpleNamespace(status="Accepted", saved=False)
		doc.save = lambda ignore_permissions=False: setattr(doc, "saved", True)
		from logistics.customs.api.us_ams_api import USAMSAPI

		api = self._client(USAMSAPI, None, doc)
		result = api.submit("AMS-1")
		self.assertFalse(result["success"])
		self.assertIn("Only Draft", result["message"])
		self.assertFalse(doc.saved)
