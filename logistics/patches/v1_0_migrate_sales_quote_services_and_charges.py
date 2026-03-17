# -*- coding: utf-8 -*-
# Copyright (c) 2026, www.agilasoft.com and contributors
"""Migrate Sales Quote from per-service tabs to Services + Charges structure."""

import frappe


def _sanitize_select(meta, fieldname, value):
	"""Return value if valid for Select field, else first option or None."""
	if value is None:
		return None
	field = meta.get_field(fieldname)
	if not field or field.fieldtype != "Select":
		return value
	opts = (field.options or "").split("\n")
	opts = [o.strip() for o in opts if o.strip()]
	if str(value).strip() in opts:
		return value
	return opts[0] if opts else None


def execute():
	"""Populate Sales Quote Service and Sales Quote Charge from old structure."""
	if not frappe.db.table_exists("Sales Quote Service") or not frappe.db.table_exists("Sales Quote Charge"):
		return

	# Service type order for is_main (first checked = main)
	SERVICE_ORDER = ["Sea", "Air", "Transport", "Customs", "Warehousing"]
	CHECKBOX_MAP = {
		"Sea": "is_sea",
		"Air": "is_air",
		"Transport": "is_transport",
		"Customs": "is_customs",
		"Warehousing": "is_warehousing",
	}
	OLD_TABLE_MAP = {
		"Sea": "Sales Quote Sea Freight",
		"Air": "Sales Quote Air Freight",
		"Transport": "Sales Quote Transport",
		"Customs": "Sales Quote Customs",
		"Warehousing": "Sales Quote Warehouse",
	}

	quotes = frappe.get_all("Sales Quote", pluck="name")
	for sq_name in quotes:
		_migrate_quote_services(sq_name, SERVICE_ORDER, CHECKBOX_MAP)
		_migrate_quote_charges(sq_name, OLD_TABLE_MAP)

	frappe.db.commit()


def _migrate_quote_services(sq_name, service_order, checkbox_map):
	"""Create Sales Quote Service rows from is_* checkboxes."""
	existing = frappe.db.count("Sales Quote Service", {"parent": sq_name, "parenttype": "Sales Quote"})
	if existing > 0:
		return

	doc = frappe.get_cached_doc("Sales Quote", sq_name)
	services_added = []
	main_set = False
	for st in service_order:
		checkbox = checkbox_map.get(st)
		if not checkbox or not getattr(doc, checkbox, 0):
			continue
		row = frappe.new_doc("Sales Quote Service")
		row.parent = sq_name
		row.parenttype = "Sales Quote"
		row.parentfield = "services"
		row.service_type = st
		row.is_main = 0 if main_set else 1
		if not main_set:
			main_set = True
		row.insert(ignore_permissions=True)
		services_added.append(row)


def _migrate_quote_charges(sq_name, old_table_map):
	"""Copy charge rows from old tables to Sales Quote Charge."""
	existing = frappe.db.count("Sales Quote Charge", {"parent": sq_name, "parenttype": "Sales Quote"})
	if existing > 0:
		return

	# Field mapping: old table field -> Sales Quote Charge field (same name if not listed)
	COMMON_FIELDS = [
		"item_code", "item_name", "charge_type", "charge_category",
		"calculation_method", "unit_rate", "unit_type", "currency",
		"quantity", "minimum_quantity", "minimum_charge", "maximum_charge", "base_amount",
		"uom", "estimated_revenue", "revenue_calc_notes",
		"cost_calculation_method", "unit_cost", "cost_unit_type", "cost_currency",
		"cost_quantity", "cost_minimum_quantity", "cost_minimum_charge",
		"cost_maximum_charge", "cost_base_amount", "cost_uom",
		"estimated_cost", "cost_calc_notes",
		"tariff", "revenue_tariff", "cost_tariff",
		"use_tariff_in_revenue", "use_tariff_in_cost", "bill_to", "pay_to",
	]
	# Service-specific field mapping (old_name -> new_name if different)
	SERVICE_FIELD_MAP = {
		"Sea": {"sea_house_type": "sea_house_type", "freight_agent_sea": "freight_agent_sea"},
		"Air": {"air_house_type": "air_house_type", "freight_agent": "freight_agent"},
		"Transport": {},
		"Customs": {"charge_category": "charge_category"},  # Customs has charge_category
		"Warehousing": {},  # Warehouse uses "item" not "item_code" - handle below
	}

	for service_type, old_dt in old_table_map.items():
		if not frappe.db.table_exists(old_dt):
			continue
		old_rows = frappe.get_all(
			old_dt,
			filters={"parent": sq_name, "parenttype": "Sales Quote"},
			fields=["*"],
			order_by="idx",
		)
		meta = frappe.get_meta("Sales Quote Charge")
		for old in old_rows:
			charge = frappe.new_doc("Sales Quote Charge")
			charge.parent = sq_name
			charge.parenttype = "Sales Quote"
			charge.parentfield = "charges"
			charge.service_type = service_type
			charge.charge_group = "Other"  # Default; can be refined later
			charge.quotation_type = old.get("quotation_type") or "Regular"

			# Copy common fields with validation fallback
			for f in COMMON_FIELDS:
				if f in old and old[f] is not None:
					if hasattr(charge, f):
						val = _sanitize_select(meta, f, old[f])
						if val is not None:
							charge.set(f, val)

			# Warehousing uses "item" not "item_code"
			if service_type == "Warehousing" and "item" in old and old["item"]:
				charge.item_code = old["item"]
				if "item_name" in old:
					charge.item_name = old["item_name"]

			# Copy service-specific fields
			svc_map = SERVICE_FIELD_MAP.get(service_type, {})
			for old_f, new_f in svc_map.items():
				if old_f in old and old[old_f] is not None:
					val = _sanitize_select(meta, new_f, old[old_f]) if meta.get_field(new_f) and meta.get_field(new_f).fieldtype == "Select" else old[old_f]
					if val is not None:
						charge.set(new_f, val)
			# Also copy any service params that exist in old and in charge
			for k, v in old.items():
				if k.startswith("_") or k in ("name", "parent", "parenttype", "parentfield", "idx", "owner", "creation", "modified", "modified_by", "docstatus"):
					continue
				if hasattr(charge, k) and getattr(charge, k) is None and v is not None:
					val = _sanitize_select(meta, k, v) if meta.get_field(k) and meta.get_field(k).fieldtype == "Select" else v
					if val is not None:
						charge.set(k, val)

			charge.flags.ignore_links = True
			charge.insert(ignore_permissions=True)
