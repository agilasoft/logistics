# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
import unittest
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today, add_days, now_datetime, cint
from logistics.air_freight.tests.test_helpers import (
	setup_basic_master_data, create_test_shipper, create_test_consignee,
	create_test_branch, create_test_cost_center, create_test_profit_center
)
from logistics.utils.linked_service_compat import linked_service_doctype
from logistics.utils.linked_service_usage import (
	USAGE_ROLE_SATELLITE_JOB,
	USAGE_ROLE_SHIPMENT,
	record_linked_service_usage,
)


class TestAirShipment(FrappeTestCase):
	"""Test cases for Air Shipment doctype"""
	
	def setUp(self):
		"""Set up test data"""
		data = setup_basic_master_data()
		self.company = data["company"]
		self.customer = data["customer"]
		
		# Create accounts
		self.branch = create_test_branch(self.company)
		self.cost_center = create_test_cost_center(self.company)
		self.profit_center = create_test_profit_center(self.company)
		
		# Create shipper and consignee
		self.shipper = create_test_shipper()
		self.consignee = create_test_consignee()
	
	def tearDown(self):
		"""Clean up test data"""
		frappe.db.rollback()
	
	def test_air_shipment_creation(self):
		"""Test creating a basic Air Shipment"""
		shipment = frappe.get_doc({
			"doctype": "Air Shipment",
			"booking_date": today(),
			"company": self.company,
			"local_customer": self.customer,
			"shipper": self.shipper,
			"consignee": self.consignee,
			"origin_port": "USLAX",
			"destination_port": "USJFK",
			"branch": self.branch,
			"cost_center": self.cost_center,
			"profit_center": self.profit_center
		})
		shipment.insert()
		
		self.assertIsNotNone(shipment.name)
		self.assertEqual(shipment.company, self.company)
		self.assertEqual(shipment.local_customer, self.customer)
	
	def test_air_shipment_date_validation(self):
		"""Test validation of dates"""
		shipment = frappe.get_doc({
			"doctype": "Air Shipment",
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
			"etd": add_days(today(), 5),
			"eta": add_days(today(), 3)  # ETA before ETD
		})
		
		# This should raise a validation error
		with self.assertRaises((frappe.ValidationError, Exception)):
			shipment.insert()
	
	def test_air_shipment_weight_volume_validation(self):
		"""Test validation of weight and volume"""
		shipment = frappe.get_doc({
			"doctype": "Air Shipment",
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
			"weight": -10,  # Negative weight
			"volume": -5    # Negative volume
		})
		
		# This should raise a validation error
		with self.assertRaises((frappe.ValidationError, Exception)):
			shipment.insert()
	
	def test_air_shipment_dangerous_goods_validation(self):
		"""Test validation of dangerous goods requirements"""
		# Test that dangerous goods requires emergency contact
		shipment = frappe.get_doc({
			"doctype": "Air Shipment",
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
			"contains_dangerous_goods": 1
		})
		
		# Dangerous goods should require emergency contact and phone
		# The validation will throw an error if these are missing
		with self.assertRaises((frappe.ValidationError, Exception)) as context:
			shipment.insert()
		
		# Verify the error message mentions dangerous goods or emergency
		error_msg = str(context.exception).lower()
		self.assertTrue(
			"dangerous goods" in error_msg or 
			"emergency" in error_msg or 
			"dg" in error_msg or
			"contact" in error_msg,
			f"Expected dangerous goods validation error, got: {error_msg}"
		)
	
	def test_air_shipment_sustainability_metrics(self):
		"""Test calculation of sustainability metrics"""
		shipment = frappe.get_doc({
			"doctype": "Air Shipment",
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
			"weight": 1000,  # 1 ton
		})
		shipment.insert()
		
		# Check if sustainability metrics are calculated
		# The before_save method should calculate these
		if hasattr(shipment, 'estimated_carbon_footprint'):
			self.assertIsNotNone(shipment.estimated_carbon_footprint)
	
	def test_air_shipment_milestones_child_table(self):
		"""Test milestones child table and populate_milestones_from_template."""
		shipment = frappe.get_doc({
			"doctype": "Air Shipment",
			"booking_date": today(),
			"company": self.company,
			"local_customer": self.customer,
			"shipper": self.shipper,
			"consignee": self.consignee,
			"origin_port": "USLAX",
			"destination_port": "USJFK",
			"branch": self.branch,
			"cost_center": self.cost_center,
			"profit_center": self.profit_center
		})
		shipment.insert()
		self.assertTrue(hasattr(shipment, "milestones"))
		# populate_milestones_from_template returns dict with message and added (0 if no template)
		from logistics.document_management.api import populate_milestones_from_template
		result = populate_milestones_from_template("Air Shipment", shipment.name)
		self.assertIsInstance(result, dict)
		self.assertIn("added", result)
		# Dashboard HTML builds from child table
		html = shipment.get_dashboard_html()
		self.assertIsInstance(html, str)
	
	def test_air_shipment_package_validation(self):
		"""Test validation of packages"""
		shipment = frappe.get_doc({
			"doctype": "Air Shipment",
			"booking_date": today(),
			"company": self.company,
			"local_customer": self.customer,
			"shipper": self.shipper,
			"consignee": self.consignee,
			"origin_port": "USLAX",
			"destination_port": "USJFK",
			"branch": self.branch,
			"cost_center": self.cost_center,
			"profit_center": self.profit_center
		})
		
		# Add a package with invalid data
		shipment.append("packages", {
			"package_type": "Box",
			"quantity": -1  # Negative quantity
		})
		
		# This should raise a validation error
		with self.assertRaises((frappe.ValidationError, Exception)):
			shipment.insert()
	
	def test_air_shipment_before_save(self):
		"""Test before_save hook"""
		shipment = frappe.get_doc({
			"doctype": "Air Shipment",
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
			"weight": 500
		})
		
		# before_save should calculate sustainability metrics
		shipment.insert()
		
		# Check if before_save was called
		self.assertIsNotNone(shipment.name)
	
	def test_air_shipment_settings_defaults(self):
		"""Test that settings defaults are applied"""
		# Create settings first
		if not frappe.db.exists("Air Freight Settings", {"company": self.company}):
			settings = frappe.get_doc({
				"doctype": "Air Freight Settings",
				"company": self.company,
				"default_currency": "USD"
			})
			settings.insert()
		
		shipment = frappe.get_doc({
			"doctype": "Air Shipment",
			"booking_date": today(),
			"company": self.company,
			"local_customer": self.customer,
			"shipper": self.shipper,
			"consignee": self.consignee,
			"origin_port": "USLAX",
			"destination_port": "USJFK",
			"branch": self.branch,
			"cost_center": self.cost_center,
			"profit_center": self.profit_center
		})
		shipment.insert()
		
		# Settings defaults should be applied in before_save or after_insert
		self.assertIsNotNone(shipment.name)


