# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Control Towers for the remaining logistics modules."""

from __future__ import annotations

import datetime
import importlib.util
import json
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PATCHES_PATH = ROOT / "logistics/patches.txt"

MODULES = (
	{
		"key": "warehousing",
		"folder": "warehousing",
		"title": "Warehousing Control Tower",
		"module": "Warehousing",
		"workspace": "warehousing/workspace/warehousing/warehousing.json",
		"sidebar": "warehousing/sidebar/warehousing/warehousing.json",
		"dashboard": "warehousing/warehousing_dashboard/warehousing_control_tower/warehousing_control_tower.json",
		"doctype": "Warehouse Job",
		"charts": ["Top Warehouse Job Types", "Warehousing Module Snapshot"],
		"card_slug": "warehousing",
		"sql": ["`tabWarehouse Job`", "job_open_date", "`job_status`"],
		"open": 4,
		"handled": 9,
		"lead": 0.0,
		"job_report": "WHCT Job Files Detail",
		"lead_report": "WHCT Milestone Lead Time",
		"returned_report": "WHCT Returned Billings",
	},
	{
		"key": "special_projects",
		"folder": "special_projects",
		"title": "Special Projects Control Tower",
		"module": "Special Projects",
		"workspace": "special_projects/workspace/special_projects/special_projects.json",
		"sidebar": "special_projects/sidebar/special_projects/special_projects.json",
		"dashboard": "special_projects/special_projects_dashboard/special_projects_control_tower/special_projects_control_tower.json",
		"doctype": "Special Project",
		"charts": ["Top Project Types", "Special Projects Module Snapshot"],
		"card_slug": "special_projects",
		"sql": ["`tabSpecial Project`", "start_date", "project_type"],
		"open": 4,
		"handled": 9,
		"lead": 1.0,
		"job_report": "SPCT Job Files Detail",
		"lead_report": "SPCT Milestone Lead Time",
		"returned_report": "SPCT Returned Billings",
	},
	{
		"key": "mice",
		"folder": "mice",
		"title": "MICE Control Tower",
		"module": "MICE",
		"workspace": "mice/workspace/mice/mice.json",
		"sidebar": "mice/sidebar/mice/mice.json",
		"dashboard": "mice/mice_dashboard/mice_control_tower/mice_control_tower.json",
		"doctype": "MICE Project",
		"charts": ["Top MICE Types", "MICE Module Snapshot"],
		"card_slug": "mice",
		"sql": ["`tabMICE Project`", "start_date", "exhibit_type"],
		"open": 4,
		"handled": 9,
		"lead": 1.0,
		"job_report": "MICT Job Files Detail",
		"lead_report": "MICT Milestone Lead Time",
		"returned_report": "MICT Returned Billings",
	},
	{
		"key": "high_value",
		"folder": "high_value",
		"title": "High Value Control Tower",
		"module": "High Value",
		"workspace": "high_value/workspace/high_value/high_value.json",
		"sidebar": "high_value/sidebar/high_value/high_value.json",
		"dashboard": "high_value/high_value_dashboard/high_value_control_tower/high_value_control_tower.json",
		"doctype": "Air Shipment",
		"charts": ["High Value by Modality", "High Value Module Snapshot"],
		"card_slug": "high_value",
		"sql": ["`tabAir Shipment`", "is_high_value", "`tabSea Shipment`", "`tabWarehouse Job`"],
		"open": 20,
		"handled": 45,
		"lead": 1.0,
		"job_report": "HVCT Job Files Detail",
		"lead_report": "HVCT Milestone Lead Time",
		"returned_report": "HVCT Returned Billings",
	},
	{
		"key": "time_sensitive",
		"folder": "time_sensitive",
		"title": "Time Sensitive Control Tower",
		"module": "Time Sensitive",
		"workspace": "time_sensitive/workspace/time_sensitive/time_sensitive.json",
		"sidebar": "time_sensitive/sidebar/time_sensitive/time_sensitive.json",
		"dashboard": "time_sensitive/time_sensitive_dashboard/time_sensitive_control_tower/time_sensitive_control_tower.json",
		"doctype": "Time Sensitive Case",
		"charts": ["Top Case Types", "Time Sensitive Module Snapshot"],
		"card_slug": "time_sensitive",
		"sql": ["DATE(`creation`)", "case_type", "`tabTime Sensitive Case`"],
		"open": 4,
		"handled": 9,
		"lead": 1.0,
		"job_report": "TSCT Job Files Detail",
		"lead_report": "TSCT Milestone Lead Time",
		"returned_report": "TSCT Returned Billings",
	},
	{
		"key": "sustainability",
		"folder": "sustainability",
		"title": "Sustainability Control Tower",
		"module": "Sustainability",
		"workspace": "sustainability/workspace/sustainability/sustainability.json",
		"sidebar": "sustainability/sidebar/sustainability/sustainability.json",
		"dashboard": "sustainability/sustainability_dashboard/sustainability_control_tower/sustainability_control_tower.json",
		"doctype": "Carbon Footprint",
		"charts": ["Carbon Footprint by Module", "Sustainability Module Snapshot"],
		"card_slug": "sustainability",
		"sql": ["`tabCarbon Footprint`", "verification_status", "verification_date"],
		"open": 4,
		"handled": 9,
		"lead": 1.0,
		"job_report": "SUCT Job Files Detail",
		"lead_report": "SUCT Milestone Lead Time",
		"returned_report": "SUCT Returned Billings",
	},
	{
		"key": "pricing_center",
		"folder": "pricing_center",
		"title": "Pricing Center Control Tower",
		"module": "Pricing Center",
		"workspace": "pricing_center/workspace/pricing/pricing.json",
		"sidebar": "pricing_center/sidebar/pricing_center/pricing_center.json",
		"dashboard": "pricing_center/pricing_center_dashboard/pricing_center_control_tower/pricing_center_control_tower.json",
		"doctype": "Sales Quote",
		"charts": ["Quotes by Service", "Pricing Center Module Snapshot"],
		"card_slug": "pricing_center",
		"sql": ["`tabSales Quote`", "main_service", "`status`"],
		"open": 4,
		"handled": 9,
		"lead": 0.0,
		"job_report": "PCCT Job Files Detail",
		"lead_report": "PCCT Milestone Lead Time",
		"returned_report": "PCCT Returned Billings",
	},
)


