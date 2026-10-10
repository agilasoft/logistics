# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Customs sidebar and workspace expose the Control Tower dashboard."""

from __future__ import annotations

import datetime
import json
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
CUSTOMS = ROOT / "logistics/customs"
SIDEBAR_PATH = CUSTOMS / "sidebar/customs/customs.json"
WORKSPACE_PATH = CUSTOMS / "workspace/customs/customs.json"
DASHBOARD_PATH = CUSTOMS / "customs_dashboard/customs_control_tower/customs_control_tower.json"
PATCHES_PATH = ROOT / "logistics/patches.txt"


def _load(path: Path) -> dict:
	return json.loads(path.read_text())


class TestCustomsControlTowerSidebar(unittest.TestCase):
	def test_sidebar_opens_the_customs_dashboard(self):
		items = _load(SIDEBAR_PATH)["items"]
		self.assertEqual(items[0]["label"], "Home")
		tower = items[1]
		self.assertEqual(tower["label"], "Control Tower")
		self.assertEqual(tower["link_to"], "Customs Control Tower")
		self.assertEqual(tower["link_type"], "Dashboard")
		self.assertEqual(tower["icon"], "tower-control")
		self.assertEqual(tower["type"], "Link")
		self.assertEqual([item["idx"] for item in items], list(range(1, len(items) + 1)))

	def test_workspace_shortcut_matches_the_sidebar(self):
		workspace = _load(WORKSPACE_PATH)
		shortcut = workspace["shortcuts"][0]
		self.assertEqual(shortcut["label"], "Control Tower")
		self.assertEqual(shortcut["link_to"], "Customs Control Tower")
		self.assertEqual(shortcut["type"], "Dashboard")
		content = json.loads(workspace["content"])
		names = [
			(block.get("data") or {}).get("shortcut_name")
			for block in content
			if block.get("type") == "shortcut"
		]
		self.assertEqual(names[0], "Control Tower")

	def test_dashboard_cards_and_charts(self):
		dashboard = _load(DASHBOARD_PATH)
		self.assertEqual(dashboard["name"], "Customs Control Tower")
		self.assertEqual(dashboard["module"], "Customs")
		self.assertEqual(
			[row["card"] for row in dashboard["cards"]],
			[
				"Open Job Files (Customs)",
				"Avg Age of Open Jobs (Customs)",
				"Job Files Handled (Customs)",
				"Avg Lead Time per Milestone (Customs)",
				"Returned Billings (Customs)",
			],
		)
		self.assertEqual(
			[row["chart"] for row in dashboard["charts"]],
			["Top Customs Authorities", "Customs Module Snapshot"],
		)
		for folder, metric in (
			("open_job_files_customs", "open_job_files_count"),
			("avg_age_of_open_jobs_customs", "avg_age_open_jobs"),
			("job_files_handled_customs", "jobs_handled_count"),
			("avg_lead_time_per_milestone_customs", "avg_lead_time_per_milestone"),
			("returned_billings_customs", "returned_billings_count"),
		):
			card = _load(CUSTOMS / "number_card" / folder / f"{folder}.json")
			self.assertEqual(card["method"], "logistics.customs.customs_control_tower.number_card_value")
			self.assertEqual(json.loads(card["filters_json"])["metric"], metric)
			self.assertEqual(card["document_type"], "Declaration")
		authorities = _load(CUSTOMS / "dashboard_chart/top_customs_authorities/top_customs_authorities.json")
		snapshot = _load(CUSTOMS / "dashboard_chart/customs_module_snapshot/customs_module_snapshot.json")
		self.assertEqual(authorities["report_name"], "CCT Authority Volumes")
		self.assertEqual(snapshot["report_name"], "CCT Module Snapshot")

	def test_patch_is_registered(self):
		text = PATCHES_PATH.read_text()
		self.assertIn("logistics.patches.v3_0_sync_customs_control_tower", text)
		self.assertTrue((ROOT / "logistics/patches/v3_0_sync_customs_control_tower.py").is_file())


