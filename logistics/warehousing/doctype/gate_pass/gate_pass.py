# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class GatePass(Document):
	def validate(self):
		"""Validate gate pass data"""
		self.validate_warehouse_job()
		self.validate_docking_details()
		self.update_reference_fields()
		self.validate_authorization()
	
	def validate_warehouse_job(self):
		"""Validate warehouse job reference"""
		if self.warehouse_job:
			job = frappe.get_doc("Warehouse Job", self.warehouse_job)
			
			# Copy reference order details from warehouse job
			if not self.reference_order_type:
				self.reference_order_type = job.reference_order_type
			if not self.reference_order:
				self.reference_order = job.reference_order
			if not self.company:
				self.company = job.company
			if not self.branch:
				self.branch = job.branch
			if not self.job_type:
				self.job_type = job.type
	
	def validate_docking_details(self):
		"""Validate docking details from warehouse job"""
		if self.warehouse_job:
			job = frappe.get_doc("Warehouse Job", self.warehouse_job)
			
			# Get docking details from warehouse job
			if job.docks:
				# Use the first dock entry for gate pass
				dock = job.docks[0]
				if not self.dock_door:
					self.dock_door = dock.dock_door
				if not self.eta:
					self.eta = dock.eta
				if not self.transport_company:
					self.transport_company = dock.transport_company
				if not self.vehicle_type:
					self.vehicle_type = dock.vehicle_type
				if not self.plate_no:
					self.plate_no = dock.plate_no
	
	def update_reference_fields(self):
		"""Update reference fields based on warehouse job"""
		if self.warehouse_job:
			job = frappe.get_doc("Warehouse Job", self.warehouse_job)
			
			# Update items from warehouse job items
			if not self.items and job.items:
				for job_item in job.items:
					self.append("items", {
						"item_code": job_item.item_code,
						"item_name": job_item.item_name,
						"description": job_item.description,
						"qty": job_item.qty,
						"uom": job_item.uom,
						"branch": self.branch or job.branch,
						"handling_unit": job_item.handling_unit
					})
	
	def validate_authorization(self):
		"""Validate authorization fields"""
		if self.status == "Authorized" and not self.authorized_by:
			frappe.throw("Authorized By is required when status is 'Authorized'")
		
		if self.status == "Completed" and not self.actual_out_time:
			frappe.throw("Actual Out Time is required when status is 'Completed'")
	
	def on_submit(self):
		"""Actions when gate pass is submitted"""
		self.status = "Authorized"
		self.authorized_date = frappe.utils.today()
		if not self.authorized_by:
			self.authorized_by = frappe.session.user
	
	def on_cancel(self):
		"""Actions when gate pass is cancelled"""
		self.status = "Cancelled"
	
	def update_actual_in_time(self):
		"""Update actual in time when vehicle enters"""
		if not self.actual_in_time:
			self.actual_in_time = frappe.utils.now()
			self.status = "In Progress"
			self.save()
	
	def update_actual_out_time(self):
		"""Update actual out time when vehicle exits"""
		if not self.actual_out_time:
			self.actual_out_time = frappe.utils.now()
			self.status = "Completed"
			self.save()


@frappe.whitelist()
def create_gate_pass_for_docking(warehouse_job, dock_name=None):
	"""Create gate pass for docking entries in warehouse job"""
	try:
		job = frappe.get_doc("Warehouse Job", warehouse_job)
		
		# If specific dock is mentioned, create for that dock only
		if dock_name:
			dock = None
			for d in job.docks:
				if d.name == dock_name:
					dock = d
					break
			
			if not dock:
				frappe.throw(f"Dock {dock_name} not found in Warehouse Job {warehouse_job}")
			
			gate_pass = create_single_gate_pass(job, dock)
			return gate_pass.name
		else:
			# Create gate pass for each dock entry
			gate_passes = []
			for dock in job.docks:
				gate_pass = create_single_gate_pass(job, dock)
				gate_passes.append(gate_pass.name)
			
			return gate_passes
			
	except Exception as e:
		frappe.log_error(f"Error creating gate pass: {str(e)}")
		frappe.throw(f"Failed to create gate pass: {str(e)}")


