# Copyright (c) 2026, www.agilasoft.com and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today, add_days, cint
from logistics.transport.doctype.transport_job.transport_job import action_create_run_sheet
from logistics.utils.linked_service_compat import linked_service_doctype
from logistics.utils.linked_service_usage import (
	USAGE_ROLE_SATELLITE_JOB,
	USAGE_ROLE_SHIPMENT,
	record_linked_service_usage,
)


class TestTransportJobChargeSubmitGate(FrappeTestCase):
	"""Submit charge gate tests (no master-data setUp)."""

	def tearDown(self):
		frappe.db.rollback()

	def test_before_submit_blocked_without_charges(self):
		"""Main-service Transport Job cannot submit without a Transport charge line."""
		from logistics.utils.charge_service_type import (
			assert_destination_service_charges_on_submit_unless_internal_job,
		)

		job = frappe.get_doc({"doctype": "Transport Job"})
		with self.assertRaises(frappe.ValidationError) as ctx:
			assert_destination_service_charges_on_submit_unless_internal_job(job)
		self.assertIn("Transport", str(ctx.exception))

	def test_before_submit_allowed_internal_job_without_charges(self):
		"""Internal jobs may submit without Transport charge rows."""
		from logistics.utils.charge_service_type import (
			assert_destination_service_charges_on_submit_unless_internal_job,
		)

		job = frappe.get_doc({"doctype": "Transport Job", "is_internal_job": 1})
		assert_destination_service_charges_on_submit_unless_internal_job(job)


