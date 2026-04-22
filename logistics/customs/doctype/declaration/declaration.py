# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import today, getdate, flt, cint
from typing import Dict, Any, Optional

from logistics.utils.charge_service_type import (
	customs_charges_rows_from_sales_quote_doc,
	throw_if_missing_destination_service_charge,
)
from logistics.utils.operational_rep_fields import copy_operational_rep_fields_from_declaration_order


class Declaration(Document):
	def validate(self):
		from logistics.utils.internal_job_main_link import validate_internal_job_main_link_unchanged

		validate_internal_job_main_link_unchanged(self)
		self._validate_declaration_order_unique()
		self._validate_etd_eta()
		self.update_payment_status()
		try:
			from logistics.utils.measurements import apply_measurement_uom_conversion_to_children
			apply_measurement_uom_conversion_to_children(self, "commercial_invoice_line_items", company=getattr(self, "company", None))
		except Exception:
			pass
		try:
			from logistics.job_management.recognition_engine import (
				sync_job_recognition_fields_from_policy,
			)

			sync_job_recognition_fields_from_policy(self)
		except Exception:
			pass

		from logistics.job_management.logistics_job_status import sync_declaration_job_status

		sync_declaration_job_status(self)

	def _validate_etd_eta(self):
		"""Departure must not be after arrival (same calendar day allowed)."""
		if not self.etd or not self.eta:
			return
		if getdate(self.etd) > getdate(self.eta):
			from logistics.utils.validation_user_messages import (
				declaration_etd_eta_invalid_message,
				declaration_etd_eta_title,
			)

			frappe.throw(
				declaration_etd_eta_invalid_message(),
				title=declaration_etd_eta_title(),
			)

	def _validate_declaration_order_unique(self):
		"""Ensure a Declaration Order can only be referenced by one Declaration."""
		if not self.declaration_order:
			return
		existing = frappe.db.get_all(
			"Declaration",
			filters={"declaration_order": self.declaration_order, "docstatus": ["<", 2]},
			pluck="name",
		)
		if not existing:
			return
		if len(existing) == 1 and self.name and existing[0] == self.name:
			return
		other = existing[1] if len(existing) > 1 else existing[0]
		frappe.throw(
			_("Declaration Order {0} is already linked to Declaration {1}. A Declaration Order can only be referenced by one Declaration.").format(
				self.declaration_order, other
			),
			title=_("Duplicate Declaration Order Reference"),
		)

	def before_save(self):
		"""Calculate values and metrics before saving"""
		from logistics.utils.module_integration import run_propagate_on_link
		from logistics.utils.shipper_consignee_defaults import apply_shipper_consignee_defaults
		from logistics.utils.transport_mode_defaults import apply_default_transport_document_type

		run_propagate_on_link(self)
		apply_shipper_consignee_defaults(self)
		apply_default_transport_document_type(self)
		self.calculate_total_payable()
		self.calculate_declaration_value()
		self.calculate_exemptions()
		self.calculate_sustainability_metrics()
		self.update_processing_dates()
		# Sync Job Number to Declaration Order if it exists
		if self.job_number:
			self.sync_job_number_to_declaration_order()
	
	def on_update(self):
		"""Handle status changes"""
		self.handle_status_changes()
		self.sync_internal_job_details_to_declaration_order()
	
	def before_submit(self):
		"""Validate before submission"""
		self.validate_permits()
		self.validate_permit_expiry()
		self.validate_exemption_certificates()
		throw_if_missing_destination_service_charge(self)
		# Auto-set status to Submitted when submitting from Draft
		if self.status == "Draft":
			self.status = "Submitted"
	
	def after_submit(self):
		"""Record sustainability metrics after declaration submission"""
		self.record_sustainability_metrics()
	
	def after_insert(self):
		"""Create Job Number after document is inserted"""
		# Store original job_number to check if it was created
		original_jcn = self.job_number
		self.create_job_number_if_needed()
		
		# Save the document if Job Number was created
		if self.job_number and self.job_number != original_jcn:
			try:
				self.save(ignore_permissions=True)
			except Exception as e:
				# If save fails, log error but don't raise
				frappe.log_error(
					f"Error saving Declaration {self.name} after creating Job Number: {str(e)}",
					"Declaration Save Error"
				)
			else:
				return
		self.sync_internal_job_details_to_declaration_order()

	def sync_internal_job_details_to_declaration_order(self):
		"""Keep linked Declaration Order Internal Jobs in sync when this Declaration's table changes."""
		try:
			from logistics.utils.internal_job_detail_copy import (
				sync_internal_job_details_from_declaration_to_declaration_order,
			)

			sync_internal_job_details_from_declaration_to_declaration_order(self)
		except Exception as e:
			frappe.log_error(
				f"Error syncing Internal Job Details to Declaration Order for Declaration {self.name}: {str(e)}",
				"Declaration Internal Job Sync Error",
			)

	def create_job_number_if_needed(self):
		"""Create Job Number when document is first saved"""
		# Only create if job_number is not set
		if not self.job_number:
			# Check if this is the first save (no existing Job Number)
			existing_job_ref = frappe.db.get_value("Job Number", {
				"job_type": "Declaration",
				"job_no": self.name
			})
			
			if not existing_job_ref:
				# Create Job Number
				try:
					job_ref = frappe.new_doc("Job Number")
					job_ref.job_type = "Declaration"
					job_ref.job_no = self.name
					job_ref.company = self.company
					job_ref.branch = self.branch
					job_ref.cost_center = self.cost_center
					job_ref.profit_center = self.profit_center
					# Use declaration_date as job_open_date if available
					job_ref.job_open_date = self.declaration_date
					job_ref.insert(ignore_permissions=True)
					
					# Set the job_number field
					self.job_number = job_ref.name
					
					# Sync to related Declaration Order if it exists
					self.sync_job_number_to_declaration_order()
					
					frappe.msgprint(_("Job Number {0} created successfully").format(job_ref.name))
				except frappe.DuplicateEntryError as e:
					# If duplicate entry error occurs, try to get the existing one
					if self.name:
						existing = frappe.db.get_value("Job Number", {
							"job_type": "Declaration",
							"job_no": self.name
						})
						if existing:
							self.job_number = existing
							self.sync_job_number_to_declaration_order()
							return
					frappe.log_error(
						f"Duplicate Job Number error for Declaration {self.name}: {str(e)}",
						"Job Number Duplicate Error"
					)
					raise
				except Exception as e:
					frappe.log_error(
						f"Error creating Job Number for Declaration {self.name}: {str(e)}",
						"Job Number Creation Error"
					)
					# Don't raise - allow document to save even if Job Number creation fails
		else:
			# If job_number is already set, sync to Declaration Order
			self.sync_job_number_to_declaration_order()
	
	def sync_job_number_to_declaration_order(self):
		"""Sync Job Number from Declaration to related Declaration Order"""
		if not self.job_number:
			return
		
		if not getattr(self, "declaration_order", None):
			return
		
		try:
			# Check if Declaration Order exists and get its current Job Number
			order_jcn = frappe.db.get_value("Declaration Order", self.declaration_order, "job_number")
			
			# Update Declaration Order if it doesn't have a Job Number or if it's different
			if order_jcn != self.job_number:
				frappe.db.set_value("Declaration Order", self.declaration_order, "job_number", self.job_number)
				frappe.db.commit()
		except Exception as e:
			# Log error but don't fail the declaration save
			frappe.log_error(
				f"Error syncing Job Number to Declaration Order {self.declaration_order}: {str(e)}",
				"Job Number Sync Error"
			)
	
	def calculate_total_payable(self):
		"""Calculate total payable from duty, tax, and other charges (after exemptions)"""
		duty = flt(self.duty_amount or 0)
		tax = flt(self.tax_amount or 0)
		other = flt(self.other_charges or 0)
		
		# Subtract exemptions if any
		total_exempted = self.get_total_exempted_amount()
		
		self.total_payable = (duty + tax + other) - total_exempted
		
		# Ensure total payable is not negative
		if self.total_payable < 0:
			self.total_payable = 0
	
	def calculate_exemptions(self):
		"""Calculate exemption amounts for each exemption in the declaration"""
		if not self.exemptions:
			return
		
		for exemption in self.exemptions:
			exemption_type = None
			type_code = exemption.exemption_type or exemption.get("planned_exemption_type")
			if type_code:
				try:
					exemption_type = frappe.get_doc("Exemption Type", type_code)
				except frappe.DoesNotExistError:
					continue
			
			# Calculate exempted amounts based on exemption type
			if exemption_type:
				exemption_percentage = flt(exemption.exemption_percentage or 0) or flt(
					exemption_type.exemption_percentage or 0
				)
				
				# Calculate exempted duty
				if self.duty_amount:
					exempted_duty = (flt(self.duty_amount) * exemption_percentage) / 100
					# Apply maximum value limit if set
					if exemption_type.maximum_value and exempted_duty > exemption_type.maximum_value:
						exempted_duty = exemption_type.maximum_value
					exemption.exempted_duty = exempted_duty
				
				# Calculate exempted tax
				if self.tax_amount:
					exempted_tax = (flt(self.tax_amount) * exemption_percentage) / 100
					# Apply maximum value limit if set
					if exemption_type.maximum_value and exempted_tax > exemption_type.maximum_value:
						exempted_tax = exemption_type.maximum_value
					exemption.exempted_tax = exempted_tax
				
				# Calculate exempted fees
				if self.other_charges:
					exempted_fee = (flt(self.other_charges) * exemption_percentage) / 100
					# Apply maximum value limit if set
					if exemption_type.maximum_value and exempted_fee > exemption_type.maximum_value:
						exempted_fee = exemption_type.maximum_value
					exemption.exempted_fee = exempted_fee
			
			# Calculate total exempted
			exemption.total_exempted = (
				flt(exemption.exempted_duty or 0) +
				flt(exemption.exempted_tax or 0) +
				flt(exemption.exempted_fee or 0)
			)
	
	def get_total_exempted_amount(self) -> float:
		"""Get total exempted amount from all exemptions"""
		total = 0.0
		if self.exemptions:
			for exemption in self.exemptions:
				total += flt(exemption.total_exempted or 0)
		return total

	def _permit_exemption_submit_settings(self):
		"""Customs Settings (per company) for declaration submit checks; defaults match strict behaviour."""
		defaults = {
			"block_submit_if_required_permit_not_obtained": 1,
			"block_submit_if_permit_expired": 1,
			"permit_expiring_warn_days": 7,
			"block_submit_if_permit_expires_within_days": 0,
			"block_submit_if_exemption_cert_invalid": 1,
			"block_submit_if_exemption_cert_not_active": 1,
			"block_submit_if_exemption_cert_expired": 1,
		}
		if not getattr(self, "company", None):
			return frappe._dict(defaults)
		row = frappe.db.get_value(
			"Customs Settings",
			{"company": self.company},
			list(defaults.keys()),
			as_dict=True,
		)
		out = dict(defaults)
		if row:
			for k in defaults:
				val = row.get(k)
				if val is not None:
					out[k] = val
		out["permit_expiring_warn_days"] = max(0, cint(out.get("permit_expiring_warn_days", 7)))
		out["block_submit_if_permit_expires_within_days"] = max(0, cint(out.get("block_submit_if_permit_expires_within_days", 0)))
		for k in (
			"block_submit_if_required_permit_not_obtained",
			"block_submit_if_permit_expired",
			"block_submit_if_exemption_cert_invalid",
			"block_submit_if_exemption_cert_not_active",
			"block_submit_if_exemption_cert_expired",
		):
			out[k] = cint(out.get(k, 1))
		return frappe._dict(out)
	
	def validate_permits(self):
		"""Validate that all required permits are obtained before submission"""
		if not self.permit_requirements:
			return
		s = self._permit_exemption_submit_settings()
		if not s.block_submit_if_required_permit_not_obtained:
			return
		
		missing_permits = []
		for permit_req in self.permit_requirements:
			if permit_req.is_required and not permit_req.is_obtained:
				permit_type_name = permit_req.permit_type or permit_req.get("planned_permit_type") or "Unknown"
				missing_permits.append(permit_type_name)
		
		if missing_permits:
			frappe.throw(
				_("The following required permits are not yet obtained (not Approved/Renewed): {0}").format(", ".join(missing_permits)),
				title=_("Missing Permits")
			)

	def validate_permit_expiry(self):
		"""Warn or block submission if required permits are expired or expiring soon (avoid delays/penalties)."""
		if not self.permit_requirements:
			return
		from frappe.utils import getdate, today, date_diff

		s = self._permit_exemption_submit_settings()
		today_date = getdate(today())
		expired = []
		expiring_blocked = []
		expiring_soon = []
		block_days = s.block_submit_if_permit_expires_within_days
		warn_days = s.permit_expiring_warn_days

		for permit_req in self.permit_requirements:
			if not permit_req.is_obtained or not permit_req.expiry_date:
				continue
			exp_date = getdate(permit_req.expiry_date)
			ptn = permit_req.permit_type or permit_req.get("planned_permit_type") or "Unknown"
			days_left = date_diff(exp_date, today_date)
			if days_left < 0:
				if s.block_submit_if_permit_expired:
					expired.append((ptn, permit_req.expiry_date))
			elif block_days > 0 and days_left <= block_days:
				expiring_blocked.append((ptn, permit_req.expiry_date, days_left))
			elif warn_days > 0 and days_left <= warn_days:
				expiring_soon.append((ptn, permit_req.expiry_date, days_left))

		if expired:
			frappe.throw(
				_("The following permits have expired and may cause delays or penalties: {0}. Please renew before submission.").format(
					", ".join(f"{p[0]} (expired {p[1]})" for p in expired)
				),
				title=_("Expired Permits")
			)
		if expiring_blocked:
			frappe.throw(
				_("The following permits expire within the configured window and must be renewed before submission: {0}").format(
					", ".join(f"{p[0]} (expires {p[1]}, in {p[2]} day(s))" for p in expiring_blocked)
				),
				title=_("Permits Expiring Soon"),
			)
		if expiring_soon:
			frappe.msgprint(
				_("The following permits expire within {0} day(s): {1}. Consider renewing to avoid clearance delays.").format(
					warn_days,
					", ".join(f"{p[0]} (expires {p[1]})" for p in expiring_soon),
				),
				title=_("Permits Expiring Soon"),
				indicator="orange",
			)

	def validate_exemption_certificates(self):
		"""Validate exemption certificates are active and not expired (avoid delays/penalties)."""
		if not self.exemptions:
			return
		s = self._permit_exemption_submit_settings()
		for exemption in self.exemptions:
			if not exemption.exemption_certificate:
				continue
			try:
				cert = frappe.get_doc("Exemption Certificate", exemption.exemption_certificate)
			except frappe.DoesNotExistError:
				if s.block_submit_if_exemption_cert_invalid:
					frappe.throw(
						_("Exemption Certificate {0} does not exist.").format(exemption.exemption_certificate),
						title=_("Invalid Exemption Certificate"),
					)
				continue
			if cert.status != "Active":
				if s.block_submit_if_exemption_cert_not_active:
					frappe.throw(
						_("Exemption Certificate {0} is not active (status: {1}). Using inactive certificates may cause delays or penalties.").format(
							cert.name, cert.status
						),
						title=_("Inactive Exemption Certificate"),
					)
				continue
			if cert.valid_to and getdate(cert.valid_to) < getdate(today()):
				if s.block_submit_if_exemption_cert_expired:
					frappe.throw(
						_("Exemption Certificate {0} has expired (valid to: {1}).").format(cert.name, cert.valid_to),
						title=_("Expired Exemption Certificate"),
					)

	def get_delay_penalty_alerts(self):
		"""Return list of alerts related to delays and penalties for dashboard display."""
		from frappe.utils import getdate, today, date_diff
		alerts = []
		today_date = getdate(today())
		s = self._permit_exemption_submit_settings()
		warn_days = s.permit_expiring_warn_days
		block_within = s.block_submit_if_permit_expires_within_days

		# 1. Pending required permits (virtual permit fields use properties; avoid pr.get for those)
		for pr in (self.get("permit_requirements") or []):
			is_req = pr.get("is_required")
			is_obt = getattr(pr, "is_obtained", None)
			ptype = getattr(pr, "permit_type", None) or pr.get("planned_permit_type")
			expiry = getattr(pr, "expiry_date", None)
			if is_req and not is_obt:
				if s.block_submit_if_required_permit_not_obtained:
					alerts.append(
						{
							"level": "danger",
							"msg": _("Required permit {0} is not obtained (not Approved/Renewed). Submission will be blocked.").format(ptype or "—"),
						}
					)
				else:
					alerts.append(
						{
							"level": "warning",
							"msg": _("Required permit {0} is not obtained; Customs Settings allow submission anyway.").format(ptype or "—"),
						}
					)
			elif is_obt and expiry:
				exp = getdate(expiry)
				days_left = date_diff(exp, today_date)
				if days_left < 0:
					if s.block_submit_if_permit_expired:
						alerts.append(
							{
								"level": "danger",
								"msg": _("Permit {0} expired on {1}. Submission will be blocked.").format(ptype or "—", expiry),
							}
						)
					else:
						alerts.append(
							{
								"level": "warning",
								"msg": _("Permit {0} expired on {1}; Customs Settings allow submission.").format(ptype or "—", expiry),
							}
						)
				elif block_within > 0 and days_left <= block_within:
					alerts.append(
						{
							"level": "danger",
							"msg": _("Permit {0} expires on {1} (within {2} day(s)). Submission will be blocked.").format(
								ptype or "—", expiry, block_within
							),
						}
					)
				elif warn_days > 0 and days_left <= warn_days:
					alerts.append(
						{
							"level": "warning",
							"msg": _("Permit {0} expires on {1}. Renew soon to avoid clearance delays.").format(ptype or "—", expiry),
						}
					)

		# 2. Exemption certificates expiring or inactive
		for ex in (self.get("exemptions") or []):
			if not ex.get("exemption_certificate"):
				continue
			try:
				cert = frappe.get_doc("Exemption Certificate", ex.exemption_certificate)
				if cert.status != "Active":
					if s.block_submit_if_exemption_cert_not_active:
						alerts.append(
							{
								"level": "danger",
								"msg": _("Exemption certificate {0} is not active. Submission will be blocked.").format(cert.name),
							}
						)
					else:
						alerts.append(
							{
								"level": "warning",
								"msg": _("Exemption certificate {0} is not active; Customs Settings allow submission.").format(cert.name),
							}
						)
				elif cert.valid_to:
					exp = getdate(cert.valid_to)
					dleft = date_diff(exp, today_date)
					if exp < today_date:
						if s.block_submit_if_exemption_cert_expired:
							alerts.append(
								{
									"level": "danger",
									"msg": _("Exemption certificate {0} expired on {1}. Submission will be blocked.").format(cert.name, cert.valid_to),
								}
							)
						else:
							alerts.append(
								{
									"level": "warning",
									"msg": _("Exemption certificate {0} expired on {1}; Customs Settings allow submission.").format(cert.name, cert.valid_to),
								}
							)
					elif warn_days > 0 and dleft <= warn_days:
						alerts.append(
							{
								"level": "warning",
								"msg": _("Exemption certificate {0} expires on {1}.").format(cert.name, cert.valid_to),
							}
						)
			except frappe.DoesNotExistError:
				if s.block_submit_if_exemption_cert_invalid:
					alerts.append(
						{
							"level": "danger",
							"msg": _("Exemption certificate link is invalid. Submission will be blocked."),
						}
					)
				else:
					alerts.append(
						{
							"level": "warning",
							"msg": _("Exemption certificate link is invalid; Customs Settings allow submission."),
						}
					)

		# 3. Expected clearance date passed but not released
		expected = getattr(self, "expected_clearance_date", None)
		if expected and self.status not in ("Cleared", "Released", "Cancelled", "Rejected"):
			exp_dt = getdate(expected)
			if exp_dt < today_date:
				days = date_diff(today_date, exp_dt)
				alerts.append({"level": "warning", "msg": _("Expected clearance date ({0}) passed {1} day(s) ago. Follow up with customs.").format(expected, days)})

		# 4. Overdue required documents
		for doc in (self.get("documents") or []):
			if not doc.get("is_required"):
				continue
			status = (doc.get("status") or "").strip()
			if status in ("Received", "Verified", "Done"):
				continue
			date_req = doc.get("date_required")
			if date_req:
				dr = getdate(date_req)
				if dr < today_date:
					alerts.append({"level": "warning", "msg": _("Document {0} was required on {1} and is overdue.").format(doc.get("document_type") or "—", date_req)})

		# 5. Documents expiring within 7 days
		for doc in (self.get("documents") or []):
			exp_date = doc.get("expiry_date")
			if not exp_date:
				continue
			exp = getdate(exp_date)
			if exp >= today_date and date_diff(exp, today_date) <= 7:
				alerts.append({"level": "info", "msg": _("Document {0} expires on {1}.").format(doc.get("document_type") or "—", exp_date)})

		# 6. Under Review - follow up reminder
		if self.status == "Under Review":
			alerts.append({"level": "info", "msg": _("Under review. Follow up with customs to avoid prolonged delays.")})

		return alerts
	
	def calculate_declaration_value(self):
		"""Calculate total declaration value from commercial invoice line items or inv_total_amount"""
		if flt(self.inv_total_amount):
			self.declaration_value = self.inv_total_amount
		else:
			total_value = 0
			if self.commercial_invoice_line_items:
				for row in self.commercial_invoice_line_items:
					qty = flt(row.invoice_qty or row.customs_qty or 1)
					price = flt(row.price or 0)
					total_value += qty * price
			self.declaration_value = total_value

	def update_payment_status(self):
		"""Auto-set payment status from invoice total, payment amount, and payment due date."""
		total_amount = flt(self.inv_total_amount or 0)
		paid_amount = flt(self.payment_amount or 0)
		due_date = getdate(self.payment_date) if self.payment_date else None
		today_date = getdate(today())

		# Fully settled takes priority regardless of due date.
		if total_amount > 0 and paid_amount >= total_amount:
			self.payment_status = "Paid"
			return

		# Partial settlement when some amount is paid but not full.
		if paid_amount > 0 and (total_amount <= 0 or paid_amount < total_amount):
			self.payment_status = "Partially Paid"
			return

		# Unpaid and due date has passed.
		if (paid_amount <= 0) and due_date and due_date < today_date:
			self.payment_status = "Overdue"
			return

		# Default for unpaid invoices not yet due or with no due date.
		self.payment_status = "Pending"
	
	def update_processing_dates(self):
		"""Update processing dates based on status"""
		from frappe.utils import now, nowdate, get_datetime
		
		if self.status == "Submitted" and not self.submission_date:
			self.submission_date = nowdate()
			if not self.submission_time:
				self.submission_time = get_datetime(now()).strftime("%H:%M:%S")
		elif self.status in ("Cleared", "Released") and not self.approval_date:
			self.approval_date = nowdate()
		elif self.status == "Rejected" and not self.rejection_date:
			self.rejection_date = nowdate()
	
	def handle_status_changes(self):
		"""Validate status transitions and enforce customs workflow rules."""
		if self.is_new():
			return
		old_status = frappe.db.get_value(self.doctype, self.name, "status")
		new_status = self.status
		if old_status == new_status:
			return
		# Customs declaration workflow: Draft -> Submitted -> Under Review -> Cleared -> Released
		allowed_transitions = {
			"Draft": ["Submitted", "Under Review", "Cancelled"],
			"Submitted": ["Under Review", "Cleared", "Released", "Rejected", "Cancelled"],
			"Under Review": ["Submitted", "Cleared", "Rejected", "Cancelled"],
			"Cleared": ["Released", "Cancelled"],
			"Released": ["Cancelled"],
			"Rejected": ["Draft", "Submitted", "Cancelled"],
			"Cancelled": [],
		}
		if old_status and new_status not in allowed_transitions.get(old_status, []):
			frappe.throw(
				_("Cannot change status from {0} to {1}").format(old_status, new_status),
				title=_("Invalid Status Transition"),
			)
	
	def calculate_sustainability_metrics(self):
		"""Calculate sustainability metrics for this declaration"""
		try:
			# For customs declarations, we can track compliance-related sustainability metrics
			# This could include paper usage, digital processing efficiency, etc.
			
			# Calculate estimated paper usage (simplified)
			paper_usage = self._calculate_paper_usage()
			self.estimated_paper_usage = paper_usage
			
			# Calculate estimated carbon footprint from processing
			carbon_footprint = self._calculate_processing_carbon_footprint()
			self.estimated_carbon_footprint = carbon_footprint
			
		except Exception as e:
			frappe.log_error(f"Error calculating sustainability metrics for Declaration {self.name}: {e}", "Declaration Sustainability Error")
	
	@frappe.whitelist()
	def get_dashboard_html(self):
		"""Generate HTML for Dashboard tab: tabbed layout with route, milestones, alerts."""
		try:
			from logistics.document_management.logistics_form_dashboard import (
				build_declaration_dashboard_config,
				render_logistics_form_dashboard_html,
			)

			return render_logistics_form_dashboard_html(
				self, build_declaration_dashboard_config(self)
			)
		except Exception as e:
			frappe.log_error(f"Declaration get_dashboard_html: {str(e)}", "Declaration Dashboard")
			return "<div class='alert alert-warning'>Error loading dashboard.</div>"

	@frappe.whitelist()
	def get_milestone_html(self):
		"""Generate HTML for milestone visualization in Milestones tab."""
		try:
			from logistics.document_management.api import get_milestone_display_rows_and_editor_doctype
			from logistics.document_management.milestone_html import build_milestone_html

			origin_name = getattr(self, "port_of_loading", None) or "Port of Loading"
			destination_name = getattr(self, "port_of_discharge", None) or "Port of Discharge"

			milestones, editor_child_dt = get_milestone_display_rows_and_editor_doctype(self)

			detail_items = [
				("Status", self.status or ""),
				("Declaration Type", getattr(self, "declaration_type", None) or ""),
				("Submission Date", str(self.submission_date) if getattr(self, "submission_date", None) else ""),
				("Approval Date", str(self.approval_date) if getattr(self, "approval_date", None) else ""),
				("Actual Clearance", str(self.actual_clearance_date) if getattr(self, "actual_clearance_date", None) else ""),
			]
			detail_items = [(l, v) for l, v in detail_items if v]

			def format_dt(dt):
				return frappe.utils.format_datetime(dt) if dt else None

			return build_milestone_html(
				doctype="Declaration",
				docname=self.name or "new",
				origin_name=origin_name,
				destination_name=destination_name,
				detail_items=detail_items,
				milestones=milestones,
				format_datetime_fn=format_dt,
				child_milestone_doctype=editor_child_dt,
				origin_party_name=getattr(self, "exporter_shipper", None) or "",
				destination_party_name=getattr(self, "importer_consignee", None) or "",
			)
		except Exception as e:
			frappe.log_error(f"Error in get_milestone_html: {str(e)}", "Declaration - Milestone HTML")
			return "<div class='alert alert-danger'>Error loading milestone view. Please check the error log.</div>"

	@frappe.whitelist()
	def get_permit_application_create_context(self):
		from logistics.customs.declaration_permit_exemption_create import get_permit_application_create_context

		return get_permit_application_create_context(self)

	@frappe.whitelist()
	def create_linked_permit_application(self, permit_type, child_row_name=None):
		from logistics.customs.declaration_permit_exemption_create import create_linked_permit_application

		return create_linked_permit_application(self, permit_type, child_row_name)

	@frappe.whitelist()
	def get_exemption_certificate_create_context(self):
		from logistics.customs.declaration_permit_exemption_create import get_exemption_certificate_create_context

		return get_exemption_certificate_create_context(self)

	@frappe.whitelist()
	def create_linked_exemption_certificate(self, exemption_type, certificate_number, child_row_name=None):
		from logistics.customs.declaration_permit_exemption_create import create_linked_exemption_certificate

		return create_linked_exemption_certificate(self, exemption_type, certificate_number, child_row_name)

	@frappe.whitelist()
	def recalculate_all_charges(self):
		"""Recalculate all declaration charges using each row's calculation routine."""
		if not hasattr(self, "charges") or not self.charges:
			return {"success": False, "message": _("No charges found to recalculate")}
		if self.docstatus == 1:
			frappe.throw(
				_("Cannot recalculate charges after submission. Please cancel/amend the document or use a Draft Declaration."),
				title=_("Cannot Update After Submit"),
			)
		try:
			charges_recalculated = 0
			for charge in self.charges:
				if hasattr(charge, "calculate_charge_amount"):
					charge.calculate_charge_amount(parent_doc=self)
					charges_recalculated += 1
			self.save()
			return {
				"success": True,
				"message": _("Successfully recalculated {0} charges").format(charges_recalculated),
				"charges_recalculated": charges_recalculated,
			}
		except Exception as e:
			try:
				frappe.log_error(
					title="Declaration - Recalculate Charges Error",
					message=frappe.get_traceback(),
				)
			except Exception:
				pass
			frappe.throw(_("Error recalculating charges: {0}").format(str(e)))

	@frappe.whitelist()
	def revert_charges_to_source(self):
		"""Revert charges to Declaration Order charges, else Sales Quote charges."""
		if self.docstatus == 1:
			frappe.throw(
				_("Cannot revert charges after submission. Please cancel/amend the document or use a Draft Declaration."),
				title=_("Cannot Update After Submit"),
			)
		if not self.declaration_order and not self.sales_quote:
			return {"success": False, "message": _("No source charges available to revert.")}
		try:
			self.set("charges", [])

			source = None
			if self.declaration_order and frappe.db.exists("Declaration Order", self.declaration_order):
				order = frappe.get_doc("Declaration Order", self.declaration_order)
				if hasattr(order, "charges") and order.charges:
					_populate_charges_from_declaration_order(self, order)
					source = "declaration_order"

			if not source and self.sales_quote and frappe.db.exists("Sales Quote", self.sales_quote):
				sq = frappe.get_doc("Sales Quote", self.sales_quote)
				_populate_charges_from_sales_quote(self, sq)
				source = "sales_quote"

			if not source:
				return {"success": False, "message": _("No source charges available to revert.")}

			self.save()
			return {
				"success": True,
				"source": source,
				"charges_count": len(self.get("charges") or []),
				"message": _("Charges reverted successfully."),
			}
		except Exception as e:
			try:
				frappe.log_error(
					title="Declaration - Revert Charges Error",
					message=frappe.get_traceback(),
				)
			except Exception:
				pass
			frappe.throw(_("Error reverting charges: {0}").format(str(e)))

	def record_sustainability_metrics(self):
		"""Record sustainability metrics in the centralized system"""
		try:
			from logistics.sustainability.utils.sustainability_integration import integrate_sustainability
			
			result = integrate_sustainability(
				doctype=self.doctype,
				docname=self.name,
				module="Customs",
				doc=self
			)
			
			if result.get("status") == "success":
				frappe.msgprint(_("Sustainability metrics recorded successfully"))
			elif result.get("status") == "skipped":
				# Don't show message if sustainability is not enabled
				pass
			else:
				frappe.log_error(f"Sustainability recording failed: {result.get('message', 'Unknown error')}", "Declaration Sustainability Error")
				
		except Exception as e:
			frappe.log_error(f"Error recording sustainability metrics for Declaration {self.name}: {e}", "Declaration Sustainability Error")
	
	def _calculate_paper_usage(self) -> float:
		"""Calculate estimated paper usage for customs declaration"""
		# Estimate based on typical customs declaration requirements
		# This is a simplified calculation
		base_pages = 5  # Base pages for standard declaration
		return float(base_pages)
	
	def _calculate_processing_carbon_footprint(self) -> float:
		"""Calculate estimated carbon footprint from processing"""
		# Estimate based on digital processing and office operations
		# This is a simplified calculation
		processing_factor = 0.1  # kg CO2e per declaration
		return processing_factor


