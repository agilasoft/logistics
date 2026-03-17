# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import today, getdate, flt
from typing import Dict, Any, Optional


class Declaration(Document):
	def validate(self):
		self._validate_declaration_order_unique()
		try:
			from logistics.utils.measurements import apply_measurement_uom_conversion_to_children
			apply_measurement_uom_conversion_to_children(self, "commercial_invoice_line_items", company=getattr(self, "company", None))
		except Exception:
			pass

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
		run_propagate_on_link(self)
		self.calculate_total_payable()
		self.calculate_declaration_value()
		self.calculate_exemptions()
		self.calculate_sustainability_metrics()
		self.update_processing_dates()
	
	def on_update(self):
		"""Handle status changes"""
		self.handle_status_changes()
	
	def before_submit(self):
		"""Validate before submission"""
		self.validate_permits()
		self.validate_permit_expiry()
		self.validate_exemption_certificates()
		# Auto-set status to Submitted when submitting from Draft
		if self.status == "Draft":
			self.status = "Submitted"
	
	def after_submit(self):
		"""Record sustainability metrics after declaration submission"""
		self.record_sustainability_metrics()
	
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
			
			# Get exemption type details
			if exemption.exemption_type:
				try:
					exemption_type = frappe.get_doc("Exemption Type", exemption.exemption_type)
				except frappe.DoesNotExistError:
					continue
			
			# Calculate exempted amounts based on exemption type
			if exemption_type:
				exemption_percentage = flt(exemption.exemption_percentage or exemption_type.exemption_percentage or 0)
				
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
	
	def validate_permits(self):
		"""Validate that all required permits are obtained before submission"""
		if not self.permit_requirements:
			return
		
		missing_permits = []
		for permit_req in self.permit_requirements:
			if permit_req.is_required and not permit_req.is_obtained:
				permit_type_name = permit_req.permit_type or "Unknown"
				missing_permits.append(permit_type_name)
		
		if missing_permits:
			frappe.throw(
				_("The following required permits are not yet obtained: {0}").format(", ".join(missing_permits)),
				title=_("Missing Permits")
			)

	def validate_permit_expiry(self):
		"""Warn or block submission if required permits are expired or expiring soon (avoid delays/penalties)."""
		if not self.permit_requirements:
			return
		from frappe.utils import getdate, today, date_diff
		today_date = getdate(today())
		expired = []
		expiring_soon = []
		for permit_req in self.permit_requirements:
			if not permit_req.is_obtained or not permit_req.expiry_date:
				continue
			exp_date = getdate(permit_req.expiry_date)
			if exp_date < today_date:
				expired.append((permit_req.permit_type or "Unknown", permit_req.expiry_date))
			elif date_diff(exp_date, today_date) <= 7:
				expiring_soon.append((permit_req.permit_type or "Unknown", permit_req.expiry_date))
		if expired:
			frappe.throw(
				_("The following permits have expired and may cause delays or penalties: {0}. Please renew before submission.").format(
					", ".join(f"{p[0]} (expired {p[1]})" for p in expired)
				),
				title=_("Expired Permits")
			)
		if expiring_soon:
			frappe.msgprint(
				_("The following permits expire within 7 days: {0}. Consider renewing to avoid clearance delays.").format(
					", ".join(f"{p[0]} (expires {p[1]})" for p in expiring_soon)
				),
				title=_("Permits Expiring Soon"),
				indicator="orange",
			)

	def validate_exemption_certificates(self):
		"""Validate exemption certificates are active and not expired (avoid delays/penalties)."""
		if not self.exemptions:
			return
		for exemption in self.exemptions:
			if not exemption.exemption_certificate:
				continue
			try:
				cert = frappe.get_doc("Exemption Certificate", exemption.exemption_certificate)
			except frappe.DoesNotExistError:
				frappe.throw(
					_("Exemption Certificate {0} does not exist.").format(exemption.exemption_certificate),
					title=_("Invalid Exemption Certificate"),
				)
			if cert.status != "Active":
				frappe.throw(
					_("Exemption Certificate {0} is not active (status: {1}). Using inactive certificates may cause delays or penalties.").format(
						cert.name, cert.status
					),
					title=_("Inactive Exemption Certificate"),
				)
			if cert.valid_to and getdate(cert.valid_to) < getdate(today()):
				frappe.throw(
					_("Exemption Certificate {0} has expired (valid to: {1}).").format(cert.name, cert.valid_to),
					title=_("Expired Exemption Certificate"),
				)

	def get_delay_penalty_alerts(self):
		"""Return list of alerts related to delays and penalties for dashboard display."""
		from frappe.utils import getdate, today, date_diff
		alerts = []
		today_date = getdate(today())

		# 1. Pending required permits
		for pr in (self.get("permit_requirements") or []):
			if pr.get("is_required") and not pr.get("is_obtained"):
				alerts.append({"level": "danger", "msg": _("Required permit {0} not yet obtained. Submission will be blocked.").format(pr.get("permit_type") or "—")})
			elif pr.get("is_obtained") and pr.get("expiry_date"):
				exp = getdate(pr.expiry_date)
				if exp < today_date:
					alerts.append({"level": "danger", "msg": _("Permit {0} expired on {1}. Renew to avoid penalties.").format(pr.get("permit_type") or "—", pr.expiry_date)})
				elif date_diff(exp, today_date) <= 7:
					alerts.append({"level": "warning", "msg": _("Permit {0} expires on {1}. Renew soon to avoid clearance delays.").format(pr.get("permit_type") or "—", pr.expiry_date)})

		# 2. Exemption certificates expiring or inactive
		for ex in (self.get("exemptions") or []):
			if not ex.get("exemption_certificate"):
				continue
			try:
				cert = frappe.get_doc("Exemption Certificate", ex.exemption_certificate)
				if cert.status != "Active":
					alerts.append({"level": "warning", "msg": _("Exemption certificate {0} is not active.").format(cert.name)})
				elif cert.valid_to:
					exp = getdate(cert.valid_to)
					if exp < today_date:
						alerts.append({"level": "danger", "msg": _("Exemption certificate {0} expired on {1}.").format(cert.name, cert.valid_to)})
					elif date_diff(exp, today_date) <= 14:
						alerts.append({"level": "warning", "msg": _("Exemption certificate {0} expires on {1}.").format(cert.name, cert.valid_to)})
			except frappe.DoesNotExistError:
				pass

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
		"""Generate HTML for Dashboard tab: declaration details (Air Shipment header format), milestones (from Milestones tab), Documents Management (from Air Shipment)."""
		try:
			from logistics.document_management.api import get_document_alerts_html, get_milestone_html
			from logistics.document_management.dashboard_layout import build_run_sheet_style_dashboard

			# Section 1: Declaration details (Air Shipment header format) with Exporter | Importer
			status = "Cancelled" if self.docstatus == 2 else (self.status or "Draft")
			# Status badge for dashboard (prominent display)
			status_class = (status or "draft").lower().replace(" ", "_").replace(" ", "_")
			status_badge_html = f'<span class="dash-status-badge {status_class}">{frappe.utils.escape_html(status)}</span>'
			# Format value with correct currency code from commercial invoice
			currency = self.inv_currency or frappe.db.get_default("currency") or "PHP"
			# Format number and append currency code instead of using symbol
			amount = flt(self.declaration_value or 0)
			value_display = f"{frappe.utils.fmt_money(amount, precision=2)} {currency}"
			
			header_items = [
				("Status", status),
				("Declaration #", self.declaration_number or "—"),
				("Type", self.declaration_type or "—"),
				("Date", str(self.declaration_date) if self.declaration_date else "—"),
				("Port of Loading", self.port_of_loading or "—"),
				("Port of Discharge", self.port_of_discharge or "—"),
				("ETD", str(self.etd) if self.etd else "—"),
				("ETA", str(self.eta) if self.eta else "—"),
				("Value", value_display),
				("Payment", self.payment_status or "—"),
			]

			# Exporter and Importer for header (Shipper and Consignee names)
			exporter_label = self.exporter_shipper or "—"
			importer_label = self.importer_consignee or "—"

			# Importer classification card (below Importer) - from Consignee customs_importer_classification
			route_below_html = ""
			if self.importer_consignee:
				classification = frappe.db.get_value("Consignee", self.importer_consignee, "customs_importer_classification")
				if classification and classification != "Not Classified":
					cls_lower = (classification or "").lower().replace(" ", "_")
					card_class = "sgl" if "sgl" in cls_lower else "gl" if "gl" in cls_lower or "green" in cls_lower else "yellow" if "yellow" in cls_lower else "red" if "red" in cls_lower else ""
					route_below_html = (
						f'<div class="importer-classification-card {card_class}" style="margin-left: 0;">'
						f'<div class="classification-label">Importer Classification</div>'
						f'<div class="classification-value">{frappe.utils.escape_html(classification)}</div>'
						f'</div>'
					)

			# Section 2: Milestones (from Milestones tab)
			milestone_html = ""
			if self.name and not self.is_new():
				milestone_html = get_milestone_html("Declaration", self.name)
			else:
				milestone_html = '<div class="alert alert-info">Save the document to view milestones.</div>'

			# Section 3: Documents Management (from Air Shipment)
			doc_alerts_html = ""
			try:
				doc_alerts_html = get_document_alerts_html("Declaration", self.name or "new")
			except Exception:
				pass

			# Delay & penalty alerts
			alerts_html = ""
			if self.name and not self.is_new():
				alerts = self.get_delay_penalty_alerts()
				if alerts:
					icons = {"danger": "fa-exclamation-circle", "warning": "fa-exclamation-triangle", "info": "fa-info-circle"}
					items = []
					for a in alerts:
						level = a.get("level") or "info"
						icon = icons.get(level, "fa-info-circle")
						items.append(
							f'<div class="dash-alert-item {level}"><i class="fa {icon}"></i><span>{frappe.utils.escape_html(a.get("msg", ""))}</span></div>'
						)
					alerts_html = "\n".join(items)

			# Use build_run_sheet_style_dashboard: one card with declaration details + milestones, then Documents Management
			return build_run_sheet_style_dashboard(
				header_title=self.name or "Declaration",
				header_subtitle="Declaration",
				header_items=header_items,
				status_badge_html=status_badge_html,
				alerts_html=alerts_html,
				cards_html=milestone_html,
				map_points=[],
				map_id_prefix="decl-dash-map",
				doc_alerts_html=doc_alerts_html,
				straight_line=True,
				origin_label=exporter_label,
				destination_label=importer_label,
				origin_section_label="Exporter",
				destination_section_label="Importer",
				route_below_html=route_below_html,
				doc_management_position="before",
				cards_full_width=True,
				hide_map=True,
				merge_header_with_cards=True,
				header_items_in_card=True,
			)
		except Exception as e:
			frappe.log_error(f"Declaration get_dashboard_html: {str(e)}", "Declaration Dashboard")
			return "<div class='alert alert-warning'>Error loading dashboard.</div>"

	@frappe.whitelist()
	def get_milestone_html(self):
		"""Generate HTML for milestone visualization in Milestones tab."""
		try:
			from logistics.document_management.milestone_html import build_milestone_html

			origin_name = getattr(self, "port_of_loading", None) or "Port of Loading"
			destination_name = getattr(self, "port_of_discharge", None) or "Port of Discharge"

			milestones = frappe.get_all(
				"Job Milestone",
				filters={"job_type": "Declaration", "job_number": self.name},
				fields=["name", "milestone", "status", "planned_start", "planned_end", "actual_start", "actual_end"],
				order_by="planned_start",
			)

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
				origin_party_name=getattr(self, "exporter_shipper", None) or "",
				destination_party_name=getattr(self, "importer_consignee", None) or "",
			)
		except Exception as e:
			frappe.log_error(f"Error in get_milestone_html: {str(e)}", "Declaration - Milestone HTML")
			return "<div class='alert alert-danger'>Error loading milestone view. Please check the error log.</div>"

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
		has_customs = (
			getattr(sq, "main_service", None) == "Customs"
			or any(c.get("service_type") == "Customs" for c in (getattr(sq, "charges") or []))
		)
		if not has_customs:
			frappe.throw(_("No customs details found in the linked Sales Quote."))
		declaration = frappe.new_doc("Declaration")
		_copy_order_to_declaration(declaration, order, sq)
		declaration.insert(ignore_permissions=True)
		# Prefer charges from Declaration Order if present; else from Sales Quote
		if hasattr(order, "charges") and order.charges:
			_populate_charges_from_declaration_order(declaration, order)
		else:
			_populate_charges_from_sales_quote(declaration, sq)
		declaration.save(ignore_permissions=True)
		frappe.db.commit()
		return {
			"success": True,
			"declaration": declaration.name,
			"message": _("Declaration {0} created successfully.").format(declaration.name),
		}
	except frappe.DoesNotExistError:
		frappe.throw(_("Declaration Order {0} does not exist.").format(declaration_order_name))
	except Exception as e:
		frappe.log_error(f"Error creating Declaration from Declaration Order: {str(e)}", "Declaration Creation Error")
		frappe.throw(_("Error creating Declaration: {0}").format(str(e)))


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