class TestTransportJob(FrappeTestCase):
	"""Test Transport Job status workflow"""
	
	def setUp(self):
		"""Set up test data"""
		# Create test company if it doesn't exist
		if not frappe.db.exists("Company", "Test Company"):
			company = frappe.new_doc("Company")
			company.company_name = "Test Company"
			company.abbr = "TC"
			company.default_currency = "USD"
			company.insert(ignore_permissions=True)
		
		# Create test customer if it doesn't exist
		if not frappe.db.exists("Customer", "Test Customer"):
			customer = frappe.new_doc("Customer")
			customer.customer_name = "Test Customer"
			customer.customer_type = "Company"
			customer.insert(ignore_permissions=True)
		
		# Create test vehicle type if it doesn't exist (autoname: field:code)
		if not frappe.db.exists("Vehicle Type", "Test Truck"):
			vehicle_type = frappe.new_doc("Vehicle Type")
			vehicle_type.code = "Test Truck"
			vehicle_type.description = "Test Truck"
			vehicle_type.insert(ignore_permissions=True)

		# Create test facilities (Shipper and Consignee - autoname: field:code)
		if not frappe.db.exists("Shipper", "Test Shipper"):
			shipper = frappe.new_doc("Shipper")
			shipper.code = "Test Shipper"
			shipper.shipper_name = "Test Shipper"
			shipper.insert(ignore_permissions=True)

		if not frappe.db.exists("Consignee", "Test Consignee"):
			consignee = frappe.new_doc("Consignee")
			consignee.code = "Test Consignee"
			consignee.consignee_name = "Test Consignee"
			consignee.insert(ignore_permissions=True)
		
		frappe.db.commit()
	
	def tearDown(self):
		"""Clean up test data"""
		# Clean up in reverse order of creation
		pass  # FrappeTestCase handles cleanup
	
	def test_job_status_workflow(self):
		"""
		Test the complete job status workflow:
		1. Create Job → Status: "Draft"
		2. Submit Job → Status: "Submitted" (legs are "Open")
		3. Assign Leg to Run Sheet → Status: "In Progress" (leg becomes "Assigned")
		4. Start Leg → Status: "In Progress" (leg becomes "Started")
		5. Complete All Legs → Status: "Completed" (all legs "Completed")
		"""
		# Step 1: Create Transport Job → Status: "Draft"
		job = frappe.new_doc("Transport Job")
		job.customer = "Test Customer"
		job.company = "Test Company"
		job.transport_job_type = "Non-Container"
		job.vehicle_type = "Test Truck"
		job.booking_date = today()
		job.insert(ignore_permissions=True)
		
		# Verify initial status is Draft
		self.assertEqual(job.status, "Draft", "Job should be in Draft status after creation")
		self.assertEqual(job.docstatus, 0, "Job should be unsaved (draft) after creation")
		
		# Create Transport Leg
		leg = frappe.new_doc("Transport Leg")
		leg.transport_job = job.name
		leg.vehicle_type = "Test Truck"
		leg.facility_type_from = "Shipper"
		leg.facility_from = "Test Shipper"
		leg.facility_type_to = "Consignee"
		leg.facility_to = "Test Consignee"
		leg.date = today()
		leg.insert(ignore_permissions=True)
		
		# Verify leg status is Open (no run_sheet, no dates)
		self.assertEqual(leg.status, "Open", "Leg should be in Open status after creation")
		
		# Add leg to job
		job.append("legs", {
			"transport_leg": leg.name
		})
		job.save(ignore_permissions=True)
		
		# Reload job to get updated status
		job.reload()
		self.assertEqual(job.status, "Draft", "Job should still be Draft before submission")

		job.append("charges", {"service_type": "Transport"})
		job.save(ignore_permissions=True)
		
		# Step 2: Submit Job → Status: "Submitted" (legs are "Open")
		job.submit()
		job.reload()
		
		# Verify job status is Submitted
		self.assertEqual(job.status, "Submitted", "Job should be in Submitted status after submission")
		self.assertEqual(job.docstatus, 1, "Job should be submitted")
		
		# Verify leg status is still Open
		leg.reload()
		self.assertEqual(leg.status, "Open", "Leg should be in Open status (not assigned to run sheet)")
		
		# Step 3: Assign Leg to Run Sheet → Status: "In Progress" (leg becomes "Assigned")
		# Create a Run Sheet
		run_sheet = frappe.new_doc("Run Sheet")
		run_sheet.vehicle_type = "Test Truck"
		run_sheet.run_date = today()
		run_sheet.status = "Draft"
		run_sheet.append("legs", {
			"transport_leg": leg.name
		})
		run_sheet.insert(ignore_permissions=True)
		run_sheet.save(ignore_permissions=True)
		
		# Assign leg to run sheet by updating the leg
		leg.reload()
		leg.run_sheet = run_sheet.name
		leg.save(ignore_permissions=True)
		
		# Verify leg status changed to Assigned
		leg.reload()
		self.assertEqual(leg.status, "Assigned", "Leg should be in Assigned status after run sheet assignment")
		
		# Verify job status changed to In Progress
		job.reload()
		self.assertEqual(job.status, "In Progress", "Job should be in In Progress status when leg is Assigned")
		
		# Step 4: Start Leg → Status: "In Progress" (leg becomes "Started")
		leg.reload()
		leg.start_date = today()
		leg.save(ignore_permissions=True)
		
		# Verify leg status changed to Started
		leg.reload()
		self.assertEqual(leg.status, "Started", "Leg should be in Started status after start_date is set")
		
		# Verify job status is still In Progress
		job.reload()
		self.assertEqual(job.status, "In Progress", "Job should remain in In Progress status when leg is Started")
		
		# Step 5: Complete All Legs → Status: "Completed" (all legs "Completed")
		leg.reload()
		leg.end_date = today()
		leg.save(ignore_permissions=True)
		
		# Verify leg status changed to Completed
		leg.reload()
		self.assertEqual(leg.status, "Completed", "Leg should be in Completed status after end_date is set")
		
		# Verify job status changed to Completed
		job.reload()
		self.assertEqual(job.status, "Completed", "Job should be in Completed status when all legs are Completed")
	
	def test_job_status_with_multiple_legs(self):
		"""
		Test job status workflow with multiple legs:
		- Job should be In Progress if any leg is Assigned/Started
		- Job should be Completed only when ALL legs are Completed
		"""
		# Create Transport Job
		job = frappe.new_doc("Transport Job")
		job.customer = "Test Customer"
		job.company = "Test Company"
		job.transport_job_type = "Non-Container"
		job.vehicle_type = "Test Truck"
		job.booking_date = today()
		job.insert(ignore_permissions=True)
		
		# Create two Transport Legs
		leg1 = frappe.new_doc("Transport Leg")
		leg1.transport_job = job.name
		leg1.vehicle_type = "Test Truck"
		leg1.facility_type_from = "Shipper"
		leg1.facility_from = "Test Shipper"
		leg1.facility_type_to = "Consignee"
		leg1.facility_to = "Test Consignee"
		leg1.date = today()
		leg1.insert(ignore_permissions=True)
		
		leg2 = frappe.new_doc("Transport Leg")
		leg2.transport_job = job.name
		leg2.vehicle_type = "Test Truck"
		leg2.facility_type_from = "Shipper"
		leg2.facility_from = "Test Shipper"
		leg2.facility_type_to = "Consignee"
		leg2.facility_to = "Test Consignee"
		leg2.date = today()
		leg2.insert(ignore_permissions=True)
		
		# Add legs to job
		job.append("legs", {"transport_leg": leg1.name})
		job.append("legs", {"transport_leg": leg2.name})
		job.append("charges", {"service_type": "Transport"})
		job.save(ignore_permissions=True)
		
		# Submit job
		job.submit()
		job.reload()
		self.assertEqual(job.status, "Submitted", "Job should be Submitted when all legs are Open")
		
		# Assign first leg to run sheet
		run_sheet1 = frappe.new_doc("Run Sheet")
		run_sheet1.vehicle_type = "Test Truck"
		run_sheet1.run_date = today()
		run_sheet1.status = "Draft"
		run_sheet1.append("legs", {"transport_leg": leg1.name})
		run_sheet1.insert(ignore_permissions=True)
		run_sheet1.save(ignore_permissions=True)
		
		leg1.reload()
		leg1.run_sheet = run_sheet1.name
		leg1.save(ignore_permissions=True)
		
		# Job should be In Progress (one leg is Assigned)
		job.reload()
		self.assertEqual(job.status, "In Progress", "Job should be In Progress when one leg is Assigned")
		
		# Complete first leg
		leg1.reload()
		leg1.start_date = today()
		leg1.end_date = today()
		leg1.save(ignore_permissions=True)
		
		# Job should still be In Progress (second leg is still Open)
		job.reload()
		self.assertEqual(job.status, "In Progress", "Job should still be In Progress when one leg is Completed but other is Open")
		
		# Complete second leg
		run_sheet2 = frappe.new_doc("Run Sheet")
		run_sheet2.vehicle_type = "Test Truck"
		run_sheet2.run_date = today()
		run_sheet2.status = "Draft"
		run_sheet2.append("legs", {"transport_leg": leg2.name})
		run_sheet2.insert(ignore_permissions=True)
		run_sheet2.save(ignore_permissions=True)
		
		leg2.reload()
		leg2.run_sheet = run_sheet2.name
		leg2.start_date = today()
		leg2.end_date = today()
		leg2.save(ignore_permissions=True)
		
		# Job should now be Completed (all legs are Completed)
		job.reload()
		self.assertEqual(job.status, "Completed", "Job should be Completed when all legs are Completed")


