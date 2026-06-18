# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Packages ledger and delivery helpers for Special Project.

A Package row is the canonical declaration of an item/part the customer expects
to be delivered for the project. Deliveries (stored on the parent's ``deliveries``
table, a.k.a. ``Special Project Site Receipt``) record how much of each package
has actually been received on site, tagged by lifecycle stage.
"""

from __future__ import annotations

import json
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, flt, getdate, today

from logistics.utils.internal_job_from_source import _child_doctype_for_table_field

POSTED_RECEIPT_STATUS = "Posted"
CANCELLED_RECEIPT_STATUS = "Cancelled"

_DELIVERY_COMPARE_DATE_FIELDS = frozenset({"receipt_date"})
_DELIVERY_COMPARE_FLOAT_FIELDS = frozenset({"qty_received", "package_row"})

DEFAULT_RECEIPT_LIFECYCLE_STAGE = "Logistics"

# Execution documents that may post delivery receipts (planning orders/bookings excluded).
PACKAGE_RECEIPT_TRANSPORT_DOCTYPES = frozenset({"Transport Job"})
PACKAGE_RECEIPT_FREIGHT_SHIPMENT_DOCTYPES = frozenset({"Air Shipment", "Sea Shipment"})
PACKAGE_RECEIPT_PROJECT_JOB_DOCTYPES = frozenset({"Project Job"})


def _stage_from_lifecycle_job(sp_doc: Any, job_type: str, job_no: str) -> str | None:
	"""Find the originating Lifecycle Job row on the Special Project and return its stage."""
	job_type = _norm(job_type)
	job_no = _norm(job_no)
	if not job_no:
		return None
	for row in getattr(sp_doc, "lifecycle_jobs", None) or []:
		row_job_type = _norm(getattr(row, "job_type", None))
		row_job_no = _norm(getattr(row, "job_no", None))
		row_order_no = _norm(getattr(row, "order_no", None))
		matched = False
		if row_job_no and row_job_no == job_no:
			# Execution ref (Transport Job, Shipment, Project Job, …).
			matched = True
		elif job_type and row_job_type == job_type and (
			row_order_no == job_no or row_job_no == job_no
		):
			# Planning order ref (Transport Order, Air Booking, …).
			matched = True
		if matched:
			stage = _norm(getattr(row, "lifecycle_stage", None))
			if stage:
				return stage
	return None


def _default_receipt_stage(
	sp_doc: Any,
	job_type: str | None = None,
	job_no: str | None = None,
	*,
	fallback_refs: list[tuple[str, str]] | None = None,
) -> str | None:
	"""Pick a sensible lifecycle_stage for a new delivery receipt.

	Priority: originating Lifecycle Job's stage -> any ``fallback_refs`` (e.g. the
	Air/Sea Booking that spawned this Shipment) -> Special Project's current stage
	-> module default ("Logistics"). Returns None if Lifecycle Stage master is empty.
	"""
	stage = _stage_from_lifecycle_job(sp_doc, job_type or "", job_no or "")
	if stage and frappe.db.exists("Lifecycle Stage", stage):
		return stage
	for ref_type, ref_name in fallback_refs or []:
		fallback = _stage_from_lifecycle_job(sp_doc, ref_type or "", ref_name or "")
		if fallback and frappe.db.exists("Lifecycle Stage", fallback):
			return fallback
	current = _norm(getattr(sp_doc, "lifecycle_stage", None))
	if current and frappe.db.exists("Lifecycle Stage", current):
		return current
	if frappe.db.exists("Lifecycle Stage", DEFAULT_RECEIPT_LIFECYCLE_STAGE):
		return DEFAULT_RECEIPT_LIFECYCLE_STAGE
	return None


def lifecycle_stages_for_special_project() -> list[dict[str, Any]]:
	"""Return Lifecycle Stage rows applicable to Special Project in display order."""
	stages = frappe.get_all(
		"Lifecycle Stage",
		filters={"for_special_project": 1},
		fields=["name", "sort_order", "is_closed", "description"],
		order_by="sort_order asc, name asc",
	)
	return stages


def resolve_special_project_from_project(project: str | None) -> str | None:
	"""Map ERPNext Project id or Special Project name to Special Project document name."""
	project = (project or "").strip()
	if not project:
		return None
	if frappe.db.exists("Special Project", project):
		return project
	name = frappe.db.get_value("Special Project", {"project": project}, "name")
	return name or None


def _norm(value: Any) -> str:
	return (value or "").strip()


def _norm_desc(value: Any) -> str:
	return _norm(value).lower()


def _posted_deliveries(sp_doc: Any) -> list[Any]:
	return [
		r
		for r in (getattr(sp_doc, "deliveries", None) or [])
		if (getattr(r, "status", None) or POSTED_RECEIPT_STATUS) == POSTED_RECEIPT_STATUS
		and flt(getattr(r, "qty_received", 0)) > 0
	]


def _tracked_package_rows(sp_doc: Any) -> list[Any]:
	return [
		pkg
		for pkg in getattr(sp_doc, "packages", None) or []
		if not cint_safe(getattr(pkg, "include_on_create", 0))
	]


def _package_row_index_maps(sp_doc: Any) -> tuple[
	dict[str, list[int]], dict[str, list[int]], dict[str, list[int]]
]:
	"""Map warehouse_item / commodity / normalized description to tracked package idx lists."""
	wh_map: dict[str, list[int]] = {}
	commodity_map: dict[str, list[int]] = {}
	desc_map: dict[str, list[int]] = {}
	for pkg in _tracked_package_rows(sp_doc):
		idx = cint_safe(getattr(pkg, "idx", None))
		if not idx:
			continue
		wh = _norm(getattr(pkg, "warehouse_item", None))
		if wh:
			wh_map.setdefault(wh, []).append(idx)
		commodity = _norm(getattr(pkg, "commodity", None))
		if commodity:
			commodity_map.setdefault(commodity, []).append(idx)
		desc = _norm_desc(getattr(pkg, "description", None))
		if desc:
			desc_map.setdefault(desc, []).append(idx)
	return wh_map, commodity_map, desc_map


def sync_package_delivery_balances(sp_doc: Any) -> None:
	"""Recompute qty_on_site and qty_short on each package row from posted deliveries.

	Rows where include_on_create is ticked are off-ledger always-along packages and
	stay at qty_on_site = qty_short = 0.
	"""
	packages = getattr(sp_doc, "packages", None) or []
	if not packages:
		return

	wh_map, commodity_map, desc_map = _package_row_index_maps(sp_doc)
	totals_by_row: dict[int, float] = {}
	totals_by_warehouse_item: dict[str, float] = {}
	totals_by_commodity: dict[str, float] = {}
	totals_by_desc: dict[str, float] = {}

	for rc in _posted_deliveries(sp_doc):
		qty = flt(getattr(rc, "qty_received", 0))
		row_idx = cint_safe(getattr(rc, "package_row", None))
		if row_idx:
			totals_by_row[row_idx] = totals_by_row.get(row_idx, 0) + qty
			continue
		wh = _norm(getattr(rc, "warehouse_item", None))
		if wh and len(wh_map.get(wh, [])) == 1:
			totals_by_warehouse_item[wh] = totals_by_warehouse_item.get(wh, 0) + qty
			continue
		commodity = _norm(getattr(rc, "commodity", None))
		if commodity and len(commodity_map.get(commodity, [])) == 1:
			totals_by_commodity[commodity] = (
				totals_by_commodity.get(commodity, 0) + qty
			)
			continue
		desc = _norm_desc(getattr(rc, "description", None))
		if desc and len(desc_map.get(desc, [])) == 1:
			totals_by_desc[desc] = totals_by_desc.get(desc, 0) + qty

	for pkg in packages:
		if cint_safe(getattr(pkg, "include_on_create", 0)):
			pkg.qty_on_site = 0
			pkg.qty_short = 0
			continue
		idx = cint_safe(getattr(pkg, "idx", None))
		on_site = flt(totals_by_row.get(idx, 0))
		if not on_site:
			wh = _norm(getattr(pkg, "warehouse_item", None))
			if wh and len(wh_map.get(wh, [])) == 1:
				on_site = flt(totals_by_warehouse_item.get(wh, 0))
			if not on_site:
				commodity = _norm(getattr(pkg, "commodity", None))
				if commodity and len(commodity_map.get(commodity, [])) == 1:
					on_site = flt(totals_by_commodity.get(commodity, 0))
			if not on_site:
				desc = _norm_desc(getattr(pkg, "description", None))
				if desc and len(desc_map.get(desc, [])) == 1:
					on_site = flt(totals_by_desc.get(desc, 0))
		required = flt(getattr(pkg, "qty_required", 0))
		pkg.qty_on_site = on_site
		pkg.qty_short = max(required - on_site, 0)


def autofill_delivery_lifecycle_stages(sp_doc: Any) -> None:
	"""Set lifecycle_stage on posted deliveries when missing (system default, not user input)."""
	fallback_stage = _default_receipt_stage(sp_doc)
	for rc in getattr(sp_doc, "deliveries", None) or []:
		if flt(getattr(rc, "qty_received", 0)) <= 0:
			continue
		if _norm(getattr(rc, "lifecycle_stage", None)):
			continue
		job_type = _norm(getattr(rc, "source_job_type", None))
		job_no = _norm(getattr(rc, "source_job_no", None))
		stage = _default_receipt_stage(sp_doc, job_type, job_no) or fallback_stage
		if stage:
			rc.lifecycle_stage = stage


def _receipt_matches_source(rc: Any, source_doctype: str, source_name: str) -> bool:
	"""True when a delivery row was posted from the given operational document."""
	source_doctype = _norm(source_doctype)
	source_name = _norm(source_name)
	if not source_doctype or not source_name:
		return False
	if (
		_norm(getattr(rc, "source_doctype", None)) == source_doctype
		and _norm(getattr(rc, "source_name", None)) == source_name
	):
		return True
	return (
		_norm(getattr(rc, "source_job_type", None)) == source_doctype
		and _norm(getattr(rc, "source_job_no", None)) == source_name
	)


def _source_job_is_cancelled(doctype: str, docname: str) -> bool:
	if not doctype or not docname or not frappe.db.exists(doctype, docname):
		return False
	return cint(frappe.db.get_value(doctype, docname, "docstatus")) == 2


def _delivery_fields_equal(old: Any, row: Any, fieldname: str) -> bool:
	old_val = getattr(old, fieldname, None)
	new_val = getattr(row, fieldname, None)
	if fieldname in _DELIVERY_COMPARE_DATE_FIELDS:
		if not old_val and not new_val:
			return True
		return getdate(old_val) == getdate(new_val)
	if fieldname in _DELIVERY_COMPARE_FLOAT_FIELDS:
		return flt(old_val) == flt(new_val)
	return (old_val or "") == (new_val or "")


def _resolve_delivery_source(row: Any | None) -> tuple[str, str] | None:
	"""Return (doctype, name) for the operational job that posted a delivery row."""
	if not row:
		return None
	job_type = _norm(getattr(row, "source_job_type", None))
	job_no = _norm(getattr(row, "source_job_no", None))
	if job_type and job_no:
		return job_type, job_no
	src_dt = _norm(getattr(row, "source_doctype", None))
	src_name = _norm(getattr(row, "source_name", None))
	if src_dt and src_name:
		return src_dt, src_name
	return None


def _delivery_field_label(fieldname: str) -> str:
	return frappe.get_meta("Special Project Site Receipt").get_label(fieldname) or fieldname


def _open_source_job_primary_action(doctype: str, docname: str) -> dict[str, Any]:
	return {
		"label": _("Open {0}").format(doctype),
		"client_action": "logistics.special_project_modals.open_source_job",
		"args": {"doctype": doctype, "docname": docname},
		"hide_on_success": True,
	}


def _view_fulfillment_primary_action() -> dict[str, Any]:
	return {
		"label": _("View Fulfillment"),
		"client_action": "logistics.special_project_modals.go_to_tab",
		"args": {"fieldname": "fulfillment_tab"},
		"hide_on_success": True,
	}


def _throw_deliveries_read_only(
	*,
	row: Any | None = None,
	changed_field: str | None = None,
	rows_added_or_removed: bool = False,
	manual_on_create: bool = False,
) -> None:
	"""Raise a validation error with an optional button to open the source job."""
	kwargs: dict[str, Any] = {"title": _("Deliveries")}
	source = _resolve_delivery_source(row)

	if manual_on_create:
		msg = _(
			"Deliveries are posted automatically from operational jobs. "
			"You cannot add delivery rows manually on Special Project."
		)
		kwargs["primary_action"] = _view_fulfillment_primary_action()
	elif rows_added_or_removed:
		if source:
			doctype, docname = source
			msg = _(
				"Deliveries are read-only on Special Project. "
				"Post or cancel deliveries from source document {0} {1}."
			).format(doctype, docname)
			kwargs["primary_action"] = _open_source_job_primary_action(doctype, docname)
		else:
			msg = _(
				"Deliveries are read-only on Special Project. "
				"Post or cancel deliveries from the source Transport Job, Shipment, or Project Job."
			)
			kwargs["primary_action"] = _view_fulfillment_primary_action()
	elif source:
		doctype, docname = source
		if _source_job_is_cancelled(doctype, docname):
			if changed_field:
				field_label = _delivery_field_label(changed_field)
				msg = _(
					"Delivery for cancelled {0} {1} was not synced ({2}). "
					"Reload this Special Project or contact support."
				).format(doctype, docname, field_label)
			else:
				msg = _(
					"Delivery for cancelled {0} {1} was not synced. "
					"Reload this Special Project or contact support."
				).format(doctype, docname)
			kwargs["primary_action"] = _view_fulfillment_primary_action()
		elif changed_field:
			field_label = _delivery_field_label(changed_field)
			msg = _(
				"Delivery for {0} {1} was changed ({2}). "
				"Open that document to amend or cancel the receipt."
			).format(doctype, docname, field_label)
			kwargs["primary_action"] = _open_source_job_primary_action(doctype, docname)
		else:
			msg = _(
				"Delivery for {0} {1} was changed. "
				"Open that document to amend or cancel the receipt."
			).format(doctype, docname)
			kwargs["primary_action"] = _open_source_job_primary_action(doctype, docname)
	else:
		msg = _(
			"Deliveries are read-only on Special Project. "
			"Amend the source job to change posted receipts."
		)
		kwargs["primary_action"] = _view_fulfillment_primary_action()

	frappe.throw(msg, **kwargs)


def validate_deliveries_read_only(sp_doc: Any) -> None:
	"""Block manual add/edit/delete of delivery rows on the Special Project form."""
	if sp_doc.flags.get("ignore_delivery_validation"):
		return
	if getattr(sp_doc, "__islocal", False):
		if sp_doc.get("deliveries"):
			_throw_deliveries_read_only(manual_on_create=True)
		return

	before = sp_doc.get_doc_before_save()
	if before is None:
		return

	before_by_name = {r.name: r for r in before.get("deliveries") or [] if getattr(r, "name", None)}
	after_rows = sp_doc.get("deliveries") or []
	after_by_name = {r.name: r for r in after_rows if getattr(r, "name", None)}

	if set(before_by_name.keys()) != set(after_by_name.keys()):
		added = set(after_by_name.keys()) - set(before_by_name.keys())
		removed = set(before_by_name.keys()) - set(after_by_name.keys())
		row = None
		if added:
			row = after_by_name[next(iter(added))]
		elif removed:
			row = before_by_name[next(iter(removed))]
		_throw_deliveries_read_only(row=row, rows_added_or_removed=True)

	compare_fields = (
		"package_row",
		"commodity",
		"warehouse_item",
		"description",
		"qty_received",
		"uom",
		"receipt_date",
		"lifecycle_stage",
		"status",
		"source_job_type",
		"source_job_no",
		"container_no",
	)
	for name, row in after_by_name.items():
		old = before_by_name.get(name)
		if not old:
			continue
		if (getattr(old, "status", None) or "") == CANCELLED_RECEIPT_STATUS:
			continue
		for fn in compare_fields:
			if not _delivery_fields_equal(old, row, fn):
				_throw_deliveries_read_only(row=row, changed_field=fn)


def validate_packages(sp_doc: Any) -> None:
	"""Validate package lines and delivery receipt idempotency keys."""
	packages = getattr(sp_doc, "packages", None) or []
	for i, pkg in enumerate(packages, start=1):
		wh = _norm(getattr(pkg, "warehouse_item", None))
		commodity = _norm(getattr(pkg, "commodity", None))
		desc = _norm(getattr(pkg, "description", None))
		if not wh and not commodity and not desc:
			frappe.throw(
				_("Packages row {0}: enter Warehouse Item, Commodity, or Description.").format(i),
				title=_("Packages"),
			)
		if flt(getattr(pkg, "qty_required", 0)) <= 0:
			frappe.throw(
				_("Packages row {0}: Qty Required must be greater than zero.").format(i),
				title=_("Packages"),
			)

	seen_idem: set[tuple[str, str, int]] = set()
	for j, rc in enumerate(getattr(sp_doc, "deliveries", None) or [], start=1):
		if flt(getattr(rc, "qty_received", 0)) <= 0:
			continue
		src_dt = _norm(getattr(rc, "source_doctype", None))
		src_name = _norm(getattr(rc, "source_name", None))
		src_idx = cint_safe(getattr(rc, "source_package_idx", None))
		if src_dt and src_name:
			key = (src_dt, src_name, src_idx)
			if key in seen_idem:
				frappe.throw(
					_("Deliveries row {0}: duplicate source {1} {2} package {3}.").format(
						j, src_dt, src_name, src_idx
					),
					title=_("Packages"),
				)
			seen_idem.add(key)

	sync_package_delivery_balances(sp_doc)

	for pkg in packages:
		if cint_safe(getattr(pkg, "include_on_create", 0)):
			continue
		if flt(getattr(pkg, "qty_on_site", 0)) > flt(getattr(pkg, "qty_required", 0)):
			label = package_label(pkg)
			frappe.msgprint(
				_("Package {0}: delivered quantity exceeds required quantity.").format(label),
				indicator="orange",
				title=_("Packages"),
			)


def package_label(pkg: Any) -> str:
	wh = _norm(getattr(pkg, "warehouse_item", None))
	if wh:
		name = frappe.db.get_value("Warehouse Item", wh, "item_name")
		return name or wh
	commodity = _norm(getattr(pkg, "commodity", None))
	if commodity:
		return commodity
	return _norm(getattr(pkg, "description", None)) or _("line")


def _append_child_row(sp_doc: Any, table_field: str, row: dict[str, Any]) -> None:
	append_fn = getattr(sp_doc, "append", None)
	if callable(append_fn):
		append_fn(table_field, row)
		return
	rows = getattr(sp_doc, table_field, None)
	if rows is None:
		setattr(sp_doc, table_field, [])
		rows = getattr(sp_doc, table_field)
	rows.append(frappe._dict(row))


def cint_safe(value: Any) -> int:
	try:
		return int(value) if value not in (None, "") else 0
	except (TypeError, ValueError):
		return 0


def _find_package_row(
	sp_doc: Any,
	*,
	warehouse_item: str | None = None,
	commodity: str | None = None,
	description: str | None = None,
) -> Any | None:
	matches = _find_all_tracked_package_rows(
		sp_doc,
		warehouse_item=warehouse_item,
		commodity=commodity,
		description=description,
	)
	return matches[0] if len(matches) == 1 else None


def _find_all_tracked_package_rows(
	sp_doc: Any,
	*,
	warehouse_item: str | None = None,
	commodity: str | None = None,
	description: str | None = None,
) -> list[Any]:
	"""Return tracked package rows matching identification fields (may be multiple)."""
	warehouse_item = _norm(warehouse_item)
	commodity = _norm(commodity)
	description = _norm(description)
	matches: list[Any] = []
	for pkg in _tracked_package_rows(sp_doc):
		if warehouse_item and _norm(getattr(pkg, "warehouse_item", None)) == warehouse_item:
			matches.append(pkg)
		elif commodity and _norm(getattr(pkg, "commodity", None)) == commodity:
			matches.append(pkg)
		elif description and not warehouse_item and not commodity:
			if _norm(getattr(pkg, "description", None)).lower() == description.lower():
				matches.append(pkg)
	return matches


def _operational_line_label(
	*,
	warehouse_item: str | None = None,
	commodity: str | None = None,
	description: str | None = None,
) -> str:
	return (
		warehouse_item
		or commodity
		or description
		or _("package line")
	)


def _resolve_sp_package_for_operational_line(
	sp_doc: Any, pkg: Any
) -> tuple[Any | None, int]:
	"""Resolve a Special Project package row for an operational document package line.

	Returns ``(package_row_doc, 1-based package_row index)``. Raises when multiple
	tracked rows match and ``package_row`` is not set on the operational line.
	"""
	packages = getattr(sp_doc, "packages", None) or []
	explicit_row = cint_safe(getattr(pkg, "package_row", None))
	if explicit_row and 1 <= explicit_row <= len(packages):
		mat = packages[explicit_row - 1]
		if cint_safe(getattr(mat, "include_on_create", 0)):
			return None, 0
		return mat, explicit_row

	wh = _norm(getattr(pkg, "warehouse_item", None))
	commodity = _norm(getattr(pkg, "commodity", None))
	desc = _package_description(pkg) or _norm(getattr(pkg, "description", None))
	matches = _find_all_tracked_package_rows(
		sp_doc, warehouse_item=wh, commodity=commodity, description=desc
	)
	if len(matches) == 1:
		mat = matches[0]
		return mat, cint_safe(getattr(mat, "idx", None))
	if len(matches) > 1:
		label = _operational_line_label(
			warehouse_item=wh, commodity=commodity, description=desc
		)
		frappe.throw(
			_(
				"Multiple Packages lines match {0}. Set Package Row on the operational "
				"document package line, or recreate the booking from Shipment lines on "
				"the Special Project."
			).format(label),
			title=_("Ambiguous package line"),
		)
	return None, 0


def _warehouse_item_for_sales_quote_product(sp_doc: Any, item: str) -> str | None:
	"""Best-effort Warehouse Item lookup from Sales Quote ERPNext Item."""
	cust = _norm(getattr(sp_doc, "customer", None))
	item = _norm(item)
	if not cust or not item:
		return None
	for filters in (
		{"customer": cust, "code": item},
		{"customer": cust, "customer_code": item},
	):
		name = frappe.db.get_value("Warehouse Item", filters, "name", order_by="modified desc")
		if name:
			return name
	return None


def seed_packages_from_sales_quote(sp_doc: Any, sales_quote: Any, *, clear_existing: bool = False) -> int:
	"""Copy Sales Quote project_products into packages requirement rows."""
	products = getattr(sales_quote, "project_products", None) or []
	if not products:
		return 0
	if clear_existing:
		sp_doc.set("packages", [])

	existing_wh = {
		_norm(getattr(m, "warehouse_item", None))
		for m in (getattr(sp_doc, "packages", None) or [])
		if _norm(getattr(m, "warehouse_item", None))
	}
	added = 0
	for row in products:
		item = _norm(getattr(row, "item", None))
		desc = _norm(getattr(row, "description", None))
		if not item and not desc:
			continue
		wh = _warehouse_item_for_sales_quote_product(sp_doc, item) if item else None
		if wh and wh in existing_wh:
			continue
		if not wh and not desc and item:
			desc = frappe.db.get_value("Item", item, "item_name") or item
		_append_child_row(
			sp_doc,
			"packages",
			{
				"warehouse_item": wh,
				"description": desc or None,
				"qty_required": flt(getattr(row, "quantity", 0)) or 0,
				"uom": getattr(row, "uom", None),
				"sales_quote_product_row": getattr(row, "name", None),
			},
		)
		if wh:
			existing_wh.add(wh)
		added += 1
	return added


def _parse_shipment_lines(shipment_lines: Any) -> list[dict[str, Any]]:
	if shipment_lines is None or shipment_lines == "":
		return []
	if isinstance(shipment_lines, str):
		try:
			shipment_lines = json.loads(shipment_lines)
		except Exception:
			return []
	if not isinstance(shipment_lines, list):
		return []
	out: list[dict[str, Any]] = []
	for row in shipment_lines:
		if isinstance(row, dict):
			out.append(row)
		elif hasattr(row, "__dict__"):
			out.append(dict(row))
	return out


_PACKAGE_DETAIL_FIELDS: tuple[str, ...] = (
	"hs_code",
	"reference_no",
	"no_of_packs",
	"length",
	"width",
	"height",
	"dimension_uom",
	"weight",
	"weight_uom",
	"volume",
	"volume_uom",
	"contains_dangerous_goods",
)


def _package_row_dict(sp_doc: Any, row_idx: int) -> dict[str, Any] | None:
	packages = getattr(sp_doc, "packages", None) or []
	if row_idx < 1 or row_idx > len(packages):
		return None
	pkg = packages[row_idx - 1]
	out: dict[str, Any] = {
		"package_row": row_idx,
		"commodity": getattr(pkg, "commodity", None),
		"warehouse_item": getattr(pkg, "warehouse_item", None),
		"description": getattr(pkg, "description", None),
		"uom": getattr(pkg, "uom", None),
		"qty_required": flt(getattr(pkg, "qty_required", 0)),
		"qty_on_site": flt(getattr(pkg, "qty_on_site", 0)),
		"qty_short": flt(getattr(pkg, "qty_short", 0)),
	}
	for fn in _PACKAGE_DETAIL_FIELDS:
		out[fn] = getattr(pkg, fn, None)
	return out


def apply_shipment_lines_to_target(
	sp_doc: Any,
	target_doc: Any,
	shipment_lines: Any,
) -> int:
	"""Append package rows from Booking/Order dialog picks onto a target document."""
	lines = _parse_shipment_lines(shipment_lines)
	if not lines:
		return 0
	child_dt = _child_doctype_for_table_field(target_doc.doctype, "packages")
	if not child_dt:
		return 0
	meta = frappe.get_meta(child_dt)
	count = 0
	for line in lines:
		qty = flt(line.get("qty") or line.get("quantity") or 0)
		if qty <= 0:
			continue
		row_idx = cint_safe(line.get("package_row") or line.get("site_material_row"))
		pkg_info = _package_row_dict(sp_doc, row_idx) if row_idx else {}
		pkg_info = pkg_info or {}
		remaining = flt(pkg_info.get("qty_short", 0))
		if row_idx and qty > remaining:
			label = (
				pkg_info.get("description")
				or pkg_info.get("commodity")
				or pkg_info.get("warehouse_item")
				or _("Line {0}").format(row_idx)
			)
			frappe.throw(
				_("Cannot ship {0} of {1} — only {2} remaining to deliver.").format(
					qty, label, remaining
				)
			)
		wh = _norm(line.get("warehouse_item") or pkg_info.get("warehouse_item"))
		commodity = _norm(line.get("commodity") or pkg_info.get("commodity"))
		desc = _norm(line.get("description") or pkg_info.get("description"))
		row_dict: dict[str, Any] = {}
		if meta.get_field("quantity"):
			row_dict["quantity"] = qty
		elif meta.get_field("no_of_packs"):
			row_dict["no_of_packs"] = qty
		if wh and meta.get_field("warehouse_item"):
			row_dict["warehouse_item"] = wh
		if commodity and meta.get_field("commodity"):
			row_dict["commodity"] = commodity
		if desc and meta.get_field("description"):
			row_dict["description"] = desc
		elif wh and meta.get_field("description"):
			row_dict["description"] = (
				frappe.db.get_value("Warehouse Item", wh, "item_name") or wh
			)
		uom = line.get("uom") or pkg_info.get("uom")
		if uom and meta.get_field("uom"):
			row_dict["uom"] = uom
		if row_idx and meta.get_field("package_row"):
			row_dict["package_row"] = row_idx
		for fn in _PACKAGE_DETAIL_FIELDS:
			value = line.get(fn) if isinstance(line, dict) else None
			if value in (None, "", 0, 0.0):
				value = pkg_info.get(fn)
			if value in (None, "", 0, 0.0):
				continue
			if meta.get_field(fn):
				row_dict[fn] = value
		if row_dict:
			target_doc.append("packages", row_dict)
			count += 1
	return count


def copy_always_along_packages_to_target(sp_doc: Any, target_doc: Any) -> int:
	"""Append always-along package rows (include_on_create=1) onto target packages table.

	These rows are hidden from the Shipment Lines dialog, so there is no dedupe to perform.
	"""
	packages = getattr(sp_doc, "packages", None) or []
	rows = [m for m in packages if cint_safe(getattr(m, "include_on_create", 0))]
	if not rows:
		return 0
	child_dt = _child_doctype_for_table_field(target_doc.doctype, "packages")
	if not child_dt:
		return 0
	meta = frappe.get_meta(child_dt)
	count = 0
	for pkg in rows:
		qty = flt(getattr(pkg, "no_of_packs", 0)) or flt(getattr(pkg, "qty_required", 0))
		if qty <= 0:
			qty = 1
		row_dict: dict[str, Any] = {}
		if meta.get_field("quantity"):
			row_dict["quantity"] = qty
		elif meta.get_field("no_of_packs"):
			row_dict["no_of_packs"] = qty
		for fn in ("warehouse_item", "commodity", "description", "uom"):
			value = getattr(pkg, fn, None)
			if value and meta.get_field(fn):
				row_dict[fn] = value
		wh = _norm(getattr(pkg, "warehouse_item", None))
		if not getattr(pkg, "description", None) and wh and meta.get_field("description"):
			row_dict["description"] = (
				frappe.db.get_value("Warehouse Item", wh, "item_name") or wh
			)
		for fn in _PACKAGE_DETAIL_FIELDS:
			value = getattr(pkg, fn, None)
			if value in (None, "", 0, 0.0):
				continue
			if meta.get_field(fn):
				row_dict[fn] = value
		if row_dict:
			target_doc.append("packages", row_dict)
			count += 1
	return count


def _receipt_exists(sp_doc: Any, source_doctype: str, source_name: str, package_idx: int) -> bool:
	for rc in getattr(sp_doc, "deliveries", None) or []:
		if (
			_norm(getattr(rc, "source_doctype", None)) == source_doctype
			and _norm(getattr(rc, "source_name", None)) == source_name
			and cint_safe(getattr(rc, "source_package_idx", None)) == package_idx
			and (getattr(rc, "status", None) or "") != "Cancelled"
		):
			return True
	return False


def build_receipts_from_transport_order(tro: Any) -> list[dict[str, Any]]:
	"""Transport Order is planning-only; deliveries post from the derived Transport Job."""
	return []


def build_receipts_from_transport_job(tj: Any) -> list[dict[str, Any]]:
	"""Build delivery receipt row dicts from a submitted Transport Job (caller persists on SP)."""
	if (getattr(tj, "doctype", None) or "") not in PACKAGE_RECEIPT_TRANSPORT_DOCTYPES:
		return []
	project = _norm(getattr(tj, "project", None))
	sp_name = resolve_special_project_from_project(project)
	if not sp_name:
		return []

	sp_doc = frappe.get_doc("Special Project", sp_name)
	transport_order = _norm(getattr(tj, "transport_order", None))
	fallback_refs = [("Transport Order", transport_order)] if transport_order else None
	container_no = _norm(getattr(tj, "container_no", None)) or _norm(getattr(tj, "container", None))
	if not container_no and transport_order:
		container_no = _norm(
			frappe.db.get_value("Transport Order", transport_order, "container_no")
		) or _norm(frappe.db.get_value("Transport Order", transport_order, "container"))
	stage = _default_receipt_stage(
		sp_doc, tj.doctype, tj.name, fallback_refs=fallback_refs
	)
	created: list[dict[str, Any]] = []

	for pkg in getattr(tj, "packages", None) or []:
		pkg_idx = cint_safe(getattr(pkg, "idx", None))
		if _receipt_exists(sp_doc, tj.doctype, tj.name, pkg_idx):
			continue
		qty = flt(getattr(pkg, "quantity", 0)) or flt(getattr(pkg, "no_of_packs", 0))
		if qty <= 0:
			continue
		wh = _norm(getattr(pkg, "warehouse_item", None))
		commodity = _norm(getattr(pkg, "commodity", None))
		desc = _norm(getattr(pkg, "description", None)) or _package_description(pkg)
		mat, mat_row = _resolve_sp_package_for_operational_line(sp_doc, pkg)
		if mat is None:
			continue
		created.append(
			{
				"package_row": mat_row,
				"warehouse_item": wh or getattr(mat, "warehouse_item", None),
				"commodity": commodity or getattr(mat, "commodity", None),
				"description": desc or getattr(mat, "description", None),
				"qty_received": qty,
				"uom": getattr(pkg, "uom", None) or getattr(mat, "uom", None),
				"receipt_date": getdate(today()),
				"lifecycle_stage": stage,
				"status": POSTED_RECEIPT_STATUS,
				"source_job_type": tj.doctype,
				"source_job_no": tj.name,
				"container_no": container_no or None,
				"source_doctype": tj.doctype,
				"source_name": tj.name,
				"source_package_idx": pkg_idx,
			}
		)
	return created


def persist_receipts_on_special_project(sp_name: str, receipt_rows: list[dict[str, Any]]) -> int:
	if not receipt_rows or not sp_name:
		return 0
	sp = frappe.get_doc("Special Project", sp_name)
	sp.flags.ignore_delivery_validation = True
	for row in receipt_rows:
		_append_child_row(sp, "deliveries", row)
	sp.flags.ignore_validate_update_after_submit = True
	sp.flags.ignore_charges_sync = True
	sp.flags.ignore_delivery_validation = True
	validate_packages(sp)
	sp.save(ignore_permissions=True)
	return len(receipt_rows)


def post_site_receipts_from_transport_order(tro: Any) -> int:
	"""Transport Order is planning-only; deliveries post from the derived Transport Job."""
	return 0


def post_site_receipts_from_transport_job(tj: Any) -> int:
	"""Append delivery receipts on the linked Special Project when a Transport Job is submitted."""
	rows = build_receipts_from_transport_job(tj)
	if not rows:
		return 0
	project = _norm(getattr(tj, "project", None))
	sp_name = resolve_special_project_from_project(project)
	if not sp_name:
		return 0
	n = persist_receipts_on_special_project(sp_name, rows)
	if n:
		frappe.msgprint(
			_("Posted {0} delivery line(s) to Special Project {1}.").format(n, sp_name),
			indicator="green",
			title=_("Packages"),
		)
	return n


def _cancel_receipts_on_special_project(
	sp_name: str, source_doctype: str, source_name: str
) -> int:
	"""Flip posted delivery rows for one source job to Cancelled on a Special Project."""
	sp = frappe.get_doc("Special Project", sp_name)
	changed = 0
	for rc in getattr(sp, "deliveries", None) or []:
		if (
			_receipt_matches_source(rc, source_doctype, source_name)
			and (getattr(rc, "status", None) or "") == POSTED_RECEIPT_STATUS
		):
			rc.status = CANCELLED_RECEIPT_STATUS
			changed += 1
	if not changed:
		return 0
	sp.flags.ignore_validate_update_after_submit = True
	sp.flags.ignore_charges_sync = True
	sp.flags.ignore_delivery_validation = True
	validate_packages(sp)
	sp.save(ignore_permissions=True)
	return changed


def cancel_receipts_for_transport_order(tro: Any) -> int:
	"""Legacy receipts may still reference Transport Order; cancel those if present."""
	project = _norm(getattr(tro, "project", None))
	sp_name = resolve_special_project_from_project(project)
	if not sp_name:
		return 0
	return _cancel_receipts_on_special_project(sp_name, tro.doctype, tro.name)


def cancel_receipts_for_transport_job(tj: Any) -> int:
	project = _norm(getattr(tj, "project", None))
	sp_name = resolve_special_project_from_project(project)
	if not sp_name:
		return 0
	return _cancel_receipts_on_special_project(sp_name, tj.doctype, tj.name)


def on_transport_job_submit(doc: Any, method: str | None = None) -> None:
	"""Doc-events bridge: post SP deliveries when a Transport Job is submitted."""
	try:
		post_site_receipts_from_transport_job(doc)
	except Exception:
		frappe.log_error(
			frappe.get_traceback(),
			f"Transport Job {doc.name}: package delivery post",
		)


def on_transport_job_cancel(doc: Any, method: str | None = None) -> None:
	"""Doc-events bridge: cancel SP deliveries when a Transport Job is cancelled."""
	try:
		cancel_receipts_for_transport_job(doc)
	except Exception:
		frappe.log_error(
			frappe.get_traceback(),
			f"Transport Job {doc.name}: package delivery cancel",
		)


# Air / Sea Shipment auto-receipt on submit
# ----------------------------------------
# Mirrors the Transport Order pattern: when a freight Shipment is submitted, its
# Packages table is folded into the parent Special Project's Deliveries table.
# The Shipment is the execution document for the corresponding Booking, so we
# attribute the delivery to the Shipment but fall back to the linked Booking
# when resolving the originating Lifecycle Job (the Lifecycle Job row references
# the Booking, never the Shipment).

# Maps a freight Shipment doctype to the link field that points at the originating Booking.
_FREIGHT_SHIPMENT_BOOKING_FIELDS: dict[str, tuple[str, str]] = {
	"Air Shipment": ("air_booking", "Air Booking"),
	"Sea Shipment": ("sea_booking", "Sea Booking"),
}


def _freight_shipment_booking_ref(doc: Any) -> tuple[str, str] | None:
	"""Return ``(booking_doctype, booking_name)`` for a freight Shipment, if linked."""
	mapping = _FREIGHT_SHIPMENT_BOOKING_FIELDS.get(getattr(doc, "doctype", "") or "")
	if not mapping:
		return None
	field, booking_dt = mapping
	booking_name = _norm(getattr(doc, field, None))
	if not booking_name:
		return None
	return (booking_dt, booking_name)


def _package_description(pkg: Any) -> str:
	"""Return the goods description from a package row, tolerating either field name.

	Site Material / Transport Order Packages use ``description``; Air / Sea Booking
	and Shipment Packages use ``goods_description``. Callers want a single string
	without caring which child doctype they were handed.
	"""
	value = _norm(getattr(pkg, "description", None))
	if value:
		return value
	return _norm(getattr(pkg, "goods_description", None))


def build_receipts_from_freight_shipment(doc: Any) -> list[dict[str, Any]]:
	"""Build delivery receipt row dicts from a freight Shipment (Air or Sea).

	The Shipment's ``project`` field resolves the parent Special Project. Lifecycle
	stage is looked up against the Shipment first and then against the linked
	Booking, since the SP's Lifecycle Job row references the Booking. Caller
	persists the rows on the Special Project.
	"""
	if (getattr(doc, "doctype", None) or "") not in PACKAGE_RECEIPT_FREIGHT_SHIPMENT_DOCTYPES:
		return []
	project = _norm(getattr(doc, "project", None))
	sp_name = resolve_special_project_from_project(project)
	if not sp_name:
		return []

	sp_doc = frappe.get_doc("Special Project", sp_name)
	booking_ref = _freight_shipment_booking_ref(doc)
	stage = _default_receipt_stage(
		sp_doc,
		doc.doctype,
		doc.name,
		fallback_refs=[booking_ref] if booking_ref else None,
	)
	container_no = _norm(getattr(doc, "container_no", None)) or _norm(
		getattr(doc, "container", None)
	)
	created: list[dict[str, Any]] = []

	for pkg in getattr(doc, "packages", None) or []:
		pkg_idx = cint_safe(getattr(pkg, "idx", None))
		if _receipt_exists(sp_doc, doc.doctype, doc.name, pkg_idx):
			continue
		qty = (
			flt(getattr(pkg, "quantity", 0))
			or flt(getattr(pkg, "no_of_packs", 0))
		)
		if qty <= 0:
			continue
		wh = _norm(getattr(pkg, "warehouse_item", None))
		commodity = _norm(getattr(pkg, "commodity", None))
		desc = _package_description(pkg)
		mat, mat_row = _resolve_sp_package_for_operational_line(sp_doc, pkg)
		if mat is None:
			continue
		created.append(
			{
				"package_row": mat_row,
				"warehouse_item": wh or getattr(mat, "warehouse_item", None),
				"commodity": commodity or getattr(mat, "commodity", None),
				"description": desc or getattr(mat, "description", None),
				"qty_received": qty,
				"uom": getattr(pkg, "uom", None) or getattr(mat, "uom", None),
				"receipt_date": getdate(today()),
				"lifecycle_stage": stage,
				"status": POSTED_RECEIPT_STATUS,
				"source_job_type": doc.doctype,
				"source_job_no": doc.name,
				"container_no": container_no or None,
				"source_doctype": doc.doctype,
				"source_name": doc.name,
				"source_package_idx": pkg_idx,
			}
		)
	return created


def post_site_receipts_from_freight_shipment(doc: Any) -> int:
	"""Append delivery receipts on the parent Special Project for an Air/Sea Shipment."""
	rows = build_receipts_from_freight_shipment(doc)
	if not rows:
		return 0
	project = _norm(getattr(doc, "project", None))
	sp_name = resolve_special_project_from_project(project)
	if not sp_name:
		return 0
	n = persist_receipts_on_special_project(sp_name, rows)
	if n:
		frappe.msgprint(
			_("Posted {0} delivery line(s) to Special Project {1}.").format(n, sp_name),
			indicator="green",
			title=_("Packages"),
		)
	return n


def cancel_receipts_for_freight_shipment(doc: Any) -> int:
	"""Flip matching posted delivery receipts to ``Cancelled`` when an Air/Sea Shipment is cancelled."""
	project = _norm(getattr(doc, "project", None))
	sp_name = resolve_special_project_from_project(project)
	if not sp_name:
		return 0
	return _cancel_receipts_on_special_project(sp_name, doc.doctype, doc.name)


def on_freight_shipment_submit(doc: Any, method: str | None = None) -> None:
	"""Doc-events bridge: post SP deliveries when an Air/Sea Shipment is submitted.

	Wrapped so a failure here cannot abort the Shipment submission; we log instead.
	"""
	try:
		post_site_receipts_from_freight_shipment(doc)
	except Exception:
		frappe.log_error(
			frappe.get_traceback(),
			f"{doc.doctype} {doc.name}: package delivery post",
		)


def on_freight_shipment_cancel(doc: Any, method: str | None = None) -> None:
	"""Doc-events bridge: cancel SP deliveries when an Air/Sea Shipment is cancelled."""
	try:
		cancel_receipts_for_freight_shipment(doc)
	except Exception:
		frappe.log_error(
			frappe.get_traceback(),
			f"{doc.doctype} {doc.name}: package delivery cancel",
		)


def _resolve_sp_from_project_doc(doc: Any) -> str | None:
	"""Resolve parent Special Project for a Project Job.

	Prefers the document's ``special_project`` link; falls back to the freight-style
	``project`` resolver to stay compatible with documents that only carry an ERPNext
	Project reference.
	"""
	sp_name = _norm(getattr(doc, "special_project", None))
	if sp_name and frappe.db.exists("Special Project", sp_name):
		return sp_name
	project = _norm(getattr(doc, "project", None))
	return resolve_special_project_from_project(project)


def build_receipts_from_project_job_packages(doc: Any) -> list[dict[str, Any]]:
	"""Build delivery receipt rows from Project Job ``packages`` child table."""
	if (getattr(doc, "doctype", None) or "") != "Project Job":
		return []
	if not getattr(doc, "packages", None):
		return []
	sp_name = _resolve_sp_from_project_doc(doc)
	if not sp_name:
		return []

	sp_doc = frappe.get_doc("Special Project", sp_name)
	stage = _default_receipt_stage(sp_doc, doc.doctype, doc.name)
	created: list[dict[str, Any]] = []

	for pkg in doc.packages or []:
		pkg_idx = cint_safe(getattr(pkg, "idx", None))
		if _receipt_exists(sp_doc, doc.doctype, doc.name, pkg_idx):
			continue
		qty = flt(getattr(pkg, "quantity", 0)) or flt(getattr(pkg, "no_of_packs", 0))
		if qty <= 0:
			continue
		wh = _norm(getattr(pkg, "warehouse_item", None))
		commodity = _norm(getattr(pkg, "commodity", None))
		desc = _norm(getattr(pkg, "description", None))
		mat, mat_row = _resolve_sp_package_for_operational_line(sp_doc, pkg)
		if mat is None:
			continue
		created.append(
			{
				"package_row": mat_row,
				"warehouse_item": wh or getattr(mat, "warehouse_item", None),
				"commodity": commodity or getattr(mat, "commodity", None),
				"description": desc or getattr(mat, "description", None),
				"qty_received": qty,
				"uom": getattr(pkg, "uom", None) or getattr(mat, "uom", None),
				"receipt_date": getdate(today()),
				"lifecycle_stage": stage,
				"status": POSTED_RECEIPT_STATUS,
				"source_job_type": doc.doctype,
				"source_job_no": doc.name,
				"container_no": _norm(getattr(pkg, "container_no", None)) or None,
				"source_doctype": doc.doctype,
				"source_name": doc.name,
				"source_package_idx": pkg_idx,
			}
		)
	return created


def build_receipts_from_project_doc(doc: Any) -> list[dict[str, Any]]:
	"""Build delivery receipt row dicts from a Project Job.

	Prefer ``packages`` when present; fall back to legacy ``materials_received``.
	"""
	package_rows = build_receipts_from_project_job_packages(doc)
	if package_rows:
		return package_rows

	# Legacy materials_received path
	if (getattr(doc, "doctype", None) or "") not in PACKAGE_RECEIPT_PROJECT_JOB_DOCTYPES:
		return []
	sp_name = _resolve_sp_from_project_doc(doc)
	if not sp_name:
		return []

	sp_doc = frappe.get_doc("Special Project", sp_name)
	stage = _default_receipt_stage(sp_doc, doc.doctype, doc.name)
	created: list[dict[str, Any]] = []

	for row in getattr(doc, "materials_received", None) or []:
		row_idx = cint_safe(getattr(row, "idx", None))
		if _receipt_exists(sp_doc, doc.doctype, doc.name, row_idx):
			continue
		qty = flt(getattr(row, "qty_received", 0))
		if qty <= 0:
			continue
		wh = _norm(getattr(row, "warehouse_item", None))
		commodity = _norm(getattr(row, "commodity", None))
		desc = _norm(getattr(row, "description", None))
		explicit_row_link = cint_safe(
			getattr(row, "package_row", None) or getattr(row, "site_material_row", None)
		)
		line = frappe._dict(
			package_row=explicit_row_link or None,
			warehouse_item=wh,
			commodity=commodity,
			description=desc,
		)
		mat, mat_row = _resolve_sp_package_for_operational_line(sp_doc, line)
		if mat is None:
			continue
		created.append(
			{
				"package_row": mat_row,
				"warehouse_item": wh or getattr(mat, "warehouse_item", None),
				"commodity": commodity or getattr(mat, "commodity", None),
				"description": desc or getattr(mat, "description", None),
				"qty_received": qty,
				"uom": getattr(row, "uom", None) or getattr(mat, "uom", None),
				"receipt_date": getdate(today()),
				"lifecycle_stage": stage,
				"status": POSTED_RECEIPT_STATUS,
				"source_job_type": doc.doctype,
				"source_job_no": doc.name,
				"container_no": _norm(getattr(row, "container_no", None)) or None,
				"source_doctype": doc.doctype,
				"source_name": doc.name,
				"source_package_idx": row_idx,
			}
		)
	return created


def post_site_receipts_from_project_doc(doc: Any) -> int:
	"""Append delivery receipts on the parent Special Project when a Project Job is submitted."""
	rows = build_receipts_from_project_doc(doc)
	if not rows:
		return 0
	sp_name = _resolve_sp_from_project_doc(doc)
	if not sp_name:
		return 0
	n = persist_receipts_on_special_project(sp_name, rows)
	if n:
		frappe.msgprint(
			_("Posted {0} delivery line(s) to Special Project {1}.").format(n, sp_name),
			indicator="green",
			title=_("Packages"),
		)
	return n


def cancel_receipts_for_project_doc(doc: Any) -> int:
	"""Flip matching posted delivery receipts to ``Cancelled`` when a Project Job is cancelled."""
	sp_name = _resolve_sp_from_project_doc(doc)
	if not sp_name:
		return 0
	return _cancel_receipts_on_special_project(sp_name, doc.doctype, doc.name)


@frappe.whitelist()
def recalculate_package_delivery_balances(special_project: str) -> dict[str, Any]:
	doc = frappe.get_doc("Special Project", special_project)
	doc.check_permission("write")
	validate_packages(doc)
	doc.save(ignore_permissions=True)
	return {"ok": True, "message": _("Package delivery balances updated.")}


@frappe.whitelist()
def get_packages_for_shipment_picker(special_project: str) -> list[dict[str, Any]]:
	"""Return package rows for the Booking/Order shipment lines dialog."""
	if not special_project or not frappe.db.exists("Special Project", special_project):
		frappe.throw(_("Invalid Special Project."))
	doc = frappe.get_doc("Special Project", special_project)
	doc.check_permission("read")
	validate_packages(doc)
	out: list[dict[str, Any]] = []
	for pkg in getattr(doc, "packages", None) or []:
		if cint_safe(getattr(pkg, "include_on_create", 0)):
			continue
		wh = _norm(getattr(pkg, "warehouse_item", None))
		warehouse_item_name = None
		if wh:
			warehouse_item_name = frappe.db.get_value("Warehouse Item", wh, "item_name")
		site = getattr(pkg, "site", None)
		site_label = None
		if site:
			site_label = frappe.db.get_value("Address", site, "address_title") or site
		out.append(
			{
				"package_row": cint_safe(getattr(pkg, "idx", None)),
				"commodity": getattr(pkg, "commodity", None),
				"warehouse_item": wh or None,
				"warehouse_item_name": warehouse_item_name,
				"description": getattr(pkg, "description", None),
				"site": site,
				"site_label": site_label,
				"reference_no": getattr(pkg, "reference_no", None),
				"qty_required": flt(getattr(pkg, "qty_required", 0)),
				"qty_on_site": flt(getattr(pkg, "qty_on_site", 0)),
				"qty_short": flt(getattr(pkg, "qty_short", 0)),
				"uom": getattr(pkg, "uom", None),
			}
		)
	return out


@frappe.whitelist()
def add_packages_to_transport_order(
	special_project: str,
	shipment_lines: Any,
	lifecycle_job_idx: int | None = None,
	lifecycle_jobs: Any = None,
) -> dict[str, Any]:
	"""Create Transport Order from lifecycle row with selected packages as shipment lines."""
	from logistics.special_projects.special_project_booking_creation import (
		create_booking_or_order_from_special_project,
	)

	return create_booking_or_order_from_special_project(
		special_project,
		"Transport Order",
		lifecycle_job_idx=lifecycle_job_idx,
		lifecycle_jobs=lifecycle_jobs,
		shipment_lines=shipment_lines,
	)
