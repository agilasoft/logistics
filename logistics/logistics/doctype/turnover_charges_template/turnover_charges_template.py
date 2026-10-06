# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

from __future__ import annotations

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint

PARENT_SERVICE = {
	"Air Booking": "Air",
	"Air Shipment": "Air",
	"Sea Booking": "Sea",
	"Sea Shipment": "Sea",
}

CHARGE_CHILD = {
	"Air Booking": "Air Booking Charges",
	"Air Shipment": "Air Shipment Charges",
	"Sea Booking": "Sea Booking Charges",
	"Sea Shipment": "Sea Shipment Charges",
}

TEMPLATE_CHARGE_FIELDS = (
	"service_type",
	"item_code",
	"item_name",
	"description",
	"charge_type",
	"charge_category",
	"revenue_calculation_method",
	"quantity",
	"uom",
	"currency",
	"unit_rate",
	"unit_type",
	"minimum_quantity",
	"minimum_unit_rate",
	"minimum_charge",
	"maximum_charge",
	"base_amount",
	"base_quantity",
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
	"bill_to",
	"pay_to",
	"use_tariff_in_revenue",
	"revenue_tariff",
	"use_tariff_in_cost",
	"cost_tariff",
)


class TurnoverChargesTemplate(Document):
	def validate(self):
		if not self.get("charges"):
			frappe.throw(_("Add at least one charge to the Turnover Charges Template."))
		for row in self.charges:
			if not row.item_code:
				frappe.throw(_("Each Turnover Charges Template row needs an Item."))


def turnover_shipment_skips_sales_quote(doc) -> bool:
	"""Turnover bookings and shipments do not need a Sales Quote."""
	return bool(cint(getattr(doc, "is_turnover_shipment", 0)))


def copy_turnover_shipment_fields(source, target) -> None:
	"""Copy the turnover flag and template from a booking onto its shipment."""
	if not hasattr(target, "is_turnover_shipment"):
		return
	target.is_turnover_shipment = cint(getattr(source, "is_turnover_shipment", 0))
	target.turnover_charges_template = getattr(source, "turnover_charges_template", None) or None


def assert_turnover_template_ready(doc) -> None:
	"""Require a template and at least one charge when Turnover Shipment is checked."""
	if not turnover_shipment_skips_sales_quote(doc):
		return
	if not (getattr(doc, "turnover_charges_template", None) or "").strip():
		frappe.throw(
			_("Turnover Charges Template is required for a Turnover Shipment."),
			title=_("Turnover Shipment"),
		)
	if not doc.get("charges"):
		frappe.throw(
			_("Charges are required. Select a Turnover Charges Template to load them."),
			title=_("Turnover Shipment"),
		)


@frappe.whitelist()
def get_turnover_template_charge_rows(template: str, parent_doctype: str):
	"""Map a Turnover Charges Template onto the parent document's charge child rows."""
	parent_doctype = (parent_doctype or "").strip()
	if parent_doctype not in PARENT_SERVICE:
		frappe.throw(_("Turnover Charges Template cannot be applied to {0}.").format(parent_doctype))
	frappe.has_permission(parent_doctype, "read", throw=True)
	frappe.has_permission("Turnover Charges Template", "read", throw=True)
	return charge_rows_from_template(template, parent_doctype)


def sync_turnover_shipment_charges(doc) -> None:
	"""Replace charges when the template changes. Leave existing charges on first save.

	Unchecking Turnover clears the template link and keeps charges already on the document.
	Clearing the template while Turnover stays checked removes the charge rows.
	A new document that already has charges (form fetch or booking conversion) is left as-is.
	A new document with a template and no charges loads the template, so API saves match the form.
	"""
	if getattr(doc, "doctype", None) not in PARENT_SERVICE:
		return
	if doc.docstatus == 1:
		return

	if not turnover_shipment_skips_sales_quote(doc):
		if getattr(doc, "turnover_charges_template", None):
			doc.turnover_charges_template = None
		return

	template_name = (getattr(doc, "turnover_charges_template", None) or "").strip()
	previous = doc.get_doc_before_save()
	if previous is None:
		if template_name and not doc.get("charges"):
			replace_charges_from_turnover_template(doc, template_name)
		return

	previous_template = (previous.get("turnover_charges_template") or "").strip()
	if template_name == previous_template:
		return
	if not template_name:
		doc.set("charges", [])
		return
	replace_charges_from_turnover_template(doc, template_name)


def charge_rows_from_template(template_name: str, parent_doctype: str) -> list[dict]:
	template_name = (template_name or "").strip()
	if not template_name:
		frappe.throw(_("Turnover Charges Template is required."))
	if not frappe.db.exists("Turnover Charges Template", template_name):
		frappe.throw(_("Turnover Charges Template {0} does not exist.").format(template_name))

	template = frappe.get_doc("Turnover Charges Template", template_name)
	if not cint(template.is_active):
		frappe.throw(_("Turnover Charges Template {0} is inactive.").format(template_name))

	expected = PARENT_SERVICE[parent_doctype]
	if template.service != expected:
		frappe.throw(
			_("Turnover Charges Template {0} is for {1} shipments, not {2}.").format(
				template_name, template.service, expected
			)
		)

	child_doctype = CHARGE_CHILD[parent_doctype]
	meta = frappe.get_meta(child_doctype)
	rows = []
	for line in template.get("charges") or []:
		row = {}
		for fieldname in TEMPLATE_CHARGE_FIELDS:
			if not meta.has_field(fieldname):
				continue
			value = getattr(line, fieldname, None)
			if value not in (None, ""):
				row[fieldname] = value
		if not row.get("service_type"):
			row["service_type"] = expected
		if not row.get("charge_type"):
			row["charge_type"] = "Revenue"
		if not row.get("revenue_calculation_method") and row.get("charge_type") != "Cost":
			row["revenue_calculation_method"] = "Per Unit"
		if not row.get("item_code"):
			frappe.throw(_("Turnover Charges Template {0} has a row without an Item.").format(template_name))
		rows.append(row)

	if not rows:
		frappe.throw(_("Turnover Charges Template {0} has no charges.").format(template_name))
	return rows


def replace_charges_from_turnover_template(doc, template_name: str) -> None:
	from logistics.utils.charges_calculation import compute_charge_row_estimates

	rows = charge_rows_from_template(template_name, doc.doctype)
	doc.set("charges", [])
	for row in rows:
		child = doc.append("charges", row)
		compute_charge_row_estimates(child, doc)
