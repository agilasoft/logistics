# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Post programme charge qty increments and execution logs when jobs/shipments submit."""

from __future__ import annotations

from typing import Any

import frappe
from frappe.utils import flt, now_datetime

from logistics.special_projects.lifecycle_job_financial_rollup import (
	sync_lifecycle_job_financials,
)
from logistics.special_projects.special_project_charge_lifecycle import (
	is_planning_lifecycle_row,
	programme_charge_applies_to_planning_lifecycle,
)
from logistics.special_projects.special_project_service_rows import (
	planning_service_rows,
	service_row_by_name,
	service_rows,
)
from logistics.special_projects.special_project_packages import (
	_resolve_sp_from_project_doc,
	resolve_special_project_from_project,
)
from logistics.utils.charge_service_type import sales_quote_charge_service_types_equal
from logistics.utils.charges_calculation import (
	apply_charge_type_side_cleanup,
	calculate_charge_cost,
	calculate_charge_revenue,
)
from logistics.utils.internal_job_main_rollup import _is_disbursement_charge

POSTED_LOG_STATUS = "Posted"
CANCELLED_LOG_STATUS = "Cancelled"

EXECUTION_DOCTYPES: frozenset[str] = frozenset(
	{
		"Air Shipment",
		"Sea Shipment",
		"Transport Job",
		"Declaration",
		"Warehouse Job",
		"Project Job",
	}
)

_PLANNING_ORDER_TYPES: frozenset[str] = frozenset(
	{
		"Air Booking",
		"Sea Booking",
		"Transport Order",
		"Declaration Order",
		"Inbound Order",
		"Cross-Docking Order",
		"Project Order",
	}
)


def _norm(value: Any) -> str:
	return (value or "").strip()


def _resolve_special_project_name(doc: Any) -> str | None:
	if (getattr(doc, "doctype", None) or "") == "Project Job":
		return _resolve_sp_from_project_doc(doc)
	project = _norm(getattr(doc, "project", None))
	return resolve_special_project_from_project(project) if project else None


def _order_key_from_execution_job_name(job_no: str) -> tuple[str, str] | None:
	"""Resolve a submitted shipment/job name to its planning booking/order."""
	job_no = _norm(job_no)
	if not job_no:
		return None
	for exec_dt in EXECUTION_DOCTYPES:
		if frappe.db.exists(exec_dt, job_no):
			return _order_key_from_execution_doc(frappe.get_doc(exec_dt, job_no))
	return None


def _order_key_from_planning_order_name(order_no: str) -> tuple[str, str] | None:
	"""Return the planning doctype when an order/booking name exists."""
	order_no = _norm(order_no)
	if not order_no:
		return None
	for order_type in _PLANNING_ORDER_TYPES:
		if frappe.db.exists(order_type, order_no):
			return order_type, order_no
	return None


def _planning_order_key_for_execution_log(
	lifecycle_row: Any, exec_doc: Any
) -> tuple[str, str] | None:
	"""Return booking/order type and name for a charge execution log row."""
	for field in ("job_type", "order_type"):
		order_type = _norm(getattr(lifecycle_row, field, None))
		order_no = _norm(getattr(lifecycle_row, "order_no", None))
		if order_type in _PLANNING_ORDER_TYPES and order_no:
			return order_type, order_no
	return _order_key_from_execution_doc(exec_doc)


def normalize_charge_execution_log_link_fields(doc: Any) -> None:
	"""Ensure charge execution log Dynamic Link fields use planning order types."""
	for log in doc.get("charge_execution_logs") or []:
		_normalize_one_charge_execution_log_link(log)


def _normalize_one_charge_execution_log_link(log: Any) -> None:
	jt = _norm(getattr(log, "job_type", None))
	on = _norm(getattr(log, "order_no", None))
	jn = _norm(getattr(log, "job_no", None))

	if jt in _PLANNING_ORDER_TYPES and on and frappe.db.exists(jt, on):
		return

	order_key = _order_key_from_execution_job_name(jn)
	if not order_key and on:
		order_key = _order_key_from_planning_order_name(on)
	if order_key:
		log.job_type, log.order_no = order_key
		return

	if jt not in _PLANNING_ORDER_TYPES:
		log.job_type = None
	if on:
		log.order_no = None


