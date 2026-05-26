# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import flt

from logistics.exhibits import exhibit_lifecycle
from logistics.exhibits.exhibit_lifecycle import validate_lifecycle_stage_advance
from logistics.utils.lifecycle_stage import (
	FOR_EXHIBITS,
	resolve_default_lifecycle_stage,
	validate_internal_job_activity_codes,
)


class Exhibit(Document):
	def validate(self):
		self._ensure_charges_tab_defaults()
		validate_internal_job_activity_codes(self, module_filter=FOR_EXHIBITS)
		validate_lifecycle_stage_advance(self)
		self._validate_unique_exhibitor_participants()
		self._validate_participant_docket_links()
		from logistics.utils.charges_calculation import (
			clear_charge_resolution_parent,
			register_charge_resolution_parent,
		)

		register_charge_resolution_parent(self)
		try:
			self.validate_accounts()
			self._sync_charges_with_parent_actuals()
		finally:
			clear_charge_resolution_parent(self)

	def _validate_unique_exhibitor_participants(self):
		"""Each exhibitor Customer must appear at most once on this Exhibit
		(the Docket naming format ``{exhibit}-{exhibitor}`` requires uniqueness)."""
		seen = {}
		for row in self.get("dockets") or []:
			cust = (row.customer or "").strip()
			if not cust:
				continue
			if cust in seen:
				frappe.throw(
					_(
						"Customer {0} appears more than once as an Exhibitor on this Exhibit "
						"(rows {1} and {2}). Each exhibitor may only be listed once."
					).format(frappe.bold(cust), seen[cust], row.idx)
				)
			seen[cust] = row.idx

	def _validate_participant_docket_links(self):
		"""If a docket row already has a Docket linked, ensure it matches this Exhibit +
		the row's customer. Drop stale links silently if the Docket no longer exists."""
		for row in self.get("dockets") or []:
			docket = (row.docket or "").strip()
			if not docket:
				continue
			vals = frappe.db.get_value(
				"Docket", docket, ["exhibit", "exhibitor"], as_dict=True
			)
			if not vals:
				row.docket = ""
				continue
			if self.name and vals.get("exhibit") and vals.exhibit != self.name:
				frappe.throw(
					_(
						"Docket {0} on row {1} belongs to Exhibit {2}, not {3}."
					).format(
						frappe.bold(docket),
						row.idx,
						frappe.bold(vals.exhibit),
						frappe.bold(self.name),
					)
				)
			if row.customer and vals.get("exhibitor") and vals.exhibitor != row.customer:
				frappe.throw(
					_(
						"Docket {0} on row {1} belongs to Customer {2}, not {3}."
					).format(
						frappe.bold(docket),
						row.idx,
						frappe.bold(vals.exhibitor),
						frappe.bold(row.customer),
					)
				)

	def validate_accounts(self):
		"""Ensure cost center / profit center / branch belong to company."""
		if not self.company:
			return
		if self.cost_center:
			cc_co = frappe.db.get_value("Cost Center", self.cost_center, "company")
			if cc_co and cc_co != self.company:
				frappe.throw(
					_("Cost Center {0} does not belong to Company {1}").format(self.cost_center, self.company)
				)
		if self.profit_center:
			try:
				pc_meta = frappe.get_meta("Profit Center")
				if pc_meta.has_field("company"):
					pc_co = frappe.db.get_value("Profit Center", self.profit_center, "company")
					if pc_co and pc_co != self.company:
						frappe.throw(
							_("Profit Center {0} does not belong to Company {1}").format(
								self.profit_center, self.company
							)
						)
			except Exception as e:
				if "Unknown column" not in str(e) and "1054" not in str(e):
					raise
		if self.branch:
			try:
				br_meta = frappe.get_meta("Branch")
				if br_meta.has_field("company"):
					br_co = frappe.db.get_value("Branch", self.branch, "company")
					if br_co and br_co != self.company:
						frappe.throw(_("Branch {0} does not belong to Company {1}").format(self.branch, self.company))
			except Exception as e:
				if "Unknown column" not in str(e) and "1054" not in str(e):
					raise

	def _sync_charges_with_parent_actuals(self):
		if getattr(frappe.flags, "in_import", False) or getattr(frappe.flags, "in_migrate", False):
			return
		if getattr(self.flags, "ignore_charges_sync", False):
			return
		for charge in self.get("charges") or []:
			if hasattr(charge, "calculate_charge_amount"):
				charge.calculate_charge_amount(parent_doc=self)

	def autoname(self):
		"""Use ERPNext Project ID as Exhibit ID (created in before_insert)."""
		if self.flags.get("erpnext_project_name"):
			self.name = self.flags.erpnext_project_name

	def before_insert(self):
		"""Create ERPNext Project first, then use its ID as this document's ID."""
		self._create_erpnext_project_before_insert()
		self._ensure_charges_tab_defaults()
		self._normalize_default_lifecycle_stage()
		exhibit_lifecycle.load_standard_service_activities(self)

	def _normalize_default_lifecycle_stage(self):
		"""Ensure ``lifecycle_stage`` references an existing master row.

		Mirror of the guard on ``Special Project``: avoid ``LinkValidationError`` on
		insert when the shared Lifecycle Stage master has not been seeded yet.
		"""
		stage = (self.lifecycle_stage or "").strip()
		if stage and frappe.db.exists("Lifecycle Stage", stage):
			self.lifecycle_stage = stage
			return
		self.lifecycle_stage = resolve_default_lifecycle_stage(
			module_filter=FOR_EXHIBITS, preferred="Pre-Show"
		)

	def _ensure_charges_tab_defaults(self):
		"""Default company / cost center from Project or session (Charges tab matches Sea Shipment)."""
		if not self.company:
			co = None
			if self.project:
				co = frappe.db.get_value("Project", self.project, "company")
			if not co:
				co = frappe.defaults.get_user_default("Company")
			if not co:
				co = frappe.db.get_single_value("Global Defaults", "default_company")
			if co:
				self.company = co
		if self.company and not self.cost_center:
			cc = frappe.db.get_value("Company", self.company, "cost_center")
			if cc:
				self.cost_center = cc

	def on_update(self):
		"""Hook reserved for future status-change side effects."""
		return

	def _create_erpnext_project_before_insert(self):
		"""Create ERPNext Project first; its ID will be used as Exhibit ID via autoname."""
		if self.project:
			self.flags.erpnext_project_name = self.project
			return

		if not frappe.db.exists("DocType", "Project"):
			return

		try:
			project = frappe.new_doc("Project")
			project.project_name = (
				self.project_name
				or f"Exhibit {frappe.utils.now_datetime().strftime('%Y%m%d%H%M%S')}"
			)
			project.customer = self.customer
			project.expected_start_date = self.planned_start or self.start_date
			project.expected_end_date = self.planned_end or self.end_date
			project.status = self._map_status_to_project(self.status)
			project.project_type = (
				self.project_type
				or frappe.db.get_single_value("Exhibit Settings", "default_project_type")
				or frappe.db.get_value("Project Type", {"name": "External"}, "name")
			)
			project.company = frappe.defaults.get_defaults().get("company")

			project.insert(ignore_permissions=True)

			self.project = project.name
			self.flags.erpnext_project_name = project.name
		except Exception:
			frappe.log_error(
				title=_("Exhibit: Failed to create ERPNext Project"),
				message=frappe.get_traceback(),
			)
			raise

	def _map_status_to_project(self, status):
		"""Map Exhibit status to ERPNext Project status."""
		status_map = {
			"Draft": "Open",
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
def reload_standard_service_activities(show):
	"""Reload the standard lifecycle jobs on an existing programme."""
	doc = frappe.get_doc("Exhibit", show)
	doc.set(
		"lifecycle_jobs",
		[r for r in doc.get("lifecycle_jobs") or [] if not (r.activity_code or "").strip()],
	)
	exhibit_lifecycle.load_standard_lifecycle_jobs(doc)
	doc.save()
	return _("Standard lifecycle jobs loaded.")


@frappe.whitelist()
def load_standard_service_activities(show):
	"""Backward-compatible alias for reload_standard_service_activities."""
	return reload_standard_service_activities(show)


@frappe.whitelist()
def recalculate_all_charges(docname):
	"""Recalculate all Exhibit charge lines on this programme."""
	doc = frappe.get_doc("Exhibit", docname)
	if not doc.get("charges"):
		return {"success": False, "message": _("No charges found to recalculate")}
	try:
		n = 0
		for charge in doc.charges:
			if hasattr(charge, "calculate_charge_amount"):
				charge.calculate_charge_amount(parent_doc=doc)
				n += 1
		doc.save()
		return {
			"success": True,
			"message": _("Successfully recalculated {0} charges").format(n),
			"charges_recalculated": n,
		}
	except Exception as e:
		frappe.log_error(str(e), "Exhibit - Recalculate Charges Error")
		frappe.throw(_("Error recalculating charges: {0}").format(str(e)))


@frappe.whitelist()
def get_cost_revenue_summary(show):
	"""Return HTML for Cost & Revenue Summary from project job lines."""
	if not show:
		return ""
	doc = frappe.get_doc("Exhibit", show)
	rows = doc.get("lifecycle_jobs") or []

	planned_cost = sum((flt(a.planned_cost) or 0) for a in rows)
	actual_cost = sum((flt(a.actual_cost) or 0) for a in rows)
	planned_revenue = sum((flt(a.planned_revenue) or 0) for a in rows)
	actual_revenue = sum((flt(a.actual_revenue) or 0) for a in rows)
	planned_margin = planned_revenue - planned_cost if planned_revenue or planned_cost else None
	actual_margin = actual_revenue - actual_cost if actual_revenue or actual_cost else None

	def fmt(v):
		return frappe.format_value(v, df={"fieldtype": "Currency"}) if v is not None else "—"

	html_rows = [
		f"<tr><td>{_('Planned Cost')}</td><td class='text-right'>{fmt(planned_cost)}</td>"
		f"<td>{_('Planned Revenue')}</td><td class='text-right'>{fmt(planned_revenue)}</td></tr>",
		f"<tr><td>{_('Actual Cost')}</td><td class='text-right'>{fmt(actual_cost)}</td>"
		f"<td>{_('Actual Revenue')}</td><td class='text-right'>{fmt(actual_revenue)}</td></tr>",
		f"<tr><td>{_('Planned Margin')}</td><td class='text-right'>{fmt(planned_margin)}</td>"
		f"<td>{_('Actual Margin')}</td><td class='text-right'>{fmt(actual_margin)}</td></tr>",
	]
	return (
		'<table class="table table-bordered table-sm" style="max-width: 500px;">'
		f'<tbody>{"".join(html_rows)}</tbody></table>'
	)
