# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

import json

import frappe
from frappe.tests import UnitTestCase

from logistics.special_projects.special_project_packages import (
	apply_shipment_lines_to_target,
	build_receipts_from_freight_shipment,
	build_receipts_from_project_doc,
	build_receipts_from_transport_job,
	build_receipts_from_transport_order,
	copy_always_along_packages_to_target,
	post_site_receipts_from_freight_shipment,
	post_site_receipts_from_project_doc,
	resolve_special_project_from_project,
	seed_packages_from_sales_quote,
	sync_package_delivery_balances,
	_resolve_sp_package_for_operational_line,
)
from logistics.special_projects.doctype.special_project.special_project import (
	_packages_summary_per_stage_delivered,
)


class TestPackageDeliveryBalances(UnitTestCase):
	def test_balance_two_deliveries_two_jobs(self):
		sp = frappe._dict(
			packages=[
				frappe._dict(
					idx=1,
					warehouse_item="WI-A",
					qty_required=1000,
					description="",
				),
			],
			deliveries=[
				frappe._dict(
					idx=1,
					package_row=1,
					warehouse_item="WI-A",
					qty_received=300,
					status="Posted",
					source_job_type="Transport Order",
					source_job_no="TRO-001",
				),
				frappe._dict(
					idx=2,
					package_row=1,
					warehouse_item="WI-A",
					qty_received=200,
					status="Posted",
					source_job_type="Transport Order",
					source_job_no="TRO-002",
				),
			],
		)
		sync_package_delivery_balances(sp)
		pkg = sp.packages[0]
		self.assertEqual(pkg.qty_on_site, 500)
		self.assertEqual(pkg.qty_short, 500)

	def test_cancelled_delivery_excluded(self):
		sp = frappe._dict(
			packages=[frappe._dict(idx=1, warehouse_item="WI-B", qty_required=100)],
			deliveries=[
				frappe._dict(
					idx=1,
					package_row=1,
					warehouse_item="WI-B",
					qty_received=40,
					status="Posted",
				),
				frappe._dict(
					idx=2,
					package_row=1,
					warehouse_item="WI-B",
					qty_received=60,
					status="Cancelled",
				),
			],
		)
		sync_package_delivery_balances(sp)
		self.assertEqual(sp.packages[0].qty_on_site, 40)
		self.assertEqual(sp.packages[0].qty_short, 60)

	def test_balance_skips_always_along(self):
		sp = frappe._dict(
			packages=[
				frappe._dict(
					idx=1,
					warehouse_item="WI-TOOLKIT",
					qty_required=1,
					include_on_create=1,
				),
			],
			deliveries=[
				frappe._dict(
					idx=1,
					warehouse_item="WI-TOOLKIT",
					qty_received=5,
					status="Posted",
				),
			],
		)
		sync_package_delivery_balances(sp)
		self.assertEqual(sp.packages[0].qty_on_site, 0)
		self.assertEqual(sp.packages[0].qty_short, 0)


