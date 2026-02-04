# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.utils import flt


def execute(filters=None):
	columns = get_columns(filters)
	data = get_data(filters)
	chart = get_chart_data(data, filters)
	summary = get_summary(data, filters)
	return columns, data, None, chart, summary


def get_columns(filters):
	group_by = (filters or {}).get("group_by") or "Vehicle Type"
	cols = []
	if group_by == "Vehicle Type":
		cols.extend([
			{"fieldname": "vehicle_type", "label": _("Vehicle Type"), "fieldtype": "Link", "options": "Vehicle Type", "width": 140},
			{"fieldname": "vehicle_count", "label": _("Vehicle Count"), "fieldtype": "Int", "width": 100},
		])
	else:
		cols.extend([
			{"fieldname": "vehicle", "label": _("Vehicle"), "fieldtype": "Link", "options": "Transport Vehicle", "width": 120},
			{"fieldname": "vehicle_name", "label": _("Vehicle Name"), "fieldtype": "Data", "width": 140},
			{"fieldname": "vehicle_type", "label": _("Vehicle Type"), "fieldtype": "Link", "options": "Vehicle Type", "width": 120},
		])
	cols.extend([
		{"fieldname": "transport_company", "label": _("Transport Company"), "fieldtype": "Link", "options": "Transport Company", "width": 140},
		{"fieldname": "capacity_weight", "label": _("Capacity Weight (kg)"), "fieldtype": "Float", "precision": 2, "width": 130},
		{"fieldname": "capacity_volume", "label": _("Capacity Volume"), "fieldtype": "Float", "precision": 2, "width": 120},
		{"fieldname": "capacity_pallets", "label": _("Capacity Pallets"), "fieldtype": "Int", "width": 100},
		{"fieldname": "utilized_weight", "label": _("Utilized Weight (kg)"), "fieldtype": "Float", "precision": 2, "width": 130},
		{"fieldname": "weight_utilization_pct", "label": _("Weight Utilization %"), "fieldtype": "Percent", "precision": 2, "width": 120},
		{"fieldname": "run_sheets_count", "label": _("Run Sheets"), "fieldtype": "Int", "width": 90},
		{"fieldname": "legs_count", "label": _("Legs"), "fieldtype": "Int", "width": 80},
	])
	return cols