def _order_key_from_execution_doc(doc: Any) -> tuple[str, str] | None:
	dt = (getattr(doc, "doctype", None) or "").strip()
	name = _norm(getattr(doc, "name", None))
	if not dt or not name:
		return None
	if dt == "Air Shipment":
		ab = _norm(getattr(doc, "air_booking", None))
		return ("Air Booking", ab) if ab else None
	if dt == "Sea Shipment":
		sb = _norm(getattr(doc, "sea_booking", None))
		return ("Sea Booking", sb) if sb else None
	if dt == "Transport Job":
		to = _norm(getattr(doc, "transport_order", None))
		return ("Transport Order", to) if to else None
	if dt == "Declaration":
		do = _norm(getattr(doc, "declaration_order", None))
		return ("Declaration Order", do) if do else None
	if dt == "Warehouse Job":
		ref_type = _norm(getattr(doc, "reference_order_type", None))
		ref = _norm(getattr(doc, "reference_order", None))
		if ref_type in _PLANNING_ORDER_TYPES and ref:
			return (ref_type, ref)
		return None
	if dt == "Project Job":
		po = _norm(getattr(doc, "special_project_order", None))
		return ("Project Order", po) if po else None
	return None


def resolve_lifecycle_planning_row(
	sp_doc: Any, order_type: str, order_no: str
) -> Any | None:
	order_type = _norm(order_type)
	order_no = _norm(order_no)
	if not order_type or not order_no:
		return None
	for row in sp_doc.get("lifecycle_jobs") or []:
		if not is_planning_lifecycle_row(row):
			continue
		jt = _norm(getattr(row, "job_type", None))
		on = _norm(getattr(row, "order_no", None))
		if jt == order_type and on == order_no:
			return row
		# Legacy rows may still carry planning refs on order_type/order_no.
		ot = _norm(getattr(row, "order_type", None))
		if ot == order_type and on == order_no:
			return row
	return None


def resolve_lifecycle_row_for_execution_doc(doc: Any) -> tuple[Any, Any] | tuple[None, None]:
	"""Return ``(sp_doc, planning_lifecycle_row)`` for an execution document."""
	if (getattr(doc, "doctype", None) or "") not in EXECUTION_DOCTYPES:
		return None, None
	sp_name = _resolve_special_project_name(doc)
	if not sp_name:
		return None, None
	order_key = _order_key_from_execution_doc(doc)
	if not order_key:
		return None, None
	sp_doc = frappe.get_doc("Special Project", sp_name)
	planning_row = resolve_lifecycle_planning_row(sp_doc, order_key[0], order_key[1])
	return sp_doc, planning_row


def _programme_charges_for_lifecycle(sp_doc: Any, lifecycle_row: Any) -> list[Any]:
	st = _norm(getattr(lifecycle_row, "service_type", None))
	out: list[Any] = []
	for charge in sp_doc.get("charges") or []:
		if _is_disbursement_charge(charge):
			continue
		if st and not sales_quote_charge_service_types_equal(
			getattr(charge, "service_type", None), st
		):
			continue
		out.append(charge)
	return out


def _matching_programme_charges(
	sp_doc: Any, lifecycle_row: Any, exec_doc: Any
) -> list[Any]:
	pool = _programme_charges_for_lifecycle(sp_doc, lifecycle_row)
	exec_items: set[str] = set()
	for ch in getattr(exec_doc, "charges", None) or []:
		ic = _norm(getattr(ch, "item_code", None))
		if ic:
			exec_items.add(ic)
	if exec_items:
		pool = [ch for ch in pool if _norm(getattr(ch, "item_code", None)) in exec_items]
	return [
		ch
		for ch in pool
		if programme_charge_applies_to_planning_lifecycle(sp_doc, ch, lifecycle_row)
	]


