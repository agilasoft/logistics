# Copyright (c) 2026, www.agilasoft.com and Contributors
# See license.txt

from unittest.mock import patch

from frappe.tests import IntegrationTestCase

from logistics.mice.print_format.consol_job_profit_html.consol_job_profit_html import (
	_mode_from_load_types,
	build_cargo_totals,
	build_consol_job_profit,
	build_consol_summary,
	build_routing,
	employee_initials,
	format_consol_job_profit_amount,
	format_consol_job_profit_date,
	get_consol_job_profit_context,
)


class TestConsolJobProfitHtml(IntegrationTestCase):
	def test_profit_is_revenue_minus_cost(self):
		report = build_consol_job_profit(
			[{"job_number": "S00186992", "mode": "LCL"}],
			{
				"S00186992": [
					{
						"dimension_item": "FRTINT",
						"revenue_amount": 48476.39,
						"wip_amount": 10,
						"cost_amount": 14279.46,
						"accrual_amount": 5,
						"disbursement_amount": 999,
					}
				]
			},
		)
		row = report["charge_rows"][0]
		self.assertEqual(row["charge_code"], "FRTINT")
		self.assertEqual(row["revenue"], 48476.39)
		self.assertEqual(row["wip"], 10)
		self.assertEqual(row["cost"], 14279.46)
		self.assertEqual(row["accrual"], 5)
		self.assertEqual(row["profit"], 34196.93)
		self.assertEqual(report["jobs"][0]["profit"], 34196.93)
		self.assertEqual(report["totals"]["profit"], 34196.93)
		self.assertNotEqual(report["totals"]["profit"], 34196.93 - 10 - 5)

	def test_zero_charge_code_and_matching_totals(self):
		report = build_consol_job_profit(
			[
				{"job_number": "S00186992", "mode": "LCL"},
				{"job_number": "S00187162", "mode": "UNA"},
			],
			{
				"S00186992": [
					{
						"dimension_item": "DSTCCP",
						"revenue_amount": 0,
						"cost_amount": 17007.50,
						"wip_amount": 0,
						"accrual_amount": 0,
					},
					{
						"dimension_item": "FRTAWB",
						"revenue_amount": 4262.83,
						"cost_amount": 0,
						"wip_amount": 0,
						"accrual_amount": 0,
						"disbursement_amount": 50,
					},
				],
				"S00187162": [
					{
						"dimension_item": "FRTAWB",
						"revenue_amount": 100,
						"cost_amount": 40,
						"wip_amount": 1,
						"accrual_amount": 2,
					}
				],
			},
			extra_charge_codes=["SS", "FRTAWB"],
		)
		by_code = {row["charge_code"]: row for row in report["charge_rows"]}
		self.assertEqual(list(by_code), ["DSTCCP", "FRTAWB", "SS"])
		self.assertEqual(by_code["SS"]["revenue"], 0)
		self.assertEqual(by_code["SS"]["profit"], 0)
		self.assertEqual(by_code["FRTAWB"]["revenue"], 4362.83)
		self.assertEqual(by_code["FRTAWB"]["profit"], 4322.83)
		self.assertEqual(by_code["DSTCCP"]["profit"], -17007.50)

		charge_revenue = sum(row["revenue"] for row in report["charge_rows"])
		job_revenue = sum(job["revenue"] for job in report["jobs"])
		self.assertEqual(charge_revenue, job_revenue)
		self.assertEqual(report["totals"]["revenue"], job_revenue)
		self.assertEqual(report["totals"]["cost"], sum(job["cost"] for job in report["jobs"]))
		self.assertEqual(report["totals"]["wip"], sum(job["wip"] for job in report["jobs"]))
		self.assertEqual(report["totals"]["accrual"], sum(job["accrual"] for job in report["jobs"]))
		self.assertEqual(
			report["totals"]["profit"],
			report["totals"]["revenue"] - report["totals"]["cost"],
		)
		self.assertEqual(report["jobs"][1]["mode"], "UNA")

	def test_blank_mode_prints_as_una(self):
		report = build_consol_job_profit(
			[{"job_number": "JN-1", "mode": ""}],
			{},
		)
		self.assertEqual(report["jobs"][0]["mode"], "UNA")
		self.assertEqual(report["jobs"][0]["profit"], 0)

	def test_mode_from_load_type(self):
		self.assertEqual(_mode_from_load_types(None), "UNA")
		self.assertEqual(_mode_from_load_types(["", None, "  "]), "UNA")
		self.assertEqual(_mode_from_load_types(["", "LCL", "LSE"]), "LCL")

	def test_format_amount(self):
		self.assertEqual(format_consol_job_profit_amount(0), "0.00")
		self.assertEqual(format_consol_job_profit_amount(-17007.5), "-17,007.50")
		self.assertEqual(format_consol_job_profit_amount(301892.41), "301,892.41")

	@patch(
		"logistics.mice.print_format.consol_job_profit_html.consol_job_profit_html._mode_code",
		side_effect=lambda doctype, name, linked_service=None: "LSE" if name == "MJ-2" else "UNA",
	)
	@patch("frappe.get_all")
	def test_load_jobs_skips_rows_without_job_number(self, mock_get_all, _mock_mode):
		from logistics.mice.print_format.consol_job_profit_html.consol_job_profit_html import (
			_load_jobs,
		)

		def _get_all(doctype, *args, **kwargs):
			if doctype == "Docket":
				return [
					{"name": "DK-1", "job_number": "", "company": "Co"},
					{"name": "DK-2", "job_number": "JN-1", "company": "Co"},
					{"name": "DK-3", "job_number": "JN-2", "company": ""},
				]
			if doctype == "MICE Job":
				return [
					{
						"name": "MJ-1",
						"job_number": "JN-1",
						"company": "Co",
						"linked_service": "LS-1",
					},
					{
						"name": "MJ-2",
						"job_number": "JN-9",
						"company": "Co",
						"linked_service": None,
					},
				]
			return []

		mock_get_all.side_effect = _get_all
		jobs = _load_jobs("EP-1")
		self.assertEqual([job["job_number"] for job in jobs], ["JN-1", "JN-9"])
		self.assertEqual(jobs[0]["doctype"], "Docket")
		self.assertEqual(jobs[0]["mode"], "UNA")
		self.assertEqual(jobs[1]["mode"], "LSE")

	def test_context_empty_without_project(self):
		self.assertEqual(get_consol_job_profit_context(None)["jobs"], [])
		self.assertEqual(get_consol_job_profit_context({})["charge_rows"], [])
		self.assertEqual(get_consol_job_profit_context({})["totals"]["profit"], 0)

	@patch(
		"logistics.mice.print_format.consol_job_profit_html.consol_job_profit_html._charge_item_codes",
		return_value={"TXT"},
	)
	@patch(
		"logistics.mice.print_format.consol_job_profit_html.consol_job_profit_html._classified_entries",
		return_value=[
			{
				"dimension_item": "ORGHAD",
				"revenue_amount": 10,
				"cost_amount": 4,
				"wip_amount": 0,
				"accrual_amount": 0,
			}
		],
	)
	@patch(
		"logistics.mice.print_format.consol_job_profit_html.consol_job_profit_html._load_jobs",
		return_value=[{"job_number": "JN-7", "company": "Co", "mode": "LCL"}],
	)
	def test_context_uses_loaded_jobs(self, _jobs, _entries, _codes):
		report = get_consol_job_profit_context({"name": "EP-9"})
		self.assertEqual(report["jobs"][0]["job_number"], "JN-7")
		self.assertEqual(report["jobs"][0]["mode"], "LCL")
		self.assertEqual(report["jobs"][0]["profit"], 6)
		codes = [row["charge_code"] for row in report["charge_rows"]]
		self.assertEqual(codes, ["ORGHAD", "TXT"])
		self.assertEqual(report["totals"]["profit"], 6)
		self.assertEqual(report["summary"]["income"], 10)
		self.assertEqual(report["summary"]["expense"], 4)
		self.assertEqual(report["summary"]["profit"], 6)
		self.assertEqual(report["header"]["consol"], "EP-9")
		self.assertEqual(report["header"]["title"], "Consol Job Profit")
		self.assertEqual(report["header"]["journey"], "")
		self.assertEqual(report["header"]["payment_type"], "")
		self.assertEqual(report["header"]["sending_agent"], "")

	def test_summary_income_expense_and_margins(self):
		summary = build_consol_summary(
			{"revenue": 389695.39, "wip": 0, "cost": 87802.98, "accrual": 0}
		)
		self.assertEqual(summary["income"], 389695.39)
		self.assertEqual(summary["expense"], 87802.98)
		self.assertEqual(summary["rev_cst"], 301892.41)
		self.assertEqual(summary["wip_acr"], 0)
		self.assertEqual(summary["profit"], 301892.41)
		self.assertEqual(summary["profit_cost_pct"], "344%")
		self.assertEqual(summary["profit_rev_pct"], "77%")

		with_recognition = build_consol_summary(
			{"revenue": 100, "wip": 10, "cost": 40, "accrual": 5}
		)
		self.assertEqual(with_recognition["income"], 110)
		self.assertEqual(with_recognition["expense"], 45)
		self.assertEqual(with_recognition["rev_cst"], 60)
		self.assertEqual(with_recognition["wip_acr"], 5)
		self.assertEqual(with_recognition["profit"], 65)
		self.assertEqual(with_recognition["profit_cost_pct"], "163%")
		self.assertEqual(with_recognition["profit_rev_pct"], "65%")

	def test_cargo_totals_sum_dockets(self):
		cargo = build_cargo_totals(
			[
				{
					"total_containers": 1,
					"total_teus": 2,
					"total_weight": "10.5",
					"total_weight_uom": "KG",
					"total_volume": 1.25,
					"total_volume_uom": "CBM",
					"chargeable": 12,
					"chargeable_weight_uom": "KG",
					"total_packages": 3,
				},
				{
					"total_containers": 0,
					"total_teus": 0,
					"total_weight": "1.5",
					"total_weight_uom": "KG",
					"total_volume": 0.5,
					"total_volume_uom": "CBM",
					"chargeable": 2,
					"chargeable_weight_uom": "KG",
					"total_packages": 1,
				},
			]
		)
		self.assertEqual(cargo["containers"], "1")
		self.assertEqual(cargo["teu"], "2")
		self.assertEqual(cargo["weight"], "12 KG")
		self.assertEqual(cargo["volume"], "1.75 CBM")
		self.assertEqual(cargo["chargeable"], "14 KG")
		self.assertEqual(cargo["packages"], "4 Package(s)")
		self.assertEqual(build_cargo_totals([])["packages"], "0 Package(s)")

	def test_routing_ports_and_dates(self):
		routing = build_routing(
			{"show_open_date": "2025-08-29"},
			[
				{"origin_port": "PHPIS", "destination_port": "SGSIN", "shipping_line": "Line A"},
				{"origin_port": "", "destination_port": "PHMNL", "shipping_line": "Line B"},
			],
			[{"planned_start": "2025-01-01", "planned_end": "2025-11-19"}],
		)
		self.assertEqual(routing["load_port"], "PHPIS")
		self.assertEqual(routing["discharge_port"], "PHMNL")
		self.assertEqual(routing["carrier"], "Line A")
		self.assertEqual(routing["etd"], "29-Aug-25")
		self.assertEqual(routing["eta"], "19-Nov-25")

	def test_shipment_row_and_initials(self):
		self.assertEqual(employee_initials("Kim Ong"), "KO")
		self.assertEqual(employee_initials("Ana Gomez Marin"), "AGM")
		self.assertEqual(employee_initials(""), "")
		self.assertEqual(format_consol_job_profit_date("2025-08-29"), "29-Aug-25")
		self.assertEqual(
			format_consol_job_profit_date("2026-06-03 17:34:00", with_time=True),
			"03-Jun-26 17:34",
		)
		report = build_consol_job_profit(
			[
				{
					"job_number": "S00187160",
					"mode": "LSE",
					"house": "DK-1",
					"exhibitor": "Artworks",
					"agent": "AGNT",
					"awb_bl": "123-45678901",
					"opened": "02-Sep-25",
					"closed": "19-Nov-25",
				}
			],
			{},
		)
		ship = report["shipments"][0]
		self.assertEqual(ship["job_number"], "S00187160")
		self.assertEqual(ship["mode"], "LSE")
		self.assertEqual(ship["house"], "DK-1")
		self.assertEqual(ship["exhibitor"], "Artworks")
		self.assertEqual(ship["agent"], "AGNT")
		self.assertEqual(ship["awb_bl"], "123-45678901")
		self.assertEqual(ship["opened"], "02-Sep-25")
		self.assertEqual(ship["closed"], "19-Nov-25")
