# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Validate List Settings values before they are stored.

Kept free of Frappe imports so the checks can run without a site.
"""

from __future__ import annotations

import json

CHECKBOX_FIELDS = (
	"disable_count",
	"disable_auto_refresh",
	"disable_sidebar_stats",
	"disable_automatic_recency_filters",
	"show_tags",
	"disable_comment_count",
	"disable_scrolling",
	"allow_edit",
)

MAX_COLUMNS = 50
MAX_LABEL_LENGTH = 140
MAX_WIDTH = 2000
MAX_FIELDS_CHARS = 20000
STATUS_FIELD = "status_field"


class ListSettingsPayloadError(ValueError):
	pass


def sanitize_listview_payload(settings, valid_fieldnames) -> dict:
	"""Return only the List View Settings keys a role editor is allowed to change."""
	if settings is None:
		settings = {}
	if not isinstance(settings, dict):
		raise ListSettingsPayloadError("List settings must be an object.")

	payload = {}
	for key in CHECKBOX_FIELDS:
		if key not in settings or settings[key] in (None, ""):
			continue
		payload[key] = _checkbox(key, settings[key])

	if "fields" in settings and settings["fields"] not in (None, ""):
		payload["fields"] = _fields_json(settings["fields"], valid_fieldnames)
	return payload


def sanitize_removed_fields(removed, valid_fieldnames) -> list[str]:
	if removed in (None, ""):
		return []
	if not isinstance(removed, list):
		raise ListSettingsPayloadError("Removed fields must be a list.")
	names = []
	for field in removed:
		if not isinstance(field, str) or not field or field not in valid_fieldnames:
			raise ListSettingsPayloadError("Removed field is not on this document type.")
		names.append(field)
	return names


def _checkbox(key: str, value) -> int:
	if isinstance(value, str):
		token = value.strip().lower()
		if token in ("0", "false", "no"):
			return 0
		if token in ("1", "true", "yes"):
			return 1
	if value in (0, 1, True, False):
		return 1 if value else 0
	raise ListSettingsPayloadError(f"Invalid value for {key}.")


def _fields_json(raw, valid_fieldnames) -> str:
	if isinstance(raw, str):
		if len(raw) > MAX_FIELDS_CHARS:
			raise ListSettingsPayloadError("Column list is too large.")
		try:
			parsed = json.loads(raw)
		except json.JSONDecodeError as exc:
			raise ListSettingsPayloadError("Column list is not valid.") from exc
	elif isinstance(raw, list):
		parsed = raw
	else:
		raise ListSettingsPayloadError("Column list is not valid.")

	if not isinstance(parsed, list):
		raise ListSettingsPayloadError("Column list is not valid.")
	if len(parsed) > MAX_COLUMNS:
		raise ListSettingsPayloadError(f"Choose at most {MAX_COLUMNS} columns.")

	cleaned = []
	seen = set()
	for row in parsed:
		if not isinstance(row, dict):
			raise ListSettingsPayloadError("Each column must be an object.")
		fieldname = row.get("fieldname")
		if not isinstance(fieldname, str) or fieldname not in valid_fieldnames:
			raise ListSettingsPayloadError("A selected column is not on this document type.")
		if fieldname in seen:
			continue
		seen.add(fieldname)
		item = {"fieldname": fieldname}
		label = row.get("label")
		if isinstance(label, str) and label.strip():
			item["label"] = label.strip()[:MAX_LABEL_LENGTH]
		else:
			item["label"] = fieldname
		if "width" in row and row["width"] not in (None, "", 0, "0"):
			item["width"] = _width(row["width"])
		if fieldname == STATUS_FIELD and row.get("type") == "Status":
			item["type"] = "Status"
		cleaned.append(item)
	return json.dumps(cleaned)


def _width(value) -> int:
	if isinstance(value, bool) or not isinstance(value, (int, float, str)):
		raise ListSettingsPayloadError("Column width is not a number.")
	try:
		width = int(value)
	except (TypeError, ValueError) as exc:
		raise ListSettingsPayloadError("Column width is not a number.") from exc
	if width < 1 or width > MAX_WIDTH:
		raise ListSettingsPayloadError("Column width is out of range.")
	return width