# -------------------------------------------------------------------
# ACTION: Create Declaration from Declaration Order
# -------------------------------------------------------------------
@frappe.whitelist()
def create_declaration_from_declaration_order(declaration_order_name: str) -> Dict[str, Any]:
	"""
	Create a Declaration from a Declaration Order.
	Copies all information from the Declaration Order to the new Declaration.
	A Declaration Order can only be referenced by one Declaration.
	"""
	if not declaration_order_name:
		frappe.throw(_("Declaration Order name is required."))
	try:
		order = frappe.get_doc("Declaration Order", declaration_order_name)
		# Validate: Declaration Order can only be linked to one Declaration
		existing = frappe.db.get_value("Declaration", {"declaration_order": order.name, "docstatus": ["<", 2]}, "name")
		if existing:
			frappe.throw(
				_("Declaration Order {0} is already linked to Declaration {1}. A Declaration Order can only be referenced by one Declaration.").format(
					order.name, existing
				),
				title=_("Declaration Already Exists"),
			)
		if not order.sales_quote:
			frappe.throw(_("Declaration Order must have a Sales Quote to create a Declaration."))
		sq = frappe.get_doc("Sales Quote", order.sales_quote)
		from logistics.utils.internal_job_charge_copy import (
			build_internal_job_declaration_charge_dicts,
			should_apply_internal_job_main_charge_overlay,
		)

		has_customs_on_quote = (
			getattr(sq, "main_service", None) == "Customs"
			or any(c.get("service_type") == "Customs" for c in (getattr(sq, "charges") or []))
		)
		order_customs_charges = any(
			(getattr(c, "service_type", None) or "") == "Customs" for c in (order.charges or [])
		)
		internal_job_customs_ok = cint(getattr(order, "is_internal_job", 0)) and (
			order_customs_charges or should_apply_internal_job_main_charge_overlay(order)
		)
		if not has_customs_on_quote and not internal_job_customs_ok:
			frappe.throw(
				_("No customs details on the Sales Quote and no internal-job customs source on this Declaration Order.")
			)
		declaration = frappe.new_doc("Declaration")
		# Preserve user-pruned rows copied from Declaration Order during this creation flow.
		# Without this flag, on_update auto-population re-adds missing template rows.
		declaration.flags.ignore_documents_milestones_populate = True
		_copy_order_to_declaration(declaration, order, sq)
		if not declaration.customs_authority:
			frappe.throw(
				_(
					"Customs Authority is missing. Set it on Declaration Order {0}, on the linked Sales Quote (Customs charge or header), or as Default Customs Authority in Customs Settings for the company."
				).format(order.name),
				title=_("Missing Customs Authority"),
			)
		declaration.insert(ignore_permissions=True)
		# Reload document to get latest timestamp after insert
		declaration.reload()
		# Prefer charges from Declaration Order; else internal-job main service; else Sales Quote
		if hasattr(order, "charges") and order.charges:
			_populate_charges_from_declaration_order(declaration, order)
		elif cint(getattr(order, "is_internal_job", 0)) and should_apply_internal_job_main_charge_overlay(order):
			_append_declaration_charges_from_do_style_dicts(
				declaration, build_internal_job_declaration_charge_dicts(order)
			)
		else:
			_populate_charges_from_sales_quote(declaration, sq)
		# Keep suppression for the final save in this flow as well.
		declaration.flags.ignore_documents_milestones_populate = True
		declaration.save(ignore_permissions=True)
		frappe.db.commit()
		return {
			"success": True,
			"declaration": declaration.name,
			"message": _("Declaration {0} created successfully.").format(declaration.name),
		}
	except frappe.DoesNotExistError:
		frappe.throw(_("Declaration Order {0} does not exist.").format(declaration_order_name))
	except frappe.TimestampMismatchError:
		frappe.log_error("Timestamp mismatch when creating Declaration from Declaration Order", "Declaration Creation Error")
		frappe.throw(_("The declaration was modified during creation. Please try again."), title=_("Creation Error"))
	except Exception as e:
		frappe.log_error(f"Error creating Declaration from Declaration Order: {str(e)}", "Declaration Creation Error")
		# Provide user-friendly error message
		error_msg = str(e)
		if "TimestampMismatchError" in error_msg or "modified after you have opened it" in error_msg:
			frappe.throw(_("The declaration was modified during creation. Please try again."), title=_("Creation Error"))
		else:
			frappe.throw(_("Unable to create declaration. Please check the logs for details."), title=_("Creation Error"))


