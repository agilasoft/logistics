# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import annotations

from frappe.tests.utils import FrappeTestCase

from logistics.high_value.high_value_operations_dashboard import (
	attention_rows,
	brand_alerts,
	brand_work_rows,
	build_brand_markers,
	classify_brand,
	count_brand_kpis,
	count_sla_kpis,
	hv_user_workload,
	job_mix_counts,
	merge_alert_items,
	pick_brand_unloco,
	resolve_quote_brand,
	sla_alerts,
	unassigned_work_rows,
)


class TestHighValueOperationsDashboardHelpers(FrappeTestCase):
	def test_classify_active_live_overdue_flags(self):
		idle = classify_brand([], [])
		self.assertFalse(idle["active"])
		self.assertTrue(idle["idle"])
		self.assertEqual(idle["severity"], "idle")

		active = classify_brand([{"name": "SQ-1", "docstatus": 0}], [])
		self.assertTrue(active["active"])
		self.assertFalse(active["live"])
		self.assertFalse(active["overdue"])

		live = classify_brand(
			[{"name": "SQ-1", "docstatus": 0}],
			[{"name": "AIR-1", "job_status": "In Progress", "sla_status": "On Track"}],
		)
		self.assertTrue(live["live"])
		self.assertTrue(live["active"])
		self.assertEqual(live["severity"], "live")

		overdue = classify_brand(
			[],
			[{"name": "SEA-1", "job_status": "Submitted", "sla_status": "Breached"}],
		)
		self.assertTrue(overdue["overdue"])
		self.assertEqual(overdue["severity"], "overdue")

		closed = classify_brand(
			[{"name": "SQ-1", "docstatus": 2}],
			[{"name": "AIR-1", "job_status": "Completed", "sla_status": "Breached"}],
		)
		self.assertFalse(closed["active"])
		self.assertFalse(closed["overdue"])

	def test_kpis_count_brands_not_jobs(self):
		flags = [
			classify_brand([{"docstatus": 0}], [{"job_status": "In Progress", "sla_status": "On Track"}]),
			classify_brand([{"docstatus": 0}], [{"job_status": "Submitted", "sla_status": "Breached"}]),
			classify_brand([], []),
		]
		kpis = count_brand_kpis(flags)
		self.assertEqual(kpis["brands"], 3)
		self.assertEqual(kpis["active"], 2)
		self.assertEqual(kpis["live"], 2)
		self.assertEqual(kpis["overdue"], 1)
		self.assertEqual(kpis["idle"], 1)

	def test_sla_kpis_skip_closed_jobs(self):
		jobs = [
			{"job_status": "In Progress", "sla_status": "At Risk"},
			{"job_status": "Submitted", "sla_status": "Breached"},
			{"job_status": "Completed", "sla_status": "Breached"},
		]
		self.assertEqual(count_sla_kpis(jobs), {"sla_at_risk": 1, "sla_breached": 1})

	def test_resolve_quote_brand_explicit_then_customer(self):
		by_name = {"ROLEX": "ROLEX", "rolex": "ROLEX"}
		by_label = {"Rolex SA": "ROLEX", "rolex sa": "ROLEX"}
		self.assertEqual(
			resolve_quote_brand({"hv_brand": "ROLEX", "customer": "Other"}, by_name, by_label),
			"ROLEX",
		)
		self.assertEqual(
			resolve_quote_brand({"hv_brand": "", "customer": "Rolex SA"}, by_name, by_label),
			"ROLEX",
		)
		self.assertEqual(
			resolve_quote_brand({"hv_brand": "", "customer": "Unknown"}, by_name, by_label),
			"",
		)

	def test_pick_brand_unloco_prefers_live_destination(self):
		code = pick_brand_unloco(
			[
				{"job_status": "Draft", "destination_port": "SGSIN", "origin_port": "NLRTM"},
				{"job_status": "In Progress", "destination_port": "USNYC", "origin_port": "GBLON"},
			],
			[{"destination_port": "JPTYO"}],
		)
		self.assertEqual(code, "USNYC")

	def test_markers_skip_missing_coords_and_paint_overdue_red(self):
		rows = [
			{
				"name": "ROLEX",
				"brand_name": "Rolex",
				"flags": classify_brand(
					[{"docstatus": 0}],
					[{"job_status": "In Progress", "sla_status": "Breached"}],
				),
			},
			{
				"name": "CARTIER",
				"brand_name": "Cartier",
				"flags": classify_brand([{"docstatus": 0}], []),
			},
			{
				"name": "IDLE",
				"brand_name": "Idle",
				"flags": classify_brand([], []),
			},
		]
		markers, skipped = build_brand_markers(
			rows,
			unloco_by_brand={"ROLEX": "USNYC", "CARTIER": "FRCDG", "IDLE": ""},
			coords_by_unloco={
				"USNYC": {"lat": 40.7, "lon": -74.0},
				"FRCDG": {"lat": 49.0, "lon": 2.5},
			},
		)
		self.assertEqual(len(markers), 2)
		self.assertEqual(skipped, 1)
		by_lat = {round(m["lat"], 1): m for m in markers}
		self.assertEqual(by_lat[40.7]["severity"], "overdue")
		self.assertEqual(by_lat[40.7]["projects"][0]["brand_name"], "Rolex")
		self.assertEqual(by_lat[49.0]["severity"], "active")

	def test_alerts_prepend_brand_then_jobs(self):
		brands = [
			{
				"name": "ROLEX",
				"brand_name": "Rolex",
				"flags": classify_brand(
					[],
					[{"job_status": "In Progress", "sla_status": "Breached"}],
				),
			}
		]
		jobs = [
			{
				"name": "AIR-1",
				"doctype": "Air Shipment",
				"job_status": "In Progress",
				"sla_status": "At Risk",
				"hv_brand": "ROLEX",
			}
		]
		summary, items = merge_alert_items(brand_alerts(brands), sla_alerts(jobs))
		self.assertGreaterEqual(summary["danger"], 1)
		self.assertGreaterEqual(summary["warning"], 1)
		self.assertEqual(items[0]["doctype"], "HV Brands")
		self.assertEqual(items[1]["doctype"], "Air Shipment")

	def test_brand_work_rows_and_user_workload(self):
		overdue = classify_brand(
			[],
			[{"job_status": "Submitted", "sla_status": "Breached", "owner": "u1"}],
		)
		idle = classify_brand([], [])
		brand_rows = [
			{"name": "ROLEX", "brand_name": "Rolex", "flags": overdue},
			{"name": "IDLE", "brand_name": "Idle", "flags": idle},
		]
		jobs_by = {
			"ROLEX": [{"owner": "u1", "job_status": "Submitted", "sla_status": "Breached"}],
		}
		labels = {"u1": "Alice"}
		rows, truncated = brand_work_rows(brand_rows, {}, jobs_by, labels)
		self.assertEqual(truncated, 0)
		self.assertEqual(rows[0]["name"], "ROLEX")
		self.assertEqual(rows[0]["severity"], "overdue")
		self.assertEqual(rows[0]["owner_label"], "Alice")
		self.assertEqual(rows[1]["severity"], "idle")
		self.assertEqual(attention_rows(rows)[0]["name"], "ROLEX")

		wl = hv_user_workload(
			[{"owner": "u1", "hv_brand": "ROLEX"}],
			[
				{
					"owner": "u1",
					"hv_brand": "ROLEX",
					"job_status": "Submitted",
					"sla_status": "Breached",
				}
			],
			labels,
		)
		self.assertEqual(wl[0]["label"], "Alice")
		self.assertEqual(wl[0]["brand_count"], 1)
		self.assertEqual(wl[0]["quotes"], 1)
		self.assertEqual(wl[0]["sla_breached"], 1)

		unas = unassigned_work_rows(
			[
				{
					"name": "AIR-9",
					"doctype": "Air Shipment",
					"job_status": "In Progress",
					"sla_status": "At Risk",
					"owner": "u1",
				}
			],
			labels,
		)
		self.assertEqual(unas[0]["name"], "AIR-9")
		self.assertEqual(unas[0]["owner_label"], "Alice")
		self.assertEqual(
			job_mix_counts([], [{"doctype": "Air Shipment"}, {"doctype": "Sea Shipment"}]),
			{"quotes": 0, "air": 1, "sea": 1, "transport": 0},
		)
