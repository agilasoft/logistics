# Copyright (c) 2026, AgilaSoft and contributors
# See license.txt
"""Air consolidation plans / Sea consolidation planning lines gate shipment membership."""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Set, Union

import frappe
from frappe import _
from frappe.utils import getdate

AIR_CONSOLIDATION = "Air Consolidation"
AIR_PLANNING_LINE = "Air Consolidation Planning Line"
SEA_CONSOLIDATION = "Sea Consolidation"
SEA_PLANNING_LINE = "Sea Consolidation Planning Line"

MIN_CONSOLIDATION_SHIPMENT_COUNT = 2

_INELIGIBLE_AIR_HOUSE = frozenset({"Co-load Master", "Blind Co-load Master"})
_INELIGIBLE_SEA_HOUSE = frozenset({"Co-load Master", "Blind Co-load Master"})
# Draft consolidation planning aligns draft sea jobs only (submitted shipment doc → job_status Submitted).
_SEA_PLAN_ALIGNMENT_EXCLUDED_JOB_STATUSES = frozenset({"Submitted", "Cancelled", "Closed"})
_SEA_PLAN_ALIGNMENT_JOB_STATUS_SQL_NOT_IN = ", ".join(
	"'{}'".format(x) for x in sorted(_SEA_PLAN_ALIGNMENT_EXCLUDED_JOB_STATUSES)
)


def _plan_as_dict(plan: Union[Dict[str, Any], Any]) -> Dict[str, Any]:
	if isinstance(plan, dict):
		return plan
	if hasattr(plan, "as_dict"):
		return plan.as_dict()
	return dict(plan)


# Aligned Air Shipments dialog: one scrollable load; SQL LIMIT only as a safety valve.
AIR_ALIGNMENT_PREVIEW_MAX_ROWS = 15000


def _air_plan_value_nonempty(plan: Union[Dict[str, Any], Any], key: str) -> bool:
	p = _plan_as_dict(plan)
	val = p.get(key)
	if val is None:
		return False
	if isinstance(val, str):
		return bool(val.strip())
	return True


def assert_air_plan_fields_for_strict_match(plan: Union[Dict[str, Any], Any]) -> None:
	"""Deprecated: same as :func:`assert_air_plan_fields_for_filter_match` (partial filters)."""
	assert_air_plan_fields_for_filter_match(plan)


def assert_air_plan_fields_for_filter_match(plan: Union[Dict[str, Any], Any]) -> None:
	"""Require at least one non-empty alignment filter field."""
	p = _plan_as_dict(plan)
	keys = (
		"company",
		"branch",
		"origin_airport",
		"destination_airport",
		"target_departure",
		"airline",
		"flight_number",
	)
	if not any(_air_plan_value_nonempty(p, k) for k in keys):
		frappe.throw(
			_(
				"Set at least one filter (company, branch, origin or destination airport, "
				"departure date, airline, or flight)."
			),
			title=_("No filters"),
		)


SEA_ALIGNMENT_DIALOG_FILTER_KEYS = (
	"company",
	"branch",
	"origin_port",
	"destination_port",
	"target_etd",
	"shipping_line",
	"vessel_name",
	"voyage_number",
)


def sea_alignment_plan_has_any_filter(plan: Union[Dict[str, Any], Any]) -> bool:
	"""True if *plan* has at least one non-empty sea alignment criterion."""
	p = _plan_as_dict(plan)
	return any(_air_plan_value_nonempty(p, k) for k in SEA_ALIGNMENT_DIALOG_FILTER_KEYS)


def assert_sea_plan_fields_for_filter_match(plan: Union[Dict[str, Any], Any]) -> None:
	"""Require at least one non-empty sea alignment filter field (same idea as air alignment)."""
	p = _plan_as_dict(plan)
	if not sea_alignment_plan_has_any_filter(p):
		frappe.throw(
			_(
				"Set at least one filter (company, branch, origin or destination port, "
				"ETD date, shipping line, vessel, or voyage)."
			),
			title=_("No filters"),
		)


