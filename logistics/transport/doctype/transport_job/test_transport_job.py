# Copyright (c) 2026, www.agilasoft.com and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import today, add_days
from logistics.transport.doctype.transport_job.transport_job import action_create_run_sheet


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
		
		# Create test vehicle type if it doesn't exist
		if not frappe.db.exists("Vehicle Type", "Test Truck"):
			vehicle_type = frappe.new_doc("Vehicle Type")
			vehicle_type.vehicle_type = "Test Truck"
			vehicle_type.insert(ignore_permissions=True)
		
		# Create test facilities (Shipper and Consignee)
		if not frappe.db.exists("Shipper", "Test Shipper"):
			shipper = frappe.new_doc("Shipper")
			shipper.shipper_name = "Test Shipper"
			shipper.insert(ignore_permissions=True)
		
		if not frappe.db.exists("Consignee", "Test Consignee"):
			consignee = frappe.new_doc("Consignee")
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
