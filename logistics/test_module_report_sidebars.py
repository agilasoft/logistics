# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Module sidebars file workspace report cards as their own groups."""

from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SECTION_LABEL_LIMIT = 20
CHILD_LABEL_LIMIT = 22

# Workspace card -> sidebar section. Short names stay inside the desk rail.
SPECS = [
	{
		"name": "Air Freight",
		"sidebar": "logistics/air_freight/sidebar/air_freight/air_freight.json",
		"workspace": "logistics/air_freight/workspace/air_freight/air_freight.json",
		"anchor": ("replace", "Reports"),
		"extra_reports": [],
		"sections": [
			{"card": "Operational Reports", "label": "Operational Reports", "icon": "sheet"},
			{"card": "Cost Analysis Reports", "label": "Cost Analysis", "icon": "sheet"},
			{"card": "Consolidations", "label": "Consolidations", "icon": "sheet"},
		],
		"labels": {
			"Air Shipment Status Report": "Shipment Status",
			"Air Consolidation Report": "Consolidation Report",
			"Air Freight On-Time Performance Report": "On-Time Performance",
			"Dangerous Goods Compliance Report": "Dangerous Goods",
			"Air Freight Revenue Analysis": "Revenue Analysis",
			"Air Freight Cost Analysis": "Freight Cost",
			"Billing Status Report": "Billing Status",
			"Air Consolidation Executive Snapshot": "Executive Snapshot",
			"Air Consolidation Agent Concentration": "Agent Concentration",
			"Air Consolidation Airline Concentration": "Airline Concentration",
			"Air Consolidation Status Pipeline": "Status Pipeline",
			"Air Consolidation Weekly Activity": "Weekly Activity",
			"Air Consolidation Weekly Throughput Index": "Weekly Throughput",
		},
	},
	{
		"name": "Netting",
		"sidebar": "logistics/netting/sidebar/netting/netting.json",
		"workspace": "logistics/netting/workspace/netting/netting.json",
		"anchor": ("replace", "Reports"),
		"extra_reports": [],
		"sections": [
			{"card": "Pipeline & volume", "label": "Pipeline & Volume", "icon": "sheet"},
			{"card": "Operations & health", "label": "Operations & Health", "icon": "sheet"},
			{"card": "Concentration & workload", "label": "Concentration & Load", "icon": "sheet"},
		],
		"labels": {
			"Settlement Entry Executive Snapshot": "Entry Snapshot",
			"Settlement Group Executive Snapshot": "Group Snapshot",
			"Settlement Entry Weekly Netting Volume": "Entry Weekly Volume",
			"Settlement Entry Monthly Netting Volume": "Entry Monthly Volume",
			"Settlement Entry Weekly Throughput Index": "Entry Throughput",
			"Settlement Group Active Flag Pipeline": "Group Active Pipeline",
			"Settlement Entry Open Draft Aging Backlog": "Entry Draft Aging",
			"Settlement Entry Submission Health Ratio": "Entry Health Ratio",
			"Settlement Group Open Draft Aging Backlog": "Group Draft Aging",
			"Settlement Group Submission Health Ratio": "Group Health Ratio",
			"Settlement Group Weekly Maintenance Index": "Group Weekly Index",
			"Settlement Group Monthly Maintenance Index": "Group Monthly Index",
			"Settlement Entry Customer Concentration": "Entry Customers",
			"Settlement Entry Supplier Concentration": "Entry Suppliers",
			"Settlement Entry Owner Workload Review": "Entry Workload",
			"Settlement Entry Branch Performance View": "Entry Branch View",
			"Settlement Group Customer Concentration": "Group Customers",
			"Settlement Group Owner Workload Review": "Group Workload",
		},
	},
	{
		"name": "Sea Freight",
		"sidebar": "logistics/sea_freight/sidebar/sea_freight/sea_freight.json",
		"workspace": "logistics/sea_freight/workspace/sea_freight/sea_freight.json",
		"anchor": ("replace", "Reports"),
		"extra_reports": ["Container Deposit Report"],
		"sections": [
			{"card": "Operational Reports", "label": "Operational Reports", "icon": "sheet"},
			{"card": "Cost Analysis Report", "label": "Cost Analysis", "icon": "sheet"},
			{"card": "Analytics & Insights", "label": "Analytics & Insights", "icon": "sheet"},
		],
		"labels": {
			"Sea Shipment Status Report": "Shipment Status",
			"Sea Consolidation Report": "Consolidation Report",
			"Container Utilization Report": "Container Utilization",
			"Sea Freight On-Time Performance Report": "On-Time Performance",
			"Sea Freight Revenue Analysis": "Revenue Analysis",
			"Sea Freight Cost Analysis": "Freight Cost",
			"Sea Freight Billing Status Report": "Billing Status",
			"Sea Freight Performance Dashboard": "Performance",
			"Sea Freight Route Analysis": "Route Analysis",
			"Shipping Line Performance Report": "Line Performance",
		},
	},
	{
		"name": "Transport",
		"sidebar": "logistics/transport/sidebar/transport/transport.json",
		"workspace": "logistics/transport/workspace/transport/transport.json",
		"anchor": ("replace", "Reports"),
		"extra_reports": [],
		"sections": [
			{"card": "Operational Monitoring", "label": "Ops Monitoring", "icon": "sheet"},
			{"card": "Cost Analysis Reports", "label": "Cost Analysis", "icon": "sheet"},
			{"card": "Strategic Planning", "label": "Strategic Planning", "icon": "sheet"},
		],
		"labels": {
			"Vehicle Utilization Report": "Vehicle Utilization",
			"On-Time Delivery Report": "On-Time Delivery",
			"Fuel Consumption Analysis": "Fuel Consumption",
			"Driver Performance Report": "Driver Performance",
			"Route Cost Analysis": "Route Cost",
			"Consolidation Savings Report": "Savings Report",
			"Transport Cost per Job": "Cost per Job",
			"Fleet Capacity Utilization": "Fleet Capacity",
			"Road Compliance Report": "Road Compliance",
		},
	},
	{
		"name": "Sustainability",
		"sidebar": "logistics/sustainability/sidebar/sustainability/sustainability.json",
		"workspace": "logistics/sustainability/workspace/sustainability/sustainability.json",
		"anchor": ("replace_range", "Carbon reports", "Source documents"),
		"extra_reports": [],
		"sections": [
			{"card": "Carbon footprint", "label": "Carbon Footprint", "icon": "sheet"},
			{"card": "Energy & waste", "label": "Energy & Waste", "icon": "sheet"},
			{"card": "Goals & compliance", "label": "Goals & Compliance", "icon": "flag"},
			{"card": "Metrics & trends", "label": "Metrics & Trends", "icon": "sheet"},
		],
		"labels": {
			"Carbon Footprint Report": "Carbon Footprint",
			"Carbon Footprint Dashboard": "Carbon Dashboard",
			"Carbon Footprint Executive Snapshot": "Executive Snapshot",
			"Carbon Footprint Emissions Scope Mix": "Emissions Scope Mix",
			"Carbon Footprint Monthly Activity": "Monthly Activity",
			"Carbon Footprint Weekly Activity": "Weekly Activity",
			"Energy Consumption Report": "Energy Consumption",
			"Energy Efficiency Report": "Energy Efficiency",
			"Waste Management Report": "Waste Management",
			"Sustainability Report": "Sustainability Report",
			"Sustainability Goals Report": "Sustainability Goals",
			"Sustainability Compliance Report": "Compliance Report",
			"Carbon Footprint Verification Pipeline": "Verification Pipeline",
			"Sustainability Compliance Status Pipeline": "Compliance Pipeline",
			"Sustainability Metrics Report": "Metrics Report",
			"Sustainability Dashboard Report": "Dashboard Report",
			"Trend Analysis Report": "Trend Analysis Report",
			"Cross Module Summary Report": "Cross Module Summary",
			"Sustainability Metrics Executive Snapshot": "Metrics Snapshot",
		},
	},
	{
		"name": "Special Projects",
		"sidebar": "logistics/special_projects/sidebar/special_projects/special_projects.json",
		"workspace": "logistics/special_projects/workspace/special_projects/special_projects.json",
		"anchor": ("replace", "Reports"),
		"extra_reports": [],
		"sections": [
			{"card": "Operational", "label": "Operational", "icon": "sheet"},
		],
		"labels": {
			"Special Projects Report": "Projects Report",
			"Cost Analysis Reports": "Cost Analysis",
			"Special Project Billing Status Report": "Billing Status",
		},
	},
	{
		"name": "MICE",
		"sidebar": "logistics/mice/sidebar/mice/mice.json",
		"workspace": "logistics/mice/workspace/mice/mice.json",
		"anchor": ("replace", "Reports"),
		"extra_reports": [],
		"sections": [
			{"card": "Operational", "label": "Operational", "icon": "sheet"},
		],
		"labels": {
			"MICE Pipeline Report": "Pipeline",
			"MICE Activity Status Report": "Activity Status",
			"MICE Billing Status Report": "Billing Status",
		},
	},
	{
		"name": "Pricing Center",
		"sidebar": "logistics/pricing_center/sidebar/pricing_center/pricing_center.json",
		"workspace": "logistics/pricing_center/workspace/pricing/pricing.json",
		"anchor": ("insert_before", "Module Settings"),
		"extra_reports": [],
		"sections": [
			{"card": "Ocean freight economics", "label": "Ocean Freight", "icon": "sheet"},
			{"card": "Air freight economics", "label": "Air Freight", "icon": "sheet"},
			{"card": "Road transport economics", "label": "Road Transport", "icon": "sheet"},
			{"card": "Projects & warehouse productivity", "label": "Projects & Warehouse", "icon": "sheet"},
			{"card": "Customs & declarations", "label": "Declarations", "icon": "sheet"},
			{"card": "Sustainability & cross-module KPIs", "label": "Sustainability KPIs", "icon": "sheet"},
			{"card": "Sales Quote analytics", "label": "Quote Analytics", "icon": "sheet"},
		],
		"labels": {
			"Sea Freight Revenue Analysis": "Sea Revenue",
			"Sea Freight Cost Analysis": "Sea Cost",
			"Sea Freight Billing Status Report": "Sea Billing",
			"Sea Freight Performance Dashboard": "Sea Performance",
			"Sea Freight Route Analysis": "Sea Route",
			"Air Freight Revenue Analysis": "Air Revenue",
			"Air Freight Cost Analysis": "Air Cost",
			"Billing Status Report": "Air Billing",
			"Air Freight Performance Dashboard": "Air Performance",
			"Route Analysis Report": "Air Route",
			"Cost Analysis Reports": "Cost Analysis",
			"Transport Cost per Job": "Cost per Job",
			"Route Cost Analysis": "Route Cost",
			"Consolidation Savings Report": "Savings Report",
			"On-Time Delivery Report": "On-Time Delivery",
			"Special Project Cost vs Revenue Report": "Cost vs Revenue",
			"Special Project Profitability Report": "Profitability",
			"Special Project Pipeline Report": "Project Pipeline",
			"Labor Productivity Report": "Labor Productivity",
			"Warehouse Stock Balance": "Stock Balance",
			"Declaration Value Report": "Declaration Value",
			"Declaration Status Report": "Declaration Status",
			"Customs Compliance Report": "Customs Compliance",
			"Filing Compliance Report": "Filing Compliance",
			"Global Customs Dashboard": "Customs Dashboard",
			"Cross Module Summary Report": "Cross Module",
			"Sustainability Dashboard Report": "ESG Dashboard",
			"Carbon Footprint Report": "Carbon Footprint",
			"Energy Consumption Report": "Energy Use",
			"Fuel Consumption Analysis": "Fuel Use",
			"Sales Quote Executive Control Snapshot": "Quote Snapshot",
			"Sales Quote Submission Health Ratio": "Quote Health",
			"Sales Quote Status Funnel Mix": "Status Funnel",
			"Sales Quote Open Draft Aging Backlog": "Draft Aging",
			"Sales Quote Monthly Pipeline And Value": "Monthly Pipeline",
			"Sales Quote Weekly Pipeline And Value": "Weekly Pipeline",
			"Sales Quote Monthly Throughput Index": "Monthly Throughput",
			"Sales Quote Weekly Throughput Index": "Weekly Throughput",
			"Sales Quote Customer Win Concentration": "Customer Wins",
			"Sales Quote Sales Representative Concentration": "Sales Rep Mix",
			"Sales Quote Operations Representative Concentration": "Ops Rep Mix",
			"Sales Quote Owner Workload Review": "Owner Workload",
			"Sales Quote Branch Performance View": "Branch View",
			"Sales Quote Direction Trade Mix": "Direction Mix",
			"Sales Quote Incoterm Commercial Mix": "Incoterm Mix",
			"Sales Quote Transport Mode Offer Mix": "Transport Mix",
			"Sales Quote Main Service Mix": "Service Mix",
			"Sales Quote Job Type Portfolio Mix": "Job Type Mix",
			"Sales Quote Quotation Type Mix": "Quote Type Mix",
			"Sales Quote Overdue Validity Pressure": "Overdue Validity",
		},
	},
	{
		"name": "Intercompany",
		"sidebar": "logistics/intercompany/sidebar/intercompany/intercompany.json",
		"workspace": "logistics/intercompany/workspace/intercompany/intercompany.json",
		"anchor": ("create",),
		"header_icon": "intercompany",
		"module": "Intercompany",
		"extra_reports": [],
		"pinned": [
			("Home", "Intercompany", "Workspace", "house"),
			("Workflow Center", "workflow-center", "Page", "workflow"),
			("Settings", "Intercompany Settings", "DocType", "settings"),
			("Invoice Log", "Intercompany Invoice Log", "DocType", "file-text"),
		],
		"sections": [
			{"card": "Shipment & consolidation status", "label": "Shipment Status", "icon": "sheet"},
			{"card": "Revenue & cost visibility", "label": "Revenue & Cost", "icon": "sheet"},
			{"card": "Billing & accruals context", "label": "Routes & Performance", "icon": "sheet"},
			{"card": "Customs & compliance", "label": "Customs Compliance", "icon": "sheet"},
			{"card": "Warehouse & productivity", "label": "Warehouse", "icon": "sheet"},
			{"card": "Performance & ESG analytics", "label": "ESG Analytics", "icon": "sheet"},
		],
		"labels": {
			"Sea Shipment Status Report": "Sea Status",
			"Air Shipment Status Report": "Air Status",
			"On-Time Delivery Report": "On-Time Delivery",
			"Sea Consolidation Report": "Sea Consolidation",
			"Air Consolidation Report": "Air Consolidation",
			"Sea Freight Revenue Analysis": "Sea Revenue",
			"Air Freight Revenue Analysis": "Air Revenue",
			"Sea Freight Cost Analysis": "Sea Cost",
			"Air Freight Cost Analysis": "Air Cost",
			"Sea Freight Billing Status Report": "Sea Billing",
			"Sea Freight On-Time Performance Report": "Sea On-Time",
			"Air Freight On-Time Performance Report": "Air On-Time",
			"Sea Freight Route Analysis": "Sea Route",
			"Route Analysis Report": "Route Analysis",
			"Shipping Line Performance Report": "Line Performance",
			"Declaration Status Report": "Declaration Status",
			"Manifest Status Report": "Manifest Status",
			"Customs Compliance Report": "Customs Compliance",
			"Filing Compliance Report": "Filing Compliance",
			"Declaration Value Report": "Declaration Value",
			"Warehouse Stock Balance": "Stock Balance",
			"Warehouse Stock Ledger": "Stock Ledger",
			"Storage Location Usage": "Location Usage",
			"Handling Unit Capacity": "Unit Capacity",
			"Capacity Forecasting Report": "Capacity Forecast",
			"Cross Module Summary Report": "Cross Module",
			"Sustainability Dashboard Report": "ESG Dashboard",
			"Carbon Footprint Report": "Carbon Footprint",
			"Energy Consumption Report": "Energy Use",
			"Fuel Consumption Analysis": "Fuel Use",
		},
	},
	{
		"name": "Control Tower",
		"sidebar": "logistics/control_tower/sidebar/control_tower/control_tower.json",
		"workspace": "logistics/control_tower/workspace/control_tower/control_tower.json",
		"anchor": ("create",),
		"header_icon": "control_tower",
		"module": "Control Tower",
		"extra_reports": [],
		"pinned": [
			("Home", "Control Tower", "Workspace", "house"),
			("Workflow Center", "workflow-center", "Page", "workflow"),
		],
		"sections": [
			{
				"label": "Profit Centers",
				"icon": "chart-column",
				"items": [
					("ATN Sales Luzon", "Control Tower - ATN Sales - Luzon", "Dashboard"),
					("ATN Sales VisMin", "Control Tower - ATN Sales - VisMin", "Dashboard"),
					("ATN Overseas BD", "Control Tower - ATN Overseas Business Development", "Dashboard"),
					("ALTA Fairs", "Control Tower - ALTA Fairs & Exhibits", "Dashboard"),
					("ATN Projects 1", "Control Tower - ATN Special Projects 1", "Dashboard"),
					("ATN Projects 2", "Control Tower - ATN Special Projects 2", "Dashboard"),
					("ASL Sales", "Control Tower - ASL Sales", "Dashboard"),
					("ASL Overseas BD", "Control Tower - ASL Overseas Business Development", "Dashboard"),
					("Luxury", "Control Tower - Luxury", "Dashboard"),
				],
			},
			{
				"label": "Cost Centers",
				"icon": "chart-column",
				"items": [
					("ATN Seafreight", "Control Tower - ATN Head Office Seafreight", "Dashboard"),
					("ATN Airfreight", "Control Tower - ATN Airfreight", "Dashboard"),
					("ATN Brokerage", "Control Tower - ATN Brokerage", "Dashboard"),
					("ATN Haulage", "Control Tower - ATN Haulage", "Dashboard"),
					("ATN Domestic Sea", "Control Tower - ATN Domestic Sea", "Dashboard"),
					("ATN Warehouse", "Control Tower - ATN Warehouse", "Dashboard"),
					("Vis-Min Branches", "Control Tower - Vis-Min Branches", "Dashboard"),
					("North Luzon", "Control Tower - North Luzon Branches", "Dashboard"),
					("ALTA Cost Center", "Control Tower - ALTA Fairs & Exhibits (Cost Center)", "Dashboard"),
					("ASL Operations", "Control Tower - ASL Operations", "Dashboard"),
				],
			},
			{
				"label": "Resource Centers",
				"icon": "chart-column",
				"items": [
					("Human Resources", "Control Tower - Human Resources", "Dashboard"),
					("Information Tech", "Control Tower - Information Technology", "Dashboard"),
					("Accounting", "Control Tower - Accounting & Finance", "Dashboard"),
				],
			},
			{"card": "Registry", "label": "Registry", "icon": "database"},
			{"card": "Planning", "label": "Planning", "icon": "database"},
			{"card": "Operations Supplements", "label": "Operations", "icon": "database"},
			{"card": "Human Resources", "label": "HR Trackers", "icon": "database"},
			{"card": "Information Technology", "label": "IT Trackers", "icon": "database"},
			{"card": "Accounting & Finance", "label": "Finance Trackers", "icon": "database"},
			{"card": "Profit Center Reports", "label": "Profit Reports", "icon": "sheet"},
			{"card": "Cost Center Reports", "label": "Cost Reports", "icon": "sheet"},
			# Resource Center Reports repeats CT HR Summary, CT IT Summary, and
			# CT Accounting Finance Summary. The desk keeps the first link to a
			# target, so those reports stay on the tracker groups above.
		],
		"labels": {
			"Control Tower Organization": "Organization",
			"Control Tower GP Target": "GP Target",
			"Pipeline Entry": "Pipeline Entry",
			"Risk Register Entry": "Risk Register Entry",
			"Returned Billing": "Returned Billing",
			"Vehicle Maintenance Log": "Vehicle Maintenance",
			"HR Vacancy": "HR Vacancy",
			"HR Turnover Event": "HR Turnover Event",
			"HR Tardiness OT Entry": "HR Tardiness OT Entry",
			"HR Labor Cost Period": "HR Labor Cost Period",
			"CT HR Summary": "HR Summary",
			"IT Ticket": "IT Ticket",
			"IT Uptime Log": "IT Uptime Log",
			"IT Security Incident": "IT Security Incident",
			"CT IT Summary": "IT Summary",
			"Bad Account Entry": "Bad Account Entry",
			"Customer Credit Limit": "Customer Credit Limit",
			"Investment Holding": "Investment Holding",
			"Bank Reconciliation Discrepancy": "Bank Discrepancy",
			"Supplier Cash Bond": "Supplier Cash Bond",
			"CT Accounting Finance Summary": "Finance Summary",
			"CT GP Summary": "GP Summary",
			"CT Top Clients by GP": "Top Clients",
			"CT Top Agents Volumes": "Top Agents",
			"CT Top Carriers Volumes": "Top Carriers",
			"CT Pipeline Listing": "Pipeline Listing",
			"CT Risk Register Listing": "Risk Listing",
			"CT Jobs KPI": "Jobs KPI",
			"CT Trips Per Month": "Trips Per Month",
			"CT Handling In Out": "Handling In Out",
			"CT Facility Occupancy": "Facility Occupancy",
			"CT Top Outsourced Truckers": "Outsourced Truckers",
			"CT Top Outsourced Brokers": "Outsourced Brokers",
			"CT Returned Billings": "Returned Billings",
			"CT Haulage Intercompany Charges": "Haulage Charges",
		},
	},
]


