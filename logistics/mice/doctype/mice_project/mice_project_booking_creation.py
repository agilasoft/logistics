# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Create Air / Sea Booking and Transport / Declaration / Inbound Order from Exhibit Internal Job rows.

Mirrors ``logistics.mice.doctype.docket.docket_booking_creation`` but for the Exhibit DocType:
each row of ``exhibit.internal_jobs`` (Internal Job Detail) represents one intended main-service job
for the Exhibit, and this module turns those rows into standalone booking/order documents. The new
documents are not internal jobs — they link back to the Exhibit only through the row's ``job_no``
(and through accounting context inherited from the Exhibit / its Project).
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Any

import frappe
from frappe import _
from frappe.utils import today

from logistics.utils.charge_service_type import (
	effective_internal_job_detail_job_type,
	sales_quote_charge_service_types_equal,
)
from logistics.utils.internal_job_from_source import (
	apply_internal_job_detail_row_to_operational_doc,
	coerce_internal_job_detail_idx,
	linked_internal_job_target_is_cancelled,
)
from logistics.utils.linked_service_compat import linked_service_rows


EXHIBIT_CREATABLE_JOB_TYPES: frozenset[str] = frozenset(
	{
		"Air Booking",
		"Sea Booking",
		"Transport Order",
		"Declaration Order",
		"Inbound Order",
		"MICE Order",
	}
)

_TARGET_DOC_LABELS: dict[str, str] = {
	"Air Booking": "Air Booking",
	"Sea Booking": "Sea Booking",
	"Transport Order": "Transport Order",
	"Declaration Order": "Declaration Order",
	"Inbound Order": "Inbound Order",
	"MICE Order": "MICE Order",
}


def _resolve_organizer_customer(ep_doc: Any) -> str | None:
	"""Return the billing Customer linked to the Exhibit's Organizer (if any).

	Replaces the previous direct ``ep_doc.customer`` reads now that
	``MICE Project`` no longer stores a Customer link directly.
	"""
	if not ep_doc:
		return None
	getter = getattr(ep_doc, "get_organizer_customer", None)
	if callable(getter):
		try:
			return getter() or None
		except Exception:
			pass
	organizer = getattr(ep_doc, "organizer", None)
	if not organizer:
		return None
	try:
		return frappe.db.get_value("MICE Organizer", organizer, "customer") or None
	except Exception:
		return None


def _dialog_creatable_job_type(row: Any) -> str:
	"""Job type used in Create > Booking/Order. Special Project service → Project Order; MICE → MICE Order."""
	if not row:
		return ""
	st = (getattr(row, "service_type", None) or "").strip()
	if sales_quote_charge_service_types_equal(st, "Special Project"):
		return ""
	if sales_quote_charge_service_types_equal(st, "MICE"):
		return "MICE Order"
	return effective_internal_job_detail_job_type(row)


_LOGISTICS_EX_CLIENT_ROWS = "_logistics_ex_ij_client_rows"


def _coerce_client_rows(client_value: Any) -> list | None:
	if client_value is None or client_value == "":
		return None
	if isinstance(client_value, str):
		try:
			client_value = frappe.parse_json(client_value)
		except Exception:
			return None
	if not isinstance(client_value, list):
		return None
	return client_value


@contextmanager
def _client_rows_context(client_value: Any):
	key = _LOGISTICS_EX_CLIENT_ROWS
	parsed = _coerce_client_rows(client_value)
	# Empty list is not a useful override — virtual Linked Services grids often serialize as [].
	install = parsed is not None and len(parsed) > 0
	had_before = hasattr(frappe.local, key)
	old_val = getattr(frappe.local, key, None) if had_before else None
	try:
		if install:
			setattr(
				frappe.local,
				key,
				[frappe._dict(r) if isinstance(r, dict) else r for r in parsed],
			)
		yield
	finally:
		if install:
			if had_before:
				setattr(frappe.local, key, old_val)
			else:
				try:
					delattr(frappe.local, key)
				except AttributeError:
					pass


def _resolve_client_rows(client_value: Any, linked_services: Any = None) -> Any:
	"""Accept desk payload from ``linked_services`` or legacy ``internal_jobs``."""
	if client_value is not None and client_value != "":
		return client_value
	return linked_services


