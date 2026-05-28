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
from frappe.utils import flt, getdate, today

from logistics.utils.internal_job_from_source import _child_doctype_for_table_field

POSTED_RECEIPT_STATUS = "Posted"

DEFAULT_RECEIPT_LIFECYCLE_STAGE = "Logistics"


def _stage_from_lifecycle_job(sp_doc: Any, job_type: str, job_no: str) -> str | None:
	"""Find the originating Lifecycle Job row on the Special Project and return its stage."""
	job_type = _norm(job_type)
	job_no = _norm(job_no)
	if not job_type or not job_no:
		return None
	for row in getattr(sp_doc, "lifecycle_jobs", None) or []:
		if (
			_norm(getattr(row, "job_type", None)) == job_type
			and _norm(getattr(row, "job_no", None)) == job_no
		):
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


def sync_package_delivery_balances(sp_doc: Any) -> None:
	"""Recompute qty_on_site and qty_short on each package row from posted deliveries.

	Rows where include_on_create is ticked are off-ledger always-along packages and
	stay at qty_on_site = qty_short = 0.
	"""
	packages = getattr(sp_doc, "packages", None) or []
	if not packages:
		return

	totals_by_row: dict[int, float] = {}
	totals_by_warehouse_item: dict[str, float] = {}
	totals_by_commodity: dict[str, float] = {}
	totals_by_desc: dict[str, float] = {}

	for rc in _posted_deliveries(sp_doc):
		qty = flt(getattr(rc, "qty_received", 0))
		row_idx = cint_safe(getattr(rc, "package_row", None))
		if row_idx:
			totals_by_row[row_idx] = totals_by_row.get(row_idx, 0) + qty
		wh = _norm(getattr(rc, "warehouse_item", None))
		if wh:
			totals_by_warehouse_item[wh] = totals_by_warehouse_item.get(wh, 0) + qty
		commodity = _norm(getattr(rc, "commodity", None))
		if commodity:
			totals_by_commodity[commodity] = totals_by_commodity.get(commodity, 0) + qty
		desc = _norm_desc(getattr(rc, "description", None))
		if desc:
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
			if wh:
				on_site = flt(totals_by_warehouse_item.get(wh, 0))
			if not on_site:
				commodity = _norm(getattr(pkg, "commodity", None))
				if commodity:
					on_site = flt(totals_by_commodity.get(commodity, 0))
			if not on_site:
				desc = _norm_desc(getattr(pkg, "description", None))
				if desc:
					on_site = flt(totals_by_desc.get(desc, 0))
		required = flt(getattr(pkg, "qty_required", 0))
		pkg.qty_on_site = on_site
		pkg.qty_short = max(required - on_site, 0)


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
	fallback_stage = _default_receipt_stage(sp_doc)
	for j, rc in enumerate(getattr(sp_doc, "deliveries", None) or [], start=1):
		if flt(getattr(rc, "qty_received", 0)) <= 0:
			continue
		if not _norm(getattr(rc, "lifecycle_stage", None)):
			job_type = _norm(getattr(rc, "source_job_type", None))
			job_no = _norm(getattr(rc, "source_job_no", None))
			stage = _default_receipt_stage(sp_doc, job_type, job_no) or fallback_stage
			if stage:
				rc.lifecycle_stage = stage
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
	warehouse_item = _norm(warehouse_item)
	commodity = _norm(commodity)
	description = _norm(description)
	for pkg in getattr(sp_doc, "packages", None) or []:
		if warehouse_item and _norm(getattr(pkg, "warehouse_item", None)) == warehouse_item:
			return pkg
		if commodity and _norm(getattr(pkg, "commodity", None)) == commodity:
			return pkg
		if description and not warehouse_item and not commodity:
			if _norm(getattr(pkg, "description", None)).lower() == description.lower():
				return pkg
	return None


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
	"""Build delivery receipt row dicts from a submitted Transport Order (caller persists on SP)."""
	project = _norm(getattr(tro, "project", None))
	sp_name = resolve_special_project_from_project(project)
	if not sp_name:
		return []

	sp_doc = frappe.get_doc("Special Project", sp_name)
	container_no = _norm(getattr(tro, "container_no", None)) or _norm(getattr(tro, "container", None))
	stage = _default_receipt_stage(sp_doc, tro.doctype, tro.name)
	created: list[dict[str, Any]] = []

	for pkg in getattr(tro, "packages", None) or []:
		pkg_idx = cint_safe(getattr(pkg, "idx", None))
		if _receipt_exists(sp_doc, tro.doctype, tro.name, pkg_idx):
			continue
		qty = flt(getattr(pkg, "quantity", 0)) or flt(getattr(pkg, "no_of_packs", 0))
		if qty <= 0:
			continue
		wh = _norm(getattr(pkg, "warehouse_item", None))
		commodity = _norm(getattr(pkg, "commodity", None))
		desc = _norm(getattr(pkg, "description", None))
		mat = _find_package_row(
			sp_doc, warehouse_item=wh, commodity=commodity, description=desc
		)
		if mat is not None and cint_safe(getattr(mat, "include_on_create", 0)):
			continue
		mat_row = cint_safe(getattr(mat, "idx", None)) if mat else 0
		created.append(
			{
				"package_row": mat_row,
				"warehouse_item": wh or (getattr(mat, "warehouse_item", None) if mat else None),
				"commodity": commodity or (getattr(mat, "commodity", None) if mat else None),
				"description": desc or (getattr(mat, "description", None) if mat else None),
				"qty_received": qty,
				"uom": getattr(pkg, "uom", None) or (getattr(mat, "uom", None) if mat else None),
				"receipt_date": getdate(today()),
				"lifecycle_stage": stage,
				"status": POSTED_RECEIPT_STATUS,
				"source_job_type": tro.doctype,
				"source_job_no": tro.name,
				"container_no": container_no or None,
				"source_doctype": tro.doctype,
				"source_name": tro.name,
				"source_package_idx": pkg_idx,
			}
		)
	return created


