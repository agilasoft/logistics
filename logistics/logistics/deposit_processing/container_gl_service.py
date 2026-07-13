# -*- coding: utf-8 -*-
# Copyright (c) 2026, Logistics Team and contributors
"""
Container deposit / charge views from **GL Entry** using the **Container** accounting dimension.

The **Deposits** HTML table lists only GL rows on **Deposits Pending for Refund Request** (Sea Freight Settings)
whose **Item** accounting dimension is a **Container Deposit Charge** item (or non-item refund JE lines).
**Charges** include only GL rows whose **Item** accounting dimension points to an Item with **Container charge** checked;
those amounts roll into Total charges and are **not** deducted from the deposit header.
"""

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import escape_html, flt, formatdate

from logistics.invoice_integration.container_deposit_pi import (
	item_is_container_charge,
	item_is_container_deposit,
)
from logistics.job_management.gl_item_dimension import get_item_dimension_fieldname_on_gl_entry
from logistics.job_management.gl_reference_dimension import get_accounting_dimension_fieldname


def _container_column():
	fn = get_accounting_dimension_fieldname("Container")
	if not fn or not frappe.db.has_column("GL Entry", fn):
		return None
	return fn


def _gl_item_column():
	"""Column on GL Entry for Item accounting dimension (profitability / charge tagging)."""
	fn = get_item_dimension_fieldname_on_gl_entry()
	if not fn or not frappe.db.has_column("GL Entry", fn):
		return None
	return fn


def _pending_refund_account_for_company(company):
	"""Pending-refund GL account for ``company`` (reads DB; does not rely on Sea Freight Settings doc permission)."""
	if not company:
		return None
	if not frappe.db.table_exists("Sea Freight Settings"):
		return None
	return frappe.db.get_value(
		"Sea Freight Settings",
		{"company": company},
		"container_deposit_pending_refund_account",
	)


def _all_pending_refund_accounts():
	"""Distinct Deposits Pending accounts configured across all Sea Freight Settings rows (SQL; not permission-filtered)."""
	if not frappe.db.table_exists("Sea Freight Settings"):
		return []
	rows = frappe.db.sql(
		"""
		SELECT DISTINCT container_deposit_pending_refund_account
		FROM `tabSea Freight Settings`
		WHERE IFNULL(container_deposit_pending_refund_account, '') != ''
		""",
	)
	out = []
	for (acc,) in rows or []:
		if acc:
			out.append(acc)
	return out


def get_deposit_system_accounts():
	"""Accounts that belong to the deposit / refund lifecycle (not operational charges)."""
	accts = set()
	try:
		for row in frappe.db.sql(
			"""
			SELECT container_deposit_pending_refund_account, container_deposit_ar_shipping_lines_account
			FROM `tabSea Freight Settings`
			""",
			as_dict=True,
		) or []:
			for f in ("container_deposit_pending_refund_account", "container_deposit_ar_shipping_lines_account"):
				v = row.get(f)
				if v:
					accts.add(v)
	except Exception:
		pass
	try:
		ls = frappe.get_single("Logistics Settings")
		for f in (
			"container_deposit_clearing_account",
			"container_deposit_customer_liability_account",
			"container_deposit_forfeiture_account",
			"container_deposit_debtors_account",
		):
			v = ls.get(f)
			if v:
				accts.add(v)
	except Exception:
		pass
	return accts


def _gl_row_is_container_deposit_charge(row):
	"""True when a pending-account GL row belongs on the Container Deposit tab."""
	item_code = row.get("gl_item_code")
	if item_code:
		return item_is_container_deposit(item_code)
	# Refund JEs and other non-item postings on the pending account stay visible.
	return True


def _deposit_gl_item_filter_sql(item_fn):
	"""SQL fragment: pending-account GL is a container-deposit charge (or non-item refund line)."""
	if not item_fn or not frappe.db.has_column("Item", "custom_container_deposit_charge"):
		return "1=1"
	return """(
		IFNULL(gle.`{item_fn}`, '') = ''
		OR IFNULL(item.custom_container_deposit_charge, 0) = 1
	)""".format(item_fn=item_fn)


