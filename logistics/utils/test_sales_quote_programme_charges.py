# Copyright (c) 2026, AgilaSoft and Contributors

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, today

from logistics.air_freight.tests.test_helpers import (
	create_test_consignee,
	create_test_item,
	create_test_shipper,
	setup_basic_master_data,
)
from logistics.utils.charge_service_type import sales_quote_charge_service_types_equal
from logistics.utils.sales_quote_programme_charges import (
	copy_charge_breaks_for_reference,
	copy_sales_quote_charge_breaks_to_programme_parent,
	fetch_sales_quote_charges_for_programme,
	map_sales_quote_charge_to_programme_charge_dict,
	populate_programme_charges_from_sales_quote,
	programme_charge_service_types_for_parent,
)


class TestSalesQuoteProgrammeCharges(FrappeTestCase):
	def setUp(self):
		sq_row = frappe.db.get_value(
			"Sales Quote",
			{"docstatus": 1, "main_service": "MICE"},
			["company", "customer", "shipper", "consignee", "branch", "cost_center", "profit_center", "sales_rep", "operations_rep", "customer_service_rep"],
			as_dict=True,
		)
		if sq_row and sq_row.company and sq_row.customer:
			self.company = sq_row.company
			self.customer = sq_row.customer
			self.shipper = sq_row.shipper or frappe.db.get_value("Shipper", {}, "name")
			self.consignee = sq_row.consignee or frappe.db.get_value("Consignee", {}, "name")
			self._sq_defaults = {
				k: sq_row.get(k)
				for k in (
					"branch",
					"cost_center",
					"profit_center",
					"sales_rep",
					"operations_rep",
					"customer_service_rep",
				)
			}
		else:
			self.company = frappe.db.get_value("Company", {}, "name")
			self.customer = frappe.db.get_value("Customer", {}, "name")
			if not self.company or not self.customer:
				data = setup_basic_master_data()
				self.company = data["company"]
				self.customer = data["customer"]
			self.shipper = (
				frappe.db.get_value("Shipper", {}, "name") or create_test_shipper()
			)
			self.consignee = (
				frappe.db.get_value("Consignee", {}, "name") or create_test_consignee()
			)
			rep = frappe.db.get_value("Employee", {}, "name")
			self._sq_defaults = {
				"branch": frappe.db.get_value("Branch", {"custom_company": self.company}, "name"),
				"cost_center": frappe.db.get_value("Cost Center", {"company": self.company}, "name"),
				"profit_center": frappe.db.get_value("Profit Center", {}, "name"),
				"sales_rep": rep,
				"operations_rep": rep,
				"customer_service_rep": rep,
			}

	def _load_sales_quote_defaults(self):
		return self._sq_defaults

	def tearDown(self):
		frappe.db.rollback()

	def test_map_charge_includes_service_type_and_sales_quote_link(self):
		sq_row = {
			"service_type": "Special Project",
			"item_code": "Item-Test",
			"unit_rate": 100,
		}
		mapped = map_sales_quote_charge_to_programme_charge_dict(
			sq_row, "SQU-TEST-001", "Special Project Charges"
		)
		self.assertEqual(mapped.get("sales_quote_link"), "SQU-TEST-001")
		self.assertEqual(mapped.get("service_type"), "Special Project")
		self.assertTrue(
			sales_quote_charge_service_types_equal(mapped.get("service_type"), "Special Project")
		)

	def test_docket_programme_populate_uses_all_quote_charge_lines(self):
		self.assertEqual(programme_charge_service_types_for_parent("Docket"), "__all__")
		self.assertIsNone(programme_charge_service_types_for_parent("MICE Project"))

	def test_map_charge_for_docket_exhibit_charges(self):
		sq_row = {
			"service_type": "MICE",
			"item_code": "Item-Test",
			"unit_rate": 50,
		}
		mapped = map_sales_quote_charge_to_programme_charge_dict(
			sq_row, "SQU-TEST-002", "MICE Project Charges"
		)
		self.assertEqual(mapped.get("sales_quote_link"), "SQU-TEST-002")
		self.assertEqual(mapped.get("unit_rate"), 50)
		self.assertTrue(
			sales_quote_charge_service_types_equal(mapped.get("service_type"), "MICE")
		)

	def test_map_charge_maps_legacy_exhibits_to_mice(self):
		sq_row = {
			"service_type": "Exhibits",
			"item_code": "Item-Test",
			"unit_rate": 75,
		}
		mapped = map_sales_quote_charge_to_programme_charge_dict(
			sq_row, "SQU-TEST-003", "MICE Project Charges"
		)
		self.assertEqual(mapped.get("service_type"), "MICE")

	def test_copy_charge_breaks_for_reference_copies_weight_and_qty_rows(self):
		if not frappe.db.exists("DocType", "Sales Quote Weight Break"):
			self.skipTest("Sales Quote Weight Break not installed")

		source_name = frappe.db.get_value("Sales Quote Charge", {}, "name")
		if not source_name:
			self.skipTest("No Sales Quote Charge row in database")

		target_name = None
		try:
			dk = frappe.db.get_value("Docket", {}, "name")
			if not dk:
				self.skipTest("No Docket row in database")
			ch = frappe.get_doc(
				{
					"doctype": "MICE Project Charges",
					"parent": dk,
					"parenttype": "Docket",
					"parentfield": "charges",
					"service_type": "MICE",
					"item_code": create_test_item(f"Break Copy Ref {frappe.generate_hash(length=6)}"),
					"unit_rate": 1,
				}
			)
			ch.insert(ignore_permissions=True)
			target_name = ch.name

			wb = frappe.new_doc("Sales Quote Weight Break")
			wb.reference_doctype = "Sales Quote Charge"
			wb.reference_no = source_name
			wb.type = "Selling"
			wb.weight_break = 100
			wb.unit_rate = 12.5
			wb.currency = "USD"
			wb.insert(ignore_permissions=True)

			if frappe.db.exists("DocType", "Sales Quote Qty Break"):
				qb = frappe.new_doc("Sales Quote Qty Break")
				qb.reference_doctype = "Sales Quote Charge"
				qb.reference_no = source_name
				qb.type = "Cost"
				qb.qty_break = 5
				qb.unit_rate = 3
				qb.currency = "USD"
				qb.insert(ignore_permissions=True)

			copied = copy_charge_breaks_for_reference(
				"Sales Quote Charge",
				source_name,
				"MICE Project Charges",
				target_name,
			)
			self.assertGreaterEqual(copied, 1)

			weight_rows = frappe.get_all(
				"Sales Quote Weight Break",
				filters={
					"reference_doctype": "MICE Project Charges",
					"reference_no": target_name,
					"type": "Selling",
				},
				fields=["weight_break", "unit_rate"],
			)
			self.assertEqual(len(weight_rows), 1)
			self.assertEqual(frappe.utils.flt(weight_rows[0].weight_break), 100)
			self.assertEqual(frappe.utils.flt(weight_rows[0].unit_rate), 12.5)
		finally:
			if target_name:
				for break_dt in ("Sales Quote Weight Break", "Sales Quote Qty Break"):
					if frappe.db.exists("DocType", break_dt):
						frappe.db.delete(
							break_dt,
							{
								"reference_doctype": "MICE Project Charges",
								"reference_no": target_name,
							},
						)
				if frappe.db.exists("MICE Project Charges", target_name):
					frappe.delete_doc("MICE Project Charges", target_name, force=1, ignore_permissions=True)
			if source_name and frappe.db.exists("DocType", "Sales Quote Weight Break"):
				frappe.db.delete(
					"Sales Quote Weight Break",
					{
						"reference_doctype": "Sales Quote Charge",
						"reference_no": source_name,
						"weight_break": 100,
						"unit_rate": 12.5,
					},
				)
			if source_name and frappe.db.exists("DocType", "Sales Quote Qty Break"):
				frappe.db.delete(
					"Sales Quote Qty Break",
					{
						"reference_doctype": "Sales Quote Charge",
						"reference_no": source_name,
						"qty_break": 5,
						"unit_rate": 3,
					},
				)

	def _test_site_address(self):
		existing = frappe.db.get_value("Address", {}, "name")
		if existing:
			return existing
		addr = frappe.get_doc(
			{
				"doctype": "Address",
				"address_title": "SQ Programme Charges Test Site",
				"address_type": "Office",
				"address_line1": "1 Test St",
				"city": "Testville",
			}
		)
		addr.flags.ignore_mandatory = True
		addr.insert(ignore_permissions=True)
		return addr.name

	def _minimal_mice_sales_quote_with_charge(self, item_code):
		ex = frappe.new_doc("MICE Project")
		ex.project_name = f"Expo Break Copy {frappe.generate_hash(length=6)}"
		ex.customer = self.customer
		ex.show_open_date = today()
		ex.show_close_date = add_days(today(), 3)
		ex.insert(ignore_permissions=True)

		sq = frappe.get_doc(
			{
				"doctype": "Sales Quote",
				"quotation_type": "Regular",
				"naming_series": "SQU.#########",
				"company": self.company,
				"customer": self.customer,
				"date": today(),
				"valid_until": add_days(today(), 30),
				"shipper": self.shipper,
				"consignee": self.consignee,
				"main_service": "MICE",
				"exhibit": ex.name,
				"exhibit_show_open_date": today(),
				"exhibit_show_close_date": add_days(today(), 3),
				**self._sq_defaults,
			}
		)
		sq.append(
			"charges",
			{
				"service_type": "MICE",
				"sp_site": self._test_site_address(),
				"item_code": item_code,
				"unit_rate": 100,
			},
		)
		sq.insert()
		sq.submit()
		return sq

	def test_copy_sales_quote_charge_breaks_to_programme_parent_for_docket(self):
		if not frappe.db.exists("DocType", "Sales Quote Weight Break"):
			self.skipTest("Sales Quote Weight Break not installed")
		if not frappe.db.exists("DocType", "Docket"):
			self.skipTest("Docket not installed")

		item_code = create_test_item(f"Test Docket Break Item {frappe.generate_hash(length=6)}")
		sq = self._minimal_mice_sales_quote_with_charge(item_code)
		sq_charge = sq.charges[0].name

		wb = frappe.new_doc("Sales Quote Weight Break")
		wb.reference_doctype = "Sales Quote Charge"
		wb.reference_no = sq_charge
		wb.type = "Selling"
		wb.weight_break = 250
		wb.unit_rate = 18.5
		wb.currency = "USD"
		wb.insert(ignore_permissions=True)

		qb = None
		if frappe.db.exists("DocType", "Sales Quote Qty Break"):
			qb = frappe.new_doc("Sales Quote Qty Break")
			qb.reference_doctype = "Sales Quote Charge"
			qb.reference_no = sq_charge
			qb.type = "Cost"
			qb.qty_break = 10
			qb.unit_rate = 4.25
			qb.currency = "USD"
			qb.insert(ignore_permissions=True)

		dk = frappe.new_doc("Docket")
		dk.exhibit = sq.exhibit
		dk.exhibitor = sq.customer
		dk.sales_quote = sq.name
		dk.company = sq.company
		for fn in ("branch", "cost_center", "profit_center", "sales_rep", "operations_rep", "customer_service_rep"):
			val = sq.get(fn)
			if val:
				dk.set(fn, val)
		populate_programme_charges_from_sales_quote(dk, sq.name, clear_existing=True, service_types="__all__")
		dk.insert(ignore_permissions=True)
		copied = copy_sales_quote_charge_breaks_to_programme_parent(dk, sq.name)
		self.assertGreaterEqual(copied, 1)

		prog_charge = dk.charges[0].name
		weight_rows = frappe.get_all(
			"Sales Quote Weight Break",
			filters={
				"reference_doctype": "MICE Project Charges",
				"reference_no": prog_charge,
				"type": "Selling",
			},
			fields=["weight_break", "unit_rate"],
		)
		self.assertEqual(len(weight_rows), 1)
		self.assertEqual(frappe.utils.flt(weight_rows[0].weight_break), 250)
		self.assertEqual(frappe.utils.flt(weight_rows[0].unit_rate), 18.5)

		if qb:
			qty_rows = frappe.get_all(
				"Sales Quote Qty Break",
				filters={
					"reference_doctype": "MICE Project Charges",
					"reference_no": prog_charge,
					"type": "Cost",
				},
				fields=["qty_break", "unit_rate"],
			)
			self.assertEqual(len(qty_rows), 1)
			self.assertEqual(frappe.utils.flt(qty_rows[0].qty_break), 10)
			self.assertEqual(frappe.utils.flt(qty_rows[0].unit_rate), 4.25)