def _load(path):
	return json.loads(Path(path).read_text())


class TestModuleControlTowerAssets(unittest.TestCase):
	def test_sidebar_and_workspace_link_each_dashboard(self):
		for spec in MODULES:
			with self.subTest(spec["key"]):
				items = _load(ROOT / "logistics" / spec["sidebar"])["items"]
				self.assertEqual(items[0]["label"], "Home")
				tower = items[1]
				self.assertEqual(tower["label"], "Control Tower")
				self.assertEqual(tower["link_to"], spec["title"])
				self.assertEqual(tower["link_type"], "Dashboard")
				self.assertEqual(tower["icon"], "tower-control")
				self.assertEqual([item["idx"] for item in items], list(range(1, len(items) + 1)))

				workspace = _load(ROOT / "logistics" / spec["workspace"])
				shortcut = workspace["shortcuts"][0]
				self.assertEqual(shortcut["label"], "Control Tower")
				self.assertEqual(shortcut["link_to"], spec["title"])
				self.assertEqual(shortcut["type"], "Dashboard")
				content = json.loads(workspace["content"])
				header_at = next(index for index, block in enumerate(content) if block.get("type") == "header")
				self.assertEqual(content[header_at + 1]["type"], "shortcut")
				self.assertEqual(content[header_at + 1]["data"]["shortcut_name"], "Control Tower")

	def test_dashboards_cards_and_pages(self):
		for spec in MODULES:
			with self.subTest(spec["key"]):
				dashboard = _load(ROOT / "logistics" / spec["dashboard"])
				self.assertEqual(dashboard["name"], spec["title"])
				self.assertEqual(dashboard["module"], spec["module"])
				self.assertEqual(dashboard["is_standard"], 1)
				self.assertEqual(
					[row["card"] for row in dashboard["cards"]],
					[
						"Open Job Files ({0})".format(spec["module"]),
						"Avg Age of Open Jobs ({0})".format(spec["module"]),
						"Job Files Handled ({0})".format(spec["module"]),
						"Avg Lead Time per Milestone ({0})".format(spec["module"]),
						"Returned Billings ({0})".format(spec["module"]),
					],
				)
				self.assertEqual([row["chart"] for row in dashboard["charts"]], spec["charts"])
				method = "logistics.{0}.{0}_control_tower.number_card_value".format(spec["folder"])
				for slug, metric in (
					("open_job_files", "open_job_files_count"),
					("avg_age_of_open_jobs", "avg_age_open_jobs"),
					("job_files_handled", "jobs_handled_count"),
					("avg_lead_time_per_milestone", "avg_lead_time_per_milestone"),
					("returned_billings", "returned_billings_count"),
				):
					folder = "{0}_{1}".format(slug, spec["card_slug"])
					card = _load(ROOT / "logistics" / spec["folder"] / "number_card" / folder / "{0}.json".format(folder))
					self.assertEqual(card["method"], method)
					self.assertEqual(json.loads(card["filters_json"])["metric"], metric)
					self.assertEqual(card["document_type"], spec["doctype"])
					self.assertEqual(card["type"], "Custom")
				route = spec["title"].lower().replace(" ", "-")
				page = scrub_page(route)
				script = (ROOT / "logistics" / spec["folder"] / "page" / page / "{0}.js".format(page)).read_text()
				self.assertIn('frappe.set_route("dashboard-view", "{0}")'.format(spec["title"]), script)

	def test_patch_is_registered(self):
		text = PATCHES_PATH.read_text()
		self.assertIn("logistics.patches.v3_0_sync_module_control_towers", text)
		patch = (ROOT / "logistics/patches/v3_0_sync_module_control_towers.py").read_text()
		self.assertIn("from logistics.control_tower.module_tower import TOWERS", patch)
		self.assertIn('frappe.reload_doc(tower["folder"], "report", name, force=True)', patch)
		engine = (ROOT / "logistics/control_tower/module_tower.py").read_text()
		for spec in MODULES:
			self.assertIn(spec["title"], engine)
			self.assertIn('"{0}"'.format(spec["folder"]), engine)


