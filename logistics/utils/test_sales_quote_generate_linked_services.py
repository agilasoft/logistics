# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Generate Sales Quote linked services from main scope and container rows."""

from __future__ import annotations

import frappe
from frappe.tests.utils import FrappeTestCase

from logistics.pricing_center.doctype.sales_quote.sales_quote import (
	add_linked_service,
	create_linked_services_from_main,
	preview_linked_services_from_main,
)
from logistics.utils.linked_service_compat import linked_service_doctype


class TestSalesQuoteGenerateLinkedServices(FrappeTestCase):
	def setUp(self):
		if not frappe.db.exists("DocType", "Sales Quote"):
			self.skipTest("Sales Quote not installed")
		if not frappe.db.exists("DocType", linked_service_doctype()):
			self.skipTest("Linked Service not installed")
		self._created_container_types = []
		self._created_unlocos = []
		self._created_vehicle_types = []

	def tearDown(self):
		for name in self._created_container_types:
			if frappe.db.exists("Container Type", name):
				frappe.delete_doc("Container Type", name, force=True, ignore_permissions=True)
		for name in self._created_vehicle_types:
			if frappe.db.exists("Vehicle Type", name):
				frappe.delete_doc("Vehicle Type", name, force=True, ignore_permissions=True)
		for name in self._created_unlocos:
			if frappe.db.exists("UNLOCO", name):
				frappe.delete_doc("UNLOCO", name, force=True, ignore_permissions=True)

	def _base_quote(self, title: str, *, quotation_type="Regular", main_service="Sea"):
		doc = frappe.new_doc("Sales Quote")
		doc.quotation_type = quotation_type
		doc.main_service = main_service
		if quotation_type == "Project":
			doc.naming_series = "PQ.#####"
			doc.project_name = title
		elif quotation_type == "One-off":
			doc.naming_series = "OOQ.#####"
		else:
			doc.naming_series = "SQU.#########"
		doc.customer = frappe.db.get_value("Customer", {}, "name")
		if not doc.customer:
			self.skipTest("No Customer in system")
		doc.company = frappe.db.get_value("Company", {}, "name")
		doc.date = frappe.utils.today()
		doc.valid_until = frappe.utils.add_days(frappe.utils.today(), 30)
		doc.flags.ignore_validate = True
		doc.flags.ignore_mandatory = True
		doc.flags.ignore_links = True
		return doc

	def _save(self, doc):
		doc.flags.ignore_validate = True
		doc.flags.ignore_mandatory = True
		doc.flags.ignore_links = True
		doc.insert(ignore_permissions=True) if doc.is_new() else doc.save(ignore_permissions=True)
		return doc

	def _cleanup_quote(self, quote_name: str | None):
		if not quote_name or not frappe.db.exists("Sales Quote", quote_name):
			return
		for name in frappe.get_all(
			linked_service_doctype(),
			filters={"parent_booking_type": "Sales Quote", "parent_booking_name": quote_name},
			pluck="name",
		):
			frappe.delete_doc(linked_service_doctype(), name, force=True, ignore_permissions=True)
		frappe.delete_doc("Sales Quote", quote_name, force=True, ignore_permissions=True)

	def _two_container_types(self):
		names = frappe.get_all("Container Type", pluck="name", limit=2, order_by="name asc")
		while len(names) < 2:
			code = f"LSGEN{len(names) + 1}"
			if not frappe.db.exists("Container Type", code):
				row = frappe.new_doc("Container Type")
				row.code = code
				row.description = code
				row.active = 1
				row.insert(ignore_permissions=True)
				self._created_container_types.append(row.name)
				names.append(row.name)
			else:
				names.append(code)
		return names[0], names[1]

	def _link(self, doctype: str, filters=None):
		if not frappe.db.exists("DocType", doctype):
			return None
		return frappe.db.get_value(doctype, filters or {}, "name")

	def test_container_quantities_create_transport_services(self):
		type_a, type_b = self._two_container_types()
		sq = self._base_quote("SQ Generate Containers")
		sq.append(
			"containers",
			{"type": type_a, "size": "40ft", "delivery_modes": "CY/Door"},
		)
		sq.append(
			"containers",
			{"type": type_b, "size": "20ft", "delivery_modes": "CY/CY"},
		)
		quote_name = None
		try:
			self._save(sq)
			quote_name = sq.name
			add_linked_service(sq.name, "Sea")
			doc = frappe.get_doc("Sales Quote", sq.name)
			doc.append("charges", {"service_type": "Sea", "charge_type": "Margin"})
			doc.flags.ignore_validate = True
			doc.flags.ignore_mandatory = True
			doc.flags.ignore_links = True
			doc.save(ignore_permissions=True)
			charge_count = len(doc.charges)
			existing = {
				row.name
				for row in frappe.get_all(
					linked_service_doctype(),
					filters={
						"parent_booking_type": "Sales Quote",
						"parent_booking_name": sq.name,
					},
					fields=["name", "service_type"],
				)
				if row.service_type == "Sea"
			}
			self.assertEqual(len(existing), 1)

			preview = preview_linked_services_from_main(sq.name)
			proposals = preview["proposals"]
			self.assertEqual(len(proposals), 2)
			self.assertTrue(all(row["key"] == "transport_container" for row in proposals))
			self.assertEqual(proposals[0]["fields"]["container_type"], type_a)
			self.assertEqual(proposals[1]["fields"]["container_type"], type_b)
			self.assertIn(type_a, proposals[0]["label"])
			self.assertIn("40ft", proposals[0]["label"])

			create_linked_services_from_main(
				sq.name,
				[
					{
						"key": "transport_container",
						"container_row": proposals[0]["container_row"],
						"quantity": 2,
						"fields": {"container_type": "NOT-A-TYPE"},
					},
					{
						"key": "transport_container",
						"container_row": proposals[1]["container_row"],
						"quantity": 1,
						"fields": {"container_type": "NOT-A-TYPE"},
					},
				],
			)

			rows = frappe.get_all(
				linked_service_doctype(),
				filters={
					"parent_booking_type": "Sales Quote",
					"parent_booking_name": sq.name,
					"service_type": "Transport",
				},
				fields=["name", "container_type", "company", "quantity"],
				order_by="creation asc",
			)
			self.assertEqual(len(rows), 2)
			by_type = {row.container_type: row.quantity for row in rows}
			self.assertEqual(by_type[type_a], 2)
			self.assertEqual(by_type[type_b], 1)
			self.assertTrue(all(row.company == sq.company for row in rows))
			self.assertTrue(all(row.container_type != "NOT-A-TYPE" for row in rows))

			reloaded = frappe.get_doc("Sales Quote", sq.name)
			self.assertEqual(len(reloaded.charges), charge_count)
			still_there = frappe.get_all(
				linked_service_doctype(),
				filters={
					"parent_booking_type": "Sales Quote",
					"parent_booking_name": sq.name,
					"service_type": "Sea",
				},
				pluck="name",
			)
			self.assertEqual(set(still_there), existing)
		finally:
			self._cleanup_quote(quote_name)

	def test_zero_quantity_skips_container_row(self):
		type_a, type_b = self._two_container_types()
		sq = self._base_quote("SQ Generate Zero Qty")
		sq.append("containers", {"type": type_a, "size": "40ft"})
		sq.append("containers", {"type": type_b, "size": "20ft"})
		quote_name = None
		try:
			self._save(sq)
			quote_name = sq.name
			preview = preview_linked_services_from_main(sq.name)
			create_linked_services_from_main(
				sq.name,
				[
					{
						"key": "transport_container",
						"container_row": preview["proposals"][0]["container_row"],
						"quantity": 0,
					},
					{
						"key": "transport_container",
						"container_row": preview["proposals"][1]["container_row"],
						"quantity": 1,
					},
				],
			)
			rows = frappe.get_all(
				linked_service_doctype(),
				filters={
					"parent_booking_type": "Sales Quote",
					"parent_booking_name": sq.name,
				},
				fields=["container_type"],
			)
			self.assertEqual(len(rows), 1)
			self.assertEqual(rows[0].container_type, type_b)
		finally:
			self._cleanup_quote(quote_name)

	def test_quantity_above_cap_is_rejected(self):
		type_a, _type_b = self._two_container_types()
		sq = self._base_quote("SQ Generate Qty Cap")
		sq.append("containers", {"type": type_a})
		quote_name = None
		try:
			self._save(sq)
			quote_name = sq.name
			preview = preview_linked_services_from_main(sq.name)
			with self.assertRaises(frappe.ValidationError):
				create_linked_services_from_main(
					sq.name,
					[
						{
							"key": "transport_container",
							"container_row": preview["proposals"][0]["container_row"],
							"quantity": 51,
						}
					],
				)
			self.assertEqual(
				frappe.db.count(
					linked_service_doctype(),
					{"parent_booking_type": "Sales Quote", "parent_booking_name": sq.name},
				),
				0,
			)
		finally:
			self._cleanup_quote(quote_name)

	def test_customs_from_main_copies_header_fields(self):
		authority = self._ensure_customs_authority()
		broker = self._ensure_broker()
		category = self._ensure_charge_category()
		branch = self._link("Branch")
		sq = self._base_quote("SQ Generate Customs", main_service="Customs")
		sq.customs_authority = authority
		sq.declaration_type = "Import"
		sq.customs_broker = broker
		sq.customs_charge_category = category
		if branch:
			sq.branch = branch
		shipper = self._link("Shipper")
		consignee = self._link("Consignee")
		if shipper:
			sq.shipper = shipper
		if consignee:
			sq.consignee = consignee
		quote_name = None
		try:
			self._save(sq)
			quote_name = sq.name
			preview = preview_linked_services_from_main(sq.name)
			self.assertEqual(len(preview["proposals"]), 1)
			self.assertEqual(preview["proposals"][0]["key"], "customs_main")
			self.assertEqual(preview["proposals"][0]["service_type"], "Customs")

			result = create_linked_services_from_main(
				sq.name,
				[{"key": "customs_main", "quantity": 4, "fields": {"declaration_type": "Export"}}],
			)
			self.assertEqual(result["created"], 1)
			ls = frappe.get_doc(linked_service_doctype(), result["linked_services"][0])
			self.assertEqual(ls.service_type, "Customs")
			self.assertEqual(ls.customs_authority, authority)
			self.assertEqual(ls.declaration_type, "Import")
			self.assertEqual(ls.customs_broker, broker)
			self.assertEqual(ls.customs_charge_category, category)
			self.assertEqual(ls.company, sq.company)
			if branch:
				self.assertEqual(ls.branch, branch)
			if shipper:
				self.assertEqual(ls.shipper, shipper)
			if consignee:
				self.assertEqual(ls.consignee, consignee)
			self.assertEqual(ls.parent_booking_name, sq.name)
		finally:
			self._cleanup_quote(quote_name)

	def _ensure_unloco(self, code: str):
		if frappe.db.exists("UNLOCO", code):
			return code
		row = frappe.new_doc("UNLOCO")
		row.unlocode = code
		row.location_name = code
		row.is_active = 1
		row.insert(ignore_permissions=True)
		self._created_unlocos.append(row.name)
		return row.name

	def _ensure_vehicle_type(self, code: str):
		if frappe.db.exists("Vehicle Type", code):
			return code
		row = frappe.new_doc("Vehicle Type")
		row.code = code
		row.description = code
		row.is_active = 1
		row.insert(ignore_permissions=True)
		self._created_vehicle_types.append(row.name)
		return row.name

	def test_transport_from_main_copies_header_fields(self):
		origin = self._ensure_unloco("LSGO1")
		destination = self._ensure_unloco("LSGD1")
		vehicle = self._ensure_vehicle_type("LSGV1")
		container_type, _other = self._two_container_types()
		pick_mode = self._link("Pick and Drop Mode")
		drop_mode = pick_mode
		load_type = self._link("Load Type")
		transport_mode = self._link("Transport Mode")
		template, template_load, template_vehicle = self._compatible_template()

		sq = self._base_quote("SQ Generate Transport", main_service="Transport")
		sq.location_type = "UNLOCO"
		sq.location_from = origin
		sq.location_to = destination
		sq.vehicle_type = template_vehicle or vehicle
		sq.container_type = container_type
		sq.container_no = "LSGEN1234567"
		if pick_mode:
			sq.pick_mode = pick_mode
			sq.drop_mode = drop_mode
		if template and template_load and template_vehicle:
			sq.transport_template = template
			sq.load_type = template_load
			sq.vehicle_type = template_vehicle
		elif load_type:
			sq.load_type = load_type
		if transport_mode:
			sq.transport_mode = transport_mode
		quote_name = None
		try:
			self._save(sq)
			quote_name = sq.name
			preview = preview_linked_services_from_main(sq.name)
			self.assertEqual(len(preview["proposals"]), 1)
			self.assertEqual(preview["proposals"][0]["key"], "transport_main")
			result = create_linked_services_from_main(
				sq.name,
				[{"key": "transport_main", "fields": {"location_from": "IGNORED"}}],
			)
			ls = frappe.get_doc(linked_service_doctype(), result["linked_services"][0])
			self.assertEqual(ls.service_type, "Transport")
			self.assertEqual(ls.location_type, "UNLOCO")
			self.assertEqual(ls.location_from, origin)
			self.assertEqual(ls.location_to, destination)
			self.assertEqual(ls.vehicle_type, sq.vehicle_type)
			self.assertEqual(ls.container_type, container_type)
			self.assertEqual(ls.container_no, "LSGEN1234567")
			self.assertEqual(ls.company, sq.company)
			if pick_mode:
				self.assertEqual(ls.pick_mode, pick_mode)
				self.assertEqual(ls.drop_mode, drop_mode)
			if sq.transport_template:
				self.assertEqual(ls.transport_template, sq.transport_template)
			if sq.load_type:
				self.assertEqual(ls.load_type, sq.load_type)
			if transport_mode:
				self.assertEqual(ls.transport_mode, transport_mode)
		finally:
			self._cleanup_quote(quote_name)

	def test_preview_is_empty_without_source_data(self):
		sq = self._base_quote(
			"SQ Generate Empty", quotation_type="Project", main_service="Special Project"
		)
		quote_name = None
		try:
			self._save(sq)
			quote_name = sq.name
			preview = preview_linked_services_from_main(sq.name)
			self.assertEqual(preview["proposals"], [])
			result = create_linked_services_from_main(sq.name, [])
			self.assertEqual(result["created"], 0)
			self.assertEqual(
				frappe.db.count(
					linked_service_doctype(),
					{"parent_booking_type": "Sales Quote", "parent_booking_name": sq.name},
				),
				0,
			)
		finally:
			self._cleanup_quote(quote_name)

	def test_submitted_and_additional_charge_quotes_are_rejected(self):
		sq = self._base_quote(
			"SQ Generate Guards", quotation_type="Project", main_service="Special Project"
		)
		quote_name = None
		try:
			self._save(sq)
			quote_name = sq.name
			frappe.db.set_value("Sales Quote", sq.name, "docstatus", 1, update_modified=False)
			with self.assertRaises(frappe.ValidationError):
				preview_linked_services_from_main(sq.name)
			frappe.db.set_value("Sales Quote", sq.name, "docstatus", 0, update_modified=False)

			doc = frappe.get_doc("Sales Quote", sq.name)
			doc.additional_charge = 1
			doc.flags.ignore_validate = True
			doc.flags.ignore_mandatory = True
			doc.flags.ignore_links = True
			doc.save(ignore_permissions=True)
			with self.assertRaises(frappe.ValidationError):
				create_linked_services_from_main(sq.name, [])
		finally:
			if quote_name:
				frappe.db.set_value(
					"Sales Quote", quote_name, "docstatus", 0, update_modified=False
				)
			self._cleanup_quote(quote_name)

	def _ensure_customs_authority(self):
		name = self._link("Customs Authority")
		if name:
			return name
		doc = frappe.new_doc("Customs Authority")
		doc.code = "LSGEN-CA"
		doc.customs_authority_name = "Generate Test Authority"
		doc.insert(ignore_permissions=True)
		return doc.name

	def _ensure_broker(self):
		name = self._link("Broker", {"is_active": 1}) or self._link("Broker")
		if name:
			return name
		doc = frappe.new_doc("Broker")
		doc.code = "LSGEN-BR"
		doc.broker_name = "Generate Test Broker"
		doc.is_active = 1
		doc.insert(ignore_permissions=True)
		return doc.name

	def _ensure_charge_category(self):
		name = self._link("Charge Category", {"disabled": 0}) or self._link("Charge Category")
		if name:
			return name
		doc = frappe.new_doc("Charge Category")
		doc.category_name = "LSGEN Charge"
		doc.disabled = 0
		doc.insert(ignore_permissions=True)
		return doc.name

	def _compatible_template(self):
		template = self._link("Transport Template")
		if not template:
			return None, None, None
		from logistics.utils.transport_template_rules import get_template_constraints

		allowed = get_template_constraints(template).get("allowed_load_types") or []
		if not allowed:
			return None, None, None
		for load_type in allowed:
			vehicle = frappe.db.get_value(
				"Vehicle Type Load Types", {"load_type": load_type}, "parent"
			)
			if vehicle:
				return template, load_type, vehicle
		return None, None, None