def _query_gl_for_container(container_name):
	fn = _container_column()
	if not fn:
		return []
	item_fn = _gl_item_column()
	item_expr = ""
	if item_fn:
		item_expr = ", gle.`{item_fn}` AS gl_item_code".format(item_fn=item_fn)
	sql = """
		SELECT gle.posting_date, gle.voucher_type, gle.voucher_no, gle.account,
			gle.debit, gle.credit, gle.debit_in_account_currency, gle.credit_in_account_currency,
			gle.against_voucher_type, gle.against_voucher, gle.party_type, gle.party,
			gle.remarks, gle.company{item_expr}
		FROM `tabGL Entry` gle
		WHERE gle.`{fn}` = %s AND IFNULL(gle.is_cancelled, 0) = 0
		ORDER BY gle.posting_date DESC, gle.creation DESC
		LIMIT 500
	""".format(fn=fn, item_expr=item_expr)
	return frappe.db.sql(sql, (container_name,), as_dict=True)


def get_gl_rows_split(container_name):
	"""Return (deposit_rows, charge_rows) for HTML.

	**Deposit** display rows: pending-refund account GL with **Container Deposit Charge** Items only.
	**Charge** display rows: GL lines on **Container charge** Items (Item dimension), excluding deposit account lines.
	"""
	fn = _container_column()
	if not fn:
		return [], []
	all_rows = _query_gl_for_container(container_name)
	deposit_rows = []
	charge_rows = []
	for r in all_rows:
		acc = r.get("account")
		co = r.get("company")
		pending = _pending_refund_account_for_company(co) if co else None
		if pending and acc == pending and _gl_row_is_container_deposit_charge(r):
			deposit_rows.append(r)
			continue
		item_code = r.get("gl_item_code")
		if item_code and item_is_container_charge(item_code):
			charge_rows.append(r)
	return deposit_rows, charge_rows


def net_pending_balance_for_container(container_name):
	"""Net balance on the Deposits Pending for Refund account for this container (company currency)."""
	fn = _container_column()
	item_fn = _gl_item_column()
	accounts = _all_pending_refund_accounts()
	if not fn or not accounts:
		return 0.0
	ph = ",".join(["%s"] * len(accounts))
	item_filter = _deposit_gl_item_filter_sql(item_fn)
	join_item = ""
	if item_fn and frappe.db.has_column("Item", "custom_container_deposit_charge"):
		join_item = "LEFT JOIN `tabItem` item ON item.name = gle.`{item_fn}`".format(item_fn=item_fn)
	r = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(gle.debit - gle.credit), 0) FROM `tabGL Entry` gle
		{join_item}
		WHERE gle.`{col}` = %s AND gle.account IN ({ph}) AND IFNULL(gle.is_cancelled, 0) = 0
			AND {item_filter}
		""".format(col=fn, ph=ph, join_item=join_item, item_filter=item_filter),
		(container_name,) + tuple(accounts),
	)
	return flt(r[0][0] if r else 0)


def total_container_charges_amount_from_gl(container_name):
	"""Sum of debit GL rows on **Container charge** Items (Item dimension), excluding deposit lifecycle accounts."""
	fn = _container_column()
	item_fn = _gl_item_column()
	if not fn or not item_fn:
		return 0.0
	if not frappe.db.has_column("Item", "custom_container_charge"):
		return 0.0
	deposit_accts = get_deposit_system_accounts()
	pending_accounts = _all_pending_refund_accounts()
	if not deposit_accts:
		if not pending_accounts:
			return 0.0
		ph = ",".join(["%s"] * len(pending_accounts))
		r = frappe.db.sql(
			"""
			SELECT COALESCE(SUM(gle.debit), 0) FROM `tabGL Entry` gle
			INNER JOIN `tabItem` item ON item.name = gle.`{item_fn}`
			WHERE gle.`{col}` = %s AND IFNULL(gle.is_cancelled, 0) = 0 AND gle.debit > 0
				AND IFNULL(item.custom_container_charge, 0) = 1
				AND gle.account NOT IN ({ph})
			""".format(col=fn, item_fn=item_fn, ph=ph),
			(container_name,) + tuple(pending_accounts),
		)
		return flt(r[0][0] if r else 0)
	placeholders = ",".join(["%s"] * len(deposit_accts))
	ac_list = tuple(deposit_accts)
	r = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(gle.debit), 0) FROM `tabGL Entry` gle
		INNER JOIN `tabItem` item ON item.name = gle.`{item_fn}`
		WHERE gle.`{col}` = %s AND IFNULL(gle.is_cancelled, 0) = 0
			AND IFNULL(item.custom_container_charge, 0) = 1
			AND gle.account NOT IN ({ph})
			AND gle.debit > 0
		""".format(col=fn, item_fn=item_fn, ph=placeholders),
		(container_name,) + ac_list,
	)
	return flt(r[0][0] if r else 0)


