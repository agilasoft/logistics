# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Shared capacity / utilization and package rollup for Sea Booking Containers and Sea Freight Containers."""

from __future__ import annotations

import frappe
from frappe.utils import cint, flt

from logistics.container_management.api import sea_container_row_field_to_equipment_number
from logistics.utils.container_validation import normalize_container_number


def sync_sea_freight_container_child_rows(parent_doc):
	"""Roll up package cargo per container row, then max_weight / utilization from Container Type."""
	if getattr(frappe.flags, "in_import", False) or getattr(frappe.flags, "in_migrate", False):
		return
	sync_container_cargo_from_packages(parent_doc)
	for row in getattr(parent_doc, "containers", None) or []:
		_sync_one_container_row(row)


def sync_container_cargo_from_packages(parent_doc):
	"""Set packages_in_container, weight_in_container, volume_in_container from assigned package lines."""
	company = getattr(parent_doc, "company", None)
	packages = getattr(parent_doc, "packages", None) or []
	for row in getattr(parent_doc, "containers", None) or []:
		equipment_key = _container_row_equipment_key(row)
		if not equipment_key:
			row.packages_in_container = 0
			row.weight_in_container = flt(0)
			row.volume_in_container = flt(0)
			continue
		packs, weight_kg, volume_m3 = _aggregate_packages_for_container(
			packages, equipment_key, company
		)
		row.packages_in_container = cint(packs)
		row.weight_in_container = flt(weight_kg, 2)
		row.volume_in_container = flt(volume_m3, 3)


def container_cargo_payload_from_doc(parent_doc) -> list[dict]:
	"""Return per-container metrics already on parent_doc (no re-sync)."""
	out = []
	for row in getattr(parent_doc, "containers", None) or []:
		out.append(
			{
				"idx": getattr(row, "idx", None),
				"name": getattr(row, "name", None),
				"packages_in_container": cint(getattr(row, "packages_in_container", 0) or 0),
				"weight_in_container": flt(getattr(row, "weight_in_container", 0) or 0),
				"volume_in_container": flt(getattr(row, "volume_in_container", 0) or 0),
				"max_weight": flt(getattr(row, "max_weight", 0) or 0),
				"max_volume": flt(getattr(row, "max_volume", 0) or 0),
				"utilization_percentage": flt(getattr(row, "utilization_percentage", 0) or 0),
			}
		)
	return out


def build_container_cargo_payload(parent_doc) -> list[dict]:
	"""Sync container cargo then return payload for client refresh."""
	sync_sea_freight_container_child_rows(parent_doc)
	return container_cargo_payload_from_doc(parent_doc)


@frappe.whitelist()
def compute_container_cargo_metrics(doc=None):
	"""Compute container cargo metrics from a doc snapshot (works for unsaved documents)."""
	if isinstance(doc, str):
		doc = frappe.parse_json(doc)
	if not doc:
		return {"container_cargo": []}

	parent = frappe._dict(doc)
	packages = [frappe._dict(p) for p in (parent.get("packages") or [])]
	containers = [frappe._dict(c) for c in (parent.get("containers") or [])]
	company = parent.get("company")

	for row in containers:
		equipment_key = _container_row_equipment_key(row)
		if not equipment_key:
			row.packages_in_container = 0
			row.weight_in_container = flt(0)
			row.volume_in_container = flt(0)
		else:
			packs, weight_kg, volume_m3 = _aggregate_packages_for_container(
				packages, equipment_key, company
			)
			row.packages_in_container = cint(packs)
			row.weight_in_container = flt(weight_kg, 2)
			row.volume_in_container = flt(volume_m3, 3)
		_sync_one_container_row(row)

	out = []
	for row in containers:
		out.append(
			{
				"idx": row.get("idx"),
				"name": row.get("name"),
				"packages_in_container": cint(row.get("packages_in_container") or 0),
				"weight_in_container": flt(row.get("weight_in_container") or 0),
				"volume_in_container": flt(row.get("volume_in_container") or 0),
				"max_weight": flt(row.get("max_weight") or 0),
				"max_volume": flt(row.get("max_volume") or 0),
				"utilization_percentage": flt(row.get("utilization_percentage") or 0),
			}
		)
	return {"container_cargo": out}


def _container_row_equipment_key(row) -> str:
	"""Normalized ISO equipment number for a container child row."""
	container_no = getattr(row, "container_no", None) if not isinstance(row, dict) else row.get("container_no")
	if container_no:
		key = sea_container_row_field_to_equipment_number(container_no)
		if key:
			return key
	raw_container = getattr(row, "container", None) if not isinstance(row, dict) else row.get("container")
	if raw_container and str(raw_container).strip():
		return normalize_container_number(str(raw_container).strip()) or ""
	return ""