# -------------------------------------------------------------------
# ACTION: Create Declaration from Sales Quote
# -------------------------------------------------------------------
@frappe.whitelist()
def create_declaration_from_sales_quote(sales_quote_name: str) -> Dict[str, Any]:
	"""
	Create a Declaration from a Sales Quote when the quote has customs details.
	
	Args:
		sales_quote_name: Name of the Sales Quote
		
	Returns:
		dict: Result with created Declaration name and status
	"""
	try:
		sq = frappe.get_doc("Sales Quote", sales_quote_name)
		
		# Check if the quote is tagged as One-Off
		if getattr(sq, "quotation_type", None) != "One-off":
			frappe.throw(_("This Sales Quote is not tagged as One-Off. Only One-Off quotes can create Declarations."))
		
		# Check if Sales Quote has customs details (main_service or charges)
		has_customs = (
			getattr(sq, "main_service", None) == "Customs"
			or any(c.get("service_type") == "Customs" for c in (getattr(sq, "charges") or []))
		)
		if not has_customs:
			frappe.throw(_("No customs details found in this Sales Quote."))
		
		# Allow creation of multiple Declarations from the same Sales Quote
		# No duplicate prevention - users can create multiple declarations as needed
		
		# Create new Declaration
		declaration = frappe.new_doc("Declaration")
		
		# Map basic fields from Sales Quote to Declaration
		declaration.customer = sq.customer
		declaration.declaration_date = today()
		declaration.sales_quote = sq.name
		declaration.company = sq.company
		declaration.branch = getattr(sq, 'branch', None)
		declaration.cost_center = getattr(sq, 'cost_center', None)
		declaration.profit_center = getattr(sq, 'profit_center', None)
		
		# Set customs authority from first Customs charge or legacy header
		customs_charge = next((c for c in (getattr(sq, "charges") or []) if c.get("service_type") == "Customs"), None)
		if customs_charge and customs_charge.get("customs_authority"):
			declaration.customs_authority = customs_charge.customs_authority
		elif hasattr(sq, "customs_authority") and sq.customs_authority:
			declaration.customs_authority = sq.customs_authority
		
		# Set currency from quote
		if hasattr(sq, 'currency') and sq.currency:
			declaration.currency = sq.currency
		
		# Insert the Declaration
		declaration.insert(ignore_permissions=True)
		
		# Populate charges from Sales Quote Customs
		_populate_charges_from_sales_quote(declaration, sq)
		
		# Save the Declaration
		declaration.save(ignore_permissions=True)
		
		# Ensure commit before client navigates (avoids "not found" on form load)
		frappe.db.commit()
		
		return {
			"success": True,
			"declaration": declaration.name,
			"message": _("Declaration {0} created successfully.").format(declaration.name)
		}
		
	except frappe.DoesNotExistError:
		frappe.throw(_("Sales Quote {0} does not exist.").format(sales_quote_name))
	except Exception as e:
		frappe.log_error(f"Error creating Declaration from Sales Quote: {str(e)}", "Declaration Creation Error")
		frappe.throw(_("Error creating Declaration: {0}").format(str(e)))


