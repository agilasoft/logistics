# Copyright (c) 2025, www.agilasoft.com and contributors
# For license information, see license.txt

"""
Default UOM helpers.

Dimension, volume, and weight defaults always come from Logistics Settings
through logistics.utils.measurements.get_default_uoms. Domain arguments are
kept for older client calls and are not a second source.
"""

from __future__ import annotations

import frappe
from typing import Any, Optional


# Conversion rows store the pair being converted. They are not measurements.
EXCLUDED_MEASUREMENT_UOM_DOCTYPES = frozenset({
	"Dimension Volume UOM Conversion",
})


def measurement_uom_kind(fieldname: Optional[str]) -> Optional[str]:
	"""Map a field name to the Logistics Settings default it should use.

	Returns dimension, volume, weight, chargeable_weight, or aggregation_volume.
	aggregation_volume is the volume unit used when a header total is summed
	(base volume UOM, otherwise the default volume UOM).
	"""
	if not fieldname or fieldname.startswith(("default_", "base_")):
		return None
	if fieldname == "peak_uom":
		return "volume"
	if fieldname.endswith("chargeable_weight_uom"):
		return "chargeable_weight"
	if fieldname.endswith("total_volume_uom") or fieldname == "inv_volume_uom":
		return "aggregation_volume"
	if fieldname.endswith("dimension_uom"):
		return "dimension"
	if fieldname.endswith("volume_uom"):
		return "volume"
	if fieldname.endswith("weight_uom"):
		return "weight"
	return None


def measurement_uom_defaults(company: Optional[str] = None) -> dict[str, Optional[str]]:
	"""One dict of Logistics Settings measurement defaults, including rolled-up volume."""
	from logistics.utils.measurements import get_aggregation_volume_uom, get_default_uoms

	defaults = dict(get_default_uoms(company=company))
	defaults["aggregation_volume"] = get_aggregation_volume_uom(company=company) or defaults.get("volume")
	if not defaults.get("chargeable_weight"):
		defaults["chargeable_weight"] = defaults.get("weight")
	return defaults


def measurement_default_uom(kind: str, company: Optional[str] = None) -> Optional[str]:
	"""Return one Logistics Settings default. kind comes from measurement_uom_kind."""
	return measurement_uom_defaults(company=company).get(kind)


def _doc_meta(doc: Any):
	meta = getattr(doc, "meta", None)
	if meta is not None:
		return meta
	doctype = getattr(doc, "doctype", None)
	if not doctype:
		return None
	return frappe.get_meta(doctype)


def _fetched_uom(doc: Any, df) -> Optional[str]:
	"""Copy a linked document's UOM when this field fetches it and the link is set."""
	fetch_from = getattr(df, "fetch_from", None)
	if not fetch_from or "." not in fetch_from:
		return None
	link_field, source_field = fetch_from.split(".", 1)
	link_name = doc.get(link_field)
	if not link_name:
		return None
	meta = _doc_meta(doc)
	link_df = meta.get_field(link_field) if meta else None
	if not link_df or getattr(link_df, "fieldtype", None) != "Link" or not getattr(link_df, "options", None):
		return None
	value = frappe.db.get_value(link_df.options, link_name, source_field)
	return value or None


def _empty_measurement_fields(doc: Any) -> list:
	if getattr(doc, "doctype", None) in EXCLUDED_MEASUREMENT_UOM_DOCTYPES:
		return []
	meta = _doc_meta(doc)
	if not meta:
		return []
	pending = []
	for df in meta.fields or []:
		fieldname = getattr(df, "fieldname", None)
		kind = measurement_uom_kind(fieldname)
		if not kind or doc.get(fieldname):
			continue
		pending.append((fieldname, kind, df))
	return pending


def _fill_measurement_uom_fields(doc: Any, defaults: dict[str, Optional[str]]) -> None:
	for fieldname, kind, df in _empty_measurement_fields(doc):
		if doc.get(fieldname):
			continue
		value = _fetched_uom(doc, df) or defaults.get(kind)
		if value:
			doc.set(fieldname, value)


def apply_measurement_uom_defaults(doc, method=None, company: Optional[str] = None):
	"""Fill empty dimension, volume, and weight UOM fields from Logistics Settings.

	Linked fetch_from values win over the default. Child rows are included so a
	parent save covers table fields. Already filled fields are left unchanged.
	"""
	if doc is None:
		return doc
	company = company or getattr(doc, "company", None)
	rows = [doc]
	get_children = getattr(doc, "get_all_children", None)
	if callable(get_children):
		try:
			rows.extend(get_children() or [])
		except Exception:
			pass
	if not any(_empty_measurement_fields(row) for row in rows):
		return doc
	defaults = measurement_uom_defaults(company=company)
	for row in rows:
		_fill_measurement_uom_fields(row, defaults)
	return doc


@frappe.whitelist()
def get_measurement_uom_defaults(company: Optional[str] = None):
	"""Client API. Same values as measurement_uom_defaults."""
	return measurement_uom_defaults(company=company)


def get_default_uoms_for_domain(
	domain: str,
	company: Optional[str] = None,
) -> dict[str, Optional[str]]:
	"""
	Return default weight_uom, volume_uom, chargeable_uom from Logistics Settings (single source).
	Domain is ignored; all measurement defaults come from Logistics Settings.

	Args:
		domain: One of "transport", "air", "sea", "warehousing" (kept for API compatibility).
		company: Optional company (passed to get_default_uoms for compatibility).

	Returns:
		Dict with keys weight_uom, volume_uom, chargeable_uom.
	"""
	uoms = measurement_uom_defaults(company=company)
	return {
		"weight_uom": uoms.get("weight"),
		"volume_uom": uoms.get("volume"),
		"chargeable_uom": uoms.get("chargeable_weight"),
	}


@frappe.whitelist()
def get_default_uoms_for_domain_api(domain: str, company: Optional[str] = None):
	"""
	Whitelisted API for client scripts to fetch default UOMs by domain.
	domain: "transport" | "air" | "sea" | "warehousing"
	"""
	return get_default_uoms_for_domain(domain=domain, company=company)
