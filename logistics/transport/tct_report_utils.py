# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Shared filters / SQL helpers for Transport Control Tower detail reports."""

from __future__ import unicode_literals

import frappe
from frappe.utils import cint, getdate, nowdate

OPEN_EXCLUDES = ("Completed", "Closed", "Cancelled")


def default_date_range(fiscal_year=None):
	year = cint(fiscal_year) or cint(nowdate()[:4])
	from_date = "{0}-01-01".format(year)
	today = nowdate()
	year_end = "{0}-12-31".format(year)
	to_date = today if str(today)[:4] == str(year) else year_end
	return from_date, to_date


def date_bounds(filters):
	"""Effective from/to dates; falls back to fiscal year window."""
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	if from_date and to_date:
		fd, td = getdate(from_date), getdate(to_date)
		if fd > td:
			fd, td = td, fd
		return str(fd), str(td)
	return default_date_range(filters.get("fiscal_year"))


def normalize_filters(filters=None):
	filters = frappe._dict(filters or {})
	# A missing company means the viewer's default Company (dashboard charts
	# omit the key). An explicit blank company stays blank so a cleared
	# report filter still means every company.
	if "company" not in filters:
		company = (frappe.defaults.get_user_default("Company") or "").strip()
	else:
		company = (filters.get("company") or "").strip()
	out = frappe._dict({
		"company": company,
		"branch": (filters.get("branch") or "").strip(),
		"cost_center": (filters.get("cost_center") or "").strip(),
		"profit_center": (filters.get("profit_center") or "").strip(),
		"vehicle_type": (filters.get("vehicle_type") or "").strip(),
		"scope": (filters.get("scope") or "Open").strip() or "Open",
	})
	fy = filters.get("fiscal_year")
	out["fiscal_year"] = cint(fy) if fy else cint(nowdate()[:4])
	out["limit"] = max(1, min(50, cint(filters.get("limit") or 10)))

	fd = filters.get("from_date")
	td = filters.get("to_date")
	if not fd or not td:
		default_from, default_to = default_date_range(out["fiscal_year"])
		fd = fd or default_from
		td = td or default_to
	fd, td = getdate(fd), getdate(td)
	if fd > td:
		fd, td = td, fd
	out["from_date"] = str(fd)
	out["to_date"] = str(td)
	return out


def dim_clauses(filters, prefix=""):
	conditions = []
	values = []
	for key in ("company", "branch", "cost_center", "profit_center"):
		val = filters.get(key)
		if not val:
			continue
		conditions.append("{0}{1} = %s".format(prefix, key))
		values.append(val)
	return conditions, values


def vehicle_type_clause(filters, prefix=""):
	vehicle_type = filters.get("vehicle_type")
	if not vehicle_type:
		return [], []
	return ["{0}vehicle_type = %s".format(prefix)], [vehicle_type]
