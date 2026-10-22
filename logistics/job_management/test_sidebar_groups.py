# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Job Management sidebar follows the same desk pattern as the other modules."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKSPACE = ROOT / "logistics/job_management/workspace/job_management/job_management.json"
SIDEBAR = ROOT / "logistics/job_management/sidebar/job_management/job_management.json"
PATCHES = ROOT / "logistics/patches.txt"
SPRITE = ROOT / "logistics/public/icons/module-icons.svg"
DOCTYPES = ROOT / "logistics/job_management/doctype"

# The desk rail fits about this many characters before the label ellipsizes.
SECTION_LABEL_LIMIT = 20
CHILD_LABEL_LIMIT = 22

PINNED = (
	("Home", "Workspace", "Job Management", "house"),
	("Workflow Center", "Page", "workflow-center", "workflow"),
	("Job Number", "DocType", "Job Number", "file-text"),
	("Beginning Jobs", "Page", "beginning-jobs", "file-plus"),
)

SECTION_ICONS = {
	"Job Operations": "chart-column",
	"Masters": "database",
	"Settings": "settings",
	"Freight Analysis": "sheet",
	"Revenue & Cost": "sheet",
	"Billing": "sheet",
	"OTIF & Productivity": "sheet",
	"Customs & Security": "sheet",
	"Projects & ESG": "sheet",
}

GROUPS = {
	"Job Operations": (
		("Recognition Status", "Report", "Recognition Status"),
		("Recognition Aging", "Report", "Job Recognition Aging"),
		("Receivables Aging", "Report", "Job Receivables Aging"),
		("Margin Watchlist", "Report", "Job Profit Margin Watchlist"),
	),
	"Masters": (
		("Company", "DocType", "Company"),
		("Branch", "DocType", "Branch"),
		("Cost Center", "DocType", "Cost Center"),
		("Profit Center", "DocType", "Profit Center"),
		("Job Task Template", "DocType", "Job Task Template"),
	),
	"Settings": (
		("Recognition Policy", "DocType", "Recognition Policy Settings"),
	),
	"Freight Analysis": (
		("Sea Revenue Analysis", "Report", "Sea Freight Revenue Analysis"),
		("Air Revenue Analysis", "Report", "Air Freight Revenue Analysis"),
		("Sea Cost Analysis", "Report", "Sea Freight Cost Analysis"),
		("Air Cost Analysis", "Report", "Air Freight Cost Analysis"),
	),
	"Revenue & Cost": (
		("Transport Cost", "Report", "Transport Cost per Job"),
		("Route Cost Analysis", "Report", "Route Cost Analysis"),
		("Cost Analysis", "Report", "Cost Analysis Reports"),
		("Consolidation Savings", "Report", "Consolidation Savings Report"),
		("Cost vs Revenue", "Report", "Special Project Cost vs Revenue Report"),
	),
	"Billing": (
		("Sea Billing Status", "Report", "Sea Freight Billing Status Report"),
		("Billing Status", "Report", "Billing Status Report"),
		("Project Billing Status", "Report", "Special Project Billing Status Report"),
		("Sea Performance", "Report", "Sea Freight Performance Dashboard"),
		("Air Performance", "Report", "Air Freight Performance Dashboard"),
	),
	"OTIF & Productivity": (
		("On-Time Delivery", "Report", "On-Time Delivery Report"),
		("Sea On-Time", "Report", "Sea Freight On-Time Performance Report"),
		("Air On-Time", "Report", "Air Freight On-Time Performance Report"),
		("Labor Productivity", "Report", "Labor Productivity Report"),
		("Cross-Module Summary", "Report", "Cross Module Summary Report"),
	),
	"Customs & Security": (
		("Declaration Status", "Report", "Declaration Status Report"),
		("Customs Compliance", "Report", "Customs Compliance Report"),
		("Filing Compliance", "Report", "Filing Compliance Report"),
		("Manifest Status", "Report", "Manifest Status Report"),
		("Dangerous Goods", "Report", "Dangerous Goods Compliance Report"),
	),
	"Projects & ESG": (
		("Stock Balance", "Report", "Warehouse Stock Balance"),
		("Stock Ledger", "Report", "Warehouse Stock Ledger"),
		("Profitability", "Report", "Special Project Profitability Report"),
		("Projects by Customer", "Report", "Special Projects by Customer Report"),
		("Project Pipeline", "Report", "Special Project Pipeline Report"),
	),
}