def _linked_services_list(parent_doc: Any) -> list[Any]:
	ov = getattr(frappe.local, _LOGISTICS_EX_CLIENT_ROWS, None)
	if ov:
		return list(ov)
	return linked_service_rows(parent_doc)


def _all_rows_for_form(parent_doc: Any, client_rows: Any, linked_services: Any = None) -> list[tuple[int, Any]]:
	client_rows = _resolve_client_rows(client_rows, linked_services)
	parsed = _coerce_client_rows(client_rows)
	if parsed is None:
		rows = linked_service_rows(parent_doc)
		return [(i, r) for i, r in enumerate(rows, start=1)]
	if (
		not parsed
		and getattr(parent_doc, "name", None)
		and not getattr(parent_doc, "__islocal", False)
	):
		rows = linked_service_rows(parent_doc)
		return [(i, r) for i, r in enumerate(rows, start=1)]
	out: list[tuple[int, Any]] = []
	for i, rowd in enumerate(parsed, start=1):
		rw = frappe._dict(rowd) if isinstance(rowd, dict) else rowd
		out.append((i, rw))
	return out


def _resolve_row_for_create(
	parent_doc: Any, job_type: str, idx: int | None
) -> tuple[Any | None, int | None]:
	jt = (job_type or "").strip()
	if idx is not None:
		rows = _linked_services_list(parent_doc)
		if idx < 1 or idx > len(rows):
			frappe.throw(_("Invalid Linked Service row."))
		row = rows[idx - 1]
		row_jt = _dialog_creatable_job_type(row)
		if row_jt != jt:
			frappe.throw(_("The selected line is not for {0}.").format(jt))
		jn = (getattr(row, "job_no", None) or "").strip()
		if jn:
			frappe.throw(
				_("This Internal Job line already references {0} {1}.").format(row_jt, jn),
				title=_("Already linked"),
			)
		return row, idx
	rows = _linked_services_list(parent_doc)
	for i, r in enumerate(rows, start=1):
		if _dialog_creatable_job_type(r) != jt:
			continue
		if (getattr(r, "job_no", None) or "").strip():
			continue
		return r, i
	return None, None


def _choice_header(job_type: str, row: Any | None, idx: int | None, jn: str) -> dict[str, Any]:
	jt_label = (job_type or "").strip()
	st = (getattr(row, "service_type", None) or "").strip() if row else ""
	title = _(st) if st else (_(jt_label) if jt_label else _("(no service type)"))
	if jn:
		badge = jn
	elif idx is not None:
		badge = _("Pending")
	else:
		badge = _("Job Details")
	if jn:
		subtitle = _("Already linked — open the job from Job No above.")
	elif not st:
		subtitle = _("Select a service type on this line to set the target document type.")
	elif not jt_label:
		subtitle = _("This service type cannot be created from a MICE Project.")
	else:
		subtitle = _("Creates {0} linked to this MICE Project.").format(
			_(_TARGET_DOC_LABELS.get(jt_label, jt_label))
		)
	return {"header_title": title, "header_badge": badge, "header_subtitle": subtitle}


@frappe.whitelist()
def get_exhibit_booking_choices(
	exhibit: str, internal_jobs: Any = None, linked_services: Any = None
):
	"""Return Create > Booking/Order options for each Linked Service row on an Exhibit."""
	if not exhibit or not frappe.db.exists("MICE Project", exhibit):
		frappe.throw(_("Invalid MICE Project."))
	doc = frappe.get_doc("MICE Project", exhibit)
	doc.check_permission("read")

	client_rows = _resolve_client_rows(internal_jobs, linked_services)
	with _client_rows_context(client_rows):
		choices: list[dict[str, Any]] = []
		for idx, row in _all_rows_for_form(doc, client_rows):
			st = (getattr(row, "service_type", None) or "").strip()
			jt = _dialog_creatable_job_type(row)
			jn = (getattr(row, "job_no", None) or "").strip()
			creatable = bool(jt) and jt in EXHIBIT_CREATABLE_JOB_TYPES and not jn
			not_creatable_message = None
			if creatable:
				from logistics.utils.internal_job_creation_eligibility import (
					evaluate_internal_job_creation_eligibility,
				)

				elig = evaluate_internal_job_creation_eligibility(
					sales_quote=getattr(doc, "sales_quote", None),
					parent_doc=doc,
					ij_row=row,
					service_type_label=st,
				)
				if not elig.get("eligible"):
					creatable = False
					not_creatable_message = elig.get("message")
			header = _choice_header(jt, row, idx, jn)
			cancelled = bool(jn and linked_internal_job_target_is_cancelled(jt, jn))
			if cancelled:
				header = {
					**header,
					"header_subtitle": _("Linked to {0} (cancelled).").format(jn),
					"linked_job_cancelled": True,
				}
			choices.append(
				{
					"mode": "detail",
					"detail_idx": idx,
					"job_type": jt,
					"service_type": st or None,
					"job_no": jn or None,
					"creatable": creatable,
					"not_creatable_message": not_creatable_message,
					**header,
				}
			)
	return {"choices": choices}


