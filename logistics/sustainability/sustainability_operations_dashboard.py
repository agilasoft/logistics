# Copyright (c) 2026, Agilasoft and contributors
"""Sustainability Home: carbon footprint lanes colored by emission."""

from __future__ import unicode_literals

from collections import OrderedDict


def flt(value, precision=None):
	try:
		number = float(value or 0)
	except (TypeError, ValueError):
		number = 0.0
	if precision is None:
		return number
	return round(number, precision)


def cint(value):
	try:
		return int(float(value or 0))
	except (TypeError, ValueError):
		return 0

# Same cutoffs as CarbonFootprint.get_carbon_efficiency_rating (kg CO2e).
EMISSION_BANDS = (
	{"key": "excellent", "label": "Excellent", "max": 100, "color": "#15803d", "tint": "#dcfce7"},
	{"key": "good", "label": "Good", "max": 500, "color": "#4d7c0f", "tint": "#ecfccb"},
	{"key": "fair", "label": "Fair", "max": 1000, "color": "#a16207", "tint": "#fef9c3"},
	{"key": "poor", "label": "Poor", "max": 2000, "color": "#c2410c", "tint": "#ffedd5"},
	{"key": "very_poor", "label": "Very Poor", "max": None, "color": "#b91c1c", "tint": "#fee2e2"},
)
HIGH_BANDS = {"poor", "very_poor"}

MODULES = (
	"Transport",
	"Warehousing",
	"Air Freight",
	"Sea Freight",
	"Customs",
	"Job Management",
	"Pricing Center",
)
SCOPES = ("Scope 1", "Scope 2", "Scope 3", "Combined")
PERIODS = (0, 30, 90, 365)
DEFAULT_PERIOD = 90
DEFAULT_LIMIT = 12
MAX_LIMIT = 40
MAX_RECORDS = 500
MAX_CHIPS = 4

ROUTE_FIELDS = {
	"Air Shipment": ("origin_port", "destination_port"),
	"Sea Shipment": ("origin_port", "destination_port"),
}


def emission_band(kg):
	"""Color band for a kilogram CO2e total. Higher emission, warmer color."""
	value = flt(kg)
	if value < 0:
		value = 0
	for band in EMISSION_BANDS:
		ceiling = band["max"]
		if ceiling is None or value <= ceiling:
			return {
				"key": band["key"],
				"label": band["label"],
				"color": band["color"],
				"tint": band["tint"],
			}
	last = EMISSION_BANDS[-1]
	return {"key": last["key"], "label": last["label"], "color": last["color"], "tint": last["tint"]}


def lane_identity(module, origin, destination, facility):
	"""Route lane when both ends differ, otherwise a facility or module lane."""
	module = (module or "Other").strip() or "Other"
	origin = (origin or "").strip()
	destination = (destination or "").strip()
	facility = (facility or "").strip()
	if origin and destination and origin != destination:
		return {
			"module": module,
			"origin": origin,
			"destination": destination,
			"kind": "route",
			"label": "{0} → {1}".format(origin, destination),
		}
	point = ""
	if origin and origin == destination:
		point = origin
	elif origin and not destination:
		point = origin
	elif destination and not origin:
		point = destination
	elif facility:
		point = facility
	if point:
		return {
			"module": module,
			"origin": point,
			"destination": "",
			"kind": "facility",
			"label": point,
		}
	return {
		"module": module,
		"origin": "",
		"destination": "",
		"kind": "module",
		"label": module,
	}


def _date_text(value):
	if not value:
		return ""
	return str(value)[:10]


def _chip(record):
	emissions = flt(record.get("total_emissions"))
	band = emission_band(emissions)
	return {
		"name": record.get("name") or "",
		"date": _date_text(record.get("date")),
		"emissions": flt(emissions, 2),
		"scope": record.get("scope") or "",
		"reference_doctype": record.get("reference_doctype") or "",
		"reference_name": record.get("reference_name") or "",
		"band": band["key"],
		"color": band["color"],
		"tint": band["tint"],
	}