def _workspace_targets():
	workspace = json.loads(WORKSPACE.read_text())
	targets = {(row["type"], row["link_to"]) for row in workspace["shortcuts"]}
	for link in workspace["links"]:
		if link.get("type") == "Link":
			targets.add((link["link_type"], link["link_to"]))
	return targets


def _parent_doctypes():
	names = []
	for path in DOCTYPES.glob("*/*.json"):
		data = json.loads(path.read_text())
		if data.get("doctype") == "DocType" and not data.get("istable"):
			names.append(data["name"])
	return names


class TestJobManagementSidebarGroups(unittest.TestCase):
	def test_sidebar_matches_other_modules(self):
		sidebar = json.loads(SIDEBAR.read_text())
		self.assertEqual(sidebar["doctype"], "Sidebar")
		self.assertEqual(sidebar["name"], "Job Management")
		self.assertEqual(sidebar["title"], "Job Management")
		self.assertEqual(sidebar["module"], "Job Management")
		self.assertEqual(sidebar["app"], "logistics")
		self.assertEqual(sidebar["standard"], 1)
		self.assertEqual(sidebar["header_icon"], "job_management")
		self.assertIn('id="icon-job_management"', SPRITE.read_text())

		items = sidebar["items"]
		self.assertEqual([item["idx"] for item in items], list(range(1, len(items) + 1)))

		pinned = [
			(item["label"], item["link_type"], item["link_to"], item["icon"])
			for item in items
			if item.get("type") == "Link" and not item.get("child")
		]
		self.assertEqual(pinned, list(PINNED))
		for item in items:
			if item.get("type") == "Link" and not item.get("child"):
				self.assertEqual(item["indent"], 0)
				self.assertLessEqual(len(item["label"]), CHILD_LABEL_LIMIT)

		sections = [item for item in items if item.get("type") == "Section Break"]
		self.assertEqual([item["label"] for item in sections], list(SECTION_ICONS))
		for item in sections:
			self.assertEqual(item["child"], 0)
			self.assertEqual(item["indent"], 1)
			self.assertEqual(item["collapsible"], 1)
			self.assertEqual(item["keep_closed"], 1)
			self.assertEqual(item["icon"], SECTION_ICONS[item["label"]])
			self.assertLessEqual(len(item["label"]), SECTION_LABEL_LIMIT)

		groups = {}
		current = None
		for item in items:
			if item.get("type") == "Section Break":
				current = item["label"]
				groups[current] = []
			elif current and item.get("child"):
				self.assertEqual(item["indent"], 0)
				self.assertFalse(item.get("icon"))
				self.assertEqual(item["type"], "Link")
				self.assertFalse(item.get("filters"))
				self.assertLessEqual(len(item["label"]), CHILD_LABEL_LIMIT)
				groups[current].append((item["label"], item["link_type"], item["link_to"]))
			else:
				current = None

		self.assertEqual(groups, {name: list(rows) for name, rows in GROUPS.items()})

		sidebar_targets = {
			(item["link_type"], item["link_to"])
			for item in items
			if item.get("type") == "Link"
		}
		self.assertTrue(_workspace_targets() <= sidebar_targets)
		report_targets = [link_to for link_type, link_to in sidebar_targets if link_type == "Report"]
		self.assertEqual(len(report_targets), len(set(report_targets)))

		sidebar_doctypes = [
			item["link_to"]
			for item in items
			if item.get("type") == "Link" and item.get("link_type") == "DocType"
		]
		for name in _parent_doctypes():
			self.assertIn(name, sidebar_doctypes)

	def test_migrate_refreshes_the_sidebar(self):
		text = PATCHES.read_text()
		self.assertIn("logistics.patches.v3_0_sync_job_management_sidebar", text)
		patch = (ROOT / "logistics/patches/v3_0_sync_job_management_sidebar.py").read_text()
		self.assertIn('"job_management.json"', patch)
		self.assertIn('"sidebar"', patch)
		self.assertIn('SIDEBAR_NAME = "Job Management"', patch)

		self.assertIn("logistics.patches.v3_0_align_job_management_sidebar", text)
		align = (ROOT / "logistics/patches/v3_0_align_job_management_sidebar.py").read_text()
		self.assertIn("v3_0_sync_job_management_sidebar", align)
		self.assertIn("sync_sidebar", align)

		self.assertIn("logistics.patches.v3_0_show_beginning_jobs_in_sidebar", text)
		show = (ROOT / "logistics/patches/v3_0_show_beginning_jobs_in_sidebar.py").read_text()
		self.assertIn("v3_0_sync_job_management_sidebar", show)
		self.assertIn("sync_sidebar", show)
		self.assertIn("beginning-jobs", show)
