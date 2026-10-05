# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Standard costing for internal tariff cost charges.

A charge qualifies when its cost side is marked Internal and priced from a tariff.
Those lines are not supplier invoices: Post Standard Costs records

    Dr Item.custom_standard_cost_account
    Cr Item.custom_applied_standard_cost_account

for the tariff cost (company currency).
"""

from __future__ import annotations

import frappe
from frappe import _
from frappe.utils import cint, flt, now, today

CHARGE_TABLES = ("charges", "consolidation_charges")


def is_internal_tariff_cost_charge(charge) -> bool:
	"""True when this charge's cost is an internal tariff (checkbox + use tariff in cost)."""
	if not charge:
		return False
	if (getattr(charge, "charge_type", None) or "").strip().lower() == "disbursement":
		return False
	return bool(cint(getattr(charge, "cost_internal", 0))) and bool(
		cint(getattr(charge, "use_tariff_in_cost", 0))
	)


def _iter_charge_rows(job):
	for fieldname in CHARGE_TABLES:
		rows = job.get(fieldname) if hasattr(job, "get") else None
		if not rows:
			continue
		for row in rows:
			yield row


def _charge_item_code(charge) -> str | None:
	return getattr(charge, "item_code", None) or getattr(charge, "charge_item", None)


def _tariff_cost_in_company_currency(job, charge, posting_date: str) -> float:
	from logistics.job_management.recognition_engine import resolve_charge_row_cost

	amount = flt(resolve_charge_row_cost(charge, prefer_actual=False))
	if amount <= 0:
		return 0.0
	company = getattr(job, "company", None)
	company_currency = (
		frappe.get_cached_value("Company", company, "default_currency") if company else None
	)
	cost_currency = getattr(charge, "cost_currency", None) or company_currency
	if not company_currency or not cost_currency or cost_currency == company_currency:
		return amount
	from logistics.invoice_integration.billing_currency import charge_to_company_rate_buying

	rate = charge_to_company_rate_buying(charge, cost_currency, company_currency, posting_date)
	return flt(amount * rate)


def _charge_label(charge) -> str:
	return (
		_charge_item_code(charge)
		or getattr(charge, "item_name", None)
		or getattr(charge, "description", None)
		or _("Charge")
	)


def _stamp_posted(charge, journal_entry: str) -> None:
	meta = frappe.get_meta(charge.doctype)
	if meta.get_field("standard_cost_posted"):
		charge.standard_cost_posted = 1
	if meta.get_field("standard_cost_posted_at"):
		charge.standard_cost_posted_at = now()
	if meta.get_field("journal_entry_reference"):
		charge.journal_entry_reference = journal_entry


@frappe.whitelist()
def post_standard_costs_for_job(doctype: str, docname: str) -> dict:
	"""Post internal tariff standard costs for one job document."""
	job = frappe.get_doc(doctype, docname)
	return post_internal_tariff_standard_costs(job)


def post_internal_tariff_standard_costs(job) -> dict:
	"""Create one Journal Entry for unposted internal tariff cost charges on ``job``."""
	from logistics.utils.menu_permission import assert_perm

	assert_perm(job.doctype, "write", doc=job)
	assert_perm("Journal Entry", "create")

	if not getattr(job, "company", None):
		return {"ok": False, "message": _("Company is required to post standard costs.")}

	posting_date = today()
	to_post = []
	skipped = []
	for charge in _iter_charge_rows(job):
		if not is_internal_tariff_cost_charge(charge):
			continue
		if cint(getattr(charge, "standard_cost_posted", 0)):
			continue
		meta = frappe.get_meta(charge.doctype)
		if not meta.get_field("standard_cost_posted"):
			skipped.append(
				_("{0}: standard cost posting is not available on this charge.").format(
					_charge_label(charge)
				)
			)
			continue
		item_code = _charge_item_code(charge)
		if not item_code:
			skipped.append(_("{0}: item is required.").format(_charge_label(charge)))
			continue
		try:
			amount = _tariff_cost_in_company_currency(job, charge, posting_date)
		except Exception as exc:
			skipped.append(_("{0}: {1}").format(_charge_label(charge), exc))
			continue
		if amount <= 0:
			skipped.append(_("{0}: tariff cost is zero.").format(_charge_label(charge)))
			continue
		item = frappe.get_doc("Item", item_code)
		debit_account = item.get("custom_standard_cost_account")
		credit_account = item.get("custom_applied_standard_cost_account")
		if not debit_account or not credit_account:
			skipped.append(
				_("{0}: set Standard Cost Account and Applied Standard Cost Account on the Item.").format(
					item_code
				)
			)
			continue
		to_post.append(
			{
				"charge": charge,
				"item_code": item_code,
				"amount": amount,
				"debit_account": debit_account,
				"credit_account": credit_account,
			}
		)

	if not to_post:
		message = _("No internal tariff costs to post.")
		if skipped:
			message = message + "\n" + "\n".join(skipped)
		return {"ok": False, "message": message, "skipped": skipped}

	cost_center = getattr(job, "cost_center", None)
	profit_center = getattr(job, "profit_center", None)
	job_number = getattr(job, "job_number", None)
	branch = getattr(job, "branch", None)

	je = frappe.new_doc("Journal Entry")
	je.voucher_type = "Journal Entry"
	je.posting_date = posting_date
	je.company = job.company
	je.branch = branch
	je.cost_center = cost_center
	je.profit_center = profit_center
	je.job_number = job_number
	je.user_remark = _("Standard costs for {0} {1}").format(job.doctype, job.name)

	total_amount = 0.0
	for row in to_post:
		amount = row["amount"]
		total_amount += amount
		remark_item = row["item_code"]
		je.append(
			"accounts",
			{
				"account": row["debit_account"],
				"debit_in_account_currency": amount,
				"credit_in_account_currency": 0,
				"cost_center": cost_center,
				"profit_center": profit_center,
				"job_number": job_number,
				"item": remark_item,
				"against_account": row["credit_account"],
				"user_remark": _("Standard cost for {0} ({1} {2})").format(
					remark_item, job.doctype, job.name
				),
			},
		)
		je.append(
			"accounts",
			{
				"account": row["credit_account"],
				"debit_in_account_currency": 0,
				"credit_in_account_currency": amount,
				"cost_center": cost_center,
				"profit_center": profit_center,
				"job_number": job_number,
				"item": remark_item,
				"against_account": row["debit_account"],
				"user_remark": _("Applied standard cost for {0} ({1} {2})").format(
					remark_item, job.doctype, job.name
				),
			},
		)

	je.insert(ignore_permissions=True)
	je.submit()

	for row in to_post:
		_stamp_posted(row["charge"], je.name)

	flags = getattr(job, "flags", None)
	if flags is not None:
		flags.ignore_validate_update_after_submit = True
		flags.ignore_permissions = True
	job.save(ignore_permissions=True)
	frappe.db.commit()

	message = _("Journal Entry {0} posted for standard costs.").format(je.name)
	if skipped:
		message = message + "\n" + "\n".join(skipped)
	return {
		"ok": True,
		"message": message,
		"journal_entry": je.name,
		"total_amount": total_amount,
		"charges_posted": len(to_post),
		"skipped": skipped,
	}