def _company_fieldname(doctype: str) -> str | None:
	"""Return the fieldname on `doctype` that links to Company (if any)."""
	dt_meta = frappe.get_meta(doctype)
	for fn in ("company", "custom_company"):
		if dt_meta.has_field(fn):
			return fn
	return None


def _strip_link(value: Any) -> str | None:
	return (value or "").strip() or None


def _resolve_exhibit_org_context(ep_doc: Any) -> dict[str, Any]:
	"""Best-effort accounting context for the new booking/order.

	Reads company / branch / cost center / profit center from the MICE Project when
	set, then resolves company from the linked ERPNext Project and fills any remaining
	gaps from Customs Settings and company-scoped master data so mandatory fields on
	orders such as Declaration Order are populated on insert.
	"""
	ctx: dict[str, Any] = {
		"company": _strip_link(getattr(ep_doc, "company", None)),
		"branch": _strip_link(getattr(ep_doc, "branch", None)),
		"cost_center": _strip_link(getattr(ep_doc, "cost_center", None)),
		"profit_center": _strip_link(getattr(ep_doc, "profit_center", None)),
		"project": _strip_link(getattr(ep_doc, "project", None)),
	}

	project = ctx["project"]
	if project and frappe.db.exists("Project", project):
		try:
			project_company = frappe.db.get_value("Project", project, "company")
		except Exception:
			project_company = None
		if project_company:
			if not ctx["company"]:
				ctx["company"] = project_company
			if not ctx["cost_center"]:
				try:
					company_cost_center = frappe.db.get_value("Company", project_company, "cost_center")
					if company_cost_center:
						ctx["cost_center"] = company_cost_center
				except Exception:
					pass

	if not ctx["company"]:
		ctx["company"] = (
			frappe.defaults.get_user_default("Company")
			or frappe.db.get_single_value("Global Defaults", "default_company")
		)

	company = ctx["company"]
	if not company:
		return ctx

	if not ctx["branch"] or not ctx["cost_center"] or not ctx["profit_center"]:
		try:
			cs = frappe.db.get_value(
				"Customs Settings",
				{"company": company},
				["default_branch", "default_cost_center", "default_profit_center"],
				as_dict=True,
			)
			if cs:
				if not ctx["branch"]:
					ctx["branch"] = cs.get("default_branch")
				if not ctx["cost_center"]:
					ctx["cost_center"] = cs.get("default_cost_center")
				if not ctx["profit_center"]:
					ctx["profit_center"] = cs.get("default_profit_center")
		except Exception:
			pass

	if not ctx["branch"]:
		branch_company_fn = _company_fieldname("Branch")
		if branch_company_fn:
			ctx["branch"] = frappe.db.get_value(
				"Branch",
				{branch_company_fn: company},
				"name",
				order_by="modified desc",
			)

	if not ctx["cost_center"]:
		cc_filters = {"is_group": 0, "disabled": 0}
		cc_company_fn = _company_fieldname("Cost Center")
		if cc_company_fn:
			cc_filters[cc_company_fn] = company
		ctx["cost_center"] = frappe.db.get_value(
			"Cost Center",
			cc_filters,
			"name",
			order_by="creation asc",
		)

	if not ctx["profit_center"]:
		pc_company_fn = _company_fieldname("Profit Center")
		if pc_company_fn:
			ctx["profit_center"] = frappe.db.get_value(
				"Profit Center",
				{pc_company_fn: company},
				"name",
				order_by="creation asc",
			)
		else:
			ctx["profit_center"] = frappe.db.get_value(
				"Profit Center",
				{},
				"name",
				order_by="creation asc",
			)

	return ctx


