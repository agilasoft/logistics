# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Journal Entry posting for container deposits per design:
- Pending carrier pay: Dr clearing, Cr Debtors (party Customer).
- Pending refund from carrier: Dr Debtors (party Customer), Cr clearing.
- Bank settlement: reversing / clearing pairs against Debtors and Bank.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate


def _settings():
	return frappe.get_single("Logistics Settings")


def _company_for_row(container_doc, deposit_row):
	company = deposit_row.get("company") or getattr(container_doc, "company", None)
	if company:
		return company
	if deposit_row.get("job_number"):
		jc = frappe.db.get_value("Job Number", deposit_row.job_number, "company")
		if jc:
			return jc
	s = _settings()
	if s.get("container_deposit_default_company"):
		return s.container_deposit_default_company
	return (
		frappe.defaults.get_user_default("Company")
		or frappe.db.get_single_value("Global Defaults", "default_company")
		or (frappe.get_all("Company", filters={}, limit_page_length=1, pluck="name") or [None])[0]
	)


def _debtors_account(company):
	s = _settings()
	if s.get("container_deposit_debtors_account"):
		return s.container_deposit_debtors_account
	acc = frappe.db.get_value("Company", company, "default_receivable_account")
	if not acc:
		frappe.throw(_("Set Default Receivable Account for Company {0} or Debtors override in Logistics Settings.").format(company))
	return acc


def _clearing_account():
	s = _settings()
	if not s.get("container_deposit_clearing_account"):
		frappe.throw(_("Set Deposit clearing account in Logistics Settings (Container deposits section)."))
	return s.container_deposit_clearing_account


def _bank_account(company):
	acc = frappe.db.get_value("Company", company, "default_bank_account")
	if not acc:
		frappe.throw(_("Set default bank account for Company {0}.").format(company))
	return acc


def _job_dimensions(job_number):
	if not job_number:
		return {}
	row = frappe.db.get_value(
		"Job Number",
		job_number,
		["cost_center", "profit_center"],
		as_dict=True,
	)
	if not row:
		return {}
	out = {}
	if row.get("cost_center"):
		out["cost_center"] = row.cost_center
	if row.get("profit_center"):
		out["profit_center"] = row.profit_center
	return out


def _require_job_number_if_enabled(row):
	s = _settings()
	if not s.require_job_number_on_container_deposits:
		return
	if not row.get("job_number"):
		frappe.throw(_("Job Number is required on this deposit line (Logistics Settings)."), title=_("Container deposit"))


def _require_debtor_for_ar(row):
	if not row.get("debtor_party"):
		frappe.throw(_("Debtor (Customer) is required for this posting."), title=_("Container deposit"))


def _append_je_line(je, account, debit, credit, party_type=None, party=None, job_number=None, user_remark=None):
	row = {
		"account": account,
		"debit_in_account_currency": flt(debit),
		"credit_in_account_currency": flt(credit),
	}
	if party_type and party:
		row["party_type"] = party_type
		row["party"] = party
	if job_number:
		row["job_number"] = job_number
	row.update(_job_dimensions(job_number))
	je.append("accounts", row)


def _assert_not_linked(row):
	if row.get("reference_doctype") == "Journal Entry" and row.get("reference_name"):
		if frappe.db.get_value("Journal Entry", row.reference_name, "docstatus") == 1:
			frappe.throw(_("This line is already linked to submitted Journal Entry {0}.").format(row.reference_name))


def assert_refund_readiness(container_doc):
	"""Raise if mandatory refund documents are not Received or Waived with permission."""
	for line in container_doc.get("refund_readiness") or []:
		if not frappe.utils.cint(line.get("mandatory")):
			continue
		if line.status == "Received":
			continue
		if line.status == "Waived":
			if not (line.waiver_reason or "").strip():
				frappe.throw(_("Waiver reason is required on all Waived mandatory lines."))
			if not _user_can_waive_refund_docs():
				frappe.throw(_("You are not allowed to waive refund document requirements."), title=_("Refund readiness"))
			continue
		frappe.throw(
			_("Refund document '{0}' must be Received or Waived before this action.").format(line.requirement_name or _("(unnamed)")),
			title=_("Refund readiness"),
		)


