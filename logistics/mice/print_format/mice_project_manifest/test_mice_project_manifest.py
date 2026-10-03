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

	@patch(
		"logistics.mice.print_format.mice_project_manifest.mice_project_manifest._docket_description",
		return_value="",
	)
	@patch("frappe.db.get_value", return_value="Pacific Agent")
	@patch("frappe.get_all")
	def test_air_shipment_fills_freight_columns(self, mock_get_all, _mock_value, _mock_description):
		def _get_all_side_effect(doctype, *args, **kwargs):
			if doctype == "Linked Service":
				return [{"name": "LS-1", "freight_agent": "FA-1", "freight_agent_sea": ""}]
			if doctype == "Air Shipment":
				return [
					{
						"name": "AS-1",
						"house_awb_no": "123-456",
						"house_awb": "",
						"eta": "2026-09-30",
					}
				]
			if doctype == "Air Shipment Routing Leg":
				return [{"flight_no": "", "vessel": "", "voyage_no": ""}, {"flight_no": "PR 102"}]
			if doctype == "Declaration":
				return [
					{
						"actual_clearance_date": None,
						"expected_clearance_date": None,
						"eta": "2026-09-29",
						"transport_document_number": "DECL-AWB",
						"vessel_flight_number": "XX1",
					},
					{
						"actual_clearance_date": "2026-10-02",
						"expected_clearance_date": "2026-10-01",
						"transport_document_number": "",
						"vessel_flight_number": "",
					},
				]
			return []

		mock_get_all.side_effect = _get_all_side_effect
		row = _build_row({"name": "DK-AIR", "job_number": "JN-AIR"}, "Show Org")
		self.assertEqual(row["agent"], "Pacific Agent")
		self.assertEqual(row["eta_mnl"], "30-SEP-2026")
		self.assertEqual(row["clearance_date"], "02-OCT-2026")
		self.assertEqual(row["awb_bl"], "123-456")
		self.assertEqual(row["vsl_flight"], "PR 102")

	@patch(
		"logistics.mice.print_format.mice_project_manifest.mice_project_manifest._docket_description",
		return_value="",
	)
	@patch("frappe.db.get_value", return_value="Sea Agent")
	@patch("frappe.get_all")
	def test_sea_shipment_fills_house_bl_and_vessel(self, mock_get_all, _mock_value, _mock_description):
		def _get_all_side_effect(doctype, *args, **kwargs):
			if doctype == "Linked Service":
				return [{"name": "LS-SEA", "freight_agent": "", "freight_agent_sea": "FA-SEA"}]
			if doctype == "Air Shipment":
				return []
			if doctype == "Sea Shipment":
				return [
					{
						"name": "SS-1",
						"house_bl": "HBL-9",
						"eta": "2026-09-15",
						"master_bill": "MB-1",
					}
				]
			if doctype == "Sea Shipment Routing Leg":
				return [{"vessel": "EVER GIVEN", "voyage_no": "012E", "flight_no": ""}]
			return []

		mock_get_all.side_effect = _get_all_side_effect
		row = _build_row({"name": "DK-SEA", "job_number": "JN-SEA"}, "")
		self.assertEqual(row["agent"], "Sea Agent")
		self.assertEqual(row["awb_bl"], "HBL-9")
		self.assertEqual(row["vsl_flight"], "EVER GIVEN / 012E")
		self.assertEqual(row["eta_mnl"], "15-SEP-2026")
		self.assertEqual(row["clearance_date"], "-")

	@patch(
		"logistics.mice.print_format.mice_project_manifest.mice_project_manifest._docket_description",
		return_value="",
	)
	@patch("frappe.db.exists", return_value=True)
	@patch("frappe.db.get_value")
	@patch("frappe.get_all")
	def test_declaration_and_master_bill_fill_gaps(self, mock_get_all, mock_get_value, _mock_exists, _mock_description):
		def _get_all_side_effect(doctype, *args, **kwargs):
			filters = kwargs.get("filters") or {}
			if doctype == "Linked Service":
				return [{"name": "LS-GAP", "freight_agent": "FA-GAP", "freight_agent_sea": ""}]
			if doctype == "Air Shipment":
				return []
			if doctype == "Sea Shipment":
				return [
					{
						"name": "SS-GAP",
						"house_bl": "",
						"eta": None,
						"master_bill": "MB-GAP",
					}
				]
			if doctype == "Sea Shipment Routing Leg":
				return [{"vessel": "", "voyage_no": "", "flight_no": ""}]
			if doctype == "Declaration":
				if filters.get("linked_service"):
					return []
				if filters.get("job_number") == "JN-GAP":
					return [
						{
							"eta": "2026-12-01",
							"actual_clearance_date": None,
							"expected_clearance_date": "2026-12-03",
							"transport_document_number": "BL-DECL",
							"vessel_flight_number": "MV PACIFIC",
						}
					]
			return []

		def _get_value(doctype, name, fieldname=None, *args, **kwargs):
			if doctype == "Freight Agent":
				return None
			if doctype == "Master Bill":
				return {"vessel": "MAERSK", "voyage_no": "88"}
			return None

		mock_get_all.side_effect = _get_all_side_effect
		mock_get_value.side_effect = _get_value
		row = _build_row({"name": "DK-GAP", "job_number": "JN-GAP"}, "")
		self.assertEqual(row["agent"], "FA-GAP")
		self.assertEqual(row["awb_bl"], "BL-DECL")
		self.assertEqual(row["eta_mnl"], "01-DEC-2026")
		self.assertEqual(row["clearance_date"], "03-DEC-2026")
		self.assertEqual(row["vsl_flight"], "MAERSK / 88")

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
