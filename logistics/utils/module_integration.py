# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Propagate data from linked freight/transport documents when integration link fields are set.
Used by Declaration Order, Declaration, Transport Order, Transport Job, Inbound Order, Release Order, Warehouse Job.
"""

import frappe


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
	elif doctype == "Release Order":
		_set_if_empty(doc, "customer", getattr(order, "customer", None))


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
def create_transport_order_from_air_shipment(air_shipment_name: str, routing_leg_idx: int = None):
	"""Create a Transport Order from an Air Shipment. Only allowed for pre-carriage or on-forwarding legs where company has control (per Logistics Settings)."""
	from frappe import _
	shipment = frappe.get_doc("Air Shipment", air_shipment_name)
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
	# Copy packages
	_copy_shipment_packages_to_transport_order(shipment, order)
	order.insert(ignore_permissions=True)
	frappe.db.commit()
	return {"transport_order": order.name, "message": _("Transport Order {0} created.").format(order.name)}


@frappe.whitelist()
def create_transport_order_from_sea_shipment(sea_shipment_name: str, routing_leg_idx: int = None):
	"""Create a Transport Order from a Sea Shipment. Only allowed for pre-carriage or on-forwarding legs where company has control (per Logistics Settings)."""
	from frappe import _
	shipment = frappe.get_doc("Sea Shipment", sea_shipment_name)
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
	_copy_sea_packages_to_transport_order(shipment, order)
	order.insert(ignore_permissions=True)
	frappe.db.commit()
	return {"transport_order": order.name, "message": _("Transport Order {0} created.").format(order.name)}


def _copy_shipment_packages_to_transport_order(shipment, order):
	"""Copy packages from Air Shipment to Transport Order."""
	from frappe.utils import flt
	packages = getattr(shipment, "packages", []) or []
	to_meta = frappe.get_meta("Transport Order Package")
	common = ["commodity", "description", "uom", "no_of_packs", "weight", "weight_uom", "volume", "volume_uom", "chargeable_weight", "chargeable_weight_uom", "length", "width", "height", "dimension_uom", "goods_description"]
	for pkg in packages:
		row = {}
		for f in common:
			if to_meta.has_field(f) and hasattr(pkg, f) and getattr(pkg, f) is not None:
				row[f] = getattr(pkg, f)
		if row:
			order.append("packages", row)


def _copy_sea_packages_to_transport_order(shipment, order):
	"""Copy packages from Sea Shipment to Transport Order."""
	packages = getattr(shipment, "packages", []) or []
	to_meta = frappe.get_meta("Transport Order Package")
	common = ["commodity", "description", "uom", "no_of_packs", "weight", "weight_uom", "volume", "volume_uom", "chargeable_weight", "chargeable_weight_uom", "length", "width", "height", "dimension_uom", "goods_description"]
	for pkg in packages:
		row = {}
		for f in common:
			if to_meta.has_field(f) and hasattr(pkg, f) and getattr(pkg, f) is not None:
				row[f] = getattr(pkg, f)
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
	packages = getattr(job, "packages", []) or []
	default_item = _get_default_warehouse_item(getattr(job, "customer", None))
	if not default_item:
		frappe.throw(_("No Warehouse Item found. Please create at least one Warehouse Item before creating Inbound Order from Transport Job."))
	
	for pkg in packages:
		order.append("items", {
			"item": default_item,
			"quantity": getattr(pkg, "no_of_packs", 1) or getattr(pkg, "quantity", 1) or 1,
			"uom": getattr(pkg, "uom", None),
			"weight": getattr(pkg, "weight", None),
			"volume": getattr(pkg, "volume", None),
		})
	# Ensure at least one item exists even if no packages
	if not order.items:
		order.append("items", {"item": default_item, "quantity": 1})