def assert_sea_plan_fields_for_strict_match(plan: Union[Dict[str, Any], Any]) -> None:
	"""Deprecated: same as :func:`assert_sea_plan_fields_for_filter_match` (partial filters)."""
	assert_sea_plan_fields_for_filter_match(plan)


def _air_shipment_filter_parts(p: Dict[str, Any]) -> tuple[str, List[str], Dict[str, Any]]:
	"""Shared JOIN + WHERE fragments for optional air alignment filters (*p* is a plain dict)."""
	conditions = [
		"s.docstatus != 2",
		# Planning alignment: only draft operational jobs (submitted doc → job_status Submitted, etc.).
		"IFNULL(s.job_status, '') = 'Draft'",
		"IFNULL(s.house_type, '') NOT IN ('Co-load Master', 'Blind Co-load Master')",
	]
	params: Dict[str, Any] = {}

	if _air_plan_value_nonempty(p, "company"):
		conditions.append("s.company = %(company)s")
		params["company"] = p["company"]
	if _air_plan_value_nonempty(p, "branch"):
		conditions.append("s.branch = %(branch)s")
		params["branch"] = p["branch"]
	if _air_plan_value_nonempty(p, "origin_airport"):
		conditions.append("s.origin_port = %(origin)s")
		params["origin"] = p["origin_airport"]
	if _air_plan_value_nonempty(p, "destination_airport"):
		conditions.append("s.destination_port = %(dest)s")
		params["dest"] = p["destination_airport"]
	if _air_plan_value_nonempty(p, "target_departure"):
		conditions.append("DATE(s.etd) = %(etd_date)s")
		params["etd_date"] = getdate(p["target_departure"])

	flight_raw = (p.get("flight_number") or "").strip()
	join_sql = ""
	if flight_raw:
		join_sql = """
		INNER JOIN `tabAir Shipment Routing Leg` rl
			ON rl.parent = s.name
			AND rl.parenttype = 'Air Shipment'
			AND rl.parentfield = 'routing_legs'
		"""
		conditions.append("rl.type = 'Main'")
		conditions.append("IFNULL(rl.flight_no, '') != ''")
		conditions.append("UPPER(TRIM(rl.flight_no)) = UPPER(TRIM(%(flight)s))")
		params["flight"] = flight_raw

		if _air_plan_value_nonempty(p, "airline"):
			# Match header *or* the Main leg used for the flight (leg often holds carrier when header is blank).
			params["airline"] = p["airline"]
			conditions.append(
				"(IFNULL(s.airline, '') = %(airline)s OR "
				"IFNULL(TRIM(rl.airline), '') = '' OR IFNULL(rl.airline, '') = %(airline)s)"
			)
		if _air_plan_value_nonempty(p, "origin_airport"):
			conditions.append(
				"(IFNULL(TRIM(rl.load_port), '') = '' OR rl.load_port = %(origin)s)"
			)
			if "origin" not in params:
				params["origin"] = p["origin_airport"]
		if _air_plan_value_nonempty(p, "destination_airport"):
			conditions.append(
				"(IFNULL(TRIM(rl.discharge_port), '') = '' OR rl.discharge_port = %(dest)s)"
			)
			if "dest" not in params:
				params["dest"] = p["destination_airport"]
	elif _air_plan_value_nonempty(p, "airline"):
		# No flight filter: carrier may be on the header or on any routing leg (not always Main).
		params["airline"] = p["airline"]
		conditions.append(
			"("
			"IFNULL(s.airline, '') = %(airline)s OR EXISTS ("
			"SELECT 1 FROM `tabAir Shipment Routing Leg` rl_a "
			"WHERE rl_a.parent = s.name AND rl_a.parenttype = 'Air Shipment' "
			"AND rl_a.parentfield = 'routing_legs' "
			"AND IFNULL(rl_a.airline, '') = %(airline)s)"
			")"
		)

	return join_sql, conditions, params