def scrub_page(route):
	return route.replace("-", "_")


def _install_fake_frappe():
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

		def sql(self, query, values=None, as_dict=False):
			compact = " ".join(query.split())
			self.queries.append((compact, tuple(values) if values is not None else ()))
			if "age_sum" in compact:
				return [(4, 40)]
			if "sum_sec" in compact:
				if as_dict:
					return [FrappeDict({"record": "JOB-1", "milestone": "Gate", "lead_time_days": 1.0})]
				return [(172800.0, 2)]
			if "sum_days" in compact:
				return [(2, 2)]
			if "lead_time_days" in compact and as_dict:
				return [FrappeDict({"record": "CF-1", "lead_time_days": 2})]
			if "job_count" in compact:
				return [FrappeDict({"label": "Putaway", "job_count": 5, "open_count": 2})]
			if " AS label" in compact and " AS value" in compact:
				return [FrappeDict({"label": "Putaway", "value": 5})]
			if "Returned Billing" in compact and "COUNT" in compact:
				return [(2,)]
			if "COUNT(*)" in compact:
				return [(9,)]
			return []

		def exists(self, *args, **kwargs):
			return True

		def has_column(self, *args, **kwargs):
			return True

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

	utils = types.ModuleType("frappe.utils")
	utils.cint = cint
	utils.flt = flt
	utils.getdate = getdate
	utils.nowdate = lambda: "2026-10-09"
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
	frappe_mod.parse_json = lambda value: json.loads(value) if isinstance(value, str) and value else value
	frappe_mod.get_traceback = lambda: ""

	def log_error(*args, **kwargs):
		raise RuntimeError(args[1] if len(args) > 1 else args)

	frappe_mod.log_error = log_error
	frappe_mod._ = lambda text: text
	sys.modules["frappe"] = frappe_mod
	sys.modules["frappe.utils"] = utils
	sys.modules["frappe.defaults"] = defaults
	return frappe_mod


