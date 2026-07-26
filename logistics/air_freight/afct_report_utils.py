# -*- coding: utf-8 -*-
# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Shared filters / SQL helpers for Air Freight Control Tower detail reports."""

from __future__ import unicode_literals

import frappe
from frappe import _
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
	out = frappe._dict({
		"company": (filters.get("company") or "").strip(),
		"branch": (filters.get("branch") or "").strip(),
		"cost_center": (filters.get("cost_center") or "").strip(),
		"profit_center": (filters.get("profit_center") or "").strip(),
		"unloco": (filters.get("unloco") or "").strip(),
		"airline": (filters.get("airline") or "").strip(),
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


def year_bounds(fiscal_year):
	"""Backward-compatible alias: full calendar year."""
	year = cint(fiscal_year) or cint(nowdate()[:4])
	return "{0}-01-01".format(year), "{0}-12-31".format(year)


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


def unloco_clause(filters, prefix=""):
	unloco = filters.get("unloco")
	if not unloco:
		return [], []
	return (
		["({0}origin_port = %s OR {0}destination_port = %s)".format(prefix)],
		[unloco, unloco],
	)


def report_roles():
	return [
		{"role": "System Manager"},
		{"role": "Air Freight Manager"},
		{"role": "Air Freight User"},
		{"role": "Control Tower Manager"},
		{"role": "Control Tower Viewer"},
	]