# -------------------------------------------------------------------
# ACTION: Create or link Declaration Order from Declaration (Sales Quote)
# -------------------------------------------------------------------
@frappe.whitelist()
def link_or_create_declaration_order_for_declaration(declaration_name: str) -> Dict[str, Any]:
	"""
	If this Declaration has a Sales Quote but no Declaration Order, link an existing
	Declaration Order for that quote or create one (same rules as Sales Quote → Create Declaration Order).
	"""
	if not declaration_name:
		frappe.throw(_("Declaration name is required."))
	declaration = frappe.get_doc("Declaration", declaration_name)
	declaration.check_permission("write")
	if declaration.docstatus == 2:
		frappe.throw(_("Cannot modify a cancelled Declaration."))
	if declaration.declaration_order:
		frappe.throw(_("Declaration Order is already linked."), title=_("Already Linked"))
	if not declaration.sales_quote:
		frappe.throw(
			_(
				"Link a Sales Quote first. Declaration Order is created from a One-off Sales Quote with Customs charges."
			),
			title=_("Sales Quote Required"),
		)

	existing_do = frappe.db.get_value("Declaration Order", {"sales_quote": declaration.sales_quote}, "name")
	if existing_do:
		other = frappe.db.get_value(
			"Declaration",
			{
				"declaration_order": existing_do,
				"name": ["!=", declaration.name],
				"docstatus": ["<", 2],
			},
			"name",
		)
		if other:
			frappe.throw(
				_("Declaration Order {0} is already linked to Declaration {1}.").format(existing_do, other),
				title=_("Declaration Order In Use"),
			)
		declaration.declaration_order = existing_do
		declaration.save()
		return {
			"success": True,
			"declaration_order": existing_do,
			"created": False,
			"message": _("Linked Declaration Order {0} to this Declaration.").format(existing_do),
		}

	from logistics.customs.doctype.declaration_order.declaration_order import (
		create_declaration_order_from_sales_quote,
	)

	result = create_declaration_order_from_sales_quote(declaration.sales_quote)
	do_name = (result or {}).get("declaration_order")
	if not do_name:
		frappe.throw(_("Could not create Declaration Order."))

	declaration.reload()
	declaration.declaration_order = do_name
	declaration.save()
	return {
		"success": True,
		"declaration_order": do_name,
		"created": True,
		"message": (result or {}).get("message") or _("Declaration Order {0} created and linked.").format(do_name),
	}


