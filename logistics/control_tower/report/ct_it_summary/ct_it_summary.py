# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.utils import flt, nowdate


def execute(filters=None):
	filters = frappe._dict(filters or {})
	year = int(filters.get("fiscal_year_yyyy") or nowdate()[:4])
	ys, ye = "{0}-01-01".format(year), "{0}-12-31".format(year)

	rs = frappe.db.sql(
		"""
		SELECT COUNT(*) AS n,
		       AVG(CASE WHEN status IN ('Resolved','Closed') THEN tat_hours END) AS avg_tat
		FROM `tabIT Ticket`
		WHERE opened_on BETWEEN %s AND %s
		""",
		(ys + " 00:00:00", ye + " 23:59:59"),
	)
	tickets = int(rs[0][0]) if rs and rs[0] and rs[0][0] is not None else 0
	avg_tat = flt(rs[0][1]) if rs and rs[0] and rs[0][1] is not None else 0.0

	incidents = frappe.db.count("IT Security Incident", filters={"incident_date": ["between", [ys, ye]]}) or 0

	uptime_rs = frappe.db.sql(
		"""
		SELECT AVG(uptime_pct) AS sys_uptime
		FROM `tabIT Uptime Log`
		WHERE period BETWEEN %s AND %s AND kind = 'System'
		""",
		(ys, ye),
	)
	system_uptime = flt(uptime_rs[0][0]) if uptime_rs and uptime_rs[0] and uptime_rs[0][0] is not None else 0.0

	net_rs = frappe.db.sql(
		"""
		SELECT AVG(uptime_pct) AS net_uptime
		FROM `tabIT Uptime Log`
		WHERE period BETWEEN %s AND %s AND kind = 'Network'
		""",
		(ys, ye),
	)
	network_uptime = flt(net_rs[0][0]) if net_rs and net_rs[0] and net_rs[0][0] is not None else 0.0

	columns = [
		{"fieldname": "metric", "label": _("Metric"), "fieldtype": "Data", "width": 280},
		{"fieldname": "value", "label": _("Value"), "fieldtype": "Float", "width": 180},
	]
	rows = [
		{"metric": _("Tickets Served (YTD)"), "value": tickets},
		{"metric": _("Average TAT per Ticket (Hours)"), "value": flt(avg_tat, 2)},
		{"metric": _("System Uptime % (Avg)"), "value": flt(system_uptime, 2)},
		{"metric": _("Network Uptime % (Avg)"), "value": flt(network_uptime, 2)},
		{"metric": _("Security Incidents (YTD)"), "value": incidents},
	]
	chart = {
		"data": {
			"labels": [_("System Uptime"), _("Network Uptime")],
			"datasets": [{"name": _("Uptime %"), "values": [system_uptime, network_uptime]}],
		},
		"type": "bar",
		"title": _("System / Network Uptime"),
	}
	report_summary = [
		{"label": _("Tickets YTD"), "value": tickets, "datatype": "Int", "indicator": "Blue"},
		{"label": _("Avg TAT (h)"), "value": flt(avg_tat, 2), "datatype": "Float", "indicator": "Grey"},
		{"label": _("System Uptime %"), "value": flt(system_uptime, 2), "datatype": "Percent", "indicator": "Green" if system_uptime >= 99 else "Orange"},
		{"label": _("Security Incidents YTD"), "value": incidents, "datatype": "Int", "indicator": "Red"},
	]
	return columns, rows, None, chart, report_summary
