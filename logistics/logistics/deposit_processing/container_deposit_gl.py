# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Container deposit (PI-only path):
- Purchase Invoice: expense hits Sea Freight Settings Deposits Pending for Refund Request (see container_deposit_pi).
- Request Deposit Refund: Journal Entry Dr Container Deposit Receivable (Customer) / Cr Deposits Pending for Refund Request.
- Operational charges: standalone Container Charge rows (link Container) reduce rolled-up deposit_amount.

Legacy clearing/bank carrier Journal Entry actions were removed; carrier payment is via PI only.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

from logistics.invoice_integration.container_deposit_pi import item_is_container_deposit
from logistics.job_management.gl_item_dimension import item_row_dict
from logistics.job_management.gl_reference_dimension import reference_dimension_row_dict


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


def _append_je_line(
	je,
	account,
	debit,
	credit,
	party_type=None,
	party=None,
	job_number=None,
	user_remark=None,
	extra_dimensions=None,
):
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
	if extra_dimensions:
		row.update(extra_dimensions)
	je.append("accounts", row)


def _item_code_from_pi_for_container_deposit(pi_name, container_name):
	if not pi_name or not frappe.db.exists("Purchase Invoice", pi_name):
		return None
	pi = frappe.get_doc("Purchase Invoice", pi_name)
	meta = frappe.get_meta("Purchase Invoice Item")
	has_lc = bool(meta.get_field("logistics_container"))
	first_cd = None
	for it in pi.get("items") or []:
		ic = it.get("item_code")
		if not ic or not item_is_container_deposit(ic):
			continue
		if not first_cd:
			first_cd = ic
		if has_lc and container_name and it.get("logistics_container") == container_name:
			return ic
	return first_cd


def _item_code_for_refund_deposit_row(deposit_row):
	if deposit_row.get("item_code"):
		return deposit_row.item_code
	return _item_code_from_pi_for_container_deposit(
		deposit_row.get("purchase_invoice"),
		deposit_row.get("container"),
	)


def _refund_je_dimension_extras(deposit_row):
	item_code = _item_code_for_refund_deposit_row(deposit_row)
	out = {}
	out.update(item_row_dict("Journal Entry Account", item_code))
	out.update(
		reference_dimension_row_dict(
			"Journal Entry Account",
			"Container",
			deposit_row.get("container"),
		)
	)
	return out


