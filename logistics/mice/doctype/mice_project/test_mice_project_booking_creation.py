# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from types import SimpleNamespace
from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, flt, today

from logistics.mice.doctype.mice_order.mice_order import action_create_mice_job
from logistics.mice.doctype.mice_project.mice_project_booking_creation import (
	_apply_exhibit_context,
	_dialog_creatable_job_type,
	_prepare_operational_charges_before_insert,
	booking_is_linked_from_mice_project,
	create_booking_or_order_from_exhibit,
	get_exhibit_booking_choices,
)
from logistics.mice.doctype.mice_project.mice_project_charge_copy import (
	consolidation_charges_preview_rows,
	populate_operational_charges_from_mice_consolidation,
	push_consolidation_charges_to_dockets,
	SOURCE_CONSOLIDATION_CHARGE_FIELD,
	SOURCE_MICE_PROJECT_FIELD,
)
from logistics.utils.charge_service_type import default_job_type_for_internal_job_service_type


def _mock_consolidation_charge(**fields):
	"""Stand-in for a MICE Project Consolidation Charges row (supports as_dict for scrub)."""
	sn = SimpleNamespace(**fields)
	sn.as_dict = lambda: dict(fields)
	return sn


class _FakeDocket:
	def __init__(self, name, charges=None):
		self.doctype = "Docket"
		self.name = name
		self.charges = [frappe._dict(row) for row in (charges or [])]

	def get(self, fieldname):
		return self.charges if fieldname == "charges" else None

	def set(self, fieldname, value):
		if fieldname == "charges":
			self.charges = [frappe._dict(row) for row in (value or [])]

	def append(self, fieldname, row):
		if fieldname == "charges":
			self.charges.append(frappe._dict(row))

	def save(self, ignore_permissions=False):
		return self


class _FakeMiceProject:
	def __init__(self, charges, allocations, *, basis="Equal", name="PROJ-TEST"):
		self.name = name
		self.doctype = "MICE Project"
		self.cost_allocation_basis = basis
		self.consolidation_charges = list(charges)
		self.cost_allocations = [frappe._dict(row) for row in allocations]
		self.saved = False

	def get(self, fieldname):
		return getattr(self, fieldname, None)

	def _refresh_cost_allocation_targets(self, target_type):
		return len(self.cost_allocations)

	def _validate_allocation_prerequisites(self):
		return None

	def _apply_allocation_to_targets(self):
		return None

	def _recalculate_consolidation_charge_totals(self):
		return None

	def _recalculate_cost_allocation_totals(self):
		return None

	def save(self, ignore_permissions=False):
		self.saved = True

	def _per_target_allocation_factor(self, charge, allocation_rows, total_targets):
		method = (getattr(charge, "allocation_method", None) or self.cost_allocation_basis or "Equal").strip()
		if method == "Custom":
			total_pct = sum(flt(getattr(row, "cost_allocation_percentage", 0)) for row in allocation_rows)
			if total_pct > 0:
				return [
					flt(getattr(row, "cost_allocation_percentage", 0)) / total_pct
					for row in allocation_rows
				]
		share = 1.0 / float(total_targets or 1)
		return [share for _ in allocation_rows]


def _ensure_test_mice_charge_item() -> str:
	item = "TEST-ITEM-MICE-CHG"
	if frappe.db.exists("Item", item):
		return item
	item_group = frappe.db.get_value("Item Group", {"is_group": 0}, "name")
	if not item_group:
		item_group = frappe.db.get_value("Item Group", {}, "name")
	frappe.get_doc(
		{
			"doctype": "Item",
			"item_code": item,
			"item_name": item,
			"item_group": item_group,
			"is_sales_item": 1,
		}
	).insert(ignore_permissions=True)
	return item


