# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt


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
def get_dashboard_html(special_project):
	"""Generate HTML for Dashboard tab: resources, jobs, billings, costs, budgets, deliveries."""
	if not special_project:
		return "<div class='alert alert-info'>Save the project to view the dashboard.</div>"
	try:
		doc = frappe.get_doc("Special Project", special_project)
		status = doc.status or "Draft"
		status_class = status.lower().replace(" ", "-").replace("/", "-")

		# Resources
		resources = doc.get("resources") or []
		res_count = len(resources)
		planned_hrs = sum(flt(r.planned_hours or 0) for r in resources)
		actual_hrs = sum(flt(r.actual_hours or 0) for r in resources)

		# Jobs
		jobs = doc.get("jobs") or []
		job_count = len(jobs)
		planned_cost = sum(flt(j.planned_cost or 0) for j in jobs)
		actual_cost = sum(flt(j.actual_cost or 0) for j in jobs)
		planned_rev = sum(flt(j.planned_revenue or 0) for j in jobs)
		actual_rev = sum(flt(j.actual_revenue or 0) for j in jobs)

		# Billings
		billings = doc.get("billings") or []
		bill_count = len(billings)
		bill_planned = sum(flt(b.planned_amount or 0) for b in billings)
		bill_pending = sum(1 for b in billings if (b.status or "").strip() == "Pending")
		bill_invoiced = sum(1 for b in billings if (b.status or "").strip() in ("Invoiced", "Paid"))

		# Deliveries
		deliveries = doc.get("deliveries") or []
		del_count = len(deliveries)
		del_pending = sum(1 for d in deliveries if (d.status or "").strip() in ("Pending", "Scheduled"))
		del_completed = sum(1 for d in deliveries if (d.status or "").strip() == "Completed")

		def fmt(v):
			return frappe.format_value(v, df={"fieldtype": "Currency"}) if v is not None else "—"

		html = f"""
		<div class="sp-dashboard">
			<div class="dash-header">
				<div class="dash-status-badge {status_class}">{status}</div>
				<div class="dash-meta">
					<span>{doc.project_name or doc.name}</span>
					{f'<span class="dash-priority">{doc.priority}</span>' if doc.priority else ''}
				</div>
			</div>
			<div class="dash-grid">
				<div class="dash-card">
					<div class="dash-card-title">Resources</div>
					<div class="dash-card-body">
						<div class="dash-row"><span>Count</span><strong>{res_count}</strong></div>
						<div class="dash-row"><span>Planned hrs</span><strong>{planned_hrs:.1f}</strong></div>
						<div class="dash-row"><span>Actual hrs</span><strong>{actual_hrs:.1f}</strong></div>
					</div>
				</div>
				<div class="dash-card">
					<div class="dash-card-title">Jobs</div>
					<div class="dash-card-body">
						<div class="dash-row"><span>Count</span><strong>{job_count}</strong></div>
						<div class="dash-row"><span>Planned Cost</span><strong>{fmt(planned_cost)}</strong></div>
						<div class="dash-row"><span>Actual Cost</span><strong>{fmt(actual_cost)}</strong></div>
						<div class="dash-row"><span>Planned Revenue</span><strong>{fmt(planned_rev)}</strong></div>
						<div class="dash-row"><span>Actual Revenue</span><strong>{fmt(actual_rev)}</strong></div>
					</div>
				</div>
				<div class="dash-card">
					<div class="dash-card-title">Billings</div>
					<div class="dash-card-body">
						<div class="dash-row"><span>Items</span><strong>{bill_count}</strong></div>
						<div class="dash-row"><span>Planned</span><strong>{fmt(bill_planned)}</strong></div>
						<div class="dash-row"><span>Pending</span><strong>{bill_pending}</strong></div>
						<div class="dash-row"><span>Invoiced/Paid</span><strong>{bill_invoiced}</strong></div>
					</div>
				</div>
				<div class="dash-card">
					<div class="dash-card-title">Deliveries</div>
					<div class="dash-card-body">
						<div class="dash-row"><span>Total</span><strong>{del_count}</strong></div>
						<div class="dash-row"><span>Pending</span><strong>{del_pending}</strong></div>
						<div class="dash-row"><span>Completed</span><strong>{del_completed}</strong></div>
					</div>
				</div>
			</div>
			<div class="dash-summary">
				<div class="dash-summary-item"><span class="dash-num">{fmt(planned_cost)}</span><span class="dash-desc">Budget (Cost)</span></div>
				<div class="dash-summary-item"><span class="dash-num">{fmt(actual_cost)}</span><span class="dash-desc">Actual Cost</span></div>
				<div class="dash-summary-item"><span class="dash-num">{fmt(planned_rev)}</span><span class="dash-desc">Budget (Revenue)</span></div>
				<div class="dash-summary-item"><span class="dash-num">{fmt(actual_rev)}</span><span class="dash-desc">Actual Revenue</span></div>
			</div>
		</div>
		<style>
		.sp-dashboard {{ font-family: inherit; font-size: 13px; }}
		.dash-header {{ display: flex; align-items: center; gap: 16px; flex-wrap: wrap; margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px solid #e0e0e0; }}
		.dash-status-badge {{ padding: 4px 12px; border-radius: 6px; font-weight: 600; font-size: 12px; text-transform: uppercase; }}
		.dash-status-badge.draft {{ background: #e2e3e5; color: #383d41; }}
		.dash-status-badge.scoping {{ background: #cce5ff; color: #004085; }}
		.dash-status-badge.booked {{ background: #d4edda; color: #155724; }}
		.dash-status-badge.planning {{ background: #fff3cd; color: #856404; }}
		.dash-status-badge.approved {{ background: #d4edda; color: #155724; }}
		.dash-status-badge.in-progress {{ background: #cce5ff; color: #004085; }}
		.dash-status-badge.on-hold {{ background: #f8d7da; color: #721c24; }}
		.dash-status-badge.completed {{ background: #d4edda; color: #155724; }}
		.dash-status-badge.cancelled {{ background: #e2e3e5; color: #6c757d; }}
		.dash-meta {{ font-size: 14px; color: #333; }}
		.dash-priority {{ margin-left: 8px; padding: 2px 6px; background: #f8f9fa; border-radius: 4px; font-size: 11px; }}
		.dash-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; margin-bottom: 16px; }}
		.dash-card {{ background: #fff; border: 1px solid #e0e0e0; border-radius: 6px; overflow: hidden; }}
		.dash-card-title {{ background: #f8f9fa; padding: 8px 12px; font-weight: 600; font-size: 12px; color: #495057; }}
		.dash-card-body {{ padding: 10px 12px; }}
		.dash-row {{ display: flex; justify-content: space-between; margin-bottom: 4px; font-size: 12px; }}
		.dash-row span {{ color: #6c757d; }}
		.dash-row strong {{ color: #333; }}
		.dash-summary {{ display: flex; gap: 12px; flex-wrap: wrap; }}
		.dash-summary-item {{ background: #fff; border: 1px solid #e0e0e0; border-radius: 6px; padding: 10px 14px; min-width: 100px; text-align: center; }}
		.dash-num {{ display: block; font-size: 14px; font-weight: 700; color: #007bff; }}
		.dash-desc {{ font-size: 11px; color: #6c757d; }}
		</style>
		"""
		return html
	except Exception as e:
		frappe.log_error(f"Special Project get_dashboard_html: {str(e)}", "Special Project Dashboard")
		return "<div class='alert alert-warning'>Error loading dashboard.</div>"


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