def _cards(path: Path):
	links = json.loads(path.read_text())["links"]
	cards = []
	current = None
	for link in links:
		if link.get("type") == "Card Break":
			current = {"label": link["label"], "links": []}
			cards.append(current)
		elif current is not None and link.get("type") == "Link":
			current["links"].append((link.get("link_type"), link.get("link_to"), link.get("label")))
	return cards


def _sidebar_groups(items):
	groups = {}
	order = []
	current = None
	for item in items:
		if item.get("type") == "Section Break":
			current = item["label"]
			groups[current] = []
			order.append(current)
		elif current and item.get("child") and item.get("type") == "Link":
			groups[current].append(item)
		elif item.get("type") == "Link" and not item.get("child"):
			current = None
	return order, groups


def _section(label, icon):
	return {
		"child": 0,
		"collapsible": 1,
		"doctype": "Sidebar Item",
		"icon": icon,
		"idx": 0,
		"indent": 1,
		"keep_closed": 1,
		"label": label,
		"link_type": "DocType",
		"parentfield": "items",
		"parenttype": "Sidebar",
		"show_arrow": 0,
		"type": "Section Break",
	}


def _child(label, link_to, link_type):
	return {
		"child": 1,
		"collapsible": 1,
		"doctype": "Sidebar Item",
		"idx": 0,
		"indent": 0,
		"keep_closed": 0,
		"label": label,
		"link_to": link_to,
		"link_type": link_type,
		"parentfield": "items",
		"parenttype": "Sidebar",
		"show_arrow": 0,
		"type": "Link",
	}