def count_filtered_air_shipments(plan: Union[Dict[str, Any], Any]) -> int:
	"""Number of Air Shipments matching optional filters in *plan*."""
	p = _plan_as_dict(plan)
	join_sql, conditions, params = _air_shipment_filter_parts(p)
	sql = (
		"SELECT COUNT(DISTINCT s.name) FROM `tabAir Shipment` s "
		+ join_sql
		+ " WHERE "
		+ " AND ".join(conditions)
	)
	row = frappe.db.sql(sql, params)
	return int(row[0][0]) if row else 0


def air_shipment_matches_plan_filter(shipment_name: str, plan: Union[Dict[str, Any], Any]) -> bool:
	"""True if *shipment_name* matches the same optional filters as :func:`get_filtered_air_shipment_names`."""
	p = _plan_as_dict(plan)
	join_sql, conditions, params = _air_shipment_filter_parts(p)
	params = dict(params)
	params["acm_match_name"] = shipment_name
	conditions = list(conditions) + ["s.name = %(acm_match_name)s"]
	sql = (
		"SELECT 1 FROM `tabAir Shipment` s "
		+ join_sql
		+ " WHERE "
		+ " AND ".join(conditions)
		+ " LIMIT 1"
	)
	return bool(frappe.db.sql(sql, params))


def get_filtered_air_shipment_names(
	plan: Union[Dict[str, Any], Any],
	*,
	offset: int = 0,
	limit: Optional[int] = None,
) -> List[str]:
	"""Match Air Shipments using only non-empty filter fields from *plan*.

	Unset criteria are ignored. When *flight_number* is set, a Main routing leg must match that
	flight (and optional leg airline / load / discharge rules consistent with other active filters).

	When *limit* is ``None``, no ``LIMIT`` is applied (e.g. bulk fetch on consolidation).
	Otherwise ``OFFSET`` / ``LIMIT`` implement paging (aligned shipments dialog).
	"""
	p = _plan_as_dict(plan)
	join_sql, conditions, params = _air_shipment_filter_parts(p)
	sql = (
		"SELECT DISTINCT s.name FROM `tabAir Shipment` s "
		+ join_sql
		+ " WHERE "
		+ " AND ".join(conditions)
		+ " ORDER BY s.name"
	)
	params = dict(params)
	if limit is not None:
		off = max(0, int(offset))
		lim = max(0, int(limit))
		sql += " LIMIT %(acm_limit)s OFFSET %(acm_offset)s"
		params["acm_limit"] = lim
		params["acm_offset"] = off
	rows = frappe.db.sql(sql, params, as_dict=False)
	return [r[0] for r in rows]


def get_strict_matching_air_shipment_names(plan: Union[Dict[str, Any], Any]) -> List[str]:
	"""Backward-compatible name for :func:`get_filtered_air_shipment_names` (no paging limit)."""
	return get_filtered_air_shipment_names(plan, limit=None)


