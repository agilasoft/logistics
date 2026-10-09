# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Transport workspace and sidebar expose the Control Tower dashboard."""

from __future__ import annotations

import datetime
import json
import sys
import types
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
TRANSPORT = ROOT / "logistics/transport"
SIDEBAR_PATH = TRANSPORT / "sidebar/transport/transport.json"
WORKSPACE_PATH = TRANSPORT / "workspace/transport/transport.json"
DASHBOARD_PATH = TRANSPORT / "transport_dashboard/transport_control_tower/transport_control_tower.json"
PATCHES_PATH = ROOT / "logistics/patches.txt"


def _load(path: Path) -> dict:
	return json.loads(path.read_text())


class TestTransportControlTowerWorkspace(unittest.TestCase):
	def test_sidebar_opens_the_transport_dashboard(self):
		items = _load(SIDEBAR_PATH)["items"]
		self.assertEqual(items[0]["label"], "Home")
		tower = items[1]
		self.assertEqual(tower["label"], "Control Tower")
		self.assertEqual(tower["link_to"], "Transport Control Tower")
		self.assertEqual(tower["link_type"], "Dashboard")
		self.assertEqual(tower["icon"], "tower-control")
		self.assertEqual(items[2]["label"], "Dashboard")
		self.assertEqual([item["idx"] for item in items], list(range(1, len(items) + 1)))

	def test_workspace_shortcut_matches_the_sidebar(self):
		workspace = _load(WORKSPACE_PATH)
		shortcut = workspace["shortcuts"][0]
		self.assertEqual(shortcut["label"], "Control Tower")
		self.assertEqual(shortcut["link_to"], "Transport Control Tower")
		self.assertEqual(shortcut["type"], "Dashboard")
		content = json.loads(workspace["content"])
		names = [
			(block.get("data") or {}).get("shortcut_name")
			for block in content
			if block.get("type") == "shortcut"
		]
		self.assertEqual(names[0], "Control Tower")
		self.assertIn("Sales Quote", names)
		self.assertIn("Transport Job", names)

	def test_dashboard_cards_and_charts(self):
		dashboard = _load(DASHBOARD_PATH)
		self.assertEqual(dashboard["name"], "Transport Control Tower")
		self.assertEqual(dashboard["module"], "Transport")
		self.assertEqual(
			[row["card"] for row in dashboard["cards"]],
			[
				"Open Job Files (Transport)",
				"Avg Age of Open Jobs (Transport)",
				"Job Files Handled (Transport)",
				"Avg Lead Time per Milestone (Transport)",
				"Returned Billings (Transport)",
			],
		)
		self.assertEqual(
			[row["chart"] for row in dashboard["charts"]],
			["Top Vehicle Types", "Transport Module Snapshot"],
		)
		for folder, metric in (
			("open_job_files_transport", "open_job_files_count"),
			("avg_age_of_open_jobs_transport", "avg_age_open_jobs"),
			("job_files_handled_transport", "jobs_handled_count"),
			("avg_lead_time_per_milestone_transport", "avg_lead_time_per_milestone"),
			("returned_billings_transport", "returned_billings_count"),
		):
			card = _load(TRANSPORT / "number_card" / folder / f"{folder}.json")
			self.assertEqual(card["method"], "logistics.transport.transport_control_tower.number_card_value")
			self.assertEqual(json.loads(card["filters_json"])["metric"], metric)
			self.assertEqual(card["document_type"], "Transport Job")

	def test_patch_is_registered(self):
		text = PATCHES_PATH.read_text()
		self.assertIn("logistics.patches.v3_0_sync_transport_control_tower", text)
		self.assertTrue((ROOT / "logistics/patches/v3_0_sync_transport_control_tower.py").is_file())


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
			if "vehicle_type AS label" in compact:
				return [self._row({"label": "Van", "value": 5}, as_dict)]
			if "job_count" in compact:
				return [self._row({
					"vehicle_type": "Van",
					"job_count": 5,
					"total_weight": 100,
					"open_count": 2,
				}, as_dict)]
			if "FROM `tabTransport Job`" in compact and "COUNT(*)" in compact:
				return [(9,)]
			if "Returned Billing" in compact and "COUNT" in compact:
				return [(2,)]
			if "DISTINCT vehicle_type" in compact:
				return [("Van",)]
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
	frappe_mod.as_json = lambda value: json.dumps(value)
	frappe_mod.get_traceback = lambda: ""
	frappe_mod.log_error = lambda *args, **kwargs: (_ for _ in ()).throw(
		RuntimeError(args[1] if len(args) > 1 else args)
	)
	frappe_mod.get_all = db.get_all
	frappe_mod._ = lambda text: text
	frappe_mod.flags = types.SimpleNamespace()
	sys.modules["frappe"] = frappe_mod
	sys.modules["frappe.utils"] = utils
	sys.modules["frappe.defaults"] = defaults
	return frappe_mod