def _user_can_waive_refund_docs():
	s = _settings()
	raw = (s.get("container_deposit_refund_waiver_roles") or "").strip()
	roles = [r.strip() for r in raw.split(",") if r.strip()]
	if not roles:
		roles = ["System Manager"]
	user_roles = set(frappe.get_roles(frappe.session.user))
	return bool(user_roles.intersection(roles))


@frappe.whitelist()
def materialize_refund_readiness(container_name):
	"""Append template-based refund readiness rows not already present."""
	doc = frappe.get_doc("Container", container_name)
	settings = _settings()
	existing = {r.requirement_name for r in doc.get("refund_readiness") or [] if r.requirement_name}
	owner_sl = doc.get("owner_carrier")
	for tpl in settings.get("container_refund_requirements") or []:
		if not tpl.requirement_name or tpl.requirement_name in existing:
			continue
		if tpl.get("shipping_line") and owner_sl and tpl.shipping_line != owner_sl:
			continue
		doc.append(
			"refund_readiness",
			{
				"requirement_name": tpl.requirement_name,
				"mandatory": 1 if tpl.mandatory_for_refund else 0,
				"attachment_required": 1 if tpl.attachment_required else 0,
				"status": "Pending",
			},
		)
	doc.save()
	return doc.name


@frappe.whitelist()
def create_pending_carrier_pay_je(container_name, child_row_name):
	"""Dr clearing, Cr Debtors — pending payment to carrier (AR policy)."""
	container = frappe.get_doc("Container", container_name)
	row = _get_deposit_row(container, child_row_name)
	_require_job_number_if_enabled(row)
	_require_debtor_for_ar(row)
	_assert_not_linked(row)
	amt = flt(row.deposit_amount)
	if amt <= 0:
		frappe.throw(_("Deposit amount must be positive."), title=_("Container deposit"))
	company = _company_for_row(container, row)
	clearing = _clearing_account()
	debtors = _debtors_account(company)

	je = frappe.new_doc("Journal Entry")
	je.company = company
	je.posting_date = row.deposit_date or getdate(nowdate())
	je.voucher_type = "Journal Entry"
	je.user_remark = _("Container deposit pending carrier pay {0}").format(container_name)

	_append_je_line(je, clearing, amt, 0, job_number=row.get("job_number"))
	_append_je_line(je, debtors, 0, amt, party_type="Customer", party=row.debtor_party, job_number=row.get("job_number"))

	je.insert()
	je.submit()

	frappe.db.set_value(
		"Container Deposit",
		row.name,
		{"reference_doctype": "Journal Entry", "reference_name": je.name},
	)

	return je.name


@frappe.whitelist()
def create_pending_refund_from_carrier_je(container_name, child_row_name):
	"""Dr Debtors, Cr clearing — carrier refund requested, not yet at bank."""
	container = frappe.get_doc("Container", container_name)
	assert_refund_readiness(container)
	row = _get_deposit_row(container, child_row_name)
	_require_job_number_if_enabled(row)
	_require_debtor_for_ar(row)
	_assert_not_linked(row)
	amt = flt(row.refund_amount or row.deposit_amount)
	if amt <= 0:
		frappe.throw(_("Refund amount (or deposit amount) must be positive."), title=_("Container deposit"))
	company = _company_for_row(container, row)
	clearing = _clearing_account()
	debtors = _debtors_account(company)

	je = frappe.new_doc("Journal Entry")
	je.company = company
	je.posting_date = row.refund_date or row.deposit_date or getdate(nowdate())
	je.voucher_type = "Journal Entry"
	je.user_remark = _("Container deposit pending refund from carrier {0}").format(container_name)

	_append_je_line(je, debtors, amt, 0, party_type="Customer", party=row.debtor_party, job_number=row.get("job_number"))
	_append_je_line(je, clearing, 0, amt, job_number=row.get("job_number"))

	je.insert()
	je.submit()

	frappe.db.set_value(
		"Container Deposit",
		row.name,
		{"reference_doctype": "Journal Entry", "reference_name": je.name},
	)

	return je.name