def _install_fake_frappe():
	"""Minimal frappe stand-in so KPI helpers can run without a site."""

	class FrappeDict(dict):
		def __getattr__(self, key):
			try:
				return self[key]
			except KeyError as exc:
				raise AttributeError(key) from exc

		def __setattr__(self, key, value):
			self[key] = value

	class DB:
		def __init__(self):
			self.queries = []
			self.defaults = {}

		def _row(self, mapping, as_dict):
			if as_dict:
				return FrappeDict(mapping)
			return tuple(mapping.values())

		def sql(self, query, values=None, as_dict=False):
			self.queries.append((" ".join(query.split()), values))
			compact = self.queries[-1][0]
			if "age_sum" in compact:
				return [(4, 40)]
			if "sum_sec" in compact:
				return [(172800.0, 2)]
			if "customs_authority AS label" in compact:
				row = {"label": "AU Customs", "value": 5}
				return [self._row(row, as_dict)]
			if "declaration_count" in compact:
				row = {
					"customs_authority": "AU Customs",
					"declaration_count": 5,
					"total_value": 100,
					"open_count": 2,
				}
				return [self._row(row, as_dict)]
			if "FROM `tabDeclaration`" in compact and "COUNT(*)" in compact:
				return [(9,)]
			if "Returned Billing" in compact and "COUNT" in compact:
				return [(2,)]
			if "DISTINCT port" in compact:
				return [("AUSYD",), ("USNYC",)]
			if "GREATEST(DATEDIFF" in compact:
				row = {
					"name": "DEC-0001",
					"job_status": "Draft",
					"declaration_date": "2026-01-01",
					"customs_authority": "AU Customs",
					"customer": "Acme",
					"port_of_loading": "AUSYD",
					"port_of_discharge": "USNYC",
					"declaration_type": "Import",
					"declaration_number": "1",
					"company": "CargoNext",
					"branch": "Sydney",
					"cost_center": "Main",
					"profit_center": "Main",
					"age_days": 10,
				}
				return [self._row(row, as_dict)]
			if "lead_time_days" in compact:
				row = {
					"declaration": "DEC-0001",
					"milestone": "Clearance",
					"status": "Completed",
					"planned_start": None,
					"planned_end": None,
					"actual_start": None,
					"actual_end": None,
					"lead_time_days": 1,
					"customs_authority": "AU Customs",
					"company": "CargoNext",
					"branch": "Sydney",
					"job_status": "Draft",
				}
				return [self._row(row, as_dict)]
			if "FROM `tabReturned Billing`" in compact:
				return []
			return []

		def exists(self, *args, **kwargs):
			return True

		def has_column(self, *args, **kwargs):
			return True

		def get_default(self, key):
			return self.defaults.get(key)

		def set_default(self, key, value):
			self.defaults[key] = value

		def get_all(self, *args, **kwargs):
			return []

	def cint(value):
		try:
			return int(value)
		except (TypeError, ValueError):
			return 0

	def flt(value, precision=None):
		try:
			number = float(value)
		except (TypeError, ValueError):
			number = 0.0
		if precision is None:
			return number
		return round(number, precision)

	def getdate(value):
		if isinstance(value, datetime.date):
			return value
		return datetime.date.fromisoformat(str(value)[:10])

	def whitelist(*args, **kwargs):
		def decorator(fn):
			return fn

		if len(args) == 1 and callable(args[0]) and not kwargs:
			return args[0]
		return decorator

	def parse_json(value):
		if isinstance(value, str):
			return json.loads(value) if value else {}
		return value

	utils = types.ModuleType("frappe.utils")
	utils.cint = cint
	utils.flt = flt
	utils.getdate = getdate
	utils.nowdate = lambda: "2026-10-08"

	defaults = types.ModuleType("frappe.defaults")
	defaults.get_user_default = lambda key=None: ""

	db = DB()
	frappe_mod = types.ModuleType("frappe")
	frappe_mod.__path__ = []
	frappe_mod.__package__ = "frappe"
	utils.__package__ = "frappe.utils"
	defaults.__package__ = "frappe.defaults"
	frappe_mod.db = db
	frappe_mod.utils = utils
	frappe_mod.defaults = defaults
	frappe_mod._dict = FrappeDict
	frappe_mod.whitelist = whitelist
	frappe_mod.parse_json = parse_json
	frappe_mod.as_json = lambda value: json.dumps(value)
	frappe_mod.get_traceback = lambda: ""
	frappe_mod.log_error = lambda *args, **kwargs: (_ for _ in ()).throw(RuntimeError(args[1] if len(args) > 1 else args))
	frappe_mod.get_all = db.get_all
	frappe_mod._ = lambda text: text
	frappe_mod.flags = types.SimpleNamespace()

	sys.modules["frappe"] = frappe_mod
	sys.modules["frappe.utils"] = utils
	sys.modules["frappe.defaults"] = defaults
	return frappe_mod


