# Copyright (c) 2026, AgilaSoft and Contributors

import uuid

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, flt, today

from logistics.air_freight.tests.test_helpers import (
	create_test_currency,
	create_test_item,
	create_test_unloco,
	setup_basic_master_data,
)
from logistics.utils.charges_calculation import (
	_apply_unit_break_to_rate_data,
	_charge_side_uses_unit_breaks,
	_fetch_rates_from_tariff_if_needed,
	_get_quantity_for_calculation_method,
	_resolve_unit_break_rate,
	_spread_row_qty_into_actual_data,
	calculate_charge_cost,
	calculate_charge_revenue,
	calculate_charge_row,
	container_type_counts_from_parent,
	realign_charge_row_quantities_from_parent,
)
from logistics.pricing_center.doctype.charge_unit_break.charge_unit_break import (
	get_unit_breaks,
	save_unit_breaks_for_reference,
)
from logistics.utils.sales_quote_programme_charges import copy_charge_breaks_for_reference


class TestChargeUnitBreaks(FrappeTestCase):
	def tearDown(self):
		frappe.db.rollback()

	def test_value_unit_type_uses_goods_value(self):
		actual_data = {"actual_goods_value": 50000, "actual_quantity": 0}
		qty = _get_quantity_for_calculation_method(actual_data, "Per Unit", "Value")
		self.assertEqual(qty, 50000)

	def test_job_unit_type_always_one_not_weight_fallback(self):
		"""Job must not use actual_quantity (weight/volume fallback) or qty inflates."""
		actual_data = {
			"actual_quantity": 100.0,
			"actual_weight": 100.0,
			"actual_volume": 8.0,
			"actual_pieces": 1.0,
		}
		qty = _get_quantity_for_calculation_method(actual_data, "Per Unit", "Job")
		self.assertEqual(qty, 1.0)
		self.assertEqual(
			_get_quantity_for_calculation_method(actual_data, "Per Unit", "Shipment"),
			1.0,
		)

	def test_realign_charge_row_quantities_job_uses_one_not_weight(self):
		parent = frappe._dict(doctype="Air Shipment", total_weight=500, total_volume=0, total_pieces=1)
		charge = frappe._dict(
			doctype="Air Shipment Charges",
			revenue_calculation_method="Per Unit",
			unit_type="Job",
			quantity=500,
			cost_calculation_method="Per Unit",
			cost_unit_type="Job",
			cost_quantity=500,
		)
		realign_charge_row_quantities_from_parent(charge, parent)
		self.assertEqual(charge.quantity, 1.0)
		self.assertEqual(charge.cost_quantity, 1.0)

	def test_calculate_charge_revenue_job_unit_on_air_shipment(self):
		parent = frappe._dict(doctype="Air Shipment", total_weight=500, total_volume=0, total_pieces=1)
		charge = frappe._dict(
			doctype="Air Shipment Charges",
			revenue_calculation_method="Per Unit",
			unit_type="Job",
			unit_rate=78000,
			quantity=500,
			currency="PHP",
			parenttype="Air Shipment",
			parent="ASP-TEST",
		)
		result = calculate_charge_revenue(charge, parent)
		self.assertTrue(result.get("success"))
		self.assertEqual(result.get("amount"), 78000.0)
		self.assertEqual(charge.quantity, 1.0)

	def test_calculate_charge_cost_job_unit_on_air_shipment(self):
		parent = frappe._dict(doctype="Air Shipment", total_weight=500, total_volume=0, total_pieces=1)
		charge = frappe._dict(
			doctype="Air Shipment Charges",
			cost_calculation_method="Per Unit",
			cost_unit_type="Job",
			unit_cost=12000,
			cost_quantity=500,
			cost_currency="PHP",
			parenttype="Air Shipment",
			parent="ASP-TEST",
		)
		result = calculate_charge_cost(charge, parent)
		self.assertTrue(result.get("success"))
		self.assertEqual(result.get("amount"), 12000.0)
		self.assertEqual(charge.cost_quantity, 1.0)

	def test_charge_side_uses_unit_breaks_flag(self):
		row = frappe._dict(
			use_unit_breaks=1,
			cost_use_unit_breaks=0,
			revenue_calculation_method="Per Unit",
			cost_calculation_method="Flat Rate",
		)
		self.assertTrue(_charge_side_uses_unit_breaks(row, True))
		self.assertFalse(_charge_side_uses_unit_breaks(row, False))

	def test_charge_side_uses_unit_breaks_requires_per_unit(self):
		row = frappe._dict(use_unit_breaks=1, revenue_calculation_method="Weight Break")
		self.assertFalse(_charge_side_uses_unit_breaks(row, True))
		row.revenue_calculation_method = "Per Unit"
		self.assertTrue(_charge_side_uses_unit_breaks(row, True))
		cost = frappe._dict(cost_use_unit_breaks=1, cost_calculation_method="Qty Break")
		self.assertFalse(_charge_side_uses_unit_breaks(cost, False))
		cost.cost_calculation_method = "Per Unit"
		self.assertTrue(_charge_side_uses_unit_breaks(cost, False))
		cr = frappe._dict(use_unit_breaks=1, calculation_method="Per Unit")
		self.assertTrue(_charge_side_uses_unit_breaks(cr, True))
		mice = frappe._dict(cost_use_unit_breaks=1, revenue_calculation_method="Per Unit")
		self.assertTrue(_charge_side_uses_unit_breaks(mice, False))

	def test_unit_breaks_checkbox_depends_on_per_unit(self):
		meta = frappe.get_meta("Sales Quote Charge")
		selling = meta.get_field("use_unit_breaks")
		self.assertIsNotNone(selling)
		self.assertIn("Per Unit", selling.depends_on or "")
		self.assertIn("revenue_calculation_method", selling.depends_on or "")
		cost = meta.get_field("cost_use_unit_breaks")
		self.assertIsNotNone(cost)
		self.assertIn("Per Unit", cost.depends_on or "")
		self.assertIn("cost_calculation_method", cost.depends_on or "")
		btn = meta.get_field("selling_unit_break")
		self.assertIn("use_unit_breaks", btn.depends_on or "")
		self.assertIn("Per Unit", btn.depends_on or "")
		tariff = frappe.get_meta("Tariff Charge")
		self.assertIn("Per Unit", (tariff.get_field("use_unit_breaks").depends_on or ""))
		self.assertIn(
			"revenue_calculation_method",
			tariff.get_field("use_unit_breaks").depends_on or "",
		)
		cr = frappe.get_meta("Change Request Charge")
		self.assertIn("calculation_method", (cr.get_field("use_unit_breaks").depends_on or ""))

	def test_resolve_unit_break_rate_picks_highest_matching_tier(self):
		if not frappe.db.exists("DocType", "Charge Unit Break"):
			self.skipTest("Charge Unit Break DocType not installed")

		ref_doctype = "Sales Quote Charge"
		ref_no = "TEST-UNIT-BREAK-001"
		for row in frappe.get_all(
			"Charge Unit Break",
			filters={"reference_doctype": ref_doctype, "reference_no": ref_no},
			pluck="name",
		):
			frappe.delete_doc("Charge Unit Break", row, force=1)

		for threshold, rate in ((100, 10), (500, 8), (1000, 5)):
			doc = frappe.new_doc("Charge Unit Break")
			doc.reference_doctype = ref_doctype
			doc.reference_no = ref_no
			doc.type = "Selling"
			doc.unit_type = "Weight"
			doc.unit_break = threshold
			doc.unit_rate = rate
			doc.currency = "USD"
			doc.insert(ignore_permissions=True, ignore_links=True)

		charge_doc = frappe._dict(doctype=ref_doctype, name=ref_no)
		applicable = _resolve_unit_break_rate(charge_doc, 750, "Selling", unit_type="Weight")
		self.assertIsNotNone(applicable)
		self.assertEqual(flt(applicable.get("unit_rate")), 8)

	def test_apply_unit_break_overrides_rate_data(self):
		if not frappe.db.exists("DocType", "Charge Unit Break"):
			self.skipTest("Charge Unit Break DocType not installed")

		ref_doctype = "Sales Quote Charge"
		ref_no = "TEST-UNIT-BREAK-002"
		for row in frappe.get_all(
			"Charge Unit Break",
			filters={"reference_doctype": ref_doctype, "reference_no": ref_no},
			pluck="name",
		):
			frappe.delete_doc("Charge Unit Break", row, force=1)

		doc = frappe.new_doc("Charge Unit Break")
		doc.reference_doctype = ref_doctype
		doc.reference_no = ref_no
		doc.type = "Selling"
		doc.unit_type = "TEU"
		doc.unit_break = 2
		doc.unit_rate = 150
		doc.currency = "USD"
		doc.insert(ignore_permissions=True, ignore_links=True)

		charge_doc = frappe._dict(
			doctype=ref_doctype,
			name=ref_no,
			use_unit_breaks=1,
			revenue_calculation_method="Per Unit",
			unit_type="TEU",
			currency="USD",
			uom="Nos",
		)
		rate_data = {"calculation_method": "Per Unit", "rate": 100, "unit_rate": 100, "currency": "USD"}
		actual_data = {"actual_teu": 4, "actual_quantity": 4}
		prefix = _apply_unit_break_to_rate_data(
			charge_doc, rate_data, actual_data, "TEU", "Selling", True
		)
		self.assertTrue(prefix)
		self.assertEqual(flt(rate_data.get("rate")), 150)

	def test_apply_unit_break_skipped_when_method_is_not_per_unit(self):
		charge_doc = frappe._dict(
			doctype="Sales Quote Charge",
			name="TEST-UNIT-BREAK-SKIP",
			use_unit_breaks=1,
			revenue_calculation_method="Weight Break",
			unit_type="TEU",
		)
		rate_data = {"calculation_method": "Weight Break", "rate": 100, "unit_rate": 100, "currency": "USD"}
		prefix = _apply_unit_break_to_rate_data(
			charge_doc, rate_data, {"actual_teu": 4}, "TEU", "Selling", True
		)
		self.assertIsNone(prefix)
		self.assertEqual(flt(rate_data.get("rate")), 100)

	def test_apply_unit_break_notes_rate_adjustment(self):
		if not frappe.db.exists("DocType", "Charge Unit Break"):
			self.skipTest("Charge Unit Break DocType not installed")

		ref_doctype = "Sales Quote Charge"
		ref_no = "TEST-UNIT-BREAK-NOTES"
		for row in frappe.get_all(
			"Charge Unit Break",
			filters={"reference_doctype": ref_doctype, "reference_no": ref_no},
			pluck="name",
		):
			frappe.delete_doc("Charge Unit Break", row, force=1)

		doc = frappe.new_doc("Charge Unit Break")
		doc.reference_doctype = ref_doctype
		doc.reference_no = ref_no
		doc.type = "Selling"
		doc.unit_type = "Weight"
		doc.unit_break = 500
		doc.unit_rate = 8
		doc.currency = "USD"
		doc.insert(ignore_permissions=True, ignore_links=True)

		charge_doc = frappe._dict(
			doctype=ref_doctype,
			name=ref_no,
			use_unit_breaks=1,
			unit_type="Weight",
			revenue_calculation_method="Per Unit",
			unit_rate=10,
			currency="USD",
			uom="Kg",
			quantity=750,
		)
		rate_data = {"calculation_method": "Per Unit", "rate": 10, "unit_rate": 10, "currency": "USD"}
		actual_data = {"actual_weight": 750, "actual_quantity": 750}
		prefix = _apply_unit_break_to_rate_data(
			charge_doc, rate_data, actual_data, "Weight", "Selling", True
		)
		self.assertIn("Unit Break", prefix)
		self.assertIn("adjusted from 10", prefix)
		self.assertIn("to 8", prefix)
		self.assertEqual(flt(charge_doc.unit_rate), 8)

	def test_spread_row_qty_into_actual_data_for_teu(self):
		actual_data = {"actual_teu": 0, "actual_quantity": 0}
		_spread_row_qty_into_actual_data(actual_data, "TEU", 4)
		self.assertEqual(actual_data["actual_teu"], 4)

	def test_calculate_charge_revenue_includes_unit_break_in_calc_notes(self):
		if not frappe.db.exists("DocType", "Charge Unit Break"):
			self.skipTest("Charge Unit Break DocType not installed")

		ref_doctype = "Sales Quote Charge"
		ref_no = "TEST-UNIT-BREAK-CALC"
		for row in frappe.get_all(
			"Charge Unit Break",
			filters={"reference_doctype": ref_doctype, "reference_no": ref_no},
			pluck="name",
		):
			frappe.delete_doc("Charge Unit Break", row, force=1)

		for threshold, rate in ((100, 10), (500, 8)):
			doc = frappe.new_doc("Charge Unit Break")
			doc.reference_doctype = ref_doctype
			doc.reference_no = ref_no
			doc.type = "Selling"
			doc.unit_type = "Weight"
			doc.unit_break = threshold
			doc.unit_rate = rate
			doc.currency = "USD"
			doc.insert(ignore_permissions=True, ignore_links=True)

		charge_doc = frappe._dict(
			doctype=ref_doctype,
			name=ref_no,
			use_unit_breaks=1,
			unit_type="Weight",
			revenue_calculation_method="Per Unit",
			unit_rate=10,
			currency="USD",
			uom="Kg",
			quantity=750,
			parenttype="Sales Quote",
			parent="SQ-TEST",
		)
		result = calculate_charge_revenue(charge_doc, parent_doc=frappe._dict(doctype="Sales Quote"))
		self.assertTrue(result.get("success"))
		notes = result.get("calc_notes") or ""
		self.assertIn("Unit Break", notes)
		self.assertIn("750", notes)
		self.assertIn("8", notes)


	def _ensure_container_type(self, code, teu=1):
		if frappe.db.exists("Container Type", code):
			return code
		doc = frappe.get_doc(
			{
				"doctype": "Container Type",
				"code": code,
				"description": code,
				"active": 1,
				"teu_count": teu,
			}
		)
		doc.flags.ignore_mandatory = True
		doc.insert(ignore_permissions=True, ignore_links=True)
		return doc.name

	def test_container_type_counts_from_parent(self):
		ct20 = self._ensure_container_type("UB-20FT", 1)
		ct40 = self._ensure_container_type("UB-40FT", 2)
		parent = frappe._dict(
			doctype="Sea Booking",
			containers=[
				frappe._dict(type=ct20),
				frappe._dict(type=ct20),
				frappe._dict(type=ct40),
			],
		)
		counts = container_type_counts_from_parent(parent)
		self.assertEqual(counts.get(ct20), 2)
		self.assertEqual(counts.get(ct40), 1)

	def test_save_and_get_container_type_unit_breaks(self):
		if not frappe.db.exists("DocType", "Charge Unit Break"):
			self.skipTest("Charge Unit Break DocType not installed")
		if not frappe.get_meta("Charge Unit Break").has_field("container_type"):
			self.skipTest("container_type not on Charge Unit Break")

		ct20 = self._ensure_container_type("UB-20FT", 1)
		ct40 = self._ensure_container_type("UB-40FT", 2)
		ref_doctype = "Tariff Charge"
		ref_no = "TEST-UB-CT-SAVE"
		for row in frappe.get_all(
			"Charge Unit Break",
			filters={"reference_doctype": ref_doctype, "reference_no": ref_no},
			pluck="name",
		):
			frappe.delete_doc("Charge Unit Break", row, force=1)

		saved = save_unit_breaks_for_reference(
			ref_doctype,
			ref_no,
			[
				{"container_type": ct20, "unit_rate": 100, "currency": "USD"},
				{"container_type": ct40, "unit_rate": 180, "currency": "USD"},
			],
			"Selling",
			unit_type="Container",
		)
		self.assertTrue(saved.get("success"))
		loaded = get_unit_breaks(ref_doctype, ref_no, "Selling")
		self.assertTrue(loaded.get("success"))
		rows = loaded.get("unit_breaks") or []
		self.assertEqual(len(rows), 2)
		by_type = {r.get("container_type"): r for r in rows}
		self.assertEqual(flt(by_type[ct20].get("unit_rate")), 100)
		self.assertEqual(flt(by_type[ct40].get("unit_rate")), 180)
		self.assertEqual(by_type[ct20].get("currency"), "USD")

	def test_apply_container_type_rates_uses_count_per_type(self):
		if not frappe.db.exists("DocType", "Charge Unit Break"):
			self.skipTest("Charge Unit Break DocType not installed")
		if not frappe.get_meta("Charge Unit Break").has_field("container_type"):
			self.skipTest("container_type not on Charge Unit Break")

		ct20 = self._ensure_container_type("UB-20FT", 1)
		ct40 = self._ensure_container_type("UB-40FT", 2)
		ref_doctype = "Sea Booking Charges"
		ref_no = "TEST-UB-CT-CALC"
		for row in frappe.get_all(
			"Charge Unit Break",
			filters={"reference_doctype": ref_doctype, "reference_no": ref_no},
			pluck="name",
		):
			frappe.delete_doc("Charge Unit Break", row, force=1)

		for ctype, rate in ((ct20, 100), (ct40, 180)):
			doc = frappe.new_doc("Charge Unit Break")
			doc.reference_doctype = ref_doctype
			doc.reference_no = ref_no
			doc.type = "Selling"
			doc.unit_type = "Container"
			doc.container_type = ctype
			doc.unit_rate = rate
			doc.currency = "USD"
			doc.insert(ignore_permissions=True, ignore_links=True)

		charge_doc = frappe._dict(
			doctype=ref_doctype,
			name=ref_no,
			use_unit_breaks=1,
			unit_type="Container",
			revenue_calculation_method="Per Unit",
			unit_rate=1,
			quantity=3,
			currency="USD",
			parenttype="Sea Booking",
			parent="SB-TEST",
		)
		parent = frappe._dict(
			doctype="Sea Booking",
			total_containers=3,
			containers=[
				frappe._dict(type=ct20),
				frappe._dict(type=ct20),
				frappe._dict(type=ct40),
			],
		)
		result = calculate_charge_revenue(charge_doc, parent)
		self.assertTrue(result.get("success"))
		self.assertAlmostEqual(flt(result.get("amount")), 380, places=2)
		self.assertEqual(flt(charge_doc.quantity), 3)
		self.assertAlmostEqual(flt(charge_doc.unit_rate), 380 / 3, places=4)
		self.assertIn("Container Type rates", result.get("calc_notes") or "")

	def test_apply_container_type_rate_single_size_qty(self):
		if not frappe.db.exists("DocType", "Charge Unit Break"):
			self.skipTest("Charge Unit Break DocType not installed")
		if not frappe.get_meta("Charge Unit Break").has_field("container_type"):
			self.skipTest("container_type not on Charge Unit Break")

		ct20 = self._ensure_container_type("UB-20FT", 1)
		ct40 = self._ensure_container_type("UB-40FT", 2)
		ref_doctype = "Sea Booking Charges"
		ref_no = "TEST-UB-CT-ONE"
		for row in frappe.get_all(
			"Charge Unit Break",
			filters={"reference_doctype": ref_doctype, "reference_no": ref_no},
			pluck="name",
		):
			frappe.delete_doc("Charge Unit Break", row, force=1)

		for ctype, rate in ((ct20, 100), (ct40, 180)):
			doc = frappe.new_doc("Charge Unit Break")
			doc.reference_doctype = ref_doctype
			doc.reference_no = ref_no
			doc.type = "Selling"
			doc.unit_type = "Container"
			doc.container_type = ctype
			doc.unit_rate = rate
			doc.currency = "USD"
			doc.insert(ignore_permissions=True, ignore_links=True)

		charge_doc = frappe._dict(
			doctype=ref_doctype,
			name=ref_no,
			use_unit_breaks=1,
			unit_type="Container",
			revenue_calculation_method="Per Unit",
			unit_rate=1,
			quantity=1,
			currency="USD",
			parenttype="Sea Booking",
			parent="SB-TEST",
		)
		parent = frappe._dict(
			doctype="Sea Booking",
			total_containers=2,
			containers=[frappe._dict(type=ct20), frappe._dict(type=ct20)],
		)
		result = calculate_charge_revenue(charge_doc, parent)
		self.assertTrue(result.get("success"))
		self.assertEqual(flt(result.get("amount")), 200)
		self.assertEqual(flt(charge_doc.quantity), 2)
		self.assertEqual(flt(charge_doc.unit_rate), 100)

	def test_resolve_container_type_exact_match(self):
		if not frappe.db.exists("DocType", "Charge Unit Break"):
			self.skipTest("Charge Unit Break DocType not installed")
		if not frappe.get_meta("Charge Unit Break").has_field("container_type"):
			self.skipTest("container_type not on Charge Unit Break")

		ct20 = self._ensure_container_type("UB-20FT", 1)
		ct40 = self._ensure_container_type("UB-40FT", 2)
		ref_doctype = "Sales Quote Charge"
		ref_no = "TEST-UB-CT-RESOLVE"
		for row in frappe.get_all(
			"Charge Unit Break",
			filters={"reference_doctype": ref_doctype, "reference_no": ref_no},
			pluck="name",
		):
			frappe.delete_doc("Charge Unit Break", row, force=1)

		for ctype, rate in ((ct20, 100), (ct40, 180)):
			doc = frappe.new_doc("Charge Unit Break")
			doc.reference_doctype = ref_doctype
			doc.reference_no = ref_no
			doc.type = "Selling"
			doc.unit_type = "Container"
			doc.container_type = ctype
			doc.unit_rate = rate
			doc.currency = "USD"
			doc.insert(ignore_permissions=True, ignore_links=True)

		charge_doc = frappe._dict(doctype=ref_doctype, name=ref_no)
		row = _resolve_unit_break_rate(
			charge_doc, 3, "Selling", unit_type="Container", container_type=ct40
		)
		self.assertIsNotNone(row)
		self.assertEqual(flt(row.get("unit_rate")), 180)


