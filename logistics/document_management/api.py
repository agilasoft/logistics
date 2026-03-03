# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""API for document management: template resolution, population, and alerts."""

from __future__ import unicode_literals

import frappe
from frappe.utils import getdate, add_days, date_diff, today


# Mapping of doctype to (product_type, applies_to)
DOCTYPE_CONTEXT = {
	"Air Booking": ("Air Freight", "Booking"),
	"Sea Booking": ("Sea Freight", "Booking"),
	"Transport Order": ("Transport", "Booking"),
	"Declaration Order": ("Customs", "Booking"),
	"Inbound Order": ("Warehousing", "Booking"),
	"Release Order": ("Warehousing", "Booking"),
	"Transfer Order": ("Warehousing", "Booking"),
	"Air Shipment": ("Air Freight", "Shipment/Job"),
	"Sea Shipment": ("Sea Freight", "Shipment/Job"),
	"Sea Consolidation": ("Sea Freight", "Shipment/Job"),
	"Transport Job": ("Transport", "Shipment/Job"),
	"Warehouse Job": ("Warehousing", "Shipment/Job"),
	"General Job": ("General", "Shipment/Job"),
	"Declaration": ("Customs", "Shipment/Job"),
	"Special Project": ("Special Projects", "Shipment/Job"),
}

# Doctypes that have milestone child table (field "milestones")
MILESTONE_DOCTYPES = ("Air Shipment", "Sea Booking", "Sea Shipment", "Sea Consolidation", "Transport Job", "Declaration", "Declaration Order")

# Child table doctype for each parent
MILESTONE_CHILD_DOCTYPE = {
	"Air Shipment": "Air Shipment Milestone",
	"Sea Booking": "Sea Booking Milestone",
	"Sea Shipment": "Sea Shipment Milestone",
	"Sea Consolidation": "Sea Consolidation Milestone",
	"Transport Job": "Transport Job Milestone",
	"Declaration": "Declaration Milestone",
	"Declaration Order": "Declaration Order Milestone",
}


@frappe.whitelist()
def get_milestone_html(doctype, docname):
	"""Generate graphical milestone HTML for Milestones tab. Uses child table milestones."""
	if not doctype or not docname or docname == "new":
		return '<div class="alert alert-info">Save the document to view milestones.</div>'
	if doctype not in MILESTONE_DOCTYPES:
		return '<div class="alert alert-warning">Milestones not supported for this doctype.</div>'
	try:
		doc = frappe.get_doc(doctype, docname)
	except frappe.DoesNotExistError:
		return '<div class="alert alert-warning">Document not found.</div>'

	milestone_rows = list(doc.get("milestones") or [])
	child_doctype = MILESTONE_CHILD_DOCTYPE.get(doctype, "")

	# Build milestone dicts for build_milestone_html
	milestones = []
	for row in milestone_rows:
		milestones.append({
			"name": row.name,
			"milestone": row.milestone,
			"status": row.status or "Planned",
			"planned_start": row.planned_start,
			"planned_end": row.planned_end,
			"actual_start": row.actual_start,
			"actual_end": row.actual_end,
		})

	# Resolve origin/destination per doctype (detail items section removed)
	origin_name = (
		getattr(doc, "origin_port", None) or getattr(doc, "port_of_loading", None)
		or getattr(doc, "origin", None) or getattr(doc, "origin_terminal", None) or ""
	)
	destination_name = (
		getattr(doc, "destination_port", None) or getattr(doc, "port_of_discharge", None)
		or getattr(doc, "destination", None) or getattr(doc, "destination_terminal", None) or ""
	)
	detail_items = []  # Status, Booking Date, Scheduled Date section removed

	def format_dt(v):
		return frappe.utils.format_datetime(v, "dd-MM-yyyy HH:mm") if v else None

	from logistics.document_management.milestone_html import build_milestone_html
	return build_milestone_html(
		doctype=doctype,
		docname=docname,
		origin_name=origin_name or "Origin",
		destination_name=destination_name or "Destination",
		detail_items=detail_items,
		milestones=milestones,
		format_datetime_fn=format_dt,
		child_milestone_doctype=child_doctype,
		include_doc_alerts=False,
		include_origin_destination=False,
	)


