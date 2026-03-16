# Copyright (c) 2025, Agilasoft Cloud Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _
from frappe.utils import flt, today


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
			header_items = [
				("Status", status),
				("Type", self.declaration_type or "—"),
				("Date", str(self.order_date) if self.order_date else "—"),
				("Port of Loading", self.port_of_loading or "—"),
				("Port of Discharge", self.port_of_discharge or "—"),
				("ETD", str(self.etd) if self.etd else "—"),
				("ETA", str(self.eta) if self.eta else "—"),
				("Value", frappe.format_value(self.inv_total_amount or 0, df=dict(fieldtype="Currency"))),
			]

			exporter_label = self.exporter_shipper or "—"
			importer_label = self.importer_consignee or "—"

			# Importer classification card (below Importer)
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

			# Section 2: Milestones
			milestone_html = ""
			if self.name and not self.is_new():
				milestone_html = get_milestone_html("Declaration Order", self.name)
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

			return build_run_sheet_style_dashboard(
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
				doc_management_position="after",
				cards_full_width=True,
				hide_map=True,
				merge_header_with_cards=True,
				header_items_in_card=True,
			)
		except Exception as e:
			frappe.log_error(f"Declaration Order get_dashboard_html: {str(e)}", "Declaration Order Dashboard")
			return "<div class='alert alert-warning'>Error loading dashboard.</div>"

	def get_delay_penalty_alerts(self):
		"""Return list of alerts related to delays and penalties for dashboard display."""
		from frappe.utils import getdate, today, date_diff
		alerts = []
		today_date = getdate(today())

		# 1. Pending required permits
		for pr in (self.get("permit_requirements") or []):
			if pr.get("is_required") and not pr.get("is_obtained"):
				alerts.append({"level": "danger", "msg": _("Required permit {0} not yet obtained.").format(pr.get("permit_type") or "—")})
			elif pr.get("is_obtained") and pr.get("expiry_date"):
				exp = getdate(pr.expiry_date)
				if exp < today_date:
					alerts.append({"level": "danger", "msg": _("Permit {0} expired on {1}. Renew to avoid penalties.").format(pr.get("permit_type") or "—", pr.expiry_date)})
				elif date_diff(exp, today_date) <= 7:
					alerts.append({"level": "warning", "msg": _("Permit {0} expires on {1}.").format(pr.get("permit_type") or "—", pr.expiry_date)})

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

		# 3. Overdue required documents
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
					alerts.append({"level": "danger", "msg": _("Document {0} was required on {1} and is overdue.").format(doc.get("document_type") or "—", date_req)})

		# 4. Documents expiring within 7 days
		for doc in (self.get("documents") or []):
			exp_date = doc.get("expiry_date")
			if not exp_date:
				continue
			exp = getdate(exp_date)
			if exp >= today_date and date_diff(exp, today_date) <= 7:
				alerts.append({"level": "info", "msg": _("Document {0} expires on {1}.").format(doc.get("document_type") or "—", exp_date)})

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
			from logistics.pricing_center.doctype.sales_quote.sales_quote import validate_one_off_quote_not_converted
			validate_one_off_quote_not_converted(self.sales_quote, self.doctype, self.name)

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

	def before_save(self):
		from logistics.utils.module_integration import run_propagate_on_link, set_billing_company_from_sales_quote
		run_propagate_on_link(self)
		set_billing_company_from_sales_quote(self)

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

	def _populate_charges_from_sales_quote(self):
		"""Populate charges from Sales Quote Customs when sales_quote is set."""
		if not self.sales_quote:
			return
		try:
			if not frappe.db.exists("Sales Quote", self.sales_quote):
				return
			sq = frappe.get_doc("Sales Quote", self.sales_quote)
			if not hasattr(sq, "customs") or not sq.customs:
				return
			meta = frappe.get_meta("Declaration Order Charges")
			charge_fields = [f.fieldname for f in meta.fields]
			common_fields = [
				"item_code", "item_name", "charge_type", "charge_category", "quantity", "uom",
				"currency", "unit_type", "minimum_quantity", "minimum_unit_rate", "minimum_charge",
				"maximum_charge", "base_amount", "base_quantity", "estimated_revenue",
				"cost_calculation_method", "cost_quantity", "cost_uom", "cost_currency", "unit_cost",
				"cost_unit_type", "cost_minimum_quantity", "cost_minimum_unit_rate", "cost_minimum_charge",
				"cost_maximum_charge", "cost_base_amount", "cost_base_quantity", "estimated_cost",
				"revenue_calc_notes", "cost_calc_notes", "charge_basis", "rate",
			]
			self.set("charges", [])
			for sq_charge in sq.customs:
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
		"customer", "company", "customs_authority", "branch", "cost_center", "profit_center",
		"declaration_type", "incoterm",
	]
	out = frappe.db.get_value("Sales Quote", sales_quote, fields, as_dict=True)
	return out or {}


@frappe.whitelist()
def populate_charges_from_sales_quote(docname=None, sales_quote=None):
	"""Populate charges from Sales Quote Customs. Called from client when sales_quote changes."""
	if not sales_quote:
		return {"charges": [], "charges_count": 0}
	try:
		if not frappe.db.exists("Sales Quote", sales_quote):
			return {"charges": [], "error": _("Sales Quote {0} does not exist.").format(sales_quote)}
		sq = frappe.get_doc("Sales Quote", sales_quote)
		if not hasattr(sq, "customs") or not sq.customs:
			return {"charges": [], "message": _("No customs charges found in Sales Quote: {0}").format(sales_quote)}
		meta = frappe.get_meta("Declaration Order Charges")
		charge_fields = [f.fieldname for f in meta.fields]
		common_fields = [
			"item_code", "item_name", "charge_type", "charge_category", "quantity", "uom",
			"currency", "unit_type", "minimum_quantity", "minimum_unit_rate", "minimum_charge",
			"maximum_charge", "base_amount", "base_quantity", "estimated_revenue",
			"cost_calculation_method", "cost_quantity", "cost_uom", "cost_currency", "unit_cost",
			"cost_unit_type", "cost_minimum_quantity", "cost_minimum_unit_rate", "cost_minimum_charge",
			"cost_maximum_charge", "cost_base_amount", "cost_base_quantity", "estimated_cost",
			"revenue_calc_notes", "cost_calc_notes", "charge_basis", "rate",
		]
		charges = []
		for sq_charge in sq.customs:
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
			if "charge_type" not in row or not row.get("charge_type"):
				row["charge_type"] = "Revenue"
			if row:
				charges.append(row)
		return {"charges": charges, "charges_count": len(charges)}
	except Exception as e:
		frappe.log_error(f"Error populating Declaration Order charges: {str(e)}")
		return {"charges": [], "error": str(e)}


@frappe.whitelist()
def create_declaration_order_from_sales_quote(sales_quote_name: str):
	"""
	Create a Declaration Order from a Sales Quote (One-off, with customs).
	Updates the Sales Quote status and converted_to_doc to the new Declaration Order.
	"""
	if not sales_quote_name:
		frappe.throw(_("Sales Quote is required."))
	sq = frappe.get_doc("Sales Quote", sales_quote_name)
	if sq.quotation_type != "One-off":
		frappe.throw(_("Only One-off Sales Quotes can create a Declaration Order."))
	if not getattr(sq, "customs", None) or not sq.customs:
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
	order._populate_charges_from_sales_quote()
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