def _sea_shipment_filter_parts(p: Dict[str, Any]) -> tuple[List[str], Dict[str, Any]]:
	"""WHERE fragments for optional sea alignment filters (*p* is a plain dict)."""
	conditions = [
		"s.docstatus != 2",
		"IFNULL(s.job_status, '') NOT IN ({0})".format(_SEA_PLAN_ALIGNMENT_JOB_STATUS_SQL_NOT_IN),
		"IFNULL(s.house_type, '') NOT IN ('Co-load Master', 'Blind Co-load Master')",
		"IFNULL(TRIM(s.load_type), '') != ''",
		"IFNULL(lt.can_be_consolidated, 0) = 1",
	]
	params: Dict[str, Any] = {}

	if _air_plan_value_nonempty(p, "company"):
		conditions.append("s.company = %(company)s")
		params["company"] = p["company"]
	if _air_plan_value_nonempty(p, "branch"):
		conditions.append("s.branch = %(branch)s")
		params["branch"] = p["branch"]
	if _air_plan_value_nonempty(p, "origin_port"):
		conditions.append("s.origin_port = %(origin)s")
		params["origin"] = p["origin_port"]
	if _air_plan_value_nonempty(p, "destination_port"):
		conditions.append("s.destination_port = %(dest)s")
		params["dest"] = p["destination_port"]
	if _air_plan_value_nonempty(p, "target_etd"):
		# Header ETD is often Datetime; Sea Shipment.etd is Date — compare calendar dates only.
		conditions.append("DATE(s.etd) = %(etd_date)s")
		params["etd_date"] = getdate(p["target_etd"])

	sl = (p.get("shipping_line") or "").strip()
	if sl:
		conditions.append("s.shipping_line = %(sl)s")
		conditions.append(
			"(IFNULL(mb.shipping_line, '') = '' OR IFNULL(mb.shipping_line, '') = %(sl)s)"
		)
		params["sl"] = sl
	vessel = (p.get("vessel_name") or "").strip()
	if vessel:
		conditions.append(
			"(IFNULL(TRIM(mb.vessel), '') = '' "
			"OR UPPER(TRIM(IFNULL(mb.vessel, ''))) = UPPER(TRIM(%(vessel)s)))"
		)
		params["vessel"] = vessel
	voyage = (p.get("voyage_number") or "").strip()
	if voyage:
		conditions.append(
			"(IFNULL(TRIM(mb.voyage_no), '') = '' "
			"OR UPPER(TRIM(IFNULL(mb.voyage_no, ''))) = UPPER(TRIM(%(voyage)s)))"
		)
		params["voyage"] = voyage

	return conditions, params


def get_strict_matching_sea_shipment_names(plan: Union[Dict[str, Any], Any]) -> List[str]:
	"""Match Sea Shipments using only non-empty filter fields from *plan* (aligned with air alignment).

	Carrier / vessel / voyage filters use the shipment header and linked Master Bill when set.
	Excludes cancelled/closed jobs and operational job statuses outside draft alignment.
	"""
	p = _plan_as_dict(plan)
	if not sea_alignment_plan_has_any_filter(p):
		return []

	conditions, params = _sea_shipment_filter_parts(p)
	sql = (
		"SELECT DISTINCT s.name FROM `tabSea Shipment` s "
		"INNER JOIN `tabLoad Type` lt ON lt.name = s.load_type "
		"LEFT JOIN `tabMaster Bill` mb ON mb.name = s.master_bill "
		"WHERE "
		+ " AND ".join(conditions)
		+ " ORDER BY s.name"
	)
	rows = frappe.db.sql(sql, params, as_dict=False)
	return [r[0] for r in rows]


def get_air_shipment_names_from_consolidation(doc) -> Set[str]:
	names: Set[str] = set()
	for row in doc.get("consolidation_packages") or []:
		if getattr(row, "air_freight_job", None):
			names.add(row.air_freight_job)
	return names


def get_sea_shipment_names_from_consolidation_cargo(doc) -> Set[str]:
	"""Sea Shipment names referenced by consolidation cargo only (packages + containers).

	Excludes ``attached_sea_shipments``, which is derived from packages and can retain
	stale rows after packages are removed (see Sea Consolidation ``on_update`` sync).
	"""
	names: Set[str] = set()
	for row in doc.get("consolidation_packages") or []:
		if getattr(row, "sea_shipment", None):
			names.add(row.sea_shipment)
	for row in doc.get("consolidation_containers") or []:
		if getattr(row, "sea_shipment", None):
			names.add(row.sea_shipment)
	return names


def get_sea_shipment_names_from_consolidation(doc) -> Set[str]:
	"""All distinct Sea Shipment names linked on the consolidation (cargo + attached table)."""
	names = get_sea_shipment_names_from_consolidation_cargo(doc)
	for row in doc.get("attached_sea_shipments") or []:
		if getattr(row, "sea_shipment", None):
			names.add(row.sea_shipment)
	return names


