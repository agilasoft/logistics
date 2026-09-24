# Copyright (c) 2026, www.agilasoft.com and Contributors
# See license.txt

from unittest.mock import patch

import frappe
from frappe.tests import IntegrationTestCase

from logistics.mice.print_format.mice_project_manifest.mice_project_manifest import (
	_build_row,
	_format_qty,
	_format_weight,
	get_mice_project_manifest_rows,
)


class TestMiceProjectManifest(IntegrationTestCase):
	def test_get_rows_empty_without_project_name(self):
		self.assertEqual(get_mice_project_manifest_rows({}), [])
		self.assertEqual(get_mice_project_manifest_rows(None), [])

	@patch(
		"logistics.mice.print_format.mice_project_manifest.mice_project_manifest._organizer_name",
		return_value="Show Org Inc.",
	)
	@patch("frappe.get_all")
	def test_get_rows_one_docket(self, mock_get_all, _mock_org):
		docket_rows = [
			{
				"name": "DK-TEST-1",
				"job_number": "JN-001",
				"exhibitor": "CUST-1",
				"exhibitor_name": "Acme Exhibitor",
				"description": "<p>Booth materials</p>",
				"total_packages": 3,
				"total_weight": 120,
				"total_weight_uom": "KG",
				"total_volume": 2.5,
				"total_volume_uom": "CBM",
				"sales_invoice": None,
				"sales_quote": None,
				"required_by": "2026-01-10",
			}
		]

		def _get_all_side_effect(doctype, *args, **kwargs):
			if doctype == "Docket":
				return docket_rows
			return []

		mock_get_all.side_effect = _get_all_side_effect
		with patch(
			"logistics.mice.print_format.mice_project_manifest.mice_project_manifest._find_primary_shipment",
			return_value=("", ""),
		), patch(
			"logistics.mice.print_format.mice_project_manifest.mice_project_manifest._declaration_clearance_date",
			return_value="",
		), patch(
			"logistics.mice.print_format.mice_project_manifest.mice_project_manifest._ingress_schedule",
			return_value="01-10-2026",
		), patch(
			"logistics.mice.print_format.mice_project_manifest.mice_project_manifest._exhibitor_contact",
			return_value="",
		):
			rows = get_mice_project_manifest_rows({"name": "EP-00001"})
		self.assertEqual(len(rows), 1)
		row = rows[0]
		self.assertEqual(row["job_no"], "JN-001")
		self.assertEqual(row["exhibitor"], "Acme Exhibitor")
		self.assertEqual(row["org"], "Show Org Inc.")
		self.assertEqual(row["description"], "Booth materials")
		self.assertEqual(row["qty_pkgs"], "3")
		self.assertIn("120", row["g_weight_kg"])
		self.assertIn("2.5", row["volume_cbm"])
		self.assertEqual(row["ingress_schedule"], "01-10-2026")

	def test_format_qty_and_weight(self):
		self.assertEqual(_format_qty(None), "-")
		self.assertEqual(_format_qty(0), "0")
		self.assertEqual(_format_qty(4), "4")
		dk = {"total_weight": 50, "total_weight_uom": "KG"}
		self.assertEqual(_format_weight(dk), "50 KG")

	def test_build_row_defaults_dashes(self):
		with patch(
			"logistics.mice.print_format.mice_project_manifest.mice_project_manifest._find_primary_shipment",
			return_value=("", ""),
		), patch(
			"logistics.mice.print_format.mice_project_manifest.mice_project_manifest._docket_description",
			return_value="",
		), patch(
			"logistics.mice.print_format.mice_project_manifest.mice_project_manifest._ingress_schedule",
			return_value="",
		), patch(
			"logistics.mice.print_format.mice_project_manifest.mice_project_manifest._exhibitor_contact",
			return_value="",
		), patch(
			"logistics.mice.print_format.mice_project_manifest.mice_project_manifest._declaration_clearance_date",
			return_value="",
		):
			row = _build_row({"name": "DK-1"}, "")
		self.assertEqual(row["job_no"], "-")
		self.assertEqual(row["agent"], "-")
		self.assertEqual(row["billing_invoice"], "-")
