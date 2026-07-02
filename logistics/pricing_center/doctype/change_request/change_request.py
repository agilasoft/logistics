# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today

from logistics.utils.charge_service_type import sales_quote_charge_service_types_equal
from logistics.utils.linked_service_compat import (
	CHARGE_SCOPE_LINKED,
	charge_row_linked_service_link,
	linked_service_doctype,
	linked_service_record_exists,
	set_charge_row_linked_service_link,
)


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
		or getattr(job_doc, "start_date", None)
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
	elif sales_quote_charge_service_types_equal(main_service or "", "Customs") and job_type in ("Declaration", "Declaration Order"):
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
	"""Map Change Request Charge row to Sales Quote Charge child dict (same field names).

	When the CR Charge row is tagged with a Linked Service, force ``charge_scope='Linked'`` on the
	produced Sales Quote Charge so any downstream copy (satellite ``_populate_charges_from_sales_quote_doc``
	Path-2 fallback, ``Get Charges from Quotation`` per-scope helpers, etc.) preserves linked-service
	scoping rather than defaulting to ``Main``. ``charge_scope`` is not a field on
	``Change Request Charge`` itself, so without this explicit decoration the SQ side would always
	default to ``Main``.
	"""
	out = {}
	for k, v in charge_row.as_dict().items():
		if k in _SKIP_CHARGE_COPY:
			continue
		if v is None or v == "":
			continue
		out[k] = v
	if not out.get("service_type"):
		out["service_type"] = default_service_type
	ls = (charge_row_linked_service_link(out) or "").strip()
	if ls:
		out["charge_scope"] = CHARGE_SCOPE_LINKED
		set_charge_row_linked_service_link(out, ls)
	return out


@frappe.whitelist()
def get_eligible_internal_jobs_for_change_request_job(job_type, job_name):
	"""Return Linked Service names eligible for tagging on Change Request Charge rows.

	* When ``job_type`` is a Main job, returns every Linked Service whose
	  ``parent_booking_type``/``parent_booking_name`` matches the Main.
	* When ``job_type`` is a linked-service satellite booking, returns the satellite's own
	  ``internal_job`` link so the user is steered to tag only that service.

	Used by the client-side filter on ``Change Request Charge.linked_service``.
	Response keys include legacy ``internal_jobs`` / ``default_internal_job`` aliases.
	"""
	from logistics.pricing_center.additional_charge_to_job import (
		INTERNAL_JOB_SATELLITE_JOB_TYPES,
		MAIN_JOB_TYPES_FOR_CHANGE_REQUEST,
	)

	ls_dt = linked_service_doctype()
	out: dict = {
		"linked_services": [],
		"default_linked_service": "",
		"internal_jobs": [],
		"default_internal_job": "",
	}
	if not job_type or not job_name:
		return out
	if not frappe.db.exists(job_type, job_name):
		return out

	if job_type in MAIN_JOB_TYPES_FOR_CHANGE_REQUEST:
		rows = frappe.get_all(
			ls_dt,
			filters={"parent_booking_type": job_type, "parent_booking_name": job_name},
			fields=["name", "service_type", "job_type", "job_no", "job_description"],
			order_by="creation asc",
		)
		out["linked_services"] = rows
		out["internal_jobs"] = rows
		return out

	if job_type in INTERNAL_JOB_SATELLITE_JOB_TYPES:
		sat = frappe.db.get_value(
			job_type,
			job_name,
			("main_job_type", "main_job", "internal_job"),
			as_dict=True,
		) or {}
		ls_name = (sat.get("internal_job") or "").strip()
		if ls_name and linked_service_record_exists(ls_name):
			row = frappe.db.get_value(
				ls_dt,
				ls_name,
				("name", "service_type", "job_type", "job_no", "job_description"),
				as_dict=True,
			)
			if row:
				out["linked_services"] = [row]
				out["default_linked_service"] = ls_name
				out["internal_jobs"] = [row]
				out["default_internal_job"] = ls_name
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


