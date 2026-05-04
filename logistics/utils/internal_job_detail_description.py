# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Build a concise Job Description string from Internal Job Detail row fields (by service type)."""

from __future__ import unicode_literals

import frappe


def _g(row, key, default=""):
	if isinstance(row, dict):
		v = row.get(key)
	else:
		v = getattr(row, key, None)
	if v is None:
		return default
	s = str(v).strip()
	return s if s else default


def _format_location(row, which):
	val = _g(row, "location_from" if which == "from" else "location_to")
	if not val:
		return ""
	lt = _g(row, "location_type")
	if lt == "Transport Zone" and frappe.db.exists("Transport Zone", val):
		zn = frappe.db.get_value("Transport Zone", val, "zone_name")
		return (zn or val).strip()
	return val


def build_internal_job_description(row):
	"""
	Summary line(s) for Internal Job Detail Job Description from service-type parameters.
	``row`` may be a dict (from the form) or a document-like object.
	"""
	st = _g(row, "service_type")
	if not st:
		return ""

	parts = []

	if st == "Air":
		for key in ("air_house_type", "airline", "freight_agent", "load_type", "direction"):
			x = _g(row, key)
			if x:
				parts.append(x)
		op = _g(row, "origin_port")
		dp = _g(row, "destination_port")
		if op or dp:
			parts.append("{} → {}".format(op or "—", dp or "—"))

	elif st == "Sea":
		for key in ("sea_house_type", "shipping_line", "freight_agent_sea", "load_type", "direction"):
			x = _g(row, key)
			if x:
				parts.append(x)
		op = _g(row, "origin_port")
		dp = _g(row, "destination_port")
		if op or dp:
			parts.append("{} → {}".format(op or "—", dp or "—"))
		tm = _g(row, "transport_mode")
		if tm:
			parts.append(tm)

	elif st == "Transport":
		for key in (
			"transport_template",
			"vehicle_type",
			"container_type",
			"container_no",
			"pick_mode",
			"drop_mode",
		):
			x = _g(row, key)
			if x:
				parts.append(x)
		ltp = _g(row, "location_type")
		if ltp:
			parts.append(ltp)
		lf = _format_location(row, "from")
		lt = _format_location(row, "to")
		if lf or lt:
			parts.append("{} → {}".format(lf or "—", lt or "—"))

	elif st == "Customs":
		for key in ("customs_authority", "declaration_type", "customs_broker", "customs_charge_category"):
			x = _g(row, key)
			if x:
				parts.append(x)

	elif st == "Warehousing":
		jt = _g(row, "job_type")
		jn = _g(row, "job_no")
		if jt:
			parts.append(jt)
		if jn:
			parts.append(jn)

	elif st == "Special Project":
		site = _g(row, "sp_site")
		if site:
			lbl = frappe.db.get_value("Address", site, "address_title")
			parts.append((lbl or site)[:160])
		for key in ("sp_equipment_type", "sp_handling"):
			x = _g(row, key)
			if x:
				parts.append(x)
		mp = row.get("sp_manpower") if isinstance(row, dict) else getattr(row, "sp_manpower", None)
		sk = row.get("sp_skilled") if isinstance(row, dict) else getattr(row, "sp_skilled", None)
		try:
			if mp is not None and float(mp) != 0:
				parts.append("Manpower: {}".format(mp))
		except (TypeError, ValueError):
			pass
		try:
			if sk is not None and float(sk) != 0:
				parts.append("Skilled labor: {}".format(sk))
		except (TypeError, ValueError):
			pass
		sn = _g(row, "sp_resource_notes")
		if sn:
			parts.append(sn[:300])

	out = " · ".join(parts) if parts else ""
	if out:
		return "{} · {}".format(st, out)
	return st