def _planned_programme_charge_qty(charge: Any) -> float:
	"""Default programme qty before any execution has posted."""
	mq = flt(getattr(charge, "minimum_quantity", 0))
	if mq > 0:
		return mq
	return 1.0


def _posted_qty_total_for_charge(sp_doc: Any, charge_idx: int) -> float:
	total = 0.0
	for log in sp_doc.get("charge_execution_logs") or []:
		if frappe.utils.cint(getattr(log, "charge_idx", 0) or 0) != charge_idx:
			continue
		if (getattr(log, "status", None) or "") != POSTED_LOG_STATUS:
			continue
		total += flt(getattr(log, "qty", 0) or 1)
	return total


def _apply_programme_charge_qty_from_logs(sp_doc: Any, charge: Any) -> None:
	"""Set programme charge qty from posted execution logs (execution count)."""
	charge_idx = frappe.utils.cint(getattr(charge, "idx", 0) or 0)
	if not charge_idx:
		return
	posted_total = _posted_qty_total_for_charge(sp_doc, charge_idx)
	if posted_total > 0:
		charge.quantity = posted_total
	else:
		charge.quantity = _planned_programme_charge_qty(charge)
	if hasattr(charge, "cost_quantity"):
		charge.cost_quantity = flt(getattr(charge, "quantity", 0))


def _recalculate_programme_charge(charge: Any, sp_doc: Any) -> None:
	"""Recalculate actual revenue/cost from execution qty; leave estimated (quote plan) unchanged."""
	apply_charge_type_side_cleanup(charge)
	rev = calculate_charge_revenue(charge, sp_doc)
	cost = calculate_charge_cost(charge, sp_doc)
	if hasattr(charge, "actual_revenue"):
		charge.actual_revenue = flt(rev.get("amount", 0))
	if hasattr(charge, "actual_cost"):
		charge.actual_cost = flt(cost.get("amount", 0))
	if hasattr(charge, "revenue_calc_notes"):
		charge.revenue_calc_notes = rev.get("calc_notes", "") or ""
	if hasattr(charge, "cost_calc_notes"):
		charge.cost_calc_notes = cost.get("calc_notes", "") or ""
	if hasattr(charge, "cost_quantity") and hasattr(charge, "quantity"):
		charge.cost_quantity = flt(getattr(charge, "quantity", 0))


def _execution_log_exists(
	sp_doc: Any, exec_doc: Any, charge: Any, *, posted_only: bool = True
) -> bool:
	exec_name = _norm(getattr(exec_doc, "name", None))
	charge_idx = frappe.utils.cint(getattr(charge, "idx", 0) or 0)
	if not exec_name or not charge_idx:
		return False
	for log in sp_doc.get("charge_execution_logs") or []:
		if _norm(getattr(log, "job_no", None)) != exec_name:
			continue
		if frappe.utils.cint(getattr(log, "charge_idx", 0) or 0) != charge_idx:
			continue
		if posted_only and (getattr(log, "status", None) or "") != POSTED_LOG_STATUS:
			continue
		return True
	return False


def _append_execution_log(
	sp_doc: Any,
	charge: Any,
	lifecycle_row: Any,
	exec_doc: Any,
	qty: float,
) -> None:
	order_key = _planning_order_key_for_execution_log(lifecycle_row, exec_doc)
	order_type, order_no = order_key if order_key else ("", "")
	sp_doc.append(
		"charge_execution_logs",
		{
			"charge_idx": frappe.utils.cint(getattr(charge, "idx", 0) or 0),
			"item_code": getattr(charge, "item_code", None),
			"item_name": getattr(charge, "item_name", None),
			"service_type": getattr(charge, "service_type", None),
			"qty": flt(qty) or 1,
			"status": POSTED_LOG_STATUS,
			"posted_on": now_datetime(),
			"lifecycle_stage": getattr(lifecycle_row, "lifecycle_stage", None),
			"job_type": order_type or None,
			"order_no": order_no or None,
			"job_no": exec_doc.name,
		},
	)