@frappe.whitelist()
def create_bank_settle_carrier_pay_je(container_name, child_row_name):
	"""After pending carrier pay (Cr Debtors): Dr Debtors, Cr Bank."""
	container = frappe.get_doc("Container", container_name)
	row = _get_deposit_row(container, child_row_name)
	_require_debtor_for_ar(row)
	amt = flt(row.deposit_amount)
	if amt <= 0:
		frappe.throw(_("Deposit amount must be positive."), title=_("Container deposit"))
	company = _company_for_row(container, row)
	debtors = _debtors_account(company)
	bank = _bank_account(company)

	je = frappe.new_doc("Journal Entry")
	je.company = company
	je.posting_date = getdate(nowdate())
	je.voucher_type = "Journal Entry"
	je.user_remark = _("Container deposit bank pay carrier {0}").format(container_name)

	_append_je_line(je, debtors, amt, 0, party_type="Customer", party=row.debtor_party, job_number=row.get("job_number"))
	_append_je_line(je, bank, 0, amt, job_number=row.get("job_number"))

	je.insert()
	je.submit()
	return je.name


@frappe.whitelist()
def create_bank_receive_carrier_refund_je(container_name, child_row_name):
	"""After pending refund (Dr Debtors): Dr Bank, Cr Debtors."""
	container = frappe.get_doc("Container", container_name)
	row = _get_deposit_row(container, child_row_name)
	_require_debtor_for_ar(row)
	amt = flt(row.refund_amount or row.deposit_amount)
	if amt <= 0:
		frappe.throw(_("Refund amount must be positive."), title=_("Container deposit"))
	company = _company_for_row(container, row)
	debtors = _debtors_account(company)
	bank = _bank_account(company)

	je = frappe.new_doc("Journal Entry")
	je.company = company
	je.posting_date = getdate(nowdate())
	je.voucher_type = "Journal Entry"
	je.user_remark = _("Container deposit bank receive carrier refund {0}").format(container_name)

	_append_je_line(je, bank, amt, 0, job_number=row.get("job_number"))
	_append_je_line(je, debtors, 0, amt, party_type="Customer", party=row.debtor_party, job_number=row.get("job_number"))

	je.insert()
	je.submit()
	return je.name


def _get_deposit_row(container_doc, child_row_name):
	for r in container_doc.get("deposits") or []:
		if r.name == child_row_name:
			return r
	frappe.throw(_("Deposit row not found."), title=_("Container deposit"))


def sync_deposit_header_from_child_rows(container_doc):
	"""Roll up child lines into header summary fields."""
	rows = container_doc.get("deposits") or []
	net = 0
	cur = None
	last_paid = None
	for r in rows:
		ev = r.get("event_type") or ""
		amt = flt(r.deposit_amount)
		ref = flt(r.refund_amount)
		if ev in ("Customer Receipt", "Pay Carrier"):
			net += amt
		elif ev in ("Refund From Carrier", "Refund To Customer"):
			net -= ref or amt
		elif ev == "Forfeit":
			net -= ref or amt
		if r.get("deposit_currency"):
			cur = r.deposit_currency
		if r.get("deposit_date") and amt:
			last_paid = r.deposit_date
	container_doc.deposit_amount = max(net, 0)
	if cur:
		container_doc.deposit_currency = cur
	if last_paid:
		container_doc.deposit_paid_date = last_paid


def resolve_default_job_number_for_container(container_name):
	jobs = frappe.db.sql(
		"""
		SELECT DISTINCT s.job_number
		FROM `tabSea Freight Containers` sfc
		INNER JOIN `tabSea Shipment` s ON s.name = sfc.parent AND sfc.parenttype = 'Sea Shipment'
		WHERE sfc.container = %s AND IFNULL(s.job_number,'') != ''
		""",
		(container_name,),
		pluck=True,
	)
	if len(jobs) == 1:
		return jobs[0]
	return None
