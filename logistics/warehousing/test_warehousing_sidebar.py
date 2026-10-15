# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Warehousing sidebar report groups follow the workspace cards."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT / "logistics/warehousing/workspace/warehousing/warehousing.json"
SIDEBAR = ROOT / "logistics/warehousing/sidebar/warehousing/warehousing.json"
PATCHES = ROOT / "logistics/patches.txt"
REPORTS = ROOT / "logistics/warehousing/report"

# The desk rail fits about this many characters before the label ellipsizes.
SECTION_LABEL_LIMIT = 20
CHILD_LABEL_LIMIT = 22

# Workspace card -> sidebar section. Short names stay inside the rail.
REPORT_SECTIONS = {
	"Inventory health & rotation": "Inventory & Rotation",
	"Productivity & slot capacity": "Productivity & Slots",
	"Energy, waste & site metrics": "Energy & Waste",
	"Trade & multimodal flow": "Trade Flow",
	"Commercial & route economics": "Commercial",
	"Sustainability goals & trends": "Sustainability",
}

# Workspace report name -> sidebar label.
SIDEBAR_LABELS = {
	"Warehouse Stock Balance": "Stock Balance",
	"Warehouse Stock Ledger": "Stock Ledger",
	"Batch Expiry Risk": "Batch Expiry Risk",
	"ABC Report": "ABC Report",
	"Labor Productivity Report": "Labor Productivity",
	"Machine Productivity Report": "Machine Productivity",
	"Storage Location Usage": "Location Usage",
	"Handling Unit Capacity": "Unit Capacity",
	"Capacity Forecasting Report": "Capacity Forecast",
	"Energy Efficiency Report": "Energy Efficiency",
	"Waste Management Report": "Waste Management",
	"Inbound Weekly Volume And Value Trend": "Inbound Weekly",
	"Inbound Monthly Volume And Value Trend": "Inbound Monthly",
	"Inbound Priority Pipeline Mix": "Inbound Priority",
	"Inbound Branch Performance View": "Inbound Branch",
	"Inbound Overdue And Due Date Pressure": "Inbound Overdue",
	"Inbound Open Draft Aging Backlog": "Inbound Backlog",
	"Inbound Owner Workload Review": "Inbound Workload",
	"Inbound Submission Health Ratio": "Inbound Submit Ratio",
	"Release Weekly Volume And Value Trend": "Release Weekly",
	"Release Monthly Volume And Value Trend": "Release Monthly",
	"Release Priority Pipeline Mix": "Release Priority",
	"Release Branch Performance View": "Release Branch",
	"Release Overdue And Due Date Pressure": "Release Overdue",
	"Release Open Draft Aging Backlog": "Release Backlog",
	"Release Owner Workload Review": "Release Workload",
	"Release Submission Health Ratio": "Release Submit Ratio",
	"Inbound Customer Demand Concentration": "Inbound Demand",
	"Release Customer Fulfillment Concentration": "Release Fulfillment",
	"Inbound Order Executive Control Snapshot": "Inbound Snapshot",
	"Release Order Executive Control Snapshot": "Release Snapshot",
	"Sustainability Report": "Sustainability Report",
	"Carbon Footprint Dashboard": "Carbon Footprint",
}


def _workspace_report_groups():
	links = json.loads(WORKSPACE.read_text())["links"]
	groups = {}
	current = None
	for link in links:
		if link.get("type") == "Card Break":
			current = link["label"] if link["label"] in REPORT_SECTIONS else None
			if current:
				groups[current] = []
		elif current and link.get("type") == "Link":
			groups[current].append(link["link_to"])
	return groups


def _sidebar_groups(items):
	groups = {}
	current = None
	for item in items:
		if item.get("type") == "Section Break":
			current = item["label"]
			groups[current] = []
		elif current and item.get("child") and item.get("type") == "Link":
			groups[current].append(item)
		elif item.get("type") == "Link" and not item.get("child"):
			current = None
	return groups


class TestWarehousingSidebarReports(unittest.TestCase):
	def test_report_sections_follow_workspace_cards(self):
		sidebar = json.loads(SIDEBAR.read_text())
		items = sidebar["items"]
		self.assertEqual(sidebar["name"], "Warehousing")
		self.assertEqual(sidebar["module"], "Warehousing")
		self.assertEqual([item["idx"] for item in items], list(range(1, len(items) + 1)))
		self.assertNotIn("Reports", [item["label"] for item in items])

		workspace_groups = _workspace_report_groups()
		self.assertEqual(list(workspace_groups), list(REPORT_SECTIONS))
		sidebar_groups = _sidebar_groups(items)
		report_sections = [
			item for item in items if item.get("type") == "Section Break" and item["label"] in REPORT_SECTIONS.values()
		]
		self.assertEqual(
			[item["label"] for item in report_sections],
			list(REPORT_SECTIONS.values()),
		)

		for card, section in REPORT_SECTIONS.items():
			rows = sidebar_groups[section]
			self.assertEqual([row["link_to"] for row in rows], workspace_groups[card])
			for row in rows:
				self.assertEqual(row["label"], SIDEBAR_LABELS[row["link_to"]])
				self.assertEqual(row["link_type"], "Report")
				self.assertLessEqual(len(row["label"]), CHILD_LABEL_LIMIT)
				self.assertEqual(row["child"], 1)
				self.assertEqual(row["indent"], 0)
				self.assertFalse(row.get("icon"))
				self.assertTrue(_report_dir(row["link_to"]))

		for item in report_sections:
			self.assertEqual(item["child"], 0)
			self.assertEqual(item["indent"], 1)
			self.assertEqual(item["collapsible"], 1)
			self.assertEqual(item["keep_closed"], 1)
			self.assertEqual(item["icon"], "sheet")
			self.assertLessEqual(len(item["label"]), SECTION_LABEL_LIMIT)

		sidebar_reports = [
			item["link_to"]
			for item in items
			if item.get("type") == "Link" and item.get("link_type") == "Report"
		]
		workspace_reports = [name for names in workspace_groups.values() for name in names]
		self.assertEqual(sidebar_reports, workspace_reports)
		self.assertEqual(len(sidebar_reports), len(set(sidebar_reports)))
		self.assertEqual(items[-1]["label"], "Settings")
		self.assertEqual(items[-1]["link_to"], "Warehouse Settings")

	def test_migrate_refreshes_the_sidebar(self):
		text = PATCHES.read_text()
		self.assertIn("logistics.patches.v3_0_sync_warehousing_sidebar", text)
		patch = (ROOT / "logistics/patches/v3_0_sync_warehousing_sidebar.py").read_text()
		self.assertIn('"warehousing.json"', patch)
		self.assertIn('"sidebar"', patch)
		self.assertIn('SIDEBAR_NAME = "Warehousing"', patch)


def _report_dir(report_name: str) -> bool:
	slug = report_name.lower().replace(" ", "_")
	return (REPORTS / slug).is_dir()