def _copy_order_to_declaration(declaration: Document, order: Document, sales_quote: Document):
	"""Copy all information from Declaration Order to Declaration."""
	# Core references
	declaration.declaration_order = order.name
	declaration.sales_quote = order.sales_quote
	declaration.customer = order.customer
	od = getattr(order, "order_date", None)
	declaration.declaration_date = getdate(od) if od else today()
	declaration.customs_authority = order.customs_authority
	if not declaration.customs_authority and order.sales_quote:
		from logistics.customs.doctype.declaration_order.declaration_order import get_sales_quote_details

		sqd = get_sales_quote_details(order.sales_quote)
		if sqd.get("customs_authority"):
			declaration.customs_authority = sqd["customs_authority"]
	if not declaration.customs_authority:
		company = getattr(order, "company", None) or (
			getattr(sales_quote, "company", None) if sales_quote else None
		)
		if company:
			default_ca = frappe.db.get_value(
				"Customs Settings", {"company": company}, "default_customs_authority"
			)
			if default_ca:
				declaration.customs_authority = default_ca
	declaration.status = "Draft"
	declaration.is_main_service = cint(getattr(order, "is_main_service", 0))
	# Preserve internal-job classification context from the source order.
	declaration.is_internal_job = getattr(order, "is_internal_job", 0)
	declaration.main_job_type = getattr(order, "main_job_type", None)
	declaration.main_job = getattr(order, "main_job", None)

	# Main section
	declaration.currency = order.currency or (getattr(sales_quote, "currency", None) if sales_quote else None)
	declaration.exchange_rate = order.exchange_rate
	declaration.customs_broker = order.customs_broker
	declaration.notify_party = order.notify_party
	declaration.freight_agent = getattr(order, "freight_agent", None)

	# Shipment details
	declaration.exporter_shipper = order.exporter_shipper
	declaration.importer_consignee = order.importer_consignee
	declaration.declaration_type = order.declaration_type
	declaration.transport_mode = order.transport_mode

	# Transport information
	declaration.vessel_flight_number = order.vessel_flight_number
	declaration.transport_document_number = order.transport_document_number
	declaration.transport_document_type = order.transport_document_type
	declaration.container_numbers = order.container_numbers
	declaration.port_of_loading = order.port_of_loading
	declaration.port_of_discharge = order.port_of_discharge
	declaration.etd = order.etd
	declaration.eta = order.eta

	# Trade information
	declaration.incoterm = order.incoterm
	declaration.payment_terms = order.payment_terms
	declaration.trade_agreement = order.trade_agreement
	declaration.country_of_origin = order.country_of_origin
	declaration.country_of_destination = order.country_of_destination
	declaration.priority_level = order.priority_level

	# Additional information
	declaration.marks_and_numbers = order.marks_and_numbers
	declaration.special_instructions = order.special_instructions
	declaration.external_reference = order.external_reference

	# Commercial invoice header fields
	declaration.invoice_no = order.invoice_no
	declaration.exporter = getattr(order, "exporter", None)
	declaration.exporter_name = getattr(order, "exporter_name", None)
	declaration.inv_date = order.inv_date
	declaration.payment_date = order.payment_date
	declaration.inv_importer = order.inv_importer
	declaration.importer_name = getattr(order, "importer_name", None)
	declaration.agreed_place = order.agreed_place
	declaration.incoterm_place = order.incoterm_place
	declaration.inv_incoterm = order.inv_incoterm
	declaration.inv_total_amount = order.inv_total_amount
	declaration.inv_currency = order.inv_currency
	declaration.inv_exchange_rate = order.inv_exchange_rate
	declaration.balance = getattr(order, "balance", None)
	declaration.inv_volume = order.inv_volume
	declaration.inv_volume_uom = order.inv_volume_uom
	declaration.inv_gross_weight = order.inv_gross_weight
	declaration.inv_gross_weight_uom = order.inv_gross_weight_uom
	declaration.inv_net_weight = order.inv_net_weight
	declaration.inv_net_weight_uom = order.inv_net_weight_uom
	declaration.packages = order.packages
	declaration.packages_uom = order.packages_uom
	declaration.cif = order.cif
	declaration.fob = order.fob
	declaration.charges_excl_from_itot = order.charges_excl_from_itot
	declaration.expected_invoice_line_total = order.expected_invoice_line_total
	declaration.remarks = order.remarks
	declaration.exporters_bank_account_no = order.exporters_bank_account_no
	declaration.exporters_bank_name = order.exporters_bank_name
	declaration.exporters_bank_name_copy = getattr(order, "exporters_bank_name_copy", None)
	declaration.exporters_bank_swift_code = order.exporters_bank_swift_code
	declaration.letter_of_credit_number = order.letter_of_credit_number
	declaration.letter_of_credit_date = order.letter_of_credit_date
	declaration.lc_ex_rate = order.lc_ex_rate
	declaration.payment_number = order.payment_number
	declaration.payment_currency = getattr(order, "payment_currency", None)
	declaration.payment_amount = order.payment_amount
	declaration.payment_ex_rate = order.payment_ex_rate

	# Document template and milestone template
	declaration.document_list_template = getattr(order, "document_list_template", None)
	declaration.milestone_template = order.milestone_template

	# Service Level Agreement
	declaration.service_level = getattr(order, "service_level", None)
	declaration.sla_target_date = getattr(order, "sla_target_date", None)
	declaration.sla_status = getattr(order, "sla_status", None)
	declaration.sla_target_source = getattr(order, "sla_target_source", None)
	declaration.sla_notes = getattr(order, "sla_notes", None)

	# Accounts
	declaration.company = order.company
	declaration.branch = order.branch
	declaration.cost_center = order.cost_center
	declaration.profit_center = order.profit_center
	declaration.job_number = getattr(order, "job_number", None)
	declaration.project = order.project
	copy_operational_rep_fields_from_declaration_order(declaration, order)

	# Notes
	declaration.internal_notes = order.internal_notes
	declaration.external_notes = getattr(order, "external_notes", None)

	# Child tables: internal jobs (same child doctype on both)
	if order.get("internal_job_details"):
		declaration.set("internal_job_details", [])
		ij_meta = frappe.get_meta("Internal Job Detail")
		ij_fields = {
			f.fieldname
			for f in ij_meta.fields
			if f.fieldtype not in ("Section Break", "Column Break", "Tab Break")
		}
		for row in order.internal_job_details:
			child = declaration.append("internal_job_details", {})
			_copy_child_row(row, child, ij_fields)

	# Child tables: commercial invoice line items (same structure)
	if order.get("commercial_invoice_line_items"):
		declaration.set("commercial_invoice_line_items", [])
		line_meta = frappe.get_meta("Commercial Invoice Line Item")
		line_fields = {f.fieldname for f in line_meta.fields if f.fieldtype not in ("Section Break", "Column Break", "Tab Break")}
		for row in order.commercial_invoice_line_items:
			child = declaration.append("commercial_invoice_line_items", {})
			_copy_child_row(row, child, line_fields)

	# Child tables: commercial invoice charges (same structure)
	if order.get("commercial_invoice_charges"):
		declaration.set("commercial_invoice_charges", [])
		chg_meta = frappe.get_meta("Commercial Invoice Charges")
		chg_fields = {f.fieldname for f in chg_meta.fields if f.fieldtype not in ("Section Break", "Column Break", "Tab Break")}
		for row in order.commercial_invoice_charges:
			child = declaration.append("commercial_invoice_charges", {})
			_copy_child_row(row, child, chg_fields)

	# Child tables: permit requirements (Declaration Order Permit Requirement -> Permit Requirement, same fields)
	if order.get("permit_requirements"):
		declaration.set("permit_requirements", [])
		perm_meta = frappe.get_meta("Permit Requirement")
		perm_fields = {f.fieldname for f in perm_meta.fields if f.fieldtype not in ("Section Break", "Column Break", "Tab Break")}
		for row in order.permit_requirements:
			child = declaration.append("permit_requirements", {})
			_copy_child_row(row, child, perm_fields)

	# Child tables: exemptions (Declaration Order Exemption -> Declaration Exemption, same fields)
	if order.get("exemptions"):
		declaration.set("exemptions", [])
		exempt_meta = frappe.get_meta("Declaration Exemption")
		exempt_fields = {f.fieldname for f in exempt_meta.fields if f.fieldtype not in ("Section Break", "Column Break", "Tab Break")}
		for row in order.exemptions:
			child = declaration.append("exemptions", {})
			_copy_child_row(row, child, exempt_fields)

	# Child tables: milestones (Declaration Order Milestone -> Declaration Milestone, same fields)
	if order.get("milestones"):
		declaration.set("milestones", [])
		ms_meta = frappe.get_meta("Declaration Milestone")
		ms_fields = {f.fieldname for f in ms_meta.fields if f.fieldtype not in ("Section Break", "Column Break", "Tab Break")}
		for row in order.milestones:
			child = declaration.append("milestones", {})
			_copy_child_row(row, child, ms_fields)

	# Child tables: documents (Job Document - same structure for both)
	if order.get("documents"):
		declaration.set("documents", [])
		doc_meta = frappe.get_meta("Job Document")
		doc_fields = {f.fieldname for f in doc_meta.fields if f.fieldtype not in ("Section Break", "Column Break", "Tab Break")}
		for row in order.documents:
			child = declaration.append("documents", {})
			_copy_child_row(row, child, doc_fields)


