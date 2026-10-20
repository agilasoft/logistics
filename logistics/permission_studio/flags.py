# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Small helpers that do not import Frappe, so they can be tested on their own."""


def as_flag(value) -> int:
	"""Coerce a Frappe checkbox value to 0 or 1.

	Frappe sends checkboxes as ints, bools, or the strings ``"0"`` and ``"1"``.
	A non-empty string must not be treated as true.
	"""
	if value is None or value is False:
		return 0
	if value is True:
		return 1
	if isinstance(value, (int, float)):
		return 1 if int(value) else 0
	return 1 if str(value).strip().lower() in {"1", "true", "yes"} else 0


def clean_text(value) -> str:
	return " ".join(str(value or "").split())


def parse_payload(value, fallback):
	"""Accept a dict or list, or the JSON string Frappe sends from the desk."""
	import json

	if isinstance(fallback, dict):
		fallback = dict(fallback)
	elif isinstance(fallback, list):
		fallback = list(fallback)
	if value is None or value == "":
		return fallback
	if isinstance(value, str):
		return json.loads(value)
	if isinstance(value, dict):
		return dict(value)
	return value
