# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Unused portal debug files stay deleted, and the live customer page stays."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import logistics.patches.v3_0_retarget_transport_portal_template as patch


APP = Path(__file__).resolve().parents[1]

REMOVED = (
	"www/transport_debug.html",
	"www/warehousing_debug.html",
	"www/test_portal.html",
	"www/simple_test.html",
	"www/transport_portal_old.html",
	"api_backup.py",
	"transport/add_portal_items.py",
	"transport/add_portal_items_to_settings.py",
	"transport/add_to_portal_settings.py",
	"transport/create_portal_items.py",
	"transport/check_and_create_pages.py",
	"transport/check_portal_structure.py",
	"transport/www/__init__.py",
	"transport/www/transport_portal.py",
	"transport/www/transport_portal.html",
	"transport/www/test_portal.html",
	"transport/www/transport_job_detail.py",
	"transport/www/transport_job_detail.html",
)

KEPT = (
	"www/transport_portal.html",
	"www/transport_portal.py",
	"www/transport_job_detail.html",
	"www/transport_job_detail.py",
	"transport/api_telematics_debug.py",
)

TEMPLATE_DOCTYPES = (
	"transport/doctype/transport_portal_page/transport_portal_page.json",
	"transport/doctype/web_page/transport_portal_web_page.json",
)


class TestPortalLeftovers(unittest.TestCase):
	def test_removed_files_are_gone(self):
		for relative in REMOVED:
			self.assertFalse((APP / relative).exists(), relative)

	def test_customer_pages_and_telematics_stay(self):
		for relative in KEPT:
			self.assertTrue((APP / relative).is_file(), relative)

	def test_template_defaults_use_customer_page(self):
		for relative in TEMPLATE_DOCTYPES:
			doctype = json.loads((APP / relative).read_text())
			field = next(row for row in doctype["fields"] if row["fieldname"] == "template_path")
			self.assertEqual(field["default"], patch.NEW_TEMPLATE)

	def test_patch_rewrites_the_old_template(self):
		patches = (APP / "patches.txt").read_text()
		self.assertIn("logistics.patches.v3_0_retarget_transport_portal_template", patches)
		self.assertEqual(patch.OLD_TEMPLATE, "logistics/transport/www/transport_portal.html")
		self.assertEqual(patch.NEW_TEMPLATE, "logistics/www/transport_portal.html")
		self.assertEqual(
			patch.DOCTYPES,
			("Transport Portal Page", "Transport Portal Web Page"),
		)


if __name__ == "__main__":
	unittest.main()
