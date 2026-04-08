# Copyright (c) 2025, Agilasoft Cloud Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import cint, flt, today, getdate

from logistics.utils.charge_service_type import (
	customs_charges_rows_from_sales_quote_doc,
	throw_if_missing_destination_service_charge,
)
from logistics.utils.internal_job_charge_copy import (
	apply_internal_job_main_charge_overlay,
	build_internal_job_declaration_charge_dicts,
	populate_internal_job_charges_from_main_service,
	should_apply_internal_job_main_charge_overlay,
)


class DeclarationOrder(Document):
	@frappe.whitelist()
	def get_dashboard_html(self):
		"""Generate HTML for Dashboard tab: order details (same layout as Declaration), milestones, Documents Management."""
		try:
			from logistics.document_management.api import get_document_alerts_html, get_milestone_html
			from logistics.document_management.dashboard_layout import build_run_sheet_style_dashboard

			# Section 1: Order details (header format) with Exporter | Importer
			status = self.status or "Draft"
			status_badge_html = f'<span class="dash-status-badge {(status or "draft").lower().replace(" ", "_")}">{frappe.utils.escape_html(status)}</span>'
			# Format value with correct currency code from commercial invoice
			currency = self.inv_currency or frappe.db.get_default("currency") or "PHP"
			try:
				# Format number and append currency code instead of using symbol
				amount = flt(self.inv_total_amount or 0)
				value_str = f"{frappe.utils.fmt_money(amount, precision=2)} {currency}"
			except Exception:
				value_str = str(self.inv_total_amount) if self.inv_total_amount is not None else "—"
			header_items = [
				("Status", status),
				("Type", self.declaration_type or "—"),
				("Date", str(self.order_date) if self.order_date else "—"),
				("Port of Loading", self.port_of_loading or "—"),
				("Port of Discharge", self.port_of_discharge or "—"),
				("ETD", str(self.etd) if self.etd else "—"),
				("ETA", str(self.eta) if self.eta else "—"),
				("Value", value_str),
			]

			exporter_label = self.exporter_shipper or "—"
			importer_label = self.importer_consignee or "—"

			# Importer classification card (below Importer)
			route_below_html = ""
			if self.importer_consignee:
				try:
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
				except Exception:
					pass

			# Section 2: Milestones
			milestone_html = ""
			if self.name and not self.is_new():
				try:
					milestone_html = get_milestone_html("Declaration Order", self.name)
				except Exception:
					milestone_html = '<div class="alert alert-warning">Could not load milestones.</div>'
			else:
				milestone_html = '<div class="alert alert-info">Save the document to view milestones.</div>'

			# Section 3: Documents Management
			doc_alerts_html = ""
			try:
				doc_alerts_html = get_document_alerts_html("Declaration Order", self.name or "new")
			except Exception:
				pass

			# Delay & penalty alerts
			alerts_html = ""
			if self.name and not self.is_new():
				try:
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
				except Exception as alert_err:
					frappe.log_error(f"Declaration Order get_delay_penalty_alerts: {str(alert_err)}", "Declaration Order Dashboard Alerts")

			from logistics.utils.sales_quote_validity import get_sales_quote_validity_dashboard_html

			dash = build_run_sheet_style_dashboard(
				header_title=self.name or "Declaration Order",
				header_subtitle="Declaration Order",
				header_items=header_items,
				status_badge_html=status_badge_html,
				alerts_html=alerts_html,
				route_below_html=route_below_html,
				cards_html=milestone_html,
				map_points=[],
				map_id_prefix="dco-dash-map",
				doc_alerts_html=doc_alerts_html,
				straight_line=True,
				origin_label=exporter_label,
				destination_label=importer_label,
				origin_section_label="Exporter",
				destination_section_label="Importer",
				doc_management_position="before",
				cards_full_width=True,
				hide_map=True,
				merge_header_with_cards=True,
				header_items_in_card=True,
			)
			return get_sales_quote_validity_dashboard_html(self) + dash
		except Exception as e:
			frappe.log_error(f"Declaration Order get_dashboard_html: {str(e)}", "Declaration Order Dashboard")
			err_msg = frappe.utils.escape_html(str(e))
			return f"<div class='alert alert-warning'>Error loading dashboard. See Error Log (Declaration Order Dashboard) for details.</div><div class='text-muted small' style='margin-top:8px'>{err_msg}</div>"

	def get_delay_penalty_alerts(self):
		"""Return list of alerts related to delays and penalties for dashboard display."""
		from frappe.utils import getdate, today, date_diff
		alerts = []
		try:
			today_date = getdate(today())
		except Exception:
			return alerts

		# 1. Pending required permits (virtual permit fields use properties; avoid pr.get for those)
		for pr in (self.get("permit_requirements") or []):
			is_req = pr.get("is_required")
			is_obt = getattr(pr, "is_obtained", None)
			ptype = getattr(pr, "permit_type", None) or pr.get("planned_permit_type")
			expiry = getattr(pr, "expiry_date", None)
			if is_req and not is_obt:
				alerts.append({"level": "danger", "msg": _("Required permit {0} not yet obtained.").format(ptype or "—")})
			elif is_obt and expiry:
				try:
					exp = getdate(expiry)
					if exp < today_date:
						alerts.append({"level": "danger", "msg": _("Permit {0} expired on {1}. Renew to avoid penalties.").format(ptype or "—", expiry)})
					elif date_diff(exp, today_date) <= 7:
						alerts.append({"level": "warning", "msg": _("Permit {0} expires on {1}.").format(ptype or "—", expiry)})
				except Exception:
					pass

		# 2. Exemption certificates expiring or inactive
		for ex in (self.get("exemptions") or []):
			if not ex.get("exemption_certificate"):
				continue
			try:
				cert = frappe.get_doc("Exemption Certificate", ex.exemption_certificate)
				if cert.status != "Active":
					alerts.append({"level": "warning", "msg": _("Exemption certificate {0} is not active.").format(cert.name)})
				elif cert.valid_to:
					try:
						exp = getdate(cert.valid_to)
						if exp < today_date:
							alerts.append({"level": "danger", "msg": _("Exemption certificate {0} expired on {1}.").format(cert.name, cert.valid_to)})
						elif date_diff(exp, today_date) <= 14:
							alerts.append({"level": "warning", "msg": _("Exemption certificate {0} expires on {1}.").format(cert.name, cert.valid_to)})
					except Exception:
						pass
			except (frappe.DoesNotExistError, Exception):
				pass

		# 3. Overdue required documents
		for doc in (self.get("documents") or []):
			if not doc.get("is_required"):
				continue
			status = (doc.get("status") or "").strip()
			if status in ("Received", "Verified", "Done"):
				continue
			date_req = doc.get("date_required")
			if date_req:
				try:
					dr = getdate(date_req)
					if dr < today_date:
						alerts.append({"level": "danger", "msg": _("Document {0} was required on {1} and is overdue.").format(doc.get("document_type") or "—", date_req)})
				except Exception:
					pass

		# 4. Documents expiring within 7 days
		for doc in (self.get("documents") or []):
			exp_date = doc.get("expiry_date")
			if not exp_date:
				continue
			try:
				exp = getdate(exp_date)
				if exp >= today_date and date_diff(exp, today_date) <= 7:
					alerts.append({"level": "info", "msg": _("Document {0} expires on {1}.").format(doc.get("document_type") or "—", exp_date)})
			except Exception:
				pass

		return alerts

	def validate(self):
		"""Validate and handle Sales Quote link (One-off conversion and link-cleared reset)."""
		original_sales_quote = None
		if not self.is_new():
			try:
				original_sales_quote = frappe.db.get_value(self.doctype, self.name, "sales_quote")
			except Exception:
				pass
		if not original_sales_quote:
			original_sales_quote = getattr(self, "sales_quote", None)

		if self.sales_quote:
			from logistics.pricing_center.doctype.sales_quote.sales_quote import (
				resolve_allow_linked_freight_bookings_for_internal_job,
				validate_one_off_quote_not_converted,
			)

			allow_sea, allow_air = resolve_allow_linked_freight_bookings_for_internal_job(self)
			validate_one_off_quote_not_converted(
				self.sales_quote,
				self.doctype,
				self.name,
				allow_linked_sea_booking=allow_sea,
				allow_linked_air_booking=allow_air,
			)

		# Handle sales_quote field clearing - reset One-off quote if cleared
		if not self.is_new() and original_sales_quote and not self.sales_quote:
			try:
				if frappe.db.exists("Sales Quote", original_sales_quote):
					sq = frappe.get_doc("Sales Quote", original_sales_quote)
					if sq.quotation_type == "One-off":
						from logistics.pricing_center.doctype.sales_quote.sales_quote import reset_one_off_quote_on_cancel
						reset_one_off_quote_on_cancel(original_sales_quote)
			except Exception:
				pass

		self._validate_etd_eta()

		from logistics.utils.sales_quote_validity import msgprint_sales_quote_validity_warnings

		msgprint_sales_quote_validity_warnings(self)

		apply_internal_job_main_charge_overlay(self)

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

	def after_insert(self):
		"""Called after document is inserted."""
		pass

	def before_save(self):
		from logistics.utils.module_integration import (
			apply_internal_job_declaration_order_from_shipment,
			run_propagate_on_link,
		)
		from logistics.utils.shipper_consignee_defaults import apply_shipper_consignee_defaults

		run_propagate_on_link(self)
		apply_internal_job_declaration_order_from_shipment(self)
		apply_shipper_consignee_defaults(self)
		self.calculate_exemptions()
		# First save only: pull charges from Sales Quote (or internal-job main service) when the grid is still empty.
		# Covers API/quick entry and cases where the form did not run the client fetch (e.g. pre-filled sales_quote).
		if self.is_new() and not (self.get("charges") or []):
			if self.sales_quote:
				self._populate_charges_from_sales_quote()
			elif cint(getattr(self, "is_internal_job", 0)) and should_apply_internal_job_main_charge_overlay(
				self
			):
				self._populate_charges_from_sales_quote()

	def before_submit(self):
		"""Prevent submission if no Sales Quote is linked to this Declaration Order.
		
		This ensures every submitted Declaration Order is connected to a Sales Quote,
		which is necessary for proper tracking and billing.
		"""
		if not self.sales_quote:
			frappe.throw(_("Sales Quote is required. Please select a Sales Quote before submitting the Declaration Order."))
		throw_if_missing_destination_service_charge(self)

	def on_submit(self):
		if self.sales_quote:
			try:
				from logistics.pricing_center.doctype.sales_quote.sales_quote import update_one_off_quote_on_submit
				update_one_off_quote_on_submit(self.sales_quote, self.name, self.doctype)
			except Exception as e:
				frappe.log_error(f"Update Sales Quote on Declaration Order submit: {e}", "Declaration Order Submit")

	def on_cancel(self):
		"""Reset One-off Sales Quote status when Declaration Order is cancelled."""
		if self.sales_quote:
			try:
				from logistics.pricing_center.doctype.sales_quote.sales_quote import reset_one_off_quote_on_cancel
				reset_one_off_quote_on_cancel(self.sales_quote)
			except Exception as e:
				frappe.log_error(f"Reset Sales Quote on Declaration Order cancel: {e}", "Declaration Order Cancel")

	def on_trash(self):
		"""Remove Internal Job Detail back-link on Air/Sea Shipment when this order is deleted."""
		try:
			from logistics.utils.internal_job_detail_copy import unlink_declaration_order_from_shipment

			if getattr(self, "air_shipment", None) and frappe.db.exists("Air Shipment", self.air_shipment):
				unlink_declaration_order_from_shipment("Air Shipment", self.air_shipment, self.name)
			if getattr(self, "sea_shipment", None) and frappe.db.exists("Sea Shipment", self.sea_shipment):
				unlink_declaration_order_from_shipment("Sea Shipment", self.sea_shipment, self.name)
		except Exception as e:
			frappe.log_error(f"Declaration Order on_trash clear shipment link: {e}", "Declaration Order Trash")

	@frappe.whitelist()
	def calculate_total_charges(self):
		"""Calculate total charges for this Declaration Order."""
		total_charges = 0
		if hasattr(self, "charges") and self.charges:
			for charge in self.charges:
				if hasattr(charge, "calculate_charge_amount"):
					charge.calculate_charge_amount(parent_doc=self)
				total_charges += flt(
					getattr(charge, "total_amount", None) or getattr(charge, "estimated_revenue", 0)
				) or 0
		return {
			"total_charges": total_charges,
			"currency": self.get("charges")[0].currency if self.get("charges") else None,
		}

	@frappe.whitelist()
	def recalculate_all_charges(self):
		"""Recalculate all charges using centralized charge calculation."""
		if not hasattr(self, "charges") or not self.charges:
			return {"success": False, "message": "No charges found to recalculate"}
		try:
			charges_recalculated = 0
			for charge in self.charges:
				if hasattr(charge, "calculate_charge_amount"):
					charge.calculate_charge_amount(parent_doc=self)
					charges_recalculated += 1
			self.save()
			frappe.msgprint(
				_("Successfully recalculated {0} charges").format(charges_recalculated),
				title=_("Charges Recalculated"),
				indicator="green",
			)
			return {
				"success": True,
				"message": _("Successfully recalculated {0} charges").format(charges_recalculated),
				"charges_recalculated": charges_recalculated,
			}
		except Exception as e:
			frappe.log_error(
				"Error recalculating Declaration Order charges: {0}".format(str(e)),
				"Declaration Order - Recalculate Charges Error",
			)
			frappe.throw(_("Error recalculating charges: {0}").format(str(e)))

	@frappe.whitelist()
	def revert_charges_to_source(self):
		"""Revert charges to their source baseline (Main Job overlay or Sales Quote)."""
		if self.docstatus == 1:
			frappe.throw(
				_("Cannot revert charges after submission. Please cancel/amend the document or use a Draft Declaration Order."),
				title=_("Cannot Update After Submit"),
			)
		if not self.sales_quote and not should_apply_internal_job_main_charge_overlay(self):
			return {"success": False, "message": _("No source charges available to revert.")}
		try:
			self.set("charges", [])
			self._populate_charges_from_sales_quote()
			self.save()

			source = "sales_quote"
			if cint(getattr(self, "is_internal_job", 0)) and should_apply_internal_job_main_charge_overlay(self):
				source = "main_job"

			return {
				"success": True,
				"source": source,
				"charges_count": len(self.get("charges") or []),
				"message": _("Charges reverted successfully."),
			}
		except Exception as e:
			frappe.log_error(
				"Error reverting Declaration Order charges: {0}".format(str(e)),
				"Declaration Order - Revert Charges Error",
			)
			frappe.throw(_("Error reverting charges: {0}").format(str(e)))

	def calculate_exemptions(self):
		"""Calculate total_exempted amount for each exemption in the declaration order"""
		if not self.exemptions:
			return
		
		for exemption in self.exemptions:
			# Calculate total_exempted from exempted_duty, exempted_tax, and exempted_fee
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

	def _populate_charges_from_sales_quote(self):
		"""Populate charges from Sales Quote Charge (Customs) or Sales Quote Customs (legacy)."""
		overlay_populated = False
		if cint(getattr(self, "is_internal_job", 0)) and should_apply_internal_job_main_charge_overlay(self):
			try:
				n, st = populate_internal_job_charges_from_main_service(self)
				if n:
					frappe.msgprint(
						_("Populated {0} charge rows from Main Job (Service Type: {1}).").format(n, st),
						title=_("Charges Updated"),
						indicator="green",
					)
					overlay_populated = True
				else:
					frappe.msgprint(
						_("No Customs charge lines on the Main Job; loading charges from Sales Quote if available."),
						title=_("Charges"),
						indicator="orange",
					)
			except Exception as e:
				frappe.log_error(f"Error populating Declaration Order charges from Main Job: {str(e)}")
				frappe.msgprint(str(e), title=_("Error"), indicator="red")

		if overlay_populated:
			return

		if not self.sales_quote:
			return
		try:
			if not frappe.db.exists("Sales Quote", self.sales_quote):
				return
			sq = frappe.get_doc("Sales Quote", self.sales_quote)
			sq_charges = customs_charges_rows_from_sales_quote_doc(self, sq)
			if not sq_charges and hasattr(sq, "customs") and sq.customs:
				sq_charges = list(sq.customs)
			if not sq_charges:
				return
			meta = frappe.get_meta("Declaration Order Charges")
			charge_fields = [f.fieldname for f in meta.fields]
			common_fields = [
				"service_type", "item_code", "item_name", "charge_type", "charge_category", "quantity", "uom",
				"currency", "unit_type", "minimum_quantity", "minimum_unit_rate", "minimum_charge",
				"maximum_charge", "base_amount", "base_quantity", "estimated_revenue",
				"cost_calculation_method", "cost_quantity", "cost_uom", "cost_currency", "unit_cost",
				"cost_unit_type", "cost_minimum_quantity", "cost_minimum_unit_rate", "cost_minimum_charge",
				"cost_maximum_charge", "cost_base_amount", "cost_base_quantity", "estimated_cost",
				"revenue_calc_notes", "cost_calc_notes", "charge_basis", "rate",
			]
			self.set("charges", [])
			for sq_charge in sq_charges:
				row = self.append("charges", {})
				for field in common_fields:
					if field in charge_fields and hasattr(sq_charge, field):
						val = getattr(sq_charge, field, None)
						if val is not None:
							row.set(field, val)
				# Map Sales Quote field names to charge table (charge_basis/rate)
				if "charge_basis" in charge_fields and hasattr(sq_charge, "calculation_method") and sq_charge.calculation_method:
					row.set("charge_basis", sq_charge.calculation_method)
				if "rate" in charge_fields and hasattr(sq_charge, "unit_rate") and sq_charge.unit_rate is not None:
					row.set("rate", sq_charge.unit_rate)
				if "charge_type" in charge_fields and not row.get("charge_type"):
					row.set("charge_type", "Revenue")
		except Exception as e:
			frappe.log_error(f"Error populating Declaration Order charges from Sales Quote: {str(e)}")


