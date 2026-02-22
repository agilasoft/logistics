# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import today, getdate, flt
from typing import Dict, Any, Optional


class Declaration(Document):
	def validate(self):
		try:
			from logistics.utils.measurements import apply_measurement_uom_conversion_to_children
			apply_measurement_uom_conversion_to_children(self, "commodities", company=getattr(self, "company", None))
		except Exception:
			pass

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
	
	def calculate_declaration_value(self):
		"""Calculate total declaration value from commodities"""
		total_value = 0
		if self.commodities:
			for commodity in self.commodities:
				value = flt(commodity.total_value or 0)
				total_value += value
		self.declaration_value = total_value
	
	def update_processing_dates(self):
		"""Update processing dates based on status"""
		from frappe.utils import now, nowdate, get_datetime
		
		if self.status == "Submitted" and not self.submission_date:
			self.submission_date = nowdate()
			if not self.submission_time:
				self.submission_time = get_datetime(now()).strftime("%H:%M:%S")
		elif self.status == "Approved" and not self.approval_date:
			self.approval_date = nowdate()
		elif self.status == "Rejected" and not self.rejection_date:
			self.rejection_date = nowdate()
	
	def handle_status_changes(self):
		"""Validate status transitions and enforce workflow rules."""
		if self.is_new():
			return
		old_status = frappe.db.get_value(self.doctype, self.name, "status")
		new_status = self.status
		if old_status == new_status:
			return
		# Define allowed transitions
		allowed_transitions = {
			"Draft": ["Submitted", "In Progress", "Cancelled"],
			"Submitted": ["In Progress", "Approved", "Rejected", "Cancelled"],
			"In Progress": ["Submitted", "Approved", "Rejected", "Cancelled"],
			"Approved": ["Cancelled"],
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
		"""Generate HTML for Dashboard tab: status, alerts, missing, exceptions, compliance."""
		try:
			from frappe.utils import getdate, today, date_diff

			status = self.status or "Draft"
			status_class = status.lower().replace(" ", "-").replace("/", "-")

			# Status & key metrics row
			metrics = []
			metrics.append(("Status", status))
			if self.declaration_type:
				metrics.append(("Type", self.declaration_type))
			if self.declaration_number:
				metrics.append(("Declaration #", self.declaration_number))
			if self.payment_status:
				metrics.append(("Payment", self.payment_status))
			if self.expected_clearance_date:
				metrics.append(("Expected Clearance", str(self.expected_clearance_date)))
			if self.actual_clearance_date:
				metrics.append(("Actual Clearance", str(self.actual_clearance_date)))

			metric_cards = "".join(
				f'<div class="dash-card"><span class="dash-label">{m[0]}</span><span class="dash-value">{m[1]}</span></div>'
				for m in metrics
			)

			# Document alerts (Declaration Document structure)
			doc_alerts = []
			today_date = getdate(today())
			for d in (self.get("documents") or []):
				if not getattr(d, "is_required", 0):
					continue
				st = (getattr(d, "status", None) or "").strip()
				exp = getattr(d, "expiry_date", None)
				att = getattr(d, "attachment", None)
				doc_type = getattr(d, "document_type", None) or "Document"
				if st in ("Expired", "Rejected") or (exp and getdate(exp) < today_date):
					doc_alerts.append(("danger", f"{doc_type} – expired or rejected"))
				elif not att and st in ("Pending", "Attached"):
					doc_alerts.append(("warning", f"{doc_type} – pending"))
				elif exp and date_diff(getdate(exp), today_date) <= 7 and date_diff(getdate(exp), today_date) >= 0:
					doc_alerts.append(("info", f"{doc_type} – expires {exp}"))

			# Missing permits
			permits_alerts = []
			for p in (self.get("permit_requirements") or []):
				if getattr(p, "is_required", 0) and not getattr(p, "is_obtained", 0):
					permits_alerts.append(getattr(p, "permit_type", None) or "Permit")

			# Compliance / exceptions
			exceptions = []
			if self.status == "Rejected" and getattr(self, "rejection_reason", None):
				exceptions.append(("Rejection", self.rejection_reason[:200]))
			if self.payment_status == "Overdue":
				exceptions.append(("Payment", "Payment overdue"))

			# Build alerts HTML
			alerts_html = ""
			for level, msg in doc_alerts[:5]:
				alerts_html += f'<div class="alert alert-{level} dash-alert">{msg}</div>'
			if permits_alerts:
				alerts_html += f'<div class="alert alert-warning dash-alert"><strong>Missing Permits:</strong> {", ".join(permits_alerts)}</div>'
			for title, msg in exceptions[:3]:
				alerts_html += f'<div class="alert alert-danger dash-alert"><strong>{title}:</strong> {msg}</div>'

			html = f"""
			<div class="decl-dashboard">
				<div class="dash-header">
					<div class="dash-status-badge {status_class}">{status}</div>
					<div class="dash-metrics">{metric_cards}</div>
				</div>
				{f'<div class="dash-alerts">{alerts_html}</div>' if alerts_html else ''}
				<div class="dash-summary">
					<div class="dash-summary-item"><span class="dash-num">{len(self.commodities or [])}</span><span class="dash-desc">Commodities</span></div>
					<div class="dash-summary-item"><span class="dash-num">{frappe.format_value(self.declaration_value or 0, df=dict(fieldtype="Currency"))}</span><span class="dash-desc">Value</span></div>
					<div class="dash-summary-item"><span class="dash-num">{frappe.format_value(self.total_payable or 0, df=dict(fieldtype="Currency"))}</span><span class="dash-desc">Total Payable</span></div>
				</div>
			</div>
			<style>
			.decl-dashboard {{ font-family: inherit; font-size: 13px; }}
			.dash-header {{ display: flex; align-items: center; gap: 16px; flex-wrap: wrap; margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px solid #e0e0e0; }}
			.dash-status-badge {{ padding: 4px 12px; border-radius: 6px; font-weight: 600; font-size: 12px; text-transform: uppercase; }}
			.dash-status-badge.draft {{ background: #e2e3e5; color: #383d41; }}
			.dash-status-badge.submitted {{ background: #cce5ff; color: #004085; }}
			.dash-status-badge.in-progress {{ background: #fff3cd; color: #856404; }}
			.dash-status-badge.approved {{ background: #d4edda; color: #155724; }}
			.dash-status-badge.rejected {{ background: #f8d7da; color: #721c24; }}
			.dash-status-badge.cancelled {{ background: #e2e3e5; color: #6c757d; }}
			.dash-metrics {{ display: flex; gap: 12px; flex-wrap: wrap; }}
			.dash-card {{ background: #f8f9fa; border: 1px solid #e9ecef; border-radius: 4px; padding: 6px 10px; min-width: 100px; }}
			.dash-label {{ font-size: 10px; color: #6c757d; display: block; }}
			.dash-value {{ font-size: 12px; font-weight: 600; color: #333; }}
			.dash-alerts {{ margin-bottom: 12px; display: flex; flex-direction: column; gap: 8px; }}
			.dash-alert {{ margin: 0; padding: 8px 12px; font-size: 12px; border-radius: 4px; }}
			.dash-summary {{ display: flex; gap: 16px; flex-wrap: wrap; }}
			.dash-summary-item {{ background: #fff; border: 1px solid #e0e0e0; border-radius: 6px; padding: 12px 16px; min-width: 120px; text-align: center; }}
			.dash-num {{ display: block; font-size: 16px; font-weight: 700; color: #007bff; }}
			.dash-desc {{ font-size: 11px; color: #6c757d; }}
			</style>
			"""
			return html
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
	Sets declaration_order and sales_quote from the order; copies customer, company, customs_authority, etc.
	"""
	if not declaration_order_name:
		frappe.throw(_("Declaration Order name is required."))
	try:
		order = frappe.get_doc("Declaration Order", declaration_order_name)
		if not order.sales_quote:
			frappe.throw(_("Declaration Order must have a Sales Quote to create a Declaration."))
		sq = frappe.get_doc("Sales Quote", order.sales_quote)
		has_customs = bool(getattr(sq, "customs", None))
		if not has_customs:
			frappe.throw(_("No customs details found in the linked Sales Quote."))
		declaration = frappe.new_doc("Declaration")
		declaration.declaration_order = order.name
		declaration.sales_quote = order.sales_quote
		declaration.customer = order.customer
		declaration.declaration_date = today()
		declaration.customs_authority = order.customs_authority
		declaration.company = order.company
		declaration.branch = order.branch
		declaration.cost_center = order.cost_center
		declaration.profit_center = order.profit_center
		if hasattr(sq, "currency") and sq.currency:
			declaration.currency = sq.currency
		declaration.insert(ignore_permissions=True)
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
		if not sq.one_off:
			frappe.throw(_("This Sales Quote is not tagged as One-Off. Only One-Off quotes can create Declarations."))
		
		# Check if Sales Quote has customs details
		has_customs = False
		if hasattr(sq, 'customs') and sq.customs:
			has_customs = True
		
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
		
		# Set customs authority if available in quote
		if hasattr(sq, 'customs_authority') and sq.customs_authority:
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


def _populate_charges_from_sales_quote(declaration: Document, sales_quote: Document):
	"""Populate charges from Sales Quote Customs charges"""
	try:
		if not hasattr(sales_quote, 'customs') or not sales_quote.customs:
			return
		
		# Get customs charges from Sales Quote
		customs_charges = sales_quote.get('customs') or []
		
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
				'use_tariff_in_revenue', 'use_tariff_in_cost', 'tariff'
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