def build_lanes(records, limit=DEFAULT_LIMIT):
	"""Group footprint rows into lanes and color each lane by its total emissions."""
	buckets = OrderedDict()
	for record in records or []:
		ident = lane_identity(
			record.get("module"),
			record.get("origin"),
			record.get("destination"),
			record.get("facility"),
		)
		key = (ident["module"], ident["kind"], ident["origin"], ident["destination"])
		bucket = buckets.get(key)
		if bucket is None:
			bucket = {
				"module": ident["module"],
				"origin": ident["origin"],
				"destination": ident["destination"],
				"kind": ident["kind"],
				"label": ident["label"],
				"emissions": 0.0,
				"net": 0.0,
				"offset": 0.0,
				"count": 0,
				"records": [],
			}
			buckets[key] = bucket
		bucket["emissions"] += flt(record.get("total_emissions"))
		bucket["net"] += flt(record.get("net_emissions"))
		bucket["offset"] += flt(record.get("carbon_offset"))
		bucket["count"] += 1
		if len(bucket["records"]) < MAX_CHIPS:
			bucket["records"].append(_chip(record))

	lanes = list(buckets.values())
	lanes.sort(key=lambda row: (-flt(row["emissions"]), (row.get("label") or "").lower()))
	lim = cint(limit) or DEFAULT_LIMIT
	if lim < 1:
		lim = DEFAULT_LIMIT
	lim = min(lim, MAX_LIMIT)
	shown = lanes[:lim]
	hottest = flt(shown[0]["emissions"]) if shown else 0
	for lane in shown:
		band = emission_band(lane["emissions"])
		lane["emissions"] = flt(lane["emissions"], 2)
		lane["net"] = flt(lane["net"], 2)
		lane["offset"] = flt(lane["offset"], 2)
		lane["band"] = band["key"]
		lane["band_label"] = band["label"]
		lane["color"] = band["color"]
		lane["tint"] = band["tint"]
		lane["bar_pct"] = round((flt(lane["emissions"]) / hottest) * 100, 1) if hottest else 0
	return shown, len(lanes)


def summarize(records, lanes, totals=None):
	"""Header figures. ``totals`` may cover more rows than the lane sample."""
	totals = totals or {}
	if totals:
		emissions = flt(totals.get("emissions"))
		net = flt(totals.get("net"))
		offset = flt(totals.get("offset"))
		record_count = cint(totals.get("records"))
	else:
		emissions = sum(flt(row.get("total_emissions")) for row in (records or []))
		net = sum(flt(row.get("net_emissions")) for row in (records or []))
		offset = sum(flt(row.get("carbon_offset")) for row in (records or []))
		record_count = len(records or [])
	high = [lane for lane in (lanes or []) if lane.get("band") in HIGH_BANDS]
	high_kg = sum(flt(lane.get("emissions")) for lane in high)
	sample_kg = sum(flt(lane.get("emissions")) for lane in (lanes or []))
	return {
		"records": record_count,
		"lanes": len(lanes or []),
		"emissions": flt(emissions, 2),
		"net": flt(net, 2),
		"offset": flt(offset, 2),
		"high_lanes": len(high),
		"high_share": round((high_kg / sample_kg) * 100, 1) if sample_kg else 0,
	}


def legend():
	return [
		{"key": band["key"], "label": band["label"], "color": band["color"], "tint": band["tint"], "max": band["max"]}
		for band in EMISSION_BANDS
	]


def parse_period(value):
	if value in (None, ""):
		return DEFAULT_PERIOD
	days = cint(value)
	if days in PERIODS:
		return days
	return DEFAULT_PERIOD


def parse_choice(value, allowed):
	text = (value or "").strip()
	if not text or text.lower() == "all":
		return ""
	if text in allowed:
		return text
	return ""


def _frappe():
	import frappe

	return frappe


def _filters(company, module, scope, since):
	filters = {}
	if company:
		filters["company"] = company
	if module:
		filters["module"] = module
	if scope:
		filters["scope"] = scope
	if since:
		filters["date"] = [">=", since]
	return filters


def _sum_totals(filters):
	rows = _frappe().get_all(
		"Carbon Footprint",
		filters=filters,
		fields=[
			"count(name) as records",
			"sum(total_emissions) as emissions",
			"sum(net_emissions) as net",
			"sum(carbon_offset) as offset",
		],
	)
	row = rows[0] if rows else {}
	return {
		"records": cint(row.get("records")),
		"emissions": flt(row.get("emissions")),
		"net": flt(row.get("net")),
		"offset": flt(row.get("offset")),
	}


