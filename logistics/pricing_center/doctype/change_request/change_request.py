# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

from __future__ import unicode_literals

import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import today

from logistics.utils.charge_service_type import sales_quote_charge_service_types_equal
from logistics.utils.linked_service_compat import (
	CHARGE_SCOPE_LINKED,
	CHARGE_SCOPE_MAIN,
	charge_row_linked_service_link,
	linked_service_doctype,
	linked_service_record_exists,
	linked_service_rows,
	normalize_charge_scope,
	set_charge_row_linked_service_link,
)

_LINKED_SERVICE_VIEW_FIELDS = (
	"linked_service",
	"service_type",
	"job_type",
	"job_no",
	"job_description",
	"air_house_type",
	"airline",
	"freight_agent",
	"sea_house_type",
	"freight_agent_sea",
	"shipping_line",
	"transport_mode",
	"load_type",
	"direction",
	"origin_port",
	"destination_port",
	"transport_template",
	"vehicle_type",
	"container_type",
	"container_no",
	"location_type",
	"location_from",
	"location_to",
	"pick_mode",
	"drop_mode",
	"customs_authority",
	"declaration_type",
	"customs_broker",
	"customs_charge_category",
	"planned_cost",
	"actual_cost",
	"planned_revenue",
	"actual_revenue",
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
	def __setup__(self):
		self._stage_linked_services_from_form()

	@property
	def linked_services(self):
		"""Live view of Linked Service documents owned by this Change Request.

		Prefer ``__dict__`` when present so Frappe's computed Table wrapper +
		``LazyDocument.append`` (full-page printview) does not RecursionError.
		"""
		if self.flags.get("_linked_services_from_form"):
			return self.__dict__.get("linked_services") or []
		if "linked_services" in self.__dict__:
			rows = self.__dict__["linked_services"]
			if rows and any(getattr(r, "__islocal", None) for r in rows):
				self.flags._linked_services_from_form = True
			return rows
		if self.flags.get("_linked_services_view_cached"):
			return []
		value = self._build_linked_services_view()
		self.__dict__["linked_services"] = value
		self.flags._linked_services_view_cached = True
		return value

	def _build_linked_services_view(self):
		if not getattr(self, "name", None) or getattr(self, "__islocal", False):
			return []
		from logistics.logistics.doctype.linked_service.linked_service import (
			get_linked_services_for_change_request,
		)

		rows = []
		for ls in get_linked_services_for_change_request(self.name):
			row = {"linked_service": ls.name}
			for fn in _LINKED_SERVICE_VIEW_FIELDS:
				if fn == "linked_service":
					continue
				if hasattr(ls, fn):
					row[fn] = getattr(ls, fn, None)
			rows.append(row)
		return rows

	def _drop_virtual_linked_services_rows(self):
		self.flags._linked_services_from_form = False
		self.flags._linked_services_view_cached = False
		if "linked_services" in self.__dict__:
			del self.__dict__["linked_services"]

	def _stage_linked_services_from_form(self):
		if "linked_services" not in self.__dict__:
			return
		if self.__dict__.get("linked_services") is None:
			self.__dict__["linked_services"] = []
		if not self.flags.get("_linked_services_view_cached"):
			self.flags._linked_services_from_form = True

	def _honour_linked_services_form_rows(self):
		self._stage_linked_services_from_form()

	def validate(self):
		self._honour_linked_services_form_rows()
		self.validate_job_context_immutable()
		self.validate_linked_service_charge_tagging()
		if not (getattr(self, "reason", None) or "").strip():
			frappe.throw(_("Reason is required for a Change Request."), title=_("Reason Required"))
		try:
			from logistics.pricing_center.change_request_field_apply import refresh_change_request_summary

			refresh_change_request_summary(self)
		except Exception:
			frappe.log_error(frappe.get_traceback(), "Change Request summary refresh")

	def validate_job_context_immutable(self):
		"""Job Type / Job are locked after the CR is linked to a job (create-from-job path)."""
		if self.is_new():
			return
		before = self.get_doc_before_save()
		if not before:
			return
		prev_type = (getattr(before, "job_type", None) or "").strip()
		prev_job = (getattr(before, "job", None) or "").strip()
		if not prev_job:
			return
		cur_type = (getattr(self, "job_type", None) or "").strip()
		cur_job = (getattr(self, "job", None) or "").strip()
		if prev_type != cur_type or prev_job != cur_job:
			frappe.throw(
				_("Job Type and Job cannot be changed after the Change Request is created. "
				  "Cancel this request and create a new one from the correct job."),
				title=_("Job Locked"),
			)

	def validate_linked_service_charge_tagging(self):
		"""Validate per-charge Linked Service tagging on Change Request charges."""
		from logistics.utils.linked_service_compat import (
			CHARGE_SCOPE_LINKED,
			CHARGE_SCOPE_MAIN,
			normalize_charge_scope,
			set_charge_row_linked_service_link,
		)

		allowed_ls: set[str] = set()
		for ls_row in linked_service_rows(self):
			ls_name = charge_row_linked_service_link(ls_row)
			if ls_name:
				allowed_ls.add(ls_name)

		for row in getattr(self, "charges", None) or []:
			scope = normalize_charge_scope(getattr(row, "charge_scope", None))
			ls_link = charge_row_linked_service_link(row)
			if not getattr(row, "charge_scope", None) and ls_link:
				row.charge_scope = CHARGE_SCOPE_LINKED
				scope = CHARGE_SCOPE_LINKED
			if scope != CHARGE_SCOPE_LINKED:
				if ls_link:
					set_charge_row_linked_service_link(row, None)
				row.charge_scope = CHARGE_SCOPE_MAIN
				continue
			row.charge_scope = CHARGE_SCOPE_LINKED
			if not ls_link:
				frappe.throw(
					_("Charges row {0}: select a Linked Service when Scope is \"Linked\".").format(
						getattr(row, "idx", "") or "?",
					),
					title=_("Linked Service Required"),
				)
			if allowed_ls and ls_link not in allowed_ls:
				frappe.throw(
					_(
						"Charges row {0}: Linked Service {1} is not defined on this Change Request. "
						"Add it via Manage Linked Services first."
					).format(
						getattr(row, "idx", "") or "?",
						frappe.bold(ls_link),
					),
					title=_("Linked Service Not Found"),
				)
			ls_service_type = frappe.db.get_value(
				linked_service_doctype(), ls_link, "service_type"
			)
			if ls_service_type and not sales_quote_charge_service_types_equal(
				getattr(row, "service_type", None), ls_service_type
			):
				frappe.throw(
					_(
						"Charges row {0}: Linked Service {1} is {2}, but this charge is {3}."
					).format(
						getattr(row, "idx", "") or "?",
						frappe.bold(ls_link),
						frappe.bold(ls_service_type),
						frappe.bold(getattr(row, "service_type", None) or "?"),
					),
					title=_("Linked Service Type Mismatch"),
				)

	def after_insert(self):
		self._drop_virtual_linked_services_rows()

	def on_update(self):
		self._drop_virtual_linked_services_rows()

	def on_submit(self):
		from logistics.pricing_center.change_request_field_apply import apply_change_request_fields_to_job
		from logistics.pricing_center.change_request_to_job import apply_change_request_charges_to_job

		frappe.flags.from_change_request = True
		try:
			apply_change_request_fields_to_job(self)
			apply_change_request_charges_to_job(self)
		finally:
			frappe.flags.from_change_request = False
		frappe.db.set_value("Change Request", self.name, "status", "Submitted", update_modified=False)

	def on_cancel(self):
		from logistics.pricing_center.change_request_to_job import remove_change_request_charges_from_job

		frappe.flags.from_change_request = True
		try:
			remove_change_request_charges_from_job(self)
		finally:
			frappe.flags.from_change_request = False
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


def _charge_row_as_sales_quote_dict(charge_row, default_service_type, default_linked_service=None):
	"""Map Change Request Charge row to Sales Quote Charge child dict (same field names).

	When the CR Charge row is tagged with a Linked Service (explicitly or via *default_linked_service*),
	force ``charge_scope='Linked'`` on the produced Sales Quote Charge.
	"""
	from logistics.pricing_center.change_request_to_job import _linked_service_for_row

	out = {}
	for k, v in charge_row.as_dict().items():
		if k in _SKIP_CHARGE_COPY:
			continue
		if v is None or v == "":
			continue
		out[k] = v
	if not out.get("service_type"):
		out["service_type"] = default_service_type
	ls = (_linked_service_for_row(out, default_linked_service) or "").strip()
	raw_scope = (out.get("charge_scope") or "").strip()
	if ls:
		out["charge_scope"] = CHARGE_SCOPE_LINKED
		set_charge_row_linked_service_link(out, ls)
	elif raw_scope and normalize_charge_scope(raw_scope) == CHARGE_SCOPE_MAIN:
		out["charge_scope"] = CHARGE_SCOPE_MAIN
		set_charge_row_linked_service_link(out, None)
	else:
		out["charge_scope"] = CHARGE_SCOPE_MAIN
	return out


def _linked_service_identity(ls_doc) -> tuple:
	return (
		(getattr(ls_doc, "service_type", None) or "").strip(),
		(getattr(ls_doc, "job_type", None) or "").strip(),
		(getattr(ls_doc, "job_no", None) or "").strip(),
	)


def _cr_default_linked_service_for_charges(cr) -> str | None:
	"""Default Linked Service tag for charge rows on this Change Request."""
	rows = linked_service_rows(cr)
	if len(rows) == 1:
		return charge_row_linked_service_link(rows[0]) or None

	from logistics.pricing_center.change_request_to_job import _resolve_main_and_default_internal_job

	_, _, job_default = _resolve_main_and_default_internal_job(cr)
	if not job_default:
		return None
	if any(charge_row_linked_service_link(r) == job_default for r in rows):
		return job_default

	try:
		job_default_doc = frappe.get_doc(linked_service_doctype(), job_default)
	except frappe.DoesNotExistError:
		return job_default

	job_identity = _linked_service_identity(job_default_doc)
	for row in rows:
		ls_name = charge_row_linked_service_link(row)
		if not ls_name:
			continue
		try:
			cr_ls = frappe.get_doc(linked_service_doctype(), ls_name)
		except frappe.DoesNotExistError:
			continue
		if _linked_service_identity(cr_ls) == job_identity:
			return ls_name
	return job_default


def _clone_change_request_linked_services_onto_sales_quote(cr, sq_name: str) -> dict[str, str]:
	"""Clone CR-owned Linked Services onto a Sales Quote; return ``{cr_ls: sq_ls}``."""
	from logistics.utils.internal_job_persistence import (
		create_internal_job_for_parent_from_source,
		get_internal_jobs_for_booking,
	)

	mapping: dict[str, str] = {}
	for cr_ls in get_internal_jobs_for_booking(cr):
		new_name = create_internal_job_for_parent_from_source("Sales Quote", sq_name, cr_ls)
		mapping[cr_ls.name] = new_name
	return mapping


@frappe.whitelist()
def get_eligible_internal_jobs_for_change_request_job(
	job_type, job_name, change_request_name=None
):
	"""Return Linked Service names eligible for tagging on Change Request Charge rows.

	When *change_request_name* is set, returns services from that Change Request's Services tab.
	Otherwise falls back to linked services on the job (legacy / pre-save).
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
	if change_request_name and frappe.db.exists("Change Request", change_request_name):
		from logistics.logistics.doctype.linked_service.linked_service import (
			get_linked_services_for_change_request,
		)

		from logistics.utils.linked_service_usage import latest_satellite_job_from_usage

		rows = []
		for ls in get_linked_services_for_change_request(change_request_name):
			jt, jn = latest_satellite_job_from_usage(ls.name)
			rows.append(
				{
					"name": ls.name,
					"service_type": ls.service_type,
					"job_type": jt or None,
					"job_no": jn or None,
					"job_description": None,
				}
			)
		out["linked_services"] = rows
		out["internal_jobs"] = rows
		if len(rows) == 1:
			out["default_linked_service"] = rows[0]["name"]
			out["default_internal_job"] = rows[0]["name"]
		return out

	if not job_type or not job_name:
		return out
	if not frappe.db.exists(job_type, job_name):
		return out

	from logistics.utils.linked_service_usage import latest_satellite_job_from_usage

	if job_type in MAIN_JOB_TYPES_FOR_CHANGE_REQUEST:
		ls_names = frappe.get_all(
			ls_dt,
			filters={"parent_booking_type": job_type, "parent_booking_name": job_name},
			pluck="name",
			order_by="creation asc",
		)
		rows = []
		for ls_name in ls_names:
			st = frappe.db.get_value(ls_dt, ls_name, "service_type")
			jt, jn = latest_satellite_job_from_usage(ls_name)
			rows.append(
				{
					"name": ls_name,
					"service_type": st,
					"job_type": jt or None,
					"job_no": jn or None,
					"job_description": None,
				}
			)
		out["linked_services"] = rows
		out["internal_jobs"] = rows
		return out

	if job_type in INTERNAL_JOB_SATELLITE_JOB_TYPES:
		from logistics.utils.service_role_rules import get_linked_service_name

		sat = frappe.db.get_value(
			job_type,
			job_name,
			("main_service_type", "main_service", "linked_service"),
			as_dict=True,
		) or {}
		ls_name = get_linked_service_name(sat)
		if ls_name and linked_service_record_exists(ls_name):
			st = frappe.db.get_value(ls_dt, ls_name, "service_type")
			jt, jn = latest_satellite_job_from_usage(ls_name)
			row = {
				"name": ls_name,
				"service_type": st,
				"job_type": jt or None,
				"job_no": jn or None,
				"job_description": None,
			}
			out["linked_services"] = [row]
			out["default_linked_service"] = ls_name
			out["internal_jobs"] = [row]
			out["default_internal_job"] = ls_name
	return out


@frappe.whitelist()
def create_change_request(job_type, job_name, sections=None, reason=None, reuse_draft=None):
	"""Create a Change Request linked to the job, seeded from current job values.

	Returns the Change Request name. When *reuse_draft* is truthy and a Draft CR already
	exists for this job, returns that name instead of creating another.
	"""
	if not job_type or not job_name:
		frappe.throw(_("Job Type and Job are required"))
	if not frappe.db.exists(job_type, job_name):
		frappe.throw(_("Job {0} does not exist").format(job_name))

	from frappe.utils import cint

	from logistics.pricing_center.change_request_field_apply import seed_change_request_from_job

	if cint(reuse_draft):
		existing_rows = frappe.get_all(
			"Change Request",
			filters={"job_type": job_type, "job": job_name, "docstatus": 0},
			pluck="name",
			order_by="modified desc",
			limit_page_length=1,
		)
		if existing_rows:
			return existing_rows[0]

	reason = (reason or "").strip() or _("Amendment")

	# sections may arrive as JSON list from the dialog
	if isinstance(sections, str) and sections.strip().startswith("["):
		try:
			sections = json.loads(sections)
		except Exception:
			pass

	cr = frappe.new_doc("Change Request")
	cr.job_type = job_type
	cr.job = job_name
	cr.status = "Draft"
	seed_change_request_from_job(cr, sections=sections, reason=reason)
	cr.insert(ignore_permissions=True)
	return cr.name


def _resolve_main_job_for_change_request(cr):
	"""Resolve the Main job ``(doctype, name)`` for the CR, walking IJ satellite back-links when needed.

	* CR target is a Main job → returns the CR target itself.
	* CR target is an Internal Job satellite (Transport Order / Sea Booking / Air Booking /
	  Declaration Order / Inbound Order / Release Order) → walks ``main_service_type`` /
	  ``main_service`` on the satellite to find its parent Main job. The Sales Quote is always
	  created against the Main so that billing and the Change Request revenue merge stay on one
	  canonical job.
	"""
	from logistics.pricing_center.additional_charge_to_job import (
		INTERNAL_JOB_SATELLITE_JOB_TYPES,
		MAIN_JOB_TYPES_FOR_CHANGE_REQUEST,
	)
	from logistics.utils.service_role_rules import get_main_service_name, get_main_service_type

	if cr.job_type in MAIN_JOB_TYPES_FOR_CHANGE_REQUEST:
		return cr.job_type, cr.job
	if cr.job_type in INTERNAL_JOB_SATELLITE_JOB_TYPES:
		sat = (
			frappe.db.get_value(
				cr.job_type,
				cr.job,
				("service_role", "main_service_type", "main_service"),
				as_dict=True,
			)
			or {}
		)
		mt = get_main_service_type(sat)
		mn = get_main_service_name(sat)
		if mt and mn and frappe.db.exists(mt, mn):
			return mt, mn
		frappe.throw(
			_(
				"Cannot create Sales Quote: Change Request target {0} {1} is not linked to a Main job. "
				"Set main_service_type / main_service on the Internal Job satellite first."
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
		"Docket": "MICE",
	}
	sq.main_service = job_to_service.get(main_job_type, "Transport")
	# Additional-charge quotes from Change Request are always one-off (and matching naming series).
	sq.quotation_type = "One-off"
	sq.naming_series = "OOQ.#####"
	sq.change_request = cr.name
	populate_sales_quote_from_job(sq, job_doc, main_job_type)
	sq.flags.ignore_mandatory = True
	sq.insert(ignore_permissions=True)

	ls_mapping = _clone_change_request_linked_services_onto_sales_quote(cr, sq.name)
	default_ls = _cr_default_linked_service_for_charges(cr)

	sq.reload()
	for row in cr.charges:
		row_dict = _charge_row_as_sales_quote_dict(row, sq.main_service, default_ls)
		cr_ls = charge_row_linked_service_link(row_dict)
		if cr_ls and ls_mapping.get(cr_ls):
			set_charge_row_linked_service_link(row_dict, ls_mapping[cr_ls])
			row_dict["charge_scope"] = CHARGE_SCOPE_LINKED
		row_dict["change_request_charge"] = row.name
		sq.append("charges", row_dict)
	sq.flags.ignore_mandatory = True
	sq.save(ignore_permissions=True)
	# Link back (submitted doc: avoid save(); status/sales_quote are not allow_on_submit)
	frappe.db.set_value(
		"Change Request",
		cr.name,
		{"sales_quote": sq.name, "status": "Sales Quote Created"},
		update_modified=False,
	)
	link_sales_quote_to_change_request_job_charges(cr.name, sq.name)
	return sq.name


def _clear_change_request_charge_links_to_linked_service(cr, linked_service: str) -> None:
	"""Clear charge rows that tagged *linked_service* (revert to Main scope)."""
	changed = False
	for row in getattr(cr, "charges", None) or []:
		if charge_row_linked_service_link(row) != linked_service:
			continue
		set_charge_row_linked_service_link(row, None)
		row.charge_scope = CHARGE_SCOPE_MAIN
		changed = True
	if changed:
		cr.flags.ignore_mandatory = True


def _assert_change_request_can_manage_linked_services(cr) -> None:
	if cr.docstatus != 0:
		frappe.throw(
			_("Linked Services can only be managed on draft Change Requests."),
			title=_("Change Request Not Editable"),
		)


@frappe.whitelist()
def list_change_request_linked_services(change_request: str):
	"""Return Linked Services for the Manage Services dialog on Change Request."""
	from logistics.logistics.doctype.linked_service.linked_service import (
		get_linked_services_for_change_request,
	)
	from logistics.utils.linked_service_usage import latest_satellite_job_from_usage

	cr = frappe.get_doc("Change Request", change_request)
	frappe.has_permission("Change Request", "read", doc=cr, throw=True)
	rows = []
	for linked in get_linked_services_for_change_request(cr.name):
		job_type, job_no = latest_satellite_job_from_usage(linked.name)
		rows.append(
			{
				"linked_service": linked.name,
				"service_type": linked.service_type,
				"owned_by_change_request": 1,
				"job_type": job_type or "",
				"job_no": job_no or "",
			}
		)
	return {"name": cr.name, "linked_services": rows}


@frappe.whitelist()
def add_linked_service(change_request: str, service_type: str):
	"""Create a Linked Service owned by this Change Request."""
	from logistics.time_sensitive.service_linking import validate_linked_service_type

	cr = frappe.get_doc("Change Request", change_request)
	frappe.has_permission("Change Request", "write", doc=cr, throw=True)
	_assert_change_request_can_manage_linked_services(cr)
	if not cr.name or cr.is_new():
		frappe.throw(_("Save the Change Request before adding a linked service."))

	service_type = validate_linked_service_type(service_type)
	linked = frappe.new_doc(linked_service_doctype())
	linked.service_type = service_type
	linked.parent_booking_type = "Change Request"
	linked.parent_booking_name = cr.name
	linked.insert(ignore_permissions=True)

	cr.flags._linked_services_view_cached = False
	if "linked_services" in cr.__dict__:
		del cr.__dict__["linked_services"]

	return {
		"name": cr.name,
		"linked_service": linked.name,
		"service_type": linked.service_type,
	}


@frappe.whitelist()
def remove_linked_service(change_request: str, linked_service: str):
	"""Delete a Change Request–owned Linked Service and clear charge tags to it."""
	from logistics.logistics.doctype.linked_service.linked_service import (
		get_linked_services_for_change_request,
	)

	cr = frappe.get_doc("Change Request", change_request)
	frappe.has_permission("Change Request", "write", doc=cr, throw=True)
	_assert_change_request_can_manage_linked_services(cr)

	ls_dt = linked_service_doctype()
	if not frappe.db.exists(ls_dt, linked_service):
		frappe.throw(_("Linked Service {0} was not found.").format(linked_service))

	owned_names = {row.name for row in get_linked_services_for_change_request(cr.name)}
	if linked_service not in owned_names:
		frappe.throw(
			_("Linked Service {0} is not linked to this Change Request.").format(linked_service)
		)

	parent_type = frappe.db.get_value(ls_dt, linked_service, "parent_booking_type")
	parent_name = frappe.db.get_value(ls_dt, linked_service, "parent_booking_name")
	if parent_type != "Change Request" or parent_name != cr.name:
		frappe.throw(
			_("Linked Service {0} is not owned by this Change Request.").format(linked_service)
		)

	_clear_change_request_charge_links_to_linked_service(cr, linked_service)
	frappe.delete_doc(ls_dt, linked_service, ignore_permissions=True, force=True)

	cr.flags._linked_services_view_cached = False
	if "linked_services" in cr.__dict__:
		del cr.__dict__["linked_services"]
	cr.flags.ignore_mandatory = True
	cr.save(ignore_permissions=True)

	return {
		"name": cr.name,
		"linked_service": linked_service,
		"action": "removed",
	}
