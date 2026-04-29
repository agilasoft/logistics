# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Container deposit (PI-only path):
- Purchase Invoice: expense hits Sea Freight Settings Deposits Pending for Refund Request (see container_deposit_pi); GL must carry **Container** accounting dimension.
- Request Deposit Refund: Journal Entry Dr Container Deposit Receivable (Customer) / Cr Deposits Pending for Refund Request.
- Deposits and charges on the Container form are **virtual** (read from GL Entry); header roll-up uses `container_gl_service`.
"""

import frappe
from frappe import _
from frappe.utils import flt, getdate, nowdate

from logistics.invoice_integration.container_deposit_pi import item_is_container_deposit
from logistics.job_management.gl_item_dimension import item_row_dict
from logistics.job_management.gl_reference_dimension import reference_dimension_row_dict
from logistics.logistics.deposit_processing.container_gl_service import (
	has_refund_link,
	list_eligible_refund_purchase_invoices,
	net_refund_amount_after_charges_for_pi,
	pending_amount_for_pi_container,
	sync_deposit_header_from_gl,
	total_container_charges_amount_from_gl,
)


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


def _refund_je_dimension_extras_from_pi(container_name, purchase_invoice):
	item_code = _item_code_from_pi_for_container_deposit(purchase_invoice, container_name)
	out = {}
	out.update(item_row_dict("Journal Entry Account", item_code))
	out.update(
		reference_dimension_row_dict(
			"Journal Entry Account",
			"Container",
			container_name,
		)
	)
	return out


def total_container_charges_amount(container_doc):
	"""Compatibility: operational charge total from GL (Container dimension)."""
	name = getattr(container_doc, "name", None) if container_doc else None
	if not name:
		return 0.0
	return total_container_charges_amount_from_gl(name)


def sync_deposit_header_from_child_rows(container_doc):
	"""Backward-compatible name: roll-up from GL."""
	sync_deposit_header_from_gl(container_doc)


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


def _job_number_from_purchase_invoice(purchase_invoice):
	if not purchase_invoice:
		return None
	pi = frappe.get_doc("Purchase Invoice", purchase_invoice)
	header_ref_dt = pi.get("reference_doctype") or ""
	header_ref_name = pi.get("reference_name") or ""
	for row in pi.get("items") or []:
		jdt = row.get("reference_doctype") or header_ref_dt
		jnm = row.get("reference_name") or header_ref_name
		if not jdt or not jnm or not frappe.db.exists(jdt, jnm):
			continue
		job = frappe.get_doc(jdt, jnm)
		return getattr(job, "job_number", None)
	return None


def _debtor_party_from_purchase_invoice(purchase_invoice):
	if not purchase_invoice:
		return None
	pi = frappe.get_doc("Purchase Invoice", purchase_invoice)
	header_ref_dt = pi.get("reference_doctype") or ""
	header_ref_name = pi.get("reference_name") or ""
	for row in pi.get("items") or []:
		jdt = row.get("reference_doctype") or header_ref_dt
		jnm = row.get("reference_name") or header_ref_name
		if jdt == "Sea Shipment" and jnm and frappe.db.exists("Sea Shipment", jnm):
			job = frappe.get_doc("Sea Shipment", jnm)
			return getattr(job, "local_customer", None) or getattr(job, "booking_party", None)
		if jdt == "Declaration" and jnm and frappe.db.exists("Declaration", jnm):
			job = frappe.get_doc("Declaration", jnm)
			return getattr(job, "customer", None)
	return None


def _container_eligible_for_cd_refund_request(container_doc):
	rs = getattr(container_doc, "return_status", None) or ""
	st = getattr(container_doc, "status", None) or ""
	if rs == "Returned":
		return True
	if st in ("Empty Returned", "Closed"):
		return True
	return False


@frappe.whitelist()
def create_request_cd_refund_journal_entry(container_name, purchase_invoice=None):
	"""Dr Container Deposit Receivable (Customer), Cr Deposits Pending for Refund Request — GL-backed deposits."""
	if not purchase_invoice:
		frappe.throw(_("Purchase Invoice is required."), title=_("Request Deposit Refund"))
	container = frappe.get_doc("Container", container_name)
	if not _container_eligible_for_cd_refund_request(container):
		frappe.throw(
			_("Container must be returned (empty returned / closed) before requesting CD refund."),
			title=_("Request Deposit Refund"),
		)
	assert_refund_readiness(container)
	if frappe.db.get_value("Purchase Invoice", purchase_invoice, "docstatus") != 1:
		frappe.throw(_("Purchase Invoice must be submitted."), title=_("Request Deposit Refund"))
	if has_refund_link(container_name, purchase_invoice):
		frappe.throw(_("Refund request Journal Entry already exists for this PI."), title=_("Request Deposit Refund"))
	pending_amt = pending_amount_for_pi_container(container_name, purchase_invoice)
	if pending_amt <= 0:
		frappe.throw(
			_("No posted carrier deposit GL found for this Purchase Invoice and container (check Container dimension on PI)."),
			title=_("Request Deposit Refund"),
		)
	amt = net_refund_amount_after_charges_for_pi(container_name, purchase_invoice)
	if amt <= 0:
		frappe.throw(
			_("Nothing to refund after container charges (net is zero or negative)."),
			title=_("Request Deposit Refund"),
		)
	proxy = frappe._dict(
		{
			"job_number": _job_number_from_purchase_invoice(purchase_invoice),
			"debtor_party": _debtor_party_from_purchase_invoice(purchase_invoice),
			"company": frappe.db.get_value("Purchase Invoice", purchase_invoice, "company"),
		}
	)
	_require_debtor_for_ar(proxy)
	from logistics.sea_freight.doctype.sea_freight_settings.sea_freight_settings import SeaFreightSettings

	pi_company = frappe.db.get_value("Purchase Invoice", purchase_invoice, "company")
	sf = SeaFreightSettings.get_settings(pi_company)
	if not sf:
		frappe.throw(_("Sea Freight Settings not found for company {0}.").format(pi_company or "-"), title=_("Request Deposit Refund"))
	pending = sf.get("container_deposit_pending_refund_account")
	ar_acc = sf.get("container_deposit_ar_shipping_lines_account")
	if not pending or not ar_acc:
		frappe.throw(
			_("Set Deposits Pending for Refund Request and Container Deposit Receivable Account in Sea Freight Settings for company {0}.").format(
				pi_company or "-"
			),
			title=_("Request Deposit Refund"),
		)
	ar_doc = frappe.get_doc("Account", ar_acc)
	if getattr(ar_doc, "account_type", None) != "Receivable":
		frappe.throw(
			_("Container Deposit Receivable Account must be a Receivable account."),
			title=_("Request Deposit Refund"),
		)
	company = _company_for_row(container, proxy)
	_require_job_number_if_enabled(proxy)

	je = frappe.new_doc("Journal Entry")
	je.company = company
	je.posting_date = getdate(nowdate())
	je.voucher_type = "Journal Entry"
	je.user_remark = _("Container deposit refund request {0}").format(container_name)

	_dim_extras = _refund_je_dimension_extras_from_pi(container_name, purchase_invoice)
	_append_je_line(
		je,
		ar_acc,
		amt,
		0,
		party_type="Customer",
		party=proxy.debtor_party,
		job_number=proxy.get("job_number"),
		extra_dimensions=_dim_extras,
	)
	_append_je_line(
		je,
		pending,
		0,
		amt,
		job_number=proxy.get("job_number"),
		extra_dimensions=_dim_extras,
	)

	je.insert()
	je.submit()

	container.append(
		"refund_links",
		{"purchase_invoice": purchase_invoice, "journal_entry": je.name},
	)
	container.save(ignore_permissions=True)
	return je.name


@frappe.whitelist()
def get_eligible_refund_purchase_invoices(container_name):
	return list_eligible_refund_purchase_invoices(container_name)


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
