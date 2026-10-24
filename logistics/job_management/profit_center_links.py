# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt
"""Profit Center link fields only offer active records.

DocType and Custom Field links store ``link_filters`` for Is Active.
Report filters, web forms, and dialogs have no place to store that filter,
so link search itself drops inactive Profit Centers.
"""

from __future__ import annotations

import json

ACTIVE_FILTER_ROW = ["Profit Center", "is_active", "=", 1]


def merge_active_link_filters(raw):
	"""Return link_filters JSON that includes Is Active, or None when it already does."""
	if raw is None or raw == "" or raw == "null":
		rows = []
	elif isinstance(raw, list):
		rows = list(raw)
	else:
		rows = json.loads(raw)
	if not isinstance(rows, list):
		return None
	for row in rows:
		if isinstance(row, (list, tuple)) and len(row) >= 2 and row[1] == "is_active":
			return None
	rows.append(list(ACTIVE_FILTER_ROW))
	return json.dumps(rows)


def _parse_filters(filters):
	if isinstance(filters, str):
		text = filters.strip()
		if not text:
			return {}
		return json.loads(text)
	return filters


def _include_disabled(value) -> bool:
	if isinstance(value, (list, tuple)):
		if len(value) >= 2 and value[0] in ("=", "=="):
			value = value[1]
		else:
			return False
	return value in (1, "1", True, "true", "True")


def _is_active_value(value) -> str:
	"""Classify one is_active filter value as active or other."""
	if value in (1, "1", True):
		return "active"
	if isinstance(value, (list, tuple)) and len(value) >= 2 and value[0] in ("=", "==") and value[1] in (1, "1", True):
		return "active"
	return "other"


def profit_center_filter_constraint(filters) -> str | None:
	"""How a link search treats inactive Profit Centers.

	``None`` means the caller did not say. ``active`` keeps only active rows.
	``all`` is Frappe's include_disabled escape hatch. ``other`` is an explicit
	is_active condition the caller already set.
	"""
	try:
		parsed = _parse_filters(filters)
	except (TypeError, ValueError):
		return None
	if parsed is None:
		return None
	if isinstance(parsed, dict):
		if _include_disabled(parsed.get("include_disabled")):
			return "all"
		if "is_active" not in parsed:
			return None
		return _is_active_value(parsed.get("is_active"))
	if isinstance(parsed, list):
		found = None
		for row in parsed:
			if not isinstance(row, (list, tuple)) or not row:
				continue
			if len(row) >= 4:
				field, operator, value = row[1], row[2], row[3]
			elif len(row) >= 3:
				field, operator, value = row[0], row[1], row[2]
			else:
				continue
			if field == "include_disabled" and operator in ("=", "==") and _include_disabled(value):
				return "all"
			if field != "is_active":
				continue
			if operator in ("=", "==") and value in (1, "1", True):
				found = "active"
			else:
				return "other"
		return found
	return None


def active_profit_center_link_filters(filters):
	"""Filters for a Profit Center link search. Inactive rows stay out."""
	try:
		parsed = _parse_filters(filters)
	except (TypeError, ValueError):
		return filters
	kind = profit_center_filter_constraint(parsed)
	if kind in ("all", "active", "other"):
		return filters
	if parsed is None:
		parsed = {}
	if isinstance(parsed, dict):
		updated = dict(parsed)
		updated["is_active"] = 1
		return updated
	if isinstance(parsed, list):
		return [*parsed, list(ACTIVE_FILTER_ROW)]
	return filters


def allows_inactive_profit_centers(filters) -> bool:
	return profit_center_filter_constraint(filters) in ("all", "other")


def _row_name(row):
	if isinstance(row, dict):
		return row.get("name") or row.get("value")
	if isinstance(row, (list, tuple)) and row:
		return row[0]
	if isinstance(row, str):
		return row
	return None


def keep_active_profit_center_rows(values, active_names=None):
	"""Drop inactive Profit Centers from a link-search result."""
	if not values:
		return values
	if active_names is None:
		active_names = _active_names_from_db(values)
		if active_names is None:
			return values
	active = set(active_names)
	return [row for row in values if _row_name(row) in active]


def _active_names_from_db(values):
	try:
		import frappe
	except Exception:
		return None
	names = [name for row in values if (name := _row_name(row))]
	if not names:
		return set()
	try:
		if not frappe.db.has_column("Profit Center", "is_active"):
			return None
		# Names already came from link search. Read the flag even when the user
		# cannot open the Profit Center list, so ignore_user_permissions links
		# still hide inactive rows.
		return set(
			frappe.get_all(
				"Profit Center",
				filters={"name": ["in", names], "is_active": 1},
				pluck="name",
				ignore_permissions=True,
			)
		)
	except Exception:
		return None


def install_active_profit_center_link_search() -> None:
	"""Link search for Profit Center hides inactive records on every link field."""
	import sys

	import frappe
	import frappe.desk.search as search_mod

	current = search_mod.search_widget
	if getattr(current, "_logistics_active_profit_center", False):
		return

	original = current

	def search_widget(
		doctype,
		txt,
		query=None,
		searchfield=None,
		start=0,
		page_length=10,
		filters=None,
		filter_fields=None,
		as_dict=False,
		reference_doctype=None,
		ignore_user_permissions=False,
		link_fieldname=None,
		for_link_validation=False,
		query_filters_as_dict=False,
	):
		if doctype == "Profit Center":
			filters = active_profit_center_link_filters(filters)
		values = original(
			doctype,
			txt,
			query,
			searchfield,
			start,
			page_length,
			filters,
			filter_fields,
			as_dict,
			reference_doctype,
			ignore_user_permissions,
			link_fieldname=link_fieldname,
			for_link_validation=for_link_validation,
			query_filters_as_dict=query_filters_as_dict,
		)
		if doctype == "Profit Center" and not allows_inactive_profit_centers(filters):
			values = keep_active_profit_center_rows(values)
		return values

	search_widget.__name__ = "search_widget"
	search_widget.__module__ = getattr(original, "__module__", "frappe.desk.search")
	wrapped = frappe.whitelist()(search_widget)
	wrapped._logistics_active_profit_center = True
	for module in list(sys.modules.values()):
		if module is None:
			continue
		try:
			if getattr(module, "search_widget", None) is original:
				module.search_widget = wrapped
		except Exception:
			continue
