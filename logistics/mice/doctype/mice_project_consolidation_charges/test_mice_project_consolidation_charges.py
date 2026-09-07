# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Tests for MICE Project Consolidation Charges tariff-in-cost behaviour."""

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, cint, flt, today

from logistics.mice.doctype.mice_project_consolidation_charges.mice_project_consolidation_charges import (
	fetch_cost_tariff_rate,
)


class TestMICEProjectConsolidationCharges(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def _default_currency(self):
		company = frappe.defaults.get_defaults().get("company")
		if company:
			currency = frappe.db.get_value("Company", company, "default_currency")
			if currency:
				return currency
		return frappe.db.get_value("Currency", {"enabled": 1}, "name") or "USD"

	def _ensure_uom(self, name="Trip"):
		if frappe.db.exists("UOM", name):
			return name
		uom = frappe.get_doc({"doctype": "UOM", "uom_name": name, "enabled": 1})
		uom.insert(ignore_permissions=True)
		return uom.name

	def _charge_category(self):
		return frappe.db.get_value("Charge Category", {}, "name") or "Other"

	def _make_tariff_with_cost_rate(
		self,
		item_code,
		rate=250.0,
		currency=None,
		cost_uom=None,
		unit_rate=None,
		cost_quantity=None,
		cost_unit_type="Trip",
	):
		currency = currency or self._default_currency()
		tariff = frappe.get_doc(
			{
				"doctype": "Tariff",
				"tariff_name": f"MICE-CT-TAR-{frappe.generate_hash(length=8)}",
				"tariff_type": "All Customers",
				"currency": currency,
				"valid_from": today(),
				"valid_to": add_days(today(), 365),
				"is_active": 1,
			}
		)
		tariff.flags.ignore_mandatory = True
		tariff.insert(ignore_permissions=True)
		rate_row = {
			"service_type": "Air",
			"charge_type": "Cost",
			"item_code": item_code,
			"revenue_calculation_method": "Per Unit",
			"unit_rate": unit_rate if unit_rate is not None else rate,
			"quantity": 1,
			"currency": currency,
			"tariff_valid_from": today(),
			"tariff_rate_active": 1,
		}
		if cost_uom:
			rate_row["cost_uom"] = cost_uom
			rate_row["cost_calculation_method"] = "Per Unit"
			rate_row["unit_cost"] = rate
			rate_row["cost_currency"] = currency
			rate_row["cost_unit_type"] = cost_unit_type
			rate_row["cost_quantity"] = cost_quantity if cost_quantity is not None else 1
		tariff.append("rates", rate_row)
		tariff.flags.ignore_mandatory = True
		tariff.save(ignore_permissions=True)
		return tariff

	def _add_cost_unit_breaks(self, tariff, tiers, unit_type="Trip", currency=None):
		currency = currency or self._default_currency()
		rate_row = tariff.rates[-1]
		for threshold, rate in tiers:
			doc = frappe.new_doc("Charge Unit Break")
			doc.reference_doctype = "Tariff Charge"
			doc.reference_no = rate_row.name
			doc.type = "Cost"
			doc.unit_type = unit_type
			doc.unit_break = threshold
			doc.unit_rate = rate
			doc.currency = currency
			doc.insert(ignore_permissions=True)
		return rate_row.name

	def _minimal_mice_project(self, project_name="MICE CUB Test"):
		customer = frappe.db.get_value("Customer", {}, "name")
		if not customer:
			self.skipTest("No Customer in system")
		organizer_name = f"CUB Organizer {frappe.generate_hash(length=6)}"
		existing = frappe.db.get_value("MICE Organizer", {"organizer_name": organizer_name}, "name")
		if existing:
			organizer = existing
		else:
			org = frappe.new_doc("MICE Organizer")
			org.organizer_name = organizer_name
			org.organizer_type = "Company"
			org.customer = customer
			org.insert(ignore_permissions=True)
			organizer = org.name
		doc = frappe.new_doc("MICE Project")
		doc.project_name = project_name
		doc.organizer = organizer
		doc.show_open_date = today()
		doc.show_close_date = add_days(today(), 3)
		return doc

	def test_use_tariff_in_cost_fills_unit_rate_on_validate(self):
		if not frappe.db.exists("DocType", "MICE Project Consolidation Charges"):
			self.skipTest("MICE Project Consolidation Charges DocType not installed")
		if not frappe.db.exists("DocType", "Tariff"):
			self.skipTest("Tariff DocType not installed")

		item_code = frappe.db.get_value("Item", {"disabled": 0}, "name")
		if not item_code:
			self.skipTest("No Item in system")

		tariff_rate = 250.0
		currency = self._default_currency()
		cost_uom = self._ensure_uom("Trip")
		tariff = self._make_tariff_with_cost_rate(
			item_code,
			rate=tariff_rate,
			currency=currency,
			cost_uom=cost_uom,
			unit_rate=999.0,
			cost_quantity=2,
			cost_unit_type="Trip",
		)

		row = frappe.new_doc("MICE Project Consolidation Charges")
		row.charge_type = "Cost"
		row.charge_category = self._charge_category()
		row.revenue_calculation_method = "Per Unit"
		row.unit_rate = 1
		row.quantity = 9
		row.currency = currency
		row.item_code = item_code
		row.use_tariff_in_cost = 1
		row.cost_tariff = tariff.name
		row.validate()

		self.assertEqual(flt(row.unit_rate), tariff_rate)
		self.assertNotEqual(flt(row.unit_rate), 999.0)
		self.assertEqual(flt(row.quantity), 2)
		self.assertEqual(row.unit_type, "Trip")
		self.assertEqual(row.revenue_calculation_method, "Per Unit")
		self.assertEqual(flt(row.total_amount), tariff_rate * 2)
		self.assertEqual(cint(row.use_tariff_in_cost), 1)
		self.assertEqual(row.unit_of_measure, cost_uom)

	def test_fetch_cost_tariff_rate_whitelist(self):
		if not frappe.db.exists("DocType", "Tariff"):
			self.skipTest("Tariff DocType not installed")

		item_code = frappe.db.get_value("Item", {"disabled": 0}, "name")
		if not item_code:
			self.skipTest("No Item in system")

		tariff_rate = 175.0
		cost_uom = self._ensure_uom("Container")
		tariff = self._make_tariff_with_cost_rate(
			item_code,
			rate=tariff_rate,
			cost_uom=cost_uom,
			unit_rate=50.0,
			cost_quantity=4,
			cost_unit_type="Trip",
		)
		rate_data = fetch_cost_tariff_rate(tariff.name, item_code)
		self.assertIsNotNone(rate_data)
		self.assertEqual(flt(rate_data.get("rate")), tariff_rate)
		self.assertNotEqual(flt(rate_data.get("rate")), 50.0)
		self.assertEqual(rate_data.get("calculation_method"), "Per Unit")
		self.assertEqual(rate_data.get("uom"), cost_uom)
		self.assertEqual(flt(rate_data.get("quantity")), 4)
		self.assertEqual(rate_data.get("unit_type"), "Trip")
		self.assertEqual(cint(rate_data.get("has_cost_unit_breaks")), 0)
		self.assertEqual(rate_data.get("unit_breaks") or [], [])
		self.assertIsNone(fetch_cost_tariff_rate(tariff.name, "NO-SUCH-ITEM"))

	def test_fetch_cost_tariff_rate_falls_back_when_service_type_mismatches(self):
		"""MICE row + Customs/Air tariff line must still return rate/UOM via item-only fallback."""
		if not frappe.db.exists("DocType", "Tariff"):
			self.skipTest("Tariff DocType not installed")

		item_code = frappe.db.get_value("Item", {"disabled": 0}, "name")
		if not item_code:
			self.skipTest("No Item in system")

		tariff_rate = 1000.0
		cost_uom = self._ensure_uom("Trip")
		tariff = self._make_tariff_with_cost_rate(item_code, rate=tariff_rate, cost_uom=cost_uom)

		# Tariff line is Air; row service_type MICE must still resolve via fallback.
		rate_data = fetch_cost_tariff_rate(tariff.name, item_code, service_type="MICE")
		self.assertIsNotNone(rate_data)
		self.assertEqual(flt(rate_data.get("rate")), tariff_rate)
		self.assertEqual(rate_data.get("uom"), cost_uom)

		# Exact service match still works.
		rate_data_air = fetch_cost_tariff_rate(tariff.name, item_code, service_type="Air")
		self.assertIsNotNone(rate_data_air)
		self.assertEqual(flt(rate_data_air.get("rate")), tariff_rate)

	def test_validate_applies_tariff_with_mismatched_service_type(self):
		if not frappe.db.exists("DocType", "MICE Project Consolidation Charges"):
			self.skipTest("MICE Project Consolidation Charges DocType not installed")
		if not frappe.db.exists("DocType", "Tariff"):
			self.skipTest("Tariff DocType not installed")

		item_code = frappe.db.get_value("Item", {"disabled": 0}, "name")
		if not item_code:
			self.skipTest("No Item in system")

		tariff_rate = 420.0
		currency = self._default_currency()
		cost_uom = self._ensure_uom("Trip")
		tariff = self._make_tariff_with_cost_rate(
			item_code, rate=tariff_rate, currency=currency, cost_uom=cost_uom
		)

		row = frappe.new_doc("MICE Project Consolidation Charges")
		row.charge_type = "Cost"
		row.charge_category = self._charge_category()
		row.service_type = "MICE"
		row.revenue_calculation_method = "Per Unit"
		row.unit_rate = 1
		row.quantity = 1
		row.currency = currency
		row.item_code = item_code
		row.use_tariff_in_cost = 1
		row.cost_tariff = tariff.name
		row.validate()

		self.assertEqual(flt(row.unit_rate), tariff_rate)
		self.assertEqual(row.unit_of_measure, cost_uom)

	def test_fixed_amount_calculation_method(self):
		if not frappe.db.exists("DocType", "MICE Project Consolidation Charges"):
			self.skipTest("MICE Project Consolidation Charges DocType not installed")

		currency = self._default_currency()
		row = frappe.new_doc("MICE Project Consolidation Charges")
		row.charge_type = "Cost"
		row.charge_category = self._charge_category()
		row.revenue_calculation_method = "Fixed Amount"
		row.unit_rate = 1000
		row.quantity = 5
		row.currency = currency
		row.calculate_charge_amount()
		self.assertEqual(flt(row.base_amount), 1000)
		self.assertEqual(flt(row.total_amount), 1000)

	def test_calculation_method_field_options_match_tariff(self):
		if not frappe.db.exists("DocType", "MICE Project Consolidation Charges"):
			self.skipTest("MICE Project Consolidation Charges DocType not installed")

		meta = frappe.get_meta("MICE Project Consolidation Charges")
		df = meta.get_field("revenue_calculation_method")
		self.assertEqual(df.label, "Calculation Method")
		expected = (
			"Per Unit\nFixed Amount\nFlat Rate\nBase Plus Additional\nFirst Plus Additional\n"
			"Percentage\nLocation-based\nWeight Break\nQty Break\nPercentage Break"
		)
		self.assertEqual(df.options, expected)

	def test_unit_break_fields_and_unit_type_options(self):
		if not frappe.db.exists("DocType", "MICE Project Consolidation Charges"):
			self.skipTest("MICE Project Consolidation Charges DocType not installed")

		meta = frappe.get_meta("MICE Project Consolidation Charges")
		self.assertTrue(meta.has_field("cost_use_unit_breaks"))
		self.assertTrue(meta.has_field("cost_unit_break"))
		expected = (
			"Distance\nWeight\nChargeable Weight\nVolume\nPackage\nPiece\nContainer\nTEU\n"
			"Item Count\nOperation Time\nJob\nTrip\nHandling Unit\nValue"
		)
		self.assertEqual(meta.get_field("unit_type").options, expected)

	def test_fetch_cost_tariff_rate_returns_cost_unit_breaks(self):
		if not frappe.db.exists("DocType", "Tariff"):
			self.skipTest("Tariff DocType not installed")
		if not frappe.db.exists("DocType", "Charge Unit Break"):
			self.skipTest("Charge Unit Break DocType not installed")

		item_code = frappe.db.get_value("Item", {"disabled": 0}, "name")
		if not item_code:
			self.skipTest("No Item in system")

		currency = self._default_currency()
		cost_uom = self._ensure_uom("Trip")
		tariff = self._make_tariff_with_cost_rate(
			item_code, rate=50.0, currency=currency, cost_uom=cost_uom
		)
		self._add_cost_unit_breaks(tariff, [(10, 100), (20, 200)], currency=currency)

		rate_data = fetch_cost_tariff_rate(tariff.name, item_code)
		self.assertIsNotNone(rate_data)
		self.assertEqual(cint(rate_data.get("has_cost_unit_breaks")), 1)
		self.assertTrue(rate_data.get("tariff_rate_name"))
		tiers = rate_data.get("unit_breaks") or []
		self.assertEqual(len(tiers), 2)
		self.assertEqual(flt(tiers[0].get("unit_break")), 10)
		self.assertEqual(flt(tiers[0].get("unit_rate")), 100)
		self.assertEqual(flt(tiers[1].get("unit_break")), 20)
		self.assertEqual(flt(tiers[1].get("unit_rate")), 200)

	def test_mice_project_save_copies_cost_unit_breaks(self):
		if not frappe.db.exists("DocType", "MICE Project"):
			self.skipTest("MICE Project DocType not installed")
		if not frappe.db.exists("DocType", "Charge Unit Break"):
			self.skipTest("Charge Unit Break DocType not installed")
		if not frappe.db.exists("DocType", "Tariff"):
			self.skipTest("Tariff DocType not installed")

		item_code = frappe.db.get_value("Item", {"disabled": 0}, "name")
		if not item_code:
			self.skipTest("No Item in system")

		currency = self._default_currency()
		cost_uom = self._ensure_uom("Trip")
		tariff = self._make_tariff_with_cost_rate(
			item_code, rate=50.0, currency=currency, cost_uom=cost_uom, cost_quantity=15
		)
		self._add_cost_unit_breaks(tariff, [(10, 100), (20, 200)], currency=currency)

		doc = self._minimal_mice_project("MICE CUB Copy")
		doc.append(
			"consolidation_charges",
			{
				"charge_type": "Cost",
				"charge_category": self._charge_category(),
				"service_type": "Air",
				"item_code": item_code,
				"use_tariff_in_cost": 1,
				"cost_tariff": tariff.name,
				"revenue_calculation_method": "Per Unit",
				"unit_type": "Trip",
				"unit_rate": 1,
				"quantity": 15,
				"currency": currency,
			},
		)
		doc.insert(ignore_permissions=True)

		charge = doc.consolidation_charges[0]
		self.assertEqual(cint(charge.cost_use_unit_breaks), 1)
		rows = frappe.get_all(
			"Charge Unit Break",
			filters={
				"reference_doctype": "MICE Project Consolidation Charges",
				"reference_no": charge.name,
				"type": "Cost",
			},
			fields=["unit_break", "unit_rate", "currency"],
			order_by="unit_break asc",
		)
		self.assertEqual(len(rows), 2)
		self.assertEqual(flt(rows[0].unit_break), 10)
		self.assertEqual(flt(rows[0].unit_rate), 100)
		self.assertEqual(flt(rows[1].unit_break), 20)
		self.assertEqual(flt(rows[1].unit_rate), 200)
		# qty 15 → tier 10 @ 100
		self.assertEqual(flt(charge.unit_rate), 100)
		self.assertEqual(flt(charge.total_amount), 1500)

	def test_calculate_applies_cost_unit_break_tier_from_quantity(self):
		if not frappe.db.exists("DocType", "MICE Project"):
			self.skipTest("MICE Project DocType not installed")
		if not frappe.db.exists("DocType", "Charge Unit Break"):
			self.skipTest("Charge Unit Break DocType not installed")

		currency = self._default_currency()
		doc = self._minimal_mice_project("MICE CUB Apply")
		doc.append(
			"consolidation_charges",
			{
				"charge_type": "Cost",
				"charge_category": self._charge_category(),
				"revenue_calculation_method": "Per Unit",
				"unit_type": "Trip",
				"unit_rate": 50,
				"quantity": 25,
				"currency": currency,
				"cost_use_unit_breaks": 1,
			},
		)
		doc.insert(ignore_permissions=True)
		row = doc.consolidation_charges[0]

		for threshold, rate in ((10, 100), (20, 200)):
			ub = frappe.new_doc("Charge Unit Break")
			ub.reference_doctype = "MICE Project Consolidation Charges"
			ub.reference_no = row.name
			ub.type = "Cost"
			ub.unit_type = "Trip"
			ub.unit_break = threshold
			ub.unit_rate = rate
			ub.currency = currency
			ub.insert(ignore_permissions=True)

		row.quantity = 25
		row.calculate_charge_amount()
		self.assertEqual(flt(row.unit_rate), 200)
		self.assertEqual(flt(row.total_amount), 5000)

		row.quantity = 12
		row.calculate_charge_amount()
		self.assertEqual(flt(row.unit_rate), 100)
		self.assertEqual(flt(row.total_amount), 1200)

	def _ensure_charge_category(self, name, apply_95_5=0):
		if not frappe.db.exists("DocType", "Charge Category"):
			self.skipTest("Charge Category DocType not installed")
		if frappe.db.exists("Charge Category", name):
			frappe.db.set_value("Charge Category", name, "apply_95_5_rule", cint(apply_95_5))
			return name
		cat = frappe.get_doc(
			{
				"doctype": "Charge Category",
				"category_name": name,
				"apply_95_5_rule": cint(apply_95_5),
			}
		)
		cat.insert(ignore_permissions=True)
		return cat.name

	def _new_consolidation_row(self, charge_category, **kwargs):
		row = frappe.new_doc("MICE Project Consolidation Charges")
		row.charge_type = "Cost"
		row.charge_category = charge_category
		row.revenue_calculation_method = "Fixed Amount"
		row.unit_rate = 100
		row.quantity = 1
		row.currency = self._default_currency()
		for key, value in kwargs.items():
			row.set(key, value)
		return row

	def test_taxes_section_fields_match_sales_quote(self):
		if not frappe.db.exists("DocType", "MICE Project Consolidation Charges"):
			self.skipTest("MICE Project Consolidation Charges DocType not installed")
		if not frappe.db.exists("DocType", "Sales Quote Charge"):
			self.skipTest("Sales Quote Charge DocType not installed")

		meta = frappe.get_meta("MICE Project Consolidation Charges")
		sq_meta = frappe.get_meta("Sales Quote Charge")
		for fieldname in (
			"freight_taxes_section",
			"category_apply_95_5_rule",
			"apply_95_5_rule",
			"taxable_freight_item",
			"taxable_freight_item_tax_template",
		):
			self.assertTrue(meta.has_field(fieldname), fieldname)
			ours = meta.get_field(fieldname)
			theirs = sq_meta.get_field(fieldname)
			self.assertEqual(ours.fieldtype, theirs.fieldtype, fieldname)
			self.assertEqual(ours.label, theirs.label, fieldname)
			self.assertEqual(ours.depends_on, theirs.depends_on, fieldname)
		self.assertEqual(
			meta.get_field("category_apply_95_5_rule").fetch_from,
			"charge_category.apply_95_5_rule",
		)
		self.assertEqual(
			meta.get_field("freight_taxes_section").depends_on,
			"eval:doc.category_apply_95_5_rule",
		)

	def test_apply_95_5_requires_taxable_freight_item(self):
		if not frappe.db.exists("DocType", "MICE Project Consolidation Charges"):
			self.skipTest("MICE Project Consolidation Charges DocType not installed")

		freight = self._ensure_charge_category(
			f"95-5-ON-{frappe.generate_hash(length=6)}", apply_95_5=1
		)
		row = self._new_consolidation_row(freight, apply_95_5_rule=1)
		with self.assertRaises(frappe.ValidationError):
			row.validate()

	def test_non_95_5_category_clears_tax_fields(self):
		if not frappe.db.exists("DocType", "MICE Project Consolidation Charges"):
			self.skipTest("MICE Project Consolidation Charges DocType not installed")

		other = self._ensure_charge_category(
			f"95-5-OFF-{frappe.generate_hash(length=6)}", apply_95_5=0
		)
		row = self._new_consolidation_row(
			other,
			apply_95_5_rule=1,
			taxable_freight_item="ITEM-TAX",
			taxable_freight_item_tax_template="TMPL",
		)
		row.validate()
		self.assertEqual(cint(row.apply_95_5_rule), 0)
		self.assertFalse(row.taxable_freight_item)
		self.assertFalse(row.taxable_freight_item_tax_template)

