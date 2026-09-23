# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

from collections import Counter

from frappe import _

from logistics.analytics_reports.bootstrap import series_chart
from logistics.high_value.hv_analytics import (
	apply_job_filters,
	load_report_context,
	sort_jobs_by_sla,
)


def execute(filters=None):
	filters = filters or {}
	columns = _columns()
	_brands, _quotes, jobs = load_report_context(filters)
	rows = sort_jobs_by_sla(apply_job_filters(jobs, filters))
	chart = _chart(rows)
	return columns, rows, None, chart, _summary(rows)


def _columns():
	return [
		{
			"label": _("Job"),
			"fieldname": "name",
			"fieldtype": "Dynamic Link",
			"options": "doctype",
			"width": 140,
		},
		{"label": _("Doctype"), "fieldname": "doctype", "fieldtype": "Data", "width": 130},
		{"label": _("Modality"), "fieldname": "modality", "fieldtype": "Data", "width": 90},
		{"label": _("Brand"), "fieldname": "hv_brand", "fieldtype": "Link", "options": "HV Brands", "width": 110},
		{"label": _("Brand Name"), "fieldname": "brand_name", "fieldtype": "Data", "width": 140},
		{"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 140},
		{"label": _("Status"), "fieldname": "job_status", "fieldtype": "Data", "width": 110},
		{"label": _("SLA"), "fieldname": "sla_status", "fieldtype": "Data", "width": 100},
		{"label": _("SLA Target"), "fieldname": "sla_target_date", "fieldtype": "Date", "width": 110},
		{"label": _("Owner"), "fieldname": "owner", "fieldtype": "Link", "options": "User", "width": 140},
		{
			"label": _("Sales Quote"),
			"fieldname": "sales_quote",
			"fieldtype": "Link",
			"options": "Sales Quote",
			"width": 130,
		},
	]


def _chart(rows):
	c = Counter((r.get("sla_status") or _("Blank")) for r in rows)
	order = ["Breached", "At Risk", "On Track", "Not Applicable", _("Blank")]
	data = [{"sla_status": k, "jobs": c[k]} for k in order if c.get(k)]
	for k, n in c.items():
		if k not in order:
			data.append({"sla_status": k, "jobs": n})
	return series_chart(data, "sla_status", "jobs")


def _summary(rows):
	breached = sum(1 for r in rows if (r.get("sla_status") or "") == "Breached")
	at_risk = sum(1 for r in rows if (r.get("sla_status") or "") == "At Risk")
	return [
		{"label": _("Jobs"), "value": len(rows), "indicator": "blue"},
		{"label": _("SLA Breached"), "value": breached, "indicator": "red" if breached else "green"},
		{"label": _("SLA At Risk"), "value": at_risk, "indicator": "orange" if at_risk else "green"},
	]