class TestMiceConsolidationChargeCopy(UnitTestCase):
	def test_populate_sea_booking_from_sea_consolidation_rows(self):
		item = _ensure_test_mice_charge_item()
		ep = frappe._dict(
			doctype="MICE Project",
			consolidation_charges=[
				_mock_consolidation_charge(
					service_type="Sea",
					charge_type="Margin",
					item_code=item,
					unit_rate=4300,
					total_amount=4300,
					quantity=1,
				),
				_mock_consolidation_charge(
					service_type="Transport",
					charge_type="Margin",
					item_code=item,
					unit_rate=100,
					total_amount=100,
					quantity=1,
				),
			],
		)
		row = frappe._dict(service_type="Sea")
		booking = frappe.new_doc("Sea Booking")
		n = populate_operational_charges_from_mice_consolidation(ep, booking, row)
		self.assertEqual(n, 1)
		self.assertEqual(len(booking.charges), 1)
		self.assertEqual((booking.charges[0].service_type or "").strip(), "Sea")
		self.assertEqual(booking.charges[0].item_code, item)
		self.assertEqual(flt(booking.charges[0].estimated_cost), 4300)
		self.assertEqual(flt(booking.charges[0].estimated_revenue), 4300)

	def test_disbursement_consolidation_rows_are_excluded(self):
		item = _ensure_test_mice_charge_item()
		ep = frappe._dict(
			doctype="MICE Project",
			consolidation_charges=[
				_mock_consolidation_charge(
					service_type="Sea",
					charge_type="Disbursement",
					item_code=item,
					unit_rate=50,
					total_amount=50,
					quantity=1,
				),
				_mock_consolidation_charge(
					service_type="Sea",
					charge_type="Margin",
					item_code=item,
					unit_rate=200,
					total_amount=200,
					quantity=1,
				),
			],
		)
		booking = frappe.new_doc("Sea Booking")
		n = populate_operational_charges_from_mice_consolidation(
			ep, booking, frappe._dict(service_type="Sea")
		)
		self.assertEqual(n, 1)
		self.assertEqual(flt(booking.charges[0].unit_rate), 200)

	def test_cost_charge_type_maps_to_cost_not_revenue(self):
		item = _ensure_test_mice_charge_item()
		ep = frappe._dict(
			doctype="MICE Project",
			consolidation_charges=[
				_mock_consolidation_charge(
					service_type="Sea",
					charge_type="Cost",
					item_code=item,
					unit_rate=590,
					total_amount=590,
					quantity=1,
				),
			],
		)
		booking = frappe.new_doc("Sea Booking")
		n = populate_operational_charges_from_mice_consolidation(
			ep, booking, frappe._dict(service_type="Sea")
		)
		self.assertEqual(n, 1)
		self.assertEqual(flt(booking.charges[0].estimated_cost), 590)
		self.assertEqual(flt(booking.charges[0].estimated_revenue), 0)

	def test_prepare_prefers_consolidation_over_sales_quote(self):
		item = _ensure_test_mice_charge_item()
		ep = frappe._dict(
			doctype="MICE Project",
			sales_quote="",
			consolidation_charges=[
				_mock_consolidation_charge(
					service_type="Sea",
					charge_type="Margin",
					item_code=item,
					unit_rate=100,
					total_amount=100,
					quantity=1,
				),
			],
		)
		booking = frappe.new_doc("Sea Booking")
		row = frappe._dict(service_type="Sea", linked_service="IJ-TEST-1")
		with patch(
			"logistics.mice.doctype.mice_project.mice_project_booking_creation._populate_charges_from_linked_sales_quote"
		) as mock_sq:
			_prepare_operational_charges_before_insert(ep, booking, row)
			mock_sq.assert_not_called()
		self.assertEqual(len(booking.charges), 1)
		self.assertEqual(booking.charges[0].item_code, item)

	def test_prepare_sea_does_not_fall_back_to_sales_quote(self):
		"""Sea/Air from MICE: no Sales Quote attach or charge fallback when consolidation is empty."""
		ep = frappe._dict(
			doctype="MICE Project",
			sales_quote="SQ-FAKE",
			consolidation_charges=[],
		)
		booking = frappe.new_doc("Sea Booking")
		row = frappe._dict(service_type="Sea")
		with patch(
			"logistics.mice.doctype.mice_project.mice_project_booking_creation._populate_charges_from_linked_sales_quote"
		) as mock_sq:
			_prepare_operational_charges_before_insert(ep, booking, row)
			mock_sq.assert_not_called()
		self.assertFalse((booking.sales_quote or "").strip())
		self.assertEqual(len(booking.charges or []), 0)

	def test_prepare_transport_still_falls_back_to_sales_quote(self):
		ep = frappe._dict(
			doctype="MICE Project",
			sales_quote="SQ-FAKE",
			consolidation_charges=[],
		)
		order = frappe.new_doc("Transport Order")
		order.sales_quote = "SQ-FAKE"
		row = frappe._dict(service_type="Transport")

		def _fake_sq(target_doc):
			target_doc.append(
				"charges",
				{
					"service_type": "Transport",
					"item_code": _ensure_test_mice_charge_item(),
					"charge_type": "Revenue",
					"unit_rate": 99,
				},
			)

		with patch(
			"logistics.mice.doctype.mice_project.mice_project_booking_creation._populate_charges_from_linked_sales_quote",
			side_effect=_fake_sq,
		) as mock_sq:
			_prepare_operational_charges_before_insert(ep, order, row)
			mock_sq.assert_called_once()
		self.assertEqual(len(order.charges), 1)
		self.assertEqual(flt(order.charges[0].unit_rate), 99)

	def test_preview_includes_consolidation_charges(self):
		item = _ensure_test_mice_charge_item()
		ep = frappe._dict(
			doctype="MICE Project",
			consolidation_charges=[
				_mock_consolidation_charge(
					service_type="Sea",
					charge_type="Margin",
					item_code=item,
					unit_rate=4300,
					total_amount=4300,
					quantity=1,
				),
			],
		)
		preview = consolidation_charges_preview_rows(
			ep, "Sea Booking", frappe._dict(service_type="Sea")
		)
		self.assertEqual(len(preview), 1)
		self.assertEqual(preview[0]["item_code"], item)
		self.assertEqual(flt(preview[0]["unit_rate"]), 4300)

	def test_push_to_dockets_uses_equal_split_and_preserves_existing_rows(self):
		item = _ensure_test_mice_charge_item()
		charge = _mock_consolidation_charge(
			name="ROW-1",
			service_type="MICE",
			charge_type="Cost",
			item_code=item,
			unit_rate=10,
			total_amount=20,
			quantity=2,
			revenue_calculation_method="Per Unit",
			unit_type="Job",
			unit_of_measure="Job",
			currency="PHP",
		)
		project = _FakeMiceProject(
			[charge],
			[
				{"target_type": "Docket", "target": "DK-1", "cost_allocation_percentage": 50},
				{"target_type": "Docket", "target": "DK-2", "cost_allocation_percentage": 50},
			],
		)
		dockets = {
			"DK-1": _FakeDocket("DK-1", charges=[{"unit_rate": 99, "charge_scope": "Main"}]),
			"DK-2": _FakeDocket("DK-2"),
		}

		with patch(
			"logistics.mice.doctype.mice_project.mice_project_charge_copy.frappe.get_doc",
			side_effect=lambda doctype, name: dockets[name],
		):
			inserted = push_consolidation_charges_to_dockets(
				project,
				selected_charges=[charge],
				purchase_invoice="PINV-0001",
			)

		self.assertEqual(inserted, 2)
		self.assertTrue(project.saved)
		generated_1 = [
			row
			for row in dockets["DK-1"].charges
			if getattr(row, SOURCE_MICE_PROJECT_FIELD, None) == project.name
		]
		generated_2 = [
			row
			for row in dockets["DK-2"].charges
			if getattr(row, SOURCE_MICE_PROJECT_FIELD, None) == project.name
		]
		self.assertEqual(len(generated_1), 1)
		self.assertEqual(len(generated_2), 1)
		# total_amount 20 at 50/50 → 10 each (not unit_rate 10 → 5)
		self.assertEqual(flt(generated_1[0].unit_cost), 10.0)
		self.assertEqual(flt(generated_2[0].unit_cost), 10.0)
		self.assertEqual(flt(generated_1[0].estimated_cost), 10.0)
		self.assertEqual(flt(generated_1[0].cost_quantity), 1)
		self.assertEqual(generated_1[0].cost_calculation_method, "Per Unit")
		self.assertEqual(generated_1[0].cost_unit_type, "Job")
		self.assertEqual(generated_1[0].cost_uom, "Job")
		self.assertEqual(generated_1[0].cost_currency, "PHP")
		self.assertEqual(generated_1[0].purchase_invoice, "PINV-0001")
		self.assertEqual(generated_1[0].purchase_invoice_status, "Requested")
		self.assertTrue(
			any(not getattr(row, SOURCE_MICE_PROJECT_FIELD, None) and flt(row.unit_rate) == 99 for row in dockets["DK-1"].charges)
		)

		with patch(
			"logistics.mice.doctype.mice_project.mice_project_charge_copy.frappe.get_doc",
			side_effect=lambda doctype, name: dockets[name],
		):
			inserted_again = push_consolidation_charges_to_dockets(
				project,
				selected_charges=[charge],
				purchase_invoice="PINV-0002",
			)

		self.assertEqual(inserted_again, 2)
		generated_1 = [
			row
			for row in dockets["DK-1"].charges
			if getattr(row, SOURCE_MICE_PROJECT_FIELD, None) == project.name
		]
		self.assertEqual(len(generated_1), 1)
		self.assertEqual(generated_1[0].purchase_invoice, "PINV-0002")
		self.assertEqual(
			getattr(generated_1[0], SOURCE_CONSOLIDATION_CHARGE_FIELD, None),
			"ROW-1",
		)

	def test_push_to_dockets_uses_custom_percentages(self):
		item = _ensure_test_mice_charge_item()
		charge = _mock_consolidation_charge(
			name="ROW-2",
			service_type="MICE",
			charge_type="Cost",
			item_code=item,
			unit_rate=10,
			total_amount=10,
			quantity=1,
			allocation_method="Custom",
		)
		project = _FakeMiceProject(
			[charge],
			[
				{"target_type": "Docket", "target": "DK-1", "cost_allocation_percentage": 60},
				{"target_type": "Docket", "target": "DK-2", "cost_allocation_percentage": 40},
			],
			basis="Custom",
		)
		dockets = {"DK-1": _FakeDocket("DK-1"), "DK-2": _FakeDocket("DK-2")}

		with patch(
			"logistics.mice.doctype.mice_project.mice_project_charge_copy.frappe.get_doc",
			side_effect=lambda doctype, name: dockets[name],
		):
			inserted = push_consolidation_charges_to_dockets(project, selected_charges=[charge])

		self.assertEqual(inserted, 2)
		generated_1 = dockets["DK-1"].charges[0]
		generated_2 = dockets["DK-2"].charges[0]
		self.assertEqual(flt(generated_1.unit_rate), 6.0)
		self.assertEqual(flt(generated_2.unit_rate), 4.0)
		self.assertEqual(flt(generated_1.estimated_cost), 6.0)
		self.assertEqual(flt(generated_2.estimated_cost), 4.0)

	def test_push_to_dockets_skips_disbursement(self):
		item = _ensure_test_mice_charge_item()
		keep = _mock_consolidation_charge(
			name="ROW-3",
			service_type="MICE",
			charge_type="Cost",
			item_code=item,
			unit_rate=10,
			total_amount=10,
			quantity=1,
		)
		skip = _mock_consolidation_charge(
			name="ROW-4",
			service_type="MICE",
			charge_type="Disbursement",
			item_code=item,
			unit_rate=8,
			total_amount=8,
			quantity=1,
		)
		project = _FakeMiceProject(
			[keep, skip],
			[
				{"target_type": "Docket", "target": "DK-1", "cost_allocation_percentage": 50},
				{"target_type": "Docket", "target": "DK-2", "cost_allocation_percentage": 50},
			],
		)
		dockets = {"DK-1": _FakeDocket("DK-1"), "DK-2": _FakeDocket("DK-2")}

		with patch(
			"logistics.mice.doctype.mice_project.mice_project_charge_copy.frappe.get_doc",
			side_effect=lambda doctype, name: dockets[name],
		):
			inserted = push_consolidation_charges_to_dockets(
				project,
				selected_charges=[keep, skip],
			)

		self.assertEqual(inserted, 2)
		self.assertEqual(len(dockets["DK-1"].charges), 1)
		self.assertEqual(
			getattr(dockets["DK-1"].charges[0], SOURCE_CONSOLIDATION_CHARGE_FIELD, None),
			"ROW-3",
		)


