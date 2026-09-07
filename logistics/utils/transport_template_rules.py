# Copyright (c) 2026, Agilasoft and contributors
# Licensed under the MIT License. See license.txt

"""Transport Template load/vehicle constraints (#1122)."""

from __future__ import annotations

from typing import Any

import frappe
from frappe import _

CONTAINER_FACILITY_TYPES = frozenset({
	"Terminal",
	"Container Yard",
	"Container Depot",
})

LAND_FACILITY_TYPES = frozenset({
	"Container Freight Station",
	"Storage Facility",
	"Shipper",
	"Consignee",
	"Sorting Hub",
	"Truck Park",
})

# Container load types permitted on land-lane templates (e.g. CFS → Consignee drayage).
LAND_LANE_CONTAINER_LOAD_TYPES = frozenset({"FCL"})

JOB_TYPE_LOAD_TYPE_FIELD = {
	"Container": "container",
	"Non-Container": "non_container",
	"Special": "special",
	"Oversized": "oversized",
	"Multimodal": "multimodal",
	"Heavy Haul": "heavy_haul",
}


def _row_val(row: Any, fieldname: str) -> Any:
	if row is None:
		return None
	if isinstance(row, dict):
		return row.get(fieldname)
	return getattr(row, fieldname, None)


def _leg_facility_types(legs: list[Any]) -> set[str]:
	types: set[str] = set()
	for leg in legs or []:
		for field in ("facility_type_from", "facility_type_to"):
			value = _row_val(leg, field)
			if value:
				types.add(value)
	return types


def _load_type_flags(load_type: str) -> dict[str, int]:
	return frappe.db.get_value(
		"Load Type",
		load_type,
		["container", "non_container"],
		as_dict=True,
	) or {}


def classify_leg_pattern(legs: list[Any]) -> str:
	"""Return container, land, mixed, or unknown based on leg facility types."""
	facilities = _leg_facility_types(legs)
	if not facilities:
		return "unknown"

	has_container = bool(facilities & CONTAINER_FACILITY_TYPES)
	has_land = bool(facilities & LAND_FACILITY_TYPES)
	other = facilities - CONTAINER_FACILITY_TYPES - LAND_FACILITY_TYPES

	if has_container and (has_land or other):
		return "mixed"
	if has_container:
		return "container"
	if has_land or other:
		return "land"
	return "unknown"


def suggest_allowed_load_types_from_legs(legs: list[Any]) -> list[str]:
	"""Convention-based load type suggestions for template authoring."""
	pattern = classify_leg_pattern(legs)
	base_filters: dict[str, Any] = {"is_active": 1, "transport": 1}

	if pattern == "container":
		return frappe.get_all(
			"Load Type",
			filters={**base_filters, "container": 1},
			pluck="name",
			order_by="name",
		)

	if pattern in ("land", "unknown"):
		suggested = frappe.get_all(
			"Load Type",
			filters={**base_filters, "non_container": 1},
			pluck="name",
			order_by="name",
		)
		if LAND_LANE_CONTAINER_LOAD_TYPES:
			container_exceptions = frappe.get_all(
				"Load Type",
				filters={
					**base_filters,
					"container": 1,
					"name": ["in", list(LAND_LANE_CONTAINER_LOAD_TYPES)],
				},
				pluck="name",
				order_by="name",
			)
			for name in container_exceptions:
				if name not in suggested:
					suggested.append(name)
		return suggested

	return []


def filter_load_types_for_transport_job_type(
	load_type_names: list[str],
	transport_job_type: str | None,
) -> list[str]:
	"""Return template-allowed load types compatible with the transport job type."""
	if not load_type_names:
		return []

	if not transport_job_type:
		return list(load_type_names)

	allowed_field = JOB_TYPE_LOAD_TYPE_FIELD.get(transport_job_type)
	if not allowed_field:
		return list(load_type_names)

	matching = set(
		frappe.get_all(
			"Load Type",
			filters={
				"name": ["in", load_type_names],
				"is_active": 1,
				"transport": 1,
				allowed_field: 1,
			},
			pluck="name",
		)
	)
	return [name for name in load_type_names if name in matching]


def get_allowed_load_types_from_doc(doc: Any) -> list[str]:
	rows = getattr(doc, "allowed_load_types", None) or []
	names = []
	for row in rows:
		lt = _row_val(row, "load_type")
		if lt and lt not in names:
			names.append(lt)
	return names


def get_template_constraints(template_name: str | None) -> dict[str, Any]:
	if not template_name:
		return {
			"allowed_load_types": [],
			"allowed_load_types_all": [],
			"default_load_type": None,
			"default_vehicle_type": None,
			"leg_pattern": "unknown",
			"requires_container": False,
		}

	doc = frappe.get_doc("Transport Template", template_name)
	allowed = get_allowed_load_types_from_doc(doc)
	legs = getattr(doc, "legs", None) or []
	pattern = classify_leg_pattern(legs)

	return {
		"allowed_load_types": allowed,
		"allowed_load_types_all": list(allowed),
		"default_load_type": getattr(doc, "default_load_type", None),
		"default_vehicle_type": getattr(doc, "default_vehicle_type", None),
		"leg_pattern": pattern,
		"requires_container": pattern == "container",
	}