@unittest.skipIf("frappe" in sys.modules, "site tests cover the live dashboard")
class TestCustomsControlTowerMetrics(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		_install_fake_frappe()
		from logistics.customs.customs_control_tower import (
			get_dashboard_data,
			module_snapshot_rows,
			number_card_value,
		)
		from logistics.customs.report.cct_authority_volumes.cct_authority_volumes import (
			execute as authority_execute,
		)
		from logistics.customs.report.cct_module_snapshot.cct_module_snapshot import (
			execute as snapshot_execute,
		)

		cls.get_dashboard_data = staticmethod(get_dashboard_data)
		cls.module_snapshot_rows = staticmethod(module_snapshot_rows)
		cls.number_card_value = staticmethod(number_card_value)
		cls.authority_execute = staticmethod(authority_execute)
		cls.snapshot_execute = staticmethod(snapshot_execute)
		cls.db = sys.modules["frappe"].db

	def setUp(self):
		self.db.queries.clear()

	def test_cards_read_declarations_and_open_detail_reports(self):
		open_jobs = self.number_card_value({"metric": "open_job_files_count", "company": "CargoNext"})
		self.assertEqual(open_jobs["value"], 4)
		self.assertEqual(open_jobs["route"], ["query-report", "CCT Job Files Detail"])
		self.assertEqual(open_jobs["route_options"]["scope"], "Open")
		self.assertEqual(open_jobs["route_options"]["company"], "CargoNext")

		age = self.number_card_value({"metric": "avg_age_open_jobs", "company": ""})
		self.assertEqual(age["value"], 10.0)
		handled = self.number_card_value({"metric": "jobs_handled_count", "company": ""})
		self.assertEqual(handled["value"], 9)
		self.assertEqual(handled["route_options"]["scope"], "Handled")
		lead = self.number_card_value({"metric": "avg_lead_time_per_milestone", "company": ""})
		self.assertEqual(lead["value"], 1.0)
		self.assertEqual(lead["route"], ["query-report", "CCT Milestone Lead Time"])
		returned = self.number_card_value({"metric": "returned_billings_count", "company": ""})
		self.assertEqual(returned["value"], 2)
		self.assertEqual(returned["route"], ["query-report", "CCT Returned Billings"])
		self.assertEqual(self.number_card_value({"metric": "missing"})["value"], 0)

		joined = "\n".join(query for query, _values in self.db.queries)
		self.assertIn("`tabDeclaration`", joined)
		self.assertIn("declaration_date", joined)
		self.assertIn("`tabDeclaration Milestone`", joined)
		self.assertIn("module = %s", joined)
		self.assertIn("Customs", [value for _query, values in self.db.queries for value in (values or ())])

	def test_dashboard_groups_customs_authorities(self):
		data = self.get_dashboard_data(
			company="CargoNext",
			unloco="AUSYD",
			authority_limit=99,
			from_date="2026-01-01",
			to_date="2026-10-08",
		)
		self.assertEqual(data["authority_limit"], 50)
		self.assertEqual(data["kpis"]["open_job_files_count"], 4)
		self.assertEqual(data["kpis"]["jobs_handled_count"], 9)
		self.assertEqual(data["top_authorities"], [{"label": "AU Customs", "value": 5.0}])
		self.assertEqual(data["by_module"][0]["module"], "Declaration")
		self.assertEqual(data["links"]["authority_volumes"], "CCT Authority Volumes")
		unloco_queries = [values for query, values in self.db.queries if "port_of_loading" in query and values]
		self.assertTrue(any(values and "AUSYD" in values for values in unloco_queries))

	def test_detail_reports_use_declaration_facts(self):
		columns, rows, message, chart, summary = self.snapshot_execute({"company": ""})
		self.assertIsNone(message)
		self.assertEqual([column["fieldname"] for column in columns], ["module", "open", "open_avg_age", "handled"])
		self.assertEqual(rows[0]["module"], "Declaration")
		self.assertEqual(rows[0]["open"], 4)
		self.assertEqual(rows[0]["handled"], 9)
		self.assertEqual(chart["type"], "bar")
		self.assertTrue(summary)

		_columns, authority_rows, _message, authority_chart, _summary = self.authority_execute({"company": ""})
		self.assertEqual(authority_rows[0]["customs_authority"], "AU Customs")
		self.assertEqual(authority_rows[0]["declaration_count"], 5)
		self.assertEqual(authority_chart["title"], "Top Customs Authorities by Declarations")
		authority_sql = [query for query, _values in self.db.queries if "declaration_count" in query]
		self.assertTrue(authority_sql)
		self.assertIn("customs_authority", authority_sql[0])
