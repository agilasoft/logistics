# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Create Order from Request - create logistics orders from Special Project Product Requests.
"""

import frappe
from frappe import _
from frappe.utils import today, getdate


@frappe.whitelist()
def create_inbound_order_from_request(special_project_request):
	"""Create Inbound Order from product requests where fulfillment_type = Inbound."""
	return _create_warehouse_order_from_request(
		special_project_request, "Inbound Order", "Inbound Order Item", "items", "Inbound"
	)


@frappe.whitelist()
def create_release_order_from_request(special_project_request):
	"""Create Release Order from product requests where fulfillment_type = Release."""
	return _create_warehouse_order_from_request(
		special_project_request, "Release Order", "Release Order Item", "items", "Release"
	)


@frappe.whitelist()
def create_transfer_order_from_request(special_project_request):
	"""Create Transfer Order from product requests where fulfillment_type = Transfer."""
	return _create_warehouse_order_from_request(
		special_project_request, "Transfer Order", "Transfer Order Item", "items", "Transfer"
	)


def _create_warehouse_order_from_request(request_name, order_doctype, order_item_doctype, items_field, fulfillment_type):
	"""Create a warehouse order (Inbound/Release/Transfer) from product requests."""
	request_doc = frappe.get_doc("Special Project Request", request_name)
	special_project = frappe.get_doc("Special Project", request_doc.special_project)

	# Get product requests for this fulfillment type
	product_requests = [pr for pr in (request_doc.product_requests or []) if pr.fulfillment_type == fulfillment_type]
	if not product_requests:
		frappe.throw(_("No product requests with fulfillment type {0} found.").format(fulfillment_type))

	customer = special_project.customer or request_doc.get("customer")
	if not customer:
		frappe.throw(_("Customer is required. Set customer on Special Project."))

	# Get project for linking
	project = special_project.project

	# Create order
	order = frappe.new_doc(order_doctype)
	order.customer = customer
	order.order_date = today()
	order.planned_date = getdate()
	order.due_date = getdate()
	if hasattr(order, "transfer_type") and order_doctype == "Transfer Order":
		order.transfer_type = "Internal"
	if project and hasattr(order, "project"):
		order.project = project

	# Resolve Warehouse Item for each product request (warehouse orders use Warehouse Item)
	customer_code = frappe.db.get_value("Customer", customer, "custom_code") or frappe.db.get_value("Customer", customer, "customer_code") or ""

	for pr in product_requests:
		warehouse_item = _get_warehouse_item_for_product(pr.item, customer, customer_code)
		if not warehouse_item:
			frappe.throw(_("No Warehouse Item found for Item {0} and Customer {1}. Create Warehouse Item first.").format(pr.item, customer))

		item_row = order.append(items_field, {})
		item_row.item = warehouse_item
		item_row.quantity = pr.quantity or 1
		item_row.uom = pr.uom

		# Update fulfillment status
		pr.fulfillment_status = "Ordered"
		pr.reference_doctype = order_doctype

	order.insert()
	order.save()

	# Link back to request rows
	for pr in product_requests:
		pr.reference_doc = order.name
	request_doc.save()

	return {"order_type": order_doctype, "order_name": order.name}


def _get_warehouse_item_for_product(item_code, customer, customer_code=""):
	"""Find Warehouse Item for given Item and Customer. Warehouse Item code typically matches Item."""
	if not item_code or not customer:
		return None
	# Warehouse Item autoname: format:{code}-{customer_code}
	# Try exact match first
	name = f"{item_code}-{customer_code}" if customer_code else None
	if name and frappe.db.exists("Warehouse Item", name):
		return name
	# Try by code and customer
	wh_item = frappe.db.get_value(
		"Warehouse Item",
		{"code": item_code, "customer": customer},
		"name"
	)
	return wh_item


def _get_or_create_commodity_for_item(item_code):
	"""Resolve Item to Commodity. Commodity has code=name. Create if missing."""
	if not item_code:
		return None
	if frappe.db.exists("Commodity", item_code):
		return item_code
	# Create Commodity from Item
	try:
		item_doc = frappe.get_doc("Item", item_code)
		comm = frappe.new_doc("Commodity")
		comm.code = item_code
		comm.description = item_doc.item_name or item_code
		comm.insert(ignore_permissions=True)
		return item_code
	except Exception:
		return None


@frappe.whitelist()
def create_transport_order_from_request(special_project_request):
	"""Create Transport Order from product requests where fulfillment_type = Transport."""
	request_doc = frappe.get_doc("Special Project Request", special_project_request)
	special_project = frappe.get_doc("Special Project", request_doc.special_project)

	product_requests = [pr for pr in (request_doc.product_requests or []) if pr.fulfillment_type == "Transport"]
	if not product_requests:
		frappe.throw(_("No product requests with fulfillment type Transport found."))

	customer = special_project.customer
	if not customer:
		frappe.throw(_("Customer is required on Special Project."))

	project = special_project.project

	order = frappe.new_doc("Transport Order")
	order.customer = customer
	order.booking_date = today()
	order.scheduled_date = getdate()
	if project and hasattr(order, "project"):
		order.project = project

	for pr in product_requests:
		pkg = order.append("packages", {})
		pkg.commodity = _get_or_create_commodity_for_item(pr.item)
		pkg.quantity = pr.quantity or 1
		pkg.uom = pr.uom
		pkg.description = pr.description
		pr.fulfillment_status = "Ordered"
		pr.reference_doctype = "Transport Order"

	order.insert()
	order.save()

	for pr in product_requests:
		pr.reference_doc = order.name
	request_doc.save()

	return {"order_type": "Transport Order", "order_name": order.name}


@frappe.whitelist()
def create_air_booking_from_request(special_project_request, origin_port=None, destination_port=None):
	"""Create Air Booking from product requests where fulfillment_type = Air Freight."""
	request_doc = frappe.get_doc("Special Project Request", special_project_request)
	special_project = frappe.get_doc("Special Project", request_doc.special_project)

	product_requests = [pr for pr in (request_doc.product_requests or []) if pr.fulfillment_type == "Air Freight"]
	if not product_requests:
		frappe.throw(_("No product requests with fulfillment type Air Freight found."))

	customer = special_project.customer
	if not customer:
		frappe.throw(_("Customer is required on Special Project."))

	project = special_project.project

	# Get defaults from Air Freight Settings (keyed by company)
	default_company = frappe.defaults.get_defaults().get("company")
	settings = frappe.db.get_value(
		"Air Freight Settings",
		default_company,
		["company", "default_branch", "default_cost_center", "default_profit_center",
		 "default_origin_airport", "default_destination_airport", "default_direction"],
		as_dict=True,
	) or {}
	company = settings.get("company") or default_company
	if not company:
		frappe.throw(_("Company is required. Set default company or Air Freight Settings."))

	origin = origin_port or settings.get("default_origin_airport")
	dest = destination_port or settings.get("default_destination_airport")
	if not origin or not dest:
		frappe.throw(_("Origin Airport and Destination Airport are required. Set them in Air Freight Settings or pass as parameters."))

	booking = frappe.new_doc("Air Booking")
	booking.booking_date = today()
	booking.local_customer = customer
	booking.origin_port = origin
	booking.destination_port = dest
	booking.direction = settings.get("default_direction") or "Export"
	booking.company = company
	booking.branch = settings.get("default_branch")
	booking.cost_center = settings.get("default_cost_center")
	booking.profit_center = settings.get("default_profit_center")
	if project and hasattr(booking, "project"):
		booking.project = project

	for pr in product_requests:
		pkg = booking.append("packages", {})
		pkg.commodity = _get_or_create_commodity_for_item(pr.item)
		pkg.no_of_packs = pr.quantity or 1
		pkg.uom = pr.uom
		pkg.weight = pr.get("weight")
		pkg.volume = pr.get("volume")
		pkg.goods_description = pr.description or (frappe.db.get_value("Item", pr.item, "item_name") if pr.item else None)
		pr.fulfillment_status = "Ordered"
		pr.reference_doctype = "Air Booking"

	booking.insert()
	booking.save()

	for pr in product_requests:
		pr.reference_doc = booking.name
	request_doc.save()

	return {"order_type": "Air Booking", "order_name": booking.name}


@frappe.whitelist()
def create_sea_booking_from_request(special_project_request, origin_port=None, destination_port=None, shipper=None, consignee=None):
	"""Create Sea Booking from product requests where fulfillment_type = Sea Freight."""
	request_doc = frappe.get_doc("Special Project Request", special_project_request)
	special_project = frappe.get_doc("Special Project", request_doc.special_project)

	product_requests = [pr for pr in (request_doc.product_requests or []) if pr.fulfillment_type == "Sea Freight"]
	if not product_requests:
		frappe.throw(_("No product requests with fulfillment type Sea Freight found."))

	customer = special_project.customer
	if not customer:
		frappe.throw(_("Customer is required on Special Project."))

	project = special_project.project

	# Sea Freight Settings is a single doc
	try:
		settings_doc = frappe.get_single("Sea Freight Settings")
		settings = {
			"company": settings_doc.default_company,
			"default_branch": settings_doc.default_branch,
			"default_cost_center": settings_doc.default_cost_center,
			"default_profit_center": settings_doc.default_profit_center,
			"default_origin_port": settings_doc.default_origin_port,
			"default_destination_port": settings_doc.default_destination_port,
			"default_direction": getattr(settings_doc, "default_direction", None),
			"default_transport_mode": getattr(settings_doc, "default_transport_mode", None),
		}
	except Exception:
		settings = {}
	company = settings.get("company") or frappe.defaults.get_defaults().get("company")
	if not company:
		frappe.throw(_("Company is required. Set default company or Sea Freight Settings."))

	origin = origin_port or settings.get("default_origin_port")
	dest = destination_port or settings.get("default_destination_port")
	if not origin or not dest:
		frappe.throw(_("Origin Port and Destination Port are required. Set them in Sea Freight Settings or pass as parameters."))
	
	# Shipper and Consignee are required for Sea Booking
	if not shipper:
		frappe.throw(_("Shipper is required to create Sea Booking. Please provide shipper parameter."))
	if not consignee:
		frappe.throw(_("Consignee is required to create Sea Booking. Please provide consignee parameter."))

	booking = frappe.new_doc("Sea Booking")
	booking.booking_date = today()
	booking.local_customer = customer
	booking.origin_port = origin
	booking.destination_port = dest
	booking.direction = settings.get("default_direction") or "Export"
	booking.transport_mode = settings.get("default_transport_mode") or "LCL"
	booking.shipper = shipper
	booking.consignee = consignee
	booking.company = company
	booking.branch = settings.get("default_branch")
	booking.cost_center = settings.get("default_cost_center")
	booking.profit_center = settings.get("default_profit_center")
	if project and hasattr(booking, "project"):
		booking.project = project

	for pr in product_requests:
		pkg = booking.append("packages", {})
		pkg.commodity = _get_or_create_commodity_for_item(pr.item)
		pkg.no_of_packs = pr.quantity or 1
		pkg.uom = pr.uom
		pkg.weight = pr.get("weight")
		pkg.volume = pr.get("volume")
		pkg.goods_description = pr.description or (frappe.db.get_value("Item", pr.item, "item_name") if pr.item else None)
		pr.fulfillment_status = "Ordered"
		pr.reference_doctype = "Sea Booking"

	booking.insert()
	booking.save()

	for pr in product_requests:
		pr.reference_doc = booking.name
	request_doc.save()

	return {"order_type": "Sea Booking", "order_name": booking.name}


@frappe.whitelist()
def link_existing_order_to_request(special_project_request, reference_doctype, reference_doc):
	"""Link an existing order/booking to the request and set project."""
	request_doc = frappe.get_doc("Special Project Request", special_project_request)
	special_project = frappe.get_doc("Special Project", request_doc.special_project)
	project = special_project.project

	if not project:
		frappe.throw(_("Special Project has no linked ERPNext Project. Create Project first."))

	doc = frappe.get_doc(reference_doctype, reference_doc)
	if hasattr(doc, "project"):
		doc.project = project
		doc.save()
		frappe.db.commit()
		return {"linked": True, "project": project}
	return {"linked": False, "message": _("Document has no project field.")}
