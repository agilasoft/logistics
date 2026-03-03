# Copyright (c) 2025, Agilasoft Cloud Technologies Inc. and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe import _


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
					alerts.append({"level": "warning", "msg": _("Document {0} was required on {1} and is overdue.").format(doc.get("document_type") or "—", date_req)})

		# 4. Documents expiring within 7 days
		for doc in (self.get("documents") or []):
			exp_date = doc.get("expiry_date")
			if not exp_date:
				continue
			exp = getdate(exp_date)
			if exp >= today_date and date_diff(exp, today_date) <= 7:
				alerts.append({"level": "info", "msg": _("Document {0} expires on {1}.").format(doc.get("document_type") or "—", exp_date)})

		return alerts

	def before_save(self):
		from logistics.utils.module_integration import run_propagate_on_link
		run_propagate_on_link(self)

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
				"item_code", "item_name", "calculation_method", "quantity", "uom",
				"currency", "unit_rate", "unit_type", "minimum_quantity", "minimum_charge",
				"maximum_charge", "base_amount", "estimated_revenue", "cost_calculation_method",
				"cost_quantity", "cost_uom", "cost_currency", "unit_cost", "cost_unit_type",
				"cost_minimum_quantity", "cost_minimum_charge", "cost_maximum_charge",
				"cost_base_amount", "estimated_cost", "revenue_calc_notes", "cost_calc_notes",
			]
			self.set("charges", [])
			for sq_charge in sq.customs:
				row = self.append("charges", {})
				for field in common_fields:
					if field in charge_fields and hasattr(sq_charge, field):
						val = getattr(sq_charge, field, None)
						if val is not None:
							row.set(field, val)
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
			"item_code", "item_name", "calculation_method", "quantity", "uom",
			"currency", "unit_rate", "unit_type", "minimum_quantity", "minimum_charge",
			"maximum_charge", "base_amount", "estimated_revenue", "cost_calculation_method",
			"cost_quantity", "cost_uom", "cost_currency", "unit_cost", "cost_unit_type",
			"cost_minimum_quantity", "cost_minimum_charge", "cost_maximum_charge",
			"cost_base_amount", "estimated_cost", "revenue_calc_notes", "cost_calc_notes",
		]
		charges = []
		for sq_charge in sq.customs:
			row = {}
			for field in common_fields:
				if field in charge_fields and hasattr(sq_charge, field):
					val = getattr(sq_charge, field, None)
					if val is not None:
						row[field] = val
			if row:
				charges.append(row)
		return {"charges": charges, "charges_count": len(charges)}
	except Exception as e:
		frappe.log_error(f"Error populating Declaration Order charges: {str(e)}")
		return {"charges": [], "error": str(e)}