def get_distinct_air_planning_shipments(doc) -> Set[str]:
	return {
		getattr(r, "air_shipment", None)
		for r in (doc.get("consolidation_planning_lines") or [])
		if getattr(r, "air_shipment", None)
	}


def get_distinct_sea_planning_shipments(doc) -> Set[str]:
	return {
		getattr(r, "sea_shipment", None)
		for r in (doc.get("consolidation_planning_lines") or [])
		if getattr(r, "sea_shipment", None)
	}


def get_distinct_air_consolidation_shipments(doc) -> Set[str]:
	"""Distinct Air Shipments on cargo and planned shipment lines."""
	names = get_air_shipment_names_from_consolidation(doc)
	names.update(get_distinct_air_planning_shipments(doc))
	return names


def get_distinct_sea_consolidation_shipments(doc) -> Set[str]:
	"""Distinct Sea Shipments on cargo and planned shipment lines."""
	names = get_sea_shipment_names_from_consolidation_cargo(doc)
	names.update(get_distinct_sea_planning_shipments(doc))
	return names


def get_linked_sea_shipment_names_for_consolidation_tagging(doc) -> Set[str]:
	"""Sea Shipment names that should drive consolidation back-reference on save."""
	return get_distinct_sea_consolidation_shipments(doc)


def get_previous_linked_sea_shipment_names_for_consolidation(consolidation_name: str) -> Set[str]:
	"""Distinct Sea Shipment names linked on a consolidation before the current save."""
	if not consolidation_name:
		return set()
	names: Set[str] = set()
	for row in frappe.get_all(
		"Sea Consolidation Packages",
		filters={"parent": consolidation_name},
		pluck="sea_shipment",
	):
		if row:
			names.add(row)
	for row in frappe.get_all(
		"Sea Consolidation Containers",
		filters={"parent": consolidation_name},
		pluck="sea_shipment",
	):
		if row:
			names.add(row)
	for row in frappe.get_all(
		"Sea Consolidation Planning Line",
		filters={"parent": consolidation_name},
		pluck="sea_shipment",
	):
		if row:
			names.add(row)
	return names


def sea_shipment_can_be_consolidated(shipment_name: str) -> bool:
	"""True when the shipment's Load Type has Can be Consolidated enabled."""
	load_type = frappe.db.get_value("Sea Shipment", shipment_name, "load_type")
	if not load_type:
		return False
	return bool(frappe.db.get_value("Load Type", load_type, "can_be_consolidated"))


def sea_shipment_consolidation_load_type_message(shipment_name: str) -> str:
	"""User-facing reason when a Sea Shipment load type cannot join consolidation planning."""
	load_type = frappe.db.get_value("Sea Shipment", shipment_name, "load_type")
	if not load_type:
		return _("Sea Shipment {0} has no Load Type; only consolidatable load types can be added.").format(
			shipment_name
		)
	if not frappe.db.get_value("Load Type", load_type, "can_be_consolidated"):
		return _("Load Type {0} cannot be added to a consolidation plan.").format(load_type)
	return ""


@frappe.whitelist()
@frappe.validate_and_sanitize_search_inputs
def consolidatable_sea_shipment_query(
	doctype, txt, searchfield, start, page_len, filters, as_dict=False, **kwargs
):
	"""Link search: Sea Shipments whose Load Type has Can be Consolidated enabled."""
	_ = (as_dict, kwargs, doctype, searchfield)
	start = frappe.utils.cint(start)
	page_len = frappe.utils.cint(page_len) or 20
	txt = (txt or "").strip()
	params: Dict[str, Any] = {"start": start, "page_len": page_len}
	conditions = [
		"s.docstatus != 2",
		"IFNULL(s.house_type, '') NOT IN ('Co-load Master', 'Blind Co-load Master')",
		"IFNULL(TRIM(s.load_type), '') != ''",
		"IFNULL(lt.can_be_consolidated, 0) = 1",
	]
	if txt:
		conditions.append("(s.name LIKE %(txt)s OR s.house_bl LIKE %(txt)s)")
		params["txt"] = "%" + txt + "%"
	sql = """
		SELECT s.name
		FROM `tabSea Shipment` s
		INNER JOIN `tabLoad Type` lt ON lt.name = s.load_type
		WHERE {where}
		ORDER BY s.name ASC
		LIMIT %(start)s, %(page_len)s
	""".format(where=" AND ".join(conditions))
	return frappe.db.sql(sql, params)


