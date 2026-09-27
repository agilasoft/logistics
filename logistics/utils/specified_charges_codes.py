# Copyright (c) 2026, Agilasoft and contributors
"""Parse JSON item / charge-group code lists stored on charge rows."""

from __future__ import annotations

import json
from typing import Any, List

import frappe


def parse_code_list(raw: Any) -> List[str]:
	if raw is None or raw == "":
		return []
	if isinstance(raw, list):
		return _dedupe_str_list(raw)
	if isinstance(raw, str):
		raw = raw.strip()
		if not raw:
			return []
		try:
			parsed = json.loads(raw)
			if isinstance(parsed, list):
				return _dedupe_str_list(parsed)
		except (TypeError, ValueError):
			pass
		return _dedupe_str_list([p.strip() for p in raw.split(",") if p.strip()])
	return []


def _dedupe_str_list(values: List[Any]) -> List[str]:
	out: List[str] = []
	seen = set()
	for val in values:
		s = (val or "").strip() if isinstance(val, str) else str(val or "").strip()
		if s and s not in seen:
			out.append(s)
			seen.add(s)
	return out


def codes_from_charge_row(charge_doc: Any, json_fieldname: str) -> List[str]:
	if isinstance(charge_doc, dict):
		return parse_code_list(charge_doc.get(json_fieldname))
	return parse_code_list(getattr(charge_doc, json_fieldname, None))