@frappe.whitelist()
def get_exhibit_booking_preview(
	exhibit: str,
	job_type: str,
	internal_job_idx: int | None = None,
	internal_jobs: Any = None,
	linked_services: Any = None,
):
	"""Linked Service row parameters that will inform the new operational document."""
	if not exhibit or not frappe.db.exists("MICE Project", exhibit):
		frappe.throw(_("Invalid MICE Project."))
	doc = frappe.get_doc("MICE Project", exhibit)
	doc.check_permission("read")

	jt = (job_type or "").strip()
	idx = coerce_internal_job_detail_idx(internal_job_idx)
	org = _resolve_exhibit_org_context(doc)

	source_context = {
		"source_doctype": "MICE Project",
		"source_name": doc.name,
		"organizer": getattr(doc, "organizer", None),
		"customer": _resolve_organizer_customer(doc),
		"company": org.get("company"),
		"project": org.get("project"),
		"sales_quote": None,
		"source_is_internal_job": False,
		"source_main_job_type": None,
		"source_main_job": None,
		"from_main_service_shipment": False,
	}

	client_rows = _resolve_client_rows(internal_jobs, linked_services)
	with _client_rows_context(client_rows):
		rows = _linked_services_list(doc)

		if idx is not None and 1 <= idx <= len(rows):
			row_linked = rows[idx - 1]
			jn_linked = (getattr(row_linked, "job_no", None) or "").strip()
			if jn_linked:
				row_jt = _dialog_creatable_job_type(row_linked)
				cancelled = linked_internal_job_target_is_cancelled(row_jt, jn_linked)
				msg = _("This line is already linked to {0}.").format(jn_linked)
				if cancelled:
					msg = _(
						"This line still references {0}, which is cancelled. Reload the MICE Project if the link should have been removed."
					).format(jn_linked)
				return {
					"job_type": jt or row_jt,
					"detail_idx": idx,
					"uses_job_detail_row": True,
					"creatable": False,
					"not_creatable_message": msg,
					"linked_job_cancelled": cancelled,
					"source_context": source_context,
					"target_internal_job": None,
					"job_detail_parameters": {},
					"charges": [],
				}

		if not jt:
			if idx is None:
				frappe.throw(_("Invalid selection."))
			rows[idx - 1]
			return {
				"job_type": "",
				"detail_idx": idx,
				"uses_job_detail_row": True,
				"creatable": False,
				"not_creatable_message": _("Set Service Type on this line before creating."),
				"source_context": source_context,
				"target_internal_job": None,
				"job_detail_parameters": {},
				"charges": [],
			}

		if jt not in EXHIBIT_CREATABLE_JOB_TYPES:
			return {
				"job_type": jt,
				"detail_idx": idx,
				"uses_job_detail_row": True,
				"creatable": False,
				"not_creatable_message": _(
					"This job type cannot be created from a MICE Project. Choose a supported booking/order."
				),
				"source_context": source_context,
				"target_internal_job": None,
				"job_detail_parameters": {},
				"charges": [],
			}

		row, res_idx = _resolve_row_for_create(doc, jt, idx)

		from logistics.utils.sales_quote_charge_parameters import (
			extract_sales_quote_charge_parameters,
		)

		routing_params = extract_sales_quote_charge_parameters(row) if row else {}
		preview_params = {k: v for k, v in (routing_params or {}).items() if k != "charge_group"}

		from logistics.utils.internal_job_creation_eligibility import (
			apply_eligibility_to_preview_flags,
		)

		return apply_eligibility_to_preview_flags(
			{
				"job_type": jt,
				"detail_idx": res_idx,
				"uses_job_detail_row": row is not None,
				"creatable": True,
				"source_context": source_context,
				"target_internal_job": None,
				"job_detail_parameters": preview_params,
				"charges": [],
			},
			sales_quote=getattr(doc, "sales_quote", None),
			parent_doc=doc,
			ij_row=row,
			service_type_label=(getattr(row, "service_type", None) or "").strip() if row else None,
		)