def validate_minimum_air_planning_shipments(doc) -> None:
	"""Require at least two planned air shipments before submitting planning."""
	if len(get_distinct_air_planning_shipments(doc)) < MIN_CONSOLIDATION_SHIPMENT_COUNT:
		frappe.throw(
			_(
				"Select at least {0} distinct Air Shipments in planned shipments before submitting planning."
			).format(MIN_CONSOLIDATION_SHIPMENT_COUNT),
			title=_("Insufficient shipments"),
		)


def validate_minimum_sea_planning_shipments(doc) -> None:
	"""Require at least two planned sea shipments before submitting planning."""
	if len(get_distinct_sea_planning_shipments(doc)) < MIN_CONSOLIDATION_SHIPMENT_COUNT:
		frappe.throw(
			_(
				"Select at least {0} distinct Sea Shipments in planned shipments before submitting planning."
			).format(MIN_CONSOLIDATION_SHIPMENT_COUNT),
			title=_("Insufficient shipments"),
		)


def validate_minimum_air_consolidation_shipments(doc) -> None:
	"""Require at least two distinct air shipments before submitting the consolidation."""
	if len(get_distinct_air_consolidation_shipments(doc)) < MIN_CONSOLIDATION_SHIPMENT_COUNT:
		frappe.throw(
			_("An Air Consolidation must include at least two distinct Air Shipments."),
			title=_("Insufficient shipments"),
		)


def validate_minimum_sea_consolidation_shipments(doc) -> None:
	"""Require at least two distinct sea shipments before submitting the consolidation."""
	if len(get_distinct_sea_consolidation_shipments(doc)) < MIN_CONSOLIDATION_SHIPMENT_COUNT:
		frappe.throw(
			_("A Sea Consolidation must include at least two distinct Sea Shipments."),
			title=_("Insufficient shipments"),
		)


def sea_shipment_on_submitted_consolidation_planning(consolidation_name: str, shipment: str) -> bool:
	"""True if this consolidation has submitted planning and lists the shipment."""
	st = frappe.db.get_value(SEA_CONSOLIDATION, consolidation_name, "sea_planning_status")
	if st != "Submitted":
		return False
	return bool(
		frappe.db.exists(
			SEA_PLANNING_LINE,
			{"parent": consolidation_name, "sea_shipment": shipment},
		)
	)


def air_shipment_on_submitted_consolidation_planning(consolidation_name: str, shipment: str) -> bool:
	"""True if this Air Consolidation has submitted embedded planning and lists the shipment."""
	st = frappe.db.get_value(AIR_CONSOLIDATION, consolidation_name, "air_planning_status")
	if st != "Submitted":
		return False
	return bool(
		frappe.db.exists(
			AIR_PLANNING_LINE,
			{"parent": consolidation_name, "air_shipment": shipment},
		)
	)


def conflicting_submitted_air_planning_elsewhere(shipment: str, exclude_consolidation: Optional[str]) -> bool:
	"""True if another Air Consolidation (not exclude_consolidation) has submitted planning for this shipment."""
	rows = frappe.db.sql(
		"""
		SELECT pl.parent
		FROM `tabAir Consolidation Planning Line` pl
		INNER JOIN `tabAir Consolidation` c ON c.name = pl.parent
		WHERE pl.air_shipment = %(sh)s
			AND IFNULL(c.air_planning_status, '') = 'Submitted'
			AND IFNULL(c.docstatus, 0) != 2
		""",
		{"sh": shipment},
	)
	for (parent,) in rows:
		if exclude_consolidation and parent == exclude_consolidation:
			continue
		return True
	return False


