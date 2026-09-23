# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

from unittest.mock import patch

import frappe
from frappe.tests import UnitTestCase

from logistics.pricing_center.sales_quote_booking_creation import (
	_main_service_choice,
	_preview_main_service_creatability,
	_use_main_service_mode,
	get_sales_quote_booking_choices,
	quotation_type_supports_booking_creation,
)


class TestSalesQuoteBookingMainService(UnitTestCase):
	def _air_quote(self, *, with_charges=True, origin="HKHKG", destination="PHMNL"):
		sq = frappe.get_doc(
			{
				"doctype": "Sales Quote",
				"name": "SQU-TEST-MAIN",
				"quotation_type": "Regular",
				"docstatus": 1,
				"main_service": "Air",
				"origin_port": origin,
				"destination_port": destination,
				"direction": "Export",
				"company": "_Test Company",
				"customer": "_Test Customer",
			}
		)
		if with_charges:
			sq.append(
				"charges",
				{
					"service_type": "Air",
					"origin_port": origin,
					"destination_port": destination,
					"direction": "Export",
				},
			)
		return sq

	def test_main_service_choice_when_no_services_rows(self):
		sq = self._air_quote()
		sq.check_permission = lambda *a, **k: None

		with patch(
			"logistics.pricing_center.sales_quote_booking_creation.frappe.db.exists",
			return_value=True,
		), patch(
			"logistics.pricing_center.sales_quote_booking_creation.frappe.get_doc",
			return_value=sq,
		), patch(
			"logistics.pricing_center.sales_quote_booking_creation.charges_exist_for_service",
			return_value=True,
		), patch(
			"logistics.pricing_center.sales_quote_booking_creation.internal_job_matches_charges",
			return_value=True,
		):
			result = get_sales_quote_booking_choices("SQU-TEST-MAIN")

		self.assertEqual(len(result["choices"]), 1)
		choice = result["choices"][0]
		self.assertEqual(choice["mode"], "main")
		self.assertEqual(choice["job_type"], "Air Booking")
		self.assertTrue(choice["creatable"])

	def test_main_service_choice_when_services_rows_present(self):
		sq = self._air_quote()
		sq.check_permission = lambda *a, **k: None
		service_row = frappe._dict(service_type="Sea", job_type="Sea Booking")

		with patch(
			"logistics.pricing_center.sales_quote_booking_creation.frappe.db.exists",
			return_value=True,
		), patch(
			"logistics.pricing_center.sales_quote_booking_creation.frappe.get_doc",
			return_value=sq,
		), patch(
			"logistics.pricing_center.sales_quote_booking_creation._rows_for_form",
			return_value=[(1, service_row)],
		), patch(
			"logistics.pricing_center.sales_quote_booking_creation.charges_exist_for_service",
			return_value=True,
		), patch(
			"logistics.pricing_center.sales_quote_booking_creation.internal_job_matches_charges",
			return_value=True,
		):
			result = get_sales_quote_booking_choices("SQU-TEST-MAIN")

		self.assertEqual(len(result["choices"]), 1)
		choice = result["choices"][0]
		self.assertEqual(choice["mode"], "main")
		self.assertEqual(choice["job_type"], "Air Booking")
		self.assertNotEqual(choice.get("detail_idx"), 1)

	def test_use_main_service_mode_defaults_to_main(self):
		self.assertTrue(_use_main_service_mode(None, None))
		self.assertTrue(_use_main_service_mode(None, 1))
		self.assertTrue(_use_main_service_mode(1, 1))
		self.assertFalse(_use_main_service_mode(0, 1))

	def test_preview_main_service_creatable_with_scope_and_charges(self):
		sq = self._air_quote()
		with patch(
			"logistics.pricing_center.sales_quote_booking_creation.charges_exist_for_service",
			return_value=True,
		), patch(
			"logistics.pricing_center.sales_quote_booking_creation.internal_job_matches_charges",
			return_value=True,
		):
			flags = _preview_main_service_creatability(sq)
		self.assertTrue(flags["creatable"])

	def test_main_service_choice_not_creatable_without_charges(self):
		sq = self._air_quote(with_charges=False)
		with patch(
			"logistics.pricing_center.sales_quote_booking_creation.charges_exist_for_service",
			return_value=False,
		):
			choice = _main_service_choice(sq)
		self.assertIsNotNone(choice)
		self.assertFalse(choice["creatable"])
		self.assertIn("charge", (choice.get("not_creatable_message") or "").lower())

	def test_transport_project_quote_booking_choices(self):
		sq = frappe.get_doc(
			{
				"doctype": "Sales Quote",
				"name": "PQ-TEST-TRANSPORT",
				"quotation_type": "Project",
				"docstatus": 1,
				"main_service": "Transport",
				"location_from": "PHMNL",
				"location_to": "PHBAG",
				"company": "_Test Company",
				"customer": "_Test Customer",
			}
		)
		sq.append(
			"charges",
			{
				"service_type": "Transport",
				"location_from": "PHMNL",
				"location_to": "PHBAG",
			},
		)
		sq.check_permission = lambda *a, **k: None
		self.assertTrue(quotation_type_supports_booking_creation(sq))

		with patch(
			"logistics.pricing_center.sales_quote_booking_creation.frappe.db.exists",
			return_value=True,
		), patch(
			"logistics.pricing_center.sales_quote_booking_creation.frappe.get_doc",
			return_value=sq,
		), patch(
			"logistics.pricing_center.sales_quote_booking_creation.charges_exist_for_service",
			return_value=True,
		), patch(
			"logistics.pricing_center.sales_quote_booking_creation.internal_job_matches_charges",
			return_value=True,
		):
			result = get_sales_quote_booking_choices("PQ-TEST-TRANSPORT")

		self.assertEqual(len(result["choices"]), 1)
		choice = result["choices"][0]
		self.assertEqual(choice["job_type"], "Transport Order")
		self.assertTrue(choice["creatable"])

	def test_project_special_project_main_service_not_supported(self):
		sq = frappe._dict(
			{
				"quotation_type": "Project",
				"main_service": "Special Project",
				"additional_charge": 0,
			}
		)
		self.assertFalse(quotation_type_supports_booking_creation(sq))

	def test_main_service_virtual_row_scope_parameters_extractable(self):
		from logistics.pricing_center.sales_quote_booking_creation import _main_service_virtual_row
		from logistics.utils.sales_quote_charge_parameters import extract_sales_quote_charge_parameters

		sq = frappe._dict(
			{
				"main_service": "Transport",
				"transport_template": "TT-SCOPE",
				"load_type": "FCL",
				"vehicle_type": "10T",
				"location_from": "PHMNL",
				"location_to": "PHBAG",
				"origin_port": "PHMNL",
				"destination_port": "PHBAG",
				"transport_mode": "Road",
				"pick_mode": "Door",
				"drop_mode": "Port",
			}
		)
		row = _main_service_virtual_row(sq)
		params = extract_sales_quote_charge_parameters(row)
		self.assertEqual(params.get("transport_template"), "TT-SCOPE")
		self.assertEqual(params.get("location_from"), "PHMNL")
		self.assertEqual(params.get("transport_mode"), "Road")
		self.assertEqual(params.get("pick_mode"), "Door")

	def test_transport_scoped_preview_includes_transport_mode(self):
		from logistics.utils.sales_quote_charge_parameters import (
			extract_service_scoped_quote_parameters,
		)

		sq = frappe._dict(
			{
				"main_service": "Transport",
				"transport_mode": "Road",
				"load_type": "FCL",
				"transport_template": "TT-SCOPE",
			}
		)
		scoped = extract_service_scoped_quote_parameters(sq, "Transport")
		self.assertEqual(scoped.get("transport_mode"), "Road")
		self.assertEqual(scoped.get("load_type"), "FCL")

	def test_virtual_scope_row_parameters_not_shadowed_by_charge_group_legacy(self):
		from logistics.utils.sales_quote_charge_parameters import extract_sales_quote_charge_parameters

		row = frappe._dict(
			{
				"service_type": "Transport",
				"charge_group": "Origin",
				"transport_mode": "Road",
				"load_type": "FCL",
				"transport_template": "TT-SCOPE",
				"location_from": "PHMNL",
				"location_to": "PHBAG",
			}
		)
		params = extract_sales_quote_charge_parameters(row)
		self.assertEqual(params.get("transport_mode"), "Road")
		self.assertEqual(params.get("load_type"), "FCL")
		self.assertEqual(params.get("charge_group"), "Origin")

	def test_apply_transport_scope_fields_to_order_direct(self):
		from logistics.utils.sales_quote_charge_parameters import (
			apply_scope_fields_to_operational_doc,
		)

		scope_row = frappe._dict(
			{
				"service_type": "Transport",
				"transport_mode": "Road",
				"load_type": "FCL",
				"vehicle_type": "20FT-CH",
				"transport_template": "SH-CNSGN",
				"container_type": "CT-20FT",
				"location_type": "Transport Zone",
				"location_from": "0n6d4ss5dl",
				"location_to": "125d2ks571",
			}
		)
		order = frappe.new_doc("Transport Order")
		apply_scope_fields_to_operational_doc(order, scope_row, overwrite=True)
		self.assertEqual(order.transport_mode, "Road")
		self.assertEqual(order.load_type, "FCL")
		self.assertEqual(order.vehicle_type, "20FT-CH")
		self.assertEqual(order.transport_template, "SH-CNSGN")
		self.assertEqual(order.location_from, "0n6d4ss5dl")

	def test_sea_booking_scope_applies_load_type_with_charge_group_shadow(self):
		from logistics.utils.sales_quote_charge_parameters import (
			apply_scope_fields_to_operational_doc,
		)

		row = frappe._dict(
			{
				"service_type": "Sea",
				"charge_group": "Origin",
				"origin_port": "PHMNL",
				"destination_port": "PHBAG",
				"transport_mode": "Road",
				"load_type": "FCL",
				"direction": "Domestic",
				"shipping_line": "TEST-LINE",
			}
		)
		doc = frappe.new_doc("Sea Booking")
		apply_scope_fields_to_operational_doc(doc, row, overwrite=True)
		self.assertEqual(doc.origin_port, "PHMNL")
		self.assertEqual(doc.destination_port, "PHBAG")
		self.assertEqual(doc.transport_mode, "Road")
		self.assertEqual(doc.load_type, "FCL")
		self.assertEqual(doc.shipping_line, "TEST-LINE")

	def test_air_booking_scope_applies_house_type_and_load_type(self):
		from logistics.utils.sales_quote_charge_parameters import (
			apply_scope_fields_to_operational_doc,
		)

		row = frappe._dict(
			{
				"service_type": "Air",
				"charge_group": "Freight",
				"air_house_type": "Standard House",
				"airline": "PR",
				"origin_port": "HKHKG",
				"destination_port": "PHMNL",
				"load_type": "General",
				"transport_mode": "Air",
			}
		)
		doc = frappe.new_doc("Air Booking")
		apply_scope_fields_to_operational_doc(doc, row, overwrite=True)
		self.assertEqual(doc.house_type, "Standard House")
		self.assertEqual(doc.airline, "PR")
		self.assertEqual(doc.load_type, "General")
		self.assertEqual(doc.transport_mode, "Air")


