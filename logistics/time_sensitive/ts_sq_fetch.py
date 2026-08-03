# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Fetch shared fields + charges between Sales Quote and Time Sensitive Case.

Design: ts_sq_fetch_dialog_v1 (free-edit)
  - No global mode cards
  - Every row editable
  - Per-row direction (from_quote / to_quote)
  - Action buttons: Fill / Add / Replace / Skip
  - Optional replace-all-charges flag on apply
"""

from __future__ import annotations

import json
from typing import Any

import frappe
from frappe import _
from frappe.utils import cint, flt, strip_html

DIRECTIONS = ("from_quote", "to_quote")

FIELD_MAP = (
	{
		"key": "case_type",
		"label": "Case type",
		"case": "case_type",
		"quote": "ts_case_type",
		"fieldtype": "Link",
		"options": "Time Sensitive Case Type",
	},
	{
		"key": "cargo_summary",
		"label": "Cargo summary",
		"case": "cargo_summary",
		"quote": "special_handling_instructions",
		"quote_fallbacks": ("description", "scope_title"),
		"fieldtype": "Small Text",
	},
	{
		"key": "notes",
		"label": "Notes",
		"case": "notes",
		"quote": "internal_notes",
		"quote_fallbacks": ("external_notes",),
		"fieldtype": "Small Text",
	},
	{
		"key": "origin",
		"label": "Origin",
		"case": "origin",
		"quote": "origin_port",
		"fieldtype": "Link",
		"options": "UNLOCO",
	},
	{
		"key": "destination",
		"label": "Destination",
		"case": "destination",
		"quote": "destination_port",
		"fieldtype": "Link",
		"options": "UNLOCO",
	},
	{
		"key": "priority",
		"label": "Priority",
		"case": "priority",
		"quote": "priority",
		"fieldtype": "Select",
		"options": "Low\nNormal\nHigh\nUrgent",
	},
	{
		"key": "critical_deadline",
		"label": "Critical deadline",
		"case": "critical_deadline",
		"quote": "critical_deadline",
		"fieldtype": "Data",
	},
	{
		"key": "customer",
		"label": "Customer",
		"case": "customer",
		"quote": "customer",
		"fieldtype": "Link",
		"options": "Customer",
	},
	{
		"key": "company",
		"label": "Company",
		"case": "company",
		"quote": "company",
		"fieldtype": "Link",
		"options": "Company",
	},
	{
		"key": "branch",
		"label": "Branch",
		"case": "branch",
		"quote": "branch",
		"fieldtype": "Link",
		"options": "Branch",
	},
	{
		"key": "cost_center",
		"label": "Cost center",
		"case": "cost_center",
		"quote": "cost_center",
		"fieldtype": "Link",
		"options": "Cost Center",
	},
	{
		"key": "profit_center",
		"label": "Profit center",
		"case": "profit_center",
		"quote": "profit_center",
		"fieldtype": "Link",
		"options": "Profit Center",
	},
)

FIELD_BY_KEY = {m["key"]: m for m in FIELD_MAP}


def _blank(val) -> bool:
	if val is None:
		return True
	if isinstance(val, str):
		return not strip_html(val).strip()
	return False


def _display(val) -> str:
	if _blank(val):
		return ""
	if isinstance(val, str):
		text = strip_html(val).strip()
		if len(text) > 80:
			return text[:77] + "…"
		return text
	return str(val)


def _plain(val) -> str:
	if _blank(val):
		return ""
	if isinstance(val, str):
		return strip_html(val).strip()
	return str(val)


def _fmt_qty_rate(qty, rate, currency=None) -> str:
	q = flt(qty) if qty is not None else 0
	r = flt(rate) if rate is not None else 0
	cur = f" {currency}" if currency else ""
	return f"{q:g} × {r:,.2f}{cur}".strip()


def _fmt_amount(amount, currency=None) -> str:
	cur = f" {currency}" if currency else ""
	return f"{flt(amount):,.2f}{cur}".strip()


def _charge_fingerprint(item_code, qty, rate, linked_service=None) -> str:
	return "|".join(
		[
			(item_code or "").strip(),
			f"{flt(qty):.6f}",
			f"{flt(rate):.6f}",
			(linked_service or "").strip(),
		]
	)


def _get_attr(doc, field: str):
	return getattr(doc, field, None) if hasattr(doc, field) else None


def _quote_value(sq, mapping: dict) -> Any:
	val = _get_attr(sq, mapping["quote"])
	if not _blank(val):
		return val
	for fb in mapping.get("quote_fallbacks") or ():
		val = _get_attr(sq, fb)
		if not _blank(val):
			return val
	return None


def _case_value(case, mapping: dict) -> Any:
	return _get_attr(case, mapping["case"])


def _parse_json(value, default=None):
	if value is None:
		return default if default is not None else []
	if isinstance(value, (list, dict)):
		return value
	if isinstance(value, str):
		value = value.strip()
		if not value:
			return default if default is not None else []
		return json.loads(value)
	return default if default is not None else []


def _quote_charge_payload(ch) -> dict:
	qty = flt(getattr(ch, "quantity", None) or 0)
	rate = flt(getattr(ch, "unit_rate", None) or 0)
	amount = flt(getattr(ch, "base_amount", None) or 0)
	if not amount and qty and rate:
		amount = qty * rate
	item = getattr(ch, "item_code", None) or ""
	raw_desc = getattr(ch, "description", None) or ""
	desc = strip_html(raw_desc).strip() if raw_desc else ""
	desc = desc or item
	ls = getattr(ch, "linked_service", None) or ""
	currency = getattr(ch, "currency", None)
	return {
		"side": "quote",
		"name": ch.name,
		"label": desc or item or ch.name,
		"item_code": item,
		"description": desc,
		"qty": qty,
		"rate": rate,
		"amount": amount,
		"currency": currency,
		"service_type": getattr(ch, "service_type", None),
		"charge_scope": getattr(ch, "charge_scope", None) or "Main",
		"linked_service": ls,
		"fingerprint": _charge_fingerprint(item, qty, rate, ls),
		"display": _fmt_qty_rate(qty, rate, currency),
		"amount_display": _fmt_amount(amount, currency),
	}


def _case_charge_payload(ch) -> dict:
	qty = flt(getattr(ch, "qty", None) or 0)
	rate = flt(getattr(ch, "rate", None) or 0)
	amount = flt(getattr(ch, "amount", None) or 0)
	if not amount and qty and rate:
		amount = qty * rate
	item = getattr(ch, "item_code", None) or ""
	raw_desc = getattr(ch, "description", None) or ""
	desc = strip_html(raw_desc).strip() if raw_desc else ""
	desc = desc or item
	ls = getattr(ch, "linked_service", None) or ""
	currency = getattr(ch, "currency", None)
	return {
		"side": "case",
		"name": ch.name,
		"label": desc or item or ch.name,
		"item_code": item,
		"description": desc,
		"qty": qty,
		"rate": rate,
		"amount": amount,
		"currency": currency,
		"service_type": getattr(ch, "service_type", None),
		"charge_scope": getattr(ch, "charge_scope", None) or "Main",
		"linked_service": ls,
		"fingerprint": _charge_fingerprint(item, qty, rate, ls),
		"display": _fmt_qty_rate(qty, rate, currency),
		"amount_display": _fmt_amount(amount, currency),
	}


def _field_row_state(quote_val, case_val, default_direction: str) -> dict:
	"""Free-edit defaults: never hard-lock rows; preselect missing only."""
	q_blank = _blank(quote_val)
	c_blank = _blank(case_val)
	same = (not q_blank) and (not c_blank) and _plain(quote_val) == _plain(case_val)

	if default_direction == "from_quote":
		src_blank, tgt_blank = q_blank, c_blank
		direction = "from_quote"
	else:
		src_blank, tgt_blank = c_blank, q_blank
		direction = "to_quote"

	# No useful source either way → still editable, default skip
	if src_blank and tgt_blank:
		return {
			"direction": direction,
			"action": "skip",
			"reason": _("No values"),
			"selected": False,
			"enabled": True,
			"locked": False,
			"same": False,
		}

	if same:
		return {
			"direction": "—",
			"action": "skip",
			"reason": _("Already same"),
			"selected": False,
			"enabled": True,
			"locked": False,
			"same": True,
		}

	if src_blank:
		# Can still push the other way or type freely
		alt = "to_quote" if direction == "from_quote" else "from_quote"
		return {
			"direction": alt if not (q_blank if alt == "from_quote" else c_blank) else direction,
			"action": "skip",
			"reason": _("No source value"),
			"selected": False,
			"enabled": True,
			"locked": False,
			"same": False,
		}

	if tgt_blank:
		return {
			"direction": direction,
			"action": "fill",
			"reason": "",
			"selected": True,
			"enabled": True,
			"locked": False,
			"same": False,
		}

	# Both differ — preselect skip; user can Replace
	return {
		"direction": direction,
		"action": "skip",
		"reason": "",
		"selected": False,
		"enabled": True,
		"locked": False,
		"same": False,
	}


def _build_interactive_fields(case, sq, default_direction: str) -> list[dict]:
	rows = []
	for m in FIELD_MAP:
		q_val = _quote_value(sq, m)
		c_val = _case_value(case, m)
		state = _field_row_state(q_val, c_val, default_direction)

		# Working value in Case column (always the editable surface)
		working = _plain(c_val)
		if state["action"] == "fill" and state["direction"] == "from_quote":
			working = _plain(q_val) or working
		elif state["action"] == "fill" and state["direction"] == "to_quote":
			working = _plain(c_val)

		rows.append(
			{
				"key": m["key"],
				"label": _(m["label"]),
				"fieldtype": m.get("fieldtype") or "Data",
				"options": m.get("options") or "",
				"quote_value": _plain(q_val),
				"case_value": _plain(c_val),
				"quote_display": _display(q_val) or "",
				"case_display": _display(c_val) or "",
				"quote_empty": _blank(q_val),
				"case_empty": _blank(c_val),
				"working_value": working,
				**state,
			}
		)
	return rows


def _build_interactive_charges(case, sq, default_direction: str) -> list[dict]:
	quote_charges = [_quote_charge_payload(ch) for ch in (sq.get("charges") or [])]
	case_charges = [_case_charge_payload(ch) for ch in (case.get("charges") or [])]
	case_by_fp = {c["fingerprint"]: c for c in case_charges}
	quote_by_fp = {c["fingerprint"]: c for c in quote_charges}
	rows = []

	primary = quote_charges if default_direction == "from_quote" else case_charges
	for ch in primary:
		fp = ch["fingerprint"]
		if ch["side"] == "quote":
			q, c_match = ch, case_by_fp.get(fp)
		else:
			q, c_match = quote_by_fp.get(fp), ch

		on_quote = bool(q)
		on_case = bool(c_match)
		matched = on_quote and on_case

		if matched:
			action, reason, selected = "skip", _("Already same"), False
			direction = "—"
		elif default_direction == "from_quote":
			action, reason, selected = "add", "", True
			direction = "from_quote"
		else:
			action, reason, selected = "add", "", True
			direction = "to_quote"

		src = q if direction in ("from_quote", "—") and q else (c_match or ch)
		if direction == "to_quote":
			src = c_match or ch

		rows.append(
			{
				"row_id": f"{ch['side']}:{ch['name']}",
				"quote_row_name": q["name"] if q else None,
				"case_row_name": c_match["name"]
				if c_match
				else (ch["name"] if ch["side"] == "case" else None),
				"label": ch["label"],
				"item_code": ch["item_code"],
				"description": ch["description"],
				"service_type": ch.get("service_type"),
				"charge_scope": ch.get("charge_scope") or "Main",
				"linked_service": ch.get("linked_service") or "",
				"currency": ch.get("currency"),
				"fingerprint": fp,
				"quote_display": q["display"] if q else "",
				"quote_amount_display": q.get("amount_display") if q else "",
				"case_display": c_match["display"] if c_match else "",
				"on_quote": on_quote,
				"on_case": on_case,
				"matched": matched,
				"qty": flt(src.get("qty")),
				"rate": flt(src.get("rate")),
				"amount": flt(src.get("amount") or (flt(src.get("qty")) * flt(src.get("rate")))),
				"direction": direction,
				"action": action,
				"reason": reason,
				"selected": selected,
				"enabled": True,
				"locked": False,
			}
		)

	return rows


def _load_pair(case_name: str | None, quote_name: str | None, default_direction: str):
	if default_direction == "from_quote":
		if not case_name:
			frappe.throw(_("Time Sensitive Case is required"))
		case = frappe.get_doc("Time Sensitive Case", case_name)
		frappe.has_permission("Time Sensitive Case", "write", doc=case, throw=True)
		quote_name = quote_name or case.sales_quote
		if not quote_name:
			frappe.throw(_("This case has no linked Sales Quote"))
		sq = frappe.get_doc("Sales Quote", quote_name)
		frappe.has_permission("Sales Quote", "read", doc=sq, throw=True)
		return case, sq

	if not quote_name:
		frappe.throw(_("Sales Quote is required"))
	sq = frappe.get_doc("Sales Quote", quote_name)
	frappe.has_permission("Sales Quote", "write", doc=sq, throw=True)
	case_name = case_name or getattr(sq, "time_sensitive_case", None)
	if not case_name:
		frappe.throw(_("This Sales Quote has no linked Time Sensitive Case"))
	case = frappe.get_doc("Time Sensitive Case", case_name)
	frappe.has_permission("Time Sensitive Case", "read", doc=case, throw=True)
	return case, sq


def copy_charges_from_sales_quote_to_case(case, sq, *, clear_existing: bool = False) -> int:
	"""Copy all quote charges onto the case (used on create + replace-all)."""
	if clear_existing:
		case.set("charges", [])
	existing = {
		_charge_fingerprint(
			getattr(r, "item_code", None),
			getattr(r, "qty", None),
			getattr(r, "rate", None),
			getattr(r, "linked_service", None),
		)
		for r in (case.get("charges") or [])
	}
	added = 0
	for ch in sq.get("charges") or []:
		payload = _quote_charge_payload(ch)
		if not clear_existing and payload["fingerprint"] in existing:
			continue
		case.append(
			"charges",
			{
				"item_code": payload["item_code"],
				"description": payload["description"],
				"qty": payload["qty"] or 1,
				"rate": payload["rate"],
				"amount": payload["amount"] or (flt(payload["qty"]) * flt(payload["rate"])),
				"currency": payload["currency"],
				"service_type": payload["service_type"],
				"charge_scope": payload["charge_scope"] or "Main",
				"linked_service": payload["linked_service"] or None,
			},
		)
		existing.add(payload["fingerprint"])
		added += 1
	return added


def _append_quote_charge(sq, payload: dict) -> None:
	sq.append(
		"charges",
		{
			"item_code": payload.get("item_code"),
			"description": payload.get("description"),
			"quantity": payload.get("qty") or 1,
			"unit_rate": payload.get("rate") or 0,
			"base_amount": payload.get("amount")
			or (flt(payload.get("qty")) * flt(payload.get("rate"))),
			"currency": payload.get("currency"),
			"service_type": payload.get("service_type"),
			"charge_scope": payload.get("charge_scope") or "Main",
			"linked_service": payload.get("linked_service") or None,
			"charge_type": "Revenue",
		},
	)


@frappe.whitelist()
def preview_fetch(
	direction: str | None = None,
	source_name: str | None = None,
	target_name: str | None = None,
	case_name: str | None = None,
	sales_quote: str | None = None,
	mode: str | None = None,  # ignored — kept for API compatibility
):
	"""Preview free-edit fetch payload for ts_sq_fetch_dialog_v1."""
	direction = (direction or "quote_to_case").strip()
	if direction == "quote_to_case":
		default_direction = "from_quote"
		case_name = case_name or target_name
		sales_quote = sales_quote or source_name
	elif direction == "case_to_quote":
		default_direction = "to_quote"
		sales_quote = sales_quote or target_name
		case_name = case_name or source_name
	else:
		frappe.throw(_("Invalid fetch direction"))

	case, sq = _load_pair(case_name, sales_quote, default_direction)
	fields = _build_interactive_fields(case, sq, default_direction)
	charges = _build_interactive_charges(case, sq, default_direction)

	sel_fields = sum(1 for f in fields if f.get("selected"))
	sel_charges = sum(1 for c in charges if c.get("selected"))

	return {
		"direction": direction,
		"default_direction": default_direction,
		"case_name": case.name,
		"sales_quote": sq.name,
		"title": _("Fetch from Sales Quote")
		if default_direction == "from_quote"
		else _("Fetch from Time Sensitive Case"),
		"direction_label": f"{sq.name} → {case.name}"
		if default_direction == "from_quote"
		else f"{case.name} → {sq.name}",
		"fields": fields,
		"charges": charges,
		"summary": {
			"fields_to_update": sel_fields,
			"charges_to_update": sel_charges,
			"in_sync": sel_fields == 0 and sel_charges == 0,
			"safe": True,
		},
	}


@frappe.whitelist()
def apply_fetch(
	direction: str | None = None,
	source_name: str | None = None,
	target_name: str | None = None,
	case_name: str | None = None,
	sales_quote: str | None = None,
	field_rows=None,
	charge_rows=None,
	replace_all_charges: int | str | None = 0,
	mode: str | None = None,  # ignored
	field_keys=None,
	charge_names=None,
):
	"""Apply free-edit fetch rows (edited values + per-row direction)."""
	direction = (direction or "quote_to_case").strip()
	if direction == "quote_to_case":
		default_direction = "from_quote"
		case_name = case_name or target_name
		sales_quote = sales_quote or source_name
	elif direction == "case_to_quote":
		default_direction = "to_quote"
		sales_quote = sales_quote or target_name
		case_name = case_name or source_name
	else:
		frappe.throw(_("Invalid fetch direction"))

	case, sq = _load_pair(case_name, sales_quote, default_direction)
	frappe.has_permission("Time Sensitive Case", "write", doc=case, throw=True)
	frappe.has_permission("Sales Quote", "write", doc=sq, throw=True)

	field_rows = _parse_json(field_rows, [])
	charge_rows = _parse_json(charge_rows, [])
	replace_all = cint(replace_all_charges)

	# Legacy fallback
	if not field_rows and field_keys:
		for key in _parse_json(field_keys, []):
			field_rows.append(
				{
					"key": key,
					"direction": default_direction,
					"action": "fill",
					"selected": True,
					"value": None,
				}
			)
	if not charge_rows and charge_names:
		for name in _parse_json(charge_names, []):
			charge_rows.append(
				{
					"quote_row_name": name if default_direction == "from_quote" else None,
					"case_row_name": name if default_direction == "to_quote" else None,
					"direction": default_direction,
					"action": "add",
					"selected": True,
				}
			)

	case_dirty = False
	quote_dirty = False
	fields_updated = 0
	charges_updated = 0

	for row in field_rows or []:
		if not row.get("selected") or row.get("action") == "skip":
			continue
		key = row.get("key")
		mapping = FIELD_BY_KEY.get(key)
		if not mapping:
			continue
		row_dir = (row.get("direction") or default_direction).strip()
		if row_dir == "—":
			row_dir = default_direction
		if row_dir not in DIRECTIONS:
			continue

		value = row.get("value")
		if _blank(value):
			value = _quote_value(sq, mapping) if row_dir == "from_quote" else _case_value(case, mapping)
		if _blank(value):
			continue

		if row_dir == "from_quote":
			case.set(mapping["case"], value)
			case_dirty = True
			fields_updated += 1
		else:
			if cint(getattr(sq, "docstatus", 0)) != 0:
				frappe.throw(_("Cannot write to a submitted Sales Quote"))
			sq.set(mapping["quote"], value)
			quote_dirty = True
			fields_updated += 1

	if replace_all:
		# Product link: replace-all always copies quote → case
		charges_updated = copy_charges_from_sales_quote_to_case(case, sq, clear_existing=True)
		case_dirty = True
	else:
		case_fps = {
			_charge_fingerprint(
				getattr(r, "item_code", None),
				getattr(r, "qty", None),
				getattr(r, "rate", None),
				getattr(r, "linked_service", None),
			)
			for r in (case.get("charges") or [])
		}
		quote_fps = {
			_charge_fingerprint(
				getattr(r, "item_code", None),
				getattr(r, "quantity", None),
				getattr(r, "unit_rate", None),
				getattr(r, "linked_service", None),
			)
			for r in (sq.get("charges") or [])
		}
		quote_by_name = {ch.name: ch for ch in (sq.get("charges") or [])}
		case_by_name = {ch.name: ch for ch in (case.get("charges") or [])}

		for row in charge_rows or []:
			if not row.get("selected") or row.get("action") == "skip":
				continue
			row_dir = (row.get("direction") or default_direction).strip()
			if row_dir == "—":
				continue
			qty = flt(row.get("qty")) if row.get("qty") is not None else None
			rate = flt(row.get("rate")) if row.get("rate") is not None else None

			if row_dir == "from_quote":
				src = quote_by_name.get(row.get("quote_row_name"))
				if not src:
					continue
				payload = _quote_charge_payload(src)
				if qty is not None:
					payload["qty"] = qty
				if rate is not None:
					payload["rate"] = rate
				payload["amount"] = flt(payload["qty"]) * flt(payload["rate"])
				fp = _charge_fingerprint(
					payload["item_code"], payload["qty"], payload["rate"], payload.get("linked_service")
				)
				if fp in case_fps:
					continue
				case.append(
					"charges",
					{
						"item_code": payload["item_code"],
						"description": payload["description"],
						"qty": payload["qty"] or 1,
						"rate": payload["rate"],
						"amount": payload["amount"],
						"currency": payload["currency"],
						"service_type": payload["service_type"],
						"charge_scope": payload["charge_scope"] or "Main",
						"linked_service": payload["linked_service"] or None,
					},
				)
				case_fps.add(fp)
				case_dirty = True
				charges_updated += 1
			else:
				if cint(getattr(sq, "docstatus", 0)) != 0:
					frappe.throw(_("Cannot write to a submitted Sales Quote"))
				src = case_by_name.get(row.get("case_row_name"))
				if not src:
					continue
				payload = _case_charge_payload(src)
				if qty is not None:
					payload["qty"] = qty
				if rate is not None:
					payload["rate"] = rate
				payload["amount"] = flt(payload["qty"]) * flt(payload["rate"])
				fp = _charge_fingerprint(
					payload["item_code"], payload["qty"], payload["rate"], payload.get("linked_service")
				)
				if fp in quote_fps:
					continue
				_append_quote_charge(sq, payload)
				quote_fps.add(fp)
				quote_dirty = True
				charges_updated += 1

	if case_dirty:
		case.save()
	if quote_dirty:
		sq.save()

	return {
		"case_name": case.name,
		"sales_quote": sq.name,
		"fields_updated": fields_updated,
		"charges_updated": charges_updated,
		"message": _("Fetched {0} fields, {1} charges").format(fields_updated, charges_updated),
	}
