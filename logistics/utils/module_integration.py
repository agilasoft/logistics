# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Propagate data from linked freight/transport documents when integration link fields are set.
Used by Declaration Order, Declaration, Transport Order, Transport Job, Inbound Order, Release Order, Warehouse Job.
"""

import frappe

from logistics.utils.dg_fields import copy_parent_dg_header, transport_order_package_row_from_shipment_pkg
from logistics.utils.internal_job_detail_copy import (
	get_declaration_order_job_no_from_shipment_doc,
	persist_internal_job_detail_job_link,
)
from logistics.utils.internal_job_from_source import (
	apply_internal_job_detail_row_to_operational_doc,
	coerce_internal_job_detail_idx,
	resolve_internal_job_detail_row_for_create,
)


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
	elif doctype == "Release Order":
		_set_if_empty(doc, "shipper", getattr(shipment, "shipper", None))
		_set_if_empty(doc, "consignee", getattr(shipment, "consignee", None))
		_set_if_empty(doc, "customer", getattr(shipment, "local_customer", None))
	elif doctype == "Warehouse Job":
		_set_if_empty(doc, "shipper", getattr(shipment, "shipper", None))
		_set_if_empty(doc, "consignee", getattr(shipment, "consignee", None))
		_set_if_empty(doc, "customer", getattr(shipment, "local_customer", None))

	if doctype in ("Transport Order", "Transport Job", "Declaration", "Declaration Order"):
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
	elif doctype == "Release Order":
		_set_if_empty(doc, "shipper", getattr(shipment, "shipper", None))
		_set_if_empty(doc, "consignee", getattr(shipment, "consignee", None))
		_set_if_empty(doc, "customer", getattr(shipment, "local_customer", None))
	elif doctype == "Warehouse Job":
		_set_if_empty(doc, "shipper", getattr(shipment, "shipper", None))
		_set_if_empty(doc, "consignee", getattr(shipment, "consignee", None))
		_set_if_empty(doc, "customer", getattr(shipment, "local_customer", None))

	if doctype in ("Transport Order", "Transport Job", "Declaration", "Declaration Order"):
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
	"""Copy Sales Quote link from source (shipment/booking/order/job) to a new target doc."""
	sq = _resolve_sales_quote_from_doc(source_doc)
	if sq and hasattr(target_doc, "sales_quote"):
		target_doc.sales_quote = sq


def propagate_sales_quote_from_source_if_empty(source_doc, target_doc):
	"""When user links air/sea shipment or similar, fill sales_quote if still empty."""
	sq = _resolve_sales_quote_from_doc(source_doc)
	if sq and hasattr(target_doc, "sales_quote"):
		_set_if_empty(target_doc, "sales_quote", sq)


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
	ij, mjt, mj = _transport_order_job_context_from_freight_shipment(shipment, "Air Shipment", air_shipment_name)
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
	order.insert(ignore_permissions=True)
	persist_internal_job_detail_job_link(
		"Air Shipment", air_shipment_name, "Transport Order", order.name, detail_idx=resolved_detail_idx
	)
	frappe.db.commit()
	return {"transport_order": order.name, "message": _("Transport Order {0} created.").format(order.name)}


@frappe.whitelist()
def create_transport_order_from_sea_shipment(
	sea_shipment_name: str, routing_leg_idx: int = None, internal_job_detail_idx: int = None
):
	"""Create a Transport Order from a Sea Shipment. Only allowed for pre-carriage or on-forwarding legs where company has control (per Logistics Settings).

	Routing-style header fields come from Internal Job Detail rows when present, not from Sales Quote routing parameters.
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
	order.transport_job_type = "Container" if shipment.container_type else "Non-Container"
	order.container_type = getattr(shipment, "container_type", None)
	# Get container number from containers child table if available
	if order.transport_job_type == "Container":
		containers = getattr(shipment, "containers", []) or []
		if containers:
			container_no = getattr(containers[0], "container_no", None)
			if container_no and container_no.strip():
				order.container_no = container_no.strip()
		if not order.container_no:
			packages = getattr(shipment, "packages", []) or []
			for pkg in packages:
				container_field = getattr(pkg, "container", None)
				if container_field and container_field.strip():
					order.container_no = container_field.strip()
					break
	order.company = shipment.company or frappe.defaults.get_defaults().get("company")
	order.branch = getattr(shipment, "branch", None)
	order.cost_center = getattr(shipment, "cost_center", None)
	order.profit_center = getattr(shipment, "profit_center", None)
	order.project = getattr(shipment, "project", None)
	copy_sales_quote_fields_to_target(shipment, order)
	ij, mjt, mj = _transport_order_job_context_from_freight_shipment(shipment, "Sea Shipment", sea_shipment_name)
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
			"transport_job_type": "Container" if shipment.container_type else "Non-Container",
		}
		if getattr(shipment, "shipper_address", None):
			leg["pick_address"] = shipment.shipper_address
		if getattr(shipment, "consignee_address", None):
			leg["drop_address"] = shipment.consignee_address
		order.append("legs", leg)
	copy_parent_dg_header(shipment, order)
	_copy_sea_packages_to_transport_order(shipment, order)
	_copy_transport_charges_from_shipment_to_transport_order(order, shipment)
	order.insert(ignore_permissions=True)
	persist_internal_job_detail_job_link(
		"Sea Shipment", sea_shipment_name, "Transport Order", order.name, detail_idx=resolved_detail_idx
	)
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
		if rate_val is not None and "unit_rate" in tfields:
			row.set("unit_rate", rate_val)


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
		ij, mjt, mj = _transport_order_job_context_from_freight_shipment(shipment, shipment_doctype, shipment_name)
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
	"""Copy packages from Sea Shipment to Transport Order."""
	packages = getattr(shipment, "packages", []) or []
	for pkg in packages:
		row = transport_order_package_row_from_shipment_pkg(shipment, pkg)
		if row:
			order.append("packages", row)


