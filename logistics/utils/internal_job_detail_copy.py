# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Copy Internal Job Detail child rows between operational documents (e.g. booking → shipment)."""

from __future__ import annotations

from typing import Any

import frappe
from frappe import _

from logistics.utils.charge_service_type import effective_internal_job_detail_job_type
from logistics.utils.linked_service_compat import (
	linked_service_doctype,
	linked_service_record_exists,
	row_linked_service_link,
)
from logistics.utils.virtual_internal_job_details import uses_virtual_internal_job_details

DECLARATION_ORDER_JOB_TYPE = "Declaration Order"

_DEFAULT_SERVICE_TYPE_FOR_JOB_TYPE: dict[str, str] = {
	"Declaration Order": "Customs",
	"Transport Order": "Transport",
	"Air Booking": "Air",
	"Sea Booking": "Sea",
}

_SKIP_KEYS = frozenset(
	{
		"name",
		"owner",
		"creation",
		"modified",
		"modified_by",
		"docstatus",
		"idx",
		"parent",
		"parentfield",
		"parenttype",
		"doctype",
	}
)


def internal_job_detail_row_as_dict(row: Any) -> dict:
	"""Serialize a child row for append() on another parent."""
	if isinstance(row, dict):
		d = dict(row)
	else:
		d = row.as_dict()
	for k in _SKIP_KEYS:
		d.pop(k, None)
	return d


def sync_internal_job_details_from_declaration_to_declaration_order(declaration: Any) -> None:
	"""Align ``job_no`` / ``job_type`` on Declaration Order Linked Service docs with Declaration."""
	do_name = (getattr(declaration, "declaration_order", None) or "").strip()
	dec_name = (getattr(declaration, "name", None) or "").strip()
	if not do_name or not dec_name or not frappe.db.exists("Declaration Order", do_name):
		return
	from logistics.logistics.doctype.linked_service.linked_service import (
		get_linked_services_for_booking,
	)

	dec_rows = list(get_linked_services_for_booking("Declaration", dec_name))
	if not dec_rows:
		return
	order_rows = list(get_linked_services_for_booking("Declaration Order", do_name))

	def _row_key(ls: Any) -> tuple:
		st = (getattr(ls, "service_type", None) or "").strip()
		jt = effective_internal_job_detail_job_type(ls)
		ls_name = row_linked_service_link(ls) or (getattr(ls, "name", None) or "").strip()
		return (st, jt, ls_name)

	order_by_key = {_row_key(ls): ls for ls in order_rows}
	ls_dt = linked_service_doctype()
	for dec_ls in dec_rows:
		key = _row_key(dec_ls)
		ord_ls = order_by_key.get(key)
		if not ord_ls:
			continue
		dec_jn = (getattr(dec_ls, "job_no", None) or "").strip()
		ord_jn = (getattr(ord_ls, "job_no", None) or "").strip()
		dec_jt = (effective_internal_job_detail_job_type(dec_ls) or "").strip()
		ord_jt = (effective_internal_job_detail_job_type(ord_ls) or "").strip()
		new_jn = dec_jn or ord_jn
		new_jt = dec_jt or ord_jt
		updates: dict[str, Any] = {}
		if new_jn and new_jn != ord_jn:
			updates["job_no"] = new_jn
		if new_jt and new_jt != ord_jt:
			updates["job_type"] = new_jt
		if updates:
			frappe.db.set_value(ls_dt, ord_ls.name, updates, update_modified=False)


def copy_internal_job_details_to_doc(source_doc: Any, dest_doc: Any) -> None:
	"""Append copies of source_doc.internal_job_details onto dest_doc."""
	rows = getattr(source_doc, "internal_job_details", None) or []
	if not rows:
		return
	staged = [internal_job_detail_row_as_dict(row) for row in rows]
	if uses_virtual_internal_job_details(getattr(dest_doc, "doctype", None)):
		dest_doc.set("internal_job_details", [])
		for payload in staged:
			dest_doc.append("internal_job_details", payload)
		dest_doc.flags._internal_job_details_from_form = True
		return
	for payload in staged:
		dest_doc.append("internal_job_details", payload)