class TestPackagesFunnelPerStage(UnitTestCase):
	"""Per-Lifecycle-Stage funnel aggregation used by the Fulfillment summary HTML."""

	def _stages(self):
		return [
			{"name": "Pre-Show", "sort_order": 1, "is_closed": 0, "description": ""},
			{"name": "Logistics", "sort_order": 2, "is_closed": 0, "description": ""},
			{"name": "On-Site", "sort_order": 3, "is_closed": 0, "description": ""},
			{"name": "Post-Show", "sort_order": 4, "is_closed": 0, "description": ""},
			{"name": "Closed", "sort_order": 5, "is_closed": 1, "description": ""},
		]

	def test_groups_qty_by_stage_per_package(self):
		sp = frappe._dict(
			packages=[
				frappe._dict(idx=1, warehouse_item="WI-A", qty_required=10),
				frappe._dict(idx=2, warehouse_item="WI-B", qty_required=20),
			],
			deliveries=[
				frappe._dict(
					package_row=1, warehouse_item="WI-A",
					qty_received=10, status="Posted", lifecycle_stage="Logistics",
				),
				frappe._dict(
					package_row=1, warehouse_item="WI-A",
					qty_received=8, status="Posted", lifecycle_stage="On-Site",
				),
				frappe._dict(
					package_row=2, warehouse_item="WI-B",
					qty_received=15, status="Posted", lifecycle_stage="Logistics",
				),
			],
		)
		stages = self._stages()
		out = _packages_summary_per_stage_delivered(sp, sp.packages, stages)
		# Package A: Pre-Show=0, Logistics=10, On-Site=8, Post-Show=0, Closed=0
		self.assertEqual(out[0], [0.0, 10.0, 8.0, 0.0, 0.0])
		# Package B: Pre-Show=0, Logistics=15, rest 0
		self.assertEqual(out[1], [0.0, 15.0, 0.0, 0.0, 0.0])

	def test_cancelled_deliveries_excluded_from_stage_funnel(self):
		sp = frappe._dict(
			packages=[frappe._dict(idx=1, warehouse_item="WI-A", qty_required=10)],
			deliveries=[
				frappe._dict(
					package_row=1, warehouse_item="WI-A",
					qty_received=10, status="Posted", lifecycle_stage="Logistics",
				),
				frappe._dict(
					package_row=1, warehouse_item="WI-A",
					qty_received=4, status="Cancelled", lifecycle_stage="Logistics",
				),
			],
		)
		out = _packages_summary_per_stage_delivered(sp, sp.packages, self._stages())
		self.assertEqual(out[0][1], 10.0)

	def test_always_along_rows_are_skipped_in_funnel(self):
		sp = frappe._dict(
			packages=[
				frappe._dict(idx=1, warehouse_item="WI-AA", qty_required=1, include_on_create=1),
				frappe._dict(idx=2, warehouse_item="WI-A", qty_required=10),
			],
			deliveries=[
				frappe._dict(
					package_row=1, warehouse_item="WI-AA",
					qty_received=99, status="Posted", lifecycle_stage="Logistics",
				),
				frappe._dict(
					package_row=2, warehouse_item="WI-A",
					qty_received=4, status="Posted", lifecycle_stage="On-Site",
				),
			],
		)
		out = _packages_summary_per_stage_delivered(sp, sp.packages, self._stages())
		# AA row stays zero across all stages.
		self.assertEqual(out[0], [0.0, 0.0, 0.0, 0.0, 0.0])
		self.assertEqual(out[1][2], 4.0)

	def test_unknown_stage_is_ignored(self):
		sp = frappe._dict(
			packages=[frappe._dict(idx=1, warehouse_item="WI-A", qty_required=10)],
			deliveries=[
				frappe._dict(
					package_row=1, warehouse_item="WI-A",
					qty_received=10, status="Posted", lifecycle_stage="Not A Real Stage",
				),
			],
		)
		out = _packages_summary_per_stage_delivered(sp, sp.packages, self._stages())
		self.assertEqual(out[0], [0.0, 0.0, 0.0, 0.0, 0.0])


class TestSeedFromSalesQuote(UnitTestCase):
	def test_seed_project_products(self):
		sp = frappe._dict(packages=[], customer="CUST-TEST")
		sq = frappe._dict(
			project_products=[
				frappe._dict(item="ITEM-X", quantity=10, uom="Nos", description="Widget"),
				frappe._dict(item="ITEM-Y", quantity=5, description="Gadget"),
			]
		)
		n = seed_packages_from_sales_quote(sp, sq)
		self.assertEqual(n, 2)
		self.assertEqual(len(sp.packages), 2)
		self.assertEqual(sp.packages[0].qty_required, 10)


class TestShipmentLinesAndCargo(UnitTestCase):
	def test_apply_shipment_lines_to_transport_order(self):
		sp = frappe._dict(
			packages=[
				frappe._dict(
					idx=1,
					warehouse_item="WI-A",
					commodity="COMM-A",
					description="Item A",
					uom="Nos",
					qty_required=100,
					qty_short=100,
				),
			],
		)
		tro = frappe.new_doc("Transport Order")
		lines = json.dumps(
			[
				{
					"package_row": 1,
					"warehouse_item": "WI-A",
					"commodity": "COMM-A",
					"qty": 50,
					"uom": "Nos",
				}
			]
		)
		n = apply_shipment_lines_to_target(sp, tro, lines)
		self.assertEqual(n, 1)
		self.assertEqual(len(tro.packages), 1)
		self.assertEqual(tro.packages[0].quantity, 50)
		self.assertEqual(tro.packages[0].warehouse_item, "WI-A")
		self.assertEqual(tro.packages[0].commodity, "COMM-A")
		if tro.packages[0].meta.get_field("package_row"):
			self.assertEqual(tro.packages[0].package_row, 1)

	def test_apply_shipment_lines_carries_dimensions(self):
		sp = frappe._dict(
			packages=[
				frappe._dict(
					idx=1,
					warehouse_item="WI-A",
					commodity="COMM-A",
					description="Item A",
					uom="Nos",
					qty_required=100,
					qty_short=100,
					length=1.2,
					width=0.8,
					height=0.6,
					dimension_uom="m",
					weight=120,
					weight_uom="kg",
					contains_dangerous_goods=1,
				),
			],
		)
		tro = frappe.new_doc("Transport Order")
		lines = json.dumps(
			[
				{
					"package_row": 1,
					"warehouse_item": "WI-A",
					"qty": 50,
					"uom": "Nos",
				}
			]
		)
		apply_shipment_lines_to_target(sp, tro, lines)
		self.assertEqual(len(tro.packages), 1)
		pkg = tro.packages[0]
		self.assertEqual(pkg.quantity, 50)
		if pkg.meta.get_field("length"):
			self.assertEqual(pkg.length, 1.2)
		if pkg.meta.get_field("weight"):
			self.assertEqual(pkg.weight, 120)
		if pkg.meta.get_field("contains_dangerous_goods"):
			self.assertEqual(pkg.contains_dangerous_goods, 1)

	def test_copy_always_along_appends_packages(self):
		sp = frappe._dict(
			packages=[
				frappe._dict(
					idx=1,
					warehouse_item="WI-REQ",
					qty_required=100,
					include_on_create=0,
				),
				frappe._dict(
					idx=2,
					description="Tool kit",
					qty_required=1,
					no_of_packs=1,
					include_on_create=1,
					length=0.6,
					width=0.4,
					height=0.4,
					weight=35,
				),
			],
		)
		tro = frappe.new_doc("Transport Order")
		n = copy_always_along_packages_to_target(sp, tro)
		self.assertEqual(n, 1)
		self.assertEqual(len(tro.packages), 1)
		self.assertEqual(tro.packages[0].description, "Tool kit")


