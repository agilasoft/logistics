# Copyright (c) 2026, Agilasoft and contributors
"""Persist charge-row Table MultiSelect (Frappe cannot store nested tables on istable rows)."""

from __future__ import annotations

from typing import Any, List, Optional, Tuple

import frappe

# (multiselect field on charge row, Selling|Cost, item|group, value field on child row)
MULTISELECT_FIELD_SPECS: Tuple[Tuple[str, str, str, str], ...] = (
	("selling_specified_items", "Selling", "item", "item_code"),
	("cost_specified_items", "Cost", "item", "item_code"),
	("selling_specified_charge_groups", "Selling", "group", "charge_group"),
	("cost_specified_charge_groups", "Cost", "group", "charge_group"),
)


def _multiselect_rows_from_charge_doc(charge_doc: Any, fieldname: str) -> List[dict]:
	rows = charge_doc.__dict__.get(fieldname)
	if rows is None:
		rows = charge_doc.get(fieldname)
	if not rows:
		return []
	if not isinstance(rows, list):
		return []
	out: List[dict] = []
	for row in rows:
		if isinstance(row, dict):
			out.append(row)
		else:
			out.append(row.as_dict() if hasattr(row, "as_dict") else dict(row))
	return out


def persist_charge_row_specified_selections(charge_doc: Any) -> None:
	"""Write virtual multiselect rows to Sales Quote Specified Charge reference rows."""
	if not charge_doc or not getattr(charge_doc, "name", None):
		return
	if charge_doc.name.startswith("new-"):
		return

	reference_doctype = charge_doc.doctype
	reference_no = charge_doc.name

	for fieldname, record_type, kind, value_field in MULTISELECT_FIELD_SPECS:
		rows = _multiselect_rows_from_charge_doc(charge_doc, fieldname)
		_delete_reference_rows(reference_doctype, reference_no, record_type, kind)
		for row in rows:
			val = (row.get(value_field) or "").strip()
			if not val:
				continue
			doc = frappe.new_doc("Sales Quote Specified Charge")
			doc.reference_doctype = reference_doctype
			doc.reference_no = reference_no
			doc.type = record_type
			doc.selection_kind = "Item" if kind == "item" else "Charge Group"
			if kind == "item":
				doc.item_code = val
			else:
				doc.charge_group = val
			doc.insert(ignore_permissions=True)


def _delete_reference_rows(
	reference_doctype: str, reference_no: str, record_type: str, kind: str
) -> None:
	selection_kind = "Item" if kind == "item" else "Charge Group"
	frappe.db.delete(
		"Sales Quote Specified Charge",
		{
			"reference_doctype": reference_doctype,
			"reference_no": reference_no,
			"type": record_type,
			"selection_kind": selection_kind,
		},
	)


def load_specified_items(reference_doctype: str, reference_no: str, record_type: str) -> List[str]:
	return _load_reference_values(reference_doctype, reference_no, record_type, "Item", "item_code")


def load_specified_charge_groups(
	reference_doctype: str, reference_no: str, record_type: str
) -> List[str]:
	return _load_reference_values(
		reference_doctype, reference_no, record_type, "Charge Group", "charge_group"
	)


def _load_reference_values(
	reference_doctype: str,
	reference_no: str,
	record_type: str,
	selection_kind: str,
	value_field: str,
) -> List[str]:
	if not reference_doctype or not reference_no:
		return []
	rows = frappe.get_all(
		"Sales Quote Specified Charge",
		filters={
			"reference_doctype": reference_doctype,
			"reference_no": reference_no,
			"type": record_type,
			"selection_kind": selection_kind,
		},
		fields=[value_field],
		order_by="creation asc",
	)
	values: List[str] = []
	seen = set()
	for row in rows or []:
		val = (row.get(value_field) or "").strip()
		if val and val not in seen:
			values.append(val)
			seen.add(val)
	return values


def on_charge_row_validate(charge_doc: Any, method: Optional[str] = None) -> None:
	persist_charge_row_specified_selections(charge_doc)