def _copy_child_row(source_row: Document, target_row: Document, valid_fields: set, child_meta=None):
	"""Copy fields from source child row to target child row (skip virtual fields on the target row)."""
	meta = child_meta or frappe.get_meta(target_row.doctype)
	for field in valid_fields:
		df = meta.get_field(field)
		if df and getattr(df, "is_virtual", False):
			continue
		if hasattr(source_row, field):
			val = getattr(source_row, field, None)
			if val is not None and field not in ("name", "owner", "creation", "modified", "modified_by", "parent", "parenttype", "parentfield", "idx"):
				target_row.set(field, val)


def _append_declaration_charges_from_do_style_dicts(declaration: Document, charge_dicts: list) -> None:
	"""Append Declaration Charges rows from Declaration Order–shaped charge dicts (e.g. internal-job main service)."""
	if not charge_dicts:
		return
	target_meta = frappe.get_meta("Declaration Charges")
	target_fields = {f.fieldname for f in target_meta.fields}
	field_name_map = {"description": "charge_description"}
	direct_fields = [
		"service_type",
		"item_code",
		"item_name",
		"charge_type",
		"charge_category",
		"revenue_calculation_method",
		"quantity",
		"uom",
		"currency",
		"rate",
		"unit_type",
		"minimum_quantity",
		"minimum_unit_rate",
		"minimum_charge",
		"maximum_charge",
		"base_amount",
		"base_quantity",
		"estimated_revenue",
		"cost_calculation_method",
		"cost_quantity",
		"cost_uom",
		"cost_currency",
		"unit_cost",
		"cost_unit_type",
		"cost_minimum_quantity",
		"cost_minimum_unit_rate",
		"cost_minimum_charge",
		"cost_maximum_charge",
		"cost_base_amount",
		"cost_base_quantity",
		"estimated_cost",
		"revenue_calc_notes",
		"cost_calc_notes",
		"use_tariff_in_revenue",
		"use_tariff_in_cost",
		"revenue_tariff",
		"cost_tariff",
		"bill_to",
		"pay_to",
		"is_other_service",
		"other_service_type",
		"date_started",
		"date_ended",
		"other_service_reference_no",
		"other_service_notes",
		"sales_quote_link",
		"charge_basis",
	]
	for src in charge_dicts:
		charge_row = declaration.append("charges", {})
		for field in direct_fields:
			if field not in target_fields:
				continue
			val = src.get(field)
			if val is not None:
				charge_row.set(field, val)
		for src_fn, dst_fn in field_name_map.items():
			val = src.get(src_fn)
			if val is not None and dst_fn in target_fields:
				charge_row.set(dst_fn, val)