@frappe.whitelist()
def create_inbound_order_from_air_shipment(air_shipment_name: str):
	"""Create an Inbound Order from an Air Shipment to receive goods into warehouse."""
	from frappe import _
	if not _get_default_warehouse_item():
		frappe.throw(_("No Warehouse Item found. Please create at least one Warehouse Item before creating Inbound Order from shipment."))
	shipment = frappe.get_doc("Air Shipment", air_shipment_name)
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
	_copy_shipment_packages_to_inbound_order(shipment, order)
	order.insert(ignore_permissions=True)
	frappe.db.commit()
	return {"inbound_order": order.name, "message": _("Inbound Order {0} created.").format(order.name)}


@frappe.whitelist()
def create_inbound_order_from_sea_shipment(sea_shipment_name: str):
	"""Create an Inbound Order from a Sea Shipment to receive goods into warehouse."""
	from frappe import _
	if not _get_default_warehouse_item():
		frappe.throw(_("No Warehouse Item found. Please create at least one Warehouse Item before creating Inbound Order from shipment."))
	shipment = frappe.get_doc("Sea Shipment", sea_shipment_name)
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
	_copy_sea_packages_to_inbound_order(shipment, order)
	order.insert(ignore_permissions=True)
	frappe.db.commit()
	return {"inbound_order": order.name, "message": _("Inbound Order {0} created.").format(order.name)}


@frappe.whitelist()
def create_inbound_order_from_transport_job(transport_job_name: str):
	"""Create an Inbound Order from a Transport Job to receive goods into warehouse."""
	from frappe import _
	if not _get_default_warehouse_item():
		frappe.throw(_("No Warehouse Item found. Please create at least one Warehouse Item before creating Inbound Order from Transport Job."))
	job = frappe.get_doc("Transport Job", transport_job_name)
	customer = job.customer
	if not customer:
		frappe.throw(_("Transport Job must have Customer to create Inbound Order."))
	order = frappe.new_doc("Inbound Order")
	order.transport_job = transport_job_name
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
	_copy_transport_packages_to_inbound_order(job, order)
	order.insert(ignore_permissions=True)
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
	try:
		return frappe.db.get_single_value("Warehouse Settings", "default_inbound_item")
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
