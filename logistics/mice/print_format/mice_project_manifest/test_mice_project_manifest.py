# Copyright (c) 2026, www.agilasoft.com and Contributors
# See license.txt

from unittest.mock import patch

from frappe.tests import IntegrationTestCase

from logistics.mice.print_format.mice_project_manifest.mice_project_manifest import (
	_build_row,
	_format_qty,
	_format_volume,
	_format_weight,
	format_mice_manifest_show_dates,
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
				"sales_invoice": "SINV-001",
				"required_by": "2026-01-10",
			}
		]

		def _get_all_side_effect(doctype, *args, **kwargs):
			if doctype == "Docket":
				return docket_rows
			if doctype == "Docket Package":
				return [{"commodity": "AHTN031"}]
			if doctype == "Commodity":
				return [
					{
						"name": "AHTN031",
						"description": "Plastics and articles thereof",
					}
				]
			return []

		mock_get_all.side_effect = _get_all_side_effect
		rows = get_mice_project_manifest_rows({"name": "EP-00001"})
		self.assertEqual(len(rows), 1)
		row = rows[0]
		self.assertEqual(row["job_no"], "JN-001")
		self.assertEqual(row["exhibitor"], "Acme Exhibitor")
		self.assertEqual(row["org"], "Show Org Inc.")
		self.assertEqual(row["description"], "Plastics and articles thereof")
		self.assertEqual(row["qty_pkgs"], "3")
		self.assertIn("120", row["g_weight_kg"])
		self.assertIn("2.5", row["volume_cbm"])
		self.assertEqual(row["ingress_schedule"], "")
		self.assertEqual(row["contact"], "")
		self.assertEqual(row["billing_invoice"], "SINV-001")
		self.assertNotIn("amount", row)
		for key in (
			"agent",
			"eta_mnl",
			"clearance_date",
			"awb_bl",
			"vsl_flight",
		):
			self.assertEqual(row[key], "-")

	@patch(
		"logistics.mice.print_format.mice_project_manifest.mice_project_manifest._organizer_name",
		return_value="",
	)
	@patch("frappe.get_all")
	def test_description_uses_unique_commodity_descriptions(self, mock_get_all, _mock_org):
		def _get_all_side_effect(doctype, *args, **kwargs):
			if doctype == "Docket":
				return [{"name": "DK-TEST-2", "description": "Ignored docket text"}]
			if doctype == "Docket Package":
				return [
					{"commodity": "AHTN031"},
					{"commodity": ""},
					{"commodity": "GEN"},
					{"commodity": "AHTN031"},
					{"commodity": "BLANK"},
				]
			if doctype == "Commodity":
				return [
					{"name": "AHTN031", "description": "<p>Plastics and articles thereof</p>"},
					{"name": "GEN", "description": "General cargo"},
					{"name": "BLANK", "description": "   "},
				]
			return []

		mock_get_all.side_effect = _get_all_side_effect
		rows = get_mice_project_manifest_rows({"name": "EP-00002"})
		self.assertEqual(len(rows), 1)
		self.assertEqual(
			rows[0]["description"],
			"Plastics and articles thereof, General cargo",
		)
		self.assertEqual(rows[0]["ingress_schedule"], "")
		self.assertEqual(rows[0]["contact"], "")

	@patch(
		"logistics.mice.print_format.mice_project_manifest.mice_project_manifest._organizer_name",
		return_value="",
	)
	@patch("frappe.get_all")
	def test_description_dash_without_commodity(self, mock_get_all, _mock_org):
		def _get_all_side_effect(doctype, *args, **kwargs):
			if doctype == "Docket":
				return [{"name": "DK-TEST-3", "description": "Booth materials"}]
			if doctype == "Docket Package":
				return [{"commodity": ""}]
			return []

		mock_get_all.side_effect = _get_all_side_effect
		rows = get_mice_project_manifest_rows({"name": "EP-00003"})
		self.assertEqual(rows[0]["description"], "-")

	def test_format_show_dates(self):
		self.assertEqual(format_mice_manifest_show_dates(None, None), "")
		self.assertEqual(
			format_mice_manifest_show_dates("2025-08-25", "2025-08-29"),
			"25-29 AUGUST 2025",
		)
		self.assertEqual(
			format_mice_manifest_show_dates("2025-08-25", "2025-09-02"),
			"25 AUGUST - 2 SEPTEMBER 2025",
		)
		self.assertEqual(
			format_mice_manifest_show_dates("2025-12-25", "2026-01-02"),
			"25 DECEMBER 2025 - 2 JANUARY 2026",
		)
		self.assertEqual(
			format_mice_manifest_show_dates("2025-08-25", None),
			"25 AUGUST 2025",
		)
		self.assertEqual(
			format_mice_manifest_show_dates(None, "2025-08-29"),
			"29 AUGUST 2025",
		)
		self.assertEqual(
			format_mice_manifest_show_dates("2025-08-25", "2025-08-25"),
			"25 AUGUST 2025",
		)

	def test_format_qty_and_weight(self):
		self.assertEqual(_format_qty(None), "-")
		self.assertEqual(_format_qty(0), "0")
		self.assertEqual(_format_qty(4), "4")
		dk = {"total_weight": 50, "total_weight_uom": "KG"}
		self.assertEqual(_format_weight(dk), "50")
		self.assertEqual(_format_volume({"total_volume": 2.652, "total_volume_uom": "Cubic Meter"}), "2.652")
		self.assertEqual(_format_volume({}), "-")

	def test_build_row_defaults_dashes(self):
		with patch(
			"logistics.mice.print_format.mice_project_manifest.mice_project_manifest._docket_description",
			return_value="",
		):
			row = _build_row({"name": "DK-1"}, "")
		self.assertEqual(row["job_no"], "-")
		self.assertEqual(row["exhibitor"], "-")
		self.assertEqual(row["agent"], "-")
		self.assertEqual(row["eta_mnl"], "-")
		self.assertEqual(row["clearance_date"], "-")
		self.assertEqual(row["awb_bl"], "-")
		self.assertEqual(row["vsl_flight"], "-")
		self.assertEqual(row["contact"], "")
		self.assertEqual(row["billing_invoice"], "-")
		self.assertNotIn("amount", row)
		self.assertEqual(row["ingress_schedule"], "")
		self.assertEqual(row["description"], "-")
