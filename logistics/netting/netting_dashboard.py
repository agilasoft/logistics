# Copyright (c) 2026, Agilasoft and contributors
"""Netting Home workspace dashboard: top orgs with AR and AP ready to net."""

from __future__ import unicode_literals

from collections import defaultdict

import frappe
from frappe import _
from frappe.utils import cint, flt

from logistics.operations_dashboard.heat_map_core import session_company_context

DEFAULT_LIMIT = 15
MAX_LIMIT = 50


def nettable_amount(ar, ap):
	return min(flt(ar), flt(ap))


def is_ready(ar, ap):
	return flt(ar) > 0 and flt(ap) > 0


def sum_for_parties(amount_map, parties):
	total = 0.0
	invoices = 0
	for party in parties or []:
		if not party:
			continue
		row = amount_map.get(party) or {}
		total += flt(row.get("amount"))
		invoices += cint(row.get("invoices"))
	return total, invoices


def build_org_row(group, customers, suppliers, ar_map, ap_map, drafts_map):
	ar, ar_invoices = sum_for_parties(ar_map, customers)
	ap, ap_invoices = sum_for_parties(ap_map, suppliers)
	nettable = nettable_amount(ar, ap)
	ready = is_ready(ar, ap)
	return {
		"name": group.get("name"),
		"org": group.get("settlement_group_name") or group.get("name"),
		"company": group.get("company") or "",
		"settlement_customer": group.get("settlement_customer") or "",
		"settlement_supplier": group.get("settlement_supplier") or "",
		"customers": [p for p in customers if p],
		"suppliers": [p for p in suppliers if p],
		"customer_count": len([p for p in customers if p]),
		"supplier_count": len([p for p in suppliers if p]),
		"ar": flt(ar, 2),
		"ap": flt(ap, 2),
		"ar_invoices": ar_invoices,
		"ap_invoices": ap_invoices,
		"nettable": flt(nettable, 2),
		"net_position": flt(ar - ap, 2),
		"ready": 1 if ready else 0,
		"drafts": cint(drafts_map.get(group.get("name")) or 0),
	}


def rank_orgs(rows, ready_only=True, limit=DEFAULT_LIMIT):
	ranked = list(rows or [])
	if ready_only:
		ranked = [r for r in ranked if r.get("ready")]
	ranked.sort(
		key=lambda r: (
			-flt(r.get("nettable")),
			-(flt(r.get("ar")) + flt(r.get("ap"))),
			(r.get("org") or "").lower(),
		)
	)
	lim = cint(limit) or DEFAULT_LIMIT
	if lim < 1:
		lim = DEFAULT_LIMIT
	return ranked[: min(lim, MAX_LIMIT)]


def summarize_orgs(all_rows, ranked_rows):
	ready_rows = [r for r in (all_rows or []) if r.get("ready")]
	return {
		"groups": len(all_rows or []),
		"ready": len(ready_rows),
		"shown": len(ranked_rows or []),
		"ar_ready": flt(sum(flt(r.get("ar")) for r in ready_rows), 2),
		"ap_ready": flt(sum(flt(r.get("ap")) for r in ready_rows), 2),
		"nettable": flt(sum(flt(r.get("nettable")) for r in ready_rows), 2),
		"drafts": sum(cint(r.get("drafts")) for r in (all_rows or [])),
		"ar_invoices": sum(cint(r.get("ar_invoices")) for r in ready_rows),
		"ap_invoices": sum(cint(r.get("ap_invoices")) for r in ready_rows),
	}


def _party_sets(groups):
	names = [g.get("name") for g in groups if g.get("name")]
	customers = defaultdict(set)
	suppliers = defaultdict(set)
	for g in groups:
		name = g.get("name")
		if g.get("settlement_customer"):
			customers[name].add(g.get("settlement_customer"))
		if g.get("settlement_supplier"):
			suppliers[name].add(g.get("settlement_supplier"))
	if not names:
		return customers, suppliers
	members = frappe.get_all(
		"Settlement Group Member",
		filters={"parent": ["in", names]},
		fields=["parent", "party_type", "party"],
	)
	for row in members:
		if not row.get("party"):
			continue
		if row.get("party_type") == "Customer":
			customers[row.parent].add(row.party)
		elif row.get("party_type") == "Supplier":
			suppliers[row.parent].add(row.party)
	return customers, suppliers