class TestInferMainServiceFromTimeSensitiveQuote(UnitTestCase):
	def test_first_matching_charge_wins(self):
		from logistics.patches.v3_0_migrate_sales_quote_time_sensitive_main_service import (
			infer_main_service_from_charge_types,
		)

		self.assertEqual(infer_main_service_from_charge_types(["Air", "Transport"]), "Air")
		self.assertEqual(infer_main_service_from_charge_types(["transport"]), "Transport")
		self.assertEqual(infer_main_service_from_charge_types(["Customs"]), "Customs")
		self.assertEqual(infer_main_service_from_charge_types(["custom"]), "Customs")
		self.assertEqual(infer_main_service_from_charge_types([]), "Air")
		self.assertEqual(infer_main_service_from_charge_types(["Special Project"]), "Air")


class TestSalesQuoteTimeSensitiveDeadline(UnitTestCase):
	def test_deadline_required_when_ticked(self):
		sq = frappe.get_doc(
			{
				"doctype": "Sales Quote",
				"main_service": "Air",
				"is_time_sensitive": 1,
			}
		)
		with self.assertRaises(frappe.ValidationError):
			sq.validate_time_sensitive_deadline()

	def test_deadline_ok_when_set(self):
		sq = frappe.get_doc(
			{
				"doctype": "Sales Quote",
				"main_service": "Air",
				"is_time_sensitive": 1,
				"critical_deadline": "2099-01-01 12:00:00",
			}
		)
		sq.validate_time_sensitive_deadline()

	def test_deadline_skipped_when_unticked(self):
		sq = frappe.get_doc(
			{
				"doctype": "Sales Quote",
				"main_service": "Air",
				"is_time_sensitive": 0,
			}
		)
		sq.validate_time_sensitive_deadline()