def persist_receipts_on_special_project(sp_name: str, receipt_rows: list[dict[str, Any]]) -> int:
	if not receipt_rows or not sp_name:
		return 0
	sp = frappe.get_doc("Special Project", sp_name)
	for row in receipt_rows:
		_append_child_row(sp, "deliveries", row)
	sp.flags.ignore_validate_update_after_submit = True
	sp.flags.ignore_charges_sync = True
	validate_packages(sp)
	sp.save(ignore_permissions=True)
	return len(receipt_rows)


def post_site_receipts_from_transport_order(tro: Any) -> int:
	"""Append delivery receipts on the linked Special Project when a Transport Order is submitted."""
	rows = build_receipts_from_transport_order(tro)
	if not rows:
		return 0
	project = _norm(getattr(tro, "project", None))
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


def cancel_receipts_for_transport_order(tro: Any) -> int:
	project = _norm(getattr(tro, "project", None))
	sp_name = resolve_special_project_from_project(project)
	if not sp_name:
		return 0
	sp = frappe.get_doc("Special Project", sp_name)
	changed = 0
	for rc in getattr(sp, "deliveries", None) or []:
		if (
			_norm(getattr(rc, "source_doctype", None)) == tro.doctype
			and _norm(getattr(rc, "source_name", None)) == tro.name
			and (getattr(rc, "status", None) or "") == POSTED_RECEIPT_STATUS
		):
			rc.status = "Cancelled"
			changed += 1
	if not changed:
		return 0
	sp.flags.ignore_validate_update_after_submit = True
	sp.flags.ignore_charges_sync = True
	validate_packages(sp)
	sp.save(ignore_permissions=True)
	return changed


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
		mat = _find_package_row(
			sp_doc, warehouse_item=wh, commodity=commodity, description=desc
		)
		if mat is not None and cint_safe(getattr(mat, "include_on_create", 0)):
			continue
		mat_row = cint_safe(getattr(mat, "idx", None)) if mat else 0
		created.append(
			{
				"package_row": mat_row,
				"warehouse_item": wh or (getattr(mat, "warehouse_item", None) if mat else None),
				"commodity": commodity or (getattr(mat, "commodity", None) if mat else None),
				"description": desc or (getattr(mat, "description", None) if mat else None),
				"qty_received": qty,
				"uom": getattr(pkg, "uom", None) or (getattr(mat, "uom", None) if mat else None),
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
	sp = frappe.get_doc("Special Project", sp_name)
	changed = 0
	for rc in getattr(sp, "deliveries", None) or []:
		if (
			_norm(getattr(rc, "source_doctype", None)) == doc.doctype
			and _norm(getattr(rc, "source_name", None)) == doc.name
			and (getattr(rc, "status", None) or "") == POSTED_RECEIPT_STATUS
		):
			rc.status = "Cancelled"
			changed += 1
	if not changed:
		return 0
	sp.flags.ignore_validate_update_after_submit = True
	sp.flags.ignore_charges_sync = True
	validate_packages(sp)
	sp.save(ignore_permissions=True)
	return changed


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


def build_receipts_from_project_doc(doc: Any) -> list[dict[str, Any]]:
	"""Build delivery receipt row dicts from a Project Job ``materials_received``.

	Project Order is a planning document and no longer carries ``materials_received``
	or posts receipts; only its derived Project Job does, to keep the parent Special
	Project's Deliveries table single-sourced.

	Caller persists the rows on the parent Special Project.
	"""
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
		mat = None
		if explicit_row_link:
			packages = getattr(sp_doc, "packages", None) or []
			if 1 <= explicit_row_link <= len(packages):
				mat = packages[explicit_row_link - 1]
		if mat is None:
			mat = _find_package_row(
				sp_doc, warehouse_item=wh, commodity=commodity, description=desc
			)
		if mat is not None and cint_safe(getattr(mat, "include_on_create", 0)):
			continue
		mat_row = cint_safe(getattr(mat, "idx", None)) if mat else 0
		created.append(
			{
				"package_row": mat_row,
				"warehouse_item": wh or (getattr(mat, "warehouse_item", None) if mat else None),
				"commodity": commodity or (getattr(mat, "commodity", None) if mat else None),
				"description": desc or (getattr(mat, "description", None) if mat else None),
				"qty_received": qty,
				"uom": getattr(row, "uom", None) or (getattr(mat, "uom", None) if mat else None),
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
	sp = frappe.get_doc("Special Project", sp_name)
	changed = 0
	for rc in getattr(sp, "deliveries", None) or []:
		if (
			_norm(getattr(rc, "source_doctype", None)) == doc.doctype
			and _norm(getattr(rc, "source_name", None)) == doc.name
			and (getattr(rc, "status", None) or "") == POSTED_RECEIPT_STATUS
		):
			rc.status = "Cancelled"
			changed += 1
	if not changed:
		return 0
	sp.flags.ignore_validate_update_after_submit = True
	sp.flags.ignore_charges_sync = True
	validate_packages(sp)
	sp.save(ignore_permissions=True)
	return changed


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
		out.append(
			{
				"package_row": cint_safe(getattr(pkg, "idx", None)),
				"commodity": getattr(pkg, "commodity", None),
				"warehouse_item": wh or None,
				"warehouse_item_name": warehouse_item_name,
				"description": getattr(pkg, "description", None),
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