def _apply_exhibit_context(target_doc: Any, ep_doc: Any) -> None:
	"""Populate accounting and reference fields from the MICE Project onto the new booking/order."""
	meta = frappe.get_meta(target_doc.doctype)
	org = _resolve_exhibit_org_context(ep_doc)

	def _set_if_field(fieldname: str, value: Any) -> None:
		if value in (None, ""):
			return
		if not meta.get_field(fieldname):
			return
		target_doc.set(fieldname, value)

	_set_if_field("company", org.get("company"))
	_set_if_field("branch", org.get("branch"))
	_set_if_field("cost_center", org.get("cost_center"))
	_set_if_field("profit_center", org.get("profit_center"))
	_set_if_field("project", org.get("project"))
	sq_name = (getattr(ep_doc, "sales_quote", None) or "").strip() or _resolve_sales_quote_for_exhibit(ep_doc)
	_set_if_field("sales_quote", sq_name)

	cust = _resolve_organizer_customer(ep_doc)
	if cust:
		if meta.get_field("local_customer"):
			target_doc.local_customer = cust
		if meta.get_field("customer"):
			target_doc.customer = cust
	_apply_sales_quote_parties_to_target(target_doc, ep_doc)


def _apply_sales_quote_parties_to_target(target_doc: Any, ep_doc: Any) -> None:
	"""Copy shipper/consignee from the linked Sales Quote (same as quote → booking creation)."""
	sq_name = (
		(getattr(ep_doc, "sales_quote", None) or "").strip()
		or _resolve_sales_quote_for_exhibit(ep_doc)
		or getattr(target_doc, "sales_quote", None)
		or ""
	).strip()
	if not sq_name or not frappe.db.exists("Sales Quote", sq_name):
		return
	sq = frappe.get_cached_doc("Sales Quote", sq_name)
	meta = frappe.get_meta(target_doc.doctype)
	for party_fn in ("shipper", "consignee"):
		if not meta.get_field(party_fn):
			continue
		if not (getattr(target_doc, party_fn, None) or "").strip() and getattr(sq, party_fn, None):
			target_doc.set(party_fn, sq.get(party_fn))
	if target_doc.doctype in ("Air Booking", "Sea Booking"):
		from logistics.utils.party_address_contact_from_masters import (
			populate_air_sea_booking_party_fields_from_masters,
		)
		from logistics.utils.shipper_consignee_defaults import apply_shipper_consignee_defaults

		populate_air_sea_booking_party_fields_from_masters(target_doc)
		apply_shipper_consignee_defaults(target_doc)


def _populate_charges_from_linked_sales_quote(target_doc: Any) -> None:
	"""Populate operational charges from the linked Sales Quote."""
	sq_name = getattr(target_doc, "sales_quote", None)
	if not sq_name or not frappe.db.exists("Sales Quote", sq_name):
		return

	dt = target_doc.doctype
	try:
		if dt == "Air Booking":
			from logistics.utils.internal_job_from_source import (
				_populate_air_booking_charges_from_linked_quote_on_internal_create,
			)

			_populate_air_booking_charges_from_linked_quote_on_internal_create(target_doc)
		elif dt == "Sea Booking":
			from logistics.utils.internal_job_from_source import (
				_populate_sea_booking_charges_from_linked_quote_on_internal_create,
			)

			_populate_sea_booking_charges_from_linked_quote_on_internal_create(target_doc)
		elif dt == "Transport Order" and hasattr(target_doc, "_populate_charges_from_sales_quote"):
			target_doc._populate_charges_from_sales_quote()
		elif dt == "Declaration Order" and hasattr(target_doc, "_populate_charges_from_sales_quote"):
			target_doc._populate_charges_from_sales_quote()
		elif dt == "Inbound Order" and hasattr(target_doc, "_populate_charges_from_sales_quote"):
			target_doc._populate_charges_from_sales_quote()
	except Exception:
		frappe.log_error(
			frappe.get_traceback(),
			f"MICE Project — Sales Quote charge population on {dt} create",
		)


