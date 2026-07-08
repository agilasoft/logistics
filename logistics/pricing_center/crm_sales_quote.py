# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""CRM → Sales Quote mapping (replaces ERPNext Quotation actions in the desk)."""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.mapper import get_mapped_doc
from frappe.utils import add_days, getdate, today

from logistics.pricing_center.doctype.pricing_center_settings.pricing_center_settings import (
	get_crm_sales_quote_settings,
	get_valid_until_offset,
)


def _default_company(source_company=None):
	if source_company:
		return source_company
	return (
		frappe.defaults.get_user_default("Company")
		or frappe.db.get_single_value("Global Defaults", "default_company")
	)


def _company_from_customer(customer):
	if customer.get("companies"):
		return customer.companies[0].company
	return _default_company()


def _apply_sales_quote_defaults(target, company=None):
	company = _default_company(company or getattr(target, "company", None))
	target.company = company
	target.date = target.date or today()
	target.quotation_type = target.quotation_type or "Regular"
	target.naming_series = target.naming_series or "SQU.#########"
	offset = get_valid_until_offset(company)
	target.valid_until = add_days(getdate(target.date), offset)


def _customer_from_lead(lead_name):
	if not lead_name:
		return None
	return frappe.db.get_value("Customer", {"lead_name": lead_name}, "name")


def _customer_from_prospect(prospect_name):
	if not prospect_name:
		return None
	return frappe.db.get_value("Customer", {"prospect_name": prospect_name}, "name")


def _customer_from_opportunity(source):
	opportunity_from = (source.opportunity_from or "").strip()
	party_name = (source.party_name or "").strip()
	if not party_name:
		return None
	if opportunity_from == "Customer":
		return party_name
	if opportunity_from == "Lead":
		return _customer_from_lead(party_name)
	if opportunity_from == "Prospect":
		return _customer_from_prospect(party_name)
	return None


def _throw_missing_customer(context_label):
	frappe.throw(
		_(
			"Create a Customer from this {0} before creating a Sales Quote, or enable the setting in Pricing Center Settings."
		).format(context_label),
		title=_("Customer Required"),
	)


def _throw_customer_auto_create_failed(party_doctype, party_name, error):
	from frappe.utils import get_link_to_form

	mandatory_fields = error.args[0].split(":")[1].split(",")
	customer = frappe.new_doc("Customer")
	mandatory_fields = [_(customer.meta.get_label(field.strip())) for field in mandatory_fields]
	frappe.local.message_log = []
	message = _("Could not auto create Customer due to the following missing mandatory field(s):") + "<br>"
	message += "<br><ul><li>" + "</li><li>".join(mandatory_fields) + "</li></ul>"
	message += _("Please create Customer from {0} {1}.").format(
		party_doctype, get_link_to_form(party_doctype, party_name)
	)
	frappe.throw(message, title=_("Mandatory Missing"))


def _create_customer_from_lead(lead_name, company=None):
	from erpnext.crm.doctype.lead.lead import _make_customer

	customer = _make_customer(lead_name, ignore_permissions=True)
	if company:
		customer.company = company
	elif not customer.company:
		customer.company = frappe.db.get_value("Lead", lead_name, "company")
	customer.flags.ignore_permissions = True
	try:
		customer.insert()
	except frappe.MandatoryError as error:
		_throw_customer_auto_create_failed("Lead", lead_name, error)
	return customer.name


def _create_customer_from_prospect(prospect_name, company=None):
	from erpnext.crm.doctype.prospect.prospect import make_customer as make_customer_from_prospect

	customer = make_customer_from_prospect(prospect_name)
	customer.prospect_name = prospect_name
	if company:
		customer.company = company
	elif not customer.company:
		customer.company = frappe.db.get_value("Prospect", prospect_name, "company")
	customer.flags.ignore_permissions = True
	try:
		customer.insert()
	except frappe.MandatoryError as error:
		_throw_customer_auto_create_failed("Prospect", prospect_name, error)
	return customer.name


