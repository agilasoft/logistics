# Copyright (c) 2026, www.agilasoft.com and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today
from logistics.air_freight.tests.test_helpers import (
	setup_basic_master_data,
	create_test_shipper,
	create_test_consignee,
	create_test_unloco,
	create_test_branch,
	create_test_cost_center,
	create_test_profit_center,
)


class TestSeaShipment(FrappeTestCase):
	"""Test cases for Sea Shipment doctype"""

	def setUp(self):
		"""Set up test data"""
		data = setup_basic_master_data()
		self.company = data["company"]
		self.customer = data["customer"]
		self.shipper = create_test_shipper()
		self.consignee = create_test_consignee()
		create_test_unloco("USLAX", "Los Angeles", "LAX", "US", "Airport")
		create_test_unloco("USJFK", "New York JFK", "JFK", "US", "Airport")
		try:
			self.branch = create_test_branch(self.company)
			self.cost_center = create_test_cost_center(self.company)
			self.profit_center = create_test_profit_center(self.company)
		except Exception:
			self.branch = frappe.db.get_value("Branch", {"custom_company": self.company}, "name")
			self.cost_center = frappe.db.get_value("Cost Center", {"company": self.company, "is_group": 0}, "name")
			self.profit_center = frappe.db.get_value("Profit Center", {"company": self.company}, "name")

	def tearDown(self):
		frappe.db.rollback()

	def test_sea_shipment_creation(self):
		"""Test creating a basic Sea Shipment"""
		shipment = frappe.get_doc({
			"doctype": "Sea Shipment",
			"booking_date": today(),
			"company": self.company,
			"local_customer": self.customer,
			"shipper": self.shipper,
			"consignee": self.consignee,
			"origin_port": "USLAX",
			"destination_port": "USJFK",
			"branch": self.branch,
			"cost_center": self.cost_center,
			"profit_center": self.profit_center,
		})
		shipment.insert()

		self.assertIsNotNone(shipment.name)
		self.assertEqual(shipment.company, self.company)
		self.assertEqual(shipment.local_customer, self.customer)

	def test_sea_shipment_required_fields_enforced_on_submit(self):
		"""Party/routing/booking links are enforced on submit; draft save is allowed without them."""
		shipment = frappe.get_doc({
			"doctype": "Sea Shipment",
			"booking_date": today(),
			"company": self.company,
			"branch": self.branch,
			"cost_center": self.cost_center,
			"profit_center": self.profit_center,
		})
		shipment.insert()
		self.assertTrue(shipment.name)
		with self.assertRaises(frappe.ValidationError):
			shipment.submit()

	def test_sea_shipment_with_packages(self):
		"""Test creating Sea Shipment with packages"""
		shipment = frappe.get_doc({
			"doctype": "Sea Shipment",
			"booking_date": today(),
			"company": self.company,
			"local_customer": self.customer,
			"shipper": self.shipper,
			"consignee": self.consignee,
			"origin_port": "USLAX",
			"destination_port": "USJFK",
			"branch": self.branch,
			"cost_center": self.cost_center,
			"profit_center": self.profit_center,
		})
		shipment.append("packages", {
			"package_type": "Box",
			"quantity": 10,
			"weight": 100,
			"volume": 0.5,
		})
		shipment.insert()

		self.assertEqual(len(shipment.packages), 1)
		self.assertEqual(shipment.packages[0].quantity, 10)

	def test_sea_booking_applies_sea_freight_settings_accounting_defaults(self):
		"""New Sea Booking should get branch, cost center, and profit center from Sea Freight Settings when blank."""
		branch = create_test_branch(self.company, "SF Settings Branch SBK")
		cost_center = create_test_cost_center(self.company, "SF Settings CC SBK")
		profit_center = create_test_profit_center(self.company, "SF Settings PC SBK", code="SF-SBK-PC")

		settings = frappe.get_doc("Sea Freight Settings")
		settings.default_branch = branch
		settings.default_cost_center = cost_center
		settings.default_profit_center = profit_center
		settings.default_company = self.company
		settings.save(ignore_permissions=True)

		booking = frappe.get_doc({
			"doctype": "Sea Booking",
			"booking_date": today(),
			"company": self.company,
			"local_customer": self.customer,
			"direction": "Export",
			"shipper": self.shipper,
			"consignee": self.consignee,
			"origin_port": "USLAX",
			"destination_port": "USJFK",
		})
		booking.insert()

		self.assertEqual(booking.branch, branch)
		self.assertEqual(booking.cost_center, cost_center)
		self.assertEqual(booking.profit_center, profit_center)

	def test_sea_booking_settings_defaults_do_not_override_existing_accounting(self):
		"""Sea Freight Settings should only fill empty accounting fields."""
		settings_branch = create_test_branch(self.company, "SF Branch A")
		settings_cc = create_test_cost_center(self.company, "SF CC A")
		settings_pc = create_test_profit_center(self.company, "SF PC A", code="SF-PC-A")
		manual_branch = create_test_branch(self.company, "SF Manual Branch")

		settings = frappe.get_doc("Sea Freight Settings")
		settings.default_branch = settings_branch
		settings.default_cost_center = settings_cc
		settings.default_profit_center = settings_pc
		settings.default_company = self.company
		settings.save(ignore_permissions=True)

		booking = frappe.get_doc({
			"doctype": "Sea Booking",
			"booking_date": today(),
			"company": self.company,
			"local_customer": self.customer,
			"direction": "Export",
			"shipper": self.shipper,
			"consignee": self.consignee,
			"origin_port": "USLAX",
			"destination_port": "USJFK",
			"branch": manual_branch,
		})
		booking.insert()

		self.assertEqual(booking.branch, manual_branch)
		self.assertEqual(booking.cost_center, settings_cc)
		self.assertEqual(booking.profit_center, settings_pc)

	def test_sea_freight_settings_skips_when_default_company_mismatch(self):
		"""When Default Company is set, defaults apply only if it matches the document company."""
		from unittest.mock import patch

		from logistics.sea_freight.sea_freight_settings_defaults import (
			apply_accounting_defaults_from_sea_freight_settings,
		)

		branch = create_test_branch(self.company, "SF Mismatch Branch")

		class _FakeSettings:
			default_company = "Nonexistent Company For Mismatch Test"
			default_branch = branch
			default_cost_center = None
			default_profit_center = None

		doc = frappe.get_doc({"doctype": "Sea Booking", "company": self.company})
		with patch(
			"logistics.sea_freight.sea_freight_settings_defaults.frappe.get_single",
			return_value=_FakeSettings(),
		):
			apply_accounting_defaults_from_sea_freight_settings(doc)

		self.assertFalse(doc.branch)

	def test_sea_shipment_applies_sea_freight_settings_accounting_defaults(self):
		"""New Sea Shipment must receive accounting defaults from Sea Freight Settings (required Account fields)."""
		branch = create_test_branch(self.company, "SF Shipment Branch")
		cc = create_test_cost_center(self.company, "SF Shipment CC")
		pc = create_test_profit_center(self.company, "SF Shipment PC", code="SF-SSP-PC")

		settings = frappe.get_doc("Sea Freight Settings")
		settings.default_branch = branch
		settings.default_cost_center = cc
		settings.default_profit_center = pc
		settings.default_company = self.company
		settings.save(ignore_permissions=True)

		booking = frappe.get_doc({
			"doctype": "Sea Booking",
			"booking_date": today(),
			"company": self.company,
			"local_customer": self.customer,
			"direction": "Export",
			"shipper": self.shipper,
			"consignee": self.consignee,
			"origin_port": "USLAX",
			"destination_port": "USJFK",
			"branch": branch,
			"cost_center": cc,
			"profit_center": pc,
		})
		booking.insert()

		shipment = frappe.get_doc({
			"doctype": "Sea Shipment",
			"booking_date": today(),
			"company": self.company,
			"local_customer": self.customer,
			"shipper": self.shipper,
			"consignee": self.consignee,
			"origin_port": "USLAX",
			"destination_port": "USJFK",
			"direction": "Export",
			"sea_booking": booking.name,
		})
		shipment.insert()

		self.assertEqual(shipment.branch, branch)
		self.assertEqual(shipment.cost_center, cc)
		self.assertEqual(shipment.profit_center, pc)

	def test_transport_order_from_sea_shipment_filters_packages_by_container(self):
		"""Creating a Transport Order from a multi-container sea shipment copies only cargo for the chosen container."""
		from logistics.utils.container_validation import calculate_iso6346_check_digit, normalize_container_number
		from logistics.utils.module_integration import create_transport_order_from_sea_shipment

		def _iso_container(serial6: str) -> str:
			base = "MSCU" + serial6
			return base + str(calculate_iso6346_check_digit(base + "0"))

		cn_a = _iso_container("123456")
		cn_b = _iso_container("789012")

		ct = frappe.db.get_value("Container Type", {"active": 1}, "name")
		if not ct:
			ct = frappe.get_doc(
				{
					"doctype": "Container Type",
					"code": "TST-TO-CT",
					"description": "Test container type for TO filter test",
					"active": 1,
				}
			).insert(ignore_permissions=True).name

		uom = frappe.db.get_value("UOM", {"enabled": 1}, "name")
		self.assertTrue(uom)

		comms = frappe.get_all("Commodity", filters={"active": 1}, limit=2, pluck="name")
		while len(comms) < 2:
			sfx = frappe.generate_hash(length=4)
			frappe.get_doc(
				{"doctype": "Commodity", "commodity_name": f"TST-TO {sfx}", "active": 1}
			).insert(ignore_permissions=True)
			comms = frappe.get_all("Commodity", filters={"active": 1}, limit=2, pluck="name")

		booking = frappe.get_doc(
			{
				"doctype": "Sea Booking",
				"booking_date": today(),
				"company": self.company,
				"local_customer": self.customer,
				"direction": "Export",
				"shipper": self.shipper,
				"consignee": self.consignee,
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"branch": self.branch,
				"cost_center": self.cost_center,
				"profit_center": self.profit_center,
			}
		)
		booking.insert()

		shipment = frappe.get_doc(
			{
				"doctype": "Sea Shipment",
				"booking_date": today(),
				"company": self.company,
				"local_customer": self.customer,
				"shipper": self.shipper,
				"consignee": self.consignee,
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"direction": "Export",
				"sea_booking": booking.name,
				"branch": self.branch,
				"cost_center": self.cost_center,
				"profit_center": self.profit_center,
				"container_type": ct,
			}
		)
		shipment.append(
			"packages",
			{"commodity": comms[0], "no_of_packs": 1, "uom": uom, "container": cn_a},
		)
		shipment.append(
			"packages",
			{"commodity": comms[1], "no_of_packs": 2, "uom": uom, "container": cn_b},
		)
		shipment.insert()
		frappe.db.commit()

		with self.assertRaises(frappe.ValidationError):
			create_transport_order_from_sea_shipment(shipment.name)

		res = create_transport_order_from_sea_shipment(shipment.name, container_no=cn_b)
		to = frappe.get_doc("Transport Order", res["transport_order"])
		self.assertEqual(normalize_container_number(to.container_no), normalize_container_number(cn_b))
		self.assertEqual(len(to.packages), 1)
		self.assertEqual(to.packages[0].commodity, comms[1])

	def test_transport_order_from_sea_shipment_uses_internal_job_detail_container_no(self):
		"""When Internal Job Detail has container_no, create without API container_no still scopes packages."""
		from logistics.utils.container_validation import calculate_iso6346_check_digit, normalize_container_number
		from logistics.utils.module_integration import create_transport_order_from_sea_shipment

		def _iso_container(serial6: str) -> str:
			base = "MSCU" + serial6
			return base + str(calculate_iso6346_check_digit(base + "0"))

		cn_a = _iso_container("223456")
		cn_b = _iso_container("889012")

		ct = frappe.db.get_value("Container Type", {"active": 1}, "name")
		if not ct:
			ct = frappe.get_doc(
				{
					"doctype": "Container Type",
					"code": "TST-TO-IJ-CT",
					"description": "Test container type for IJ container_no test",
					"active": 1,
				}
			).insert(ignore_permissions=True).name

		uom = frappe.db.get_value("UOM", {"enabled": 1}, "name")
		self.assertTrue(uom)

		comms = frappe.get_all("Commodity", filters={"active": 1}, limit=2, pluck="name")
		while len(comms) < 2:
			sfx = frappe.generate_hash(length=4)
			frappe.get_doc(
				{"doctype": "Commodity", "commodity_name": f"TST-IJ {sfx}", "active": 1}
			).insert(ignore_permissions=True)
			comms = frappe.get_all("Commodity", filters={"active": 1}, limit=2, pluck="name")

		booking = frappe.get_doc(
			{
				"doctype": "Sea Booking",
				"booking_date": today(),
				"company": self.company,
				"local_customer": self.customer,
				"direction": "Export",
				"shipper": self.shipper,
				"consignee": self.consignee,
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"branch": self.branch,
				"cost_center": self.cost_center,
				"profit_center": self.profit_center,
			}
		)
		booking.insert()

		shipment = frappe.get_doc(
			{
				"doctype": "Sea Shipment",
				"booking_date": today(),
				"company": self.company,
				"local_customer": self.customer,
				"shipper": self.shipper,
				"consignee": self.consignee,
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"direction": "Export",
				"sea_booking": booking.name,
				"branch": self.branch,
				"cost_center": self.cost_center,
				"profit_center": self.profit_center,
				"container_type": ct,
			}
		)
		shipment.append(
			"packages",
			{"commodity": comms[0], "no_of_packs": 1, "uom": uom, "container": cn_a},
		)
		shipment.append(
			"packages",
			{"commodity": comms[1], "no_of_packs": 2, "uom": uom, "container": cn_b},
		)
		shipment.append(
			"internal_job_details",
			{
				"service_type": "Transport",
				"job_type": "Transport Order",
				"container_no": cn_b,
			},
		)
		shipment.insert()
		frappe.db.commit()

		res = create_transport_order_from_sea_shipment(shipment.name, internal_job_detail_idx=1)
		to = frappe.get_doc("Transport Order", res["transport_order"])
		self.assertEqual(normalize_container_number(to.container_no), normalize_container_number(cn_b))
		self.assertEqual(len(to.packages), 1)
		self.assertEqual(to.packages[0].commodity, comms[1])

	def test_transport_order_from_sea_shipment_filters_by_ij_container_without_header_container_type(self):
		"""Per-line container refs without Sea Shipment Container Type still scope packages (regression)."""
		from logistics.utils.container_validation import calculate_iso6346_check_digit, normalize_container_number
		from logistics.utils.module_integration import create_transport_order_from_sea_shipment

		def _iso_container(serial6: str) -> str:
			base = "MSCU" + serial6
			return base + str(calculate_iso6346_check_digit(base + "0"))

		cn_a = _iso_container("323456")
		cn_b = _iso_container("929012")

		uom = frappe.db.get_value("UOM", {"enabled": 1}, "name")
		self.assertTrue(uom)

		comms = frappe.get_all("Commodity", filters={"active": 1}, limit=2, pluck="name")
		while len(comms) < 2:
			sfx = frappe.generate_hash(length=4)
			frappe.get_doc(
				{"doctype": "Commodity", "commodity_name": f"TST-NO-CT {sfx}", "active": 1}
			).insert(ignore_permissions=True)
			comms = frappe.get_all("Commodity", filters={"active": 1}, limit=2, pluck="name")

		booking = frappe.get_doc(
			{
				"doctype": "Sea Booking",
				"booking_date": today(),
				"company": self.company,
				"local_customer": self.customer,
				"direction": "Export",
				"shipper": self.shipper,
				"consignee": self.consignee,
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"branch": self.branch,
				"cost_center": self.cost_center,
				"profit_center": self.profit_center,
			}
		)
		booking.insert()

		shipment = frappe.get_doc(
			{
				"doctype": "Sea Shipment",
				"booking_date": today(),
				"company": self.company,
				"local_customer": self.customer,
				"shipper": self.shipper,
				"consignee": self.consignee,
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"direction": "Export",
				"sea_booking": booking.name,
				"branch": self.branch,
				"cost_center": self.cost_center,
				"profit_center": self.profit_center,
			}
		)
		shipment.append(
			"packages",
			{"commodity": comms[0], "no_of_packs": 1, "uom": uom, "container": cn_a},
		)
		shipment.append(
			"packages",
			{"commodity": comms[1], "no_of_packs": 2, "uom": uom, "container": cn_b},
		)
		shipment.append(
			"internal_job_details",
			{
				"service_type": "Transport",
				"job_type": "Transport Order",
				"container_no": cn_b,
			},
		)
		shipment.insert()
		frappe.db.commit()

		res = create_transport_order_from_sea_shipment(shipment.name, internal_job_detail_idx=1)
		to = frappe.get_doc("Transport Order", res["transport_order"])
		self.assertEqual(to.transport_job_type, "Container")
		self.assertEqual(normalize_container_number(to.container_no), normalize_container_number(cn_b))
		self.assertEqual(len(to.packages), 1)
		self.assertEqual(to.packages[0].commodity, comms[1])
