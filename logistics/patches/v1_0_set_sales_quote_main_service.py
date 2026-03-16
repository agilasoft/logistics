# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Set main_service on Sales Quote from is_* checkboxes, services, or charges."""

import frappe


def execute():
	"""Set main_service for existing Sales Quotes that don't have it."""
	if "main_service" not in frappe.db.get_table_columns("Sales Quote"):
		return

	quotes = frappe.get_all("Sales Quote", filters={"main_service": ["in", ["", None]]}, pluck="name")
	for sq_name in quotes:
		main = _derive_main_service(sq_name)
		if main:
			frappe.db.set_value("Sales Quote", sq_name, "main_service", main, update_modified=False)

	frappe.db.commit()


def _derive_main_service(sq_name):
	"""Derive main_service from is_* (legacy), services (is_main), or first charge."""
	# 1. From Sales Quote Service with is_main=1
	if frappe.db.table_exists("Sales Quote Service"):
		svc = frappe.db.get_value(
			"Sales Quote Service",
			{"parent": sq_name, "parenttype": "Sales Quote", "is_main": 1},
			"service_type",
		)
		if svc:
			return svc
		# Fallback: first service by priority
		svc = frappe.db.get_value(
			"Sales Quote Service",
			{"parent": sq_name, "parenttype": "Sales Quote"},
			"service_type",
			order_by="idx asc",
		)
		if svc:
			return svc

	# 2. From is_* checkboxes (legacy)
	cols = frappe.db.get_table_columns("Sales Quote") or {}
	order = ["Sea", "Air", "Transport", "Customs", "Warehousing"]
	checkbox_map = {"Sea": "is_sea", "Air": "is_air", "Transport": "is_transport", "Customs": "is_customs", "Warehousing": "is_warehousing"}
	for st in order:
		col = checkbox_map.get(st)
		if col and col in cols:
			val = frappe.db.get_value("Sales Quote", sq_name, col)
			if val:
				return st

	# 3. From first charge's service_type
	chg = frappe.db.get_value(
		"Sales Quote Charge",
		{"parent": sq_name, "parenttype": "Sales Quote"},
		"service_type",
		order_by="idx asc",
	)
	if chg:
		return chg

	return None
