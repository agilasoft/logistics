# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document



class ProjectJob(Document):
	def validate(self):
		from logistics.utils.document_date_validation import validate_planned_date_range

		validate_planned_date_range(self)
		if self.special_project:
			row = frappe.db.get_value(
				"Special Project",
				self.special_project,
				["customer", "project"],
				as_dict=True,
			)
			if row:
				if row.get("customer") and not self.customer:
					self.customer = row.customer
				# project is fetch_from on the form; keep DB row aligned if user saved without child fetch
				if row.get("project") and not self.get("project"):
					self.project = row.project

	def before_save(self):
		self.create_job_number_if_needed()
		if self.job_number:
			self.sync_job_number_to_project_order()

	def after_insert(self):
		original_jcn = self.job_number
		self.create_job_number_if_needed()
		if self.job_number and self.job_number != original_jcn:
			try:
				self.save(ignore_permissions=True)
			except Exception as e:
				frappe.log_error(
					f"Error saving Project Job {self.name} after creating Job Number: {e!s}",
					"Project Job Save Error",
				)
		elif self.job_number:
			self.sync_job_number_to_project_order()

	def create_job_number_if_needed(self):
		"""Create Job Number when document is first saved."""
		if self.job_number:
			self.sync_job_number_to_project_order()
			return

		if not self.name:
			return

		if not self.company:
			return

		existing_job_ref = frappe.db.get_value(
			"Job Number",
			{"job_type": "Project Job", "job_no": self.name},
		)
		if existing_job_ref:
			self.job_number = existing_job_ref
			self.sync_job_number_to_project_order()
			return

		try:
			job_ref = frappe.new_doc("Job Number")
			job_ref.job_type = "Project Job"
			job_ref.job_no = self.name
			job_ref.company = self.company
			job_ref.branch = self.branch
			job_ref.cost_center = self.cost_center
			job_ref.profit_center = self.profit_center
			if self.job_date:
				job_ref.job_open_date = self.job_date
			job_ref.insert(ignore_permissions=True)
			self.job_number = job_ref.name
			self.sync_job_number_to_project_order()
			frappe.msgprint(_("Job Number {0} created successfully").format(job_ref.name))
		except frappe.DuplicateEntryError as e:
			existing = frappe.db.get_value(
				"Job Number",
				{"job_type": "Project Job", "job_no": self.name},
			)
			if existing:
				self.job_number = existing
				self.sync_job_number_to_project_order()
				return
			frappe.log_error(
				f"Duplicate Job Number error for Project Job {self.name}: {e!s}",
				"Job Number Duplicate Error",
			)
			raise
		except Exception as e:
			frappe.log_error(
				f"Error creating Job Number for Project Job {self.name}: {e!s}",
				"Job Number Creation Error",
			)

	def sync_job_number_to_project_order(self):
		"""Sync Job Number from Project Job to related Project Order."""
		if not self.job_number:
			return

		if not getattr(self, "special_project_order", None):
			return

		try:
			order_jcn = frappe.db.get_value(
				"Project Order", self.special_project_order, "job_number"
			)
			if order_jcn != self.job_number:
				frappe.db.set_value(
					"Project Order",
					self.special_project_order,
					"job_number",
					self.job_number,
				)
		except Exception as e:
			frappe.log_error(
				f"Error syncing Job Number to Project Order {self.special_project_order}: {e!s}",
				"Job Number Sync Error",
			)

	def on_submit(self):
		try:
			from logistics.special_projects.special_project_packages import (
				post_site_receipts_from_project_doc,
			)

			post_site_receipts_from_project_doc(self)
		except Exception:
			frappe.log_error(
				frappe.get_traceback(),
				f"Project Job {self.name}: package delivery post",
			)

	def on_cancel(self):
		try:
			from logistics.special_projects.special_project_packages import (
				cancel_receipts_for_project_doc,
			)

			cancel_receipts_for_project_doc(self)
		except Exception:
			frappe.log_error(
				frappe.get_traceback(),
				f"Project Job {self.name}: package delivery cancel",
			)
