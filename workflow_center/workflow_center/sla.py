# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""SLA settings stored as custom fields on Workflow State.

The dashboard must keep loading when those columns are not on the site yet.
"""

from __future__ import annotations

from typing import Any, Callable

SLA_COLUMNS = ("wc_sla_enabled", "wc_sla_unit", "wc_sla_value")

WORKFLOW_STATE_SLA_FIELDS = [
	{
		"fieldname": "wc_sla_section",
		"label": "Workflow Center SLA",
		"fieldtype": "Section Break",
		"insert_after": "style",
		"module": "Workflow Center",
	},
	{
		"fieldname": "wc_sla_enabled",
		"label": "Enable SLA",
		"fieldtype": "Check",
		"insert_after": "wc_sla_section",
		"default": "0",
		"description": "When enabled, Workflow Center treats time in this state as time-bound.",
		"module": "Workflow Center",
	},
	{
		"fieldname": "wc_sla_unit",
		"label": "SLA Unit",
		"fieldtype": "Select",
		"options": "Hours\nDays",
		"default": "Hours",
		"insert_after": "wc_sla_enabled",
		"depends_on": "eval:doc.wc_sla_enabled",
		"mandatory_depends_on": "eval:doc.wc_sla_enabled",
		"module": "Workflow Center",
	},
	{
		"fieldname": "wc_sla_value",
		"label": "SLA Duration",
		"fieldtype": "Float",
		"insert_after": "wc_sla_unit",
		"depends_on": "eval:doc.wc_sla_enabled",
		"mandatory_depends_on": "eval:doc.wc_sla_enabled",
		"description": "How long a document may stay in this state before it is overdue.",
		"module": "Workflow Center",
	},
]


def sla_columns_ready(has_column: Callable[[str, str], bool], doctype: str = "Workflow State") -> bool:
	return all(has_column(doctype, column) for column in SLA_COLUMNS)


def is_unknown_column_error(exc: BaseException) -> bool:
	seen: set[int] = set()
	current: BaseException | None = exc
	while current is not None and id(current) not in seen:
		seen.add(id(current))
		args = getattr(current, "args", ())
		if args and args[0] == 1054:
			return True
		current = current.__cause__ or current.__context__
	return False


def sla_config_from_row(row: dict[str, Any] | None) -> dict[str, Any]:
	if not row or not row.get("wc_sla_enabled"):
		return {"enabled": False}
	return {
		"enabled": True,
		"unit": row.get("wc_sla_unit") or "Hours",
		"value": _as_float(row.get("wc_sla_value")),
	}


def load_sla_config(
	workflow_state: str | None,
	has_column: Callable[[str, str], bool],
	get_value: Callable[..., Any],
) -> dict[str, Any]:
	"""Read one state's SLA. Missing columns mean SLA is off, not a failed dashboard."""
	if not workflow_state or not sla_columns_ready(has_column):
		return {"enabled": False}
	try:
		row = get_value("Workflow State", workflow_state, list(SLA_COLUMNS), as_dict=True)
	except Exception as exc:
		if is_unknown_column_error(exc):
			return {"enabled": False}
		raise
	return sla_config_from_row(row)


def _as_float(value: Any) -> float:
	if value in (None, ""):
		return 0.0
	try:
		return float(value)
	except (TypeError, ValueError):
		return 0.0