def conflicting_submitted_sea_planning_elsewhere(shipment: str, exclude_consolidation: Optional[str]) -> bool:
	"""True if another consolidation (not exclude_consolidation) has submitted planning for this shipment."""
	rows = frappe.db.sql(
		"""
		SELECT pl.parent
		FROM `tabSea Consolidation Planning Line` pl
		INNER JOIN `tabSea Consolidation` c ON c.name = pl.parent
		WHERE pl.sea_shipment = %(sh)s
			AND IFNULL(c.sea_planning_status, '') = 'Submitted'
			AND IFNULL(c.docstatus, 0) != 2
		""",
		{"sh": shipment},
	)
	for (parent,) in rows:
		if exclude_consolidation and parent == exclude_consolidation:
			continue
		return True
	return False


def assert_air_consolidation_plan_requirements(doc) -> None:
	"""Cargo may reference air shipments only when they appear on this consolidation's planned shipment list.

	Draft planning: packages may mirror planned shipments like Sea Consolidation.
	Submitting the consolidation still requires Planning status = Submitted (see Air Consolidation.before_submit).
	"""
	consolidation_name = doc.get("name")
	if not consolidation_name:
		return
	shipments = get_air_shipment_names_from_consolidation(doc)
	if not shipments:
		return
	planned = {
		getattr(r, "air_shipment", None)
		for r in (doc.get("consolidation_planning_lines") or [])
		if getattr(r, "air_shipment", None)
	}
	for shipment in shipments:
		if shipment not in planned:
			frappe.throw(
				_(
					"Air Shipment {0} must be on this consolidation planned shipment list before it can be included in cargo."
				).format(shipment),
				title=_("Planning Required"),
			)


def assert_sea_consolidation_plan_requirements(doc) -> None:
	consolidation_name = doc.get("name")
	if not consolidation_name:
		return
	shipments = get_sea_shipment_names_from_consolidation_cargo(doc)
	if not shipments:
		return
	planned = {
		getattr(r, "sea_shipment", None)
		for r in (doc.get("consolidation_planning_lines") or [])
		if getattr(r, "sea_shipment", None)
	}
	for shipment in shipments:
		if shipment not in planned:
			frappe.throw(
				_(
					"Sea Shipment {0} must be on this consolidation planned shipment list before it can be included in cargo."
				).format(shipment),
				title=_("Planning Required"),
			)
		# Draft planning: cargo rows may mirror planned shipments (e.g. Aligned Sea Shipments).
		# Submitting the consolidation still requires Planning Status = Submitted (see Sea Consolidation.before_submit).


def sync_sea_plan_item_links(consolidation_doc) -> None:
	"""Legacy hook: sea planning lines live on Sea Consolidation; no external links to sync."""
	pass


def clear_sea_plan_links_for_consolidation(consolidation_name: str) -> None:
	"""Legacy hook: nothing to clear on separate plan rows."""
	pass


_CHILD_ROW_SNAPSHOT_IGNORE = frozenset(
	{
		"name",
		"owner",
		"creation",
		"modified",
		"modified_by",
		"parent",
		"parentfield",
		"parenttype",
		"idx",
		"docstatus",
		"__islocal",
		"__unsaved",
	}
)


def child_row_snapshot(row) -> tuple:
	data = row.as_dict() if hasattr(row, "as_dict") else dict(row)
	return tuple(sorted((k, data.get(k)) for k in data if k not in _CHILD_ROW_SNAPSHOT_IGNORE))


def cargo_tables_snapshot(doc, package_field: str = "consolidation_packages", container_field: str | None = "consolidation_containers"):
	packages = tuple(
		sorted(child_row_snapshot(r) for r in (doc.get(package_field) or []))
	)
	if not container_field:
		return (packages,)
	containers = tuple(
		sorted(child_row_snapshot(r) for r in (doc.get(container_field) or []))
	)
	return (packages, containers)