class TestPackageRowIdentity(UnitTestCase):
	def test_sync_balances_isolated_for_duplicate_warehouse_items(self):
		sp = frappe._dict(
			packages=[
				frappe._dict(idx=1, warehouse_item="WI-A", qty_required=100),
				frappe._dict(idx=2, warehouse_item="WI-A", qty_required=200),
			],
			deliveries=[
				frappe._dict(
					idx=1,
					package_row=2,
					warehouse_item="WI-A",
					qty_received=50,
					status="Posted",
				),
			],
		)
		sync_package_delivery_balances(sp)
		self.assertEqual(sp.packages[0].qty_on_site, 0)
		self.assertEqual(sp.packages[0].qty_short, 100)
		self.assertEqual(sp.packages[1].qty_on_site, 50)
		self.assertEqual(sp.packages[1].qty_short, 150)

	def test_resolve_explicit_package_row(self):
		sp = frappe._dict(
			packages=[
				frappe._dict(idx=1, warehouse_item="WI-A", qty_required=100),
				frappe._dict(idx=2, warehouse_item="WI-A", qty_required=200),
			],
		)
		op_line = frappe._dict(package_row=2, warehouse_item="WI-A", quantity=10)
		mat, row = _resolve_sp_package_for_operational_line(sp, op_line)
		self.assertEqual(row, 2)
		self.assertEqual(getattr(mat, "idx", None), 2)

	def test_resolve_ambiguous_without_package_row_throws(self):
		sp = frappe._dict(
			packages=[
				frappe._dict(idx=1, warehouse_item="WI-A", qty_required=100),
				frappe._dict(idx=2, warehouse_item="WI-A", qty_required=200),
			],
		)
		op_line = frappe._dict(warehouse_item="WI-A", quantity=10)
		with self.assertRaises(frappe.ValidationError):
			_resolve_sp_package_for_operational_line(sp, op_line)

	def test_resolve_single_legacy_match_without_package_row(self):
		sp = frappe._dict(
			packages=[
				frappe._dict(idx=1, warehouse_item="WI-A", qty_required=100),
			],
		)
		op_line = frappe._dict(warehouse_item="WI-A", quantity=10)
		mat, row = _resolve_sp_package_for_operational_line(sp, op_line)
		self.assertEqual(row, 1)
		self.assertEqual(getattr(mat, "idx", None), 1)