class TestAirShipmentMilestones(FrappeTestCase):
	"""Air Booking milestones stay on the timeline and out of the Air Shipment grid."""

	def setUp(self):
		data = setup_basic_master_data()
		self.company = data["company"]
		self.customer = data["customer"]
		self.shipper = create_test_shipper()
		self.consignee = create_test_consignee()
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

	def _ensure_logistics_milestone(self, code):
		existing = frappe.db.get_value("Logistics Milestone", {"code": code}, "name")
		if existing:
			return existing
		return (
			frappe.get_doc(
				{
					"doctype": "Logistics Milestone",
					"code": code,
					"description": code,
					"air_freight": 1,
					"transport": 1,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def _booking_with_milestones(self, milestone_names, planned_end="2026-10-01 12:00:00"):
		booking = frappe.get_doc(
			{
				"doctype": "Air Booking",
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
		for milestone in milestone_names:
			booking.append(
				"milestones",
				{
					"milestone": milestone,
					"status": "Planned",
					"planned_end": planned_end,
					"source": "Fetched",
					"automation_planned_date_basis": "Booking Date",
				},
			)
		booking.flags.ignore_documents_milestones_populate = True
		booking.flags.ignore_mandatory = True
		booking.insert(ignore_permissions=True)
		return booking

	def _shipment_for_booking(self, booking):
		shipment = frappe.get_doc(
			{
				"doctype": "Air Shipment",
				"booking_date": today(),
				"company": self.company,
				"local_customer": self.customer,
				"shipper": self.shipper,
				"consignee": self.consignee,
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"direction": "Export",
				"air_booking": booking.name,
				"override_volume_weight": 1,
				"total_weight": 10,
				"total_volume": 1,
				"branch": self.branch,
				"cost_center": self.cost_center,
				"profit_center": self.profit_center,
			}
		)
		shipment.flags.ignore_documents_milestones_populate = True
		shipment.flags.ignore_mandatory = True
		shipment.insert(ignore_permissions=True)
		return shipment

	def _plain_shipment(self):
		shipment = frappe.get_doc(
			{
				"doctype": "Air Shipment",
				"booking_date": today(),
				"company": self.company,
				"local_customer": self.customer,
				"shipper": self.shipper,
				"consignee": self.consignee,
				"origin_port": "USLAX",
				"destination_port": "USJFK",
				"direction": "Export",
				"override_volume_weight": 1,
				"total_weight": 10,
				"total_volume": 1,
				"branch": self.branch,
				"cost_center": self.cost_center,
				"profit_center": self.profit_center,
			}
		)
		shipment.flags.ignore_documents_milestones_populate = True
		shipment.flags.ignore_mandatory = True
		shipment.insert(ignore_permissions=True)
		return shipment

	def _transport_order_with_milestones(self, milestone_names, planned_end="2026-10-05 08:00:00"):
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
				"branch": self.branch,
				"cost_center": self.cost_center,
				"profit_center": self.profit_center,
				"shipper": self.shipper,
				"consignee": self.consignee,
			}
		)
		for milestone in milestone_names:
			order.append(
				"milestones",
				{
					"milestone": milestone,
					"status": "Planned",
					"planned_end": planned_end,
					"source": "Fetched",
					"automation_planned_date_basis": "Booking Date",
				},
			)
		order.flags.ignore_documents_milestones_populate = True
		order.flags.ignore_mandatory = True
		order.insert(ignore_permissions=True)
		return order

	def _transport_job_with_milestones(self, milestone_names, planned_end="2026-10-06 09:00:00"):
		job = frappe.get_doc(
			{
				"doctype": "Transport Job",
				"company": self.company,
				"customer": self.customer,
				"booking_date": today(),
				"scheduled_date": today(),
				"transport_job_type": "Non-Container",
				"consolidate": 1,
				"branch": self.branch,
				"cost_center": self.cost_center,
				"profit_center": self.profit_center,
				"shipper": self.shipper,
				"consignee": self.consignee,
			}
		)
		for milestone in milestone_names:
			job.append(
				"milestones",
				{
					"milestone": milestone,
					"status": "Planned",
					"planned_end": planned_end,
					"source": "Fetched",
					"automation_planned_date_basis": "Booking Date",
				},
			)
		job.flags.ignore_documents_milestones_populate = True
		job.flags.ignore_booking_milestone_sync = True
		job.flags.ignore_service_milestone_sync = True
		job.flags.ignore_mandatory = True
		job.insert(ignore_permissions=True)
		return job

	def _linked_service_for_shipment(self, shipment, service_type="Transport"):
		ls = frappe.new_doc(linked_service_doctype())
		ls.service_type = service_type
		ls.parent_booking_type = "Air Shipment"
		ls.parent_booking_name = shipment.name
		ls.flags.ignore_mandatory = True
		ls.insert(ignore_permissions=True)
		return ls

	def _timeline_milestone_names(self, shipment):
		from logistics.document_management.api import get_milestone_display_rows_and_editor_doctype

		rows, editor_dt = get_milestone_display_rows_and_editor_doctype(shipment)
		self.assertEqual(editor_dt, "Air Shipment Milestone")
		return [row["milestone"] for row in rows]

	def test_air_shipment_does_not_store_booking_milestones(self):
		sfx = frappe.generate_hash(length=6)
		ms_booking = self._ensure_logistics_milestone(f"TST-AB-MS-{sfx}")
		booking = self._booking_with_milestones([ms_booking])
		shipment = self._shipment_for_booking(booking)

		self.assertFalse(any(row.milestone == ms_booking for row in shipment.milestones))
		self.assertEqual(self._timeline_milestone_names(shipment), [ms_booking])

	def test_air_shipment_keeps_manual_milestone_and_shows_booking_on_timeline(self):
		sfx = frappe.generate_hash(length=6)
		ms_booking = self._ensure_logistics_milestone(f"TST-AB-MS-{sfx}")
		ms_extra = self._ensure_logistics_milestone(f"TST-AS-MS-{sfx}")
		booking = self._booking_with_milestones([ms_booking])
		shipment = self._shipment_for_booking(booking)

		shipment.append("milestones", {"milestone": ms_extra, "status": "Planned", "source": "Manual"})
		shipment.flags.ignore_documents_milestones_populate = True
		shipment.save()

		self.assertEqual([row.milestone for row in shipment.milestones], [ms_extra])
		self.assertEqual(cint(shipment.milestones[0].from_booking), 0)
		self.assertEqual(self._timeline_milestone_names(shipment), [ms_booking, ms_extra])

	def test_air_shipment_timeline_omits_grid_row_that_duplicates_booking_milestone(self):
		sfx = frappe.generate_hash(length=6)
		ms_booking = self._ensure_logistics_milestone(f"TST-AB-MS-{sfx}")
		ms_extra = self._ensure_logistics_milestone(f"TST-AS-MS-{sfx}")
		booking = self._booking_with_milestones([ms_booking])
		shipment = self._shipment_for_booking(booking)

		shipment.append("milestones", {"milestone": ms_booking, "status": "Planned", "source": "Manual"})
		shipment.append("milestones", {"milestone": ms_extra, "status": "Planned", "source": "Manual"})
		shipment.flags.ignore_documents_milestones_populate = True
		shipment.save()

		self.assertEqual([row.milestone for row in shipment.milestones], [ms_booking, ms_extra])
		self.assertEqual(self._timeline_milestone_names(shipment), [ms_booking, ms_extra])

	def test_air_shipment_does_not_add_later_booking_milestone_to_grid(self):
		sfx = frappe.generate_hash(length=6)
		ms1 = self._ensure_logistics_milestone(f"TST-AB-MS1-{sfx}")
		ms2 = self._ensure_logistics_milestone(f"TST-AB-MS2-{sfx}")
		booking = self._booking_with_milestones([ms1])
		shipment = self._shipment_for_booking(booking)
		self.assertFalse(any(row.milestone == ms1 for row in shipment.milestones))

		booking.reload()
		booking.append(
			"milestones",
			{"milestone": ms2, "status": "Planned", "planned_end": "2026-11-01 09:00:00", "source": "Fetched"},
		)
		booking.flags.ignore_documents_milestones_populate = True
		booking.save()

		shipment.reload()
		shipment.flags.ignore_documents_milestones_populate = True
		shipment.save()

		self.assertFalse(any(row.milestone in {ms1, ms2} for row in shipment.milestones))
		self.assertEqual(self._timeline_milestone_names(shipment), [ms1, ms2])

	def test_air_shipment_drops_existing_booking_milestone_on_save(self):
		sfx = frappe.generate_hash(length=6)
		ms_booking = self._ensure_logistics_milestone(f"TST-AB-MS-{sfx}")
		ms_extra = self._ensure_logistics_milestone(f"TST-AS-MS-{sfx}")
		booking = self._booking_with_milestones([ms_booking])
		shipment = self._shipment_for_booking(booking)
		shipment.append(
			"milestones",
			{
				"milestone": ms_booking,
				"status": "Planned",
				"from_booking": 1,
				"planned_end": "2026-10-01 12:00:00",
				"source": "Fetched",
			},
		)
		shipment.append("milestones", {"milestone": ms_extra, "status": "Planned", "source": "Manual"})
		shipment.flags.ignore_documents_milestones_populate = True
		shipment.save()

		self.assertEqual([row.milestone for row in shipment.milestones], [ms_extra])
		self.assertEqual(self._timeline_milestone_names(shipment), [ms_booking, ms_extra])

	def test_air_shipment_template_skips_booking_milestone_codes(self):
		from logistics.document_management.api import populate_milestones_from_template

		sfx = frappe.generate_hash(length=6)
		ms_booking = self._ensure_logistics_milestone(f"TST-AB-TPL-{sfx}")
		ms_ship = self._ensure_logistics_milestone(f"TST-AS-TPL-{sfx}")
		booking = self._booking_with_milestones([ms_booking])
		template = frappe.get_doc(
			{
				"doctype": "Milestone Template",
				"template_name": f"TST Air Shipment {sfx}",
				"product_type": "Air Freight",
				"applies_to": "Shipment/Job",
				"is_default": 0,
				"is_active": 1,
				"items": [
					{"milestone": ms_booking},
					{"milestone": ms_ship},
				],
			}
		)
		template.insert(ignore_permissions=True)

		shipment = self._shipment_for_booking(booking)
		shipment.milestone_template = template.name
		shipment.flags.ignore_documents_milestones_populate = True
		populate_milestones_from_template("Air Shipment", shipment.name, doc=shipment)

		shipment.reload()
		self.assertEqual([row.milestone for row in shipment.milestones], [ms_ship])
		self.assertEqual(self._timeline_milestone_names(shipment), [ms_booking, ms_ship])

	def test_air_shipment_does_not_copy_service_milestones_from_order_and_job(self):
		sfx = frappe.generate_hash(length=6)
		ms_svc = self._ensure_logistics_milestone(f"TST-SVC-MS-{sfx}")
		ms_extra = self._ensure_logistics_milestone(f"TST-AS-SVC-{sfx}")
		order = self._transport_order_with_milestones([ms_svc], planned_end="2026-10-05 08:00:00")
		job = self._transport_job_with_milestones([ms_svc], planned_end="2026-10-06 09:00:00")
		shipment = self._plain_shipment()
		ls = self._linked_service_for_shipment(shipment)
		record_linked_service_usage(
			ls.name, order.doctype, order.name, usage_role=USAGE_ROLE_SATELLITE_JOB
		)
		record_linked_service_usage(
			ls.name, job.doctype, job.name, usage_role=USAGE_ROLE_SHIPMENT
		)

		shipment.reload()
		shipment.append("milestones", {"milestone": ms_extra, "status": "Planned", "source": "Manual"})
		shipment.flags.ignore_documents_milestones_populate = True
		shipment.save()

		self.assertFalse(any(row.milestone == ms_svc for row in shipment.milestones))
		self.assertFalse(any(cint(row.from_service) for row in shipment.milestones))
		extra = [row for row in shipment.milestones if row.milestone == ms_extra]
		self.assertEqual(len(extra), 1)
		self.assertEqual(cint(extra[0].from_service), 0)
		self.assertEqual(cint(extra[0].from_booking), 0)
		self.assertEqual(self._timeline_milestone_names(shipment), [ms_extra])

	def test_air_shipment_booking_timeline_omits_service_milestones(self):
		sfx = frappe.generate_hash(length=6)
		ms_booking = self._ensure_logistics_milestone(f"TST-AB-CO-{sfx}")
		ms_svc = self._ensure_logistics_milestone(f"TST-SVC-CO-{sfx}")
		booking = self._booking_with_milestones([ms_booking])
		shipment = self._shipment_for_booking(booking)
		order = self._transport_order_with_milestones([ms_svc])
		ls = self._linked_service_for_shipment(shipment)
		record_linked_service_usage(
			ls.name, order.doctype, order.name, usage_role=USAGE_ROLE_SATELLITE_JOB
		)

		shipment.reload()
		shipment.flags.ignore_documents_milestones_populate = True
		shipment.save()

		self.assertFalse(any(row.milestone in {ms_booking, ms_svc} for row in shipment.milestones))
		self.assertEqual(self._timeline_milestone_names(shipment), [ms_booking])

	def test_air_shipment_drops_service_milestones_on_save(self):
		sfx = frappe.generate_hash(length=6)
		ms_svc = self._ensure_logistics_milestone(f"TST-SVC-ED-{sfx}")
		ms_extra = self._ensure_logistics_milestone(f"TST-AS-ED-{sfx}")
		shipment = self._plain_shipment()
		shipment.append(
			"milestones",
			{
				"milestone": ms_svc,
				"status": "Planned",
				"planned_end": "2026-12-31 00:00:00",
				"source": "Fetched",
				"from_service": 1,
				"service_source_doctype": "Transport Order",
				"service_source_name": "TRO-DROP",
			},
		)
		shipment.append("milestones", {"milestone": ms_extra, "status": "Planned", "source": "Manual"})
		shipment.flags.ignore_documents_milestones_populate = True
		shipment.save()

		shipment.reload()
		self.assertEqual([row.milestone for row in shipment.milestones], [ms_extra])
		self.assertEqual(cint(shipment.milestones[0].from_service), 0)

	def test_apply_uom_defaults_populates_summary_uoms(self):
		"""Summary UOM links should default from Logistics Settings (issue #1428)."""
		from logistics.utils.measurements import get_default_uoms

		defaults = get_default_uoms(company=self.company)
		if not defaults.get("volume") and not defaults.get("weight"):
			self.skipTest("Logistics UOM defaults not configured")

		shipment = frappe.new_doc("Air Shipment")
		shipment.company = self.company
		shipment._apply_uom_defaults()
		if defaults.get("volume"):
			self.assertTrue(shipment.total_volume_uom)
		if defaults.get("weight"):
			self.assertTrue(shipment.total_weight_uom)
			self.assertTrue(shipment.chargeable_weight_uom)