def _outstanding_map(doctype, party_field, parties, company):
	out = {}
	parties = [p for p in set(parties or []) if p]
	if not parties or not frappe.db.exists("DocType", doctype):
		return out
	has_rate = frappe.get_meta(doctype).has_field("conversion_rate")
	amount_expr = (
		"SUM(outstanding_amount * IFNULL(conversion_rate, 1))"
		if has_rate
		else "SUM(outstanding_amount)"
	)
	filters = ["docstatus = 1", "IFNULL(outstanding_amount, 0) > 0", "{0} IN %(parties)s".format(party_field)]
	params = {"parties": parties}
	if company:
		filters.append("company = %(company)s")
		params["company"] = company
	rows = frappe.db.sql(
		"""
		SELECT {party} AS party, {amount} AS amount, COUNT(*) AS invoices
		FROM `tab{doctype}`
		WHERE {where}
		GROUP BY {party}
		""".format(
			party=party_field,
			amount=amount_expr,
			doctype=doctype,
			where=" AND ".join(filters),
		),
		params,
		as_dict=True,
	)
	for row in rows:
		out[row.party] = {"amount": flt(row.amount), "invoices": cint(row.invoices)}
	return out


def _draft_map(company):
	out = {}
	filters = ["docstatus = 0", "IFNULL(settlement_group, '') != ''"]
	params = {}
	if company:
		filters.append("company = %(company)s")
		params["company"] = company
	rows = frappe.db.sql(
		"""
		SELECT settlement_group, COUNT(*) AS drafts
		FROM `tabSettlement Entry`
		WHERE {where}
		GROUP BY settlement_group
		""".format(where=" AND ".join(filters)),
		params,
		as_dict=True,
	)
	for row in rows:
		out[row.settlement_group] = cint(row.drafts)
	return out


def collect_org_rows(company=None):
	filters = {"is_active": 1}
	if company:
		filters["company"] = company
	groups = frappe.get_all(
		"Settlement Group",
		filters=filters,
		fields=["name", "settlement_group_name", "settlement_customer", "settlement_supplier", "company"],
	)
	customers_by_group, suppliers_by_group = _party_sets(groups)
	all_customers = set()
	all_suppliers = set()
	for name in customers_by_group:
		all_customers.update(customers_by_group[name])
	for name in suppliers_by_group:
		all_suppliers.update(suppliers_by_group[name])
	ar_map = _outstanding_map("Sales Invoice", "customer", all_customers, company)
	ap_map = _outstanding_map("Purchase Invoice", "supplier", all_suppliers, company)
	drafts_map = _draft_map(company)
	rows = []
	for group in groups:
		name = group.get("name")
		rows.append(
			build_org_row(
				group,
				sorted(customers_by_group.get(name) or []),
				sorted(suppliers_by_group.get(name) or []),
				ar_map,
				ap_map,
				drafts_map,
			)
		)
	return rows


@frappe.whitelist()
def get_netting_dashboard(limit=None, ready_only=None):
	frappe.has_permission("Settlement Group", "read", throw=True)
	ctx = session_company_context()
	company = (ctx.get("company") or "").strip()
	lim = cint(limit) if limit not in (None, "") else DEFAULT_LIMIT
	only_ready = 1 if ready_only in (None, "", True, 1, "1") else 0
	all_rows = collect_org_rows(company or None)
	ranked = rank_orgs(all_rows, ready_only=bool(only_ready), limit=lim)
	currency = ""
	if company:
		currency = frappe.db.get_value("Company", company, "default_currency") or ""
	kpis = summarize_orgs(all_rows, ranked)
	return {
		"company": ctx.get("company") or "",
		"company_name": ctx.get("company_name") or "",
		"company_logo_url": ctx.get("company_logo_url") or "",
		"currency": currency,
		"kpis": kpis,
		"orgs": ranked,
		"ready_only": only_ready,
		"limit": min(max(lim, 1), MAX_LIMIT),
	}