def sync_deposit_header_from_gl(container_doc):
	"""Roll up header currency fields from GL (Container dimension)."""
	meta = getattr(container_doc, "meta", None) or frappe.get_meta(container_doc.doctype)
	name = container_doc.name
	if not name:
		return
	net_pending = net_pending_balance_for_container(name)
	charges_sum = total_container_charges_amount_from_gl(name)
	if meta.has_field("container_charges_total"):
		container_doc.container_charges_total = charges_sum
	container_doc.deposit_amount = max(flt(net_pending), 0)
	try:
		fn = _container_column()
		pending_accounts = _all_pending_refund_accounts()
		if fn and pending_accounts:
			ph = ",".join(["%s"] * len(pending_accounts))
			item_fn = _gl_item_column()
			item_filter = _deposit_gl_item_filter_sql(item_fn)
			join_item = ""
			if item_fn and frappe.db.has_column("Item", "custom_container_deposit_charge"):
				join_item = "LEFT JOIN `tabItem` item ON item.name = gle.`{item_fn}`".format(item_fn=item_fn)
			cur = frappe.db.sql(
				"""
				SELECT gle.account_currency FROM `tabGL Entry` gle
				{join_item}
				WHERE gle.`{col}` = %s AND gle.account IN ({ph}) AND IFNULL(gle.is_cancelled, 0) = 0
					AND {item_filter}
				ORDER BY gle.posting_date DESC LIMIT 1
				""".format(col=fn, ph=ph, join_item=join_item, item_filter=item_filter),
				(name,) + tuple(pending_accounts),
			)
			if cur and cur[0][0] and meta.has_field("deposit_currency"):
				container_doc.deposit_currency = cur[0][0]
			last_pd = frappe.db.sql(
				"""
				SELECT MAX(gle.posting_date) FROM `tabGL Entry` gle
				{join_item}
				WHERE gle.`{col}` = %s AND gle.account IN ({ph}) AND gle.voucher_type = 'Purchase Invoice'
					AND IFNULL(gle.is_cancelled, 0) = 0 AND {item_filter}
				""".format(col=fn, ph=ph, join_item=join_item, item_filter=item_filter),
				(name,) + tuple(pending_accounts),
			)
			if last_pd and last_pd[0][0] and meta.has_field("deposit_paid_date"):
				container_doc.deposit_paid_date = last_pd[0][0]
	except Exception:
		pass
	if meta.has_field("deposit_reference"):
		container_doc.deposit_reference = _("GL (Container dimension)")