def _aggregate_packages_for_container(packages, equipment_key: str, company=None):
	"""Sum packs, weight (kg), and volume (aggregation UOM) for packages assigned to equipment_key."""
	if not equipment_key:
		return 0, flt(0), flt(0)

	pack_total = flt(0)
	weight_total = flt(0)
	volume_total = flt(0)

	try:
		from logistics.utils.measurements import (
			convert_volume,
			convert_weight,
			get_aggregation_volume_uom,
			get_default_uoms,
		)

		defaults = get_default_uoms(company=company)
		target_weight_uom = _target_weight_uom_kg(defaults)
		target_volume_uom = get_aggregation_volume_uom(company=company)
		target_weight_norm = str(target_weight_uom or "").strip().upper() if target_weight_uom else ""
		target_volume_norm = str(target_volume_uom or "").strip().upper() if target_volume_uom else ""
	except Exception:
		return 0, flt(0), flt(0)

	for pkg in packages:
		pkg_container = getattr(pkg, "container", None) if not isinstance(pkg, dict) else pkg.get("container")
		if not pkg_container or not str(pkg_container).strip():
			continue
		if normalize_container_number(str(pkg_container).strip()) != equipment_key:
			continue

		pack_total += flt(
			(getattr(pkg, "no_of_packs", None) if not isinstance(pkg, dict) else pkg.get("no_of_packs"))
			or 0
		)

		pkg_weight = flt(
			(getattr(pkg, "weight", None) if not isinstance(pkg, dict) else pkg.get("weight")) or 0
		)
		if pkg_weight > 0 and target_weight_uom:
			pkg_weight_uom = (
				getattr(pkg, "weight_uom", None) if not isinstance(pkg, dict) else pkg.get("weight_uom")
			) or defaults.get("weight")
			if pkg_weight_uom and str(pkg_weight_uom).strip().upper() == target_weight_norm:
				weight_total += pkg_weight
			elif pkg_weight_uom:
				weight_total += convert_weight(
					pkg_weight,
					from_uom=pkg_weight_uom,
					to_uom=target_weight_uom,
					company=company,
				)

		pkg_volume = flt(
			(getattr(pkg, "volume", None) if not isinstance(pkg, dict) else pkg.get("volume")) or 0
		)
		if pkg_volume > 0 and target_volume_uom:
			pkg_volume_uom = (
				getattr(pkg, "volume_uom", None) if not isinstance(pkg, dict) else pkg.get("volume_uom")
			) or defaults.get("volume")
			if pkg_volume_uom and str(pkg_volume_uom).strip().upper() == target_volume_norm:
				volume_total += pkg_volume
			elif pkg_volume_uom:
				volume_total += convert_volume(
					pkg_volume,
					from_uom=pkg_volume_uom,
					to_uom=target_volume_uom,
					company=company,
				)

	return pack_total, weight_total, volume_total


def _target_weight_uom_kg(defaults: dict) -> str | None:
	"""Prefer Kg for weight_in_container; fall back to company default weight UOM."""
	for candidate in ("Kg", "KGS", "KG", defaults.get("weight")):
		if not candidate:
			continue
		if frappe.db.exists("UOM", candidate):
			return candidate
	return defaults.get("weight")


def _sync_one_container_row(row):
	ctype = getattr(row, "type", None) if not isinstance(row, dict) else row.get("type")
	max_w = flt(0)
	max_v = flt(0)
	if ctype:
		ct = frappe.db.get_value(
			"Container Type",
			ctype,
			["max_gross_weight"],
			as_dict=True,
		)
		if ct and ct.get("max_gross_weight") is not None:
			max_w = flt(ct.max_gross_weight)
		if frappe.db.has_column("Container Type", "max_volume"):
			mv = frappe.db.get_value("Container Type", ctype, "max_volume")
			if mv is not None:
				max_v = flt(mv)
	if isinstance(row, dict):
		row["max_weight"] = max_w
		row["max_volume"] = max_v
		wic = flt(row.get("weight_in_container", 0) or 0)
		vic = flt(row.get("volume_in_container", 0) or 0)
	else:
		row.max_weight = max_w
		row.max_volume = max_v
		wic = flt(getattr(row, "weight_in_container", 0) or 0)
		vic = flt(getattr(row, "volume_in_container", 0) or 0)
	parts = []
	if max_w > 0:
		parts.append(wic / max_w * 100.0)
	if max_v > 0:
		parts.append(vic / max_v * 100.0)
	util = max(parts) if parts else flt(0)
	if isinstance(row, dict):
		row["utilization_percentage"] = util
	else:
		row.utilization_percentage = util