def _reparent_linked_service(ls_name: str, parent_doctype: str, parent_name: str) -> None:
	if not linked_service_record_exists(ls_name):
		return
	ls = frappe.get_doc(linked_service_doctype(), ls_name)
	ls.parent_booking_type = parent_doctype
	ls.parent_booking_name = parent_name
	ls.flags.ignore_permissions = True
	ls.flags.skip_internal_job_detail_sync = True
	ls.save(ignore_permissions=True)


def reparent_linked_services_between_parents(
	source_doctype: str,
	source_name: str,
	dest_doctype: str,
	dest_name: str,
) -> None:
	"""Re-parent every Linked Service owned by *source* onto *dest*."""
	from logistics.logistics.doctype.linked_service.linked_service import (
		get_linked_services_for_booking,
	)

	for ls in get_linked_services_for_booking(source_doctype, source_name):
		ls_name = (getattr(ls, "name", None) or "").strip()
		if ls_name:
			_reparent_linked_service(ls_name, dest_doctype, dest_name)


def transfer_linked_services_to_parent(source_doc: Any, dest_doc: Any) -> None:
	"""Re-parent Linked Service documents from *source* onto *dest*."""
	dest_name = (getattr(dest_doc, "name", None) or "").strip()
	source_name = (getattr(source_doc, "name", None) or "").strip()
	if not dest_name or not source_name:
		return
	reparent_linked_services_between_parents(
		getattr(source_doc, "doctype", None) or "",
		source_name,
		getattr(dest_doc, "doctype", None) or "",
		dest_name,
	)


def clone_linked_services_between_parents(
	source_doctype: str,
	source_name: str,
	dest_doctype: str,
	dest_name: str,
) -> dict[str, str]:
	"""Clone every Linked Service owned by *source* onto *dest*; *source* keeps originals."""
	from logistics.logistics.doctype.linked_service.linked_service import (
		get_linked_services_for_booking,
	)
	from logistics.utils.internal_job_persistence import (
		create_internal_job_for_parent_from_source,
	)

	mapping: dict[str, str] = {}
	if not source_doctype or not source_name or not dest_doctype or not dest_name:
		return mapping
	for ls in get_linked_services_for_booking(source_doctype, source_name):
		ls_name = (getattr(ls, "name", None) or "").strip()
		if not ls_name:
			continue
		mapping[ls_name] = create_internal_job_for_parent_from_source(
			dest_doctype, dest_name, ls
		)
	return mapping


def clone_linked_services_to_parent(
	source_doc: Any,
	dest_doc: Any,
	*,
	remap_charges: bool = True,
) -> dict[str, str]:
	"""Clone Linked Service documents from *source* onto *dest*; *source* retains originals."""
	dest_name = (getattr(dest_doc, "name", None) or "").strip()
	source_name = (getattr(source_doc, "name", None) or "").strip()
	if not dest_name or not source_name:
		return {}
	mapping = clone_linked_services_between_parents(
		getattr(source_doc, "doctype", None) or "",
		source_name,
		getattr(dest_doc, "doctype", None) or "",
		dest_name,
	)
	if remap_charges and mapping:
		from logistics.utils.sales_quote_one_off_internal_jobs import (
			remap_internal_job_links_on_booking_charges,
		)

		remap_internal_job_links_on_booking_charges(dest_doc, mapping)
	return mapping


def get_declaration_order_job_no_from_shipment_doc(shipment_doc: Any) -> str | None:
	"""Return linked Declaration Order name from Linked Service docs on the shipment.

	Skips cancelled Declaration Orders so the main shipment can create/link a replacement after cancel.
	"""
	parent_doctype = getattr(shipment_doc, "doctype", None) or ""
	parent_name = (getattr(shipment_doc, "name", None) or "").strip()
	if not parent_name:
		return None
	from logistics.logistics.doctype.linked_service.linked_service import (
		get_linked_services_for_booking,
	)

	for ls in get_linked_services_for_booking(parent_doctype, parent_name):
		if effective_internal_job_detail_job_type(ls) != DECLARATION_ORDER_JOB_TYPE:
			continue
		jn = (getattr(ls, "job_no", None) or "").strip()
		if not jn or not frappe.db.exists("Declaration Order", jn):
			continue
		if frappe.db.get_value("Declaration Order", jn, "docstatus") == 2:
			continue
		return jn
	return None


