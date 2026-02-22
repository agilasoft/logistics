# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


class SpecialProject(Document):
	def validate(self):
		pass

	def autoname(self):
		"""Use ERPNext Project ID as Special Project ID (created in before_insert)."""
		if self.flags.get("erpnext_project_name"):
			self.name = self.flags.erpnext_project_name

	def before_insert(self):
		"""Create ERPNext Project first, then use its ID as this document's ID."""
		self._create_erpnext_project_before_insert()

	def on_update(self):
		"""Auto-charge scoping costs when status changes to Booked."""
		if self.has_value_changed("status") and self.status in ("Booked", "Approved", "Planning", "In Progress"):
			self._maybe_charge_scoping_costs()

	def _maybe_charge_scoping_costs(self):
		"""Charge completed scoping activities when project is booked."""
		changed = False
		for row in self.scoping_activities or []:
			if row.status == "Completed" and not row.charged_to_project:
				row.charged_to_project = 1
				row.charged_date = frappe.utils.today()
				changed = True
		# Save is handled by on_update flow

	def _create_erpnext_project_before_insert(self):
		"""Create ERPNext Project first; its ID will be used as Special Project ID via autoname."""
		if self.project:
			# Link Existing Project: use that Project's ID as our name
			self.flags.erpnext_project_name = self.project
			return

		if not frappe.db.exists("DocType", "Project"):
			return

		try:
			project = frappe.new_doc("Project")
			project.project_name = (
				self.project_name
				or f"Special Project {frappe.utils.now_datetime().strftime('%Y%m%d%H%M%S')}"
			)
			project.customer = self.customer
			project.expected_start_date = self.planned_start or self.start_date
			project.expected_end_date = self.planned_end or self.end_date
			project.status = self._map_status_to_project(self.status)
			project.project_type = frappe.db.get_single_value(
				"Special Project Settings", "default_project_type"
			) or frappe.db.get_value("Project Type", {"name": "External"}, "name")
			project.company = frappe.defaults.get_defaults().get("company")

			project.insert(ignore_permissions=True)

			self.project = project.name
			self.flags.erpnext_project_name = project.name
		except Exception as e:
			frappe.log_error(
				title=_("Special Project: Failed to create ERPNext Project"),
				message=frappe.get_traceback(),
			)
			raise

	def _map_status_to_project(self, status):
		"""Map Special Project status to ERPNext Project status."""
		status_map = {
			"Draft": "Open",
			"Scoping": "Open",
			"Booked": "Open",
			"Planning": "Open",
			"Approved": "Open",
			"In Progress": "Open",
			"On Hold": "Open",
			"Completed": "Completed",
			"Cancelled": "Cancelled",
		}
		return status_map.get(status, "Open")


@frappe.whitelist()
def charge_scoping_costs(special_project):
	"""Charge all completed scoping activities to the project when it is booked."""
	doc = frappe.get_doc("Special Project", special_project)
	if doc.status not in ("Booked", "Approved", "Planning", "In Progress", "Completed"):
		frappe.throw(_("Project must be Booked or Approved to charge scoping costs."))

	changed = False
	for row in doc.scoping_activities or []:
		if row.status == "Completed" and not row.charged_to_project:
			row.charged_to_project = 1
			row.charged_date = frappe.utils.today()
			changed = True

	if changed:
		doc.save()
	return "Scoping costs charged."


@frappe.whitelist()
def get_cost_revenue_summary(special_project):
	"""Return HTML for Cost & Revenue Summary from jobs table."""
	if not special_project:
		return ""
	doc = frappe.get_doc("Special Project", special_project)
	jobs = doc.get("jobs") or []

	planned_cost = sum((j.planned_cost or 0) for j in jobs)
	actual_cost = sum((j.actual_cost or 0) for j in jobs)
	planned_revenue = sum((j.planned_revenue or 0) for j in jobs)
	actual_revenue = sum((j.actual_revenue or 0) for j in jobs)
	planned_margin = planned_revenue - planned_cost if planned_revenue or planned_cost else None
	actual_margin = actual_revenue - actual_cost if actual_revenue or actual_cost else None

	def fmt(v):
		return frappe.format_value(v, df={"fieldtype": "Currency"}) if v is not None else "—"

	rows = [
		f"<tr><td>{_('Planned Cost')}</td><td class='text-right'>{fmt(planned_cost)}</td>"
		f"<td>{_('Planned Revenue')}</td><td class='text-right'>{fmt(planned_revenue)}</td></tr>",
		f"<tr><td>{_('Actual Cost')}</td><td class='text-right'>{fmt(actual_cost)}</td>"
		f"<td>{_('Actual Revenue')}</td><td class='text-right'>{fmt(actual_revenue)}</td></tr>",
		f"<tr><td>{_('Planned Margin')}</td><td class='text-right'>{fmt(planned_margin)}</td>"
		f"<td>{_('Actual Margin')}</td><td class='text-right'>{fmt(actual_margin)}</td></tr>",
	]
	html = f'<table class="table table-bordered table-sm" style="max-width: 500px;"><tbody>{"".join(rows)}</tbody></table>'
	return html