def _pinned(label, link_to, link_type, icon):
	return {
		"child": 0,
		"collapsible": 1,
		"doctype": "Sidebar Item",
		"icon": icon,
		"idx": 0,
		"indent": 0,
		"keep_closed": 0,
		"label": label,
		"link_to": link_to,
		"link_type": link_type,
		"parentfield": "items",
		"parenttype": "Sidebar",
		"show_arrow": 0,
		"type": "Link",
	}


def _report_names():
	names = set()
	for path in ROOT.joinpath("logistics").rglob("report/*/*.json"):
		if path.name.startswith("."):
			continue
		try:
			data = json.loads(path.read_text())
		except json.JSONDecodeError:
			continue
		if data.get("doctype") == "Report" and data.get("name"):
			names.add(data["name"])
	return names


def _built_sections(spec, cards):
	by_label = {card["label"]: card for card in cards}
	rows = []
	for section in spec["sections"]:
		rows.append(_section(section["label"], section["icon"]))
		if "items" in section:
			for label, link_to, link_type in section["items"]:
				rows.append(_child(label, link_to, link_type))
			continue
		card = by_label[section["card"]]
		for link_type, link_to, _label in card["links"]:
			rows.append(_child(spec["labels"][link_to], link_to, link_type))
	return rows


def _reindex(items):
	for idx, item in enumerate(items, start=1):
		item["idx"] = idx
	return items