def _html_table(rows, title):
	if not rows:
		return "<p class='text-muted'>{0}</p>".format(escape_html(_("No GL rows.")))
	head = (
		"<div class='small text-muted mb-2'>{0}</div>"
		"<table class='table table-bordered table-condensed'>"
		"<thead><tr>"
		"<th>{1}</th><th>{2}</th><th>{3}</th><th>{4}</th><th>{5}</th><th>{6}</th><th>{7}</th><th>{8}</th>"
		"</tr></thead><tbody>"
	).format(
		escape_html(title),
		escape_html(_("Date")),
		escape_html(_("Voucher")),
		escape_html(_("Account")),
		escape_html(_("Debit")),
		escape_html(_("Credit")),
		escape_html(_("Party")),
		escape_html(_("Against")),
		escape_html(_("Remarks")),
	)
	parts = [head]
	for r in rows:
		v = "{0}: {1}".format(r.get("voucher_type") or "", r.get("voucher_no") or "")
		agn = ""
		if r.get("against_voucher"):
			agn = "{0}: {1}".format(r.get("against_voucher_type") or "", r.get("against_voucher"))
		party = (r.get("party_type") or "") + " / " + (r.get("party") or "")
		parts.append(
			"<tr><td>{pd}</td><td>{v}</td><td>{acc}</td><td>{dr}</td><td>{cr}</td><td>{pty}</td><td>{ag}</td><td>{rm}</td></tr>".format(
				pd=escape_html(formatdate(r.get("posting_date")) if r.get("posting_date") else ""),
				v=escape_html(v.strip(": ")),
				acc=escape_html(r.get("account") or ""),
				dr=flt(r.get("debit")),
				cr=flt(r.get("credit")),
				pty=escape_html(party.strip(" /")),
				ag=escape_html(agn),
				rm=escape_html((r.get("remarks") or "")[:120]),
			)
		)
	parts.append("</tbody></table>")
	return "".join(parts)


def get_deposits_gl_html(container_name):
	if not container_name or str(container_name).startswith("new-"):
		return ""
	accounts = _all_pending_refund_accounts()
	if not accounts:
		return "<p class='text-muted'>{0}</p>".format(
			escape_html(
				_(
					"No Deposits Pending for Refund Request account is configured on any Sea Freight Settings row, "
					"or the setting could not be read. Ask an administrator to set it per company on Sea Freight Settings."
				)
			)
		)
	deposit_rows, _charge = get_gl_rows_split(container_name)
	if len(accounts) == 1:
		pending_label = frappe.db.get_value("Account", accounts[0], "account_name") or accounts[0]
	else:
		pending_label = _("multiple accounts")
	return _html_table(
		deposit_rows,
		_("Container deposit charges only — Deposits Pending for Refund Request ({0})").format(pending_label),
	)


def _account_label(account):
	if not account:
		return ""
	if not frappe.db.exists("Account", account):
		return account
	row = frappe.db.get_value(
		"Account",
		account,
		["account_number", "account_name", "company"],
		as_dict=True,
	)
	if not row:
		return account
	abbr = frappe.db.get_value("Company", row.company, "abbr") if row.company else ""
	parts = [p for p in (row.account_number, row.account_name, abbr) if p]
	return " - ".join(parts) if parts else account


def _party_label(party_type, party):
	if not party:
		return ""
	if party_type == "Supplier":
		return frappe.db.get_value("Supplier", party, "supplier_name") or party
	if party_type == "Customer":
		return frappe.db.get_value("Customer", party, "customer_name") or party
	return party


def _refunded_purchase_invoices_for_container(container_name):
	rows = frappe.get_all(
		"Container Refund Link",
		filters={"parent": container_name},
		fields=["purchase_invoice"],
	)
	return {r.purchase_invoice for r in rows if r.get("purchase_invoice")}


def _refund_status_for_gl_row(row, refunded_pis):
	voucher_type = row.get("voucher_type") or ""
	voucher_no = row.get("voucher_no") or ""
	if voucher_type == "Journal Entry":
		return "Refunded"
	if voucher_type == "Purchase Invoice":
		return "Refunded" if voucher_no in refunded_pis else "Open"
	if flt(row.get("credit")) > flt(row.get("debit")):
		return "Refunded"
	return "Open"