def _populate_charges_from_declaration_order(declaration: Document, order: Document):
	"""Populate charges from Declaration Order charges (same structure as Declaration Charges)."""
	try:
		if not hasattr(order, "charges") or not order.charges:
			return
		# Target meta to validate available fields
		target_meta = frappe.get_meta("Declaration Charges")
		target_fields = {f.fieldname for f in target_meta.fields}

		# 1) Direct one-to-one fields present on both doctypes
		direct_fields = [
			"service_type",
			"item_code",
			"item_name",
			"charge_type",
			"charge_category",
			"revenue_calculation_method",
			"quantity",
			"uom",
			"currency",
			"rate",
			"unit_type",
			"minimum_quantity",
			"minimum_unit_rate",
			"minimum_charge",
			"maximum_charge",
			"base_amount",
			"base_quantity",
			"estimated_revenue",
			"cost_calculation_method",
			"cost_quantity",
			"cost_uom",
			"cost_currency",
			"unit_cost",
			"cost_unit_type",
			"cost_minimum_quantity",
			"cost_minimum_unit_rate",
			"cost_minimum_charge",
			"cost_maximum_charge",
			"cost_base_amount",
			"cost_base_quantity",
			"estimated_cost",
			"revenue_calc_notes",
			"cost_calc_notes",
			"use_tariff_in_revenue",
			"use_tariff_in_cost",
			"revenue_tariff",
			"cost_tariff",
			"bill_to",
			"pay_to",
			# Other services block
			"is_other_service",
			"other_service_type",
			"date_started",
			"date_ended",
			"other_service_reference_no",
			"other_service_notes",
			# Link back to quote if present on row
			"sales_quote_link",
		]

		# 2) Field name mappings where source and target differ
		# Declaration Order Charges -> Declaration Charges
		field_name_map = {
			"description": "charge_description",
		}

		for order_charge in order.charges:
			charge_row = declaration.append("charges", {})
			# Copy direct fields that exist on target
			for field in direct_fields:
				if field in target_fields and hasattr(order_charge, field):
					val = getattr(order_charge, field, None)
					if val is not None:
						charge_row.set(field, val)
			# Copy mapped fields
			for src, dst in field_name_map.items():
				if dst in target_fields and hasattr(order_charge, src):
					val = getattr(order_charge, src, None)
					if val is not None:
						charge_row.set(dst, val)
	except Exception as e:
		frappe.log_error(f"Error populating charges from Declaration Order: {str(e)}")


