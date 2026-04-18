# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Propagate data from linked freight/transport documents when integration link fields are set.
Used by Declaration Order, Declaration, Transport Order, Transport Job, Inbound Order, Release Order, Warehouse Job.
"""

import frappe
from frappe.utils import cint

from logistics.utils.dg_fields import copy_parent_dg_header, transport_order_package_row_from_shipment_pkg
from logistics.utils.operational_rep_fields import REP_FIELD_NAMES, copy_operational_rep_fields_from_chain
from logistics.utils.internal_job_detail_copy import (
	get_declaration_order_job_no_from_shipment_doc,
	persist_internal_job_detail_job_link,
)
from logistics.utils.internal_job_from_source import (
	apply_internal_job_detail_row_to_operational_doc,
	coerce_internal_job_detail_idx,
	resolve_internal_job_detail_row_for_create,
)
from logistics.transport.doctype.transport_order.transport_order import (
	append_transport_order_charges_from_sales_quote_if_empty,
)
from logistics.utils.container_validation import normalize_container_number


def propagate_from_air_shipment(doc, fieldname="air_shipment"):
	"""Populate doc fields from linked Air Shipment. Call from before_save when air_shipment is set."""
	if not getattr(doc, fieldname, None):
		return
	try:
		shipment = frappe.get_cached_doc("Air Shipment", doc.get(fieldname))
	except Exception:
		return

	# Map by doctype - each doctype may need different fields
	doctype = doc.doctype
	if doctype == "Declaration Order":
		_set_if_empty(doc, "customer", getattr(shipment, "local_customer", None))
		_set_if_empty(doc, "customs_authority", None)  # Shipment may not have this
	elif doctype == "Declaration":
		_set_if_empty(doc, "exporter_shipper", getattr(shipment, "shipper", None))
		_set_if_empty(doc, "importer_consignee", getattr(shipment, "consignee", None))
		_set_if_empty(doc, "transport_mode", "Air")
		_set_if_empty(doc, "port_of_loading", getattr(shipment, "origin_port", None))
		_set_if_empty(doc, "port_of_discharge", getattr(shipment, "destination_port", None))
		_set_if_empty(doc, "vessel_flight_number", getattr(shipment, "flight_number", None))
		_set_if_empty(doc, "etd", getattr(shipment, "etd", None))
		_set_if_empty(doc, "eta", getattr(shipment, "eta", None))
	elif doctype == "Transport Order":
		_set_if_empty(doc, "location_type", "UNLOCO")
		_set_if_empty(doc, "location_from", getattr(shipment, "origin_port", None))
		_set_if_empty(doc, "location_to", getattr(shipment, "destination_port", None))
		_set_if_empty(doc, "booking_date", getattr(shipment, "booking_date", None))
		_set_if_empty(doc, "customer", getattr(shipment, "local_customer", None))
		_set_if_empty(doc, "contains_dangerous_goods", getattr(shipment, "contains_dangerous_goods", None))
		for fn in ("dg_declaration_complete", "dg_compliance_status", "dg_emergency_contact", "dg_emergency_phone", "dg_emergency_email"):
			_set_if_empty(doc, fn, getattr(shipment, fn, None))
	elif doctype == "Transport Job":
		_set_if_empty(doc, "customer", getattr(shipment, "local_customer", None))
		_set_if_empty(doc, "booking_date", getattr(shipment, "booking_date", None))
	elif doctype == "Inbound Order":
		_set_if_empty(doc, "shipper", getattr(shipment, "shipper", None))
		_set_if_empty(doc, "consignee", getattr(shipment, "consignee", None))
		_set_if_empty(doc, "customer", getattr(shipment, "local_customer", None))
		_set_if_empty(doc, "planned_date", getattr(shipment, "eta", None))
		_set_if_empty(doc, "due_date", getattr(shipment, "eta", None))
		try:
			apply_inbound_order_freight_job_context_from_shipment(
				doc, shipment, "Air Shipment", doc.get(fieldname)
			)
		except Exception:
			pass
	elif doctype == "Release Order":
		_set_if_empty(doc, "shipper", getattr(shipment, "shipper", None))
		_set_if_empty(doc, "consignee", getattr(shipment, "consignee", None))
		_set_if_empty(doc, "customer", getattr(shipment, "local_customer", None))
		try:
			apply_inbound_order_freight_job_context_from_shipment(
				doc, shipment, "Air Shipment", doc.get(fieldname)
			)
		except Exception:
			pass
	elif doctype == "Warehouse Job":
		_set_if_empty(doc, "shipper", getattr(shipment, "shipper", None))
		_set_if_empty(doc, "consignee", getattr(shipment, "consignee", None))
		_set_if_empty(doc, "customer", getattr(shipment, "local_customer", None))

	if doctype in ("Transport Order", "Transport Job", "Declaration", "Declaration Order", "Inbound Order", "Release Order"):
		propagate_sales_quote_from_source_if_empty(shipment, doc)


def propagate_from_sea_shipment(doc, fieldname="sea_shipment"):
	"""Populate doc fields from linked Sea Shipment."""
	if not getattr(doc, fieldname, None):
		return
	try:
		shipment = frappe.get_cached_doc("Sea Shipment", doc.get(fieldname))
	except Exception:
		return

	doctype = doc.doctype
	if doctype == "Declaration Order":
		_set_if_empty(doc, "customer", getattr(shipment, "local_customer", None))
	elif doctype == "Declaration":
		_set_if_empty(doc, "exporter_shipper", getattr(shipment, "shipper", None))
		_set_if_empty(doc, "importer_consignee", getattr(shipment, "consignee", None))
		_set_if_empty(doc, "transport_mode", "Sea")
		_set_if_empty(doc, "port_of_loading", getattr(shipment, "origin_port", None))
		_set_if_empty(doc, "port_of_discharge", getattr(shipment, "destination_port", None))
		_set_if_empty(doc, "vessel_flight_number", getattr(shipment, "vessel", None))
		_set_if_empty(doc, "etd", getattr(shipment, "etd", None))
		_set_if_empty(doc, "eta", getattr(shipment, "eta", None))
	elif doctype == "Transport Order":
		_set_if_empty(doc, "location_type", "UNLOCO")
		_set_if_empty(doc, "location_from", getattr(shipment, "origin_port", None))
		_set_if_empty(doc, "location_to", getattr(shipment, "destination_port", None))
		_set_if_empty(doc, "booking_date", getattr(shipment, "booking_date", None))
		_set_if_empty(doc, "customer", getattr(shipment, "local_customer", None))
		_set_if_empty(doc, "contains_dangerous_goods", getattr(shipment, "contains_dangerous_goods", None))
		for fn in ("dg_declaration_complete", "dg_compliance_status", "dg_emergency_contact", "dg_emergency_phone", "dg_emergency_email"):
			_set_if_empty(doc, fn, getattr(shipment, fn, None))
	elif doctype == "Transport Job":
		_set_if_empty(doc, "customer", getattr(shipment, "local_customer", None))
		_set_if_empty(doc, "booking_date", getattr(shipment, "booking_date", None))
	elif doctype == "Inbound Order":
		_set_if_empty(doc, "shipper", getattr(shipment, "shipper", None))
		_set_if_empty(doc, "consignee", getattr(shipment, "consignee", None))
		_set_if_empty(doc, "customer", getattr(shipment, "local_customer", None))
		_set_if_empty(doc, "planned_date", getattr(shipment, "eta", None))
		_set_if_empty(doc, "due_date", getattr(shipment, "eta", None))
		try:
			apply_inbound_order_freight_job_context_from_shipment(
				doc, shipment, "Sea Shipment", doc.get(fieldname)
			)
		except Exception:
			pass
	elif doctype == "Release Order":
		_set_if_empty(doc, "shipper", getattr(shipment, "shipper", None))
		_set_if_empty(doc, "consignee", getattr(shipment, "consignee", None))
		_set_if_empty(doc, "customer", getattr(shipment, "local_customer", None))
		try:
			apply_inbound_order_freight_job_context_from_shipment(
				doc, shipment, "Sea Shipment", doc.get(fieldname)
			)
		except Exception:
			pass
	elif doctype == "Warehouse Job":
		_set_if_empty(doc, "shipper", getattr(shipment, "shipper", None))
		_set_if_empty(doc, "consignee", getattr(shipment, "consignee", None))
		_set_if_empty(doc, "customer", getattr(shipment, "local_customer", None))

	if doctype in ("Transport Order", "Transport Job", "Declaration", "Declaration Order", "Inbound Order", "Release Order"):
		propagate_sales_quote_from_source_if_empty(shipment, doc)


def propagate_from_transport_job(doc, fieldname="transport_job"):
	"""Populate doc fields from linked Transport Job."""
	if not getattr(doc, fieldname, None):
		return
	try:
		job = frappe.get_cached_doc("Transport Job", doc.get(fieldname))
	except Exception:
		return

	doctype = doc.doctype
	if doctype == "Inbound Order":
		_set_if_empty(doc, "shipper", getattr(job, "shipper", None))
		_set_if_empty(doc, "consignee", getattr(job, "consignee", None))
		_set_if_empty(doc, "customer", getattr(job, "customer", None))
		_set_if_empty(doc, "planned_date", getattr(job, "scheduled_date", None))
		_set_if_empty(doc, "due_date", getattr(job, "scheduled_date", None))
		propagate_sales_quote_from_source_if_empty(job, doc)
		try:
			apply_inbound_order_job_context_from_transport_job(doc, job)
		except Exception:
			pass
	elif doctype == "Warehouse Job":
		_set_if_empty(doc, "shipper", getattr(job, "shipper", None))
		_set_if_empty(doc, "consignee", getattr(job, "consignee", None))
		_set_if_empty(doc, "customer", getattr(job, "customer", None))

	if doctype == "Declaration":
		propagate_sales_quote_from_source_if_empty(job, doc)


def propagate_from_transport_order(doc, fieldname="transport_order"):
	"""Populate doc fields from linked Transport Order (for Declaration, Release Order)."""
	if not getattr(doc, fieldname, None):
		return
	try:
		order = frappe.get_cached_doc("Transport Order", doc.get(fieldname))
	except Exception:
		return

	doctype = doc.doctype
	if doctype == "Declaration":
		_set_if_empty(doc, "port_of_loading", getattr(order, "location_from", None))
		_set_if_empty(doc, "port_of_discharge", getattr(order, "location_to", None))
		_set_if_empty(doc, "etd", getattr(order, "etd", None))
		_set_if_empty(doc, "eta", getattr(order, "eta", None))
		propagate_sales_quote_from_source_if_empty(order, doc)
	elif doctype == "Release Order":
		_set_if_empty(doc, "customer", getattr(order, "customer", None))
		propagate_sales_quote_from_source_if_empty(order, doc)
		try:
			apply_warehousing_job_context_from_internal_job_source(doc, order)
		except Exception:
			pass
	if doctype == "Declaration Order":
		propagate_sales_quote_from_source_if_empty(order, doc)


def run_propagate_on_link(doc):
	"""Call from before_save to propagate from any set link fields."""
	if doc.flags.ignore_propagate:
		return
	if getattr(doc, "air_shipment", None):
		propagate_from_air_shipment(doc)
	if getattr(doc, "sea_shipment", None):
		propagate_from_sea_shipment(doc)
	if getattr(doc, "transport_job", None):
		propagate_from_transport_job(doc)
	if getattr(doc, "transport_order", None):
		propagate_from_transport_order(doc)


def apply_internal_job_declaration_order_from_shipment(doc):
	"""Declaration Order before_save: sync main-job link from Air/Sea Shipment when this is an internal job.

	Runs after ``run_propagate_on_link`` so shipment-driven customer / sales_quote are already set.
	Fills ``main_job_type`` / ``main_job`` only when still empty (user or dialog values win).
	"""
	from frappe.utils import cint

	if doc.doctype != "Declaration Order" or not cint(getattr(doc, "is_internal_job", 0)):
		return

	shipment_dt = shipment_name = None
	if getattr(doc, "air_shipment", None):
		shipment_dt, shipment_name = "Air Shipment", doc.air_shipment
	elif getattr(doc, "sea_shipment", None):
		shipment_dt, shipment_name = "Sea Shipment", doc.sea_shipment
	else:
		return

	try:
		shipment = frappe.get_cached_doc(shipment_dt, shipment_name)
	except Exception:
		return

	for fn in ("main_job_type", "main_job"):
		if hasattr(doc, fn) and hasattr(shipment, fn):
			_set_if_empty(doc, fn, getattr(shipment, fn, None))


def _set_if_empty(doc, fieldname, value):
	"""Set doc.fieldname = value only if doc.fieldname is empty."""
	if value is None:
		return
	if not hasattr(doc, fieldname):
		return
	current = getattr(doc, fieldname, None)
	if current is None or current == "":
		try:
			setattr(doc, fieldname, value)
		except Exception:
			pass


def _resolve_sales_quote_from_doc(source_doc):
	"""Return linked Sales Quote name from sales_quote or from quote (One-off / legacy) if it is a Sales Quote."""
	sq = getattr(source_doc, "sales_quote", None)
	if sq and frappe.db.exists("Sales Quote", sq):
		return sq
	q = getattr(source_doc, "quote", None)
	if q and frappe.db.exists("Sales Quote", q):
		return q
	return None


def copy_sales_quote_fields_to_target(source_doc, target_doc):
	"""Propagate ``sales_quote`` link (or legacy ``quote`` when it points at a Sales Quote) and rep fields.

	Does **not** copy commercial header fields (ports, parties, charges, etc.) — only the link and
	``sales_rep`` / ``operations_rep`` / ``customer_service_rep`` via ``copy_operational_rep_fields_from_chain``.
	"""
	sq = _resolve_sales_quote_from_doc(source_doc)
	if sq and hasattr(target_doc, "sales_quote"):
		target_doc.sales_quote = sq
	copy_operational_rep_fields_from_chain(target_doc, source_doc=source_doc)


def propagate_sales_quote_from_source_if_empty(source_doc, target_doc):
	"""When user links air/sea shipment or similar, fill sales_quote and rep fields if still empty."""
	sq = _resolve_sales_quote_from_doc(source_doc)
	if sq and hasattr(target_doc, "sales_quote"):
		_set_if_empty(target_doc, "sales_quote", sq)
	for fn in REP_FIELD_NAMES:
		if hasattr(target_doc, fn):
			_set_if_empty(target_doc, fn, getattr(source_doc, fn, None))
	if sq:
		try:
			sqdoc = frappe.get_cached_doc("Sales Quote", sq)
		except Exception:
			sqdoc = None
		if sqdoc:
			for fn in REP_FIELD_NAMES:
				if hasattr(target_doc, fn):
					_set_if_empty(target_doc, fn, getattr(sqdoc, fn, None))


# -------------------------------------------------------------------
# Transport Order Leg Restrictions (from Logistics Settings)
# -------------------------------------------------------------------

def _get_allowed_transport_order_legs():
	"""Get (direction, leg_type) pairs from Logistics Settings. If empty, default to Import+On-forwarding, Export+Pre-carriage."""
	settings = frappe.get_single("Logistics Settings")
	rows = getattr(settings, "allowed_transport_order_legs", None) or []
	if not rows:
		return [
			("Import", "On-forwarding"),
			("Export", "Pre-carriage"),
		]
	return [(r.direction, r.leg_type) for r in rows if r.direction and r.leg_type]


def _can_create_transport_order_from_shipment(shipment, direction_field="direction"):
	"""Check if shipment has at least one routing leg that matches allowed (direction, leg_type) from settings."""
	allowed = set(_get_allowed_transport_order_legs())
	direction = getattr(shipment, direction_field, None) or ""
	routing_legs = getattr(shipment, "routing_legs", None) or []
	if routing_legs:
		for leg in routing_legs:
			leg_type = getattr(leg, "type", None) or ""
			if (direction, leg_type) in allowed:
				return True, leg
		return False, None
	# No routing legs: infer from direction. Export -> Pre-carriage, Import -> On-forwarding
	if direction == "Export" and ("Export", "Pre-carriage") in allowed:
		return True, None
	if direction == "Import" and ("Import", "On-forwarding") in allowed:
		return True, None
	if direction == "Domestic":
		for dt, lt in allowed:
			if dt == "Domestic":
				return True, None
	return False, None


def _sea_shipment_use_container_transport_mode(shipment) -> bool:
	"""True when this shipment should drive a container Transport Order (header type and/or per-line container refs)."""
	if getattr(shipment, "container_type", None):
		return True
	return len(_collect_distinct_container_numbers_sea_shipment(shipment)) > 0


def _validate_sea_shipment_container_nos_for_transport_order(shipment) -> None:
	"""Require Container No. on rows whose Freight Mode has Requires Container No. (create Transport Order only)."""
	from frappe import _

	for i, row in enumerate(getattr(shipment, "containers", []) or [], 1):
		mode = getattr(row, "mode", None)
		if not mode:
			continue
		if not cint(frappe.db.get_value("Freight Mode", mode, "requires_container_no")):
			continue
		if not (getattr(row, "container_no", None) or "").strip():
			frappe.throw(
				_(
					"Container row {0}: enter Container No. for freight mode {1} before creating a Transport Order."
				).format(i, mode),
				title=_("Container Number Required"),
			)


def _collect_distinct_container_numbers_sea_shipment(shipment) -> list[str]:
	"""Distinct container numbers from Sea Shipment container rows and package lines (canonical display per ISO-normalized key)."""
	from logistics.container_management.api import sea_container_row_field_to_equipment_number

	seen: dict[str, str] = {}
	for row in getattr(shipment, "containers", []) or []:
		cn = getattr(row, "container_no", None)
		if cn and str(cn).strip():
			raw = str(cn).strip()
			key = sea_container_row_field_to_equipment_number(raw)
			if key and key not in seen:
				seen[key] = key
	for pkg in getattr(shipment, "packages", []) or []:
		cn = getattr(pkg, "container", None)
		if cn and str(cn).strip():
			raw = str(cn).strip()
			key = normalize_container_number(raw)
			if key and key not in seen:
				seen[key] = raw
	return [seen[k] for k in sorted(seen.keys())]


def _resolve_sea_shipment_container_for_transport_order(shipment, order, container_no=None) -> None:
	"""Set order.container_no for container moves; require explicit choice when multiple containers exist."""
	from frappe import _

	from logistics.container_management.api import sea_container_row_field_to_equipment_number

	if getattr(order, "transport_job_type", None) != "Container":
		return

	distinct = _collect_distinct_container_numbers_sea_shipment(shipment)
	passed = (container_no or "").strip()

	if len(distinct) > 1:
		if not passed:
			frappe.throw(
				_("This shipment has multiple containers. Select which container this transport order is for."),
				title=_("Container required"),
			)
		passed_key = normalize_container_number(passed)
		canonical = None
		for d in distinct:
			if normalize_container_number(d) == passed_key:
				canonical = d
				break
		if not canonical:
			frappe.throw(
				_("Container number does not match any container or cargo line on this shipment."),
				title=_("Invalid container"),
			)
		order.container_no = canonical
		return

	if len(distinct) == 1:
		order.container_no = distinct[0]
		return

	containers = getattr(shipment, "containers", []) or []
	if containers:
		c0 = getattr(containers[0], "container_no", None)
		if c0 and str(c0).strip():
			order.container_no = sea_container_row_field_to_equipment_number(c0) or str(c0).strip()
	if not order.container_no:
		for pkg in getattr(shipment, "packages", []) or []:
			cf = getattr(pkg, "container", None)
			if cf and str(cf).strip():
				order.container_no = str(cf).strip()
				break
	if passed:
		passed_key = normalize_container_number(passed)
		for pkg in getattr(shipment, "packages", []) or []:
			pc = getattr(pkg, "container", None)
			if pc and normalize_container_number(pc) == passed_key:
				order.container_no = passed.strip()
				return
		for row in getattr(shipment, "containers", []) or []:
			pc = getattr(row, "container_no", None)
			if pc:
				eq = sea_container_row_field_to_equipment_number(pc)
				if eq and eq == passed_key:
					order.container_no = eq
					return
		frappe.throw(
			_("Container number does not match any container or cargo line on this shipment."),
			title=_("Invalid container"),
		)


@frappe.whitelist()
def get_sea_shipment_containers_for_transport_order(sea_shipment_name: str | None = None):
	"""Return whether the user must pick a container before creating a Transport Order, and the list of options."""
	from frappe import _

	if not sea_shipment_name:
		frappe.throw(_("Sea Shipment is required."))
	shipment = frappe.get_doc("Sea Shipment", sea_shipment_name)
	distinct = _collect_distinct_container_numbers_sea_shipment(shipment)
	is_container = _sea_shipment_use_container_transport_mode(shipment)
	selection_required = len(distinct) > 1
	return {
		"selection_required": selection_required,
		"container_numbers": distinct,
		"is_container_shipment": is_container,
	}


# -------------------------------------------------------------------
# Create-From Actions
# -------------------------------------------------------------------

@frappe.whitelist()
def create_transport_order_from_air_shipment(
	air_shipment_name: str, routing_leg_idx: int = None, internal_job_detail_idx: int = None
):
	"""Create a Transport Order from an Air Shipment. Only allowed for pre-carriage or on-forwarding legs where company has control (per Logistics Settings).

	Routing-style header fields (locations, vehicle type, etc.) come from Internal Job Detail rows when present, not from Sales Quote routing parameters.
	"""
	from frappe import _

	shipment = frappe.get_doc("Air Shipment", air_shipment_name)
	detail_idx = coerce_internal_job_detail_idx(internal_job_detail_idx)
	ij_row, resolved_detail_idx = resolve_internal_job_detail_row_for_create(
		shipment, "Transport Order", detail_idx
	)
	can_create, matching_leg = _can_create_transport_order_from_shipment(shipment, direction_field="direction")
	if not can_create:
		allowed = _get_allowed_transport_order_legs()
		frappe.throw(
			_("Transport Order cannot be created: no routing leg matches allowed types (Direction + Leg Type). "
			  "Configure allowed legs in Logistics Settings > Transport Order. Allowed: {0}").format(
				", ".join("{0}+{1}".format(d, t) for d, t in allowed)
			)
		)
	order = frappe.new_doc("Transport Order")
	order.air_shipment = air_shipment_name
	order.customer = shipment.local_customer
	order.shipper = getattr(shipment, "shipper", None)
	order.consignee = getattr(shipment, "consignee", None)
	order.booking_date = shipment.booking_date or frappe.utils.today()
	order.scheduled_date = shipment.eta or shipment.etd or shipment.booking_date or frappe.utils.today()
	order.location_type = "UNLOCO"
	order.location_from = shipment.origin_port
	order.location_to = shipment.destination_port
	order.transport_job_type = "Non-Container"
	order.company = shipment.company or frappe.defaults.get_defaults().get("company")
	order.branch = getattr(shipment, "branch", None)
	order.cost_center = getattr(shipment, "cost_center", None)
	order.profit_center = getattr(shipment, "profit_center", None)
	order.project = getattr(shipment, "project", None)
	copy_sales_quote_fields_to_target(shipment, order)
	ij, mjt, mj = final_transport_order_job_context_from_freight_shipment(
		shipment, "Air Shipment", air_shipment_name
	)
	ij, mjt, mj = resolve_transport_order_freight_main_job_if_empty(
		shipment, "Air Shipment", air_shipment_name, ij, mjt, mj
	)
	order.is_internal_job = ij
	if ij:
		order.main_job_type = mjt
		order.main_job = mj
	else:
		order.main_job_type = None
		order.main_job = None
	if ij_row:
		apply_internal_job_detail_row_to_operational_doc(order, ij_row, overwrite=True)
	# Add door-to-door leg (restriction already enforced above)
	if shipment.shipper and shipment.consignee:
		leg = {
			"facility_type_from": "Shipper",
			"facility_from": shipment.shipper,
			"facility_type_to": "Consignee",
			"facility_to": shipment.consignee,
			"scheduled_date": shipment.eta or shipment.etd,
			"transport_job_type": "Non-Container",
		}
		if getattr(shipment, "shipper_address", None):
			leg["pick_address"] = shipment.shipper_address
		if getattr(shipment, "consignee_address", None):
			leg["drop_address"] = shipment.consignee_address
		order.append("legs", leg)
	copy_parent_dg_header(shipment, order)
	# Copy packages
	_copy_shipment_packages_to_transport_order(shipment, order)
	_copy_transport_charges_from_shipment_to_transport_order(order, shipment)
	append_transport_order_charges_from_sales_quote_if_empty(order)
	order.insert(ignore_permissions=True)
	persist_internal_job_detail_job_link(
		"Air Shipment", air_shipment_name, "Transport Order", order.name, detail_idx=resolved_detail_idx
	)
	ensure_main_service_on_freight_hub_for_transport_order_link("Air Shipment", air_shipment_name)
	frappe.db.commit()
	return {"transport_order": order.name, "message": _("Transport Order {0} created.").format(order.name)}


@frappe.whitelist()
def create_transport_order_from_sea_shipment(
	sea_shipment_name: str,
	routing_leg_idx: int = None,
	internal_job_detail_idx: int = None,
	container_no: str | None = None,
):
	"""Create a Transport Order from a Sea Shipment. Only allowed for pre-carriage or on-forwarding legs where company has control (per Logistics Settings).

	Routing-style header fields come from Internal Job Detail rows when present, not from Sales Quote routing parameters.
	When the shipment has multiple containers, pass ``container_no`` or set **Container No.** on the Internal Job Detail row (Transport).
	"""
	from frappe import _

	shipment = frappe.get_doc("Sea Shipment", sea_shipment_name)
	detail_idx = coerce_internal_job_detail_idx(internal_job_detail_idx)
	ij_row, resolved_detail_idx = resolve_internal_job_detail_row_for_create(
		shipment, "Transport Order", detail_idx
	)
	can_create, matching_leg = _can_create_transport_order_from_shipment(shipment, direction_field="direction")
	if not can_create:
		allowed = _get_allowed_transport_order_legs()
		frappe.throw(
			_("Transport Order cannot be created: no routing leg matches allowed types (Direction + Leg Type). "
			  "Configure allowed legs in Logistics Settings > Transport Order. Allowed: {0}").format(
				", ".join("{0}+{1}".format(d, t) for d, t in allowed)
			)
		)
	_validate_sea_shipment_container_nos_for_transport_order(shipment)
	order = frappe.new_doc("Transport Order")
	order.sea_shipment = sea_shipment_name
	order.customer = shipment.local_customer
	order.shipper = getattr(shipment, "shipper", None)
	order.consignee = getattr(shipment, "consignee", None)
	order.booking_date = shipment.booking_date or frappe.utils.today()
	order.scheduled_date = shipment.eta or shipment.etd or shipment.booking_date or frappe.utils.today()
	order.location_type = "UNLOCO"
	order.location_from = shipment.origin_port
	order.location_to = shipment.destination_port
	_use_container = _sea_shipment_use_container_transport_mode(shipment)
	order.transport_job_type = "Container" if _use_container else "Non-Container"
	order.container_type = getattr(shipment, "container_type", None)
	order.company = shipment.company or frappe.defaults.get_defaults().get("company")
	order.branch = getattr(shipment, "branch", None)
	order.cost_center = getattr(shipment, "cost_center", None)
	order.profit_center = getattr(shipment, "profit_center", None)
	order.project = getattr(shipment, "project", None)
	copy_sales_quote_fields_to_target(shipment, order)
	ij, mjt, mj = final_transport_order_job_context_from_freight_shipment(
		shipment, "Sea Shipment", sea_shipment_name
	)
	ij, mjt, mj = resolve_transport_order_freight_main_job_if_empty(
		shipment, "Sea Shipment", sea_shipment_name, ij, mjt, mj
	)
	order.is_internal_job = ij
	if ij:
		order.main_job_type = mjt
		order.main_job = mj
	else:
		order.main_job_type = None
		order.main_job = None
	if ij_row:
		apply_internal_job_detail_row_to_operational_doc(order, ij_row, overwrite=True)
	effective_cn = (container_no or "").strip() or (
		(getattr(ij_row, "container_no", None) or "").strip() if ij_row else ""
	)
	_resolve_sea_shipment_container_for_transport_order(
		shipment, order, container_no=effective_cn or None
	)
	# Add door-to-door leg (restriction already enforced above)
	if shipment.shipper and shipment.consignee:
		leg = {
			"facility_type_from": "Shipper",
			"facility_from": shipment.shipper,
			"facility_type_to": "Consignee",
			"facility_to": shipment.consignee,
			"scheduled_date": shipment.eta or shipment.etd,
			"transport_job_type": "Container" if _use_container else "Non-Container",
		}
		if getattr(shipment, "shipper_address", None):
			leg["pick_address"] = shipment.shipper_address
		if getattr(shipment, "consignee_address", None):
			leg["drop_address"] = shipment.consignee_address
		order.append("legs", leg)
	copy_parent_dg_header(shipment, order)
	_copy_sea_packages_to_transport_order(shipment, order)
	_copy_transport_charges_from_shipment_to_transport_order(order, shipment)
	append_transport_order_charges_from_sales_quote_if_empty(order)
	order.insert(ignore_permissions=True)
	persist_internal_job_detail_job_link(
		"Sea Shipment", sea_shipment_name, "Transport Order", order.name, detail_idx=resolved_detail_idx
	)
	ensure_main_service_on_freight_hub_for_transport_order_link("Sea Shipment", sea_shipment_name)
	frappe.db.commit()
	return {"transport_order": order.name, "message": _("Transport Order {0} created.").format(order.name)}


def _declaration_order_allowed_from_shipment(shipment) -> None:
	"""Throw if this shipment cannot create a Declaration Order.

	Only a linked Sales Quote is required. Quotes without Customs lines (e.g. air-only) still get a
	draft Declaration Order; charges can be added on the order before submit, which still validates
	destination service charges.
	"""
	from frappe import _

	sq = getattr(shipment, "sales_quote", None)
	if not sq:
		frappe.throw(_("Link a Sales Quote on this shipment before creating a Declaration Order."))
	if not frappe.db.exists("Sales Quote", sq):
		frappe.throw(_("Sales Quote {0} does not exist.").format(sq))


def _freight_shipment_has_customs_charge_rows(shipment) -> bool:
	for ch in getattr(shipment, "charges", None) or []:
		if (getattr(ch, "service_type", None) or "").strip().lower() == "customs":
			return True
	return False


def _freight_shipment_has_transport_charge_rows(shipment) -> bool:
	for ch in getattr(shipment, "charges", None) or []:
		if (getattr(ch, "service_type", None) or "").strip().lower() == "transport":
			return True
	return False


def _preview_from_main_service_internal_for_target(shipment, target_service_type: str) -> bool:
	"""True when preview message should explain main-service → internal job (not legacy internal job on shipment)."""
	from frappe.utils import cint

	if cint(getattr(shipment, "is_internal_job", 0)):
		return False
	if not cint(getattr(shipment, "is_main_service", 0)):
		return False
	if target_service_type == "customs":
		return _freight_shipment_has_customs_charge_rows(shipment)
	if target_service_type == "transport":
		return _freight_shipment_has_transport_charge_rows(shipment)
	return False


def _transport_order_job_context_from_freight_shipment(shipment, shipment_doctype: str, shipment_name: str):
	"""Same pattern as Declaration Order: internal job on shipment, or main service + Transport charge rows."""
	from frappe.utils import cint

	if cint(getattr(shipment, "is_internal_job", 0)):
		return (
			1,
			getattr(shipment, "main_job_type", None),
			getattr(shipment, "main_job", None),
		)
	if cint(getattr(shipment, "is_main_service", 0)) and _freight_shipment_has_transport_charge_rows(shipment):
		return (1, shipment_doctype, shipment_name)
	return (0, None, None)


def _one_off_transport_order_job_context_from_shipment(
	shipment, shipment_doctype: str, shipment_name: str, ij, mjt, mj
):
	"""One-off Sales Quote: TO created from this freight shipment is always a satellite of that leg."""
	sqn = getattr(shipment, "sales_quote", None)
	if not sqn or not frappe.db.exists("Sales Quote", sqn):
		return ij, mjt, mj
	try:
		sq = frappe.get_cached_doc("Sales Quote", sqn)
		if getattr(sq, "quotation_type", None) != "One-off":
			return ij, mjt, mj
		if not ij:
			return 1, shipment_doctype, shipment_name
		if ij and not (mj or "").strip():
			return ij, shipment_doctype, shipment_name
	except Exception:
		return ij, mjt, mj
	return ij, mjt, mj


_TRANSPORT_ORDER_MAIN_JOB_TYPE_OPTIONS = frozenset(
	{"Air Shipment", "Sea Shipment", "Transport Job", "Declaration"}
)


def final_transport_order_job_context_from_freight_shipment(
	shipment, shipment_doctype: str, shipment_name: str
):
	"""Same as create Transport Order from freight: base context + one-off quote adjustment."""
	ij, mjt, mj = _transport_order_job_context_from_freight_shipment(
		shipment, shipment_doctype, shipment_name
	)
	return _one_off_transport_order_job_context_from_shipment(
		shipment, shipment_doctype, shipment_name, ij, mjt, mj
	)


def resolve_transport_order_freight_main_job_if_empty(
	shipment, shipment_doctype: str, shipment_name: str, ij, mjt, mj
):
	"""If internal-job context still has no Main Job, try linked Air/Sea Booking; else validate."""
	from frappe import _
	from frappe.utils import cint

	if not cint(ij):
		return ij, mjt, mj
	if (mj or "").strip() and (mjt or "").strip():
		return ij, mjt, mj

	bk_name = None
	bk_doctype = None
	if shipment_doctype == "Air Shipment":
		bk_name = (getattr(shipment, "air_booking", None) or "").strip()
		bk_doctype = "Air Booking"
	elif shipment_doctype == "Sea Shipment":
		bk_name = (getattr(shipment, "sea_booking", None) or "").strip()
		bk_doctype = "Sea Booking"

	if bk_name and bk_doctype and frappe.db.exists(bk_doctype, bk_name):
		booking = frappe.get_cached_doc(bk_doctype, bk_name)
		bjt = (getattr(booking, "main_job_type", None) or "").strip()
		bj = (getattr(booking, "main_job", None) or "").strip()
		if bjt in _TRANSPORT_ORDER_MAIN_JOB_TYPE_OPTIONS and bj:
			return ij, bjt, bj

	frappe.throw(
		_(
			"This shipment is an Internal Job but Main Job Type / Main Job is missing. "
			"Set Main Job on the shipment (or ensure the linked {0} has a valid Main Job) before creating a Transport Order."
		).format(bk_doctype or _("booking"))
	)


def _freight_shipment_has_warehousing_charge_rows(shipment) -> bool:
	for ch in getattr(shipment, "charges", None) or []:
		if (getattr(ch, "service_type", None) or "").strip().lower() == "warehousing":
			return True
	return False


def _freight_shipment_has_internal_job_detail_for_inbound_order(shipment) -> bool:
	"""True if Internal Job Details include a warehousing / Inbound Order line (even before charge rows exist)."""
	from logistics.utils.charge_service_type import effective_internal_job_detail_job_type

	for row in getattr(shipment, "internal_job_details", None) or []:
		if effective_internal_job_detail_job_type(row) == "Inbound Order":
			return True
	return False


def _inbound_order_job_context_from_freight_shipment(
	shipment, shipment_doctype: str, shipment_name: str
):
	"""Return (is_internal_job, main_job_type, main_job) for Inbound Order from Air/Sea Shipment (mirrors Declaration/TO patterns)."""
	from frappe.utils import cint

	if cint(getattr(shipment, "is_internal_job", 0)):
		return (
			1,
			getattr(shipment, "main_job_type", None),
			getattr(shipment, "main_job", None),
		)
	if cint(getattr(shipment, "is_main_service", 0)) and (
		_freight_shipment_has_warehousing_charge_rows(shipment)
		or _freight_shipment_has_internal_job_detail_for_inbound_order(shipment)
	):
		return (1, shipment_doctype, shipment_name)
	return (0, None, None)


def _one_off_inbound_order_job_context_from_shipment(
	shipment, shipment_doctype: str, shipment_name: str, ij, mjt, mj
):
	"""One-off Sales Quote: Inbound Order from this freight shipment is a satellite of that leg (same idea as Transport Order)."""
	sqn = getattr(shipment, "sales_quote", None)
	if not sqn or not frappe.db.exists("Sales Quote", sqn):
		return ij, mjt, mj
	try:
		sq = frappe.get_cached_doc("Sales Quote", sqn)
		if getattr(sq, "quotation_type", None) != "One-off":
			return ij, mjt, mj
		if not ij:
			return 1, shipment_doctype, shipment_name
		if ij and not (mj or "").strip():
			return ij, shipment_doctype, shipment_name
	except Exception:
		return ij, mjt, mj
	return ij, mjt, mj


def final_inbound_order_job_context_from_freight_shipment(
	shipment, shipment_doctype: str, shipment_name: str
):
	ij, mjt, mj = _inbound_order_job_context_from_freight_shipment(
		shipment, shipment_doctype, shipment_name
	)
	return _one_off_inbound_order_job_context_from_shipment(
		shipment, shipment_doctype, shipment_name, ij, mjt, mj
	)


def resolve_inbound_order_freight_main_job_if_empty(
	shipment, shipment_doctype: str, shipment_name: str, ij, mjt, mj
):
	"""If internal-job context still has no Main Job, try linked Air/Sea Booking; else validate."""
	from frappe import _
	from frappe.utils import cint

	if not cint(ij):
		return ij, mjt, mj
	if (mj or "").strip() and (mjt or "").strip():
		return ij, mjt, mj

	bk_name = None
	bk_doctype = None
	if shipment_doctype == "Air Shipment":
		bk_name = (getattr(shipment, "air_booking", None) or "").strip()
		bk_doctype = "Air Booking"
	elif shipment_doctype == "Sea Shipment":
		bk_name = (getattr(shipment, "sea_booking", None) or "").strip()
		bk_doctype = "Sea Booking"

	if bk_name and bk_doctype and frappe.db.exists(bk_doctype, bk_name):
		booking = frappe.get_cached_doc(bk_doctype, bk_name)
		bjt = (getattr(booking, "main_job_type", None) or "").strip()
		bj = (getattr(booking, "main_job", None) or "").strip()
		if bjt in _TRANSPORT_ORDER_MAIN_JOB_TYPE_OPTIONS and bj:
			return ij, bjt, bj

	frappe.throw(
		_(
			"This shipment is an Internal Job but Main Job Type / Main Job is missing. "
			"Set Main Job on the shipment (or ensure the linked {0} has a valid Main Job) before creating this warehousing order."
		).format(bk_doctype or _("booking"))
	)


def apply_inbound_order_freight_job_context_from_shipment(
	doc, shipment, shipment_doctype: str, shipment_name: str
):
	"""Set Job Details (internal job + main job link) on Inbound/Release Order from linked Air/Sea Shipment."""
	from frappe.utils import cint

	if doc.doctype not in ("Inbound Order", "Release Order"):
		return
	ij, mjt, mj = final_inbound_order_job_context_from_freight_shipment(
		shipment, shipment_doctype, shipment_name
	)
	ij, mjt, mj = resolve_inbound_order_freight_main_job_if_empty(
		shipment, shipment_doctype, shipment_name, ij, mjt, mj
	)
	doc.is_internal_job = cint(ij)
	if ij:
		doc.main_job_type = mjt
		doc.main_job = mj
	else:
		doc.main_job_type = None
		doc.main_job = None


def apply_warehousing_job_context_from_internal_job_source(doc, source):
	"""Copy Main Service / Internal Job hierarchy from Transport Job or Transport Order."""
	from frappe.utils import cint

	if doc.doctype not in ("Inbound Order", "Release Order"):
		return
	if cint(getattr(source, "is_internal_job", 0)):
		doc.is_internal_job = 1
		doc.main_job_type = getattr(source, "main_job_type", None)
		doc.main_job = getattr(source, "main_job", None)
	else:
		doc.is_internal_job = 0
		doc.main_job_type = None
		doc.main_job = None


def apply_inbound_order_job_context_from_transport_job(doc, job):
	"""Set Job Details on Inbound Order from linked Transport Job.

	If the job is an Internal Job, inherit its Main Job Type / Main Job. If it is a main
	Transport Job, the Inbound Order is a satellite (same pattern as Transport Order /
	Declaration Order created from a Transport Job).
	"""
	from frappe.utils import cint

	if doc.doctype != "Inbound Order":
		return
	if cint(getattr(job, "is_internal_job", 0)):
		doc.is_internal_job = 1
		doc.main_job_type = getattr(job, "main_job_type", None)
		doc.main_job = getattr(job, "main_job", None)
	else:
		doc.is_internal_job = 1
		doc.main_job_type = "Transport Job"
		doc.main_job = job.name


def ensure_main_service_on_freight_hub_for_transport_order_link(
	shipment_doctype: str, shipment_name: str
) -> None:
	"""Mark the hub or parent freight document as Main Service when a Transport Order is linked from it."""
	from frappe.utils import cint

	if shipment_doctype not in ("Air Shipment", "Sea Shipment"):
		return
	if not frappe.db.exists(shipment_doctype, shipment_name):
		return
	meta = frappe.get_meta(shipment_doctype)
	if not meta.get_field("is_main_service"):
		return

	shipment = frappe.get_doc(shipment_doctype, shipment_name)

	def _set_main_service_if_eligible(doctype: str, name: str) -> None:
		if not doctype or not name or not frappe.db.exists(doctype, name):
			return
		m = frappe.get_meta(doctype)
		if not m.get_field("is_main_service"):
			return
		if cint(frappe.db.get_value(doctype, name, "is_internal_job")):
			return
		frappe.db.set_value(doctype, name, "is_main_service", 1)

	if not cint(getattr(shipment, "is_internal_job", 0)):
		_set_main_service_if_eligible(shipment_doctype, shipment_name)
		return

	mjt = (getattr(shipment, "main_job_type", None) or "").strip()
	mj = (getattr(shipment, "main_job", None) or "").strip()
	if mjt and mj:
		_set_main_service_if_eligible(mjt, mj)


def _copy_transport_charges_from_shipment_to_transport_order(order, shipment) -> None:
	"""Append Transport Order Charges from freight shipment rows where service_type is Transport."""
	rows = [
		r
		for r in (getattr(shipment, "charges", None) or [])
		if (getattr(r, "service_type", None) or "").strip().lower() == "transport"
	]
	if not rows:
		return

	target_meta = frappe.get_meta("Transport Order Charges")
	tfields = {f.fieldname for f in target_meta.fields}
	common_fields = [
		"service_type",
		"item_code",
		"item_name",
		"charge_type",
		"charge_category",
		"item_tax_template",
		"invoice_type",
		"description",
		"sales_quote_link",
		"change_request",
		"change_request_charge",
		"is_other_service",
		"other_service_type",
		"date_started",
		"date_ended",
		"other_service_reference_no",
		"other_service_notes",
		"revenue_calculation_method",
		"quantity",
		"uom",
		"currency",
		"unit_type",
		"minimum_quantity",
		"minimum_unit_rate",
		"minimum_charge",
		"maximum_charge",
		"base_amount",
		"base_quantity",
		"estimated_revenue",
		"selling_currency",
		"cost_calculation_method",
		"cost_quantity",
		"cost_uom",
		"cost_currency",
		"unit_cost",
		"cost_unit_type",
		"cost_minimum_quantity",
		"cost_minimum_unit_rate",
		"cost_minimum_charge",
		"cost_maximum_charge",
		"cost_base_amount",
		"cost_base_quantity",
		"estimated_cost",
		"buying_currency",
		"revenue_calc_notes",
		"cost_calc_notes",
		"bill_to",
		"pay_to",
		"use_tariff_in_revenue",
		"use_tariff_in_cost",
		"revenue_tariff",
		"cost_tariff",
		"tariff",
		"selling_weight_break",
		"selling_qty_break",
		"cost_weight_break",
		"cost_qty_break",
	]
	for src in rows:
		row = order.append("charges", {})
		for fn in common_fields:
			if fn in tfields and hasattr(src, fn):
				val = getattr(src, fn, None)
				if val is not None:
					row.set(fn, val)
		rate_val = getattr(src, "rate", None)
		if rate_val is None:
			rate_val = getattr(src, "unit_rate", None)
		if rate_val is not None and "rate" in tfields:
			row.set("rate", rate_val)
		if "service_type" in tfields:
			row.set("service_type", "Transport")


@frappe.whitelist()
def get_freight_shipment_create_order_preview(
	shipment_doctype: str,
	shipment_name: str,
	target: str,
):
	"""For Create > Declaration Order / Transport Order dialog: job context + charge lines + quote parameters."""
	from frappe import _
	from frappe.utils import flt

	from logistics.utils.routing_quote_context import get_routing_parameters_for_service

	if shipment_doctype not in ("Air Shipment", "Sea Shipment"):
		frappe.throw(_("Invalid shipment type."))
	tgt = (target or "").strip().lower()
	if tgt not in ("declaration_order", "transport_order"):
		frappe.throw(_("Invalid target."))

	shipment = frappe.get_doc(shipment_doctype, shipment_name)
	shipment.check_permission("read")

	if tgt == "declaration_order":
		ij, mjt, mj = _declaration_order_job_context_from_freight_shipment(shipment, shipment_doctype, shipment_name)
		st_need = "customs"
		from_main = _preview_from_main_service_internal_for_target(shipment, "customs")
	else:
		ij, mjt, mj = final_transport_order_job_context_from_freight_shipment(
			shipment, shipment_doctype, shipment_name
		)
		ij, mjt, mj = resolve_transport_order_freight_main_job_if_empty(
			shipment, shipment_doctype, shipment_name, ij, mjt, mj
		)
		st_need = "transport"
		from_main = _preview_from_main_service_internal_for_target(shipment, "transport")

	st_label = "Customs" if st_need == "customs" else "Transport"
	routing_params = get_routing_parameters_for_service(
		shipment, getattr(shipment, "sales_quote", None), st_label
	)

	charges_out = []
	for ch in getattr(shipment, "charges", None) or []:
		st = (getattr(ch, "service_type", None) or "").strip().lower()
		if st != st_need:
			continue
		charges_out.append(
			{
				"service_type": getattr(ch, "service_type", None),
				"item_code": getattr(ch, "item_code", None),
				"item_name": getattr(ch, "item_name", None),
				"rate": flt(getattr(ch, "rate", None)) or None,
				"unit_rate": flt(getattr(ch, "unit_rate", None)) or None,
				"per_unit_rate": flt(getattr(ch, "per_unit_rate", None)) or None,
				"currency": getattr(ch, "currency", None),
				"selling_currency": getattr(ch, "selling_currency", None),
				"estimated_revenue": flt(getattr(ch, "estimated_revenue", None)) or None,
				"parameters": dict(routing_params),
			}
		)

	return {
		"is_internal_job": ij,
		"main_job_type": mjt,
		"main_job": mj,
		"from_main_service_shipment": from_main,
		"routing_parameters": routing_params,
		"charges": charges_out,
	}


def _declaration_order_job_context_from_freight_shipment(shipment, shipment_doctype: str, shipment_name: str):
	"""Return (is_internal_job, main_job_type, main_job) for a Declaration Order created from this shipment.

	- If the shipment is already an Internal Job, copy its main job link.
	- If the shipment is the quote's main service job and has Customs charge rows on the document,
	  the Declaration Order is an internal customs job with Main Job = this shipment (customs lives on the freight job).
	"""
	from frappe.utils import cint

	if cint(getattr(shipment, "is_internal_job", 0)):
		return (
			1,
			getattr(shipment, "main_job_type", None),
			getattr(shipment, "main_job", None),
		)
	if cint(getattr(shipment, "is_main_service", 0)) and _freight_shipment_has_customs_charge_rows(shipment):
		return (1, shipment_doctype, shipment_name)
	return (0, None, None)


def _copy_customs_charges_from_shipment_to_declaration_order(order, shipment) -> None:
	"""Append Declaration Order Charges from Air/Sea Shipment rows where service_type is Customs."""
	if not getattr(shipment, "charges", None):
		return
	customs_rows = [
		r
		for r in shipment.charges
		if (getattr(r, "service_type", None) or "").strip().lower() == "customs"
	]
	if not customs_rows:
		return

	meta = frappe.get_meta("Declaration Order Charges")
	charge_fields = [f.fieldname for f in meta.fields]
	common_fields = [
		"service_type",
		"item_code",
		"item_name",
		"charge_type",
		"charge_category",
		"quantity",
		"uom",
		"currency",
		"unit_type",
		"minimum_quantity",
		"minimum_unit_rate",
		"minimum_charge",
		"maximum_charge",
		"base_amount",
		"base_quantity",
		"estimated_revenue",
		"cost_calculation_method",
		"cost_quantity",
		"cost_uom",
		"cost_currency",
		"unit_cost",
		"cost_unit_type",
		"cost_minimum_quantity",
		"cost_minimum_unit_rate",
		"cost_minimum_charge",
		"cost_maximum_charge",
		"cost_base_amount",
		"cost_base_quantity",
		"estimated_cost",
		"revenue_calc_notes",
		"cost_calc_notes",
		"revenue_calculation_method",
		"rate",
		"bill_to",
		"pay_to",
		"sales_quote_link",
		"description",
		"use_tariff_in_revenue",
		"use_tariff_in_cost",
		"revenue_tariff",
		"cost_tariff",
		"selling_weight_break",
		"selling_qty_break",
		"cost_weight_break",
		"cost_qty_break",
		"is_other_service",
		"other_service_type",
		"date_started",
		"date_ended",
		"other_service_reference_no",
		"other_service_notes",
	]
	for src in customs_rows:
		row = order.append("charges", {})
		for field in common_fields:
			if field in charge_fields and hasattr(src, field):
				val = getattr(src, field, None)
				if val is not None:
					row.set(field, val)
		if "charge_basis" in charge_fields and getattr(src, "revenue_calculation_method", None):
			row.set("charge_basis", src.revenue_calculation_method)
		if "charge_type" in charge_fields and not row.get("charge_type"):
			row.set("charge_type", "Revenue")


def _existing_declaration_order_for_freight_shipment(shipment, shipment_name: str, link_field: str):
	"""Prefer Internal Job Detail row; fall back to Declaration Order link field."""
	existing_internal = get_declaration_order_job_no_from_shipment_doc(shipment)
	if existing_internal:
		return existing_internal
	return frappe.db.get_value(
		"Declaration Order",
		{link_field: shipment_name, "docstatus": ["<", 2]},
		"name",
	)


def _create_declaration_order_from_freight_shipment(
	shipment,
	*,
	shipment_doctype: str,
	shipment_name: str,
	link_field: str,
	transport_mode: str,
	vessel_field: str | None,
	internal_job_detail_idx: int | None = None,
):
	"""Shared: new Declaration Order from Air or Sea Shipment.

	Customs-style header parameters (e.g. customs broker, customs authority) come from Internal Job Detail rows when present, not from Sales Quote charge/routing parameters.
	"""
	from frappe import _
	from frappe.utils import today
	from logistics.customs.doctype.declaration_order.declaration_order import get_sales_quote_details

	_declaration_order_allowed_from_shipment(shipment)

	existing = _existing_declaration_order_for_freight_shipment(shipment, shipment_name, link_field)
	if existing:
		return {
			"declaration_order": existing,
			"already_exists": True,
			"message": _("Already linked to Declaration Order {0}.").format(existing),
		}

	sq = shipment.sales_quote
	details = get_sales_quote_details(sq) or {}

	order = frappe.new_doc("Declaration Order")
	order.set(link_field, shipment_name)
	order.sales_quote = sq
	order.order_date = today()
	order.customer = shipment.local_customer or details.get("customer")
	order.transport_mode = transport_mode

	for key in ("company", "branch", "cost_center", "profit_center", "incoterm"):
		if details.get(key) is not None:
			order.set(key, details[key])

	if getattr(shipment, "company", None):
		order.company = shipment.company
	if getattr(shipment, "branch", None):
		order.branch = shipment.branch
	if getattr(shipment, "cost_center", None):
		order.cost_center = shipment.cost_center
	if getattr(shipment, "profit_center", None):
		order.profit_center = shipment.profit_center

	order.exporter_shipper = shipment.shipper
	order.importer_consignee = shipment.consignee
	order.port_of_loading = getattr(shipment, "origin_port", None)
	order.port_of_discharge = getattr(shipment, "destination_port", None)
	if vessel_field:
		order.vessel_flight_number = getattr(shipment, vessel_field, None)
	order.etd = getattr(shipment, "etd", None)
	order.eta = getattr(shipment, "eta", None)
	copy_sales_quote_fields_to_target(shipment, order)
	detail_idx = coerce_internal_job_detail_idx(internal_job_detail_idx)
	ij_row, resolved_detail_idx = resolve_internal_job_detail_row_for_create(
		shipment, "Declaration Order", detail_idx
	)
	if ij_row:
		apply_internal_job_detail_row_to_operational_doc(order, ij_row, overwrite=True)

	ij, mjt, mj = _declaration_order_job_context_from_freight_shipment(
		shipment, shipment_doctype, shipment_name
	)
	order.is_internal_job = ij
	if ij:
		order.main_job_type = mjt
		order.main_job = mj
	else:
		order.main_job_type = None
		order.main_job = None

	_copy_customs_charges_from_shipment_to_declaration_order(order, shipment)

	order.insert(ignore_permissions=True)
	# Re-apply after insert: validate/before_save hooks must not drop Internal Job Detail header fields.
	if ij_row:
		apply_internal_job_detail_row_to_operational_doc(order, ij_row, overwrite=True)
	order.save(ignore_permissions=True)

	persist_internal_job_detail_job_link(
		shipment_doctype, shipment_name, "Declaration Order", order.name, detail_idx=resolved_detail_idx
	)

	frappe.db.commit()
	return {"declaration_order": order.name, "message": _("Declaration Order {0} created.").format(order.name)}


@frappe.whitelist()
def create_declaration_order_from_air_shipment(
	air_shipment_name: str, internal_job_detail_idx: int | None = None
):
	"""Create a Declaration Order from an Air Shipment (Customs on quote or internal job + main job)."""
	from frappe import _

	if not air_shipment_name:
		frappe.throw(_("Air Shipment is required."))
	shipment = frappe.get_doc("Air Shipment", air_shipment_name)
	return _create_declaration_order_from_freight_shipment(
		shipment,
		shipment_doctype="Air Shipment",
		shipment_name=air_shipment_name,
		link_field="air_shipment",
		transport_mode="Air",
		vessel_field="flight_number",
		internal_job_detail_idx=internal_job_detail_idx,
	)


@frappe.whitelist()
def create_declaration_order_from_sea_shipment(
	sea_shipment_name: str, internal_job_detail_idx: int | None = None
):
	"""Create a Declaration Order from a Sea Shipment (Customs on quote or internal job + main job)."""
	from frappe import _

	if not sea_shipment_name:
		frappe.throw(_("Sea Shipment is required."))
	shipment = frappe.get_doc("Sea Shipment", sea_shipment_name)
	return _create_declaration_order_from_freight_shipment(
		shipment,
		shipment_doctype="Sea Shipment",
		shipment_name=sea_shipment_name,
		link_field="sea_shipment",
		transport_mode="Sea",
		vessel_field="vessel",
		internal_job_detail_idx=internal_job_detail_idx,
	)


def _copy_shipment_packages_to_transport_order(shipment, order):
	"""Copy packages from Air Shipment to Transport Order."""
	packages = getattr(shipment, "packages", []) or []
	for pkg in packages:
		row = transport_order_package_row_from_shipment_pkg(shipment, pkg)
		if row:
			order.append("packages", row)


def _copy_sea_packages_to_transport_order(shipment, order):
	"""Copy packages from Sea Shipment to Transport Order.

	For container moves with a container number on the order, only copy lines whose package container matches.
	"""
	from frappe import _

	packages = getattr(shipment, "packages", []) or []
	target_key = None
	if getattr(order, "container_no", None):
		target_key = normalize_container_number(order.container_no)
	copied = 0
	for pkg in packages:
		if target_key:
			pc = getattr(pkg, "container", None)
			if not pc or not str(pc).strip():
				continue
			if normalize_container_number(pc) != target_key:
				continue
		row = transport_order_package_row_from_shipment_pkg(shipment, pkg)
		if row:
			order.append("packages", row)
			copied += 1
	if target_key and copied == 0:
		frappe.throw(
			_("No cargo lines on this shipment match container {0}.").format(order.container_no),
			title=_("No matching cargo"),
		)


def _copy_warehousing_charges_from_shipment_to_inbound_order(order, shipment) -> None:
	"""Append Inbound Order Charges from Air/Sea Shipment rows where service_type is Warehousing."""
	from frappe.utils import flt

	rows = [
		r
		for r in (getattr(shipment, "charges", None) or [])
		if (getattr(r, "service_type", None) or "").strip().lower() == "warehousing"
	]
	if not rows:
		return

	meta = frappe.get_meta("Inbound Order Charges")
	tfields = {f.fieldname for f in meta.fields}
	for src in rows:
		row = order.append("charges", {})
		if "item_code" in tfields and getattr(src, "item_code", None):
			row.item_code = src.item_code
		if "item_name" in tfields:
			row.item_name = getattr(src, "item_name", None) or ""
		qty = getattr(src, "quantity", None)
		if qty is None:
			qty = 1
		if "quantity" in tfields:
			row.quantity = qty
		rate = getattr(src, "rate", None)
		if rate is None:
			rate = getattr(src, "unit_rate", None)
		if "rate" in tfields and rate is not None:
			row.rate = rate
		if "currency" in tfields and getattr(src, "currency", None):
			row.currency = src.currency
		if "uom" in tfields and getattr(src, "uom", None):
			row.uom = src.uom
		if "charge_type" in tfields and getattr(src, "charge_type", None):
			row.charge_type = src.charge_type
		if "charge_category" in tfields and getattr(src, "charge_category", None):
			row.charge_category = src.charge_category
		if "total" in tfields:
			row.total = flt(qty) * flt(rate or 0)


@frappe.whitelist()
def create_inbound_order_from_air_shipment(
	air_shipment_name: str, internal_job_detail_idx: int | None = None
):
	"""Create an Inbound Order from an Air Shipment to receive goods into warehouse."""
	from frappe import _
	if not _get_default_warehouse_item():
		frappe.throw(_("No Warehouse Item found. Please create at least one Warehouse Item before creating Inbound Order from shipment."))
	shipment = frappe.get_doc("Air Shipment", air_shipment_name)
	detail_idx = coerce_internal_job_detail_idx(internal_job_detail_idx)
	ij_row = None
	resolved_detail_idx = None
	if detail_idx is not None:
		ij_row, resolved_detail_idx = resolve_internal_job_detail_row_for_create(
			shipment, "Inbound Order", detail_idx
		)
	customer = shipment.local_customer
	if not customer:
		frappe.throw(_("Air Shipment must have Local Customer to create Inbound Order."))
	order = frappe.new_doc("Inbound Order")
	order.air_shipment = air_shipment_name
	order.customer = customer
	order.contract = _get_customer_warehouse_contract(customer) or ""
	order.shipper = shipment.shipper
	order.consignee = shipment.consignee
	order.order_date = frappe.utils.today()
	order.planned_date = shipment.eta or shipment.etd
	order.due_date = shipment.eta or shipment.etd
	order.company = shipment.company or frappe.defaults.get_defaults().get("company")
	order.branch = getattr(shipment, "branch", None)
	order.cost_center = getattr(shipment, "cost_center", None)
	order.profit_center = getattr(shipment, "profit_center", None)
	order.project = getattr(shipment, "project", None)
	copy_sales_quote_fields_to_target(shipment, order)
	ij, mjt, mj = final_inbound_order_job_context_from_freight_shipment(
		shipment, "Air Shipment", air_shipment_name
	)
	ij, mjt, mj = resolve_inbound_order_freight_main_job_if_empty(
		shipment, "Air Shipment", air_shipment_name, ij, mjt, mj
	)
	order.is_internal_job = cint(ij)
	if ij:
		order.main_job_type = mjt
		order.main_job = mj
	else:
		order.main_job_type = None
		order.main_job = None
	if ij_row:
		apply_internal_job_detail_row_to_operational_doc(order, ij_row, overwrite=True)
	_copy_shipment_packages_to_inbound_order(shipment, order)
	_copy_warehousing_charges_from_shipment_to_inbound_order(order, shipment)
	order.insert(ignore_permissions=True)
	if resolved_detail_idx:
		persist_internal_job_detail_job_link(
			"Air Shipment",
			air_shipment_name,
			"Inbound Order",
			order.name,
			detail_idx=resolved_detail_idx,
		)
	ensure_main_service_on_freight_hub_for_transport_order_link("Air Shipment", air_shipment_name)
	frappe.db.commit()
	return {"inbound_order": order.name, "message": _("Inbound Order {0} created.").format(order.name)}


@frappe.whitelist()
def create_inbound_order_from_sea_shipment(
	sea_shipment_name: str, internal_job_detail_idx: int | None = None
):
	"""Create an Inbound Order from a Sea Shipment to receive goods into warehouse."""
	from frappe import _
	if not _get_default_warehouse_item():
		frappe.throw(_("No Warehouse Item found. Please create at least one Warehouse Item before creating Inbound Order from shipment."))
	shipment = frappe.get_doc("Sea Shipment", sea_shipment_name)
	detail_idx = coerce_internal_job_detail_idx(internal_job_detail_idx)
	ij_row = None
	resolved_detail_idx = None
	if detail_idx is not None:
		ij_row, resolved_detail_idx = resolve_internal_job_detail_row_for_create(
			shipment, "Inbound Order", detail_idx
		)
	customer = shipment.local_customer
	if not customer:
		frappe.throw(_("Sea Shipment must have Local Customer to create Inbound Order."))
	order = frappe.new_doc("Inbound Order")
	order.sea_shipment = sea_shipment_name
	order.customer = customer
	order.contract = _get_customer_warehouse_contract(customer) or ""
	order.shipper = shipment.shipper
	order.consignee = shipment.consignee
	order.order_date = frappe.utils.today()
	order.planned_date = shipment.eta or shipment.etd
	order.due_date = shipment.eta or shipment.etd
	order.company = shipment.company or frappe.defaults.get_defaults().get("company")
	order.branch = getattr(shipment, "branch", None)
	order.cost_center = getattr(shipment, "cost_center", None)
	order.profit_center = getattr(shipment, "profit_center", None)
	order.project = getattr(shipment, "project", None)
	copy_sales_quote_fields_to_target(shipment, order)
	ij, mjt, mj = final_inbound_order_job_context_from_freight_shipment(
		shipment, "Sea Shipment", sea_shipment_name
	)
	ij, mjt, mj = resolve_inbound_order_freight_main_job_if_empty(
		shipment, "Sea Shipment", sea_shipment_name, ij, mjt, mj
	)
	order.is_internal_job = cint(ij)
	if ij:
		order.main_job_type = mjt
		order.main_job = mj
	else:
		order.main_job_type = None
		order.main_job = None
	if ij_row:
		apply_internal_job_detail_row_to_operational_doc(order, ij_row, overwrite=True)
	_copy_sea_packages_to_inbound_order(shipment, order)
	_copy_warehousing_charges_from_shipment_to_inbound_order(order, shipment)
	order.insert(ignore_permissions=True)
	if resolved_detail_idx:
		persist_internal_job_detail_job_link(
			"Sea Shipment",
			sea_shipment_name,
			"Inbound Order",
			order.name,
			detail_idx=resolved_detail_idx,
		)
	ensure_main_service_on_freight_hub_for_transport_order_link("Sea Shipment", sea_shipment_name)
	frappe.db.commit()
	return {"inbound_order": order.name, "message": _("Inbound Order {0} created.").format(order.name)}


@frappe.whitelist()
def create_inbound_order_from_transport_job(
	transport_job_name: str, internal_job_detail_idx: int | None = None
):
	"""Create an Inbound Order from a Transport Job to receive goods into warehouse."""
	from frappe import _
	if not _get_default_warehouse_item():
		frappe.throw(_("No Warehouse Item found. Please create at least one Warehouse Item before creating Inbound Order from Transport Job."))
	job = frappe.get_doc("Transport Job", transport_job_name)
	detail_idx = coerce_internal_job_detail_idx(internal_job_detail_idx)
	ij_row = None
	resolved_detail_idx = None
	if detail_idx is not None:
		ij_row, resolved_detail_idx = resolve_internal_job_detail_row_for_create(
			job, "Inbound Order", detail_idx
		)
	customer = job.customer
	if not customer:
		frappe.throw(_("Transport Job must have Customer to create Inbound Order."))
	order = frappe.new_doc("Inbound Order")
	order.customer = customer
	order.contract = _get_customer_warehouse_contract(customer) or ""
	order.shipper = getattr(job, "shipper", None)
	order.consignee = getattr(job, "consignee", None)
	order.order_date = frappe.utils.today()
	order.planned_date = getattr(job, "scheduled_date", None) or getattr(job, "booking_date", None)
	order.due_date = getattr(job, "scheduled_date", None) or getattr(job, "booking_date", None)
	order.company = getattr(job, "company", None) or frappe.defaults.get_defaults().get("company")
	order.branch = getattr(job, "branch", None)
	order.cost_center = getattr(job, "cost_center", None)
	order.profit_center = getattr(job, "profit_center", None)
	order.project = getattr(job, "project", None)
	copy_sales_quote_fields_to_target(job, order)
	apply_inbound_order_job_context_from_transport_job(order, job)
	if ij_row:
		apply_internal_job_detail_row_to_operational_doc(order, ij_row, overwrite=True)
	_copy_transport_packages_to_inbound_order(job, order)
	# Source link and GL job must win over any quote/routing defaults applied from Internal Job Detail.
	order.transport_job = transport_job_name
	if getattr(job, "job_number", None):
		order.job_number = job.job_number
	order.insert(ignore_permissions=True)
	if resolved_detail_idx:
		persist_internal_job_detail_job_link(
			"Transport Job",
			transport_job_name,
			"Inbound Order",
			order.name,
			detail_idx=resolved_detail_idx,
		)
	frappe.db.commit()
	return {"inbound_order": order.name, "message": _("Inbound Order {0} created.").format(order.name)}


def _copy_transport_charges_from_declaration_to_transport_order(order, declaration) -> None:
	"""Append Transport Order Charges from Declaration charge rows where service_type is Transport."""
	rows = [
		r
		for r in (getattr(declaration, "charges", None) or [])
		if (getattr(r, "service_type", None) or "").strip().lower() == "transport"
	]
	if not rows:
		return

	target_meta = frappe.get_meta("Transport Order Charges")
	tfields = {f.fieldname for f in target_meta.fields}
	common_fields = [
		"service_type",
		"item_code",
		"item_name",
		"charge_type",
		"charge_category",
		"item_tax_template",
		"invoice_type",
		"description",
		"sales_quote_link",
		"change_request",
		"change_request_charge",
		"is_other_service",
		"other_service_type",
		"date_started",
		"date_ended",
		"other_service_reference_no",
		"other_service_notes",
		"revenue_calculation_method",
		"quantity",
		"uom",
		"currency",
		"unit_type",
		"minimum_quantity",
		"minimum_unit_rate",
		"minimum_charge",
		"maximum_charge",
		"base_amount",
		"base_quantity",
		"estimated_revenue",
		"selling_currency",
		"cost_calculation_method",
		"cost_quantity",
		"cost_uom",
		"cost_currency",
		"unit_cost",
		"cost_unit_type",
		"cost_minimum_quantity",
		"cost_minimum_unit_rate",
		"cost_minimum_charge",
		"cost_maximum_charge",
		"cost_base_amount",
		"cost_base_quantity",
		"estimated_cost",
		"buying_currency",
		"revenue_calc_notes",
		"cost_calc_notes",
		"bill_to",
		"pay_to",
		"use_tariff_in_revenue",
		"use_tariff_in_cost",
		"revenue_tariff",
		"cost_tariff",
		"tariff",
		"selling_weight_break",
		"selling_qty_break",
		"cost_weight_break",
		"cost_qty_break",
	]
	for src in rows:
		row = order.append("charges", {})
		for fn in common_fields:
			if fn in tfields and hasattr(src, fn):
				val = getattr(src, fn, None)
				if val is not None:
					row.set(fn, val)
		rate_val = getattr(src, "rate", None)
		if rate_val is None:
			rate_val = getattr(src, "unit_rate", None)
		if rate_val is not None and "rate" in tfields:
			row.set("rate", rate_val)


def _declaration_order_doc_for_linked_declaration(dec):
	"""Return (Declaration Order doc, name) when ``declaration.declaration_order`` is set and exists."""
	do_name = (getattr(dec, "declaration_order", None) or "").strip()
	if not do_name or not frappe.db.exists("Declaration Order", do_name):
		return None, None
	return frappe.get_doc("Declaration Order", do_name), do_name


def _resolve_transport_ij_for_declaration_to_order(dec, internal_job_detail_idx):
	"""Resolve Internal Job Detail for Transport Order: prefer linked Declaration Order (main), then Declaration."""
	from frappe.exceptions import ValidationError

	idx = coerce_internal_job_detail_idx(internal_job_detail_idx)
	do_doc, do_name = _declaration_order_doc_for_linked_declaration(dec)

	ij_row, resolved_idx = None, None
	persist_doctype, persist_name = "Declaration", dec.name

	if do_doc is not None:
		try:
			ij_row, resolved_idx = resolve_internal_job_detail_row_for_create(
				do_doc, "Transport Order", idx
			)
		except ValidationError:
			ij_row, resolved_idx = None, None
		if ij_row is not None or resolved_idx is not None:
			persist_doctype, persist_name = "Declaration Order", do_name

	if ij_row is None and resolved_idx is None:
		ij_row, resolved_idx = resolve_internal_job_detail_row_for_create(
			dec, "Transport Order", idx
		)
		persist_doctype, persist_name = "Declaration", dec.name

	return ij_row, resolved_idx, persist_doctype, persist_name, do_doc, do_name


@frappe.whitelist()
def create_transport_order_from_declaration(
	declaration_name: str, internal_job_detail_idx: int | None = None
):
	"""Create a Transport Order from a Declaration (main-service or internal-job); link on Declaration."""
	from frappe import _
	from frappe.utils import cint

	from logistics.utils.internal_job_detail_copy import (
		sync_internal_job_details_from_declaration_to_declaration_order,
	)

	if not declaration_name:
		frappe.throw(_("Declaration is required."))
	dec = frappe.get_doc("Declaration", declaration_name)
	dec.check_permission("write")
	if not getattr(dec, "sales_quote", None):
		frappe.throw(_("Link a Sales Quote on this Declaration before creating a Transport Order."))
	if (getattr(dec, "transport_order", None) or "").strip():
		frappe.throw(_("This Declaration already has a linked Transport Order."))

	# Align linked Declaration Order child rows before resolving / persisting Internal Job Detail index.
	sync_internal_job_details_from_declaration_to_declaration_order(dec)

	is_ij = cint(getattr(dec, "is_internal_job", 0))
	is_main = cint(getattr(dec, "is_main_service", 0))
	if not ((is_main and not is_ij) or is_ij):
		frappe.throw(
			_("Transport Order can only be created from a Main Service declaration or an Internal Job declaration.")
		)

	ij_row, resolved_idx, persist_doctype, persist_name, do_doc, do_name = (
		_resolve_transport_ij_for_declaration_to_order(dec, internal_job_detail_idx)
	)

	# Header defaults: when linked to a Declaration Order, use it as the main source for corridor/parties/reps.
	header_src = do_doc if do_doc is not None else dec

	order = frappe.new_doc("Transport Order")
	order.customer = getattr(header_src, "customer", None)
	order.shipper = getattr(header_src, "exporter_shipper", None)
	order.consignee = getattr(header_src, "importer_consignee", None)
	order.sales_quote = getattr(header_src, "sales_quote", None) or getattr(dec, "sales_quote", None)
	order.booking_date = frappe.utils.today()
	order.scheduled_date = (
		getattr(header_src, "eta", None) or getattr(header_src, "etd", None) or order.booking_date
	)
	order.company = getattr(header_src, "company", None) or frappe.defaults.get_defaults().get("company")
	order.branch = getattr(header_src, "branch", None)
	order.cost_center = getattr(header_src, "cost_center", None)
	order.profit_center = getattr(header_src, "profit_center", None)
	order.project = getattr(header_src, "project", None)
	if getattr(header_src, "job_number", None):
		order.job_number = header_src.job_number
	order.location_type = "UNLOCO"
	order.location_from = getattr(header_src, "port_of_loading", None)
	order.location_to = getattr(header_src, "port_of_discharge", None)
	order.transport_job_type = "Non-Container"
	copy_sales_quote_fields_to_target(header_src, order)
	# Internal job on the TO when the declaration is an internal job, or when this TO
	# is created from a Main Service declaration via an Internal Job Detail line.
	if is_ij or ij_row:
		order.is_internal_job = 1
		# main_job_type Select only allows "Declaration" (not DocType "Declaration Order"); link to this Declaration.
		order.main_job_type = "Declaration"
		order.main_job = dec.name
	if ij_row:
		apply_internal_job_detail_row_to_operational_doc(order, ij_row, overwrite=True)
	if getattr(header_src, "exporter_shipper", None) and getattr(header_src, "importer_consignee", None):
		order.append(
			"legs",
			{
				"facility_type_from": "Shipper",
				"facility_from": header_src.exporter_shipper,
				"facility_type_to": "Consignee",
				"facility_to": header_src.importer_consignee,
				"scheduled_date": order.scheduled_date,
				"transport_job_type": "Non-Container",
			},
		)
	copy_parent_dg_header(dec, order)
	_copy_transport_charges_from_declaration_to_transport_order(order, dec)
	# Internal-job Declarations only hold Customs lines when separate billings per service type is on,
	# so there are no Transport rows to copy; pull Transport lines from the Sales Quote like Air/Sea flows.
	append_transport_order_charges_from_sales_quote_if_empty(order)
	# Primary transport doc for this quote leg: required so validate_one_off_quote_not_converted allows the
	# same one-off quote already converted to the linked Declaration Order (customs + transport one chain).
	order.is_main_service = 1
	order.insert(ignore_permissions=True)
	persist_internal_job_detail_job_link(
		persist_doctype, persist_name, "Transport Order", order.name, detail_idx=resolved_idx
	)
	frappe.db.set_value("Declaration", declaration_name, "transport_order", order.name)
	frappe.db.commit()
	return {"transport_order": order.name, "message": _("Transport Order {0} created.").format(order.name)}


@frappe.whitelist()
def create_inbound_order_from_declaration(
	declaration_name: str, internal_job_detail_idx: int | None = None
):
	"""Create an Inbound Order from a Declaration when the quote allows warehousing."""
	from frappe import _

	from logistics.utils.sales_quote_service_eligibility import get_quote_module_flags

	if not declaration_name:
		frappe.throw(_("Declaration is required."))
	if not _get_default_warehouse_item():
		frappe.throw(
			_("No Warehouse Item found. Please create at least one Warehouse Item before creating an Inbound Order.")
		)
	dec = frappe.get_doc("Declaration", declaration_name)
	dec.check_permission("write")
	detail_idx = coerce_internal_job_detail_idx(internal_job_detail_idx)
	ij_row = None
	resolved_detail_idx = None
	if detail_idx is not None:
		ij_row, resolved_detail_idx = resolve_internal_job_detail_row_for_create(
			dec, "Inbound Order", detail_idx
		)
	if not getattr(dec, "sales_quote", None):
		frappe.throw(_("Link a Sales Quote on this Declaration before creating an Inbound Order."))
	flags = get_quote_module_flags(
		dec.sales_quote, source_doctype="Declaration", source_name=declaration_name
	)
	if not flags.get("allow_inbound"):
		frappe.throw(_("Inbound Order is not allowed for this Sales Quote."))

	customer = dec.customer
	if not customer:
		frappe.throw(_("Declaration must have a Customer to create an Inbound Order."))

	order = frappe.new_doc("Inbound Order")
	order.customer = customer
	order.contract = _get_customer_warehouse_contract(customer) or ""
	order.shipper = getattr(dec, "exporter_shipper", None)
	order.consignee = getattr(dec, "importer_consignee", None)
	order.order_date = frappe.utils.today()
	order.planned_date = getattr(dec, "eta", None) or getattr(dec, "etd", None)
	order.due_date = getattr(dec, "eta", None) or getattr(dec, "etd", None)
	order.company = getattr(dec, "company", None) or frappe.defaults.get_defaults().get("company")
	order.branch = getattr(dec, "branch", None)
	order.cost_center = getattr(dec, "cost_center", None)
	order.profit_center = getattr(dec, "profit_center", None)
	order.project = getattr(dec, "project", None)
	if getattr(dec, "job_number", None):
		order.job_number = dec.job_number
	default_item = _get_default_warehouse_item(customer)
	if default_item:
		order.append("items", {"item": default_item, "quantity": 1})
	if ij_row:
		apply_internal_job_detail_row_to_operational_doc(order, ij_row, overwrite=True)
	order.insert(ignore_permissions=True)
	if resolved_detail_idx:
		persist_internal_job_detail_job_link(
			"Declaration",
			declaration_name,
			"Inbound Order",
			order.name,
			detail_idx=resolved_detail_idx,
		)
	frappe.db.commit()
	return {"inbound_order": order.name, "message": _("Inbound Order {0} created.").format(order.name)}


def _get_customer_warehouse_contract(customer):
	"""Get first active Warehouse Contract for customer."""
	if not customer:
		return None
	return frappe.db.get_value("Warehouse Contract", {"customer": customer, "docstatus": 1}, "name")


def _get_default_warehouse_item(customer=None):
	"""Get a Warehouse Item for Inbound Order - from contract or first available."""
	if customer:
		contract = frappe.db.get_value("Warehouse Contract", {"customer": customer, "docstatus": 1}, "name")
		if contract:
			# Get first Warehouse Item from contract items if mapped
			items = frappe.get_all("Warehouse Contract Item", {"parent": contract}, "item_charge", limit=1)
			if items and items[0].item_charge:
				# Try to find Warehouse Item for this customer
				wi_list = frappe.get_all("Warehouse Item", {"customer": customer}, "name", limit=1)
				if wi_list:
					return wi_list[0].name
	try:
		return frappe.db.get_value("Warehouse Item", {"is_default": 1}, "name")
	except Exception:
		pass
	wi_list = frappe.get_all("Warehouse Item", limit=1, pluck="name")
	return wi_list[0] if wi_list else None


def _copy_shipment_packages_to_inbound_order(shipment, order):
	"""Copy packages from Air Shipment to Inbound Order items. Inbound Order Item requires item (Warehouse Item)."""
	# Check if warehouse_items exist first
	warehouse_items = getattr(shipment, "warehouse_items", []) or []
	if warehouse_items:
		# Use warehouse_items to populate inbound order items
		for wi in warehouse_items:
			item = getattr(wi, "item", None)
			if item:
				order.append("items", {
					"item": item,
					"quantity": getattr(wi, "quantity", 1) or 1,
					"uom": getattr(wi, "uom", None),
				})
		return
	
	# Fall back to packages with default item
	packages = getattr(shipment, "packages", []) or []
	default_item = _get_default_warehouse_item(getattr(shipment, "local_customer", None))
	for pkg in packages:
		# Commodity is a different doctype; use default Warehouse Item
		item = default_item
		if item:
			order.append("items", {
				"item": item,
				"quantity": getattr(pkg, "no_of_packs", 1) or 1,
				"uom": getattr(pkg, "uom", None),
				"weight": getattr(pkg, "weight", None),
				"volume": getattr(pkg, "volume", None),
			})
	if not order.items and default_item:
		order.append("items", {"item": default_item, "quantity": 1})


def _copy_sea_packages_to_inbound_order(shipment, order):
	"""Copy packages from Sea Shipment to Inbound Order items."""
	# Check if warehouse_items exist first
	warehouse_items = getattr(shipment, "warehouse_items", []) or []
	if warehouse_items:
		# Use warehouse_items to populate inbound order items
		for wi in warehouse_items:
			item = getattr(wi, "item", None)
			if item:
				order.append("items", {
					"item": item,
					"quantity": getattr(wi, "quantity", 1) or 1,
					"uom": getattr(wi, "uom", None),
				})
		return
	
	# Fall back to packages with default item
	packages = getattr(shipment, "packages", []) or []
	default_item = _get_default_warehouse_item(getattr(shipment, "local_customer", None))
	for pkg in packages:
		item = default_item
		if item:
			order.append("items", {
				"item": item,
				"quantity": getattr(pkg, "no_of_packs", 1) or 1,
				"uom": getattr(pkg, "uom", None),
				"weight": getattr(pkg, "weight", None),
				"volume": getattr(pkg, "volume", None),
			})
	if not order.items and default_item:
		order.append("items", {"item": default_item, "quantity": 1})


def _copy_transport_packages_to_inbound_order(job, order):
	"""Copy packages from Transport Job to Inbound Order items."""
	from frappe import _
	# Check if warehouse_items exist first
	warehouse_items = getattr(job, "warehouse_items", []) or []
	if warehouse_items:
		# Use warehouse_items to populate inbound order items
		for wi in warehouse_items:
			item = getattr(wi, "item", None)
			if item:
				order.append("items", {
					"item": item,
					"quantity": getattr(wi, "quantity", 1) or 1,
					"uom": getattr(wi, "uom", None),
				})
		return
	
	# Fall back to packages with default item
	packages = getattr(job, "packages", []) or []
	default_item = _get_default_warehouse_item(getattr(job, "customer", None))
	if not default_item:
		frappe.throw(_("No Warehouse Item found. Please create at least one Warehouse Item before creating Inbound Order from Transport Job."))
	
	for pkg in packages:
		# Use item from package if available, otherwise fall back to default_item
		pkg_item = getattr(pkg, "item", None) or default_item
		order.append("items", {
			"item": pkg_item,
			"quantity": getattr(pkg, "no_of_packs", 1) or getattr(pkg, "quantity", 1) or 1,
			"uom": getattr(pkg, "uom", None),
			"weight": getattr(pkg, "weight", None),
			"volume": getattr(pkg, "volume", None),
		})
	# Ensure at least one item exists even if no packages
	if not order.items:
		order.append("items", {"item": default_item, "quantity": 1})
