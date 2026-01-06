# -*- coding: utf-8 -*-
# Copyright (c) 2025, Logistics Team and contributors
# For license information, please see license.txt

from __future__ import unicode_literals
import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime, get_datetime, time_diff_in_seconds

class FlightSchedule(Document):
	def validate(self):
		"""Validate Flight Schedule"""
		if not self.flight_number:
			frappe.throw("Flight Number is required")
		
		# Calculate delay if actual times are available
		if self.departure_time_scheduled and self.departure_time_actual:
			delay_seconds = time_diff_in_seconds(
				self.departure_time_actual,
				self.departure_time_scheduled
			)
			self.delay_minutes = int(delay_seconds / 60)
		
		# Calculate duration if both departure and arrival are available
		if self.departure_time_actual and self.arrival_time_actual:
			duration_seconds = time_diff_in_seconds(
				self.arrival_time_actual,
				self.departure_time_actual
			)
			self.flight_duration_minutes = int(duration_seconds / 60)
		elif self.departure_time_scheduled and self.arrival_time_scheduled:
			duration_seconds = time_diff_in_seconds(
				self.arrival_time_scheduled,
				self.departure_time_scheduled
			)
			self.flight_duration_minutes = int(duration_seconds / 60)
		
		# Calculate available cargo capacity
		if self.cargo_capacity_kg:
			self.available_cargo_capacity_kg = self.cargo_capacity_kg - (self.cargo_booked_kg or 0)
		
		# Update last_updated timestamp
		self.last_updated = now_datetime()
	
	def on_update(self):
		"""Called after saving"""
		# Update linked Air Shipments if any
		self.update_linked_air_shipments()
		
		# Send notifications for significant changes
		self.check_and_send_notifications()
	
	def update_linked_air_shipments(self):
		"""Update linked Air Shipment records with latest flight data"""
		try:
			# Find Air Shipments linked to this flight
			jobs = frappe.get_all(
				"Air Shipment",
				filters={"flight_schedule": self.name},
				fields=["name"]
			)
			
			for job in jobs:
				job_doc = frappe.get_doc("Air Shipment", job.name)
				
				# Update flight times
				if self.departure_time_actual:
					job_doc.actual_departure = self.departure_time_actual
				if self.arrival_time_actual:
					job_doc.actual_arrival = self.arrival_time_actual
				
				# Update flight status
				if self.flight_status:
					job_doc.flight_status = self.flight_status
				
				job_doc.save(ignore_permissions=True)
				
		except Exception as e:
			frappe.log_error(f"Error updating linked Air Shipments: {str(e)}")
	
	def check_and_send_notifications(self):
		"""Send notifications for flight status changes"""
		if self.has_value_changed("flight_status"):
			self.send_status_change_notification()
		
		if self.delay_minutes and self.delay_minutes > 30:
			self.send_delay_notification()
	
	def send_status_change_notification(self):
		"""Send notification when flight status changes"""
		try:
			# Get users who need to be notified
			users_to_notify = self.get_users_to_notify()
			
			for user in users_to_notify:
				frappe.publish_realtime(
					event='flight_status_changed',
					message={
						'flight_number': self.flight_number,
						'status': self.flight_status,
						'flight_schedule': self.name
					},
					user=user
				)
				
		except Exception as e:
			frappe.log_error(f"Error sending status change notification: {str(e)}")
	
	def send_delay_notification(self):
		"""Send notification for flight delays"""
		try:
			users_to_notify = self.get_users_to_notify()
			
			for user in users_to_notify:
				frappe.publish_realtime(
					event='flight_delayed',
					message={
						'flight_number': self.flight_number,
						'delay_minutes': self.delay_minutes,
						'flight_schedule': self.name
					},
					user=user
				)
				
		except Exception as e:
			frappe.log_error(f"Error sending delay notification: {str(e)}")
	
	def get_users_to_notify(self):
		"""Get list of users who should be notified about this flight"""
		users = []
		
		try:
			# Get users from linked Air Shipments
			jobs = frappe.get_all(
				"Air Shipment",
				filters={"flight_schedule": self.name},
				fields=["owner", "modified_by"]
			)
			
			for job in jobs:
				if job.owner:
					users.append(job.owner)
				if job.modified_by:
					users.append(job.modified_by)
			
			# Remove duplicates
			users = list(set(users))
			
		except Exception as e:
			frappe.log_error(f"Error getting users to notify: {str(e)}")
		
		return users

@frappe.whitelist()
def get_flight_by_number(flight_number, date=None):
	"""Get flight schedule by flight number and date"""
	filters = {"flight_number": flight_number}
	
	if date:
		from frappe.utils import getdate
		date_obj = getdate(date)
		filters["departure_time_scheduled"] = ["between", [
			f"{date_obj} 00:00:00",
			f"{date_obj} 23:59:59"
		]]
	
	flights = frappe.get_all(
		"Flight Schedule",
		filters=filters,
		fields=["*"],
		order_by="departure_time_scheduled desc",
		limit=1
	)
	
	return flights[0] if flights else None