def apply_sidebar_specs(only=None):
	"""Write the sidebar JSON files from SPECS. Used by the author, not by migrate."""
	for spec in SPECS:
		if only and spec["name"] not in only:
			continue
		cards = _cards(ROOT / spec["workspace"])
		built = _built_sections(spec, cards)
		for row in built:
			limit = SECTION_LABEL_LIMIT if row["type"] == "Section Break" else CHILD_LABEL_LIMIT
			if len(row["label"]) > limit:
				raise SystemExit(f"{spec['name']} label too long: {row['label']}")
		path = ROOT / spec["sidebar"]
		anchor = spec["anchor"]
		if anchor[0] == "create":
			items = [_pinned(*row) for row in spec["pinned"]] + built
			data = {
				"app": "logistics",
				"doctype": "Sidebar",
				"header_icon": spec["header_icon"],
				"items": _reindex(items),
				"module": spec["module"],
				"name": spec["name"],
				"standard": 1,
				"title": spec["name"],
			}
			path.parent.mkdir(parents=True, exist_ok=True)
		else:
			data = json.loads(path.read_text())
			items = data["items"]
			if anchor[0] == "replace":
				start = next(i for i, item in enumerate(items) if item.get("type") == "Section Break" and item.get("label") == anchor[1])
				end = next((i for i in range(start + 1, len(items)) if items[i].get("type") == "Section Break"), len(items))
			elif anchor[0] == "replace_range":
				start = next(i for i, item in enumerate(items) if item.get("type") == "Section Break" and item.get("label") == anchor[1])
				end = next(i for i, item in enumerate(items) if item.get("type") == "Section Break" and item.get("label") == anchor[2])
			elif anchor[0] == "insert_before":
				start = end = next(i for i, item in enumerate(items) if item.get("type") == "Section Break" and item.get("label") == anchor[1])
			else:
				raise SystemExit(anchor)
			data["items"] = _reindex(items[:start] + built + items[end:])
		path.write_text(json.dumps(data, indent=1) + "\n")