def _resolve_main_job_for_change_request(cr):
	"""Resolve the Main job ``(doctype, name)`` for the CR, walking IJ satellite back-links when needed.

	* CR target is a Main job → returns the CR target itself.
	* CR target is an Internal Job satellite (Transport Order / Sea Booking / Air Booking /
	  Declaration Order / Inbound Order / Release Order) → walks ``main_job_type`` / ``main_job``
	  on the satellite to find its parent Main job. The Sales Quote is always created against the
	  Main so that billing and the Change Request revenue merge stay on one canonical job.
	"""
	from logistics.pricing_center.additional_charge_to_job import (
		INTERNAL_JOB_SATELLITE_JOB_TYPES,
		MAIN_JOB_TYPES_FOR_CHANGE_REQUEST,
	)

	if cr.job_type in MAIN_JOB_TYPES_FOR_CHANGE_REQUEST:
		return cr.job_type, cr.job
	if cr.job_type in INTERNAL_JOB_SATELLITE_JOB_TYPES:
		sat = (
			frappe.db.get_value(
				cr.job_type,
				cr.job,
				("main_job_type", "main_job", "is_internal_job"),
				as_dict=True,
			)
			or {}
		)
		mt = (sat.get("main_job_type") or "").strip()
		mn = (sat.get("main_job") or "").strip()
		if mt and mn and frappe.db.exists(mt, mn):
			return mt, mn
		frappe.throw(
			_(
				"Cannot create Sales Quote: Change Request target {0} {1} is not linked to a Main job. "
				"Set main_job_type / main_job on the Internal Job satellite first."
			).format(cr.job_type, cr.job)
		)
	# Fallback: behave like the legacy path on unknown job types.
	return cr.job_type, cr.job


@frappe.whitelist()
def create_sales_quote_from_change_request(change_request_name):
	"""Create a Sales Quote from a Change Request (Additional Charge, items from charges).

	The Sales Quote always points at the parent Main job (Sea Shipment / Air Shipment / Transport
	Job / Warehouse Job / Declaration / Special Project). When the Change Request was filed
	against an Internal Job satellite booking, this function walks the satellite's back-links and
	creates the quote against the Main — revenue is merged onto the Main's CR-tagged rows, and
	from there propagated onto each satellite's mirrored rows (see
	``logistics.pricing_center.change_request_to_job.merge_sales_quote_revenue_into_change_request_job_rows``).
	"""
	cr = frappe.get_doc("Change Request", change_request_name)
	if cr.docstatus != 1:
		frappe.throw(_("Submit the Change Request before creating a Sales Quote."))
	if not cr.charges:
		frappe.throw(_("Change Request has no charge items. Add at least one charge before creating Sales Quote."))

	main_job_type, main_job_name = _resolve_main_job_for_change_request(cr)
	job_doc = frappe.get_doc(main_job_type, main_job_name)

	from logistics.pricing_center.change_request_to_job import (
		ensure_change_request_cost_rows_on_job,
		link_sales_quote_to_change_request_job_charges,
	)

	ensure_change_request_cost_rows_on_job(cr)

	sq = frappe.new_doc("Sales Quote")
	sq.additional_charge = 1
	sq.job_type = main_job_type
	sq.job = main_job_name
	# Populate main_service based on the Main job_type (not the CR's possibly-satellite target).
	job_to_service = {
		"Transport Job": "Transport",
		"Warehouse Job": "Warehousing",
		"Air Shipment": "Air",
		"Sea Shipment": "Sea",
		"Declaration": "Customs",
		"Declaration Order": "Customs",
		"Special Project": "Special Project",
	}
	sq.main_service = job_to_service.get(main_job_type, "Transport")
	# Additional-charge quotes from Change Request are always one-off (and matching naming series).
	sq.quotation_type = "One-off"
	sq.naming_series = "OOQ.#####"
	sq.change_request = cr.name
	populate_sales_quote_from_job(sq, job_doc, main_job_type)
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
	link_sales_quote_to_change_request_job_charges(cr.name, sq.name)
	return sq.name