def _copy_order_to_declaration(declaration: Document, order: Document, sales_quote: Document):
	"""Copy all information from Declaration Order to Declaration."""
	# Core references
	declaration.declaration_order = order.name
	declaration.sales_quote = order.sales_quote
	declaration.customer = order.customer
	declaration.declaration_date = today()
	declaration.customs_authority = order.customs_authority
	declaration.status = "Draft"

	# Main section
	declaration.currency = order.currency or (getattr(sales_quote, "currency", None) if sales_quote else None)
	declaration.exchange_rate = order.exchange_rate
	declaration.customs_broker = order.customs_broker
	declaration.notify_party = order.notify_party

	# Shipment details
	declaration.exporter_shipper = order.exporter_shipper
	declaration.importer_consignee = order.importer_consignee
	declaration.declaration_type = order.declaration_type
	declaration.transport_mode = order.transport_mode
	declaration.air_shipment = order.air_shipment
	declaration.sea_shipment = order.sea_shipment
	declaration.transport_order = order.transport_order

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
	declaration.job_costing_number = getattr(order, "job_costing_number", None)
	declaration.project = order.project

	# Notes
	declaration.internal_notes = order.internal_notes
	declaration.external_notes = getattr(order, "external_notes", None)

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


def _copy_child_row(source_row: Document, target_row: Document, valid_fields: set):
	"""Copy fields from source child row to target child row."""
	for field in valid_fields:
		if hasattr(source_row, field):
			val = getattr(source_row, field, None)
			if val is not None and field not in ("name", "owner", "creation", "modified", "modified_by", "parent", "parenttype", "parentfield", "idx"):
				target_row.set(field, val)