def _prepare_operational_charges_before_insert(ep_doc: Any, target_doc: Any, row: Any | None) -> None:
	"""Load Sales Quote charges onto the new booking/order and scope them to the Internal Job row."""
	target_meta = frappe.get_meta(target_doc.doctype)
	charges_df = target_meta.get_field("charges")
	if not charges_df or charges_df.fieldtype != "Table":
		return

	if target_meta.get_field("sales_quote") and not (getattr(target_doc, "sales_quote", None) or "").strip():
		sq_name = (getattr(ep_doc, "sales_quote", None) or "").strip() or _resolve_sales_quote_for_exhibit(ep_doc)
		if sq_name:
			target_doc.sales_quote = sq_name

	_populate_charges_from_linked_sales_quote(target_doc)
	from logistics.utils.charge_service_type import filter_operational_doc_charges_for_internal_job_row
	from logistics.utils.sales_quote_charge_copy import SCOPE_INTERNAL_JOB, stamp_scope_fields_on_charge_row

	filter_operational_doc_charges_for_internal_job_row(target_doc, row)
	row_ij = (
		(getattr(row, "internal_job", None) or getattr(row, "linked_service", None) or "").strip()
		if row
		else ""
	)
	if row_ij:
		for charge_row in getattr(target_doc, "charges", None) or []:
			stamp_scope_fields_on_charge_row(charge_row, SCOPE_INTERNAL_JOB, row_ij)


def _apply_air_sea_corridor_ports_from_row(target_doc: Any, row: Any | None) -> None:
	"""Fill mandatory origin/destination ports from the internal-job row when present."""
	if target_doc.doctype not in ("Air Booking", "Sea Booking"):
		return
	meta = frappe.get_meta(target_doc.doctype)
	if not meta.get_field("origin_port"):
		return
	if not row:
		return

	def _set_if_empty(fieldname: str, value: Any) -> None:
		if value in (None, ""):
			return
		if not meta.get_field(fieldname):
			return
		if not (getattr(target_doc, fieldname, None) or "").strip():
			target_doc.set(fieldname, value)

	for fn in ("origin_port", "destination_port", "direction"):
		_set_if_empty(fn, getattr(row, fn, None))


def _booking_date_field(target_doc: Any) -> str | None:
	meta = frappe.get_meta(target_doc.doctype)
	for fn in ("booking_date", "order_date", "scheduled_date"):
		if meta.get_field(fn):
			return fn
	return None


def _persist_row_link(ep_name: str, job_type: str, job_no: str, detail_idx: int) -> None:
	"""Write job_type and job_no back onto the MICE Project's Internal Job row."""
	from logistics.utils.internal_job_detail_copy import persist_internal_job_detail_job_link

	persist_internal_job_detail_job_link(
		"MICE Project", ep_name, job_type, job_no, detail_idx=detail_idx
	)


def _create_air_booking(ep_doc: Any, row: Any, detail_idx: int) -> dict[str, Any]:
	doc = frappe.new_doc("Air Booking")
	_apply_exhibit_context(doc, ep_doc)
	bd = _booking_date_field(doc)
	if bd:
		doc.set(bd, today())
	apply_internal_job_detail_row_to_operational_doc(doc, row, overwrite=True)
	_apply_air_sea_corridor_ports_from_row(doc, row)
	_prepare_operational_charges_before_insert(ep_doc, doc, row)
	doc.insert(ignore_permissions=True)
	_persist_row_link(ep_doc.name, "Air Booking", doc.name, detail_idx)
	frappe.db.commit()
	return {"air_booking": doc.name, "message": _("Air Booking {0} created.").format(doc.name)}


def _create_sea_booking(ep_doc: Any, row: Any, detail_idx: int) -> dict[str, Any]:
	doc = frappe.new_doc("Sea Booking")
	_apply_exhibit_context(doc, ep_doc)
	bd = _booking_date_field(doc)
	if bd:
		doc.set(bd, today())
	apply_internal_job_detail_row_to_operational_doc(doc, row, overwrite=True)
	_apply_air_sea_corridor_ports_from_row(doc, row)
	_prepare_operational_charges_before_insert(ep_doc, doc, row)
	doc.insert(ignore_permissions=True)
	_persist_row_link(ep_doc.name, "Sea Booking", doc.name, detail_idx)
	frappe.db.commit()
	return {"sea_booking": doc.name, "message": _("Sea Booking {0} created.").format(doc.name)}


