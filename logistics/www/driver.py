# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Driver journey page.

Route: /driver
Redirect a logged-in driver here after login, or open it directly.
"""

import json
import os
from urllib.parse import quote

import frappe
from frappe import _
from frappe.utils import add_to_date, cint, flt, format_time, formatdate, get_datetime, getdate, now_datetime, today

no_cache = 1
sitemap = 0

PREVIEW_ROLES = ("System Manager", "Administrator", "Transport Manager")


def get_context(context):
	if frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = "/login?redirect-to=/driver"
		raise frappe.Redirect

	driver_name, preview = _resolve_driver()
	payload = _build_payload(driver_name, preview)
	context.driver_payload_json = json.dumps(payload, default=str).replace("<", "\\u003c")
	context.driver_nav_script = _nav_script()
	context.title = "Driver"
	context.no_cache = 1
	return context


def _resolve_driver():
	requested = (frappe.form_dict.get("driver") or "").strip()
	session_driver = frappe.db.get_value("Driver", {"user": frappe.session.user}, "name")
	if requested and requested != session_driver:
		if not _can_preview():
			frappe.throw(_("You can only open your own driver page."), frappe.PermissionError)
		if not frappe.db.exists("Driver", requested):
			frappe.throw(_("Driver {0} was not found.").format(requested), frappe.DoesNotExistError)
		return requested, True
	return session_driver, False


def _nav_script():
	path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "public", "js", "driver_nav.js")
	with open(path, encoding="utf-8") as handle:
		return handle.read()


def _google_maps_key():
	from frappe.utils.password import get_decrypted_password

	for doctype in ("Logistics Settings", "Transport Settings"):
		try:
			key = get_decrypted_password(doctype, doctype, "routing_google_api_key", raise_exception=False)
		except Exception:
			key = None
		if key and len(key) > 10:
			return key
	return ""


def _can_preview():
	roles = set(frappe.get_roles())
	return bool(roles.intersection(PREVIEW_ROLES))


def _build_payload(driver_name, preview):
	user = frappe.get_cached_doc("User", frappe.session.user) if frappe.session.user != "Guest" else None
	payload = {
		"linked": bool(driver_name),
		"preview": preview,
		"driver": driver_name,
		"full_name": (user.full_name if user else "") or frappe.session.user,
		"phone": "",
		"image": (user.user_image if user else "") or "",
		"company_line": "",
		"vehicle_line": "",
		"badge": "Available",
		"on_run": False,
		"license": {"label": "License", "detail": "Not on file", "ok": False},
		"medical": {"label": "Medical", "detail": "Not on file", "ok": False},
		"hazmat": {"label": "HazMat", "detail": "None", "ok": False},
		"today_label": formatdate(today(), "MMMM d, yyyy"),
		"run_sheet": "",
		"route_name": "",
		"stops": [],
		"completed": 0,
		"total": 0,
		"progress": 0,
		"polyline": [],
		"driver_position": None,
		"activity": {
			"completed_runs": 0,
			"on_time_percent": None,
			"open_exceptions": 0,
			"gate_pass": None,
		},
		"history": [],
		"dispatcher_phone": "",
		"dispatcher_name": "",
		"google_maps_key": _google_maps_key(),
	}
	if not driver_name:
		return payload

	driver = _driver_row(driver_name)
	if not driver:
		payload["linked"] = False
		return payload

	payload["full_name"] = driver.full_name or payload["full_name"]
	payload["phone"] = driver.cell_number or ""
	if driver.user:
		image = frappe.db.get_value("User", driver.user, "user_image")
		if image:
			payload["image"] = image

	company = ""
	if driver.custom_transport_company:
		company = (
			frappe.db.get_value("Transport Company", driver.custom_transport_company, "company_name")
			or driver.custom_transport_company
		)
	if cint(driver.custom_is_internal):
		payload["company_line"] = "Internal" + (f" · {company}" if company else "")
	else:
		payload["company_line"] = company or "External driver"

	vehicle_name = driver.custom_default_vehicle
	payload["vehicle_line"] = _vehicle_line(vehicle_name)
	payload["license"] = _license_card(driver)
	payload["medical"] = _medical_card(driver)
	payload["hazmat"] = {
		"label": "HazMat",
		"detail": "Valid" if cint(driver.custom_hazmat_endorsement) else "None",
		"ok": bool(cint(driver.custom_hazmat_endorsement)),
	}
	if driver.custom_last_known_latitude and driver.custom_last_known_longitude:
		payload["driver_position"] = {
			"lat": flt(driver.custom_last_known_latitude),
			"lng": flt(driver.custom_last_known_longitude),
		}

	runs = _runs_for(driver.name)
	today_runs = [row for row in runs if _same_day(row.run_date, today()) and row.status != "Cancelled"]
	active = [
		row
		for row in today_runs
		if row.status in ("Dispatched", "In-Progress", "Hold", "Draft") or row.docstatus < 2
	]
	current = next((row for row in active if row.status in ("In-Progress", "Dispatched", "Hold")), None)
	if not current and active:
		current = active[0]

	payload["on_run"] = bool(current and current.status in ("Dispatched", "In-Progress", "Hold"))
	if driver.status == "Suspended":
		payload["badge"] = "Suspended"
	elif payload["on_run"]:
		payload["badge"] = "On a run"
	elif driver.status == "Left":
		payload["badge"] = "Left"
	else:
		payload["badge"] = "Available"

	if current:
		if current.vehicle:
			payload["vehicle_line"] = _vehicle_line(current.vehicle) or payload["vehicle_line"]
		payload["run_sheet"] = current.name
		payload["route_name"] = current.route_name or current.name
		payload["stops"] = _stops_for_run(current)
		payload["polyline"] = _route_points(current)
		payload["dispatcher_phone"], payload["dispatcher_name"] = _dispatcher(current)
		if not payload["driver_position"] and current.vehicle:
			lat, lng = frappe.db.get_value(
				"Transport Vehicle", current.vehicle, ["last_telematics_lat", "last_telematics_lon"]
			) or (None, None)
			if lat and lng:
				payload["driver_position"] = {"lat": flt(lat), "lng": flt(lng)}

	done = sum(1 for stop in payload["stops"] if stop["done"])
	total = len(payload["stops"])
	payload["completed"] = done
	payload["total"] = total
	payload["progress"] = int(round((done / total) * 100)) if total else 0
	payload["activity"] = _activity(driver, runs)
	payload["history"] = _history(runs)
	return payload


def _driver_row(driver_name):
	core = ["name", "full_name", "status", "cell_number", "user", "expiry_date"]
	custom = [
		"custom_is_internal",
		"custom_transport_company",
		"custom_default_vehicle",
		"custom_hazmat_endorsement",
		"custom_medical_clearance_expiry",
		"custom_last_known_latitude",
		"custom_last_known_longitude",
	]
	meta = frappe.get_meta("Driver")
	fields = core + [field for field in custom if meta.has_field(field)]
	row = frappe.db.get_value("Driver", driver_name, fields, as_dict=True)
	if not row:
		return None
	for field in custom:
		row.setdefault(field, None)
	return row


def _vehicle_line(vehicle_name):
	if not vehicle_name or not frappe.db.exists("Transport Vehicle", vehicle_name):
		return ""
	row = frappe.db.get_value(
		"Transport Vehicle",
		vehicle_name,
		["license_plate_number", "vehicle_name", "vehicle_type"],
		as_dict=True,
	)
	if not row:
		return vehicle_name
	plate = row.license_plate_number or row.vehicle_name or vehicle_name
	kind = row.vehicle_type or ""
	return f"{plate} · {kind}" if kind else plate


def _license_card(driver):
	classes = frappe.get_all(
		"Driving License Category",
		filters={"parent": driver.name, "parenttype": "Driver"},
		pluck="class",
		ignore_permissions=True,
	)
	classes = [c for c in classes if c]
	label = "License " + ", ".join(classes) if classes else "License"
	if driver.expiry_date:
		detail = formatdate(driver.expiry_date, "MMM d, yyyy")
		ok = getdate(driver.expiry_date) >= getdate(today())
	else:
		detail = "No expiry"
		ok = bool(classes)
	return {"label": label, "detail": detail, "ok": ok}


def _medical_card(driver):
	expiry = driver.custom_medical_clearance_expiry
	if not expiry:
		return {"label": "Medical", "detail": "Not on file", "ok": False}
	ok = getdate(expiry) >= getdate(today())
	return {"label": "Medical", "detail": "Due " + formatdate(expiry, "MMM d, yyyy"), "ok": ok}


def _runs_for(driver_name):
	return frappe.get_all(
		"Run Sheet",
		filters={"driver": driver_name, "docstatus": ["<", 2]},
		fields=["name", "run_date", "status", "route_name", "vehicle", "docstatus", "dispatcher", "selected_route_polyline"],
		order_by="run_date desc",
		limit_page_length=60,
		ignore_permissions=True,
	)


def _stops_for_run(run):
	fields = [
			"name",
			"status",
			"transport_job",
			"facility_from",
			"facility_to",
			"pick_address",
			"drop_address",
			"pick_address_format",
			"drop_address_html",
			"pick_window_start",
			"pick_window_end",
			"drop_window_start",
			"drop_window_end",
			"pick_datetime",
			"drop_datetime",
			"pick_signature",
			"drop_signature",
			"pick_signed_by",
			"drop_signed_by",
			"pick_latitude",
			"pick_longitude",
			"drop_latitude",
			"drop_longitude",
			"contains_dangerous_goods",
			"refrigeration",
			"remaining_km",
			"remaining_min",
			"distance_km",
			"duration_min",
			"eta_at_drop",
			"delay_reasons",
			"pick_notes",
			"drop_notes",
		]
	order_by = "`order` asc, creation asc" if frappe.get_meta("Transport Leg").has_field("order") else "creation asc"
	legs = frappe.get_all(
		"Transport Leg",
		filters={"run_sheet": run.name, "docstatus": ["<", 2]},
		fields=fields,
		order_by=order_by,
		ignore_permissions=True,
	)
	jobs = {leg.transport_job for leg in legs if leg.transport_job}
	packages = _package_summaries(jobs)
	stops = []
	for index, leg in enumerate(legs, start=1):
		cargo = packages.get(leg.transport_job) or ""
		flags = []
		if cint(leg.contains_dangerous_goods):
			flags.append("Hazardous")
		if cint(leg.refrigeration):
			flags.append("Keep cold")
		note = " · ".join([part for part in [cargo, *flags] if part])
		stops.append(
			_stop(
				leg,
				"pickup",
				index,
				leg.facility_from,
				leg.pick_address,
				leg.pick_address_format,
				leg.pick_latitude,
				leg.pick_longitude,
				leg.pick_window_start,
				leg.pick_window_end,
				bool(leg.pick_datetime or leg.pick_signature or leg.status == "Completed"),
				bool(leg.pick_signature),
				leg.pick_signed_by,
				note,
				leg.pick_notes,
			)
		)
		stops.append(
			_stop(
				leg,
				"delivery",
				index,
				leg.facility_to,
				leg.drop_address,
				leg.drop_address_html,
				leg.drop_latitude,
				leg.drop_longitude,
				leg.drop_window_start,
				leg.drop_window_end,
				bool(leg.drop_datetime or leg.drop_signature or leg.status == "Completed"),
				bool(leg.drop_signature),
				leg.drop_signed_by,
				note,
				leg.drop_notes,
				eta_min=leg.remaining_min or leg.duration_min,
				eta_km=leg.remaining_km or leg.distance_km,
			)
		)
	_mark_next(stops)
	for number, stop in enumerate(stops, start=1):
		stop["number"] = number
	return stops


def _stop(leg, kind, leg_index, facility, address, address_html, lat, lng, window_start, window_end, done, signed, signed_by, cargo, notes, eta_min=None, eta_km=None):
	if not lat or not lng:
		lat, lng = _address_coords(address)
	place = facility or _city(address) or ("Pickup" if kind == "pickup" else "Delivery")
	return {
		"id": f"{leg.name}:{kind}",
		"leg": leg.name,
		"leg_index": leg_index,
		"kind": kind,
		"title": ("Pickup completed" if done else "Pickup") if kind == "pickup" else ("Delivery completed" if done else "Delivery"),
		"headline": f"{'Pickup' if kind == 'pickup' else 'Delivery'} · {place}",
		"place": place,
		"facility": facility or "",
		"address": _plain_address(address_html) or _plain_address_doc(address),
		"window": _window(window_start, window_end),
		"done": done,
		"signed": signed,
		"signed_by": signed_by or "",
		"signature_pending": not done and not signed,
		"cargo": cargo,
		"notes": _plain_address(notes),
		"lat": flt(lat) if lat else None,
		"lng": flt(lng) if lng else None,
		"eta_min": int(round(flt(eta_min))) if eta_min else None,
		"eta_km": round(flt(eta_km), 1) if eta_km else None,
		"state": "done" if done else "upcoming",
		"pod_url": "/printview?doctype=Transport%20Leg&name={}&format=Proof%20of%20Delivery%20HTML&no_letterhead=1&trigger_print=0".format(
			quote(leg.name)
		),
	}


def _mark_next(stops):
	for stop in stops:
		if not stop["done"]:
			stop["state"] = "next"
			label = "Next pickup" if stop["kind"] == "pickup" else "Next delivery"
			stop["title"] = label
			break


def _package_summaries(job_names):
	if not job_names:
		return {}
	rows = frappe.get_all(
		"Transport Job Package",
		filters={"parent": ["in", list(job_names)], "parenttype": "Transport Job"},
		fields=["parent", "no_of_packs", "uom", "goods_description"],
		ignore_permissions=True,
	)
	grouped = {}
	for row in rows:
		bucket = grouped.setdefault(row.parent, {"qty": 0, "uom": "", "goods": []})
		bucket["qty"] += flt(row.no_of_packs)
		if row.uom and not bucket["uom"]:
			bucket["uom"] = row.uom
		if row.goods_description and row.goods_description not in bucket["goods"]:
			bucket["goods"].append(row.goods_description)
	summaries = {}
	for job, bucket in grouped.items():
		parts = []
		if bucket["qty"]:
			unit = (bucket["uom"] or "packs").lower()
			qty = int(bucket["qty"]) if bucket["qty"] == int(bucket["qty"]) else bucket["qty"]
			parts.append(f"{qty} {unit}")
		if bucket["goods"]:
			parts.append(bucket["goods"][0])
		summaries[job] = " · ".join(parts)
	return summaries


def _address_coords(address_name):
	if not address_name or not frappe.db.exists("Address", address_name):
		return None, None
	if not frappe.get_meta("Address").has_field("latitude"):
		return None, None
	lat, lng = frappe.db.get_value("Address", address_name, ["latitude", "longitude"])
	return lat, lng


def _city(address_name):
	if not address_name:
		return ""
	return frappe.db.get_value("Address", address_name, "city") or ""


def _plain_address_doc(address_name):
	if not address_name or not frappe.db.exists("Address", address_name):
		return ""
	row = frappe.db.get_value(
		"Address",
		address_name,
		["address_line1", "address_line2", "city", "state"],
		as_dict=True,
	)
	if not row:
		return ""
	return ", ".join([part for part in [row.address_line1, row.address_line2, row.city, row.state] if part])


def _plain_address(value):
	if not value:
		return ""
	text = frappe.utils.strip_html(str(value))
	return " ".join(text.split())


def _window(start, end):
	start_label = _clock(start)
	end_label = _clock(end)
	if start_label and end_label:
		return f"{start_label} – {end_label}"
	return start_label or end_label or ""


def _clock(value):
	if not value:
		return ""
	try:
		return format_time(value, "h:mm a")
	except Exception:
		return str(value)


def _route_points(run):
	points = _decode_polyline(run.selected_route_polyline)
	if points:
		return points
	legs = frappe.get_all(
		"Transport Leg",
		filters={"run_sheet": run.name, "docstatus": ["<", 2]},
		pluck="selected_route_polyline",
		ignore_permissions=True,
	)
	merged = []
	for encoded in legs:
		merged.extend(_decode_polyline(encoded))
	return merged


def _decode_polyline(encoded):
	if not encoded:
		return []
	text = str(encoded).strip()
	if text.startswith("["):
		try:
			raw = json.loads(text)
		except Exception:
			raw = None
		if isinstance(raw, list):
			points = []
			for item in raw:
				if isinstance(item, (list, tuple)) and len(item) >= 2:
					points.append([flt(item[0]), flt(item[1])])
				elif isinstance(item, dict) and "lat" in item and "lng" in item:
					points.append([flt(item["lat"]), flt(item["lng"])])
			return points
	return _decode_google_polyline(text)


def _decode_google_polyline(encoded):
	points = []
	index = 0
	lat = 0
	lng = 0
	length = len(encoded)
	try:
		while index < length:
			lat, index = _polyline_chunk(encoded, index, lat)
			lng, index = _polyline_chunk(encoded, index, lng)
			points.append([lat / 1e5, lng / 1e5])
	except Exception:
		return []
	return points


def _polyline_chunk(encoded, index, previous):
	result = 0
	shift = 0
	while True:
		byte = ord(encoded[index]) - 63
		index += 1
		result |= (byte & 0x1F) << shift
		shift += 5
		if byte < 0x20:
			break
	delta = ~(result >> 1) if result & 1 else (result >> 1)
	return previous + delta, index


def _dispatcher(run):
	if not run.dispatcher:
		return "", ""
	phone, name = frappe.db.get_value("Employee", run.dispatcher, ["cell_number", "employee_name"]) or ("", "")
	return phone or "", name or run.dispatcher


def _activity(driver, runs):
	month_start = getdate(today()).replace(day=1)
	completed = 0
	for run in runs:
		if run.status == "Completed" and run.run_date and getdate(run.run_date) >= month_start:
			completed += 1

	leg_rows = frappe.get_all(
		"Transport Leg",
		filters={"run_date": [">=", month_start], "docstatus": ["<", 2]},
		fields=["name", "run_sheet", "status", "drop_datetime", "drop_window_end", "delay_reasons"],
		limit_page_length=500,
		ignore_permissions=True,
	)
	run_ids = {run.name for run in runs}
	mine = [row for row in leg_rows if row.run_sheet in run_ids]
	on_time_base = [row for row in mine if row.status == "Completed" or row.drop_datetime]
	on_time = 0
	for row in on_time_base:
		if not row.drop_window_end or not row.drop_datetime:
			on_time += 1
			continue
		try:
			if get_datetime(row.drop_datetime).time() <= get_datetime(row.drop_window_end).time():
				on_time += 1
		except Exception:
			on_time += 1
	percent = int(round((on_time / len(on_time_base)) * 100)) if on_time_base else None
	open_exceptions = sum(1 for row in mine if row.delay_reasons and row.status != "Completed")

	gate_pass = None
	if driver.full_name and frappe.db.exists("DocType", "Gate Pass"):
		passes = frappe.get_all(
			"Gate Pass",
			filters={"driver_name": driver.full_name, "gate_pass_date": today()},
			fields=["name", "gate_pass_time", "status"],
			order_by="creation desc",
			limit_page_length=1,
			ignore_permissions=True,
		)
		if passes:
			row = passes[0]
			when = _clock(row.gate_pass_time)
			gate_pass = {
				"name": row.name,
				"detail": f"Issued today{', ' + when if when else ''}",
				"status": row.status or "",
			}

	return {
		"completed_runs": completed,
		"on_time_percent": percent,
		"open_exceptions": open_exceptions,
		"gate_pass": gate_pass,
	}


def _history(runs):
	items = []
	for run in runs:
		if _same_day(run.run_date, today()) and run.status not in ("Completed", "Cancelled"):
			continue
		leg_count = frappe.db.count("Transport Leg", {"run_sheet": run.name, "docstatus": ["<", 2]})
		items.append(
			{
				"name": run.name,
				"route_name": run.route_name or run.name,
				"date": formatdate(run.run_date, "MMM d, yyyy") if run.run_date else "",
				"status": run.status or "Draft",
				"stops": leg_count * 2,
				"vehicle": _vehicle_line(run.vehicle),
			}
		)
		if len(items) >= 20:
			break
	return items


def _same_day(value, day):
	if not value:
		return False
	try:
		return getdate(value) == getdate(day)
	except Exception:
		return False


@frappe.whitelist()
def report_problem(leg, reason, note=""):
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in."), frappe.PermissionError)
	driver_name, _preview = _resolve_driver()
	if not driver_name:
		frappe.throw(_("Your user is not linked to a Driver."), frappe.PermissionError)
	if not leg or not frappe.db.exists("Transport Leg", leg):
		frappe.throw(_("Stop was not found."))
	run_sheet = frappe.db.get_value("Transport Leg", leg, "run_sheet")
	owner = frappe.db.get_value("Run Sheet", run_sheet, "driver") if run_sheet else None
	if owner != driver_name and not _can_preview():
		frappe.throw(_("This stop is not on your run."), frappe.PermissionError)

	reason = (reason or "Problem reported").strip()[:140]
	note = frappe.utils.strip_html(note or "").strip()[:1000]
	stamp = formatdate(now_datetime(), "MMM d, yyyy h:mm a")
	existing = frappe.db.get_value("Transport Leg", leg, "exception_handling_notes") or ""
	line = f"<p><b>{frappe.utils.escape_html(stamp)}</b> — {frappe.utils.escape_html(reason)}"
	if note:
		line += f": {frappe.utils.escape_html(note)}"
	line += "</p>"
	frappe.db.set_value(
		"Transport Leg",
		leg,
		{"exception_handling_notes": (existing or "") + line, "delay_reasons": reason},
		update_modified=True,
	)
	return {"ok": True}


@frappe.whitelist()
def update_live_etas(updates=None, latitude=None, longitude=None):
	"""Save traffic ETAs for this driver's drops, and the latest GPS fix.

	The driver page counts the dock ETA down locally. This keeps the leg's
	remaining time and drop ETA in step with the truck while the run is moving.
	"""
	if frappe.session.user == "Guest":
		frappe.throw(_("Please log in."), frappe.PermissionError)
	driver_name, preview = _resolve_driver()
	if preview or not driver_name:
		return {"ok": False, "saved": 0}

	rows = _eta_rows(updates)
	saved = 0
	now = now_datetime()
	for row in rows:
		leg_name = (row.get("leg") or "").strip()
		if not leg_name or not frappe.db.exists("Transport Leg", leg_name):
			continue
		run_sheet, status = frappe.db.get_value("Transport Leg", leg_name, ["run_sheet", "status"]) or (None, None)
		owner = frappe.db.get_value("Run Sheet", run_sheet, "driver") if run_sheet else None
		if owner != driver_name or status in ("Completed", "Cancelled"):
			continue
		eta_min = flt(row.get("eta_min"))
		eta_km = flt(row.get("eta_km"))
		if eta_min <= 0 or eta_min > 24 * 60 or eta_km < 0 or eta_km > 5000:
			continue
		frappe.db.set_value(
			"Transport Leg",
			leg_name,
			{
				"remaining_min": round(eta_min, 1),
				"remaining_km": round(eta_km, 3),
				"eta_at_drop": add_to_date(now, minutes=eta_min),
			},
			update_modified=False,
		)
		saved += 1

	if latitude not in (None, "") and longitude not in (None, ""):
		_save_driver_fix(driver_name, flt(latitude), flt(longitude))

	if saved or latitude not in (None, ""):
		frappe.db.commit()
	return {"ok": True, "saved": saved}


def _eta_rows(updates):
	if not updates:
		return []
	if isinstance(updates, str):
		try:
			updates = json.loads(updates)
		except Exception:
			return []
	if isinstance(updates, dict):
		updates = [updates]
	if not isinstance(updates, list):
		return []
	return [row for row in updates[:40] if isinstance(row, dict)]


def _save_driver_fix(driver_name, lat, lng):
	if not (-90 <= lat <= 90) or not (-180 <= lng <= 180):
		return
	meta = frappe.get_meta("Driver")
	values = {}
	if meta.has_field("custom_last_known_latitude"):
		values["custom_last_known_latitude"] = lat
	if meta.has_field("custom_last_known_longitude"):
		values["custom_last_known_longitude"] = lng
	if meta.has_field("custom_last_location_time"):
		values["custom_last_location_time"] = now_datetime()
	if values:
		frappe.db.set_value("Driver", driver_name, values, update_modified=False)