@frappe.whitelist()
def get_document_template_items(product_type, applies_to, direction=None, entry_type=None):
	"""Get document template items for the given context."""
	filters = [
		["product_type", "=", product_type],
		["applies_to", "in", [applies_to, "Both"]],
	]

	templates = frappe.get_all(
		"Document List Template",
		filters=filters,
		fields=["name", "template_name", "is_default", "direction", "entry_type"],
		order_by="is_default asc",  # Default last as fallback
	)

	# Filter by direction/entry_type if specified
	if direction and direction != "All":
		templates = [t for t in templates if t.direction in (None, "", "All", direction)]
	if entry_type and entry_type != "All":
		templates = [t for t in templates if t.entry_type in (None, "", "All", entry_type)]

	# Prefer non-default first, then default
	template_name = None
	for t in templates:
		if not t.is_default:
			template_name = t.name
			break
	if not template_name and templates:
		template_name = next((t.name for t in templates if t.is_default), templates[0].name)

	if not template_name:
		return []

	items = frappe.get_all(
		"Document List Template Item",
		filters={"parent": template_name},
		fields=["document_type", "sequence", "is_mandatory", "date_required_basis", "days_offset", "allow_early_upload", "description"],
		order_by="sequence asc",
	)

	return items


@frappe.whitelist()
def populate_documents_from_template(doctype, docname):
	"""Populate documents child table from template. Only adds missing document types."""
	if not doctype or not docname or docname == "new":
		return {"message": "Save the document first."}

	doc = frappe.get_doc(doctype, docname)
	context = DOCTYPE_CONTEXT.get(doctype)
	if not context:
		return {"message": "Documents not supported for this doctype."}

	product_type, applies_to = context
	direction = getattr(doc, "direction", None) or ""
	entry_type = getattr(doc, "entry_type", None) or ""

	# Use override template if set
	template_name = getattr(doc, "document_list_template", None)
	if not template_name:
		items = get_document_template_items(product_type, applies_to, direction, entry_type)
	else:
		items = frappe.get_all(
			"Document List Template Item",
			filters={"parent": template_name},
			fields=["document_type", "sequence", "is_mandatory", "date_required_basis", "days_offset", "allow_early_upload", "description"],
			order_by="sequence asc",
		)

	existing_types = {d.document_type for d in (doc.get("documents") or [])}

	added = 0
	for item in items:
		if item.document_type in existing_types:
			continue
		date_required = _compute_date_required(doc, item)
		row = doc.append("documents", {
			"document_type": item.document_type,
			"is_required": 1 if item.is_mandatory else 0,
			"status": "Pending",
			"date_required": date_required,
		})
		existing_types.add(item.document_type)
		added += 1

	if added:
		doc.flags.ignore_validate = True
		doc.save()

	return {"message": f"Added {added} document(s) from template.", "added": added}


def _compute_date_required(doc, template_item):
	"""Compute date_required from parent doc and template item."""
	if not template_item or not template_item.get("date_required_basis"):
		return None
	basis = template_item["date_required_basis"]
	offset = template_item.get("days_offset") or 0

	base_date = None
	if basis == "ETD":
		base_date = getattr(doc, "etd", None)
	elif basis == "ETA":
		base_date = getattr(doc, "eta", None)
	elif basis == "Booking Date":
		base_date = getattr(doc, "booking_date", None) or getattr(doc, "order_date", None)
	elif basis == "Job Date":
		base_date = (
			getattr(doc, "booking_date", None)
			or getattr(doc, "order_date", None)
			or getattr(doc, "start_date", None)
			or getattr(doc, "planned_start", None)
			or doc.creation
		)
	if not base_date:
		return None
	base_date = getdate(base_date)
	return add_days(base_date, offset)


# --- Milestone template and population ---


