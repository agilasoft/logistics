# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today


_SKIP_CHARGE_COPY = frozenset(
	{
		"name",
		"owner",
		"creation",
		"modified",
		"modified_by",
		"docstatus",
		"parent",
		"parentfield",
		"parenttype",
		"idx",
	}
)


class ChangeRequest(Document):
	def on_submit(self):
		from logistics.pricing_center.change_request_to_job import apply_change_request_charges_to_job

		apply_change_request_charges_to_job(self)
		frappe.db.set_value("Change Request", self.name, "status", "Submitted", update_modified=False)

	def on_cancel(self):
		from logistics.pricing_center.change_request_to_job import remove_change_request_charges_from_job

		remove_change_request_charges_from_job(self)
		frappe.db.set_value("Change Request", self.name, "status", "Draft", update_modified=False)


def _nonempty_scalar(val):
	if val is None:
		return False
	if isinstance(val, str) and str(val).strip() == "":
		return False
	return True


def _set_sq_from_job(sales_quote, job_doc, job_fieldnames):
	"""Copy named fields from job to Sales Quote when the job has a value."""
	for sq_field, job_field in job_fieldnames:
		if not hasattr(sales_quote, sq_field):
			continue
		val = getattr(job_doc, job_field, None)
		if _nonempty_scalar(val):
			setattr(sales_quote, sq_field, val)


def _merge_transport_order_into_sales_quote_for_transport_job(sales_quote, transport_job_doc):
	"""Fill gaps on the quote from the linked Transport Order (locations, parties, reps)."""
	to_ref = getattr(transport_job_doc, "transport_order", None)
	if not to_ref or not frappe.db.exists("Transport Order", to_ref):
		return
	try:
		tdoc = frappe.get_doc("Transport Order", to_ref)
	except frappe.DoesNotExistError:
		return
	merge_pairs = [
		("company", "company"),
		("branch", "branch"),
		("cost_center", "cost_center"),
		("profit_center", "profit_center"),
		("shipper", "shipper"),
		("consignee", "consignee"),
		("incoterm", "incoterm"),
		("sales_rep", "sales_rep"),
		("operations_rep", "operations_rep"),
		("customer_service_rep", "customer_service_rep"),
		("location_type", "location_type"),
		("location_from", "location_from"),
		("location_to", "location_to"),
		("transport_template", "transport_template"),
		("vehicle_type", "vehicle_type"),
		("container_type", "container_type"),
		("load_type", "load_type"),
		("transport_mode", "transport_mode"),
	]
	for sq_f, t_f in merge_pairs:
		if getattr(sales_quote, sq_f, None) not in (None, ""):
			continue
		v = getattr(tdoc, t_f, None)
		if _nonempty_scalar(v):
			setattr(sales_quote, sq_f, v)


def _append_routing_legs_from_air_sea_shipment(sales_quote, shipment_doc, job_type_label):
	"""Mirror shipment multimodal routing onto Sales Quote routing legs."""
	legs = getattr(shipment_doc, "routing_legs", None) or []
	if not legs:
		return
	default_mode = "Air" if job_type_label == "Air Shipment" else "Sea"
	for idx, leg in enumerate(legs):
		origin = getattr(leg, "load_port", None)
		dest = getattr(leg, "discharge_port", None)
		mode = getattr(leg, "mode", None) or default_mode
		sales_quote.append(
			"routing_legs",
			{
				"mode": mode,
				"type": getattr(leg, "type", None) or "Main",
				# Multimodal rule: at least one Main Job leg — mark the first copied leg
				"is_main_job": 1 if idx == 0 else 0,
				"status": getattr(leg, "status", None) or "Planned",
				"origin": origin,
				"destination": dest,
				"etd": getattr(leg, "etd", None),
				"eta": getattr(leg, "eta", None),
				"job_type": job_type_label,
				"job_no": shipment_doc.name,
				"notes": getattr(leg, "notes", None),
			},
		)