def _save_parent_internal_job_details(parent: Any) -> None:
	"""Persist internal job detail child rows (including after submit)."""
	parent.flags.ignore_validate_update_after_submit = True
	parent.flags.ignore_links = True
	if getattr(parent, "doctype", None) == "Docket":
		parent.flags.ignore_charges_sync = True
	# Back-reference after Create Internal Job must not run documents/milestones on_update hooks
	# while the user may still have the source shipment/booking form open.
	parent.flags.ignore_documents_milestones_populate = True
	parent.save(ignore_permissions=True)


def _persist_internal_job_detail_row_db(row: Any, job_type: str, job_no: str) -> bool:
	"""Update a saved Internal Job Detail child row without bumping parent ``modified``."""
	jn = (job_no or "").strip()
	jt = (job_type or "").strip()
	if not getattr(row, "name", None) or not jn:
		return False
	updates: dict[str, Any] = {"job_type": jt, "job_no": jn}
	st_default = _DEFAULT_SERVICE_TYPE_FOR_JOB_TYPE.get(jt)
	if st_default and hasattr(row, "service_type") and not (getattr(row, "service_type", None) or "").strip():
		updates["service_type"] = st_default
	frappe.db.set_value(row.doctype, row.name, updates, update_modified=False)
	return True


def _stamp_internal_job_link_on_target(job_type: str, job_no: str, ij_row: Any) -> None:
	"""DB-level Linked Service stamp on the just-created operational doc (no parent ``modified`` bump).

	Idempotent: only writes when the target doctype carries ``linked_service`` and/or ``internal_job``,
	the row's link is set, and the target doc's current value differs.
	"""
	jt = (job_type or "").strip()
	jn = (job_no or "").strip()
	if not jt or not jn:
		return
	from logistics.utils.linked_service_compat import row_linked_service_link

	ij_link = row_linked_service_link(ij_row)
	if not ij_link:
		return
	try:
		meta = frappe.get_meta(jt)
	except Exception:
		return
	has_linked = bool(meta.get_field("linked_service"))
	has_internal = bool(meta.get_field("internal_job"))
	if not has_linked and not has_internal:
		return
	if not frappe.db.exists(jt, jn):
		return
	read_fields = [f for f in ("linked_service", "internal_job") if meta.get_field(f)]
	cur = frappe.db.get_value(jt, jn, read_fields, as_dict=True) or {}
	current = (cur.get("linked_service") or cur.get("internal_job") or "").strip()
	if current == ij_link:
		return
	updates = {}
	if has_linked:
		updates["linked_service"] = ij_link
	if has_internal:
		updates["internal_job"] = ij_link
	try:
		frappe.db.set_value(jt, jn, updates, update_modified=False)
	except Exception:
		frappe.log_error(
			title="Internal Job link stamp failed",
			message=f"{jt} {jn} ← {ij_link}: {frappe.get_traceback()}",
		)


def _save_shipment_internal_jobs(shipment: Any) -> None:
	_save_parent_internal_job_details(shipment)


def _coerce_positive_detail_idx(value: Any) -> int | None:
	if value is None or value == "":
		return None
	try:
		i = int(value)
		return i if i > 0 else None
	except (TypeError, ValueError):
		return None


def _is_virtual_linked_service_parent(parent_doctype: str) -> bool:
	from logistics.utils.virtual_internal_job_details import VIRTUAL_INTERNAL_JOB_DETAILS_PARENTS

	return parent_doctype in (
		frozenset({"Sales Quote", "Change Request", "MICE Project", "Docket"})
		| VIRTUAL_INTERNAL_JOB_DETAILS_PARENTS
	)


def _throw_linked_service_save_required(parent_name: str) -> None:
	frappe.throw(
		_(
			"Save {0} before creating this internal job so the Linked Service line exists in the database."
		).format(parent_name),
		title=_("Save required"),
	)


def _resolve_linked_service_name_for_persist(row: Any) -> str:
	"""Resolve Linked Service name from a view dict, detail row, or Linked Service document."""
	name = row_linked_service_link(row)
	if name:
		return name
	if getattr(row, "doctype", None) == linked_service_doctype():
		return (getattr(row, "name", None) or "").strip()
	if isinstance(row, dict) and (row.get("name") or "").strip():
		# Virtual views sometimes carry the LS name as ``name`` without ``linked_service``.
		candidate = (row.get("name") or "").strip()
		if linked_service_record_exists(candidate):
			return candidate
	return ""