@frappe.whitelist()
def get_milestone_template_items(product_type, applies_to, direction=None, entry_type=None):
	"""Resolve milestone template for context and return list of Milestone Template Items."""
	filters = [
		["product_type", "=", product_type],
		["applies_to", "in", [applies_to, "Both"]],
	]
	templates = frappe.get_all(
		"Milestone Template",
		filters=filters,
		fields=["name", "template_name", "is_default", "direction", "entry_type"],
		order_by="is_default asc",
	)
	if direction and direction != "All":
		templates = [t for t in templates if (t.direction or "") in ("", "All", direction)]
	if entry_type and entry_type != "All":
		templates = [t for t in templates if (t.entry_type or "") in ("", "All", entry_type)]
	template_name = None
	for t in templates:
		if not t.is_default:
			template_name = t.name
			break
	if not template_name and templates:
		template_name = next((t.name for t in templates if t.is_default), templates[0].name)
	if not template_name:
		return []
	items = frappe.get_all(
		"Milestone Template Item",
		filters={"parent": template_name},
		fields=["milestone", "icon", "date_basis", "planned_days_offset"],
		order_by="idx asc",
	)
	return items


def _compute_milestone_planned_date(doc, template_item):
	"""Return planned_end date for a milestone row from doc and template item (date_basis + planned_days_offset)."""
	basis = (template_item or {}).get("date_basis")
	offset = (template_item or {}).get("planned_days_offset") or 0
	base_date = None
	if basis == "ETD":
		base_date = getattr(doc, "etd", None)
	elif basis == "ETA":
		base_date = getattr(doc, "eta", None)
	elif basis == "Booking Date":
		base_date = getattr(doc, "booking_date", None) or getattr(doc, "order_date", None)
	elif basis == "Job Date":
		base_date = (
			getattr(doc, "booking_date", None)
			or getattr(doc, "order_date", None)
			or getattr(doc, "start_date", None)
			or getattr(doc, "planned_start", None)
			or getattr(doc, "declaration_date", None)
			or getattr(doc, "scheduled_date", None)
			or doc.creation
		)
	if not base_date:
		return None
	base_date = getdate(base_date)
	return add_days(base_date, offset)


@frappe.whitelist()
def populate_milestones_from_template(doctype, docname):
	"""Populate parent's milestones child table from template. Only adds missing milestones."""
	if not doctype or not docname or docname == "new":
		return {"message": "Save the document first.", "added": 0}
	if doctype not in MILESTONE_DOCTYPES:
		return {"message": "Milestones not supported for this doctype.", "added": 0}
	doc = frappe.get_doc(doctype, docname)
	context = DOCTYPE_CONTEXT.get(doctype)
	if not context:
		return {"message": "Context not found.", "added": 0}
	product_type, applies_to = context
	direction = getattr(doc, "direction", None) or ""
	entry_type = getattr(doc, "entry_type", None) or ""

	template_name = getattr(doc, "milestone_template", None)
	if template_name:
		items = frappe.get_all(
			"Milestone Template Item",
			filters={"parent": template_name},
			fields=["milestone", "icon", "date_basis", "planned_days_offset"],
			order_by="idx asc",
		)
	else:
		items = get_milestone_template_items(product_type, applies_to, direction, entry_type)

	existing_milestones = {row.milestone for row in (doc.get("milestones") or [])}
	added = 0
	for item in items:
		milestone = item.get("milestone")
		if not milestone or milestone in existing_milestones:
			continue
		planned_end = _compute_milestone_planned_date(doc, item)
		row_data = {
			"milestone": milestone,
			"status": "Planned",
			"planned_end": planned_end,
			"source": "Manual",
		}
		icon = item.get("icon")
		if not icon:
			lm = frappe.db.get_value("Logistics Milestone", milestone, "icon")
			if lm:
				icon = lm
		if icon:
			row_data["icon"] = icon
		doc.append("milestones", row_data)
		existing_milestones.add(milestone)
		added += 1
	if added:
		doc.flags.ignore_validate = True
		doc.save()
	return {"message": f"Added {added} milestone(s) from template.", "added": added}


