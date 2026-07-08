# Copyright (c) 2026, www.agilasoft.com and Contributors
# See license.txt

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, flt, today
from unittest.mock import patch

from logistics.mice.doctype.mice_project.mice_project import (
	_aggregate_job_status_counts,
	_batch_unloco_table_labels,
	_build_exhibit_job_status_tab_html,
	_build_operational_jobs_card_html,
	_fetch_transport_job_endpoints,
	get_cost_allocation_target_basis,
	get_linkable_dockets_for_exhibit,
	get_sales_quote_defaults_from_exhibit,
	link_dockets_to_exhibit,
)
from logistics.mice.mice_project_lifecycle import LIFECYCLE_STAGES, get_standard_exhibit_activities


class TestShow(IntegrationTestCase):
	def _test_customer(self):
		return frappe.db.get_value("Customer", {}, "name")

	def _test_organizer(self, name_hint="Test Organizer"):
		"""Return (or create) a MICE Organizer linked to an arbitrary Customer."""
		customer = self._test_customer()
		if not customer:
			return None
		existing = frappe.db.get_value(
			"MICE Organizer", {"organizer_name": name_hint}, "name"
		)
		if existing:
			return existing
		doc = frappe.new_doc("MICE Organizer")
		doc.organizer_name = name_hint
		doc.organizer_type = "Company"
		doc.customer = customer
		doc.insert(ignore_permissions=True)
		return doc.name

	def _minimal_exhibit(self, project_name="Test Exhibit"):
		organizer = self._test_organizer()
		if not organizer:
			self.skipTest("No Customer in system (organizer needs a backing Customer)")
		doc = frappe.new_doc("MICE Project")
		doc.project_name = project_name
		doc.organizer = organizer
		doc.show_open_date = today()
		doc.show_close_date = add_days(today(), 3)
		doc.insert(ignore_permissions=True)
		return doc

	def _minimal_docket(self, exhibit, exhibitor=None):
		if not frappe.db.exists("DocType", "Docket"):
			self.skipTest("Docket DocType not installed")
		exhibitor = exhibitor or self._test_customer()
		if not exhibitor:
			self.skipTest("No Customer in system")
		dk = frappe.new_doc("Docket")
		dk.exhibit = exhibit
		dk.exhibitor = exhibitor
		dk.flags.ignore_mandatory = True
		dk.insert(ignore_permissions=True)
		return dk

	def _default_currency(self):
		company = frappe.defaults.get_defaults().get("company")
		if company:
			currency = frappe.db.get_value("Company", company, "default_currency")
			if currency:
				return currency
		return frappe.db.get_value("Currency", {"enabled": 1}, "name")

	def _append_consolidation_charge(
		self, doc, unit_rate=100, quantity=1, *, zero_total=False, allocation_method=None
	):
		currency = self._default_currency()
		if not currency:
			self.skipTest("No currency in system")
		row_data = {
			"charge_type": "Cost",
			"charge_category": "Other",
			"revenue_calculation_method": "Per Unit",
			"unit_rate": unit_rate,
			"quantity": quantity,
			"currency": currency,
		}
		if allocation_method is not None:
			row_data["allocation_method"] = allocation_method
		row = doc.append("consolidation_charges", row_data)
		if zero_total:
			row.total_amount = 0
		return row

	def _second_customer(self):
		first = self._test_customer()
		other = frappe.db.get_value("Customer", {"name": ["!=", first]}, "name") if first else None
		return other or first

	def _docket_with_packages(self, exhibit, exhibitor=None, *, weight=0, volume=0):
		dk = self._minimal_docket(exhibit, exhibitor)
		dk.append("packages", {"weight": weight, "volume": volume})
		dk.flags.ignore_mandatory = True
		dk.save(ignore_permissions=True)
		return dk

	def test_allocate_costs_equal_split_across_dockets(self):
		if not frappe.db.exists("DocType", "MICE Project"):
			self.skipTest("MICE Project DocType not installed")
		project = self._minimal_exhibit("Test Allocate Equal")
		dk1 = self._minimal_docket(project.name, self._test_customer())
		dk2 = self._minimal_docket(project.name, self._second_customer())
		try:
			doc = frappe.get_doc("MICE Project", project.name)
			doc.cost_allocation_target = "Dockets"
			doc.cost_allocation_basis = "Equal"
			self._append_consolidation_charge(doc, unit_rate=200, quantity=1)
			doc.save(ignore_permissions=True)

			result = doc.allocate_costs(allocation_basis="Equal", target_type="Dockets")
			doc.reload()

			self.assertEqual(result["targets_loaded"], 2)
			self.assertEqual(flt(doc.total_consolidation_charges), 200.0)
			self.assertEqual(flt(doc.total_allocated_amount), 200.0)
			amounts = sorted(flt(r.allocated_amount) for r in doc.cost_allocations)
			self.assertEqual(amounts, [100.0, 100.0])
		finally:
			dk2.delete(ignore_permissions=True)
			dk1.delete(ignore_permissions=True)
			project.delete(ignore_permissions=True)

	def test_allocate_costs_recalculates_unsaved_charge_amounts(self):
		"""Regression #987: charge total_amount must be recomputed before allocation."""
		if not frappe.db.exists("DocType", "MICE Project"):
			self.skipTest("MICE Project DocType not installed")
		project = self._minimal_exhibit("Test Allocate Unsaved Charge")
		dk1 = self._minimal_docket(project.name, self._test_customer())
		dk2 = self._minimal_docket(project.name, self._second_customer())
		try:
			doc = frappe.get_doc("MICE Project", project.name)
			doc.cost_allocation_target = "Dockets"
			doc.cost_allocation_basis = "Equal"
			self._append_consolidation_charge(doc, unit_rate=150, quantity=2, zero_total=True)
			self.assertEqual(flt(doc.consolidation_charges[0].total_amount), 0)

			result = doc.allocate_costs(allocation_basis="Equal", target_type="Dockets")
			doc.reload()

			self.assertEqual(result["targets_loaded"], 2)
			self.assertEqual(flt(doc.total_consolidation_charges), 300.0)
			self.assertEqual(flt(doc.total_allocated_amount), 300.0)
			self.assertTrue(all(flt(r.allocated_amount) > 0 for r in doc.cost_allocations))
		finally:
			dk2.delete(ignore_permissions=True)
			dk1.delete(ignore_permissions=True)
			project.delete(ignore_permissions=True)

	def test_allocate_costs_custom_requires_percentages(self):
		if not frappe.db.exists("DocType", "MICE Project"):
			self.skipTest("MICE Project DocType not installed")
		project = self._minimal_exhibit("Test Allocate Custom")
		dk = self._minimal_docket(project.name, self._test_customer())
		try:
			doc = frappe.get_doc("MICE Project", project.name)
			doc.cost_allocation_target = "Dockets"
			doc.cost_allocation_basis = "Custom"
			self._append_consolidation_charge(doc, unit_rate=100, quantity=1)
			doc.save(ignore_permissions=True)

			with self.assertRaises(frappe.ValidationError):
				doc.allocate_costs(allocation_basis="Custom", target_type="Dockets")
		finally:
			dk.delete(ignore_permissions=True)
			project.delete(ignore_permissions=True)

	def test_refresh_cost_allocation_targets_populates_docket_basis(self):
		if not frappe.db.exists("DocType", "MICE Project"):
			self.skipTest("MICE Project DocType not installed")
		project = self._minimal_exhibit("Test Refresh Basis")
		dk = self._docket_with_packages(project.name, weight=120, volume=2.5)
		try:
			doc = frappe.get_doc("MICE Project", project.name)
			doc.cost_allocation_target = "Dockets"
			doc.save(ignore_permissions=True)

			result = doc.refresh_cost_allocation_targets(target_type="Docket")
			doc.reload()

			self.assertEqual(result["targets_loaded"], 1)
			row = doc.cost_allocations[0]
			self.assertEqual(row.target, dk.name)
			self.assertEqual(flt(row.weight_basis), 120.0)
			self.assertEqual(flt(row.volume_basis), 2.5)
		finally:
			dk.delete(ignore_permissions=True)
			project.delete(ignore_permissions=True)

	def test_get_cost_allocation_target_basis_for_docket(self):
		if not frappe.db.exists("DocType", "MICE Project"):
			self.skipTest("MICE Project DocType not installed")
		project = self._minimal_exhibit("Test Target Basis API")
		dk = self._docket_with_packages(project.name, weight=80, volume=1.2)
		try:
			result = get_cost_allocation_target_basis("Docket", dk.name)
			self.assertEqual(flt(result["weight_basis"]), 80.0)
			self.assertEqual(flt(result["volume_basis"]), 1.2)
			self.assertTrue(result["target_title"])
		finally:
			dk.delete(ignore_permissions=True)
			project.delete(ignore_permissions=True)

	def test_allocate_costs_weight_based_split_across_dockets(self):
		if not frappe.db.exists("DocType", "MICE Project"):
			self.skipTest("MICE Project DocType not installed")
		project = self._minimal_exhibit("Test Allocate Weight")
		dk1 = self._docket_with_packages(project.name, self._test_customer(), weight=100, volume=0)
		dk2 = self._docket_with_packages(project.name, self._second_customer(), weight=300, volume=0)
		try:
			doc = frappe.get_doc("MICE Project", project.name)
			doc.cost_allocation_target = "Dockets"
			doc.cost_allocation_basis = "Weight-based"
			self._append_consolidation_charge(
				doc, unit_rate=400, quantity=1, allocation_method="Weight-based"
			)
			doc.save(ignore_permissions=True)

			result = doc.allocate_costs(allocation_basis="Weight-based", target_type="Dockets")
			doc.reload()

			self.assertEqual(result["targets_loaded"], 2)
			by_target = {r.target: flt(r.allocated_amount) for r in doc.cost_allocations}
			self.assertEqual(by_target[dk1.name], 100.0)
			self.assertEqual(by_target[dk2.name], 300.0)
		finally:
			dk2.delete(ignore_permissions=True)
			dk1.delete(ignore_permissions=True)
			project.delete(ignore_permissions=True)

	def test_save_with_virtual_dockets_does_not_fail_version(self):
		"""Regression: virtual dockets grid must not break Version diff on save."""
		if not frappe.db.exists("DocType", "MICE Project"):
			self.skipTest("Exhibit DocType not installed")
		doc = self._minimal_exhibit("Test Virtual Dockets Save")
		try:
			doc = frappe.get_doc("MICE Project", doc.name)
			self.assertIsInstance(doc.get("dockets"), list)
			doc.description = (doc.description or "") + " updated"
			doc.save(ignore_permissions=True)
		finally:
			doc.delete(ignore_permissions=True)

	def test_standard_activities_loaded_on_insert(self):
		if not frappe.db.exists("DocType", "MICE Project"):
			self.skipTest("Exhibit DocType not installed")
		organizer = self._test_organizer("Test Org Activities")
		if not organizer:
			self.skipTest("No Customer in system")
		doc = frappe.new_doc("MICE Project")
		doc.project_name = "Test Exhibit Details"
		doc.organizer = organizer
		doc.insert(ignore_permissions=True)
		lifecycle_jobs = [r for r in doc.lifecycle_jobs if r.activity_code]
		self.assertEqual(len(lifecycle_jobs), len(get_standard_exhibit_activities()))
		self.assertEqual(doc.lifecycle_stage, "Pre-Show")
		doc.delete(ignore_permissions=True)

	def test_phase_orders_created_on_approval(self):
		if not frappe.db.exists("DocType", "MICE Project"):
			self.skipTest("Exhibit DocType not installed")
		frappe.db.set_single_value("MICE Settings", "auto_create_phase_orders", 1)
		organizer = self._test_organizer("Test Org Phase Orders")
		if not organizer:
			self.skipTest("No Customer in system")
		doc = frappe.new_doc("MICE Project")
		doc.project_name = "Test Phase Orders"
		doc.organizer = organizer
		doc.insert(ignore_permissions=True)
		doc.status = "Approved"
		doc.save(ignore_permissions=True)
		orders = frappe.get_all(
			"MICE Order",
			filters={"exhibit": doc.name},
			pluck="lifecycle_stage",
		)
		for stage in LIFECYCLE_STAGES[:-1]:
			self.assertIn(stage, orders)
		doc.delete(ignore_permissions=True)

	def test_get_sales_quote_defaults_from_exhibit(self):
		if not frappe.db.exists("DocType", "MICE Project"):
			self.skipTest("Exhibit DocType not installed")
		organizer = self._test_organizer("Test Org SQ Defaults")
		if not organizer:
			self.skipTest("No Customer in system")
		doc = frappe.new_doc("MICE Project")
		doc.project_name = "Test SQ Defaults Exhibit"
		doc.organizer = organizer
		doc.show_open_date = today()
		doc.show_close_date = add_days(today(), 3)
		doc.priority = "High"
		doc.description = "Test exhibit description"
		doc.insert(ignore_permissions=True)
		try:
			defaults = get_sales_quote_defaults_from_exhibit(doc.name, None)
			self.assertEqual(defaults["exhibit"], doc.name)
			self.assertNotIn("customer", defaults)
			self.assertEqual(defaults["main_service"], "MICE")
			self.assertEqual(defaults["quotation_type"], "Project")
			self.assertEqual(defaults["naming_series"], "PQ.#####")
			self.assertEqual(defaults["exhibit_show_open_date"], str(doc.show_open_date))
			self.assertEqual(defaults["exhibit_show_close_date"], str(doc.show_close_date))
			self.assertEqual(defaults["priority"], "High")
			self.assertEqual(defaults["description"], doc.description)
		finally:
			doc.delete(ignore_permissions=True)

	def test_link_dockets_to_exhibit_sets_exhibit_field(self):
		if not frappe.db.exists("DocType", "MICE Project"):
			self.skipTest("Exhibit DocType not installed")
		target = self._minimal_exhibit("Test Link Target")
		source_exhibit = self._minimal_exhibit("Test Link Source")
		# Resolve the target's billing Customer via the linked Organizer (MICE
		# Project no longer carries a customer link directly).
		target_customer = (
			frappe.db.get_value("MICE Organizer", target.organizer, "customer")
			if target.organizer
			else None
		)
		other_exhibitor = (
			frappe.db.get_value("Customer", {"name": ["!=", target_customer]}, "name")
			if target_customer
			else None
		) or target_customer or self._test_customer()
		dk = self._minimal_docket(source_exhibit.name, other_exhibitor)
		try:
			result = link_dockets_to_exhibit(target.name, [dk.name])
			self.assertEqual(len(result["linked"]), 1)
			self.assertEqual(frappe.db.get_value("Docket", dk.name, "exhibit"), target.name)
		finally:
			dk.delete(ignore_permissions=True)
			source_exhibit.delete(ignore_permissions=True)
			target.delete(ignore_permissions=True)

	def test_link_dockets_rejects_duplicate_exhibitor_on_exhibit(self):
		if not frappe.db.exists("DocType", "MICE Project"):
			self.skipTest("Exhibit DocType not installed")
		target = self._minimal_exhibit("Test Dup Exhibitor Target")
		other_exhibit = self._minimal_exhibit("Test Dup Exhibitor Other")
		exhibitor = self._test_customer()
		first = self._minimal_docket(target.name, exhibitor)
		second = self._minimal_docket(other_exhibit.name, exhibitor)
		try:
			result = link_dockets_to_exhibit(target.name, [second.name])
			self.assertEqual(len(result["linked"]), 0)
			self.assertTrue(result["errors"])
		finally:
			second.delete(ignore_permissions=True)
			first.delete(ignore_permissions=True)
			other_exhibit.delete(ignore_permissions=True)
			target.delete(ignore_permissions=True)

	def test_get_linkable_dockets_includes_only_on_exhibit(self):
		if not frappe.db.exists("DocType", "MICE Project"):
			self.skipTest("Exhibit DocType not installed")
		exhibit = self._minimal_exhibit("Test Linkable List")
		other_exhibit = self._minimal_exhibit("Test Linkable Other")
		exhibitor = self._test_customer()
		on_exhibit = self._minimal_docket(exhibit.name, exhibitor)
		other_exhibitor = frappe.db.get_value(
			"Customer", {"name": ["!=", exhibitor]}, "name"
		) or exhibitor
		on_other = self._minimal_docket(other_exhibit.name, other_exhibitor)
		unlinked = frappe.new_doc("Docket")
		unlinked.exhibitor = other_exhibitor
		unlinked.flags.ignore_mandatory = True
		unlinked.insert(ignore_permissions=True)
		try:
			rows = get_linkable_dockets_for_exhibit(exhibit.name)
			names = [r["name"] for r in rows]
			self.assertIn(on_exhibit.name, names)
			self.assertNotIn(on_other.name, names)
			self.assertNotIn(unlinked.name, names)
			for row in rows:
				self.assertEqual(row.get("row_type"), "eligible")
		finally:
			unlinked.delete(ignore_permissions=True)
			on_other.delete(ignore_permissions=True)
			on_exhibit.delete(ignore_permissions=True)
			other_exhibit.delete(ignore_permissions=True)
			exhibit.delete(ignore_permissions=True)

	def test_get_linkable_dockets_respects_exclude_list(self):
		if not frappe.db.exists("DocType", "MICE Project"):
			self.skipTest("Exhibit DocType not installed")
		exhibit = self._minimal_exhibit("Test Linkable Exclude")
		exhibitor = self._test_customer()
		dk = self._minimal_docket(exhibit.name, exhibitor)
		try:
			rows = get_linkable_dockets_for_exhibit(
				exhibit.name, exclude_dockets=[dk.name]
			)
			names = [r["name"] for r in rows]
			self.assertNotIn(dk.name, names)
			rows_all = get_linkable_dockets_for_exhibit(exhibit.name)
			self.assertIn(dk.name, [r["name"] for r in rows_all])
		finally:
			dk.delete(ignore_permissions=True)
			exhibit.delete(ignore_permissions=True)

	def test_mice_project_has_sales_quote_field(self):
		self.assertTrue(frappe.get_meta("MICE Project").has_field("sales_quote"))

	def _test_logistics_milestone(self, code="TEST-MS-DASH"):
		existing = frappe.db.get_value("Logistics Milestone", {"code": code}, "name")
		if existing:
			return existing
		doc = frappe.new_doc("Logistics Milestone")
		doc.code = code
		doc.description = "Dashboard test milestone"
		doc.insert(ignore_permissions=True)
		return doc.name

	def test_get_dashboard_html_renders_without_error(self):
		from logistics.mice.doctype.mice_project.mice_project import get_dashboard_html

		exhibit = self._minimal_exhibit("Dashboard Test Exhibit")
		try:
			html = get_dashboard_html(exhibit.name)
			self.assertNotIn("Error loading dashboard", html)
			self.assertIn("log-ab-dash", html)
			self.assertIn("Job Status", html)
			self.assertIn("ab-tab-panel-job_status", html)
			self.assertNotIn("Open the Milestones tab to manage milestone status.", html)
		finally:
			exhibit.delete(ignore_permissions=True)

	def test_get_dashboard_html_renders_milestone_grid(self):
		from logistics.mice.doctype.mice_project.mice_project import get_dashboard_html

		exhibit = self._minimal_exhibit("Dashboard Milestones Exhibit")
		milestone = self._test_logistics_milestone()
		exhibit.append("milestones", {"milestone": milestone, "status": "Planned"})
		exhibit.save(ignore_permissions=True)
		try:
			html = get_dashboard_html(exhibit.name)
			self.assertIn("log-ab-jc-grid", html)
			self.assertIn("Operational milestones", html)
			self.assertNotIn("Open the Milestones tab to manage milestone status.", html)
		finally:
			exhibit.delete(ignore_permissions=True)

	def test_aggregate_job_status_counts_orders_and_groups(self):
		counts = _aggregate_job_status_counts(
			["Draft", "In Progress", "In Progress", "Completed", "", None]
		)
		self.assertEqual(list(counts.keys()), ["Draft", "In Progress", "Completed"])
		self.assertEqual(counts["Draft"], 3)
		self.assertEqual(counts["In Progress"], 2)
		self.assertEqual(counts["Completed"], 1)

	def test_build_exhibit_job_status_tab_html_empty_dockets(self):
		html = _build_exhibit_job_status_tab_html("NONEXISTENT-EXHIBIT", docket_rows=[])
		self.assertIn("No dockets linked to this exhibit yet.", html)

	def test_batch_unloco_table_labels_formats_city_and_country_code(self):
		code = "TEST-UNLOCO-MICE-DASH"
		if not frappe.db.exists("UNLOCO", code):
			doc = frappe.new_doc("UNLOCO")
			doc.unlocode = code
			doc.location_name = "Test Port"
			doc.city = "Shanghai"
			doc.country_code = "CN"
			doc.is_active = 1
			doc.insert(ignore_permissions=True)
		else:
			frappe.db.set_value(
				"UNLOCO",
				code,
				{"city": "Shanghai", "country_code": "CN", "location_name": "Test Port"},
				update_modified=False,
			)
		try:
			labels = _batch_unloco_table_labels([code, ""])
			self.assertEqual(labels[code], "Shanghai, CN")
		finally:
			if frappe.db.exists("UNLOCO", code):
				frappe.delete_doc("UNLOCO", code, force=1, ignore_permissions=True)

	def test_build_operational_jobs_card_html_renders_table_and_badges(self):
		jobs = [
			{
				"job_type": "Sea Shipment",
				"name": "SF000000384",
				"service_label": "Sea",
				"job_status": "Draft",
				"origin_code": "CNSHA",
				"destination_code": "SGSIN",
				"origin_kind": "unloco",
				"destination_kind": "unloco",
				"modified": "2025-05-12 10:00:00",
			},
			{
				"job_type": "Sea Shipment",
				"name": "SF000000386",
				"service_label": "Sea",
				"job_status": "Submitted",
				"origin_code": "JPTYO",
				"destination_code": "SGSIN",
				"origin_kind": "unloco",
				"destination_kind": "unloco",
				"modified": "2025-05-20 09:15:00",
			},
		]
		status_counts = _aggregate_job_status_counts(j["job_status"] for j in jobs)
		unloco_labels = {
			"CNSHA": "Shanghai, CN",
			"JPTYO": "Tokyo, JP",
			"SGSIN": "Singapore, SG",
		}
		html = _build_operational_jobs_card_html(jobs, status_counts, unloco_labels, {})
		self.assertIn("exhibit-shipment-details-card", html)
		self.assertIn("Job Details", html)
		self.assertIn("2 jobs", html)
		self.assertIn("<strong>Draft:</strong> 1", html)
		self.assertIn("<strong>Submitted:</strong> 1", html)
		self.assertIn("SF000000384", html)
		self.assertIn("Shanghai, CN", html)
		self.assertIn("Singapore, SG", html)
		self.assertIn('exhibit-shipment-status-badge draft', html)
		self.assertIn('exhibit-shipment-status-badge submitted', html)
		self.assertIn("exhibit-shipment-row-icon--draft", html)
		self.assertIn("exhibit-shipment-row-icon--active", html)
		self.assertIn("Service", html)
		self.assertIn("Job ID", html)

	def test_build_operational_jobs_card_html_renders_mixed_service_types(self):
		jobs = [
			{
				"job_type": "Sea Shipment",
				"name": "SF000000384",
				"service_label": "Sea",
				"job_status": "Draft",
				"origin_code": "CNSHA",
				"destination_code": "SGSIN",
				"origin_kind": "unloco",
				"destination_kind": "unloco",
				"modified": None,
			},
			{
				"job_type": "Transport Job",
				"name": "TJ-00001",
				"service_label": "Transport",
				"job_status": "In Progress",
				"origin_code": "ADDR-PICK",
				"destination_code": "ADDR-DROP",
				"origin_kind": "address",
				"destination_kind": "address",
				"modified": None,
			},
			{
				"job_type": "Declaration",
				"name": "DEC-00001",
				"service_label": "Customs",
				"job_status": "Submitted",
				"origin_code": "HKHKG",
				"destination_code": "PHMNL",
				"origin_kind": "unloco",
				"destination_kind": "unloco",
				"modified": None,
			},
			{
				"job_type": "Warehouse Job",
				"name": "WJ-00001",
				"service_label": "Warehousing",
				"job_status": "Draft",
				"origin_code": "Inbound Order",
				"destination_code": "IO-00001",
				"origin_kind": "text",
				"destination_kind": "text",
				"modified": None,
			},
		]
		status_counts = _aggregate_job_status_counts(j["job_status"] for j in jobs)
		unloco_labels = {"CNSHA": "Shanghai, CN", "SGSIN": "Singapore, SG", "HKHKG": "Hong Kong, HK", "PHMNL": "Manila, PH"}
		address_labels = {"ADDR-PICK": "Warehouse A", "ADDR-DROP": "Venue Hall 3"}
		html = _build_operational_jobs_card_html(jobs, status_counts, unloco_labels, address_labels)
		self.assertIn("Sea", html)
		self.assertIn("Transport", html)
		self.assertIn("Customs", html)
		self.assertIn("Warehousing", html)
		self.assertIn("Warehouse A", html)
		self.assertIn("Venue Hall 3", html)
		self.assertIn("Hong Kong, HK", html)
		self.assertIn("Inbound Order", html)
		self.assertIn("IO-00001", html)

	def test_build_exhibit_job_status_tab_html_renders_job_details_card(self):
		docket_rows = [{"docket": "DK-TEST-1", "status": "Draft", "exhibitor": "Acme", "booth_no": "A1"}]
		job = {
			"job_type": "Sea Shipment",
			"name": "SF000000384",
			"service_label": "Sea",
			"job_status": "Draft",
			"origin_code": "CNSHA",
			"destination_code": "SGSIN",
			"origin_kind": "unloco",
			"destination_kind": "unloco",
			"modified": None,
		}

		with (
			patch(
				"logistics.mice.doctype.mice_project.mice_project._resolve_docket_operational_jobs",
				return_value=[{"job_type": "Sea Shipment", "job_no": "SF000000384"}],
			),
			patch(
				"logistics.mice.doctype.mice_project.mice_project._fetch_operational_job_statuses",
				return_value={("Sea Shipment", "SF000000384"): job},
			),
			patch(
				"logistics.mice.doctype.mice_project.mice_project._batch_unloco_table_labels",
				return_value={"CNSHA": "Shanghai, CN", "SGSIN": "Singapore, SG"},
			),
			patch(
				"logistics.mice.doctype.mice_project.mice_project._batch_address_table_labels",
				return_value={},
			),
		):
			html = _build_exhibit_job_status_tab_html("EXH-TEST", docket_rows=docket_rows)
			self.assertIn("exhibit-shipment-details-card", html)
			self.assertIn("Job Details", html)
			self.assertIn("1 job", html)
			self.assertIn("DK-TEST-1", html)
			self.assertIn("Shanghai, CN", html)

	def test_fetch_transport_job_endpoints_queries_transport_job_link(self):
		with patch("logistics.mice.doctype.mice_project.mice_project.frappe.get_all") as mock_get_all:
			mock_get_all.return_value = []
			self.assertEqual(_fetch_transport_job_endpoints(["TJ-00001"]), {})
			mock_get_all.assert_called_once()
			args, kwargs = mock_get_all.call_args
			self.assertEqual(args[0], "Transport Leg")
			filters = kwargs.get("filters", {})
			self.assertIn("transport_job", filters)
			self.assertNotIn("parent", filters)

	def test_sales_quote_dashboard_links_mice_project_via_exhibit(self):
		from logistics.pricing_center.doctype.sales_quote.sales_quote_dashboard import get_data

		data = get_data()
		self.assertEqual(data.get("internal_and_external_links", {}).get("MICE Project"), "exhibit")