def persist_internal_job_detail_job_link(
	parent_doctype: str,
	parent_name: str,
	job_type: str,
	job_no: str,
	*,
	detail_idx: int | None = None,
) -> None:
	"""Set job_type + job_no on the matching Internal Job Detail row (by idx, first open line, or append).

	When the desk passes child-table JSON, resolution uses that list but we must write ``job_no`` onto
	the parent document's real child rows so ``save`` persists the back-reference. Also updates the
	linked ``Internal Job`` document because detail-row ``job_no`` is a ``fetch_from`` view of it.

	Virtual-grid parents (Docket, MICE Project, …) store legs as Linked Service documents. We always
	stamp ``job_type`` / ``job_no`` on those documents directly (after materializing if needed) and
	never parent-save — a weak desk ``linked_services`` payload would otherwise orphan-delete rows.
	"""
	jn = (job_no or "").strip()
	if not jn or not frappe.db.exists(parent_doctype, parent_name):
		return
	from logistics.utils.internal_job_persistence import (
		create_internal_job_for_parent_from_source,
		ensure_linked_service_rows_materialized,
		internal_job_detail_fieldname,
		internal_job_detail_rows_for_parent,
		sync_internal_job_doc_job_link,
	)
	from logistics.utils.linked_service_compat import linked_service_rows

	fieldname = internal_job_detail_fieldname(parent_doctype)
	if not fieldname:
		return
	meta = frappe.get_meta(parent_doctype)
	if not meta.get_field(fieldname):
		return

	parent = frappe.get_doc(parent_doctype, parent_name)
	jt = (job_type or "").strip()
	st_default = _DEFAULT_SERVICE_TYPE_FOR_JOB_TYPE.get(jt)
	virtual_parent = _is_virtual_linked_service_parent(parent_doctype)
	# Rows as seen during create (grid JSON when provided, else DB / virtual view on parent).
	form_rows = internal_job_detail_rows_for_parent(parent)

	def _refresh_canonical() -> list[Any]:
		if hasattr(parent, "_drop_virtual_linked_services_rows"):
			parent._drop_virtual_linked_services_rows()
		if virtual_parent or fieldname in ("linked_services", "internal_jobs"):
			return list(linked_service_rows(parent))
		return list(getattr(parent, fieldname, None) or [])

	canonical = _refresh_canonical()

	def _validate_form_row_job_type(src: Any, di: int) -> None:
		existing_eff = effective_internal_job_detail_job_type(src)
		if existing_eff and existing_eff != jt:
			frappe.throw(
				_("Internal Job Detail row {0} is for {1}, not {2}.").format(di, existing_eff, jt)
			)

	def _sync_linked_service_row(src: Any) -> None:
		ls_name = _resolve_linked_service_name_for_persist(src)
		if not ls_name:
			return
		sync_row = frappe._dict({"linked_service": ls_name, "internal_job": ls_name})
		sync_internal_job_doc_job_link(sync_row, jt, jn)
		_stamp_internal_job_link_on_target(jt, jn, sync_row)

	def _apply_to_canonical_row(target: Any, di: int) -> None:
		src = form_rows[di - 1] if 0 < di <= len(form_rows) else target
		_validate_form_row_job_type(src, di)
		target.job_type = jt
		target.job_no = jn
		if st_default and hasattr(target, "service_type") and not (getattr(target, "service_type", None) or "").strip():
			target.service_type = st_default

	def _commit_virtual_row_link(target: Any, di: int) -> None:
		"""Stamp job_no on the Linked Service doc only — never parent-save virtual grids."""
		src = form_rows[di - 1] if 0 < di <= len(form_rows) else target
		_validate_form_row_job_type(src, di)
		ls_name = _resolve_linked_service_name_for_persist(src) or _resolve_linked_service_name_for_persist(
			target
		)
		if not ls_name:
			ensure_linked_service_rows_materialized(parent)
			rows_after = _refresh_canonical()
			if di > len(rows_after):
				_throw_linked_service_save_required(parent_name)
			target = rows_after[di - 1]
			ls_name = _resolve_linked_service_name_for_persist(target)
		if not ls_name:
			_throw_linked_service_save_required(parent_name)
		sync_row = frappe._dict({"linked_service": ls_name, "internal_job": ls_name})
		sync_internal_job_doc_job_link(sync_row, jt, jn)
		_stamp_internal_job_link_on_target(jt, jn, sync_row)

	def _commit_row_link(target: Any, di: int) -> None:
		if virtual_parent:
			_commit_virtual_row_link(target, di)
			return
		_apply_to_canonical_row(target, di)
		if not row_linked_service_link(target):
			_save_parent_internal_job_details(parent)
			parent.reload()
			rows_after = _refresh_canonical()
			if di > len(rows_after):
				return
			target = rows_after[di - 1]
			_apply_to_canonical_row(target, di)
		sync_internal_job_doc_job_link(target, jt, jn)
		if not _persist_internal_job_detail_row_db(target, jt, jn):
			_save_parent_internal_job_details(parent)
		# Stamp the canonical Internal Job link onto the newly-created operational doc so the
		# Booking/Order form shows it immediately (matches the apply path via
		# ``apply_internal_job_detail_row_to_operational_doc`` and covers create flows that
		# bypass that helper).
		_stamp_internal_job_link_on_target(jt, jn, target)

	def _ensure_canonical_has_row(di: int) -> list[Any]:
		nonlocal canonical
		if di <= len(canonical):
			return canonical
		ensure_linked_service_rows_materialized(parent)
		canonical = _refresh_canonical()
		return canonical

	di = _coerce_positive_detail_idx(detail_idx)
	if di is not None:
		if di < 1 or di > len(form_rows):
			frappe.throw(_("Invalid Internal Job Detail row index for persist."))
		src = form_rows[di - 1]
		if virtual_parent and _resolve_linked_service_name_for_persist(src):
			_validate_form_row_job_type(src, di)
			_sync_linked_service_row(src)
			return
		canonical = _ensure_canonical_has_row(di)
		if di > len(canonical):
			_throw_linked_service_save_required(parent_name)
		_commit_row_link(canonical[di - 1], di)
		return

	for i, src in enumerate(form_rows):
		if effective_internal_job_detail_job_type(src) != jt:
			continue
		if (getattr(src, "job_no", None) or "").strip():
			continue
		di_open = i + 1
		if virtual_parent and _resolve_linked_service_name_for_persist(src):
			_sync_linked_service_row(src)
			return
		canonical = _ensure_canonical_has_row(di_open)
		if di_open > len(canonical):
			_throw_linked_service_save_required(parent_name)
		_commit_row_link(canonical[di_open - 1], di_open)
		return

	new_row: dict[str, Any] = {"job_type": jt, "job_no": jn}
	if st_default:
		new_row["service_type"] = st_default
	if virtual_parent:
		ls_name = create_internal_job_for_parent_from_source(parent_doctype, parent_name, new_row)
		sync_row = frappe._dict({"linked_service": ls_name, "internal_job": ls_name})
		sync_internal_job_doc_job_link(sync_row, jt, jn)
		_stamp_internal_job_link_on_target(jt, jn, sync_row)
		return
	parent.append(fieldname, new_row)
	_save_parent_internal_job_details(parent)