def prevent_consolidation_cargo_edit_when_planning_submitted(
	doc,
	*,
	planning_status_field: str,
	package_field: str = "consolidation_packages",
	container_field: str | None = "consolidation_containers",
	submitted_value: str = "Submitted",
) -> None:
	"""Block package/container grid changes while consolidation planning is submitted."""
	if getattr(doc.flags, "ignore_cargo_planning_lock", False):
		return
	if getattr(frappe.flags, "in_install", False) or getattr(frappe.flags, "in_migrate", False):
		return
	if getattr(frappe.flags, "in_import", False):
		return
	if doc.is_new():
		return
	if (doc.get(planning_status_field) or "Draft") != submitted_value:
		return
	prev = doc.get_doc_before_save()
	if not prev:
		return
	if cargo_tables_snapshot(prev, package_field, container_field) != cargo_tables_snapshot(
		doc, package_field, container_field
	):
		cargo_label = _("Packages and containers") if container_field else _("Packages")
		frappe.throw(
			_(
				"{0} cannot be changed while planning status is Submitted. "
				"Reset planned shipments to draft if you need to edit cargo."
			).format(cargo_label),
			title=_("Cargo locked"),
		)


def get_previous_planning_line_shipments(doc, shipment_field: str) -> Set[str]:
	"""Shipment names already on planning lines before this save (unchanged rows)."""
	prev = doc.get_doc_before_save()
	if not prev:
		return set()
	return {
		getattr(r, shipment_field, None)
		for r in (prev.get("consolidation_planning_lines") or [])
		if getattr(r, shipment_field, None)
	}


def _job_status_blocks_new_plan_line(job_status: str, *, retain_existing: bool) -> bool:
	"""Block excluded statuses for new plan lines; keep Submitted jobs already on the list."""
	if job_status not in _SEA_PLAN_ALIGNMENT_EXCLUDED_JOB_STATUSES:
		return False
	if retain_existing and job_status == "Submitted":
		return False
	return True


def air_shipment_allowed_on_plan(shipment_name: str, *, retain_existing: bool = False) -> tuple[bool, str]:
	if not frappe.db.exists("Air Shipment", shipment_name):
		return False, _("Air Shipment {0} does not exist").format(shipment_name)
	row = frappe.db.get_value(
		"Air Shipment",
		shipment_name,
		["job_status", "house_type"],
		as_dict=True,
	)
	if not row:
		return False, _("Air Shipment {0} does not exist").format(shipment_name)
	js = row.get("job_status") or ""
	if _job_status_blocks_new_plan_line(js, retain_existing=retain_existing):
		return False, _("Job status {0} cannot be added to consolidation planning.").format(js or "-")
	ht = row.get("house_type") or ""
	if ht in _INELIGIBLE_AIR_HOUSE:
		return False, _("House type {0} cannot be added to a consolidation plan").format(ht or "-")
	return True, ""


def sea_shipment_allowed_on_plan(shipment_name: str, *, retain_existing: bool = False) -> tuple[bool, str]:
	row = frappe.db.get_value(
		"Sea Shipment",
		shipment_name,
		["job_status", "house_type"],
		as_dict=True,
	)
	if not row:
		return False, _("Sea Shipment {0} does not exist").format(shipment_name)
	js = row.get("job_status") or ""
	if _job_status_blocks_new_plan_line(js, retain_existing=retain_existing):
		return False, _("Job status {0} cannot be added to consolidation planning.").format(js or "-")
	ht = row.get("house_type") or ""
	if ht in _INELIGIBLE_SEA_HOUSE:
		return False, _("House type {0} cannot be added to a consolidation plan").format(ht or "-")
	if not sea_shipment_can_be_consolidated(shipment_name):
		return False, sea_shipment_consolidation_load_type_message(shipment_name)
	return True, ""

