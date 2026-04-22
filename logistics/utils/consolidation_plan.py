# Copyright (c) 2026, AgilaSoft and contributors
# See license.txt
"""Air / Sea consolidation plan: submitted plan lines gate consolidation membership."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Union

import frappe
from frappe import _
from frappe.utils import getdate

AIR_PLAN = "Air Consolidation Plan"
AIR_PLAN_ITEM = "Air Consolidation Plan Item"
SEA_PLAN = "Sea Consolidation Plan"
SEA_PLAN_ITEM = "Sea Consolidation Plan Item"

_INELIGIBLE_AIR_HOUSE = frozenset({"Co-load Master", "Blind Co-load Master"})
_INELIGIBLE_SEA_HOUSE = frozenset({"Co-load Master", "Blind Co-load Master"})


def _plan_as_dict(plan: Union[Dict[str, Any], Any]) -> Dict[str, Any]:
	if isinstance(plan, dict):
		return plan
	if hasattr(plan, "as_dict"):
		return plan.as_dict()
	return dict(plan)


def _air_plan_required_for_match() -> tuple[str, ...]:
	return (
		"company",
		"branch",
		"origin_airport",
		"destination_airport",
		"airline",
		"flight_number",
		"target_departure",
	)


def _sea_plan_required_for_match() -> tuple[str, ...]:
	return (
		"company",
		"branch",
		"origin_port",
		"destination_port",
		"shipping_line",
		"vessel_name",
		"voyage_number",
		"target_etd",
	)


def assert_air_plan_fields_for_strict_match(plan: Union[Dict[str, Any], Any]) -> None:
	p = _plan_as_dict(plan)
	missing = [f for f in _air_plan_required_for_match() if not p.get(f)]
	if missing:
		frappe.throw(
			_("Set {0} before fetching matching shipments.").format(", ".join(missing)),
			title=_("Incomplete plan"),
		)


def assert_sea_plan_fields_for_strict_match(plan: Union[Dict[str, Any], Any]) -> None:
	p = _plan_as_dict(plan)
	missing = [f for f in _sea_plan_required_for_match() if not p.get(f)]
	if missing:
		frappe.throw(
			_("Set {0} before fetching matching shipments.").format(", ".join(missing)),
			title=_("Incomplete plan"),
		)


def get_strict_matching_air_shipment_names(plan: Union[Dict[str, Any], Any]) -> List[str]:
	"""Strict match: ports, header airline, Main leg flight/airline/ports, same ETD calendar date as target_departure."""
	p = _plan_as_dict(plan)
	if any(not p.get(f) for f in _air_plan_required_for_match()):
		return []
	etd_date = getdate(p["target_departure"])
	flight_raw = (p.get("flight_number") or "").strip()
	if not flight_raw:
		return []
	rows = frappe.db.sql(
		"""
		SELECT DISTINCT s.name
		FROM `tabAir Shipment` s
		INNER JOIN `tabAir Shipment Routing Leg` rl
			ON rl.parent = s.name
			AND rl.parenttype = 'Air Shipment'
			AND rl.parentfield = 'routing_legs'
		WHERE s.docstatus != 2
			AND IFNULL(s.job_status, '') NOT IN ('Cancelled', 'Closed')
			AND s.company = %(company)s
			AND s.branch = %(branch)s
			AND s.origin_port = %(origin)s
			AND s.destination_port = %(dest)s
			AND IFNULL(s.airline, '') = %(airline)s
			AND s.etd = %(etd_date)s
			AND rl.type = 'Main'
			AND IFNULL(rl.flight_no, '') != ''
			AND UPPER(TRIM(rl.flight_no)) = UPPER(TRIM(%(flight)s))
			AND IFNULL(rl.airline, '') = %(airline)s
			AND rl.load_port = %(origin)s
			AND rl.discharge_port = %(dest)s
			AND IFNULL(s.house_type, '') NOT IN ('Co-load Master', 'Blind Co-load Master')
		ORDER BY s.name
		""",
		{
			"company": p["company"],
			"branch": p["branch"],
			"origin": p["origin_airport"],
			"dest": p["destination_airport"],
			"airline": p["airline"],
			"etd_date": etd_date,
			"flight": flight_raw,
		},
		as_dict=False,
	)
	return [r[0] for r in rows]


def get_strict_matching_sea_shipment_names(plan: Union[Dict[str, Any], Any]) -> List[str]:
	"""Strict match: house + MBL shipping line equal plan line, MBL vessel/voyage, same ETD date as target_etd."""
	p = _plan_as_dict(plan)
	if any(not p.get(f) for f in _sea_plan_required_for_match()):
		return []
	etd_date = getdate(p["target_etd"])
	sl = p["shipping_line"]
	vessel = (p.get("vessel_name") or "").strip()
	voyage = (p.get("voyage_number") or "").strip()
	if not vessel or not voyage:
		return []
	rows = frappe.db.sql(
		"""
		SELECT DISTINCT s.name
		FROM `tabSea Shipment` s
		WHERE s.docstatus != 2
			AND IFNULL(s.job_status, '') NOT IN ('Cancelled', 'Closed')
			AND s.company = %(company)s
			AND s.branch = %(branch)s
			AND s.origin_port = %(origin)s
			AND s.destination_port = %(dest)s
			AND s.shipping_line = %(sl)s
			AND IFNULL(s.mbl_shipping_line, '') = %(sl)s
			AND s.etd = %(etd_date)s
			AND UPPER(TRIM(IFNULL(s.mbl_vessel, ''))) = UPPER(TRIM(%(vessel)s))
			AND UPPER(TRIM(IFNULL(s.mbl_voyage_no, ''))) = UPPER(TRIM(%(voyage)s))
			AND IFNULL(s.house_type, '') NOT IN ('Co-load Master', 'Blind Co-load Master')
		ORDER BY s.name
		""",
		{
			"company": p["company"],
			"branch": p["branch"],
			"origin": p["origin_port"],
			"dest": p["destination_port"],
			"sl": sl,
			"etd_date": etd_date,
			"vessel": vessel,
			"voyage": voyage,
		},
		as_dict=False,
	)
	return [r[0] for r in rows]


def get_air_shipment_names_from_consolidation(doc) -> Set[str]:
	names: Set[str] = set()
	for row in doc.get("consolidation_packages") or []:
		if getattr(row, "air_freight_job", None):
			names.add(row.air_freight_job)
	for row in doc.get("attached_air_freight_jobs") or []:
		if getattr(row, "air_freight_job", None):
			names.add(row.air_freight_job)
	return names


def get_sea_shipment_names_from_consolidation(doc) -> Set[str]:
	names: Set[str] = set()
	for row in doc.get("consolidation_packages") or []:
		if getattr(row, "sea_shipment", None):
			names.add(row.sea_shipment)
	for row in doc.get("attached_sea_shipments") or []:
		if getattr(row, "sea_shipment", None):
			names.add(row.sea_shipment)
	for row in doc.get("consolidation_containers") or []:
		if getattr(row, "sea_shipment", None):
			names.add(row.sea_shipment)
	return names


def _find_eligible_air_plan_line(shipment: str, consolidation_name: Optional[str]) -> Optional[str]:
	submitted_plans = frappe.get_all(
		AIR_PLAN,
		filters={"docstatus": 1},
		pluck="name",
	)
	if not submitted_plans:
		return None
	filters = {
		"parent": ["in", submitted_plans],
		"air_shipment": shipment,
	}
	or_filters = [["linked_air_consolidation", "in", [None, ""]]]
	if consolidation_name:
		or_filters.append(["linked_air_consolidation", "=", consolidation_name])
	rows = frappe.get_all(
		AIR_PLAN_ITEM,
		filters=filters,
		or_filters=or_filters,
		pluck="name",
		order_by="modified desc",
		limit=1,
	)
	return rows[0] if rows else None


def _find_eligible_sea_plan_line(shipment: str, consolidation_name: Optional[str]) -> Optional[str]:
	submitted_plans = frappe.get_all(
		SEA_PLAN,
		filters={"docstatus": 1},
		pluck="name",
	)
	if not submitted_plans:
		return None
	filters = {
		"parent": ["in", submitted_plans],
		"sea_shipment": shipment,
	}
	or_filters = [["linked_sea_consolidation", "in", [None, ""]]]
	if consolidation_name:
		or_filters.append(["linked_sea_consolidation", "=", consolidation_name])
	rows = frappe.get_all(
		SEA_PLAN_ITEM,
		filters=filters,
		or_filters=or_filters,
		pluck="name",
		order_by="modified desc",
		limit=1,
	)
	return rows[0] if rows else None


def assert_air_consolidation_plan_requirements(doc) -> None:
	consolidation_name = doc.get("name")
	shipments = get_air_shipment_names_from_consolidation(doc)
	if not shipments:
		return
	for shipment in shipments:
		line = _find_eligible_air_plan_line(shipment, consolidation_name)
		if not line:
			frappe.throw(
				_(
					"Air Shipment {0} is not on a submitted {1} with an open line for this consolidation. "
					"Add it to an Air Consolidation Plan, submit the plan, then add it here (or use Create Consolidation from Plan)."
				).format(shipment, AIR_PLAN),
				title=_("Consolidation Plan Required"),
			)


def assert_sea_consolidation_plan_requirements(doc) -> None:
	consolidation_name = doc.get("name")
	shipments = get_sea_shipment_names_from_consolidation(doc)
	if not shipments:
		return
	for shipment in shipments:
		line = _find_eligible_sea_plan_line(shipment, consolidation_name)
		if not line:
			frappe.throw(
				_(
					"Sea Shipment {0} is not on a submitted {1} with an open line for this consolidation. "
					"Add it to a Sea Consolidation Plan, submit the plan, then add it here (or use Create Consolidation from Plan)."
				).format(shipment, SEA_PLAN),
				title=_("Consolidation Plan Required"),
			)


def sync_air_plan_item_links(consolidation_doc) -> None:
	name = consolidation_doc.name
	wanted = get_air_shipment_names_from_consolidation(consolidation_doc)
	for row in frappe.get_all(
		AIR_PLAN_ITEM,
		filters={"linked_air_consolidation": name},
		fields=["name", "air_shipment"],
	):
		if row.air_shipment not in wanted:
			frappe.db.set_value(AIR_PLAN_ITEM, row.name, "linked_air_consolidation", None, update_modified=False)
	for shipment in wanted:
		line = _find_eligible_air_plan_line(shipment, name)
		if line:
			frappe.db.set_value(AIR_PLAN_ITEM, line, "linked_air_consolidation", name, update_modified=False)


def sync_sea_plan_item_links(consolidation_doc) -> None:
	name = consolidation_doc.name
	wanted = get_sea_shipment_names_from_consolidation(consolidation_doc)
	for row in frappe.get_all(
		SEA_PLAN_ITEM,
		filters={"linked_sea_consolidation": name},
		fields=["name", "sea_shipment"],
	):
		if row.sea_shipment not in wanted:
			frappe.db.set_value(SEA_PLAN_ITEM, row.name, "linked_sea_consolidation", None, update_modified=False)
	for shipment in wanted:
		line = _find_eligible_sea_plan_line(shipment, name)
		if line:
			frappe.db.set_value(SEA_PLAN_ITEM, line, "linked_sea_consolidation", name, update_modified=False)


def clear_air_plan_links_for_consolidation(consolidation_name: str) -> None:
	for row in frappe.get_all(
		AIR_PLAN_ITEM,
		filters={"linked_air_consolidation": consolidation_name},
		pluck="name",
	):
		frappe.db.set_value(AIR_PLAN_ITEM, row, "linked_air_consolidation", None, update_modified=False)


def clear_sea_plan_links_for_consolidation(consolidation_name: str) -> None:
	for row in frappe.get_all(
		SEA_PLAN_ITEM,
		filters={"linked_sea_consolidation": consolidation_name},
		pluck="name",
	):
		frappe.db.set_value(SEA_PLAN_ITEM, row, "linked_sea_consolidation", None, update_modified=False)


def air_shipment_allowed_on_plan(shipment_name: str) -> tuple[bool, str]:
	if not frappe.db.exists("Air Shipment", shipment_name):
		return False, _("Air Shipment {0} does not exist").format(shipment_name)
	ht = frappe.db.get_value("Air Shipment", shipment_name, "house_type") or ""
	if ht in _INELIGIBLE_AIR_HOUSE:
		return False, _("House type {0} cannot be added to a consolidation plan").format(ht or "-")
	return True, ""


def sea_shipment_allowed_on_plan(shipment_name: str) -> tuple[bool, str]:
	if not frappe.db.exists("Sea Shipment", shipment_name):
		return False, _("Sea Shipment {0} does not exist").format(shipment_name)
	ht = frappe.db.get_value("Sea Shipment", shipment_name, "house_type") or ""
	if ht in _INELIGIBLE_SEA_HOUSE:
		return False, _("House type {0} cannot be added to a consolidation plan").format(ht or "-")
	return True, ""


def conflicting_open_air_plan_line(shipment: str, exclude_parent_plan: Optional[str]) -> bool:
	"""True if another submitted plan (not exclude_parent_plan) already has an open line for this shipment."""
	for row in frappe.get_all(
		AIR_PLAN_ITEM,
		filters={
			"air_shipment": shipment,
			"linked_air_consolidation": ["in", [None, ""]],
		},
		fields=["parent"],
	):
		if frappe.db.get_value(AIR_PLAN, row.parent, "docstatus") != 1:
			continue
		if exclude_parent_plan and row.parent == exclude_parent_plan:
			continue
		return True
	return False


def conflicting_open_sea_plan_line(shipment: str, exclude_parent_plan: Optional[str]) -> bool:
	for row in frappe.get_all(
		SEA_PLAN_ITEM,
		filters={
			"sea_shipment": shipment,
			"linked_sea_consolidation": ["in", [None, ""]],
		},
		fields=["parent"],
	):
		if frappe.db.get_value(SEA_PLAN, row.parent, "docstatus") != 1:
			continue
		if exclude_parent_plan and row.parent == exclude_parent_plan:
			continue
		return True
	return False