@frappe.whitelist()
def get_sales_quote_details(sales_quote):
	"""Return customer, company, customs_authority, declaration_type, incoterm, currency, etc. from Sales Quote for use in form."""
	if not sales_quote:
		return {}
	fields = [
		"customer", "company", "branch", "cost_center", "profit_center",
		"incoterm",
	]
	out = frappe.db.get_value("Sales Quote", sales_quote, fields, as_dict=True) or {}
	# Get customs params from first Customs charge or legacy header
	customs_charge = frappe.db.get_value(
		"Sales Quote Charge",
		{"parent": sales_quote, "parenttype": "Sales Quote", "service_type": "Customs"},
		["customs_authority", "declaration_type"],
		as_dict=True,
	)
	if customs_charge:
		out["customs_authority"] = customs_charge.get("customs_authority")
		out["declaration_type"] = customs_charge.get("declaration_type")
	if out.get("customs_authority") is None and out.get("declaration_type") is None:
		legacy = frappe.db.get_value("Sales Quote", sales_quote, ["customs_authority", "declaration_type"], as_dict=True)
		if legacy:
			out["customs_authority"] = legacy.get("customs_authority")
			out["declaration_type"] = legacy.get("declaration_type")
	return out


@frappe.whitelist()
def populate_charges_from_sales_quote(
	docname=None,
	sales_quote=None,
	is_internal_job=None,
	main_job_type=None,
	main_job=None,
):
	"""Populate charges from Sales Quote Charge (Customs) or Sales Quote Customs (legacy)."""
	try:
		parent = (
			frappe.get_doc("Declaration Order", docname)
			if docname and frappe.db.exists("Declaration Order", docname)
			else frappe._dict(
				doctype="Declaration Order", name=docname, is_internal_job=0, is_main_service=0
			)
		)
		if is_internal_job is not None:
			parent.is_internal_job = cint(is_internal_job)
		if main_job_type is not None:
			parent.main_job_type = main_job_type
		if main_job is not None:
			parent.main_job = main_job

		if should_apply_internal_job_main_charge_overlay(parent):
			charges = build_internal_job_declaration_charge_dicts(parent)
			if charges:
				return {
					"charges": charges,
					"charges_count": len(charges),
					"internal_job_charge_overlay_applied": True,
					"source": "main_service",
				}
			# No Customs rows on main job: use Sales Quote customs charges if available

		if not sales_quote:
			return {"charges": [], "charges_count": 0}
		# Temporary names (unsaved documents) cannot be fetched
		if sales_quote.startswith("new-"):
			return {"charges": [], "charges_count": 0, "error": _("Please save the Sales Quote first before selecting it here.")}
		if not frappe.db.exists("Sales Quote", sales_quote):
			return {"charges": [], "error": _("Sales Quote {0} does not exist.").format(sales_quote)}
		sq = frappe.get_doc("Sales Quote", sales_quote)
		sq_charges = customs_charges_rows_from_sales_quote_doc(parent, sq)
		if not sq_charges and hasattr(sq, "customs") and sq.customs:
			sq_charges = list(sq.customs)
		if not sq_charges:
			return {"charges": [], "message": _("No customs charges found in Sales Quote: {0}").format(sales_quote)}
		meta = frappe.get_meta("Declaration Order Charges")
		charge_fields = [f.fieldname for f in meta.fields]
		common_fields = [
			"service_type", "item_code", "item_name", "charge_type", "charge_category", "quantity", "uom",
			"currency", "unit_type", "minimum_quantity", "minimum_unit_rate", "minimum_charge",
			"maximum_charge", "base_amount", "base_quantity", "estimated_revenue",
			"cost_calculation_method", "cost_quantity", "cost_uom", "cost_currency", "unit_cost",
			"cost_unit_type", "cost_minimum_quantity", "cost_minimum_unit_rate", "cost_minimum_charge",
			"cost_maximum_charge", "cost_base_amount", "cost_base_quantity", "estimated_cost",
			"revenue_calc_notes", "cost_calc_notes", "charge_basis", "rate",
			"use_tariff_in_revenue", "revenue_tariff", "use_tariff_in_cost", "cost_tariff",
			"bill_to", "pay_to",
		]
		charges = []
		for sq_charge in sq_charges:
			row = {}
			for field in common_fields:
				if field in charge_fields and hasattr(sq_charge, field):
					val = getattr(sq_charge, field, None)
					if val is not None:
						row[field] = val
			# Map Sales Quote field names to charge table
			if "charge_basis" in charge_fields and getattr(sq_charge, "calculation_method", None):
				row["charge_basis"] = sq_charge.calculation_method
			if "rate" in charge_fields and getattr(sq_charge, "unit_rate", None) is not None:
				row["rate"] = sq_charge.unit_rate
			# Map revenue_calculation_method from calculation_method if field exists
			if "revenue_calculation_method" in charge_fields and getattr(sq_charge, "calculation_method", None):
				row["revenue_calculation_method"] = sq_charge.calculation_method
			# Map legacy tariff field to revenue_tariff and cost_tariff if they exist
			legacy_tariff = getattr(sq_charge, "tariff", None)
			if legacy_tariff and not row.get("revenue_tariff") and not row.get("cost_tariff"):
				# If source has tariff but not separate revenue_tariff/cost_tariff, map to both
				if "revenue_tariff" in charge_fields and (row.get("use_tariff_in_revenue") or getattr(sq_charge, "use_tariff_in_revenue", False)):
					row["revenue_tariff"] = legacy_tariff
				if "cost_tariff" in charge_fields and (row.get("use_tariff_in_cost") or getattr(sq_charge, "use_tariff_in_cost", False)):
					row["cost_tariff"] = legacy_tariff
			# Set sales_quote_link to link back to the Sales Quote
			if "sales_quote_link" in charge_fields:
				row["sales_quote_link"] = sales_quote
			if "charge_type" not in row or not row.get("charge_type"):
				row["charge_type"] = "Revenue"
			if row:
				charges.append(row)
		return {
			"charges": charges,
			"charges_count": len(charges),
			"internal_job_charge_overlay_applied": False,
		}
	except Exception as e:
		frappe.log_error(f"Error populating Declaration Order charges: {str(e)}")
		return {"charges": [], "error": str(e)}