@unittest.skipIf("frappe" in sys.modules, "site tests cover the live dashboard")
class TestModuleControlTowerMetrics(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		_install_fake_frappe()
		from logistics.control_tower.module_tower import (
			get_dashboard_data,
			job_files_execute,
			lead_time_execute,
			number_card_value,
			volumes_execute,
		)

		cls.get_dashboard_data = staticmethod(get_dashboard_data)
		cls.number_card_value = staticmethod(number_card_value)
		cls.job_files_execute = staticmethod(job_files_execute)
		cls.lead_time_execute = staticmethod(lead_time_execute)
		cls.volumes_execute = staticmethod(volumes_execute)
		cls.db = sys.modules["frappe"].db

	def setUp(self):
		self.db.queries.clear()

	def test_cards_match_each_module(self):
		for spec in MODULES:
			with self.subTest(spec["key"]):
				self.db.queries.clear()
				data = self.get_dashboard_data(spec["key"], {"company": "CargoNext"})
				kpis = data["kpis"]
				self.assertEqual(kpis["open_job_files_count"], spec["open"])
				self.assertEqual(kpis["avg_age_open_jobs"], 10.0)
				self.assertEqual(kpis["jobs_handled_count"], spec["handled"])
				self.assertEqual(kpis["avg_lead_time_per_milestone"], spec["lead"])
				self.assertEqual(kpis["returned_billings_count"], 2)
				open_card = self.number_card_value(spec["key"], {
					"metric": "open_job_files_count",
					"company": "CargoNext",
				})
				self.assertEqual(open_card["value"], spec["open"])
				self.assertEqual(open_card["route"], ["query-report", spec["job_report"]])
				self.assertEqual(open_card["route_options"]["scope"], "Open")
				self.assertEqual(open_card["route_options"]["company"], "CargoNext")
				returned = self.number_card_value(spec["key"], {"metric": "returned_billings_count", "company": ""})
				self.assertEqual(returned["route"], ["query-report", spec["returned_report"]])
				joined = "\n".join(query for query, _values in self.db.queries)
				for snippet in spec["sql"]:
					self.assertIn(snippet, joined)

	def test_warehousing_volume_placeholders_follow_the_select(self):
		_columns, rows, _message, chart, _summary = self.volumes_execute("warehousing", {"company": ""})
		self.assertEqual(rows[0]["label"], "Putaway")
		self.assertEqual(chart["data"]["labels"], ["Putaway"])
		query, values = next((query, values) for query, values in self.db.queries if "job_count" in query)
		self.assertLess(query.index("NOT IN"), query.index("BETWEEN"))
		self.assertEqual(values[:3], ("Completed", "Closed", "Cancelled"))
		self.assertEqual(values[-3:], ("2026-01-01", "2026-10-09", 10))

	def test_high_value_volumes_are_modalities(self):
		_columns, rows, message, _chart, _summary = self.volumes_execute("high_value", {"company": ""})
		self.assertIsNone(message)
		self.assertEqual([row["label"] for row in rows], ["Air", "Sea", "Transport", "Customs", "Warehouse"])
		self.assertTrue(all(row["job_count"] == 9 for row in rows))

	def test_modules_without_milestones_explain_the_empty_lead_time(self):
		_columns, rows, message, _chart, _summary = self.lead_time_execute("warehousing", {"company": ""})
		self.assertEqual(rows, [])
		self.assertEqual(message, "This module has no milestone table.")
		_columns, rows, message, _chart, _summary = self.lead_time_execute("pricing_center", {"company": ""})
		self.assertEqual(message, "This module has no milestone table.")
		_columns, rows, message, _chart, _summary = self.lead_time_execute("sustainability", {"company": ""})
		self.assertIsNone(message)
		self.assertEqual(rows[0]["milestone"], "Verification")

	def test_wrappers_delegate_to_the_engine(self):
		for spec in MODULES:
			with self.subTest(spec["key"]):
				path = ROOT / "logistics" / spec["folder"] / "{0}_control_tower.py".format(spec["folder"])
				module_name = "module_tower_wrapper_{0}".format(spec["key"])
				loaded = importlib.util.spec_from_file_location(module_name, path)
				module = importlib.util.module_from_spec(loaded)
				loaded.loader.exec_module(module)
				result = module.number_card_value({"metric": "jobs_handled_count", "company": ""})
				self.assertEqual(result["value"], spec["handled"])
				self.assertEqual(result["route_options"]["scope"], "Handled")
				self.assertEqual(result["route"][1], spec["job_report"])