def _populate_charges_from_sales_quote(declaration: Document, sales_quote: Document):
	"""Populate charges from Sales Quote Charge (Customs) or Sales Quote Customs (legacy)."""
	try:
		customs_charges = customs_charges_rows_from_sales_quote_doc(declaration, sales_quote)
		if not customs_charges and hasattr(sales_quote, "customs") and sales_quote.customs:
			customs_charges = list(sales_quote.customs)
		if not customs_charges:
			return
		
		# Get Declaration Charges meta to check available fields
		declaration_charges_meta = frappe.get_meta("Declaration Charges")
		declaration_charges_fields = [f.fieldname for f in declaration_charges_meta.fields]
		
		# Copy charges
		for sq_charge in customs_charges:
			charge_row = declaration.append('charges', {})
			
			# Map common fields
			common_fields = [
				'service_type', 'item_code', 'item_name', 'calculation_method', 'quantity', 'uom',
				'currency', 'unit_rate', 'unit_type', 'minimum_quantity', 'minimum_charge',
				'maximum_charge', 'base_amount', 'estimated_revenue', 'cost_calculation_method',
				'cost_quantity', 'cost_uom', 'cost_currency', 'unit_cost', 'cost_unit_type',
				'cost_minimum_quantity', 'cost_minimum_charge', 'cost_maximum_charge',
				'cost_base_amount', 'estimated_cost', 'revenue_calc_notes', 'cost_calc_notes',
				'use_tariff_in_revenue', 'use_tariff_in_cost', 'tariff',
				'revenue_tariff', 'cost_tariff', 'bill_to', 'pay_to'
			]
			
			for field in common_fields:
				if field in declaration_charges_fields and hasattr(sq_charge, field):
					value = getattr(sq_charge, field, None)
					if value is not None:
						charge_row.set(field, value)
		
	except Exception as e:
		frappe.log_error(f"Error populating charges from Sales Quote: {str(e)}", "Declaration Charges Error")


# -------------------------------------------------------------------
# ACTION: Create Sales Invoice from Declaration
# -------------------------------------------------------------------
@frappe.whitelist()
def create_sales_invoice(declaration_name: str) -> Dict[str, Any]:
	"""
	Create a Sales Invoice from a Declaration (draft or submitted; not cancelled).
	Uses charges from Declaration level.
	"""
	if not declaration_name:
		frappe.throw(_("Declaration name is required."))
	
	declaration = frappe.get_doc("Declaration", declaration_name)
	if declaration.docstatus == 2:
		frappe.throw(_("Cannot create Sales Invoice from a cancelled Declaration."))
	
	# Check if Sales Invoice already exists for this declaration
	existing_invoice = frappe.db.get_value("Sales Invoice", {"job_number": declaration.job_number}, "name")
	if existing_invoice and declaration.job_number:
		frappe.throw(_("Sales Invoice {0} already exists for this Declaration.").format(existing_invoice))
	
	# Create Sales Invoice
	si = frappe.new_doc("Sales Invoice")
	si.customer = declaration.customer
	si.company = declaration.company
	si.posting_date = today()
	
	# Add accounting fields from Declaration
	if declaration.branch:
		si.branch = declaration.branch
	if declaration.cost_center:
		si.cost_center = declaration.cost_center
	if declaration.profit_center:
		si.profit_center = declaration.profit_center
	
	# Add reference to Job Number if it exists
	if declaration.job_number:
		si.job_number = declaration.job_number
	
	# Add reference to Sales Quote if it exists
	if declaration.sales_quote:
		si.quotation_no = declaration.sales_quote
	
	# Add reference in remarks
	base_remarks = si.remarks or ""
	note = _("Auto-created from Declaration {0}").format(declaration.name)
	si.remarks = f"{base_remarks}\n{note}" if base_remarks else note
	
	# Use charges from Declaration
	charges = declaration.get("charges") or []
	si_item_fields = _safe_meta_fieldnames("Sales Invoice Item")
	
	if charges:
		# Create items from charges
		for charge in charges:
			if not charge.item_code:
				continue
			
			item = si.append('items', {})
			item.item_code = charge.item_code
			item.qty = charge.quantity or 1
			item.rate = charge.estimated_revenue or charge.unit_rate or 0
			
			# Set description
			if charge.item_name:
				item.item_name = charge.item_name
			
			# Set UOM if available
			if charge.uom:
				item.uom = charge.uom
			
			# Set cost center and profit center
			if declaration.cost_center:
				item.cost_center = declaration.cost_center
			if declaration.profit_center:
				item.profit_center = declaration.profit_center
			# Link to declaration for Recognition Engine and lifecycle tracking
			si_item_meta = frappe.get_meta("Sales Invoice Item")
			if si_item_meta.get_field("reference_doctype") and si_item_meta.get_field("reference_name"):
				item.reference_doctype = "Declaration"
				item.reference_name = declaration.name
	
	# If no charges, create a default item
	if not charges:
		item = si.append('items', {})
		item.item_code = _get_default_customs_item()
		item.qty = 1
		item.rate = declaration.declaration_value or 0
		if declaration.cost_center:
			item.cost_center = declaration.cost_center
		if declaration.profit_center:
			item.profit_center = declaration.profit_center
		si_item_meta = frappe.get_meta("Sales Invoice Item")
		if si_item_meta.get_field("reference_doctype") and si_item_meta.get_field("reference_name"):
			item.reference_doctype = "Declaration"
			item.reference_name = declaration.name
	
	# Insert and save
	si.insert(ignore_permissions=True)
	si.save(ignore_permissions=True)
	
	# Update Declaration with Sales Invoice reference and lifecycle
	decl_meta = frappe.get_meta("Declaration")
	for field in ("sales_invoice", "date_sales_invoice_requested"):
		if decl_meta.get_field(field):
			frappe.db.set_value(
				"Declaration",
				declaration.name,
				field,
				si.name if field == "sales_invoice" else frappe.utils.today(),
				update_modified=False,
			)
	
	return {
		"success": True,
		"sales_invoice": si.name,
		"message": _("Sales Invoice {0} created successfully.").format(si.name)
	}


@frappe.whitelist()
def post_standard_costs(docname):
	"""Post standard costs for Declaration charges. No-op if charges do not support standard costs."""
	declaration = frappe.get_doc("Declaration", docname)
	posted = 0
	for ch in (declaration.charges or []):
		if getattr(ch, "total_standard_cost", None) and flt(ch.total_standard_cost) > 0 and not getattr(ch, "standard_cost_posted", False):
			if frappe.get_meta(ch.doctype).get_field("standard_cost_posted"):
				ch.standard_cost_posted = 1
				ch.standard_cost_posted_at = frappe.utils.now()
				posted += 1
	if posted > 0:
		declaration.save()
	return {"message": _("Posted {0} standard cost(s).").format(posted) if posted else _("No standard costs to post.")}


def _safe_meta_fieldnames(doctype: str) -> list:
	"""Get safe list of fieldnames from doctype meta"""
	try:
		meta = frappe.get_meta(doctype)
		return [f.fieldname for f in meta.fields]
	except Exception:
		return []


def _get_default_customs_item() -> str:
	"""Get default customs item code"""
	# Try to get from settings or use a default
	default_item = frappe.db.get_single_value("Logistics Settings", "default_customs_item")
	if default_item:
		return default_item
	
	# Try to find any item with customs flag
	customs_item = frappe.db.get_value("Item", {"custom_customs_charge": 1}, "name")
	if customs_item:
		return customs_item
	
	# Return a generic item code (this should be configured)
	return "CUSTOMS SERVICE"