def get_deposit_postings_data(container_name):
	"""Structured deposit transaction rows for the Container Deposit tab UI."""
	if not container_name or str(container_name).startswith("new-"):
		return {"rows": [], "items": [], "currency": None, "error": None}

	accounts = _all_pending_refund_accounts()
	if not accounts:
		return {
			"rows": [],
			"items": [],
			"currency": None,
			"error": _(
				"No Deposits Pending for Refund Request account is configured on any Sea Freight Settings row. "
				"Ask an administrator to set it per company on Sea Freight Settings."
			),
		}

	deposit_rows, _charge = get_gl_rows_split(container_name)
	refunded_pis = _refunded_purchase_invoices_for_container(container_name)
	items = set()
	out_rows = []
	currency = None

	for r in deposit_rows:
		item_code = (r.get("gl_item_code") or "").strip()
		if item_code:
			items.add(item_code)
		if not currency and r.get("company"):
			currency = frappe.db.get_value("Company", r.get("company"), "default_currency")

		party = _party_label(r.get("party_type"), r.get("party"))
		if not party and r.get("voucher_type") == "Purchase Invoice" and r.get("voucher_no"):
			party = frappe.db.get_value("Purchase Invoice", r.voucher_no, "supplier")

		out_rows.append(
			{
				"posting_date": str(r.get("posting_date") or ""),
				"voucher_type": r.get("voucher_type") or "",
				"voucher_no": r.get("voucher_no") or "",
				"item_code": item_code,
				"account": r.get("account") or "",
				"account_label": _account_label(r.get("account")),
				"debit": flt(r.get("debit")),
				"credit": flt(r.get("credit")),
				"party": party or "",
				"refund_status": _refund_status_for_gl_row(r, refunded_pis),
			}
		)

	if not currency:
		currency = frappe.defaults.get_user_default("currency")

	return {
		"rows": out_rows,
		"items": sorted(items),
		"currency": currency,
		"error": None,
	}


def get_charges_gl_html(container_name):
	if not container_name or str(container_name).startswith("new-"):
		return ""
	_deposit, charge_rows = get_gl_rows_split(container_name)
	return _html_table(
		charge_rows,
		_("Container charge Items only — GL (Container dimension), excluding deposit pending account"),
	)