def _internal_job_detail_row_open_for_declaration_order_link(row: Any) -> bool:
	"""True if this Internal Job line can receive a new Declaration Order link without overwriting an active order."""
	if effective_internal_job_detail_job_type(row) != DECLARATION_ORDER_JOB_TYPE:
		return False
	jn = (getattr(row, "job_no", None) or "").strip()
	if not jn:
		return True
	if not frappe.db.exists("Declaration Order", jn):
		return True
	return int(frappe.db.get_value("Declaration Order", jn, "docstatus") or 0) == 2


def link_declaration_order_on_shipment(
	shipment_doctype: str, shipment_name: str, declaration_order_name: str
) -> None:
	"""Set job_no on the shipment's Customs Linked Service for this Declaration Order."""
	if not declaration_order_name or not frappe.db.exists("Declaration Order", declaration_order_name):
		return
	from logistics.logistics.doctype.linked_service.linked_service import (
		get_linked_services_for_booking,
	)
	from logistics.utils.internal_job_persistence import sync_internal_job_doc_job_link

	for ls in get_linked_services_for_booking(shipment_doctype, shipment_name):
		if not _internal_job_detail_row_open_for_declaration_order_link(ls):
			continue
		sync_internal_job_doc_job_link(ls, DECLARATION_ORDER_JOB_TYPE, declaration_order_name)
		return

	parent = frappe.get_doc(shipment_doctype, shipment_name)
	new_name = frappe.db.get_value(
		linked_service_doctype(),
		{
			"parent_booking_type": shipment_doctype,
			"parent_booking_name": shipment_name,
			"service_type": "Customs",
			"job_type": DECLARATION_ORDER_JOB_TYPE,
		},
		"name",
	)
	if new_name:
		ls = frappe.get_doc(linked_service_doctype(), new_name)
		sync_internal_job_doc_job_link(ls, DECLARATION_ORDER_JOB_TYPE, declaration_order_name)
		return
	from logistics.utils.internal_job_persistence import _create_internal_job_from_row

	row = frappe._dict(
		service_type="Customs",
		job_type=DECLARATION_ORDER_JOB_TYPE,
		job_no=declaration_order_name,
	)
	ij_name = _create_internal_job_from_row(parent, row)
	sync_internal_job_doc_job_link(
		frappe._dict(linked_service=ij_name, internal_job=ij_name),
		DECLARATION_ORDER_JOB_TYPE,
		declaration_order_name,
	)