def _route_map(records):
	by_doctype = {}
	for record in records:
		doctype = record.get("reference_doctype") or ""
		name = record.get("reference_name") or ""
		if doctype and name:
			by_doctype.setdefault(doctype, set()).add(name)
	routes = {}
	for doctype, names in by_doctype.items():
		routes.update(_routes_for_doctype(doctype, sorted(names)))
	return routes


def _routes_for_doctype(doctype, names):
	frappe = _frappe()
	if not names or not frappe.db.exists("DocType", doctype):
		return {}
	if doctype == "Transport Job":
		return _transport_routes(names)
	fields = ROUTE_FIELDS.get(doctype)
	if not fields:
		return {}
	meta = frappe.get_meta(doctype)
	if not meta.has_field(fields[0]) or not meta.has_field(fields[1]):
		return {}
	rows = frappe.get_all(
		doctype,
		filters={"name": ["in", names]},
		fields=["name", fields[0], fields[1]],
		limit=len(names),
	)
	out = {}
	for row in rows:
		out[(doctype, row.name)] = (row.get(fields[0]) or "", row.get(fields[1]) or "")
	return out


def _transport_routes(names):
	frappe = _frappe()
	if not frappe.db.exists("DocType", "Transport Job Legs"):
		return {}
	rows = frappe.get_all(
		"Transport Job Legs",
		filters={"parent": ["in", names], "parenttype": "Transport Job"},
		fields=["parent", "idx", "facility_from", "facility_to"],
		order_by="parent asc, idx asc",
		limit=len(names) * 20,
	)
	grouped = {}
	for row in rows:
		grouped.setdefault(row.parent, []).append(row)
	out = {}
	for parent, legs in grouped.items():
		if not legs:
			continue
		origin = legs[0].get("facility_from") or ""
		destination = legs[-1].get("facility_to") or ""
		out[("Transport Job", parent)] = (origin, destination)
	return out


def _with_routes(records, routes):
	prepared = []
	for record in records:
		row = dict(record)
		key = (row.get("reference_doctype") or "", row.get("reference_name") or "")
		origin, destination = routes.get(key, ("", ""))
		row["origin"] = origin or ""
		row["destination"] = destination or ""
		prepared.append(row)
	return prepared


def get_sustainability_dashboard(period=None, module=None, scope=None, limit=None):
	frappe = _frappe()
	from frappe import _
	from frappe.utils import add_days, getdate

	from logistics.operations_dashboard.heat_map_core import session_company_context

	frappe.has_permission("Carbon Footprint", "read", throw=True)
	ctx = session_company_context()
	company = (ctx.get("company") or "").strip()
	days = parse_period(period)
	module_filter = parse_choice(module, MODULES)
	scope_filter = parse_choice(scope, SCOPES)
	lim = cint(limit) if limit not in (None, "") else DEFAULT_LIMIT
	since = add_days(getdate(), -days) if days else None
	filters = _filters(company, module_filter, scope_filter, since)
	totals = _sum_totals(filters)
	records = _frappe().get_all(
		"Carbon Footprint",
		filters=filters,
		fields=[
			"name",
			"date",
			"module",
			"facility",
			"scope",
			"total_emissions",
			"net_emissions",
			"carbon_offset",
			"reference_doctype",
			"reference_name",
		],
		order_by="date desc, modified desc",
		limit=MAX_RECORDS,
	)
	prepared = _with_routes(records, _route_map(records))
	lanes, lane_count = build_lanes(prepared, limit=lim)
	kpis = summarize(prepared, lanes, totals=totals)
	kpis["lanes"] = lane_count
	kpis["shown"] = len(lanes)
	return {
		"company": ctx.get("company") or "",
		"company_name": ctx.get("company_name") or "",
		"company_logo_url": ctx.get("company_logo_url") or "",
		"kpis": kpis,
		"lanes": lanes,
		"legend": legend(),
		"period": days,
		"module": module_filter or "all",
		"scope": scope_filter or "all",
		"truncated": 1 if cint(totals.get("records")) > len(records) else 0,
		"unit": _("kg CO2e"),
	}


try:
	import frappe as _frappe_mod
except ImportError:
	_frappe_mod = None
else:
	get_sustainability_dashboard = _frappe_mod.whitelist()(get_sustainability_dashboard)