def pending_amount_for_pi_container(container_name, purchase_invoice):
	"""Carrier deposit posted on PI: debit to pending account with Container dimension."""
	fn = _container_column()
	item_fn = _gl_item_column()
	if not fn or not purchase_invoice:
		return 0.0
	co = frappe.db.get_value("Purchase Invoice", purchase_invoice, "company")
	pending = _pending_refund_account_for_company(co)
	if not pending:
		return 0.0
	item_filter = _deposit_gl_item_filter_sql(item_fn)
	join_item = ""
	if item_fn and frappe.db.has_column("Item", "custom_container_deposit_charge"):
		join_item = "LEFT JOIN `tabItem` item ON item.name = gle.`{item_fn}`".format(item_fn=item_fn)
	r = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(gle.debit), 0) FROM `tabGL Entry` gle
		{join_item}
		WHERE gle.`{col}` = %s AND gle.account = %s AND gle.voucher_type = 'Purchase Invoice'
			AND gle.voucher_no = %s AND IFNULL(gle.is_cancelled, 0) = 0 AND {item_filter}
		""".format(col=fn, join_item=join_item, item_filter=item_filter),
		(container_name, pending, purchase_invoice),
	)
	return flt(r[0][0] if r else 0)


def total_pending_pi_debits_for_container(container_name):
	fn = _container_column()
	item_fn = _gl_item_column()
	accounts = _all_pending_refund_accounts()
	if not fn or not accounts:
		return 0.0
	ph = ",".join(["%s"] * len(accounts))
	item_filter = _deposit_gl_item_filter_sql(item_fn)
	join_item = ""
	if item_fn and frappe.db.has_column("Item", "custom_container_deposit_charge"):
		join_item = "LEFT JOIN `tabItem` item ON item.name = gle.`{item_fn}`".format(item_fn=item_fn)
	r = frappe.db.sql(
		"""
		SELECT COALESCE(SUM(gle.debit), 0) FROM `tabGL Entry` gle
		{join_item}
		WHERE gle.`{col}` = %s AND gle.account IN ({ph}) AND gle.voucher_type = 'Purchase Invoice'
			AND IFNULL(gle.is_cancelled, 0) = 0 AND {item_filter}
		""".format(col=fn, ph=ph, join_item=join_item, item_filter=item_filter),
		(container_name,) + tuple(accounts),
	)
	return flt(r[0][0] if r else 0)


def has_refund_link(container_name, purchase_invoice):
	for r in frappe.get_all(
		"Container Refund Link",
		filters={"parent": container_name, "purchase_invoice": purchase_invoice},
		pluck="name",
		limit=1,
	):
		return True
	return False


def get_refund_journal_for_pi(container_name, purchase_invoice):
	row = frappe.db.get_value(
		"Container Refund Link",
		{"parent": container_name, "purchase_invoice": purchase_invoice},
		"journal_entry",
		as_dict=True,
	)
	return row.get("journal_entry") if row else None


def pro_rata_charge_allocation_for_pi(container_name, purchase_invoice):
	"""Legacy: proportional allocation of container-charge GL to one PI; unused for refund amount."""
	total_ch = total_container_charges_amount_from_gl(container_name)
	base = total_pending_pi_debits_for_container(container_name)
	if total_ch <= 0 or base <= 0:
		return 0.0
	pi_amt = pending_amount_for_pi_container(container_name, purchase_invoice)
	return total_ch * (pi_amt / base)


def net_refund_amount_after_charges_for_pi(container_name, purchase_invoice):
	"""Refund request uses carrier deposit GL on this PI; container charges do not reduce it."""
	return max(flt(pending_amount_for_pi_container(container_name, purchase_invoice)), 0)


def list_eligible_refund_purchase_invoices(container_name):
	"""Purchase Invoices with pending deposit GL for this container and no refund JE yet."""
	fn = _container_column()
	item_fn = _gl_item_column()
	accounts = _all_pending_refund_accounts()
	if not fn or not accounts:
		return []
	ph = ",".join(["%s"] * len(accounts))
	item_filter = _deposit_gl_item_filter_sql(item_fn)
	join_item = ""
	if item_fn and frappe.db.has_column("Item", "custom_container_deposit_charge"):
		join_item = "LEFT JOIN `tabItem` item ON item.name = gle.`{item_fn}`".format(item_fn=item_fn)
	pis = frappe.db.sql(
		"""
		SELECT DISTINCT gle.voucher_no
		FROM `tabGL Entry` gle
		{join_item}
		WHERE gle.`{fn}` = %s AND gle.account IN ({ph}) AND gle.voucher_type = 'Purchase Invoice'
			AND gle.debit > 0 AND IFNULL(gle.is_cancelled, 0) = 0 AND {item_filter}
		""".format(fn=fn, ph=ph, join_item=join_item, item_filter=item_filter),
		(container_name,) + tuple(accounts),
	)
	out = []
	for (pi,) in pis:
		if not pi or frappe.db.get_value("Purchase Invoice", pi, "docstatus") != 1:
			continue
		if has_refund_link(container_name, pi):
			continue
		pending_amt = pending_amount_for_pi_container(container_name, pi)
		if pending_amt <= 0:
			continue
		net = net_refund_amount_after_charges_for_pi(container_name, pi)
		if net <= 0:
			continue
		out.append(
			{
				"purchase_invoice": pi,
				"pending_amount": pending_amt,
				"net_refund": net,
			}
		)
	return out
