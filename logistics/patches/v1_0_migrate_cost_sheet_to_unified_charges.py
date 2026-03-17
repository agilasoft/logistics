# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Migrate Cost Sheet from per-service tabs to unified Cost Sheet Charge structure."""

import frappe


# Map calculation_method from old rate doctypes to cost_calculation_method
CALC_METHOD_MAP = {
	"Transport Weight": "Per Unit",
	"Transport Volume": "Per Unit",
	"Fixed Amount": "Fixed Amount",
	"Flat Rate": "Flat Rate",
	"Per Package": "Per Unit",
	"Per Unit": "Per Unit",
	"Per Piece": "Per Unit",
	"Package Count": "Per Unit",
	"Minimum Charge": "Fixed Amount",
	"Maximum Charge": "Fixed Amount",
	"Percentage": "Percentage",
	"Per Unit\nFixed Amount\nBase Plus Additional\nFirst Plus Additional\nPercentage\nLocation-based": None,
}


def execute():
	"""Migrate Cost Sheet rate data from old tables to Cost Sheet Charge."""
	if not frappe.db.table_exists("Cost Sheet Charge"):
		return

	cost_sheets = frappe.get_all("Cost Sheet", pluck="name")
	for cs_name in cost_sheets:
		_migrate_cost_sheet(cs_name)

	frappe.db.commit()


def _migrate_cost_sheet(cs_name):
	"""Migrate one Cost Sheet from old rate tables to Cost Sheet Charge."""
	existing = frappe.db.count("Cost Sheet Charge", {"parent": cs_name, "parenttype": "Cost Sheet"})
	if existing > 0:
		return

	cs_doc = frappe.get_cached_doc("Cost Sheet", cs_name)
	charges = []

	# Air Freight Rate
	if frappe.db.table_exists("Air Freight Rate"):
		for row in frappe.get_all(
			"Air Freight Rate",
			filters={"parent": cs_name, "parenttype": "Cost Sheet"},
			fields=["item_code", "calculation_method", "rate_value", "currency", "minimum_charge", "maximum_charge",
				"origin_airport", "destination_airport", "airline"]
		):
			charges.append(_map_air_rate_to_charge(row, cs_doc.currency))

	# Sea Freight Rate
	if frappe.db.table_exists("Sea Freight Rate"):
		for row in frappe.get_all(
			"Sea Freight Rate",
			filters={"parent": cs_name, "parenttype": "Cost Sheet"},
			fields=["item_code", "calculation_method", "rate_value", "currency", "minimum_charge", "maximum_charge",
				"origin_port", "destination_port", "shipping_line", "service_type"]
		):
			charges.append(_map_sea_rate_to_charge(row, cs_doc.currency))

	# Transport Rate
	if frappe.db.table_exists("Transport Rate"):
		for row in frappe.get_all(
			"Transport Rate",
			filters={"parent": cs_name, "parenttype": "Cost Sheet"},
			fields=["item_code", "calculation_method", "rate", "currency", "minimum_charge", "maximum_charge",
				"load_type", "vehicle_type", "container_type", "location_type", "location_from", "location_to"]
		):
			charges.append(_map_transport_rate_to_charge(row, cs_doc.currency))

	# Warehouse Rate
	if frappe.db.table_exists("Warehouse Rate"):
		for row in frappe.get_all(
			"Warehouse Rate",
			filters={"parent": cs_name, "parenttype": "Cost Sheet"},
			fields=["item_charge", "calculation_method", "rate", "currency", "minimum_charge", "maximum_charge"]
		):
			charges.append(_map_warehouse_rate_to_charge(row, cs_doc.currency))

	# Customs Rate
	if frappe.db.table_exists("Customs Rate"):
		for row in frappe.get_all(
			"Customs Rate",
			filters={"parent": cs_name, "parenttype": "Cost Sheet"},
			fields=["item_code", "calculation_method", "rate_value", "currency", "minimum_charge", "maximum_charge"]
		):
			charges.append(_map_customs_rate_to_charge(row, cs_doc.currency))

	for ch in charges:
		row = frappe.new_doc("Cost Sheet Charge")
		row.parent = cs_name
		row.parenttype = "Cost Sheet"
		row.parentfield = "charges"
		for k, v in ch.items():
			if v is not None:
				setattr(row, k, v)
		row.insert(ignore_permissions=True)


def _map_air_rate_to_charge(row, default_currency):
	calc = CALC_METHOD_MAP.get(row.get("calculation_method"), "Per Unit")
	return {
		"service_type": "Air",
		"item_code": row.get("item_code"),
		"cost_calculation_method": calc or "Per Unit",
		"unit_cost": row.get("rate_value"),
		"cost_currency": row.get("currency") or default_currency,
		"cost_minimum_charge": row.get("minimum_charge"),
		"cost_maximum_charge": row.get("maximum_charge"),
		"origin_port": row.get("origin_airport"),
		"destination_port": row.get("destination_airport"),
		"airline": row.get("airline"),
	}


def _map_sea_rate_to_charge(row, default_currency):
	calc = CALC_METHOD_MAP.get(row.get("calculation_method"), "Per Unit")
	return {
		"service_type": "Sea",
		"item_code": row.get("item_code"),
		"cost_calculation_method": calc or "Per Unit",
		"unit_cost": row.get("rate_value"),
		"cost_currency": row.get("currency") or default_currency,
		"cost_minimum_charge": row.get("minimum_charge"),
		"cost_maximum_charge": row.get("maximum_charge"),
		"origin_port": row.get("origin_port"),
		"destination_port": row.get("destination_port"),
		"shipping_line": row.get("shipping_line"),
		"transport_mode": row.get("service_type") if row.get("service_type") in ("FCL", "LCL") else None,
	}


def _map_transport_rate_to_charge(row, default_currency):
	calc = CALC_METHOD_MAP.get(row.get("calculation_method"), "Per Unit")
	return {
		"service_type": "Transport",
		"item_code": row.get("item_code"),
		"cost_calculation_method": calc or "Per Unit",
		"unit_cost": row.get("rate"),
		"cost_currency": row.get("currency") or default_currency,
		"cost_minimum_charge": row.get("minimum_charge"),
		"cost_maximum_charge": row.get("maximum_charge"),
		"load_type": row.get("load_type"),
		"vehicle_type": row.get("vehicle_type"),
		"container_type": row.get("container_type"),
		"location_type": row.get("location_type"),
		"location_from": row.get("location_from"),
		"location_to": row.get("location_to"),
	}


def _map_warehouse_rate_to_charge(row, default_currency):
	calc = CALC_METHOD_MAP.get(row.get("calculation_method"), "Per Unit")
	return {
		"service_type": "Warehousing",
		"item_code": row.get("item_charge"),
		"cost_calculation_method": calc or "Per Unit",
		"unit_cost": row.get("rate"),
		"cost_currency": row.get("currency") or default_currency,
		"cost_minimum_charge": row.get("minimum_charge"),
		"cost_maximum_charge": row.get("maximum_charge"),
	}


def _map_customs_rate_to_charge(row, default_currency):
	calc = CALC_METHOD_MAP.get(row.get("calculation_method"), "Per Unit")
	return {
		"service_type": "Customs",
		"item_code": row.get("item_code"),
		"cost_calculation_method": calc or "Per Unit",
		"unit_cost": row.get("rate_value"),
		"cost_currency": row.get("currency") or default_currency,
		"cost_minimum_charge": row.get("minimum_charge"),
		"cost_maximum_charge": row.get("maximum_charge"),
	}