def _populate_charges_from_declaration_order(declaration: Document, order: Document):
	"""Populate charges from Declaration Order charges (same structure as Declaration Charges)."""
	try:
		if not hasattr(order, "charges") or not order.charges:
			return
		meta = frappe.get_meta("Declaration Charges")
		charge_fields = [f.fieldname for f in meta.fields]
		common_fields = [
			"item_code", "item_name", "calculation_method", "quantity", "uom",
			"currency", "unit_rate", "unit_type", "minimum_quantity", "minimum_charge",
			"maximum_charge", "base_amount", "estimated_revenue", "cost_calculation_method",
			"cost_quantity", "cost_uom", "cost_currency", "unit_cost", "cost_unit_type",
			"cost_minimum_quantity", "cost_minimum_charge", "cost_maximum_charge",
			"cost_base_amount", "estimated_cost", "revenue_calc_notes", "cost_calc_notes",
		]
		for order_charge in order.charges:
			charge_row = declaration.append("charges", {})
			for field in common_fields:
				if field in charge_fields and hasattr(order_charge, field):
					val = getattr(order_charge, field, None)
					if val is not None:
						charge_row.set(field, val)
	except Exception as e:
		frappe.log_error(f"Error populating charges from Declaration Order: {str(e)}")


def _populate_charges_from_sales_quote(declaration: Document, sales_quote: Document):
	"""Populate charges from Sales Quote Charge (Customs) or Sales Quote Customs (legacy)."""
	try:
		customs_charges = []
		if hasattr(sales_quote, "charges") and sales_quote.charges:
			customs_charges = [c for c in sales_quote.charges if c.get("service_type") == "Customs"]
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
				'item_code', 'item_name', 'calculation_method', 'quantity', 'uom',
				'currency', 'unit_rate', 'unit_type', 'minimum_quantity', 'minimum_charge',
				'maximum_charge', 'base_amount', 'estimated_revenue', 'cost_calculation_method',
				'cost_quantity', 'cost_uom', 'cost_currency', 'unit_cost', 'cost_unit_type',
				'cost_minimum_quantity', 'cost_minimum_charge', 'cost_maximum_charge',
				'cost_base_amount', 'estimated_cost', 'revenue_calc_notes', 'cost_calc_notes',
				'use_tariff_in_revenue', 'use_tariff_in_cost', 'tariff',
				'revenue_tariff', 'cost_tariff'
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
	Create a Sales Invoice from a Declaration when declaration is submitted.
	Uses charges from Declaration level.
	"""
	if not declaration_name:
		frappe.throw(_("Declaration name is required."))
	
	declaration = frappe.get_doc("Declaration", declaration_name)
	if declaration.docstatus != 1:
		frappe.throw(_("Declaration must be submitted to create Sales Invoice."))
	
	# Check if Sales Invoice already exists for this declaration
	existing_invoice = frappe.db.get_value("Sales Invoice", {"job_costing_number": declaration.job_costing_number}, "name")
	if existing_invoice and declaration.job_costing_number:
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
	
	# Add reference to Job Costing Number if it exists
	if declaration.job_costing_number:
		si.job_costing_number = declaration.job_costing_number
	
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