def unlink_declaration_order_from_shipment(
	shipment_doctype: str,
	shipment_name: str,
	declaration_order_name: str,
) -> None:
	"""Clear Declaration Order job_no on the shipment's matching Linked Service."""
	if not (declaration_order_name or "").strip():
		return
	from logistics.logistics.doctype.linked_service.linked_service import (
		get_linked_services_for_booking,
	)

	do_name = declaration_order_name.strip()
	ls_dt = linked_service_doctype()
	for ls in get_linked_services_for_booking(shipment_doctype, shipment_name):
		if (getattr(ls, "job_type", None) or "").strip() != DECLARATION_ORDER_JOB_TYPE:
			continue
		jn = (getattr(ls, "job_no", None) or "").strip()
		if jn != do_name:
			continue
		frappe.db.set_value(ls_dt, ls.name, {"job_no": "", "job_type": DECLARATION_ORDER_JOB_TYPE}, update_modified=False)
		return


def unlink_declaration_order_from_internal_job_parent_documents(
	declaration_order_name: str,
	order_doc: Any,
	*,
	preserve_internal_job_rows: bool = False,
) -> None:
	"""Clear or remove Internal Job Detail references to this Declaration Order on linked operational parents.

	When ``preserve_internal_job_rows`` is True (Declaration Order **cancel**), rows that pointed at this
	order are left in place so users still see which line was tied to the cancelled order.

	When False (**delete**), matching rows are removed so parents do not keep links to a non-existent document.

	Parents may be linked via ``air_shipment`` / ``sea_shipment`` (freight flow) and/or
	``main_service`` / ``main_service_type`` (e.g. linked-service orders from Transport Job).
	"""
	from logistics.utils.service_role_rules import get_main_service_name, get_main_service_type

	dco = (declaration_order_name or "").strip()
	if not dco:
		return
	if preserve_internal_job_rows:
		return
	targets: list[tuple[str, str]] = []
	for fn, dt in (("air_shipment", "Air Shipment"), ("sea_shipment", "Sea Shipment")):
		nm = (getattr(order_doc, fn, None) or "").strip()
		if nm:
			targets.append((dt, nm))
	mjt = get_main_service_type(order_doc)
	mj = get_main_service_name(order_doc)
	if mj and mjt in ("Air Shipment", "Sea Shipment", "Transport Job"):
		targets.append((mjt, mj))
	seen: set[tuple[str, str]] = set()
	for dt, nm in targets:
		key = (dt, nm)
		if key in seen:
			continue
		seen.add(key)
		if frappe.db.exists(dt, nm):
			unlink_declaration_order_from_shipment(dt, nm, dco)