def _resolve_customer_for_lead(lead_name, company=None):
	company = _default_company(company or frappe.db.get_value("Lead", lead_name, "company"))
	customer = _customer_from_lead(lead_name)
	if customer:
		return customer
	settings = get_crm_sales_quote_settings(company)
	if settings.allow_sales_quote_from_lead:
		return _create_customer_from_lead(lead_name, company)
	_throw_missing_customer(_("Lead"))


def _resolve_customer_for_prospect(prospect_name, company=None):
	company = _default_company(company or frappe.db.get_value("Prospect", prospect_name, "company"))
	customer = _customer_from_prospect(prospect_name)
	if customer:
		return customer
	settings = get_crm_sales_quote_settings(company)
	if settings.allow_sales_quote_from_prospect:
		return _create_customer_from_prospect(prospect_name, company)
	_throw_missing_customer(_("Prospect"))


def _resolve_customer_for_opportunity(source):
	company = _default_company(source.company)
	customer = _customer_from_opportunity(source)
	if customer:
		return customer

	opportunity_from = (source.opportunity_from or "").strip()
	party_name = (source.party_name or "").strip()
	if opportunity_from == "Lead" and party_name:
		return _resolve_customer_for_lead(party_name, company)
	if opportunity_from == "Prospect" and party_name:
		return _resolve_customer_for_prospect(party_name, company)
	_throw_missing_customer(_("Opportunity"))


@frappe.whitelist()
def make_sales_quote_from_opportunity(source_name, target_doc=None):
	"""Open a Sales Quote mapped from an Opportunity (CRM Create → Sales Quote)."""
	source = frappe.get_doc("Opportunity", source_name)
	customer = _resolve_customer_for_opportunity(source)

	def set_missing_values(source, target):
		target.customer = customer
		target.opportunity = source.name
		if source.opportunity_from == "Lead" and source.party_name:
			target.lead = source.party_name
		if source.opportunity_from == "Prospect" and source.party_name and target.meta.get_field("prospect"):
			target.prospect = source.party_name
		_apply_sales_quote_defaults(target, source.company)
		if source.opportunity_owner and target.meta.get_field("sales_rep"):
			employee = frappe.db.get_value(
				"Employee",
				{"user_id": source.opportunity_owner, "status": "Active"},
				"name",
			)
			if employee:
				target.sales_rep = employee

	return get_mapped_doc(
		"Opportunity",
		source_name,
		{"Opportunity": {"doctype": "Sales Quote"}},
		target_doc,
		set_missing_values,
	)


@frappe.whitelist()
def make_sales_quote_from_lead(source_name, target_doc=None):
	"""Open a Sales Quote mapped from a Lead (CRM Create → Sales Quote)."""
	customer = _resolve_customer_for_lead(source_name)

	def set_missing_values(source, target):
		target.customer = customer
		target.lead = source.name
		_apply_sales_quote_defaults(target, source.company)

	return get_mapped_doc(
		"Lead",
		source_name,
		{"Lead": {"doctype": "Sales Quote"}},
		target_doc,
		set_missing_values,
	)


@frappe.whitelist()
def make_sales_quote_from_prospect(source_name, target_doc=None):
	"""Open a Sales Quote mapped from a Prospect (CRM Create → Sales Quote)."""
	customer = _resolve_customer_for_prospect(source_name)

	def set_missing_values(source, target):
		target.customer = customer
		if target.meta.get_field("prospect"):
			target.prospect = source.name
		_apply_sales_quote_defaults(target, source.company)

	return get_mapped_doc(
		"Prospect",
		source_name,
		{"Prospect": {"doctype": "Sales Quote"}},
		target_doc,
		set_missing_values,
	)


@frappe.whitelist()
def make_sales_quote_from_customer(source_name, target_doc=None):
	"""Open a Sales Quote mapped from a Customer (CRM/Selling Create → Sales Quote)."""
	def set_missing_values(source, target):
		target.customer = source.name
		if source.lead_name:
			target.lead = source.lead_name
		if source.prospect_name and target.meta.get_field("prospect"):
			target.prospect = source.prospect_name
		_apply_sales_quote_defaults(target, _company_from_customer(source))

	return get_mapped_doc(
		"Customer",
		source_name,
		{"Customer": {"doctype": "Sales Quote"}},
		target_doc,
		set_missing_values,
	)