def populate_sales_quote_from_job(sales_quote, job_doc, job_type):
	"""Copy accounting, parties, operational parameters, and routing from the linked job into an additional-charge Sales Quote."""
	customer = getattr(job_doc, "customer", None) or getattr(job_doc, "local_customer", None)
	if customer:
		sales_quote.customer = customer

	_set_sq_from_job(
		sales_quote,
		job_doc,
		[
			("company", "company"),
			("branch", "branch"),
			("cost_center", "cost_center"),
			("profit_center", "profit_center"),
			("shipper", "shipper"),
			("consignee", "consignee"),
			("incoterm", "incoterm"),
			("sales_rep", "sales_rep"),
			("operations_rep", "operations_rep"),
			("customer_service_rep", "customer_service_rep"),
		],
	)

	if job_type in ("Declaration", "Declaration Order"):
		exp = getattr(job_doc, "exporter_shipper", None)
		imp = getattr(job_doc, "importer_consignee", None)
		if _nonempty_scalar(exp):
			sales_quote.shipper = exp
		if _nonempty_scalar(imp):
			sales_quote.consignee = imp

	ref_date = (
		getattr(job_doc, "booking_date", None)
		or getattr(job_doc, "declaration_date", None)
		or getattr(job_doc, "job_open_date", None)
		or today()
	)
	if ref_date:
		sales_quote.date = ref_date

	for lvl_field in ("service_level", "logistics_service_level"):
		slv = getattr(job_doc, lvl_field, None)
		if _nonempty_scalar(slv):
			sales_quote.service_code = slv
			break

	main_service = getattr(sales_quote, "main_service", None)

	if main_service == "Air":
		_set_sq_from_job(
			sales_quote,
			job_doc,
			[
				("origin_port", "origin_port"),
				("destination_port", "destination_port"),
				("direction", "direction"),
				("airline", "airline"),
				("freight_agent", "freight_agent"),
				("load_type", "load_type"),
				("transport_mode", "transport_mode"),
			],
		)
	elif main_service == "Sea":
		_set_sq_from_job(
			sales_quote,
			job_doc,
			[
				("origin_port", "origin_port"),
				("destination_port", "destination_port"),
				("direction", "direction"),
				("shipping_line", "shipping_line"),
				("load_type", "load_type"),
				("transport_mode", "transport_mode"),
			],
		)
		fa = getattr(job_doc, "freight_agent", None)
		if _nonempty_scalar(fa):
			sales_quote.freight_agent_sea = fa
	elif main_service == "Transport":
		_set_sq_from_job(
			sales_quote,
			job_doc,
			[
				("load_type", "load_type"),
				("transport_mode", "transport_mode"),
				("vehicle_type", "vehicle_type"),
				("container_type", "container_type"),
				("transport_template", "transport_template"),
			],
		)
		_merge_transport_order_into_sales_quote_for_transport_job(sales_quote, job_doc)
	elif main_service == "Customs" and job_type in ("Declaration", "Declaration Order"):
		_set_sq_from_job(
			sales_quote,
			job_doc,
			[
				("origin_port", "port_of_loading"),
				("destination_port", "port_of_discharge"),
				("transport_mode", "transport_mode"),
			],
		)


	if job_type in ("Air Shipment", "Sea Shipment"):
		_append_routing_legs_from_air_sea_shipment(sales_quote, job_doc, job_type)


def _charge_row_as_sales_quote_dict(charge_row, default_service_type):
	"""Map Change Request Charge row to Sales Quote Charge child dict (same field names)."""
	out = {}
	for k, v in charge_row.as_dict().items():
		if k in _SKIP_CHARGE_COPY:
			continue
		if v is None or v == "":
			continue
		out[k] = v
	if not out.get("service_type"):
		out["service_type"] = default_service_type
	return out


@frappe.whitelist()
def create_change_request(job_type, job_name):
	"""Create a new Change Request linked to the given job. Returns the new doc name."""
	if not job_type or not job_name:
		frappe.throw(_("Job Type and Job are required"))
	# Validate job exists
	if not frappe.db.exists(job_type, job_name):
		frappe.throw(_("Job {0} does not exist").format(job_name))
	cr = frappe.new_doc("Change Request")
	cr.job_type = job_type
	cr.job = job_name
	cr.status = "Draft"
	cr.insert(ignore_permissions=True)
	return cr.name


@frappe.whitelist()
def create_sales_quote_from_change_request(change_request_name):
	"""Create a Sales Quote from a Change Request (Additional Charge, job reference, items from charges)."""
	cr = frappe.get_doc("Change Request", change_request_name)
	if cr.docstatus != 1:
		frappe.throw(_("Submit the Change Request before creating a Sales Quote."))
	if not cr.charges:
		frappe.throw(_("Change Request has no charge items. Add at least one charge before creating Sales Quote."))
	# Create Sales Quote
	sq = frappe.new_doc("Sales Quote")
	sq.additional_charge = 1
	sq.job_type = cr.job_type
	sq.job = cr.job
	job_doc = frappe.get_doc(cr.job_type, cr.job)
	# Populate main_service based on job_type
	job_to_service = {
		"Transport Job": "Transport",
		"Warehouse Job": "Warehousing",
		"Air Shipment": "Air",
		"Sea Shipment": "Sea",
		"Declaration": "Customs",
		"Declaration Order": "Customs",
	}
	sq.main_service = job_to_service.get(cr.job_type, "Transport")
	# Additional-charge quotes from Change Request are always one-off (and matching naming series).
	sq.quotation_type = "One-off"
	sq.naming_series = "OOQ.#####"
	sq.change_request = cr.name
	populate_sales_quote_from_job(sq, job_doc, cr.job_type)
	for row in cr.charges:
		row_dict = _charge_row_as_sales_quote_dict(row, sq.main_service)
		row_dict["change_request_charge"] = row.name
		sq.append("charges", row_dict)
	sq.flags.ignore_mandatory = True
	sq.insert(ignore_permissions=True)
	# Link back (submitted doc: avoid save(); status/sales_quote are not allow_on_submit)
	frappe.db.set_value(
		"Change Request",
		cr.name,
		{"sales_quote": sq.name, "status": "Sales Quote Created"},
		update_modified=False,
	)
	return sq.name