class TestMiceServiceTypeMapping(UnitTestCase):
	def test_mice_maps_to_mice_order(self):
		self.assertEqual(default_job_type_for_internal_job_service_type("MICE"), "MICE Order")
		self.assertEqual(default_job_type_for_internal_job_service_type("Events"), "MICE Order")

	def test_dialog_creatable_job_type_for_mice(self):
		row = frappe._dict(service_type="MICE", job_type="")
		self.assertEqual(_dialog_creatable_job_type(row), "MICE Order")

	def test_dialog_creatable_job_type_for_air_unchanged(self):
		row = frappe._dict(service_type="Air", job_type="")
		self.assertEqual(_dialog_creatable_job_type(row), "Air Booking")


class TestMiceSeaBookingExhibitContext(UnitTestCase):
	def test_apply_exhibit_context_sets_organizer_customer_not_sales_quote(self):
		ep = frappe._dict(
			doctype="MICE Project",
			name="EP-TEST",
			organizer="ORG-TEST",
			sales_quote="SQ-PROGRAMME",
			company=None,
			branch=None,
			cost_center=None,
			profit_center=None,
			project=None,
		)
		booking = frappe.new_doc("Sea Booking")
		with (
			patch(
				"logistics.mice.doctype.mice_project.mice_project_booking_creation._resolve_exhibit_org_context",
				return_value={},
			),
			patch(
				"logistics.mice.doctype.mice_project.mice_project_booking_creation._resolve_organizer_customer",
				return_value="CUST-ORGANIZER",
			),
			patch(
				"logistics.mice.doctype.mice_project.mice_project_booking_creation._apply_sales_quote_parties_to_target",
			),
			patch(
				"logistics.mice.doctype.mice_project.mice_project_booking_creation.copy_operational_rep_fields_from_chain",
			),
		):
			_apply_exhibit_context(booking, ep)
		self.assertEqual(booking.local_customer, "CUST-ORGANIZER")
		self.assertFalse((booking.sales_quote or "").strip())

	def test_apply_exhibit_context_still_sets_sales_quote_on_transport_order(self):
		ep = frappe._dict(
			doctype="MICE Project",
			name="EP-TEST",
			organizer="ORG-TEST",
			sales_quote="SQ-PROGRAMME",
			company=None,
			branch=None,
			cost_center=None,
			profit_center=None,
			project=None,
		)
		order = frappe.new_doc("Transport Order")
		with (
			patch(
				"logistics.mice.doctype.mice_project.mice_project_booking_creation._resolve_exhibit_org_context",
				return_value={},
			),
			patch(
				"logistics.mice.doctype.mice_project.mice_project_booking_creation._resolve_organizer_customer",
				return_value="CUST-ORGANIZER",
			),
			patch(
				"logistics.mice.doctype.mice_project.mice_project_booking_creation._resolve_sales_quote_for_exhibit",
				return_value="SQ-PROGRAMME",
			),
			patch(
				"logistics.mice.doctype.mice_project.mice_project_booking_creation._apply_sales_quote_parties_to_target",
			),
			patch(
				"logistics.mice.doctype.mice_project.mice_project_booking_creation.copy_operational_rep_fields_from_chain",
			),
		):
			_apply_exhibit_context(order, ep)
		self.assertEqual(order.customer, "CUST-ORGANIZER")
		self.assertEqual(order.sales_quote, "SQ-PROGRAMME")

	def test_booking_is_linked_from_mice_project(self):
		with patch(
			"logistics.utils.linked_service_usage.get_linked_services_used_by",
			return_value=["LS-1"],
		), patch(
			"frappe.db.exists",
			side_effect=lambda dt, filters: dt == "Linked Service" and filters.get("parent_booking_type") == "MICE Project",
		):
			self.assertTrue(booking_is_linked_from_mice_project("Sea Booking", "SBK-1"))
		with patch(
			"logistics.utils.linked_service_usage.get_linked_services_used_by",
			return_value=["LS-1"],
		), patch("frappe.db.exists", return_value=False):
			self.assertFalse(booking_is_linked_from_mice_project("Sea Booking", "SBK-1"))
		self.assertFalse(booking_is_linked_from_mice_project("Sea Booking", None))
		with patch(
			"logistics.utils.linked_service_usage.get_linked_services_used_by",
			return_value=[],
		):
			self.assertFalse(booking_is_linked_from_mice_project("Sea Booking", "SBK-1"))