@frappe.whitelist()
def get_document_alerts(doctype, docname):
	"""Return document alerts for dashboard: missing, overdue, expiring_soon, and counts."""
	if not doctype or not docname or docname == "new":
		return {
			"missing": [], "overdue": [], "expiring_soon": [],
			"counts": {"pending": 0, "overdue": 0, "expiring_soon": 0, "received": 0, "total": 0},
		}

	try:
		doc = frappe.get_doc(doctype, docname)
	except frappe.DoesNotExistError:
		# Document not found (may happen immediately after creation due to replication lag)
		return {
			"missing": [], "overdue": [], "expiring_soon": [],
			"counts": {"pending": 0, "overdue": 0, "expiring_soon": 0, "received": 0, "total": 0},
		}
	except Exception:
		# Any other error - log and return empty
		frappe.log_error(f"Error getting document alerts for {doctype} {docname}")
		return {
			"missing": [], "overdue": [], "expiring_soon": [],
			"counts": {"pending": 0, "overdue": 0, "expiring_soon": 0, "received": 0, "total": 0},
		}

	documents = doc.get("documents") or []

	missing = []
	overdue = []
	expiring_soon = []
	today_date = getdate(today())
	received_count = 0

	for d in documents:
		status = (d.get("status") or "").strip()
		date_required = d.get("date_required")
		expiry_date = d.get("expiry_date")
		is_required = d.get("is_required")

		# Count received/verified/done
		if status in ("Received", "Verified", "Done"):
			received_count += 1

		# Overdue: required, not received/verified, past date_required
		if is_required and status in ("Pending", "Uploaded", "Overdue"):
			if date_required and getdate(date_required) < today_date:
				days_overdue = date_diff(today_date, getdate(date_required))
				overdue.append({
					"document_type": d.document_type,
					"date_required": date_required,
					"days_overdue": days_overdue,
					"status": status,
				})
			elif not d.get("attachment"):
				missing.append({
					"document_type": d.document_type,
					"date_required": date_required,
					"status": status,
				})

		# Expiring soon (within 7 days)
		if expiry_date:
			exp = getdate(expiry_date)
			if exp >= today_date and date_diff(exp, today_date) <= 7:
				expiring_soon.append({
					"document_type": d.document_type,
					"expiry_date": expiry_date,
				})

	counts = {
		"pending": len(missing),
		"overdue": len(overdue),
		"expiring_soon": len(expiring_soon),
		"received": received_count,
		"total": len(documents),
	}
	return {"missing": missing, "overdue": overdue, "expiring_soon": expiring_soon, "counts": counts}


@frappe.whitelist()
def get_document_alerts_html(doctype, docname):
	"""Return HTML for document alerts as number cards to embed in dashboard."""
	alerts = get_document_alerts(doctype, docname)
	counts = alerts.get("counts") or {}
	pending = counts.get("pending", 0)
	overdue = counts.get("overdue", 0)
	expiring_soon = counts.get("expiring_soon", 0)
	received = counts.get("received", 0)
	total = counts.get("total", 0)

	# Declaration and Declaration Order: add pending permits and exemptions counts
	pending_permits = 0
	exemptions_count = 0
	if doctype in ("Declaration", "Declaration Order") and docname and docname != "new":
		try:
			doc = frappe.get_doc(doctype, docname)
			for pr in (doc.get("permit_requirements") or []):
				if pr.get("is_required") and not pr.get("is_obtained"):
					pending_permits += 1
			exemptions_count = len(doc.get("exemptions") or [])
		except Exception:
			pass

	# Build number cards: show cards that have meaning (total > 0 or we still show summary)
	# For Declaration and Declaration Order, always show permits and exemptions cards
	has_standard_cards = total > 0 or pending > 0 or overdue > 0 or expiring_soon > 0 or received > 0
	has_declaration_cards = doctype in ("Declaration", "Declaration Order")
	if not has_standard_cards and not has_declaration_cards:
		return ""

	cards = []
	# Pending (required, not yet received, due today or later)
	cards.append(_doc_alert_card("Pending", pending, "doc-alert-card-pending", "warning", "pending"))
	# Overdue (required, past due date)
	cards.append(_doc_alert_card("Overdue", overdue, "doc-alert-card-overdue", "danger", "overdue"))
	# Expiring soon (within 7 days)
	cards.append(_doc_alert_card("Expiring Soon", expiring_soon, "doc-alert-card-expiring", "info", "expiring_soon"))
	# Received/Verified/Done
	cards.append(_doc_alert_card("Received", received, "doc-alert-card-received", "success", "received"))
	# Total documents
	cards.append(_doc_alert_card("Total", total, "doc-alert-card-total", "secondary", "total"))

	# Declaration and Declaration Order: Pending Permits and Exemptions cards
	if doctype in ("Declaration", "Declaration Order"):
		cards.append(_doc_alert_card("Pending Permits", pending_permits, "doc-alert-card-permits", "warning", "pending_permits"))
		cards.append(_doc_alert_card("Exemptions", exemptions_count, "doc-alert-card-exemptions", "info", "exemptions"))

	cards_html = "\n".join(cards)
	return f'''
	<div class="doc-alerts-cards-wrapper" style="margin-bottom: 16px;" data-doctype="{doctype}" data-docname="{docname}">
		<div class="doc-alerts-cards">
			{cards_html}
		</div>
	</div>
	'''


