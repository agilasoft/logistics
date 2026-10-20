# Copyright (c) 2026, AgilaSoft and contributors
# For license information, please see license.txt

"""Condition and limit helpers for Bulk Update Studio.

These functions only translate the visual builder into the JSON filter
format that Frappe Bulk Update already parses. They do not select or
update records.

Source of truth (Frappe v16):
frappe/desk/doctype/bulk_update/bulk_update.py

- limit = self.limit if self.limit and cint(self.limit) < 500 else 500
- condition is parsed with frappe.parse_json and passed to frappe.get_all
- a dict may contain "or_filters", which is popped onto get_all's or_filters
- 20 or more matching names are queued; fewer than 20 run immediately
"""

from __future__ import annotations

import json
import re

# frappe/public/js/frappe/model/model.js — frappe.model.no_value_type (version-16)
NO_VALUE_TYPES = frozenset(
	{
		"Section Break",
		"Column Break",
		"Tab Break",
		"Attachment Gallery",
		"HTML",
		"Table",
		"Table MultiSelect",
		"Button",
		"Image",
		"Fold",
		"Heading",
	}
)

# Comparison and list operators accepted by frappe.database.operator_map.OPERATOR_MAP.
# Arithmetic, regex, timespan, and nested-set operators are intentionally omitted.
ALLOWED_OPERATORS = (
	"=",
	"!=",
	">",
	"<",
	">=",
	"<=",
	"like",
	"not like",
	"in",
	"not in",
	"between",
	"is",
)

OPERATOR_LABELS = (
	{"value": "=", "label": "Equals"},
	{"value": "!=", "label": "Not Equals"},
	{"value": ">", "label": "Greater Than"},
	{"value": "<", "label": "Less Than"},
	{"value": ">=", "label": "Greater or Equal"},
	{"value": "<=", "label": "Less or Equal"},
	{"value": "like", "label": "Like"},
	{"value": "not like", "label": "Not Like"},
	{"value": "in", "label": "In"},
	{"value": "not in", "label": "Not In"},
	{"value": "between", "label": "Between"},
	{"value": "is", "label": "Is"},
)

# Same numbers BulkUpdate.bulk_update and submit_cancel_or_update_docs use.
DEFAULT_LIMIT = 500
MAX_LIMIT = 500
BACKGROUND_MIN_RECORDS = 20

FIELDNAME_RE = re.compile(r"^[A-Za-z0-9_]+$")
LONG_TEXT_TYPES = frozenset(
	{
		"Text",
		"Small Text",
		"Long Text",
		"Text Editor",
		"Code",
		"Markdown Editor",
		"HTML Editor",
		"HTML",
		"JSON",
		"Geolocation",
	}
)


def coerce_limit(limit) -> int:
	"""Match BulkUpdate.bulk_update's limit expression, including cint()."""
	number = _cint(limit)
	if number and number < MAX_LIMIT:
		return number
	return MAX_LIMIT


def _cint(value, default=0) -> int:
	if value is None or isinstance(value, bool):
		return int(value) if isinstance(value, bool) else default
	try:
		return int(value)
	except Exception:
		try:
			return int(float(value))
		except Exception:
			return default


def normalize_update_value(value, fieldtype: str) -> str:
	"""String value stored in Bulk Update.update_value (Small Text)."""
	if fieldtype == "Check":
		if value is True or value == 1:
			return "1"
		text = str(value).strip().lower() if value is not None else ""
		return "1" if text in {"1", "true", "yes", "on"} else "0"
	if value is None:
		return ""
	text = str(value)
	if fieldtype not in LONG_TEXT_TYPES:
		text = text.strip()
	return text


def build_condition_from_rows(rows) -> str:
	"""Turn visual rows into a JSON filter list Bulk Update can parse.

	Empty input returns "" so Bulk Update keeps its unfiltered behavior.
	Multiple rows become one AND list. OR and nested groups belong in the
	advanced JSON, which already supports an ``or_filters`` key.
	"""
	if isinstance(rows, str):
		if not rows.strip():
			return ""
		try:
			rows = json.loads(rows)
		except json.JSONDecodeError as exc:
			raise ValueError("Condition rows are not valid JSON.") from exc
	if not rows:
		return ""
	if not isinstance(rows, (list, tuple)):
		raise ValueError("Conditions must be a list of field, operator, and value.")

	filters = []
	for row in rows:
		if not isinstance(row, dict):
			raise ValueError("Each condition must include a field, an operator, and a value.")
		field = str(row.get("field") or "").strip()
		operator = str(row.get("operator") or "=").strip()
		value = row.get("value")
		value_to = row.get("value_to")
		if not field and _is_empty(value) and _is_empty(value_to):
			continue
		if not field:
			raise ValueError("Each condition needs a field.")
		if not FIELDNAME_RE.match(field):
			raise ValueError(f"The condition field {field} is not a valid fieldname.")
		if operator not in ALLOWED_OPERATORS:
			raise ValueError(f"The operator {operator} is not supported by Bulk Update.")
		filters.append(_filter_row(field, operator, value, value_to))

	if not filters:
		return ""
	return json.dumps(filters, ensure_ascii=False)


def validate_condition_json(condition) -> str:
	"""Accept the original Bulk Update condition text and return it unchanged."""
	if condition is None:
		return ""
	text = str(condition).strip()
	if not text:
		return ""
	try:
		parsed = json.loads(text)
	except json.JSONDecodeError as exc:
		raise ValueError(
			'Condition must be valid JSON. Example: {"status": "Open", "priority": "High"}'
		) from exc
	if isinstance(parsed, dict):
		or_filters = parsed.get("or_filters")
		if "or_filters" in parsed and not isinstance(or_filters, (dict, list)):
			raise ValueError("or_filters must be a JSON object or a list of filters.")
		return text
	if isinstance(parsed, list):
		return text
	raise ValueError("Condition must be a JSON object or a list of filters.")


def split_condition_args(condition_text: str) -> dict:
	"""Mirror BulkUpdate.bulk_update's filter argument assembly for read-only preview."""
	text = (condition_text or "").strip()
	if not text:
		return {}
	parsed = json.loads(text)
	args = {}
	filters = parsed
	if isinstance(filters, dict) and "or_filters" in filters:
		filters = dict(filters)
		args["or_filters"] = filters.pop("or_filters")
	args["filters"] = filters
	return args


def _filter_row(field: str, operator: str, value, value_to):
	if operator == "is":
		choice = str(value or "").strip().lower()
		if choice not in {"set", "not set"}:
			raise ValueError('Use "set" or "not set" for the Is operator.')
		return [field, "is", choice]
	if operator == "between":
		if _is_empty(value) or _is_empty(value_to):
			raise ValueError("Between needs a start value and an end value.")
		return [field, "between", [_plain(value), _plain(value_to)]]
	if operator in {"in", "not in"}:
		parts = _as_list(value)
		if not parts:
			raise ValueError(f"Enter one or more values for {operator}.")
		return [field, operator, parts]
	if _is_empty(value):
		raise ValueError(f"Enter a value for {field}.")
	return [field, operator, _plain(value)]


def _as_list(value) -> list:
	if isinstance(value, (list, tuple)):
		return [_plain(item) for item in value if not _is_empty(item)]
	if value is None:
		return []
	return [_plain(part) for part in str(value).split(",") if str(part).strip()]


def _plain(value):
	if isinstance(value, bool):
		return int(value)
	if isinstance(value, (int, float)) and not isinstance(value, bool):
		return value
	return str(value).strip()


def _is_empty(value) -> bool:
	return value is None or (isinstance(value, str) and value.strip() == "")