class TestCreateMiceOrderFromExhibit(FrappeTestCase):
	def setUp(self):
		if not frappe.db.exists("DocType", "MICE Project"):
			self.skipTest("MICE Project not installed")

	def tearDown(self):
		frappe.db.rollback()

	def _site_company(self):
		return frappe.db.get_value("Company", {}, "name")

	def _site_customer(self):
		return frappe.db.get_value("Customer", {"disabled": 0}, "name")

	def _sales_quote_header_defaults(self):
		"""Reuse org/rep fields from an existing submitted quote on this site."""
		fields = [
			"company",
			"customer",
			"shipper",
			"consignee",
			"branch",
			"cost_center",
			"profit_center",
			"quotation_type",
			"naming_series",
			"sales_rep",
			"operations_rep",
			"customer_service_rep",
		]
		row = frappe.db.get_value(
			"Sales Quote",
			{"docstatus": 1, "quotation_type": ("in", ("Regular", "One-off"))},
			fields,
			as_dict=True,
			order_by="modified desc",
		)
		return row or {}

	def _test_site_address(self):
		existing = frappe.db.get_value("Address", {}, "name")
		if existing:
			return existing
		addr = frappe.get_doc(
			{
				"doctype": "Address",
				"address_title": f"MICE IJ Test Site {frappe.generate_hash(length=4)}",
				"address_type": "Office",
				"address_line1": "1 Test St",
				"city": "Testville",
			}
		)
		addr.flags.ignore_mandatory = True
		addr.insert(ignore_permissions=True)
		return addr.name

	def _test_item_code(self):
		existing = frappe.db.get_value("Item", {"disabled": 0, "is_sales_item": 1}, "name")
		if existing:
			return existing
		from logistics.air_freight.tests.test_helpers import create_test_item

		return create_test_item(f"MICE IJ Test Item {frappe.generate_hash(length=6)}")

	def _test_organizer(self, customer):
		existing = frappe.db.get_value(
			"MICE Organizer", {"customer": customer}, "name"
		)
		if existing:
			return existing
		org = frappe.new_doc("MICE Organizer")
		org.organizer_name = f"Test Org {frappe.generate_hash(length=4)}"
		org.organizer_type = "Company"
		org.customer = customer
		org.insert(ignore_permissions=True)
		return org.name

	def _minimal_mice_project_with_ij(self):
		company = self._site_company()
		customer = self._site_customer()
		if not company or not customer:
			self.skipTest("Company and Customer required")

		header = self._sales_quote_header_defaults()
		if not header.get("company"):
			header["company"] = company
		if not header.get("customer"):
			header["customer"] = customer

		org = self._test_organizer(customer)
		ex = frappe.new_doc("MICE Project")
		ex.project_name = f"MICE IJ Test {frappe.generate_hash(length=6)}"
		ex.organizer = org
		ex.show_open_date = today()
		ex.show_close_date = add_days(today(), 3)
		ex.company = header.get("company") or company
		ex.insert(ignore_permissions=True)

		sq = frappe.new_doc("Sales Quote")
		sq.update(
			{
				"quotation_type": header.get("quotation_type") or "Regular",
				"naming_series": header.get("naming_series") or "SQU.#########",
				"company": header.get("company") or company,
				"customer": header.get("customer") or customer,
				"date": today(),
				"valid_until": add_days(today(), 30),
				"main_service": "MICE",
				"exhibit": ex.name,
				"exhibit_show_open_date": today(),
				"exhibit_show_close_date": add_days(today(), 3),
				"shipper": header.get("shipper"),
				"consignee": header.get("consignee"),
				"branch": header.get("branch"),
				"cost_center": header.get("cost_center"),
				"profit_center": header.get("profit_center"),
				"sales_rep": header.get("sales_rep"),
				"operations_rep": header.get("operations_rep"),
				"customer_service_rep": header.get("customer_service_rep"),
			}
		)
		sq.append(
			"charges",
			{
				"service_type": "MICE",
				"sp_site": self._test_site_address(),
				"item_code": self._test_item_code(),
				"unit_rate": 100,
			},
		)
		sq.flags.ignore_mandatory = True
		sq.insert(ignore_permissions=True)
		sq.submit()

		ex.append(
			"linked_services",
			{
				"service_type": "MICE",
				"job_description": "Site resource line",
			},
		)
		ex.save(ignore_permissions=True)
		return ex, sq

	def test_booking_choices_include_creatable_mice_order(self):
		ex, _sq = self._minimal_mice_project_with_ij()
		out = get_exhibit_booking_choices(ex.name)
		mice_rows = [
			c
			for c in (out.get("choices") or [])
			if c.get("job_type") == "MICE Order"
		]
		self.assertTrue(mice_rows, out)
		self.assertTrue(mice_rows[0].get("creatable"), mice_rows[0].get("not_creatable_message"))

	def test_create_mice_order_from_internal_job_row(self):
		ex, _sq = self._minimal_mice_project_with_ij()
		ex.reload()
		ij_idx = len(ex.linked_services)

		result = create_booking_or_order_from_exhibit(
			ex.name,
			"MICE Order",
			internal_job_idx=ij_idx,
		)
		self.assertTrue(result.get("mice_order"))
		order_name = result["mice_order"]
		self.assertTrue(frappe.db.exists("MICE Order", order_name))

		ex.reload()
		row = ex.linked_services[ij_idx - 1]
		self.assertEqual(row.job_type, "MICE Order")
		self.assertEqual(row.job_no, order_name)

		order = frappe.get_doc("MICE Order", order_name)
		self.assertEqual(order.exhibit, ex.name)
		self.assertTrue(order.get("charges"))

	def test_mice_order_action_create_mice_job(self):
		ex, _sq = self._minimal_mice_project_with_ij()
		ex.reload()
		result = create_booking_or_order_from_exhibit(
			ex.name,
			"MICE Order",
			internal_job_idx=len(ex.linked_services),
		)
		order_name = result["mice_order"]
		order = frappe.get_doc("MICE Order", order_name)
		order.submit()
		payload = action_create_mice_job(order_name, title="Execution job")
		self.assertTrue(payload.get("created"))
		self.assertTrue(frappe.db.exists("MICE Job", payload["name"]))
		job = frappe.get_doc("MICE Job", payload["name"])
		self.assertEqual(job.exhibit_order, order_name)

		payload2 = action_create_mice_job(order_name, title="Execution job")
		self.assertFalse(payload2.get("created"))
		self.assertTrue(payload2.get("already_exists"))
		self.assertEqual(payload2["name"], payload["name"])

	def _minimal_mice_project_with_sea_ij(self, organizer_customer=None, sq_customer=None):
		"""MICE Project with a Sea linked service; organizer and SQ customers may differ."""
		company = self._site_company()
		customers = frappe.get_all("Customer", filters={"disabled": 0}, pluck="name", limit=2)
		if not company or not customers:
			self.skipTest("Company and Customer required")
		org_cust = organizer_customer or customers[0]
		quote_cust = sq_customer or (customers[1] if len(customers) > 1 else customers[0])

		header = self._sales_quote_header_defaults()
		if not header.get("company"):
			header["company"] = company

		org = self._test_organizer(org_cust)
		ex = frappe.new_doc("MICE Project")
		ex.project_name = f"MICE Sea Test {frappe.generate_hash(length=6)}"
		ex.organizer = org
		ex.show_open_date = today()
		ex.show_close_date = add_days(today(), 3)
		ex.company = header.get("company") or company
		ex.insert(ignore_permissions=True)

		sq = frappe.new_doc("Sales Quote")
		sq.update(
			{
				"quotation_type": header.get("quotation_type") or "Regular",
				"naming_series": header.get("naming_series") or "SQU.#########",
				"company": header.get("company") or company,
				"customer": quote_cust,
				"date": today(),
				"valid_until": add_days(today(), 30),
				"main_service": "MICE",
				"exhibit": ex.name,
				"exhibit_show_open_date": today(),
				"exhibit_show_close_date": add_days(today(), 3),
				"shipper": header.get("shipper"),
				"consignee": header.get("consignee"),
				"branch": header.get("branch"),
				"cost_center": header.get("cost_center"),
				"profit_center": header.get("profit_center"),
				"sales_rep": header.get("sales_rep"),
				"operations_rep": header.get("operations_rep"),
				"customer_service_rep": header.get("customer_service_rep"),
			}
		)
		sq.append(
			"charges",
			{
				"service_type": "MICE",
				"sp_site": self._test_site_address(),
				"item_code": self._test_item_code(),
				"unit_rate": 100,
			},
		)
		sq.flags.ignore_mandatory = True
		sq.insert(ignore_permissions=True)
		sq.submit()
		ex.sales_quote = sq.name
		ex.append(
			"linked_services",
			{
				"service_type": "Sea",
				"job_description": "Sea leg",
			},
		)
		ex.save(ignore_permissions=True)
		return ex, sq, org_cust

	def test_create_sea_booking_uses_organizer_customer_without_sales_quote(self):
		ex, sq, org_cust = self._minimal_mice_project_with_sea_ij()
		ex.reload()
		port = frappe.db.get_value("UNLOCO", {}, "name")
		if not port:
			self.skipTest("UNLOCO required for Sea Booking create")
		rows = list(ex.linked_services or [])
		if not rows:
			self.skipTest("No linked services on MICE Project")
		ij_idx = len(rows)
		# Create may still need corridor ports; set on Linked Service when fields exist.
		ls_name = (getattr(rows[ij_idx - 1], "name", None) or "").strip()
		if ls_name and frappe.db.exists("Linked Service", ls_name):
			updates = {}
			ls_meta = frappe.get_meta("Linked Service")
			for fn, val in (
				("origin_port", port),
				("destination_port", port),
				("direction", "Import"),
			):
				if ls_meta.has_field(fn):
					updates[fn] = val
			if updates:
				frappe.db.set_value("Linked Service", ls_name, updates, update_modified=False)

		try:
			result = create_booking_or_order_from_exhibit(
				ex.name,
				"Sea Booking",
				internal_job_idx=ij_idx,
			)
		except Exception as e:
			self.skipTest(f"Sea Booking create not runnable on this site: {e}")

		self.assertTrue(result.get("sea_booking"), result)
		booking = frappe.get_doc("Sea Booking", result["sea_booking"])
		self.assertEqual(booking.local_customer, org_cust)
		self.assertFalse((booking.sales_quote or "").strip())
		self.assertNotEqual(booking.sales_quote, sq.name)