def _unit_breaks_for(reference_doctype, reference_no, record_type="Selling"):
	fields = ["unit_type", "unit_break", "unit_rate", "currency"]
	order_by = "unit_break asc"
	if frappe.get_meta("Charge Unit Break").has_field("container_type"):
		fields = ["unit_type", "container_type", "unit_break", "unit_rate", "currency"]
		order_by = "container_type asc, unit_break asc"
	return frappe.get_all(
		"Charge Unit Break",
		filters={
			"reference_doctype": reference_doctype,
			"reference_no": reference_no,
			"type": record_type,
		},
		fields=fields,
		order_by=order_by,
	)


class TestTariffUnitBreakCopy(FrappeTestCase):
	def setUp(self):
		if not frappe.db.exists("DocType", "Charge Unit Break"):
			self.skipTest("Charge Unit Break DocType not installed")
		data = setup_basic_master_data()
		self.company = data["company"]
		self.customer = data["customer"]
		create_test_currency("USD")
		self.item_code = create_test_item(f"UB-ITEM-{uuid.uuid4().hex[:8]}")

	def tearDown(self):
		frappe.db.rollback()

	def _make_tariff_with_teu_breaks(self, selling_tiers=None, cost_tiers=None, service_type="Air"):
		selling_tiers = selling_tiers if selling_tiers is not None else ((1, 100), (5, 80))
		tariff = frappe.get_doc(
			{
				"doctype": "Tariff",
				"tariff_name": f"UB-TARIFF-{uuid.uuid4().hex[:8]}",
				"tariff_type": "All Customers",
				"currency": "USD",
				"valid_from": today(),
				"valid_to": add_days(today(), 365),
				"is_active": 1,
			}
		)
		tariff.flags.ignore_mandatory = True
		tariff.insert(ignore_permissions=True, ignore_links=True)
		tariff.append(
			"rates",
			{
				"service_type": service_type,
				"charge_type": "Revenue",
				"item_code": self.item_code,
				"revenue_calculation_method": "Per Unit",
				"unit_rate": 50,
				"quantity": 1,
				"currency": "USD",
				"unit_type": "TEU",
				"tariff_valid_from": today(),
				"tariff_rate_active": 1,
			},
		)
		tariff.flags.ignore_mandatory = True
		tariff.save()
		rate_row = tariff.rates[-1]
		for threshold, rate in selling_tiers:
			doc = frappe.new_doc("Charge Unit Break")
			doc.reference_doctype = "Tariff Charge"
			doc.reference_no = rate_row.name
			doc.type = "Selling"
			doc.unit_type = "TEU"
			doc.unit_break = threshold
			doc.unit_rate = rate
			doc.currency = "USD"
			doc.insert(ignore_permissions=True, ignore_links=True)
		for threshold, rate in cost_tiers or ():
			doc = frappe.new_doc("Charge Unit Break")
			doc.reference_doctype = "Tariff Charge"
			doc.reference_no = rate_row.name
			doc.type = "Cost"
			doc.unit_type = "TEU"
			doc.unit_break = threshold
			doc.unit_rate = rate
			doc.currency = "USD"
			doc.insert(ignore_permissions=True, ignore_links=True)
		return tariff.name, rate_row.name

	def _minimal_sales_quote(self, **charge_extra):
		origin = create_test_unloco("USLAX", "Los Angeles", "LAX", "US", "Airport")
		dest = create_test_unloco("USJFK", "New York JFK", "JFK", "US", "Airport")
		sq = frappe.get_doc(
			{
				"doctype": "Sales Quote",
				"quotation_type": "Regular",
				"naming_series": "SQU.#########",
				"company": self.company,
				"customer": self.customer,
				"date": today(),
				"valid_until": add_days(today(), 30),
				"main_service": "Air",
				"origin_port": origin,
				"destination_port": dest,
			}
		)
		row = {
			"service_type": "Air",
			"charge_type": "Margin",
			"item_code": self.item_code,
			"revenue_calculation_method": "Per Unit",
			"unit_type": "TEU",
			"unit_rate": 1,
			"quantity": 1,
			"currency": "USD",
		}
		row.update(charge_extra)
		sq.append("charges", row)
		sq.flags.ignore_mandatory = True
		sq.insert(ignore_permissions=True, ignore_links=True)
		return sq

	def test_copy_charge_breaks_record_types_skips_cost(self):
		_tariff_name, tariff_row = self._make_tariff_with_teu_breaks(
			selling_tiers=((1, 100),),
			cost_tiers=((1, 40),),
		)
		sq = self._minimal_sales_quote()
		target = sq.charges[0].name
		copied = copy_charge_breaks_for_reference(
			"Tariff Charge",
			tariff_row,
			"Sales Quote Charge",
			target,
			record_types=("Selling",),
		)
		self.assertGreaterEqual(copied, 1)
		self.assertEqual(len(_unit_breaks_for("Sales Quote Charge", target, "Selling")), 1)
		self.assertEqual(len(_unit_breaks_for("Sales Quote Charge", target, "Cost")), 0)

	def test_calculate_charge_row_copies_teu_breaks_and_flags(self):
		tariff_name, _tariff_row = self._make_tariff_with_teu_breaks()
		sq = self._minimal_sales_quote()
		charge = sq.charges[0]
		out = calculate_charge_row(
			"Sales Quote Charge",
			"Sales Quote",
			sq.name,
			{
				"name": charge.name,
				"doctype": "Sales Quote Charge",
				"service_type": "Air",
				"charge_type": "Margin",
				"item_code": self.item_code,
				"revenue_tariff": tariff_name,
				"use_tariff_in_revenue": 1,
				"revenue_calculation_method": "Per Unit",
				"unit_type": "TEU",
				"currency": "USD",
			},
		)
		self.assertTrue(out.get("success"))
		self.assertEqual(cint_safe(out.get("row_updates", {}).get("use_unit_breaks")), 1)
		rows = _unit_breaks_for("Sales Quote Charge", charge.name, "Selling")
		self.assertEqual(len(rows), 2)
		self.assertEqual(flt(rows[0].unit_break), 1)
		self.assertEqual(flt(rows[0].unit_rate), 100)
		self.assertEqual(rows[0].currency, "USD")
		self.assertEqual(flt(rows[1].unit_break), 5)
		self.assertEqual(flt(rows[1].unit_rate), 80)

	def test_unsaved_charge_name_does_not_copy_breaks(self):
		tariff_name, _tariff_row = self._make_tariff_with_teu_breaks()
		new_name = f"new-sales-quote-charge-{uuid.uuid4().hex[:8]}"
		charge_doc = frappe._dict(
			doctype="Sales Quote Charge",
			name=new_name,
			item_code=self.item_code,
			service_type="Air",
			revenue_tariff=tariff_name,
			use_tariff_in_revenue=1,
		)
		self.assertEqual(len(_unit_breaks_for("Sales Quote Charge", new_name, "Selling")), 0)
		_fetch_rates_from_tariff_if_needed(charge_doc)
		self.assertEqual(cint_safe(charge_doc.use_unit_breaks), 1)
		self.assertEqual(len(_unit_breaks_for("Sales Quote Charge", new_name, "Selling")), 0)

	def test_hash_style_unsaved_charge_name_does_not_copy_breaks(self):
		"""Frappe mid-insert child names are hashes, not new-* — must not Dynamic-Link yet."""
		tariff_name, _tariff_row = self._make_tariff_with_teu_breaks()
		hash_name = uuid.uuid4().hex[:10]
		self.assertFalse(str(hash_name).startswith("new"))
		self.assertFalse(frappe.db.exists("Sales Quote Charge", hash_name))
		charge_doc = frappe._dict(
			doctype="Sales Quote Charge",
			name=hash_name,
			item_code=self.item_code,
			service_type="Air",
			revenue_tariff=tariff_name,
			use_tariff_in_revenue=1,
		)
		_fetch_rates_from_tariff_if_needed(charge_doc)
		self.assertEqual(cint_safe(charge_doc.use_unit_breaks), 1)
		self.assertEqual(len(_unit_breaks_for("Sales Quote Charge", hash_name, "Selling")), 0)

	def test_transport_order_insert_copies_tariff_unit_breaks_after_persist(self):
		"""MICE/desk create: validate runs before child db_insert; breaks copy in after_insert."""
		from logistics.air_freight.tests.test_helpers import (
			create_test_branch,
			create_test_consignee,
			create_test_cost_center,
			create_test_profit_center,
			create_test_shipper,
		)

		tariff_name, _tariff_row = self._make_tariff_with_teu_breaks(
			selling_tiers=((1, 100), (5, 80)),
			service_type="Transport",
		)
		create_test_unloco("USLAX", "Los Angeles", "LAX", "US", "Airport")
		create_test_unloco("USJFK", "New York JFK", "JFK", "US", "Airport")
		shipper = create_test_shipper()
		consignee = create_test_consignee()
		try:
			branch = create_test_branch(self.company)
			cost_center = create_test_cost_center(self.company)
			profit_center = create_test_profit_center(self.company)
		except Exception:
			branch = frappe.db.get_value("Branch", {"custom_company": self.company}, "name")
			cost_center = frappe.db.get_value(
				"Cost Center", {"company": self.company, "is_group": 0}, "name"
			)
			profit_center = frappe.db.get_value("Profit Center", {"company": self.company}, "name")

		order = frappe.get_doc(
			{
				"doctype": "Transport Order",
				"company": self.company,
				"customer": self.customer,
				"booking_date": today(),
				"scheduled_date": today(),
				"location_type": "UNLOCO",
				"location_from": "USLAX",
				"location_to": "USJFK",
				"transport_job_type": "Non-Container",
				"branch": branch,
				"cost_center": cost_center,
				"profit_center": profit_center,
			}
		)
		order.append(
			"legs",
			{
				"facility_type_from": "Shipper",
				"facility_from": shipper,
				"facility_type_to": "Consignee",
				"facility_to": consignee,
				"scheduled_date": today(),
				"transport_job_type": "Non-Container",
			},
		)
		order.append(
			"charges",
			{
				"service_type": "Transport",
				"charge_type": "Margin",
				"item_code": self.item_code,
				"revenue_tariff": tariff_name,
				"use_tariff_in_revenue": 1,
				"revenue_calculation_method": "Per Unit",
				"unit_type": "TEU",
				"unit_rate": 1,
				"quantity": 1,
				"currency": "USD",
			},
		)
		order.flags.ignore_mandatory = True
		order.insert(ignore_permissions=True, ignore_links=True)

		charge = order.charges[0]
		self.assertTrue(charge.name)
		self.assertFalse(str(charge.name).startswith("new"))
		self.assertTrue(frappe.db.exists("Transport Order Charges", charge.name))
		rows = _unit_breaks_for("Transport Order Charges", charge.name, "Selling")
		self.assertEqual(len(rows), 2)
		self.assertEqual(flt(rows[0].unit_break), 1)
		self.assertEqual(flt(rows[0].unit_rate), 100)
		self.assertEqual(flt(rows[1].unit_break), 5)
		self.assertEqual(flt(rows[1].unit_rate), 80)
		order.reload()
		self.assertEqual(cint_safe(order.charges[0].use_unit_breaks), 1)

	def test_sales_quote_save_copies_tariff_unit_breaks(self):
		tariff_name, _tariff_row = self._make_tariff_with_teu_breaks(selling_tiers=((2, 150), (10, 90)))
		sq = self._minimal_sales_quote(revenue_tariff=tariff_name, use_tariff_in_revenue=1)
		charge = sq.charges[0]
		self.assertTrue(charge.name)
		self.assertFalse(str(charge.name).startswith("new"))
		rows = _unit_breaks_for("Sales Quote Charge", charge.name, "Selling")
		self.assertEqual(len(rows), 2)
		self.assertEqual(flt(rows[0].unit_break), 2)
		self.assertEqual(flt(rows[0].unit_rate), 150)
		self.assertEqual(flt(rows[1].unit_break), 10)
		self.assertEqual(flt(rows[1].unit_rate), 90)
		sq.reload()
		self.assertEqual(cint_safe(sq.charges[0].use_unit_breaks), 1)

	def test_copy_container_type_unit_breaks(self):
		if not frappe.get_meta("Charge Unit Break").has_field("container_type"):
			self.skipTest("container_type not on Charge Unit Break")
		ct20 = "UB-20FT"
		if not frappe.db.exists("Container Type", ct20):
			doc = frappe.get_doc(
				{
					"doctype": "Container Type",
					"code": ct20,
					"description": ct20,
					"active": 1,
					"teu_count": 1,
				}
			)
			doc.flags.ignore_mandatory = True
			doc.insert(ignore_permissions=True, ignore_links=True)

		_tariff_name, tariff_row = self._make_tariff_with_teu_breaks(
			selling_tiers=(),
			service_type="Sea",
		)
		ub = frappe.new_doc("Charge Unit Break")
		ub.reference_doctype = "Tariff Charge"
		ub.reference_no = tariff_row
		ub.type = "Selling"
		ub.unit_type = "Container"
		ub.container_type = ct20
		ub.unit_rate = 100
		ub.currency = "USD"
		ub.insert(ignore_permissions=True, ignore_links=True)

		sq = self._minimal_sales_quote()
		target = sq.charges[0].name
		copied = copy_charge_breaks_for_reference(
			"Tariff Charge",
			tariff_row,
			"Sales Quote Charge",
			target,
			record_types=("Selling",),
		)
		self.assertGreaterEqual(copied, 1)
		rows = _unit_breaks_for("Sales Quote Charge", target, "Selling")
		self.assertEqual(len(rows), 1)
		self.assertEqual(rows[0].get("container_type"), ct20)
		self.assertEqual(flt(rows[0].unit_rate), 100)


def cint_safe(val):
	return int(flt(val) or 0)