class TestTransportJobReceiptPosting(UnitTestCase):
	def test_build_receipts_skips_zero_qty(self):
		sp_name = "SP-TEST-RECEIPT"
		if not frappe.db.exists("Special Project", sp_name):
			return
		tj = frappe._dict(
			doctype="Transport Job",
			name="TJ-TEST-RECEIPT",
			project=sp_name,
			container_no="CONT-99",
			packages=[
				frappe._dict(idx=1, quantity=25, warehouse_item="WI-TEST", description="Mat"),
				frappe._dict(idx=2, quantity=0),
			],
		)
		rows = build_receipts_from_transport_job(tj)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]["qty_received"], 25)
		self.assertEqual(rows[0]["warehouse_item"], "WI-TEST")
		self.assertEqual(rows[0]["source_job_type"], "Transport Job")
		options = frappe.get_meta("Special Project Site Receipt").get_options("source_job_type")
		self.assertIn("Transport Job", options.split("\n"))

	def test_stage_from_lifecycle_job_matches_execution_job_no(self):
		from logistics.special_projects.special_project_packages import _stage_from_lifecycle_job

		sp = frappe._dict(
			lifecycle_jobs=[
				frappe._dict(
					job_type="Transport Order",
					order_no="TRO-001",
					job_no="TRJ-001",
					lifecycle_stage="Delivery to site",
				),
			],
		)
		self.assertEqual(
			_stage_from_lifecycle_job(sp, "Transport Job", "TRJ-001"),
			"Delivery to site",
		)
		self.assertEqual(
			_stage_from_lifecycle_job(sp, "Transport Order", "TRO-001"),
			"Delivery to site",
		)

	def test_transport_job_submit_hook_registered(self):
		from logistics.hooks import doc_events

		submit = doc_events.get("Transport Job", {}).get("on_submit")
		if isinstance(submit, list):
			self.assertIn(
				"logistics.special_projects.special_project_packages.on_transport_job_submit",
				submit,
			)
		else:
			self.assertEqual(
				submit,
				"logistics.special_projects.special_project_packages.on_transport_job_submit",
			)


class TestResolveSpecialProject(UnitTestCase):
	def test_resolve_by_name(self):
		sp_name = frappe.db.get_value("Special Project", {}, "name")
		if not sp_name:
			return
		self.assertEqual(resolve_special_project_from_project(sp_name), sp_name)


class TestPlanningDocsDoNotPostReceipts(UnitTestCase):
	"""Delivered must not move on booking/order submit — only execution jobs/shipments."""

	def _existing_sp_name(self) -> str | None:
		return frappe.db.get_value("Special Project", {}, "name")

	def test_project_order_build_receipts_returns_empty(self):
		sp_name = self._existing_sp_name()
		if not sp_name:
			return
		doc = frappe._dict(
			doctype="Project Order",
			name="SPOR-TEST-NO-POST",
			special_project=sp_name,
			materials_received=[
				frappe._dict(idx=1, qty_received=99, warehouse_item="WI-TEST"),
			],
		)
		self.assertEqual(build_receipts_from_project_doc(doc), [])
		self.assertEqual(post_site_receipts_from_project_doc(doc), 0)

	def test_air_booking_build_receipts_returns_empty(self):
		sp_name = self._existing_sp_name()
		if not sp_name:
			return
		doc = frappe._dict(
			doctype="Air Booking",
			name="ABK-TEST-NO-POST",
			project=sp_name,
			packages=[
				frappe._dict(idx=1, no_of_packs=50, warehouse_item="WI-AIR"),
			],
		)
		self.assertEqual(build_receipts_from_freight_shipment(doc), [])
		self.assertEqual(post_site_receipts_from_freight_shipment(doc), 0)

	def test_sea_booking_build_receipts_returns_empty(self):
		sp_name = self._existing_sp_name()
		if not sp_name:
			return
		doc = frappe._dict(
			doctype="Sea Booking",
			name="SBK-TEST-NO-POST",
			project=sp_name,
			packages=[
				frappe._dict(idx=1, no_of_packs=30, warehouse_item="WI-SEA"),
			],
		)
		self.assertEqual(build_receipts_from_freight_shipment(doc), [])

	def test_transport_order_build_receipts_returns_empty(self):
		sp_name = self._existing_sp_name()
		if not sp_name:
			return
		doc = frappe._dict(
			doctype="Transport Order",
			name="TRO-TEST-NO-POST",
			project=sp_name,
			packages=[
				frappe._dict(idx=1, quantity=50, warehouse_item="WI-ROAD"),
			],
		)
		self.assertEqual(build_receipts_from_transport_order(doc), [])