def validate_template_allowed_load_types_vs_legs(doc: Any) -> None:
	legs = getattr(doc, "legs", None) or []
	allowed = get_allowed_load_types_from_doc(doc)
	if not legs:
		frappe.throw(_("Transport Template must have at least one leg."))
	if not allowed:
		frappe.throw(_("Add at least one Allowed Load Type."))

	pattern = classify_leg_pattern(legs)
	if pattern == "mixed":
		frappe.throw(
			_(
				"Template legs mix container facilities (Terminal, Container Yard, Container Depot) "
				"with land facilities. Use a single lane pattern per template."
			)
		)

	for load_type in allowed:
		flags = _load_type_flags(load_type)
		if not flags:
			frappe.throw(_("Load Type {0} was not found.").format(load_type))

		if pattern == "container" and not flags.get("container"):
			frappe.throw(
				_("Load Type {0} is not allowed for container-lane templates (port/CY/CD). Use FCL.").format(
					load_type
				)
			)
		if pattern == "land" and not flags.get("non_container"):
			if load_type in LAND_LANE_CONTAINER_LOAD_TYPES and flags.get("container"):
				continue
			frappe.throw(
				_("Load Type {0} is not allowed for land-lane templates (CFS/WHS/etc.). Use FTL or LTL.").format(
					load_type
				)
			)

		if pattern == "unknown":
			if flags.get("container") and flags.get("non_container"):
				continue
			if flags.get("container") or flags.get("non_container"):
				continue
			frappe.throw(_("Load Type {0} must be marked container or non-container for transport.").format(load_type))


def validate_template_defaults(doc: Any) -> None:
	allowed = get_allowed_load_types_from_doc(doc)
	default_lt = getattr(doc, "default_load_type", None)
	default_vt = getattr(doc, "default_vehicle_type", None)

	if default_lt and default_lt not in allowed:
		frappe.throw(_("Default Load Type must be one of the Allowed Load Types."))

	if default_vt and default_lt:
		allowed_for_vehicle = frappe.get_all(
			"Vehicle Type Load Types",
			filters={"parent": default_vt, "load_type": default_lt},
			pluck="name",
			limit=1,
		)
		if not allowed_for_vehicle:
			frappe.throw(
				_("Default Vehicle Type {0} does not allow Default Load Type {1}.").format(
					default_vt, default_lt
				)
			)


def validate_against_transport_template(
	*,
	template_name: str | None,
	load_type: str | None,
	vehicle_type: str | None = None,
	context: str | None = None,
) -> None:
	if not template_name:
		return

	constraints = get_template_constraints(template_name)
	allowed = constraints.get("allowed_load_types") or []
	prefix = f"{context}: " if context else ""

	if load_type and allowed and load_type not in allowed:
		frappe.throw(
			_("{0}Load Type {1} is not allowed for Transport Template {2}. Allowed: {3}.").format(
				prefix,
				load_type,
				template_name,
				", ".join(allowed),
			)
		)

	if vehicle_type and load_type:
		allowed_for_vehicle = frappe.get_all(
			"Vehicle Type Load Types",
			filters={"parent": vehicle_type, "load_type": load_type},
			pluck="name",
			limit=1,
		)
		if not allowed_for_vehicle:
			frappe.throw(
				_("{0}Vehicle Type {1} is not allowed for Load Type {2}.").format(
					prefix, vehicle_type, load_type
				)
			)


def apply_transport_template_defaults(
	doc: Any,
	*,
	template_field: str = "transport_template",
	load_type_field: str = "load_type",
	vehicle_type_field: str = "vehicle_type",
	force: bool = False,
) -> None:
	template_name = getattr(doc, template_field, None)
	if not template_name:
		return

	constraints = get_template_constraints(template_name)
	default_lt = constraints.get("default_load_type")
	default_vt = constraints.get("default_vehicle_type")

	if default_lt and (force or not getattr(doc, load_type_field, None)):
		doc.set(load_type_field, default_lt)

	if default_vt and (force or not getattr(doc, vehicle_type_field, None)):
		doc.set(vehicle_type_field, default_vt)


def clear_incompatible_load_vehicle_for_template(
	doc: Any,
	*,
	template_field: str = "transport_template",
	load_type_field: str = "load_type",
	vehicle_type_field: str = "vehicle_type",
) -> None:
	template_name = getattr(doc, template_field, None)
	if not template_name:
		return

	constraints = get_template_constraints(template_name)
	allowed = constraints.get("allowed_load_types") or []
	load_type = getattr(doc, load_type_field, None)
	vehicle_type = getattr(doc, vehicle_type_field, None)

	if load_type and allowed and load_type not in allowed:
		doc.set(load_type_field, None)
		load_type = None
		vehicle_type = None

	if load_type and vehicle_type:
		allowed_for_vehicle = frappe.get_all(
			"Vehicle Type Load Types",
			filters={"parent": vehicle_type, "load_type": load_type},
			pluck="name",
			limit=1,
		)
		if not allowed_for_vehicle:
			doc.set(vehicle_type_field, None)
