# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import sys
import types
import unittest
from types import SimpleNamespace

from logistics.customs.filing_route import country_key, plan_filings


class TestFilingRoute(unittest.TestCase):
	def test_country_key_uses_name_or_code(self):
		self.assertEqual(country_key("United States", ""), "US")
		self.assertEqual(country_key("United States", "us"), "US")
		self.assertEqual(country_key("", "US"), "US")
		self.assertEqual(country_key("Canada", ""), "CA")
		self.assertEqual(country_key("Japan", "JP"), "JP")
		self.assertEqual(country_key("Singapore", "SG"), "")

	def test_united_states_files_ams_and_optional_isf(self):
		ams_only = plan_filings("United States", "US", {"enable_us_ams": 1, "enable_us_isf": 0})
		self.assertEqual(ams_only["filings"], ["US AMS"])
		both = plan_filings("United States", "US", {"enable_us_ams": 1, "enable_us_isf": 1})
		self.assertEqual(both["filings"], ["US AMS", "US ISF"])

	def test_isf_without_ams_does_not_file(self):
		plan = plan_filings("United States", "US", {"enable_us_ams": 0, "enable_us_isf": 1})
		self.assertEqual(plan["filings"], [])
		self.assertEqual(plan["reason"], "disabled")

	def test_canada_and_japan_follow_their_flags(self):
		canada = plan_filings("Canada", "CA", {"enable_ca_emanifest": 1})
		self.assertEqual(canada["filings"], ["CA eManifest Forwarder"])
		japan = plan_filings("Japan", "JP", {"enable_jp_afr": 1})
		self.assertEqual(japan["filings"], ["JP AFR"])
		self.assertEqual(plan_filings("Canada", "CA", {"enable_ca_emanifest": 0})["reason"], "disabled")
		self.assertEqual(plan_filings("Japan", "JP", {})["reason"], "disabled")

	def test_other_country_is_unsupported(self):
		plan = plan_filings("Singapore", "SG", {"enable_us_ams": 1, "enable_ca_emanifest": 1})
		self.assertEqual(plan["filings"], [])
		self.assertEqual(plan["reason"], "unsupported")


def _install_frappe_stub():
	frappe = sys.modules.get("frappe")
	if frappe is None:
		frappe = types.ModuleType("frappe")
		sys.modules["frappe"] = frappe

	class DoesNotExistError(Exception):
		pass

	def whitelist(*args, **kwargs):
		if args and callable(args[0]) and not kwargs:
			return args[0]

		def decorator(fn):
			return fn

		return decorator

	def throw(message, *args, **kwargs):
		raise Exception(message)

	frappe.DoesNotExistError = getattr(frappe, "DoesNotExistError", DoesNotExistError)
	frappe._ = lambda message, *args, **kwargs: message
	frappe.whitelist = whitelist
	frappe.log_error = lambda *args, **kwargs: None
	frappe.throw = throw
	frappe.defaults = types.SimpleNamespace(get_user_default=lambda *args, **kwargs: None)
	frappe.logger = lambda: types.SimpleNamespace(info=lambda *args, **kwargs: None)
	utils = sys.modules.get("frappe.utils") or types.ModuleType("frappe.utils")
	utils.getdate = lambda value: value
	utils.nowdate = lambda: "2026-10-04"
	utils.now_datetime = lambda: None
	frappe.utils = utils
	sys.modules["frappe.utils"] = utils
	model = sys.modules.get("frappe.model") or types.ModuleType("frappe.model")
	document = sys.modules.get("frappe.model.document") or types.ModuleType("frappe.model.document")
	document.Document = getattr(document, "Document", object)
	model.document = document
	frappe.model = model
	sys.modules["frappe.model"] = model
	sys.modules["frappe.model.document"] = document
	return frappe


class TestFileManifestUsesCompanySettings(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		cls.frappe = _install_frappe_stub()
		from logistics.customs.doctype.global_manifest.global_manifest import file_manifest

		cls.file_manifest = staticmethod(file_manifest)

	@classmethod
	def tearDownClass(cls):
		# Drop modules that captured this stub so later tests can install their own.
		for name in list(sys.modules):
			if name == "frappe" or name.startswith("frappe."):
				del sys.modules[name]
			elif name.startswith("logistics.customs.api.") and name != "logistics.customs.api.filing_endpoint":
				del sys.modules[name]
			elif name == "logistics.customs.doctype.global_manifest.global_manifest":
				del sys.modules[name]

	def test_live_endpoint_submits_existing_ams_and_does_not_save_manifest(self):
		saved = []
		manifest = SimpleNamespace(
			name="GM-0001",
			company="Acme",
			country="United States",
			save=lambda *args, **kwargs: saved.append("manifest"),
		)
		settings = SimpleNamespace(
			enable_us_ams=1,
			enable_us_isf=0,
			enable_ca_emanifest=0,
			enable_jp_afr=0,
			cbp_api_endpoint="https://filings.example.com/ams/v1",
			cbp_api_username="user",
			cbp_api_password="secret",
			ams_filer_code="ABCD",
		)
		ams = SimpleNamespace(name="AMS-0001", status="Draft", save=lambda *args, **kwargs: saved.append("ams"))

		def get_doc(doctype, name=None):
			if doctype == "Global Manifest":
				return manifest
			if doctype == "Manifest Settings":
				return settings
			if doctype == "US AMS":
				return ams
			raise self.frappe.DoesNotExistError

		def get_value(doctype, filters, fieldname="name"):
			if doctype == "Country":
				return "US"
			if doctype == "US AMS":
				return "AMS-0001"
			return None

		self.frappe.get_doc = get_doc
		self.frappe.db = SimpleNamespace(get_value=get_value)
		result = self.file_manifest("GM-0001")
		self.assertFalse(result["success"])
		self.assertEqual(result["filing"], {"doctype": "US AMS", "name": "AMS-0001"})
		self.assertIn("not sent", result["message"])
		self.assertEqual(saved, [])

	def test_disabled_flag_does_not_open_a_filing(self):
		lookups = []
		manifest = SimpleNamespace(name="GM-0002", company="Acme", country="Canada", save=lambda *a, **k: None)
		settings = SimpleNamespace(enable_us_ams=0, enable_us_isf=0, enable_ca_emanifest=0, enable_jp_afr=0)

		def get_doc(doctype, name=None):
			if doctype == "Global Manifest":
				return manifest
			if doctype == "Manifest Settings":
				return settings
			raise self.frappe.DoesNotExistError

		def get_value(doctype, filters, fieldname="name"):
			lookups.append(doctype)
			if doctype == "Country":
				return "CA"
			return None

		self.frappe.get_doc = get_doc
		self.frappe.db = SimpleNamespace(get_value=get_value)
		result = self.file_manifest("GM-0002")
		self.assertFalse(result["success"])
		self.assertEqual(result["filings"], [])
		self.assertIn("left unchanged", result["message"])
		self.assertNotIn("CA eManifest Forwarder", lookups)

	def test_missing_settings_leaves_the_manifest_alone(self):
		manifest = SimpleNamespace(name="GM-0003", company="Acme", country="Japan")

		def get_doc(doctype, name=None):
			if doctype == "Global Manifest":
				return manifest
			raise self.frappe.DoesNotExistError

		self.frappe.get_doc = get_doc
		self.frappe.db = SimpleNamespace(get_value=lambda *args, **kwargs: None)
		result = self.file_manifest("GM-0003")
		self.assertFalse(result["success"])
		self.assertIn("Manifest Settings", result["message"])
		self.assertEqual(result["filings"], [])