@unittest.skipIf("frappe" in sys.modules, "site tests cover the live dashboard")
class TestTransportControlTowerMetrics(unittest.TestCase):
	@classmethod
	def setUpClass(cls):
		_install_fake_frappe()
		from logistics.transport.report.tct_module_snapshot.tct_module_snapshot import execute as snapshot_execute
		from logistics.transport.report.tct_vehicle_type_volumes.tct_vehicle_type_volumes import (
			execute as vehicle_execute,
		)
		from logistics.transport.transport_control_tower import get_dashboard_data, number_card_value

		cls.get_dashboard_data = staticmethod(get_dashboard_data)
		cls.number_card_value = staticmethod(number_card_value)
		cls.snapshot_execute = staticmethod(snapshot_execute)
		cls.vehicle_execute = staticmethod(vehicle_execute)
		cls.db = sys.modules["frappe"].db

	def setUp(self):
		self.db.queries.clear()

	def test_cards_read_transport_jobs(self):
		open_jobs = self.number_card_value({"metric": "open_job_files_count", "company": "CargoNext"})
		self.assertEqual(open_jobs["value"], 4)
		self.assertEqual(open_jobs["route"], ["query-report", "TCT Job Files Detail"])
		self.assertEqual(open_jobs["route_options"]["scope"], "Open")
		self.assertEqual(open_jobs["route_options"]["company"], "CargoNext")
		self.assertEqual(self.number_card_value({"metric": "avg_age_open_jobs", "company": ""})["value"], 10.0)
		handled = self.number_card_value({"metric": "jobs_handled_count", "company": ""})
		self.assertEqual(handled["value"], 9)
		self.assertEqual(handled["route_options"]["scope"], "Handled")
		lead = self.number_card_value({"metric": "avg_lead_time_per_milestone", "company": ""})
		self.assertEqual(lead["value"], 1.0)
		self.assertEqual(lead["route"], ["query-report", "TCT Milestone Lead Time"])
		returned = self.number_card_value({"metric": "returned_billings_count", "company": ""})
		self.assertEqual(returned["value"], 2)
		self.assertEqual(returned["route"], ["query-report", "TCT Returned Billings"])
		joined = "\n".join(query for query, _values in self.db.queries)
		self.assertIn("`tabTransport Job`", joined)
		self.assertIn("booking_date", joined)
		self.assertIn("status NOT IN", joined)
		self.assertIn("`tabTransport Job Milestone`", joined)
		self.assertIn("Transport", [value for _query, values in self.db.queries for value in (values or ())])

	def test_dashboard_groups_vehicle_types(self):
		data = self.get_dashboard_data(
			company="CargoNext",
			vehicle_type="Van",
			vehicle_type_limit=99,
			from_date="2026-01-01",
			to_date="2026-10-09",
		)
		self.assertEqual(data["vehicle_type_limit"], 50)
		self.assertEqual(data["kpis"]["open_job_files_count"], 4)
		self.assertEqual(data["top_vehicle_types"], [{"label": "Van", "value": 5.0}])
		self.assertEqual(data["by_module"][0]["module"], "Transport Job")
		self.assertEqual(data["links"]["vehicle_type_volumes"], "TCT Vehicle Type Volumes")
		self.assertTrue(any("vehicle_type = %s" in query and values and "Van" in values for query, values in self.db.queries))

	def test_detail_reports_use_transport_jobs(self):
		_columns, rows, message, chart, _summary = self.snapshot_execute({"company": ""})
		self.assertIsNone(message)
		self.assertEqual(rows[0]["module"], "Transport Job")
		self.assertEqual(rows[0]["open"], 4)
		self.assertEqual(chart["type"], "bar")
		_columns, vehicle_rows, _message, vehicle_chart, _summary = self.vehicle_execute({"company": ""})
		self.assertEqual(vehicle_rows[0]["vehicle_type"], "Van")
		self.assertEqual(vehicle_rows[0]["job_count"], 5)
		self.assertEqual(vehicle_chart["title"], "Top Vehicle Types by Jobs")