def _doc_alert_card(title, count, css_class, alert_type, category):
	"""Return HTML for a single document count card (clickable, data-category for dialog)."""
	return (
		f'<div class="doc-alert-card {css_class} doc-alert-card-{alert_type}" data-category="{category}" style="cursor: pointer;">'
		f'<div class="doc-alert-card-value">{count}</div>'
		f'<div class="doc-alert-card-title">{title}</div>'
		f'</div>'
	)


@frappe.whitelist()
def get_document_list_for_category(doctype, docname, category):
	"""Return list of documents for a category (pending, overdue, expiring_soon, received, total) for dialog."""
	if not doctype or not docname or docname == "new" or not category:
		return {"documents": [], "category": category}

	doc = frappe.get_doc(doctype, docname)
	documents = doc.get("documents") or []
	today_date = getdate(today())
	out = []

	for d in documents:
		idx = d.get("idx")
		if not idx:
			continue
		status = (d.get("status") or "").strip()
		date_required = d.get("date_required")
		expiry_date = d.get("expiry_date")
		is_required = d.get("is_required")
		attachment = d.get("attachment") or ""

		row = {
			"idx": idx,
			"document_type": d.get("document_type"),
			"document_name": d.get("document_name") or d.get("document_type"),
			"status": status,
			"date_required": date_required,
			"expiry_date": expiry_date,
			"attachment": attachment,
			"has_attachment": 1 if attachment else 0,
			"is_required": is_required,
		}

		if category == "total":
			out.append(row)
			continue
		if category == "pending":
			if is_required and status in ("Pending", "Uploaded", "Overdue") and not attachment:
				if not date_required or getdate(date_required) >= today_date:
					out.append(row)
			continue
		if category == "overdue":
			if is_required and status in ("Pending", "Uploaded", "Overdue") and date_required and getdate(date_required) < today_date:
				out.append(row)
			continue
		if category == "expiring_soon":
			if expiry_date:
				exp = getdate(expiry_date)
				if exp >= today_date and date_diff(exp, today_date) <= 7:
					out.append(row)
			continue
		if category == "received":
			if status in ("Received", "Verified", "Done"):
				out.append(row)

	return {"documents": out, "category": category}


@frappe.whitelist()
def set_document_attachment(doctype, docname, idx, file_url):
	"""Set attachment on a document row by child table idx. Returns ok/message."""
	if not doctype or not docname or docname == "new":
		return {"ok": False, "message": "Invalid document."}
	try:
		idx = int(idx)
	except (TypeError, ValueError):
		return {"ok": False, "message": "Invalid row index."}
	doc = frappe.get_doc(doctype, docname)
	documents = doc.get("documents") or []
	found = False
	for row in documents:
		if row.get("idx") == idx:
			row.attachment = file_url or ""
			found = True
			break
	if not found:
		return {"ok": False, "message": "Row not found."}
	doc.flags.ignore_validate = True
	doc.save()
	return {"ok": True, "message": "Attachment updated."}


@frappe.whitelist()
def get_google_maps_api_key():
	"""Get Google Maps API key from Logistics Settings for client-side map use."""
	try:
		from frappe.utils.password import get_decrypted_password
		api_key = get_decrypted_password(
			"Logistics Settings",
			"Logistics Settings",
			"routing_google_api_key",
			raise_exception=False,
		)
		if not api_key:
			api_key = get_decrypted_password(
				"Transport Settings",
				"Transport Settings",
				"routing_google_api_key",
				raise_exception=False,
			)
		if api_key and len(api_key) > 10:
			return {"api_key": api_key, "has_key": True}
		return {"api_key": None, "has_key": False}
	except Exception as e:
		frappe.log_error(f"get_google_maps_api_key: {e}", "Dashboard Map")
		return {"api_key": None, "has_key": False}