def create_single_gate_pass(job, dock):
	"""Create a single gate pass for a dock entry"""
	gate_pass = frappe.new_doc("Gate Pass")
	gate_pass.warehouse_job = job.name
	gate_pass.job_type = job.type
	gate_pass.reference_order_type = job.reference_order_type
	gate_pass.reference_order = job.reference_order
	gate_pass.dock_door = dock.dock_door
	gate_pass.eta = dock.eta
	gate_pass.transport_company = dock.transport_company
	gate_pass.vehicle_type = dock.vehicle_type
	gate_pass.plate_no = dock.plate_no
	gate_pass.company = job.company
	gate_pass.branch = job.branch
	gate_pass.gate_pass_date = frappe.utils.today()
	gate_pass.gate_pass_time = frappe.utils.nowtime()
	
	# Add items from warehouse job
	for item in job.items:
		# Get item details from Warehouse Item
		item_details = frappe.get_value("Warehouse Item", item.item, 
			["item_name", "description", "uom"], as_dict=True) if item.item else {}
		
		gate_pass.append("items", {
			"item_code": item.item,
			"item_name": item_details.get("item_name", ""),
			"description": item_details.get("description", ""),
			"qty": item.quantity,
			"uom": item_details.get("uom", ""),
			"branch": job.branch,
			"handling_unit": item.handling_unit
		})
	
	gate_pass.insert()
	return gate_pass


@frappe.whitelist()
def get_docking_details(warehouse_job):
	"""Get docking details for a warehouse job"""
	try:
		job = frappe.get_doc("Warehouse Job", warehouse_job)
		docking_details = []
		
		for dock in job.docks:
			docking_details.append({
				"name": dock.name,
				"dock_door": dock.dock_door,
				"eta": dock.eta,
				"transport_company": dock.transport_company,
				"vehicle_type": dock.vehicle_type,
				"plate_no": dock.plate_no
			})
		
		return docking_details
		
	except Exception as e:
		frappe.log_error(f"Error getting docking details: {str(e)}")
		return []


@frappe.whitelist()
def get_gate_pass_details(gate_pass):
	"""Get detailed information about a specific gate pass"""
	try:
		gp_doc = frappe.get_doc("Gate Pass", gate_pass)
		
		gate_pass_data = {
			"name": gp_doc.name,
			"status": gp_doc.status,
			"job_type": gp_doc.job_type,
			"dock_door": gp_doc.dock_door,
			"eta": gp_doc.eta,
			"plate_no": gp_doc.plate_no,
			"transport_company": gp_doc.transport_company,
			"vehicle_type": gp_doc.vehicle_type,
			"driver_name": gp_doc.driver_name,
			"driver_contact": gp_doc.driver_contact,
			"gate_pass_date": gp_doc.gate_pass_date,
			"gate_pass_time": gp_doc.gate_pass_time,
			"actual_in_time": gp_doc.actual_in_time,
			"actual_out_time": gp_doc.actual_out_time,
			"authorized_by": gp_doc.authorized_by,
			"authorized_date": gp_doc.authorized_date,
			"security_checked_by": gp_doc.security_checked_by,
			"security_check_time": gp_doc.security_check_time,
			"security_notes": gp_doc.security_notes,
			"warehouse_job": gp_doc.warehouse_job,
			"reference_order_type": gp_doc.reference_order_type,
			"reference_order": gp_doc.reference_order,
			"company": gp_doc.company,
			"branch": gp_doc.branch,
			"notes": gp_doc.notes
		}
		
		# Get items in this gate pass
		items = []
		for item in gp_doc.items:
			items.append({
				"item_code": item.item_code,
				"item_name": item.item_name,
				"description": item.description,
				"qty": item.qty,
				"uom": item.uom,
				"branch": item.branch or gp_doc.branch,
				"handling_unit": item.handling_unit
			})
		
		gate_pass_data["items"] = items
		gate_pass_data["item_count"] = len(items)
		
		return gate_pass_data
		
	except Exception as e:
		frappe.log_error(f"Error getting gate pass details: {str(e)}")
		return {}
