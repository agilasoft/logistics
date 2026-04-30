# -*- coding: utf-8 -*-
# Copyright (c) 2025, Logistics Team and contributors
# For license information, please see license.txt

"""
**One row per container**: SUM(GL debit − credit) on **Deposits Pending for Refund Request** (Sea Freight Settings),
grouped by Container accounting dimension — same basis as Container → Deposits (GL) / net pending balance.

Underlying data is read from `tabGL Entry` then **aggregated in Python by container** (one output row per dimension value); never one row per GL Entry.

**Shipping Line** column: `Container.owner_carrier` when set; otherwise **Master Bill.shipping_line** for `Container.master_bill`.

Includes ageing buckets (Accounts Receivable–style bands) and a bar chart.
"""

from __future__ import unicode_literals

from collections import OrderedDict

import frappe
from frappe import _
from frappe.utils import cint, date_diff, flt, getdate, nowdate

from logistics.analytics_reports.bootstrap import tally_chart
from logistics.job_management.gl_reference_dimension import get_accounting_dimension_fieldname
from logistics.sea_freight.doctype.sea_freight_settings.sea_freight_settings import SeaFreightSettings


def execute(filters=None):
	filters = frappe._dict(filters or {})
	ranges = _parse_ageing_ranges(filters.get("range"))
	bucket_labels = _ageing_bucket_labels(ranges)
	columns = get_columns(filters, ranges, bucket_labels)
	data = get_data(filters, ranges)
	net_total = sum(flt(r.get("line_amount")) for r in data)
	chart = _build_ageing_bar_chart(data, bucket_labels)
	if not chart:
		chart = tally_chart(data, "return_status", _("Deposits"))
	report_summary = [
		{
			"value": net_total,
			"indicator": "Blue",
			"label": _("Total pending (net)"),
			"datatype": "Currency",
		}
	]
	message = _empty_message_if_needed(data, filters)
	return columns, data, message, chart, report_summary


def _empty_message_if_needed(data, filters):
	if data:
		return None
	return _(
		"No rows match. This report rolls up GL on Account = Deposits Pending for Refund Request (Sea Freight Settings row for the selected company), "
		"with the Container dimension set, and Company = filter. If Return Status is Returned but refund is still open in GL, "
		'enable "Include returned containers". Clear optional filters (dates, supplier, shipping line).'
	)


def _parse_ageing_ranges(range_str):
	default = [30, 60, 90, 120]
	if not range_str or not str(range_str).strip():
		return default
	out = []
	for part in str(range_str).split(","):
		part = part.strip()
		if part.isdigit():
			out.append(int(part))
	return out or default


def _ageing_bucket_labels(ranges):
	labels = [_("<0")]
	prev = 0
	for upper in ranges:
		labels.append("{0}-{1}".format(prev, upper))
		prev = upper + 1
	labels.append(_("Above"))
	return labels


def _age_bucket_index(age_days, ranges):
	if age_days < 0:
		return 0
	for idx, upper in enumerate(ranges):
		if age_days <= upper:
			return idx + 1
	return len(ranges) + 1


def _age_as_on(filters):
	if filters.get("calculate_ageing_with") == "Today Date":
		return getdate(nowdate())
	return getdate(filters.get("report_date") or nowdate())