class TestTransportJobMilestones(FrappeTestCase):
	"""Transport Order milestones copy onto Transport Job like Sea Booking → Sea Shipment."""

	def setUp(self):
		from logistics.air_freight.tests.test_helpers import (
			create_test_branch,
			create_test_consignee,
			create_test_cost_center,
			create_test_profit_center,
			create_test_shipper,
			setup_basic_master_data,
		)

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
					"transport": 1,
					"sea_freight": 1,
				}
			)
			.insert(ignore_permissions=True)
			.name
		)

	def _order_with_milestones(self, milestone_names, planned_end="2026-10-01 12:00:00"):
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
		frappe.db.set_value("Transport Order", order.name, "docstatus", 1, update_modified=False)
		order.reload()
		return order

	def _job_for_order(self, order):
		job = frappe.get_doc(
			{
				"doctype": "Transport Job",
				"company": self.company,
				"customer": self.customer,
				"booking_date": today(),
				"scheduled_date": today(),
				"transport_job_type": "Non-Container",
				"consolidate": 1,
				"transport_order": order.name,
				"branch": self.branch,
				"cost_center": self.cost_center,
				"profit_center": self.profit_center,
				"shipper": self.shipper,
				"consignee": self.consignee,
			}
		)
		job.flags.ignore_documents_milestones_populate = True
		job.flags.ignore_mandatory = True
		job.insert(ignore_permissions=True)
		return job

	def _plain_job(self):
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
		job.flags.ignore_documents_milestones_populate = True
		job.flags.ignore_mandatory = True
		job.insert(ignore_permissions=True)
		return job

	def _sea_booking_with_milestones(self, milestone_names, planned_end="2026-10-05 08:00:00"):
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

	def _sea_shipment_with_milestones(self, milestone_names, planned_end="2026-10-06 09:00:00"):
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
				"branch": self.branch,
				"cost_center": self.cost_center,
				"profit_center": self.profit_center,
			}
		)
		for milestone in milestone_names:
			shipment.append(
				"milestones",
				{
					"milestone": milestone,
					"status": "Planned",
					"planned_end": planned_end,
					"source": "Fetched",
					"automation_planned_date_basis": "Booking Date",
				},
			)
		shipment.flags.ignore_documents_milestones_populate = True
		shipment.flags.ignore_booking_milestone_sync = True
		shipment.flags.ignore_service_milestone_sync = True
		shipment.flags.ignore_mandatory = True
		shipment.insert(ignore_permissions=True)
		return shipment

	def _linked_service_for_job(self, job, service_type="Sea"):
		ls = frappe.new_doc(linked_service_doctype())
		ls.service_type = service_type
		ls.parent_booking_type = "Transport Job"
		ls.parent_booking_name = job.name
		ls.flags.ignore_mandatory = True
		ls.insert(ignore_permissions=True)
		return ls

	def test_order_milestone_row_values_marks_from_booking(self):
		from logistics.transport.doctype.transport_job.transport_job import order_milestone_row_values

		src = frappe._dict(
			{
				"milestone": "MS-A",
				"status": "Planned",
				"planned_start": None,
				"planned_end": "2026-10-01 12:00:00",
				"actual_start": None,
				"actual_end": None,
				"source": "Fetched",
				"fetched_at": "2026-09-01 08:00:00",
				"automation_planned_date_basis": "Booking Date",
				"automation_update_trigger_type": "Date Based",
			}
		)
		values = order_milestone_row_values(src)
		self.assertEqual(values["from_booking"], 1)
		self.assertEqual(values["milestone"], "MS-A")
		self.assertEqual(values["planned_end"], "2026-10-01 12:00:00")
		self.assertEqual(values["automation_planned_date_basis"], "Booking Date")
		self.assertEqual(values["automation_update_trigger_type"], "Date Based")

	def test_transport_job_populates_order_milestones_as_from_booking(self):
		sfx = frappe.generate_hash(length=6)
		ms_order = self._ensure_logistics_milestone(f"TST-TO-MS-{sfx}")
		order = self._order_with_milestones([ms_order])
		job = self._job_for_order(order)

		self.assertEqual(len(job.milestones), 1)
		self.assertEqual(job.milestones[0].milestone, ms_order)
		self.assertEqual(cint(job.milestones[0].from_booking), 1)
		self.assertEqual(str(job.milestones[0].planned_end), "2026-10-01 12:00:00")
		self.assertEqual(job.milestones[0].automation_planned_date_basis, "Booking Date")

	def test_transport_job_allows_extra_milestone_without_flagging_from_booking(self):
		sfx = frappe.generate_hash(length=6)
		ms_order = self._ensure_logistics_milestone(f"TST-TO-MS-{sfx}")
		ms_extra = self._ensure_logistics_milestone(f"TST-TJ-MS-{sfx}")
		order = self._order_with_milestones([ms_order])
		job = self._job_for_order(order)

		job.append("milestones", {"milestone": ms_extra, "status": "Planned", "source": "Manual"})
		job.flags.ignore_documents_milestones_populate = True
		job.save()

		by_ms = {row.milestone: row for row in job.milestones}
		self.assertIn(ms_order, by_ms)
		self.assertIn(ms_extra, by_ms)
		self.assertEqual(cint(by_ms[ms_order].from_booking), 1)
		self.assertEqual(cint(by_ms[ms_extra].from_booking), 0)

	def test_transport_job_adds_missing_order_milestone_on_later_save(self):
		sfx = frappe.generate_hash(length=6)
		ms1 = self._ensure_logistics_milestone(f"TST-TO-MS1-{sfx}")
		ms2 = self._ensure_logistics_milestone(f"TST-TO-MS2-{sfx}")
		order = self._order_with_milestones([ms1])
		job = self._job_for_order(order)
		self.assertEqual([row.milestone for row in job.milestones], [ms1])

		frappe.get_doc(
			{
				"doctype": "Transport Order Milestone",
				"parent": order.name,
				"parenttype": "Transport Order",
				"parentfield": "milestones",
				"milestone": ms2,
				"status": "Planned",
				"planned_end": "2026-11-01 09:00:00",
				"source": "Fetched",
			}
		).insert(ignore_permissions=True)

		job.reload()
		job.flags.ignore_documents_milestones_populate = True
		job.save()

		names = {row.milestone for row in job.milestones}
		self.assertEqual(names, {ms1, ms2})
		self.assertTrue(all(cint(row.from_booking) for row in job.milestones))

	def test_transport_job_rejects_edit_and_delete_of_order_milestones(self):
		sfx = frappe.generate_hash(length=6)
		ms_order = self._ensure_logistics_milestone(f"TST-TO-MS-{sfx}")
		order = self._order_with_milestones([ms_order])
		job = self._job_for_order(order)

		job.milestones[0].planned_end = "2026-12-31 00:00:00"
		job.flags.ignore_documents_milestones_populate = True
		with self.assertRaises(frappe.ValidationError) as ctx:
			job.save()
		self.assertIn("cannot be edited", str(ctx.exception))

		job.reload()
		job.remove(job.milestones[0])
		job.flags.ignore_documents_milestones_populate = True
		with self.assertRaises(frappe.ValidationError) as ctx:
			job.save()
		self.assertIn("cannot be deleted", str(ctx.exception))

	def test_transport_job_copies_service_milestones_from_order_and_job(self):
		sfx = frappe.generate_hash(length=6)
		ms_svc = self._ensure_logistics_milestone(f"TST-SVC-MS-{sfx}")
		ms_extra = self._ensure_logistics_milestone(f"TST-TJ-SVC-{sfx}")
		booking = self._sea_booking_with_milestones([ms_svc], planned_end="2026-10-05 08:00:00")
		shipment = self._sea_shipment_with_milestones([ms_svc], planned_end="2026-10-06 09:00:00")
		job = self._plain_job()
		ls = self._linked_service_for_job(job)
		record_linked_service_usage(
			ls.name, booking.doctype, booking.name, usage_role=USAGE_ROLE_SATELLITE_JOB
		)
		record_linked_service_usage(
			ls.name, shipment.doctype, shipment.name, usage_role=USAGE_ROLE_SHIPMENT
		)

		job.reload()
		job.append("milestones", {"milestone": ms_extra, "status": "Planned", "source": "Manual"})
		job.flags.ignore_documents_milestones_populate = True
		job.save()

		service_rows = [row for row in job.milestones if cint(row.from_service)]
		self.assertEqual(len(service_rows), 2)
		sources = {(row.service_source_doctype, row.service_source_name) for row in service_rows}
		self.assertEqual(sources, {("Sea Booking", booking.name), ("Sea Shipment", shipment.name)})
		self.assertTrue(all(row.milestone == ms_svc for row in service_rows))
		self.assertTrue(all(cint(row.from_booking) == 0 for row in service_rows))

		extra = [row for row in job.milestones if row.milestone == ms_extra]
		self.assertEqual(len(extra), 1)
		self.assertEqual(cint(extra[0].from_service), 0)
		self.assertEqual(cint(extra[0].from_booking), 0)

	def test_transport_job_booking_and_service_milestones_coexist(self):
		sfx = frappe.generate_hash(length=6)
		ms_order = self._ensure_logistics_milestone(f"TST-TO-CO-{sfx}")
		ms_svc = self._ensure_logistics_milestone(f"TST-SVC-CO-{sfx}")
		order = self._order_with_milestones([ms_order])
		job = self._job_for_order(order)
		booking = self._sea_booking_with_milestones([ms_svc])
		ls = self._linked_service_for_job(job)
		record_linked_service_usage(
			ls.name, booking.doctype, booking.name, usage_role=USAGE_ROLE_SATELLITE_JOB
		)

		job.reload()
		job.flags.ignore_documents_milestones_populate = True
		job.save()

		by_ms = {row.milestone: row for row in job.milestones}
		self.assertIn(ms_order, by_ms)
		self.assertIn(ms_svc, by_ms)
		self.assertEqual(cint(by_ms[ms_order].from_booking), 1)
		self.assertEqual(cint(by_ms[ms_order].from_service), 0)
		self.assertEqual(cint(by_ms[ms_svc].from_service), 1)
		self.assertEqual(cint(by_ms[ms_svc].from_booking), 0)
		self.assertEqual(by_ms[ms_svc].service_source_doctype, "Sea Booking")
		self.assertEqual(by_ms[ms_svc].service_source_name, booking.name)

	def test_transport_job_rejects_edit_and_delete_of_service_milestones(self):
		sfx = frappe.generate_hash(length=6)
		ms_svc = self._ensure_logistics_milestone(f"TST-SVC-ED-{sfx}")
		booking = self._sea_booking_with_milestones([ms_svc])
		job = self._plain_job()
		ls = self._linked_service_for_job(job)
		record_linked_service_usage(
			ls.name, booking.doctype, booking.name, usage_role=USAGE_ROLE_SATELLITE_JOB
		)

		job.reload()
		job.flags.ignore_documents_milestones_populate = True
		job.save()
		self.assertEqual(len(job.milestones), 1)
		self.assertEqual(cint(job.milestones[0].from_service), 1)

		job.milestones[0].planned_end = "2026-12-31 00:00:00"
		job.flags.ignore_documents_milestones_populate = True
		with self.assertRaises(frappe.ValidationError) as ctx:
			job.save()
		self.assertIn("cannot be edited", str(ctx.exception))

		job.reload()
		job.remove(job.milestones[0])
		job.flags.ignore_documents_milestones_populate = True
		with self.assertRaises(frappe.ValidationError) as ctx:
			job.save()
		self.assertIn("cannot be deleted", str(ctx.exception))