def _set_lifecycle_planning_execution_link(
	planning_row: Any, exec_doc: Any
) -> None:
	"""Store the submitted shipment/job name on the planning lifecycle row."""
	if not planning_row or not exec_doc:
		return
	planning_row.job_no = exec_doc.name


def _clear_lifecycle_execution_link_if_no_posted_logs(
	sp_doc: Any, lifecycle_row: Any
) -> None:
	line_name = _norm(getattr(lifecycle_row, "name", None))
	if not line_name:
		return
	for log in sp_doc.get("charge_execution_logs") or []:
		if _norm(getattr(log, "lifecycle_stage", None)) != _norm(
			getattr(lifecycle_row, "lifecycle_stage", None)
		):
			continue
		if (getattr(log, "status", None) or "") == POSTED_LOG_STATUS:
			return
	to_remove: list[Any] = []
	for row in service_rows(sp_doc):
		if _norm(getattr(row, "special_project_service_line", None)) != line_name:
			continue
		to_remove.append(row)
	for row in to_remove:
		sp_doc.remove(row)


def post_charge_execution_for_doc(doc: Any, qty_delta: float = 1.0) -> int:
	"""Increment programme charge qty and append execution logs for one submitted job/shipment."""
	sp_doc, lifecycle_row = resolve_lifecycle_row_for_execution_doc(doc)
	if not sp_doc or not lifecycle_row:
		return 0

	posted = 0
	for charge in _matching_programme_charges(sp_doc, lifecycle_row, doc):
		item_code = _norm(getattr(charge, "item_code", None))
		if not item_code:
			continue
		if _execution_log_exists(sp_doc, doc, charge):
			continue
		_append_execution_log(sp_doc, charge, lifecycle_row, doc, qty_delta or 1)
		_apply_programme_charge_qty_from_logs(sp_doc, charge)
		_recalculate_programme_charge(charge, sp_doc)
		posted += 1

	if not posted:
		return 0

	_set_lifecycle_planning_execution_link(lifecycle_row, doc)
	sp_doc.flags.ignore_validate = True
	sp_doc.flags.ignore_charges_sync = True
	sync_lifecycle_job_financials(sp_doc)
	sp_doc.save(ignore_permissions=True)
	return posted


def cancel_charge_execution_for_doc(doc: Any) -> int:
	"""Reverse programme charge qty and cancel execution logs for a cancelled job/shipment."""
	sp_doc, lifecycle_row = resolve_lifecycle_row_for_execution_doc(doc)
	if not sp_doc:
		return 0

	exec_name = doc.name
	changed = 0
	affected_charge_idxs: set[int] = set()
	charges_by_idx: dict[int, Any] = {
		frappe.utils.cint(getattr(ch, "idx", 0) or 0): ch
		for ch in sp_doc.get("charges") or []
	}

	for log in sp_doc.get("charge_execution_logs") or []:
		if _norm(getattr(log, "job_no", None)) != exec_name:
			continue
		if (getattr(log, "status", None) or "") != POSTED_LOG_STATUS:
			continue
		log.status = CANCELLED_LOG_STATUS
		changed += 1
		idx = frappe.utils.cint(getattr(log, "charge_idx", 0) or 0)
		if idx:
			affected_charge_idxs.add(idx)

	for charge_idx in affected_charge_idxs:
		charge = charges_by_idx.get(charge_idx)
		if not charge:
			continue
		_apply_programme_charge_qty_from_logs(sp_doc, charge)
		_recalculate_programme_charge(charge, sp_doc)

	if not changed:
		return 0

	if lifecycle_row:
		_clear_lifecycle_execution_link_if_no_posted_logs(sp_doc, lifecycle_row)

	sp_doc.flags.ignore_validate = True
	sp_doc.flags.ignore_charges_sync = True
	if lifecycle_row:
		sync_lifecycle_job_financials(sp_doc)
	sp_doc.save(ignore_permissions=True)
	return changed