def get_columns(filters=None, ranges=None, bucket_labels=None):
	ranges = ranges or _parse_ageing_ranges(filters.get("range") if filters else None)
	bucket_labels = bucket_labels or _ageing_bucket_labels(ranges)
	cols = [
		{
			"fieldname": "container_number",
			"label": _("Container"),
			"fieldtype": "Link",
			"options": "Container",
			"width": 140,
		},
		{"fieldname": "equipment_no", "label": _("Equipment No."), "fieldtype": "Data", "width": 120},
		{"fieldname": "company", "label": _("Company"), "fieldtype": "Link", "options": "Company", "width": 120},
		{"fieldname": "shipping_line", "label": _("Shipping Line"), "fieldtype": "Link", "options": "Shipping Line", "width": 130},
		{"fieldname": "job_number", "label": _("Job Number"), "fieldtype": "Link", "options": "Job Number", "width": 120},
		{"fieldname": "master_bill", "label": _("Master Bill"), "fieldtype": "Link", "options": "Master Bill", "width": 120},
		{"fieldname": "debit", "label": _("Debit (total)"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "credit", "label": _("Credit (total)"), "fieldtype": "Currency", "width": 110},
		{"fieldname": "line_amount", "label": _("Net pending balance"), "fieldtype": "Currency", "width": 130},
		{"fieldname": "gl_line_count", "label": _("GL lines (#)"), "fieldtype": "Int", "width": 100},
		{"fieldname": "deposit_paid_date", "label": _("Oldest posting (age basis)"), "fieldtype": "Date", "width": 160},
		{"fieldname": "days_outstanding", "label": _("Age (days)"), "fieldtype": "Int", "width": 100},
	]
	for i, lbl in enumerate(bucket_labels):
		cols.append(
			{
				"fieldname": "range{0}".format(i),
				"label": lbl,
				"fieldtype": "Currency",
				"width": 90,
			}
		)
	cols.append({"fieldname": "return_status", "label": _("Return Status"), "fieldtype": "Data", "width": 110})
	return cols


def _build_where(filters, fn, pending):
	conditions = [
		"gle.account = %s",
		"IFNULL(gle.is_cancelled, 0) = 0",
		"gle.company = %s",
	]
	values = [pending, filters.get("company")]
	if not cint(filters.get("include_returned", 1)):
		conditions.append("IFNULL(c.return_status, '') != 'Returned'")
	if filters.get("supplier"):
		conditions.append("gle.party_type = %s AND gle.party = %s")
		values.extend(["Supplier", filters.supplier])
	if filters.get("shipping_line"):
		conditions.append("(IFNULL(c.owner_carrier, '') = %s OR mb.shipping_line = %s)")
		values.extend([filters.shipping_line, filters.shipping_line])
	if filters.get("master_bill"):
		conditions.append("c.master_bill = %s")
		values.append(filters.master_bill)
	if filters.get("container"):
		conditions.append("gle.`{0}` = %s".format(fn))
		values.append(filters.container)
	if filters.get("job_number"):
		conditions.append("c.current_job_number = %s")
		values.append(filters.job_number)
	if filters.get("from_date"):
		conditions.append("gle.posting_date >= %s")
		values.append(filters.from_date)
	if filters.get("to_date"):
		conditions.append("gle.posting_date <= %s")
		values.append(filters.to_date)
	return " AND ".join(conditions), values


def _base_setup(filters):
	filters = frappe._dict(filters or {})
	fn = get_accounting_dimension_fieldname("Container")
	if not fn or not frappe.db.has_column("GL Entry", fn):
		return None, None, filters
	if not filters.get("company"):
		filters.company = frappe.defaults.get_user_default("Company")
	pending = None
	if filters.get("company"):
		pending = SeaFreightSettings.get_default_value(
			filters.company, "container_deposit_pending_refund_account"
		)
	if not pending:
		return None, None, filters
	return fn, pending, filters


def get_data(filters, ranges=None):
	ranges = ranges or _parse_ageing_ranges(filters.get("range"))
	fn, pending, filters = _base_setup(filters)
	if not fn or not pending:
		return []

	age_as_on = _age_as_on(filters)
	where_sql, bind = _build_where(filters, fn, pending)

	sql = """
		SELECT
			gle.`{fn}` AS container_id,
			gle.company AS gle_company,
			gle.posting_date,
			gle.debit,
			gle.credit,
			c.container_number AS equipment_no,
			c.owner_carrier,
			c.master_bill,
			mb.shipping_line AS mb_shipping_line,
			c.return_status,
			c.current_job_number AS job_number
		FROM `tabGL Entry` gle
		INNER JOIN `tabContainer` c ON c.name = gle.`{fn}`
		LEFT JOIN `tabMaster Bill` mb ON mb.name = c.master_bill
		WHERE {where_sql}
		ORDER BY c.container_number, gle.posting_date, gle.name
	""".format(fn=fn, where_sql=where_sql)

	raw = frappe.db.sql(sql, tuple(bind), as_dict=True)
	groups = OrderedDict()
	for row in raw:
		cid = row.get("container_id")
		if not cid:
			continue
		if cid not in groups:
			groups[cid] = {
				"company": row.get("gle_company"),
				"debit": 0.0,
				"credit": 0.0,
				"oldest_posting": None,
				"gl_line_count": 0,
				"equipment_no": row.get("equipment_no"),
				"owner_carrier": row.get("owner_carrier"),
				"master_bill": row.get("master_bill"),
				"mb_shipping_line": row.get("mb_shipping_line"),
				"return_status": row.get("return_status"),
				"job_number": row.get("job_number"),
			}
		g = groups[cid]
		g["debit"] += flt(row.get("debit"))
		g["credit"] += flt(row.get("credit"))
		g["gl_line_count"] += 1
		pd = row.get("posting_date")
		if pd is not None and (g["oldest_posting"] is None or pd < g["oldest_posting"]):
			g["oldest_posting"] = pd

	out = []
	n_buckets = len(ranges) + 2
	hide_zero = cint(filters.get("hide_zero_balance", 1))

	for cid, g in sorted(groups.items(), key=lambda kv: ((kv[1].get("equipment_no") or ""), kv[0])):
		dr = flt(g["debit"])
		cr = flt(g["credit"])
		net = dr - cr
		if hide_zero and abs(net) <= 1e-7:
			continue

		oc = (g.get("owner_carrier") or "").strip()
		sl = oc if oc else (g.get("mb_shipping_line") or "")
		if not sl and g.get("master_bill"):
			sl = frappe.db.get_value("Master Bill", g["master_bill"], "shipping_line") or ""

		row = {
			"container_number": cid,
			"equipment_no": g.get("equipment_no"),
			"company": g.get("company"),
			"shipping_line": sl,
			"job_number": g.get("job_number"),
			"master_bill": g.get("master_bill"),
			"debit": dr,
			"credit": cr,
			"line_amount": net,
			"gl_line_count": cint(g["gl_line_count"]),
		}
		d = g.get("oldest_posting")
		row["deposit_paid_date"] = d
		age_days = date_diff(age_as_on, d) if d else 0
		row["days_outstanding"] = cint(age_days)
		row["return_status"] = g.get("return_status")
		bi = _age_bucket_index(age_days, ranges)
		for i in range(n_buckets):
			row["range{0}".format(i)] = net if bi == i else 0.0
		out.append(row)
	return out


def _build_ageing_bar_chart(data, bucket_labels):
	if not data or not bucket_labels:
		return None
	n = len(bucket_labels)
	sums = [0.0] * n
	for row in data:
		for i in range(n):
			sums[i] += flt(row.get("range{0}".format(i)))
	if not any(sums):
		return None
	return {
		"data": {
			"labels": bucket_labels,
			"datasets": [{"name": _("Pending deposit (net)"), "values": sums}],
		},
		"type": "bar",
		"fieldtype": "Currency",
	}
