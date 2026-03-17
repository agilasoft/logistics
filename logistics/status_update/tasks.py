# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Scheduled tasks for auto-updating statuses and dates of milestones,
documents, permits, and exemptions.
"""

from __future__ import unicode_literals

import frappe
from frappe.utils import getdate, today, date_diff, now_datetime


# Child table doctypes that have milestone rows (parenttype -> child doctype)
MILESTONE_CHILD_TABLES = [
	"Air Shipment Milestone",
	"Air Consolidation Milestone",
	"Sea Shipment Milestone",
	"Sea Consolidation Milestone",
	"Sea Booking Milestone",
	"Transport Job Milestone",
	"Declaration Milestone",
	"Declaration Order Milestone",
]


def update_milestone_statuses():
	"""
	Mark milestones as Delayed when planned_end has passed and actual_end is not set.
	Runs hourly.
	"""
	try:
		settings = frappe.get_single("Logistics Settings")
		if getattr(settings, "enable_auto_status_updates", 1) == 0:
			return

		now = now_datetime()
		updated = 0

		for child_doctype in MILESTONE_CHILD_TABLES:
			if not frappe.db.table_exists(child_doctype):
				continue
			rows = frappe.get_all(
				child_doctype,
				filters={
					"status": ["in", ["Planned", "Started"]],
					"planned_end": ["<", now],
					"actual_end": ["is", "not set"],
				},
				fields=["name", "parent", "parenttype"],
				limit=500,
			)
			for row in rows:
				try:
					frappe.db.set_value(
						child_doctype,
						row.name,
						"status",
						"Delayed",
						update_modified=False,
					)
					updated += 1
				except Exception as e:
					frappe.log_error(
						f"Error updating milestone {child_doctype} {row.name}: {e}",
						"Milestone Status Update Error",
					)

		if updated:
			frappe.db.commit()
	except Exception as e:
		frappe.log_error(
			f"Error in update_milestone_statuses: {e}",
			"Milestone Status Task Error",
		)


def update_document_statuses():
	"""
	Bulk update Job Document status: Overdue when date_required passed, Expired when expiry_date passed.
	Runs daily.
	"""
	try:
		settings = frappe.get_single("Logistics Settings")
		if getattr(settings, "enable_auto_status_updates", 1) == 0:
			return

		today_date = getdate(today())
		updated = 0

		# Overdue: status in Pending/Uploaded/Overdue, date_required < today
		overdue_rows = frappe.get_all(
			"Job Document",
			filters={
				"status": ["in", ["Pending", "Uploaded", "Overdue"]],
				"date_required": ["<", today_date],
			},
			fields=["name", "date_required", "status"],
			limit=1000,
		)
		for row in overdue_rows:
			try:
				required = getdate(row.date_required)
				days = date_diff(today_date, required)
				frappe.db.set_value(
					"Job Document",
					row.name,
					{"status": "Overdue", "overdue_days": days},
					update_modified=False,
				)
				updated += 1
			except Exception as e:
				frappe.log_error(
					f"Error updating Job Document {row.name}: {e}",
					"Document Status Update Error",
				)

		# Expired: expiry_date < today
		expired_rows = frappe.get_all(
			"Job Document",
			filters={
				"status": ["not in", ["Expired"]],
				"expiry_date": ["<", today_date],
			},
			fields=["name"],
			limit=1000,
		)
		for row in expired_rows:
			try:
				frappe.db.set_value(
					"Job Document",
					row.name,
					"status",
					"Expired",
					update_modified=False,
				)
				updated += 1
			except Exception as e:
				frappe.log_error(
					f"Error updating Job Document {row.name}: {e}",
					"Document Status Update Error",
				)

		if updated:
			frappe.db.commit()
	except Exception as e:
		frappe.log_error(
			f"Error in update_document_statuses: {e}",
			"Document Status Task Error",
		)


def update_permit_statuses():
	"""
	Set Permit Application status to Expired when valid_to has passed.
	Runs daily.
	"""
	try:
		settings = frappe.get_single("Logistics Settings")
		if getattr(settings, "enable_auto_status_updates", 1) == 0:
			return

		today_date = getdate(today())
		rows = frappe.get_all(
			"Permit Application",
			filters={
				"status": "Approved",
				"valid_to": ["<", today_date],
			},
			fields=["name"],
			limit=500,
		)
		updated = 0
		for row in rows:
			try:
				frappe.db.set_value(
					"Permit Application",
					row.name,
					"status",
					"Expired",
					update_modified=False,
				)
				updated += 1
			except Exception as e:
				frappe.log_error(
					f"Error updating Permit Application {row.name}: {e}",
					"Permit Status Update Error",
				)
		if updated:
			frappe.db.commit()
	except Exception as e:
		frappe.log_error(
			f"Error in update_permit_statuses: {e}",
			"Permit Status Task Error",
		)


def update_exemption_statuses():
	"""
	Set Exemption Certificate status to Expired when valid_to passed or fully used.
	Runs daily.
	"""
	try:
		settings = frappe.get_single("Logistics Settings")
		if getattr(settings, "enable_auto_status_updates", 1) == 0:
			return

		today_date = getdate(today())
		rows = frappe.get_all(
			"Exemption Certificate",
			filters={"status": "Active"},
			fields=["name", "valid_to", "remaining_value", "remaining_quantity", "exemption_value", "exemption_quantity"],
			limit=500,
		)
		updated = 0
		for row in rows:
			try:
				expired = False
				if row.valid_to and getdate(row.valid_to) < today_date:
					expired = True
				elif row.exemption_value and (row.remaining_value or 0) <= 0:
					if not row.exemption_quantity or (row.remaining_quantity or 0) <= 0:
						expired = True
				if expired:
					frappe.db.set_value(
						"Exemption Certificate",
						row.name,
						"status",
						"Expired",
						update_modified=False,
					)
					updated += 1
			except Exception as e:
				frappe.log_error(
					f"Error updating Exemption Certificate {row.name}: {e}",
					"Exemption Status Update Error",
				)
		if updated:
			frappe.db.commit()
	except Exception as e:
		frappe.log_error(
			f"Error in update_exemption_statuses: {e}",
			"Exemption Status Task Error",
		)