def _service_row_for_execution_log(sp_doc: Any, log: Any) -> Any | None:
	stage = _norm(getattr(log, "lifecycle_stage", None))
	if stage:
		for row in planning_service_rows(sp_doc):
			if _norm(getattr(row, "lifecycle_stage", None)) == stage:
				return row
	line_name = _norm(getattr(log, "special_project_service_line", None))
	if line_name:
		return service_row_by_name(sp_doc, line_name)
	return None


def resolve_programme_charge_for_execution_log(
	sp_doc: Any, log: Any, lifecycle_row: Any | None = None
) -> Any | None:
	"""Resolve the programme charge row that should own an execution log entry."""
	item_code = _norm(getattr(log, "item_code", None))
	if not item_code:
		return None

	lifecycle_row = lifecycle_row or _service_row_for_execution_log(sp_doc, log)
	if not lifecycle_row:
		idx = frappe.utils.cint(getattr(log, "charge_idx", 0) or 0)
		if idx:
			for ch in sp_doc.get("charges") or []:
				if frappe.utils.cint(getattr(ch, "idx", 0) or 0) == idx:
					return ch
		for ch in sp_doc.get("charges") or []:
			if _norm(getattr(ch, "item_code", None)) == item_code:
				return ch
		return None

	for charge in sp_doc.get("charges") or []:
		if _norm(getattr(charge, "item_code", None)) != item_code:
			continue
		if programme_charge_applies_to_planning_lifecycle(
			sp_doc, charge, lifecycle_row
		):
			return charge
	return None


def reconcile_programme_charge_qty_from_execution_logs(sp_doc: Any) -> int:
	"""Rebuild programme charge qty and amounts from posted execution logs."""
	logs = [
		log
		for log in sp_doc.get("charge_execution_logs") or []
		if (getattr(log, "status", None) or "") == POSTED_LOG_STATUS
	]
	if not logs:
		return 0

	charges_by_idx: dict[int, Any] = {
		frappe.utils.cint(getattr(ch, "idx", 0) or 0): ch
		for ch in sp_doc.get("charges") or []
	}
	posted_qty: dict[int, float] = {}
	changed = 0

	for log in sorted(logs, key=lambda row: frappe.utils.cint(getattr(row, "idx", 0) or 0)):
		lifecycle_row = _service_row_for_execution_log(sp_doc, log)
		charge = resolve_programme_charge_for_execution_log(sp_doc, log, lifecycle_row)
		if not charge:
			continue
		charge_idx = frappe.utils.cint(getattr(charge, "idx", 0) or 0)
		if not charge_idx:
			continue
		log.charge_idx = charge_idx
		posted_qty[charge_idx] = posted_qty.get(charge_idx, 0.0) + flt(
			getattr(log, "qty", 0) or 1
		)
		changed += 1

	for charge_idx, qty_total in posted_qty.items():
		charge = charges_by_idx.get(charge_idx)
		if not charge:
			continue
		charge.quantity = flt(qty_total)
		if hasattr(charge, "cost_quantity"):
			charge.cost_quantity = charge.quantity
		_recalculate_programme_charge(charge, sp_doc)

	return changed


def on_execution_doc_submit(doc: Any, method: str | None = None) -> None:
	try:
		n = post_charge_execution_for_doc(doc)
		if n:
			frappe.msgprint(
				frappe._("Updated {0} programme charge line(s) on Special Project.").format(n),
				indicator="green",
				alert=True,
			)
	except Exception:
		frappe.log_error(
			frappe.get_traceback(),
			f"{getattr(doc, 'doctype', '?')} {getattr(doc, 'name', '?')}: charge execution post",
		)


def on_execution_doc_cancel(doc: Any, method: str | None = None) -> None:
	try:
		cancel_charge_execution_for_doc(doc)
	except Exception:
		frappe.log_error(
			frappe.get_traceback(),
			f"{getattr(doc, 'doctype', '?')} {getattr(doc, 'name', '?')}: charge execution cancel",
		)