def total_container_charges_for_container(container_name):
	"""Sum Container Charge.total_amount for this container (non-cancelled documents)."""
	if not container_name:
		return 0.0
	r = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(total_amount), 0) FROM `tabContainer Charge`
		WHERE container = %s AND IFNULL(docstatus, 0) != 2
		""",
		(container_name,),
	)
	return flt(r[0][0] if r else 0)


def _pay_carrier_pi_base(container_doc):
	return sum(
		flt(r.deposit_amount)
		for r in container_doc.get("deposits") or []
		if (r.get("event_type") or "") == "Pay Carrier"
		and flt(r.deposit_amount) > 0
		and r.get("purchase_invoice")
	)


def pro_rata_charge_allocation_for_row(container_doc, deposit_row):
	total_ch = total_container_charges_for_container(container_doc.name)
	if total_ch <= 0:
		return 0.0
	base = _pay_carrier_pi_base(container_doc)
	if base <= 0:
		return 0.0
	row_amt = flt(deposit_row.deposit_amount)
	return total_ch * (row_amt / base)


def net_refund_amount_after_charges(container_doc, deposit_row):
	gross = flt(deposit_row.deposit_amount)
	return max(gross - pro_rata_charge_allocation_for_row(container_doc, deposit_row), 0)


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


def _get_deposit_row(container_doc, child_row_name):
	for r in container_doc.get("deposits") or []:
		if r.name == child_row_name:
			return r
	frappe.throw(_("Deposit row not found."), title=_("Container deposit"))


def _container_eligible_for_cd_refund_request(container_doc):
	rs = getattr(container_doc, "return_status", None) or ""
	st = getattr(container_doc, "status", None) or ""
	if rs == "Returned":
		return True
	if st in ("Empty Returned", "Closed"):
		return True
	return False


@frappe.whitelist()
def create_request_cd_refund_journal_entry(container_name, child_row_name):
	"""Dr Container Deposit Receivable (Customer), Cr Deposits Pending for Refund Request — after container is returned."""
	container = frappe.get_doc("Container", container_name)
	if not _container_eligible_for_cd_refund_request(container):
		frappe.throw(
			_("Container must be returned (empty returned / closed) before requesting CD refund."),
			title=_("Request Deposit Refund"),
		)
	assert_refund_readiness(container)
	row = _get_deposit_row(container, child_row_name)
	if not row.get("purchase_invoice"):
		frappe.throw(
			_("This deposit line is not linked to a container-deposit Purchase Invoice."),
			title=_("Request Deposit Refund"),
		)
	if frappe.db.get_value("Purchase Invoice", row.purchase_invoice, "docstatus") != 1:
		frappe.throw(_("Purchase Invoice must be submitted."), title=_("Request Deposit Refund"))
	if row.get("refund_request_journal_entry"):
		frappe.throw(_("Refund request Journal Entry already exists for this line."), title=_("Request Deposit Refund"))
	if flt(row.deposit_amount) <= 0:
		frappe.throw(_("Deposit amount must be positive."), title=_("Request Deposit Refund"))
	amt = net_refund_amount_after_charges(container, row)
	if amt <= 0:
		frappe.throw(
			_("Nothing to refund after container charges (net is zero or negative)."),
			title=_("Request Deposit Refund"),
		)
	_require_debtor_for_ar(row)
	try:
		sf = frappe.get_single("Sea Freight Settings")
	except Exception:
		sf = None
	if not sf:
		frappe.throw(_("Sea Freight Settings not found."), title=_("Request Deposit Refund"))
	pending = sf.get("container_deposit_pending_refund_account")
	ar_acc = sf.get("container_deposit_ar_shipping_lines_account")
	if not pending or not ar_acc:
		frappe.throw(
			_("Set Deposits Pending for Refund Request and Container Deposit Receivable Account in Sea Freight Settings."),
			title=_("Request Deposit Refund"),
		)
	ar_doc = frappe.get_doc("Account", ar_acc)
	if getattr(ar_doc, "account_type", None) != "Receivable":
		frappe.throw(
			_("Container Deposit Receivable Account must be a Receivable account."),
			title=_("Request Deposit Refund"),
		)
	company = _company_for_row(container, row)
	_require_job_number_if_enabled(row)

	je = frappe.new_doc("Journal Entry")
	je.company = company
	je.posting_date = getdate(nowdate())
	je.voucher_type = "Journal Entry"
	je.user_remark = _("Container deposit refund request {0}").format(container_name)

	_dim_extras = _refund_je_dimension_extras(row)
	_append_je_line(
		je,
		ar_acc,
		amt,
		0,
		party_type="Customer",
		party=row.debtor_party,
		job_number=row.get("job_number"),
		extra_dimensions=_dim_extras,
	)
	_append_je_line(
		je,
		pending,
		0,
		amt,
		job_number=row.get("job_number"),
		extra_dimensions=_dim_extras,
	)

	je.insert()
	je.submit()

	frappe.db.set_value("Container Deposit", row.name, "refund_request_journal_entry", je.name)
	return je.name


def sync_deposit_header_from_child_rows(container_doc):
	"""Roll up child deposit lines into header summary; subtract standalone Container Charge totals."""
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

	charges_sum = total_container_charges_for_container(container_doc.name)
	meta = getattr(container_doc, "meta", None) or frappe.get_meta(container_doc.doctype)
	if meta.has_field("container_charges_total"):
		container_doc.container_charges_total = charges_sum

	container_doc.deposit_amount = max(net - charges_sum, 0)
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