def get_data(filters):
	filters = filters or {}
	from_date = filters.get("from_date")
	to_date = filters.get("to_date")
	group_by = filters.get("group_by") or "Vehicle Type"
	vehicle_type = filters.get("vehicle_type")
	vehicle = filters.get("vehicle")
	transport_company = filters.get("transport_company")

	# WHERE: base conditions are literal (no format/placeholder) to avoid "WHERE  AND" bug
	where_parts = [
		"rs.docstatus = 1",
		"rs.run_date BETWEEN %(from_date)s AND %(to_date)s",
	]
	if vehicle_type:
		where_parts.append("rs.vehicle_type = %(vehicle_type)s")
	if vehicle:
		where_parts.append("rs.vehicle = %(vehicle)s")
	if transport_company:
		where_parts.append("rs.transport_company = %(transport_company)s")
	where_sql = " WHERE " + " AND ".join(where_parts)

	# Utilized weight from Run Sheet -> Run Sheet Leg -> Transport Leg (cargo_weight_kg)
	utilized_sql = (
		"SELECT rs.vehicle, rs.vehicle_type, rs.transport_company,"
		" COUNT(DISTINCT rs.name) AS run_sheets_count,"
		" COUNT(tl.name) AS legs_count,"
		" COALESCE(SUM(COALESCE(tl.cargo_weight_kg, 0)), 0) AS utilized_weight"
		" FROM `tabRun Sheet` rs"
		" INNER JOIN `tabRun Sheet Leg` rsl ON rsl.parent = rs.name"
		" INNER JOIN `tabTransport Leg` tl ON tl.name = rsl.transport_leg"
		+ where_sql
		+ " GROUP BY rs.vehicle, rs.vehicle_type, rs.transport_company"
	)

	utilized_data = frappe.db.sql(utilized_sql, filters, as_dict=True)
	# Key by (vehicle, vehicle_type, transport_company) for per-vehicle lookup
	utilized_by_vehicle = {(row.vehicle or "", row.vehicle_type or "", row.transport_company or ""): row for row in utilized_data}
	# For Vehicle Type: sum utilized by (vehicle_type, transport_company)
	utilized_by_type = {}
	for row in utilized_data:
		key = (row.vehicle_type or "", row.transport_company or "")
		if key not in utilized_by_type:
			utilized_by_type[key] = {"utilized_weight": 0, "run_sheets_count": 0, "legs_count": 0}
		utilized_by_type[key]["utilized_weight"] += flt(row.utilized_weight, 0)
		utilized_by_type[key]["run_sheets_count"] += int(flt(row.run_sheets_count, 0))
		utilized_by_type[key]["legs_count"] += int(flt(row.legs_count, 0))

	# All vehicles (for capacity) matching filters
	vehicle_filters = {}
	if vehicle_type:
		vehicle_filters["vehicle_type"] = vehicle_type
	if vehicle:
		vehicle_filters["name"] = vehicle
	if transport_company:
		vehicle_filters["transport_company"] = transport_company
	vehicles = frappe.get_all(
		"Transport Vehicle",
		filters=vehicle_filters,
		fields=["name", "vehicle_name", "vehicle_type", "transport_company", "capacity_weight", "capacity_weight_uom", "capacity_volume", "capacity_volume_uom", "capacity_pallets"]
	)

	# Standardise capacity to kg for weight (for utilization %)
	try:
		from logistics.transport.capacity.uom_conversion import get_default_uoms, convert_weight, convert_volume
		default_uoms = get_default_uoms()
		weight_uom = default_uoms.get("weight", "KG")
		volume_uom = default_uoms.get("volume", "CBM")
		do_convert = True
	except Exception:
		do_convert = False
		weight_uom = "KG"
		volume_uom = "CBM"

	# Build rows by vehicle or by vehicle type
	aggregates = {}

	for v in vehicles:
		cap_w = flt(v.get("capacity_weight"), 0)
		cap_vol = flt(v.get("capacity_volume"), 0)
		cap_pal = flt(v.get("capacity_pallets"), 0)
		if do_convert and cap_w and v.get("capacity_weight_uom"):
			try:
				cap_w = convert_weight(cap_w, v.get("capacity_weight_uom"), weight_uom)
			except Exception:
				pass
		if do_convert and cap_vol and v.get("capacity_volume_uom"):
			try:
				cap_vol = convert_volume(cap_vol, v.get("capacity_volume_uom"), volume_uom)
			except Exception:
				pass

		if group_by == "Vehicle Type":
			key = (None, v.get("vehicle_type") or "", v.get("transport_company") or "")
		else:
			key = (v.get("name"), v.get("vehicle_type") or "", v.get("transport_company") or "")

		if key not in aggregates:
			if group_by == "Vehicle Type":
				util = utilized_by_type.get((v.get("vehicle_type") or "", v.get("transport_company") or ""))
			else:
				util = utilized_by_vehicle.get((v.get("name") or "", v.get("vehicle_type") or "", v.get("transport_company") or ""))
			aggregates[key] = {
				"vehicle": v.get("name") if group_by == "Vehicle" else None,
				"vehicle_name": v.get("vehicle_name") if group_by == "Vehicle" else None,
				"vehicle_type": v.get("vehicle_type"),
				"transport_company": v.get("transport_company"),
				"capacity_weight": 0,
				"capacity_volume": 0,
				"capacity_pallets": 0,
				"utilized_weight": flt(util.get("utilized_weight"), 0) if util else 0,
				"run_sheets_count": int(flt(util.get("run_sheets_count"), 0)) if util else 0,
				"legs_count": int(flt(util.get("legs_count"), 0)) if util else 0,
				"vehicle_count": 0,
			}
		agg = aggregates[key]
		agg["capacity_weight"] = flt(agg["capacity_weight"]) + cap_w
		agg["capacity_volume"] = flt(agg["capacity_volume"]) + cap_vol
		agg["capacity_pallets"] = int(flt(agg["capacity_pallets"]) + cap_pal)
		agg["vehicle_count"] += 1

	rows = []
	for key, agg in aggregates.items():
		cap_w = flt(agg["capacity_weight"], 0)
		util_w = flt(agg["utilized_weight"], 0)
		weight_pct = (util_w / cap_w * 100) if cap_w else 0
		agg["weight_utilization_pct"] = min(weight_pct, 100)
		rows.append(agg)

	# Sort by weight utilization descending
	rows.sort(key=lambda r: (flt(r.get("weight_utilization_pct"), 0), flt(r.get("utilized_weight"), 0)), reverse=True)
	return rows


def get_chart_data(data, filters):
	if not data:
		return None
	group_by = (filters or {}).get("group_by") or "Vehicle Type"
	labels = []
	for row in data[:15]:
		if group_by == "Vehicle Type":
			labels.append(row.get("vehicle_type") or _("N/A"))
		else:
			labels.append(row.get("vehicle_name") or row.get("vehicle") or _("N/A"))
	return {
		"data": {
			"labels": labels,
			"datasets": [{"name": _("Weight Utilization %"), "values": [row.get("weight_utilization_pct") for row in data[:15]]}],
		},
		"type": "bar",
		"colors": ["#5e64ff"],
	}


def get_summary(data, filters):
	if not data:
		return []
	total_cap = sum(flt(r.get("capacity_weight"), 0) for r in data)
	total_util = sum(flt(r.get("utilized_weight"), 0) for r in data)
	avg_pct = (total_util / total_cap * 100) if total_cap else 0
	return [
		{"label": _("Rows"), "value": len(data), "indicator": "blue"},
		{"label": _("Total Capacity (kg)"), "value": f"{total_cap:,.2f}", "indicator": "blue"},
		{"label": _("Total Utilized (kg)"), "value": f"{total_util:,.2f}", "indicator": "green"},
		{"label": _("Avg Weight Utilization %"), "value": f"{avg_pct:.2f}%", "indicator": "green" if avg_pct > 70 else "red"},
	]