class TestModuleReportSidebars(unittest.TestCase):
	def test_report_groups_follow_workspace_cards(self):
		reports = _report_names()
		for spec in SPECS:
			with self.subTest(spec["name"]):
				cards = _cards(ROOT / spec["workspace"])
				by_label = {card["label"]: card for card in cards}
				seen_reports = set()
				workspace_report_cards = []
				for card in cards:
					card_reports = [link_to for link_type, link_to, _label in card["links"] if link_type == "Report"]
					if not card_reports:
						continue
					# The desk drops a second link to the same target, so a card whose
					# reports already appear earlier would render as an empty group.
					if all(name in seen_reports for name in card_reports):
						continue
					workspace_report_cards.append(card["label"])
					seen_reports.update(card_reports)
				spec_report_cards = [
					section["card"]
					for section in spec["sections"]
					if section.get("card") and any(link[0] == "Report" for link in by_label[section["card"]]["links"])
				]
				self.assertEqual(spec_report_cards, workspace_report_cards)

				sidebar = json.loads((ROOT / spec["sidebar"]).read_text())
				self.assertEqual(sidebar["name"], spec["name"])
				self.assertEqual(sidebar["app"], "logistics")
				self.assertEqual(sidebar["standard"], 1)
				items = sidebar["items"]
				self.assertEqual([item["idx"] for item in items], list(range(1, len(items) + 1)))
				order, groups = _sidebar_groups(items)
				self.assertEqual(
					[section["label"] for section in spec["sections"]],
					[label for label in order if label in {section["label"] for section in spec["sections"]}],
				)

				for section in spec["sections"]:
					rows = groups[section["label"]]
					if "items" in section:
						expected = [(link_type, link_to) for _label, link_to, link_type in section["items"]]
						labels = [label for label, _link_to, _link_type in section["items"]]
					else:
						card = by_label[section["card"]]
						expected = [(link_type, link_to) for link_type, link_to, _label in card["links"]]
						labels = [spec["labels"][link_to] for _link_type, link_to, _label in card["links"]]
					self.assertEqual([(row["link_type"], row["link_to"]) for row in rows], expected)
					self.assertEqual([row["label"] for row in rows], labels)
					for row in rows:
						self.assertEqual(row["child"], 1)
						self.assertEqual(row["indent"], 0)
						self.assertFalse(row.get("icon"))
						self.assertLessEqual(len(row["label"]), CHILD_LABEL_LIMIT)
						if row["link_type"] == "Report":
							self.assertIn(row["link_to"], reports)

				section_rows = [item for item in items if item.get("type") == "Section Break" and item["label"] in groups]
				owned = {section["label"]: section for section in spec["sections"]}
				for item in section_rows:
					if item["label"] not in owned:
						continue
					self.assertEqual(item["child"], 0)
					self.assertEqual(item["indent"], 1)
					self.assertEqual(item["collapsible"], 1)
					self.assertEqual(item["keep_closed"], 1)
					self.assertEqual(item["icon"], owned[item["label"]]["icon"])
					self.assertLessEqual(len(item["label"]), SECTION_LABEL_LIMIT)

				workspace_reports = [
					link_to
					for card in cards
					for link_type, link_to, _label in card["links"]
					if link_type == "Report"
				]
				sidebar_reports = [
					item["link_to"] for item in items if item.get("type") == "Link" and item.get("link_type") == "Report"
				]
				self.assertEqual(
					sorted(set(sidebar_reports) - set(workspace_reports)),
					sorted(spec["extra_reports"]),
				)
				self.assertTrue(set(workspace_reports) <= set(sidebar_reports))

				if spec["anchor"][0] == "create":
					pinned = [
						(item["label"], item["link_to"], item["link_type"], item["icon"])
						for item in items
						if item.get("type") == "Link" and not item.get("child")
					]
					self.assertEqual(pinned, spec["pinned"])

	def test_migrate_refreshes_each_sidebar(self):
		text = (ROOT / "logistics/patches.txt").read_text()
		self.assertIn("logistics.patches.v3_0_sync_module_report_sidebars", text)
		patch = (ROOT / "logistics/patches/v3_0_sync_module_report_sidebars.py").read_text()
		for spec in SPECS:
			self.assertIn(spec["sidebar"].split("logistics/")[1], patch)
			self.assertIn(f'"{spec["name"]}"', patch)