def _decode_google_polyline(encoded):
	"""Decode Google polyline encoding to list of [lat, lng] coordinates."""
	if not encoded:
		return []
	inv = 1.0 / 1e5
	coords = []
	x, y = 0, 0
	i = 0
	while i < len(encoded):
		b, shift, result = 0, 0, 0
		while True:
			b = ord(encoded[i]) - 63
			i += 1
			result |= (b & 0x1f) << shift
			shift += 5
			if b < 0x20:
				break
		dlat = ~(result >> 1) if result & 1 else result >> 1
		x += dlat
		result, shift = 0, 0
		while True:
			b = ord(encoded[i]) - 63
			i += 1
			result |= (b & 0x1f) << shift
			shift += 5
			if b < 0x20:
				break
		dlng = ~(result >> 1) if result & 1 else result >> 1
		y += dlng
		coords.append([x * inv, y * inv])
	return coords


@frappe.whitelist()
def get_route_geometry(waypoints):
	"""
	Get road-following route geometry for waypoints (same logic as Run Sheet).
	Uses Google Directions API when key is configured, else OSRM public API.
	Returns coordinates suitable for polyline drawing on any map.

	Args:
		waypoints: "lat,lon|lat,lon|..." or list of [lat, lon]

	Returns:
		dict: {success, coordinates: [[lat,lng],...], error?}
	"""
	try:
		points = []
		if isinstance(waypoints, str):
			for p in waypoints.split("|"):
				p = p.strip()
				if not p:
					continue
				parts = p.split(",")
				if len(parts) >= 2:
					lat = float(parts[0].strip())
					lon = float(parts[1].strip())
					if -90 <= lat <= 90 and -180 <= lon <= 180:
						points.append((lat, lon))
		elif isinstance(waypoints, (list, tuple)):
			for wp in waypoints:
				if isinstance(wp, (list, tuple)) and len(wp) >= 2:
					lat, lon = float(wp[0]), float(wp[1])
					if -90 <= lat <= 90 and -180 <= lon <= 180:
						points.append((lat, lon))
				elif isinstance(wp, dict):
					lat = wp.get("lat") or wp.get("latitude")
					lon = wp.get("lon") or wp.get("lng") or wp.get("longitude")
					if lat is not None and lon is not None:
						lat, lon = float(lat), float(lon)
						if -90 <= lat <= 90 and -180 <= lon <= 180:
							points.append((lat, lon))

		if len(points) < 2:
			return {"success": False, "error": "Need at least 2 waypoints", "coordinates": []}

		# Try Google Directions API first (same as Run Sheet)
		try:
			from logistics.transport.api_vehicle_tracking import get_google_route_polyline
			wp_str = "|".join(f"{p[0]},{p[1]}" for p in points)
			res = get_google_route_polyline(wp_str)
			if res and res.get("success") and res.get("polyline"):
				coords = _decode_google_polyline(res["polyline"])
				if coords:
					return {"success": True, "coordinates": coords}
		except Exception:
			pass

		# Fallback: OSRM public API (no key required)
		try:
			import requests
			coords_str = ";".join(f"{p[1]},{p[0]}" for p in points)  # lon,lat for OSRM
			url = f"https://router.project-osrm.org/route/v1/driving/{coords_str}"
			r = requests.get(url, params={"overview": "full", "geometries": "geojson"}, timeout=10)
			if r.ok:
				js = r.json()
				routes = (js or {}).get("routes") or []
				if routes:
					geom = routes[0].get("geometry") or {}
					coords_raw = geom.get("coordinates") or []
					# GeoJSON is [lon, lat]
					coords = [[c[1], c[0]] for c in coords_raw if len(c) >= 2]
					if coords:
						return {"success": True, "coordinates": coords}
		except Exception:
			pass

		# Final fallback: straight line between points
		return {"success": True, "coordinates": [[p[0], p[1]] for p in points]}

	except Exception as e:
		frappe.log_error(f"get_route_geometry: {e}", "Route Geometry")
		return {"success": False, "error": str(e), "coordinates": []}