@frappe.whitelist()
def fetch_declaration_order_dashboard_html(docname):
	"""
	Return Dashboard tab HTML for a saved Declaration Order.

	Uses a standalone whitelisted method instead of frm.call(get_dashboard_html) so we do not
	go through run_doc_method / check_if_latest. That avoids TimestampMismatchError when the user
	saves and refresh() loads the dashboard in the same moment the DB modified timestamp updates.
	"""
	if not docname or str(docname).startswith("new-"):
		return ""
	if not frappe.db.exists("Declaration Order", docname):
		return ""
	doc = frappe.get_doc("Declaration Order", docname)
	return doc.get_dashboard_html()


@frappe.whitelist()
def create_declaration_order_from_sales_quote(sales_quote_name: str):
	"""
	Create a Declaration Order from a Sales Quote (One-off, with customs).
	Updates the Sales Quote status and converted_to_doc to the new Declaration Order.
	"""
	if not sales_quote_name:
		frappe.throw(_("A Sales Quote must be selected to create a Declaration Order."))
	from logistics.utils.sales_quote_validity import throw_if_sales_quote_expired_for_creation

	sq = frappe.get_doc("Sales Quote", sales_quote_name)
	throw_if_sales_quote_expired_for_creation(sq)
	if sq.quotation_type != "One-off":
		frappe.throw(_("Only One-off Sales Quotes can create a Declaration Order."))
	sq_customs = []
	if hasattr(sq, "charges") and sq.charges:
		sq_customs = [c for c in sq.charges if c.get("service_type") == "Customs"]
	if not sq_customs and hasattr(sq, "customs") and sq.customs:
		sq_customs = list(sq.customs)
	if not sq_customs:
		frappe.throw(_("No customs details in this Sales Quote."))
	existing = frappe.db.get_value("Declaration Order", {"sales_quote": sales_quote_name}, "name")
	if existing:
		frappe.throw(
			_("Declaration Order {0} already exists for this Sales Quote.").format(existing),
			title=_("Already Created"),
		)
	details = get_sales_quote_details(sales_quote_name) or {}
	order = frappe.new_doc("Declaration Order")
	order.sales_quote = sales_quote_name
	order.order_date = today()
	for key in ("customer", "company", "customs_authority", "branch", "cost_center", "profit_center", "declaration_type", "incoterm"):
		if details.get(key) is not None:
			order.set(key, details[key])
	order.insert(ignore_permissions=True)
	# Charges should be populated from Declaration Order, not automatically from Sales Quote
	# order._populate_charges_from_sales_quote()
	order.save(ignore_permissions=True)
	try:
		from logistics.pricing_center.doctype.sales_quote.sales_quote import update_one_off_quote_on_submit
		update_one_off_quote_on_submit(sales_quote_name, order.name, "Declaration Order")
	except Exception as e:
		frappe.log_error(f"Update Sales Quote on Declaration Order create: {e}", "Declaration Order Create")
	frappe.db.commit()
	return {
		"success": True,
		"declaration_order": order.name,
		"message": _("Declaration Order {0} created.").format(order.name),
	}