def _create_transport_order(ep_doc: Any, row: Any, detail_idx: int) -> dict[str, Any]:
	from logistics.utils.transport_job_type import (
		apply_container_transport_context_to_order,
		set_internal_transport_order_draft_insert_flags,
	)

	order = frappe.new_doc("Transport Order")
	_apply_exhibit_context(order, ep_doc)
	order.booking_date = today()
	if frappe.get_meta("Transport Order").get_field("transport_job_type"):
		order.transport_job_type = "Non-Container"
	if frappe.get_meta("Transport Order").get_field("scheduled_date"):
		order.scheduled_date = today()
	apply_internal_job_detail_row_to_operational_doc(order, row, overwrite=True)
	apply_container_transport_context_to_order(order, row)
	set_internal_transport_order_draft_insert_flags(order)
	# Programme-created orders are standalone, not linked satellites.
	from logistics.utils.service_role_rules import apply_standalone_service_flags

	apply_standalone_service_flags(order)
	_prepare_operational_charges_before_insert(ep_doc, order, row)
	order.insert(ignore_permissions=True)
	_persist_row_link(ep_doc.name, "Transport Order", order.name, detail_idx)
	frappe.db.commit()
	return {
		"transport_order": order.name,
		"message": _("Transport Order {0} created.").format(order.name),
	}


def _create_declaration_order(ep_doc: Any, row: Any, detail_idx: int) -> dict[str, Any]:
	order = frappe.new_doc("Declaration Order")
	_apply_exhibit_context(order, ep_doc)
	if frappe.get_meta("Declaration Order").get_field("order_date"):
		order.order_date = today()
	if frappe.get_meta("Declaration Order").get_field("transport_mode") and not order.get(
		"transport_mode"
	):
		order.transport_mode = getattr(row, "transport_mode", None) or order.get("transport_mode")
	apply_internal_job_detail_row_to_operational_doc(order, row, overwrite=True)
	from logistics.utils.service_role_rules import apply_standalone_service_flags

	apply_standalone_service_flags(order)
	_prepare_operational_charges_before_insert(ep_doc, order, row)
	order.insert(ignore_permissions=True)
	_persist_row_link(ep_doc.name, "Declaration Order", order.name, detail_idx)
	frappe.db.commit()
	return {
		"declaration_order": order.name,
		"message": _("Declaration Order {0} created.").format(order.name),
	}


def _create_inbound_order(ep_doc: Any, row: Any, detail_idx: int) -> dict[str, Any]:
	order = frappe.new_doc("Inbound Order")
	_apply_exhibit_context(order, ep_doc)
	if frappe.get_meta("Inbound Order").get_field("order_date"):
		order.order_date = today()
	apply_internal_job_detail_row_to_operational_doc(order, row, overwrite=True)
	_prepare_operational_charges_before_insert(ep_doc, order, row)
	order.insert(ignore_permissions=True)
	_persist_row_link(ep_doc.name, "Inbound Order", order.name, detail_idx)
	frappe.db.commit()
	return {
		"inbound_order": order.name,
		"message": _("Inbound Order {0} created.").format(order.name),
	}


def _resolve_sales_quote_for_exhibit(ep_doc: Any) -> str | None:
	sq = (getattr(ep_doc, "sales_quote", None) or "").strip()
	if sq and frappe.db.exists("Sales Quote", sq):
		return sq
	if not getattr(ep_doc, "name", None):
		return None
	return (
		frappe.db.get_value(
			"Sales Quote",
			{"exhibit": ep_doc.name, "docstatus": 1},
			"name",
			order_by="modified desc",
		)
		or None
	)


def _suggested_mice_order_title(ep_doc: Any, row: Any | None) -> str:
	if row:
		for fn in ("job_description",):
			val = (getattr(row, fn, None) or "").strip()
			if val:
				return val
	pn = (getattr(ep_doc, "project_name", None) or ep_doc.name or "").strip()
	return f"{pn} — {_('MICE')}" if pn else _("MICE Order")


def _prepare_mice_order_charges(ep_doc: Any, order: Any, row: Any | None) -> None:
	"""Copy matching Sales Quote MICE charge lines onto the new MICE Order."""
	from logistics.utils.charge_service_type import sales_quote_charge_service_types_equal
	from logistics.utils.sales_quote_charge_parameters import (
		extract_service_scoped_quote_parameters,
		sales_quote_charge_row_matches_internal_job_detail_params,
	)
	from logistics.utils.sales_quote_programme_charges import map_sales_quote_charge_to_programme_charge_dict

	sq_name = _resolve_sales_quote_for_exhibit(ep_doc)
	if not sq_name:
		return
	if order.meta.get_field("sales_quote"):
		order.sales_quote = sq_name

	st = (getattr(row, "service_type", None) or "MICE").strip() if row else "MICE"
	ij_params = extract_service_scoped_quote_parameters(row, st) if row else {}
	sq = frappe.get_doc("Sales Quote", sq_name)
	charge_dt = "MICE Project Charges"
	order.set("charges", [])
	for ch in sq.get("charges") or []:
		if not sales_quote_charge_service_types_equal(getattr(ch, "service_type", None), st):
			continue
		if ij_params and not sales_quote_charge_row_matches_internal_job_detail_params(ch, ij_params):
			continue
		mapped = map_sales_quote_charge_to_programme_charge_dict(ch, sq_name, charge_dt)
		if mapped:
			order.append("charges", mapped)