class TestProjectDocReceiptPosting(UnitTestCase):
	"""Coverage for build_receipts_from_project_doc (Project Job only)."""

	def _existing_sp_name(self) -> str | None:
		return frappe.db.get_value("Special Project", {}, "name")

	def _first_tracked_package(self, sp_name: str):
		sp_doc = frappe.get_doc("Special Project", sp_name)
		for pkg in sp_doc.packages or []:
			if not getattr(pkg, "include_on_create", None):
				return pkg
		return None

	def test_project_job_build_receipts_basic(self):
		sp_name = self._existing_sp_name()
		if not sp_name:
			return
		pkg = self._first_tracked_package(sp_name)
		if not pkg:
			return
		doc = frappe._dict(
			doctype="Project Job",
			name="SPJ-TEST-RECEIPT",
			special_project=sp_name,
			materials_received=[
				frappe._dict(
					idx=1,
					qty_received=30,
					package_row=pkg.idx,
					warehouse_item=pkg.warehouse_item,
					description=getattr(pkg, "description", None) or "Mat",
				),
				frappe._dict(idx=2, qty_received=0, warehouse_item="WI-ZERO"),
			],
		)
		rows = build_receipts_from_project_doc(doc)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]["qty_received"], 30)
		self.assertEqual(rows[0]["package_row"], pkg.idx)
		self.assertEqual(rows[0]["warehouse_item"], pkg.warehouse_item)
		self.assertEqual(rows[0]["source_job_type"], "Project Job")
		self.assertEqual(rows[0]["source_doctype"], "Project Job")
		self.assertEqual(rows[0]["source_name"], "SPJ-TEST-RECEIPT")
		self.assertEqual(rows[0]["source_package_idx"], 1)

	def test_project_doc_without_special_project_returns_empty(self):
		doc = frappe._dict(
			doctype="Project Job",
			name="SPJ-MISSING-SP",
			special_project="",
			materials_received=[frappe._dict(idx=1, qty_received=5)],
		)
		self.assertEqual(build_receipts_from_project_doc(doc), [])


class TestFreightShipmentReceiptPosting(UnitTestCase):
	"""Air/Sea Shipment submit -> SP delivery receipts."""

	def _existing_sp_name(self) -> str | None:
		return frappe.db.get_value("Special Project", {}, "name")

	def _first_tracked_package(self, sp_name: str):
		sp_doc = frappe.get_doc("Special Project", sp_name)
		for pkg in sp_doc.packages or []:
			if not getattr(pkg, "include_on_create", None):
				return pkg
		return None

	def test_air_shipment_build_receipts_reads_goods_description_and_packs(self):
		sp_name = self._existing_sp_name()
		if not sp_name:
			return
		pkg = self._first_tracked_package(sp_name)
		if not pkg:
			return
		goods_description = getattr(pkg, "description", None) or "Tarpaulin bundles"
		doc = frappe._dict(
			doctype="Air Shipment",
			name="ASP-TEST-RECEIPT",
			project=sp_name,
			air_booking="ABK-TEST",
			packages=[
				frappe._dict(
					idx=1,
					package_row=pkg.idx,
					no_of_packs=40,
					warehouse_item=pkg.warehouse_item,
					commodity=getattr(pkg, "commodity", None),
					goods_description=goods_description,
					uom=getattr(pkg, "uom", None) or "Piece",
				),
				frappe._dict(idx=2, no_of_packs=0, warehouse_item="WI-ZERO"),
			],
		)
		rows = build_receipts_from_freight_shipment(doc)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]["qty_received"], 40)
		self.assertEqual(rows[0]["warehouse_item"], pkg.warehouse_item)
		self.assertEqual(rows[0]["package_row"], pkg.idx)
		self.assertEqual(rows[0]["description"], goods_description)
		self.assertEqual(rows[0]["source_doctype"], "Air Shipment")
		self.assertEqual(rows[0]["source_name"], "ASP-TEST-RECEIPT")
		self.assertEqual(rows[0]["source_package_idx"], 1)

	def test_freight_shipment_without_project_returns_empty(self):
		doc = frappe._dict(
			doctype="Air Shipment",
			name="ASP-NO-PROJECT",
			project="",
			air_booking="ABK-X",
			packages=[
				frappe._dict(idx=1, no_of_packs=10, warehouse_item="WI-X"),
			],
		)
		self.assertEqual(build_receipts_from_freight_shipment(doc), [])

	def test_sea_shipment_reuses_freight_builder(self):
		sp_name = self._existing_sp_name()
		if not sp_name:
			return
		pkg = self._first_tracked_package(sp_name)
		if not pkg:
			return
		goods_description = getattr(pkg, "description", None) or "Pallet of bricks"
		doc = frappe._dict(
			doctype="Sea Shipment",
			name="SSP-TEST-RECEIPT",
			project=sp_name,
			sea_booking="SBK-TEST",
			packages=[
				frappe._dict(
					idx=1,
					package_row=pkg.idx,
					no_of_packs=12,
					warehouse_item=pkg.warehouse_item,
					goods_description=goods_description,
				),
			],
		)
		rows = build_receipts_from_freight_shipment(doc)
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0]["source_doctype"], "Sea Shipment")
		self.assertEqual(rows[0]["package_row"], pkg.idx)
		self.assertEqual(rows[0]["description"], goods_description)
