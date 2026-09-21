# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

from collections import Counter

from frappe import _
from frappe.utils import flt

from logistics.analytics_reports.bootstrap import series_chart
from logistics.high_value.hv_analytics import apply_quote_filters, load_report_context


def execute(filters=None):
	filters = filters or {}
	columns = _columns()
	_brands, quotes, _jobs = load_report_context(filters)
	rows = apply_quote_filters(quotes, filters)
	rows.sort(key=lambda r: (r.get("date") or r.get("creation") or "", r.get("name") or ""), reverse=True)
	chart = _chart(rows)
	return columns, rows, None, chart, _summary(rows)


def _columns():
	return [
		{"label": _("Quote"), "fieldname": "name", "fieldtype": "Link", "options": "Sales Quote", "width": 140},
		{"label": _("Brand"), "fieldname": "hv_brand", "fieldtype": "Link", "options": "HV Brands", "width": 110},
		{"label": _("Brand Name"), "fieldname": "brand_name", "fieldtype": "Data", "width": 140},
		{"label": _("Customer"), "fieldname": "customer", "fieldtype": "Link", "options": "Customer", "width": 140},
		{"label": _("Status"), "fieldname": "status", "fieldtype": "Data", "width": 100},
		{"label": _("Date"), "fieldname": "date", "fieldtype": "Date", "width": 100},
		{"label": _("Valid Until"), "fieldname": "valid_until", "fieldtype": "Date", "width": 100},
		{"label": _("Est. Revenue"), "fieldname": "total_estimated_revenue", "fieldtype": "Currency", "width": 120},
		{"label": _("Est. Cost"), "fieldname": "total_estimated_cost", "fieldtype": "Currency", "width": 120},
		{"label": _("Est. Profit"), "fieldname": "estimated_profit", "fieldtype": "Currency", "width": 120},
		{"label": _("Margin %"), "fieldname": "estimated_margin_pct", "fieldtype": "Percent", "width": 90},
		{"label": _("Owner"), "fieldname": "owner", "fieldtype": "Link", "options": "User", "width": 140},
		{"label": _("Company"), "fieldname": "company", "fieldtype": "Link", "options": "Company", "width": 130},
	]


def _chart(rows):
	c = Counter((r.get("status") or _("Blank")) for r in rows)
	data = [{"status": k, "quotes": n} for k, n in c.items()]
	return series_chart(data, "status", "quotes")


def _summary(rows):
	converted = sum(1 for r in rows if (r.get("status") or "") == "Converted")
	revenue = sum(flt(r.get("total_estimated_revenue")) for r in rows)
	return [
		{"label": _("Quotes"), "value": len(rows), "indicator": "blue"},
		{"label": _("Converted"), "value": converted, "indicator": "green"},
		{"label": _("Est. Revenue"), "value": flt(revenue), "indicator": "blue"},
	]