def _create_mice_order(ep_doc: Any, row: Any, detail_idx: int) -> dict[str, Any]:
	order = frappe.new_doc("MICE Order")
	order.exhibit = ep_doc.name
	lifecycle_stage = (getattr(ep_doc, "lifecycle_stage", None) or "").strip()
	if not lifecycle_stage:
		from logistics.utils.lifecycle_stage import resolve_default_lifecycle_stage, FOR_EXHIBITS

		lifecycle_stage = resolve_default_lifecycle_stage(
			module_filter=FOR_EXHIBITS, preferred="Pre-Show"
		)
	order.lifecycle_stage = lifecycle_stage
	order.order_title = _suggested_mice_order_title(ep_doc, row)
	if order.meta.get_field("order_date"):
		order.order_date = today()
	if order.meta.get_field("status"):
		order.status = "Draft"

	_apply_exhibit_context(order, ep_doc)
	sq_name = _resolve_sales_quote_for_exhibit(ep_doc)
	if sq_name and order.meta.get_field("sales_quote"):
		order.sales_quote = sq_name

	if row and order.meta.get_field("site"):
		site = (getattr(row, "sp_site", None) or "").strip()
		if site:
			order.site = site

	apply_internal_job_detail_row_to_operational_doc(order, row, overwrite=True)
	_prepare_mice_order_charges(ep_doc, order, row)
	order.insert(ignore_permissions=True)
	_persist_row_link(ep_doc.name, "MICE Order", order.name, detail_idx)
	frappe.db.commit()
	return {
		"mice_order": order.name,
		"message": _("MICE Order {0} created.").format(order.name),
	}


_CREATE_DISPATCH = {
	"Air Booking": _create_air_booking,
	"Sea Booking": _create_sea_booking,
	"Transport Order": _create_transport_order,
	"Declaration Order": _create_declaration_order,
	"Inbound Order": _create_inbound_order,
	"MICE Order": _create_mice_order,
}


@frappe.whitelist()
def create_booking_or_order_from_exhibit(
	exhibit: str,
	job_type: str,
	internal_job_idx: int | None = None,
	internal_jobs: Any = None,
	linked_services: Any = None,
):
	"""Create the chosen booking/order from the matching Linked Service row on the Exhibit."""
	if not exhibit or not frappe.db.exists("MICE Project", exhibit):
		frappe.throw(_("Invalid MICE Project."))
	jt = (job_type or "").strip()
	if jt not in EXHIBIT_CREATABLE_JOB_TYPES:
		frappe.throw(_("Invalid job type."))

	ep_doc = frappe.get_doc("MICE Project", exhibit)
	ep_doc.check_permission("write")

	idx = coerce_internal_job_detail_idx(internal_job_idx)

	client_rows = _resolve_client_rows(internal_jobs, linked_services)
	with _client_rows_context(client_rows):
		from logistics.utils.internal_job_persistence import (
			ensure_linked_service_rows_materialized,
		)

		ensure_linked_service_rows_materialized(ep_doc)
		row, resolved_idx = _resolve_row_for_create(ep_doc, jt, idx)
		if row is None:
			frappe.throw(
				_(
					"Add a Linked Service line with service type matching {0}, or select an existing open line."
				).format(jt)
			)
		if resolved_idx is None:
			frappe.throw(_("Could not resolve the Linked Service row to update after creation."))
		from logistics.utils.internal_job_creation_eligibility import (
			require_internal_job_creation_eligible,
		)

		require_internal_job_creation_eligible(
			sales_quote=getattr(ep_doc, "sales_quote", None),
			parent_doc=ep_doc,
			ij_row=row,
			service_type_label=(getattr(row, "service_type", None) or "").strip(),
		)
		handler = _CREATE_DISPATCH[jt]
		return handler(ep_doc, row, resolved_idx)
