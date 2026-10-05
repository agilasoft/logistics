# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""Initialize Sales Quote charges from an entire Tariff schedule.

Tariff charge lines are filtered with the same scope / routing parameters as the Sales Quote
(Service Scope header and Linked Services), using blank-or-equal matching on each parameter field.
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint

from logistics.utils.tariff_charge_copy import (
	_tariff_is_valid_on_date,
	_tariff_matches_job_customer,
	effective_sales_quote_scope_for_tariff,
	fetch_eligible_tariff_names_for_sales_quote,
	filter_tariff_charge_rows_for_sales_quote,
	gcfts_list_filters_payload,
	sales_quote_customer,
	tariff_charge_row_as_sales_quote_charge_dict,
)

_PREVIEW_FIELDS = (
	"item_code",
	"item_name",
	"service_type",
	"charge_group",
	"charge_category",
	"revenue_calculation_method",
	"unit_rate",
	"currency",
	"cost_calculation_method",
	"unit_cost",
	"cost_currency",
	"origin_port",
	"destination_port",
	"shipping_line",
	"airline",
)


def _charge_preview_dict(charge_dict: dict) -> dict:
	return {k: charge_dict.get(k) for k in _PREVIEW_FIELDS if charge_dict.get(k) is not None}


@frappe.whitelist()
def list_tariffs_for_sales_quote(docname: str, filter_overrides=None):
	if not docname:
		frappe.throw(_("Sales Quote is required."))
	doc = frappe.get_doc("Sales Quote", docname)
	frappe.has_permission("Sales Quote", "read", doc=doc, throw=True)

	customer = sales_quote_customer(doc)
	if not customer:
		return {
			"tariffs": [],
			"message": _("Set Customer before loading tariffs."),
			"filters": None,
		}

	scope = effective_sales_quote_scope_for_tariff(doc, filter_overrides)
	filters_payload = gcfts_list_filters_payload(doc, scope)
	names = fetch_eligible_tariff_names_for_sales_quote(doc, filter_overrides=filter_overrides)

	if not names:
		return {
			"tariffs": [],
			"message": _("No matching tariffs for this Sales Quote scope."),
			"filters": filters_payload,
		}

	fields = [
		"name",
		"tariff_name",
		"tariff_type",
		"customer",
		"valid_from",
		"valid_to",
		"description",
		"total_rates",
	]
	rows = frappe.get_all("Tariff", filters={"name": ["in", names]}, fields=fields, order_by="modified desc")
	order = {n: i for i, n in enumerate(names)}
	rows.sort(key=lambda r: order.get(r.name, 9999))
	return {"tariffs": rows, "message": None, "filters": filters_payload}


@frappe.whitelist()
def preview_tariff_schedule_for_sales_quote(docname: str, tariff_name: str, filter_overrides=None):
	if not docname or not tariff_name:
		return {"error": _("Invalid arguments.")}

	doc = frappe.get_doc("Sales Quote", docname)
	frappe.has_permission("Sales Quote", "read", doc=doc, throw=True)

	if not frappe.db.exists("Tariff", tariff_name):
		return {"error": _("Tariff {0} does not exist.").format(tariff_name)}

	customer = sales_quote_customer(doc)
	if not customer:
		return {"error": _("Set Customer on this Sales Quote first.")}

	tariff_doc = frappe.get_doc("Tariff", tariff_name)
	if not _tariff_is_valid_on_date(tariff_doc):
		return {"error": _("Tariff {0} is not active or is outside its validity period.").format(tariff_name)}
	if not _tariff_matches_job_customer(tariff_doc, customer):
		return {"error": _("Tariff {0} does not match this quote's customer.").format(tariff_name)}

	rows = filter_tariff_charge_rows_for_sales_quote(doc, tariff_doc, filter_overrides)
	if not rows:
		return {
			"error": _(
				"Tariff {0} has no charge lines matching this Sales Quote's scope parameters."
			).format(tariff_name),
		}

	charges = []
	for row in rows:
		charge_dict = tariff_charge_row_as_sales_quote_charge_dict(row, tariff_name)
		charges.append(_charge_preview_dict(charge_dict))

	return {"charges": charges, "charges_count": len(charges)}


@frappe.whitelist()
def apply_tariff_schedule_to_sales_quote(
	docname: str, tariff_name: str, filter_overrides=None, replace_charges: int = 1
):
	if not docname or not tariff_name:
		frappe.throw(_("Invalid arguments."))

	doc = frappe.get_doc("Sales Quote", docname)
	frappe.has_permission("Sales Quote", "write", doc=doc, throw=True)

	if doc.docstatus != 0:
		frappe.throw(_("Only draft Sales Quotes can load charges from a tariff."))

	customer = sales_quote_customer(doc)
	if not customer:
		frappe.throw(_("Set Customer on this Sales Quote first."))

	tariff_doc = frappe.get_doc("Tariff", tariff_name)
	if not _tariff_is_valid_on_date(tariff_doc):
		frappe.throw(_("Tariff {0} is not active or is outside its validity period.").format(tariff_name))
	if not _tariff_matches_job_customer(tariff_doc, customer):
		frappe.throw(_("Tariff {0} does not match this quote's customer.").format(tariff_name))

	rows = filter_tariff_charge_rows_for_sales_quote(doc, tariff_doc, filter_overrides)
	if not rows:
		frappe.throw(
			_(
				"Tariff {0} has no charge lines matching this Sales Quote's scope parameters."
			).format(tariff_name),
			title=_("Cannot apply tariff"),
		)

	if cint(replace_charges):
		doc.set("charges", [])

	for row in rows:
		charge_dict = tariff_charge_row_as_sales_quote_charge_dict(row, tariff_name)
		doc.append("charges", charge_dict)

	doc._sync_tariff_rates_and_breaks_on_charges()
	doc.save()

	return {
		"success": True,
		"message": _("Applied {0} charge line(s) from Tariff {1}.").format(len(rows), tariff_name),
		"name": doc.name,
		"charges_count": len(doc.get("charges") or []),
	}
