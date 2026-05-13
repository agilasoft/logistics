# Copyright (c) 2026, AgilaSoft and contributors
# See license.txt

"""Merge legacy Air Consolidation Plan rows into Air Consolidation before Plan DocTypes are removed."""

import frappe
from frappe import _
from frappe.utils import get_datetime, get_time, getdate, today


def execute():
	if not frappe.db.table_exists("Air Consolidation Plan"):
		return

	_merge_linked_plan_lines_into_consolidations()
	_create_consolidations_from_orphan_submitted_plans()
	frappe.db.commit()
	frappe.db.sql("DELETE FROM `tabAir Consolidation Plan Item`")
	frappe.db.sql("DELETE FROM `tabAir Consolidation Plan`")
	frappe.db.commit()


def _merge_linked_plan_lines_into_consolidations():
	for row in frappe.db.sql(
		"""
		SELECT DISTINCT pi.linked_air_consolidation AS name
		FROM `tabAir Consolidation Plan Item` pi
		WHERE IFNULL(pi.linked_air_consolidation, '') != ''
		""",
		as_dict=True,
	):
		name = row.name
		if not frappe.db.exists("Air Consolidation", name):
			continue
		doc = frappe.get_doc("Air Consolidation", name)
		existing = {r.air_shipment for r in doc.get("consolidation_planning_lines") or []}
		submitted_any = False
		lines_changed = False
		for item in frappe.db.sql(
			"""
			SELECT pi.air_shipment AS air_shipment, p.docstatus AS plan_docstatus
			FROM `tabAir Consolidation Plan Item` pi
			INNER JOIN `tabAir Consolidation Plan` p ON p.name = pi.parent
			WHERE pi.linked_air_consolidation = %(c)s
			""",
			{"c": name},
			as_dict=True,
		):
			if item.plan_docstatus == 1:
				submitted_any = True
			sh = item.air_shipment
			if sh and sh not in existing:
				doc.append("consolidation_planning_lines", {"air_shipment": sh})
				existing.add(sh)
				lines_changed = True
		need_planning_status_submitted = submitted_any and (doc.air_planning_status or "Draft") != "Submitted"
		if lines_changed:
			doc.flags.ignore_validate = True
			doc.flags.ignore_validate_update_after_submit = True
			doc.save(ignore_permissions=True)
		if need_planning_status_submitted:
			frappe.db.set_value(
				"Air Consolidation",
				name,
				"air_planning_status",
				"Submitted",
				update_modified=True,
			)


def _create_consolidations_from_orphan_submitted_plans():
	for pname in frappe.get_all(
		"Air Consolidation Plan",
		filters={"docstatus": 1},
		pluck="name",
	):
		has_link = frappe.db.sql(
			"""
			SELECT 1 FROM `tabAir Consolidation Plan Item`
			WHERE parent = %s AND IFNULL(linked_air_consolidation, '') != ''
			LIMIT 1
			""",
			pname,
		)
		if has_link:
			continue
		fields = [
			"company",
			"branch",
			"plan_date",
			"consolidation_type",
			"origin_airport",
			"destination_airport",
			"target_departure",
			"target_arrival",
			"airline",
			"flight_number",
		]
		plan_row = frappe.db.get_value("Air Consolidation Plan", pname, fields, as_dict=True)
		if not plan_row:
			continue
		items = frappe.get_all(
			"Air Consolidation Plan Item",
			filters={"parent": pname},
			fields=["air_shipment"],
			order_by="idx asc",
		)
		consol = _build_air_consolidation_from_plan_data(plan_row, items)
		consol.insert(ignore_permissions=True)


def _build_air_consolidation_from_plan_data(plan, items):
	settings = None
	try:
		from logistics.air_freight.doctype.air_freight_settings.air_freight_settings import AirFreightSettings

		settings = AirFreightSettings.get_settings(plan["company"])
	except Exception:
		pass

	cc = plan["company"]
	cost_center = getattr(settings, "default_cost_center", None) if settings else None
	profit_center = getattr(settings, "default_profit_center", None) if settings else None
	if not cost_center:
		frappe.throw(_("Set default Cost Center in Air Freight Settings for company {0}.").format(cc))
	if not profit_center:
		frappe.throw(_("Set default Profit Center in Air Freight Settings for company {0}.").format(cc))

	def _split_dt(val):
		if not val:
			d = getdate(today())
			return d, "00:00:00"
		dt = get_datetime(val)
		return getdate(dt), get_time(dt).strftime("%H:%M:%S")

	dep_d, dep_t = _split_dt(plan.get("target_departure"))
	arr_d, arr_t = _split_dt(plan.get("target_arrival"))

	consol = frappe.new_doc("Air Consolidation")
	consol.naming_series = "AFC.########"
	consol.consolidation_date = getdate(plan.get("plan_date")) or getdate(today())
	consol.consolidation_type = plan.get("consolidation_type")
	consol.status = "Draft"
	consol.company = cc
	consol.branch = plan.get("branch")
	consol.cost_center = cost_center
	consol.profit_center = profit_center
	consol.origin_airport = plan.get("origin_airport")
	consol.destination_airport = plan.get("destination_airport")
	consol.departure_date = dep_d
	consol.arrival_date = arr_d
	consol.airline = plan.get("airline")
	consol.flight_number = plan.get("flight_number") or "TBA"

	consol.append(
		"consolidation_routes",
		{
			"route_type": "Direct",
			"origin_airport": plan.get("origin_airport"),
			"destination_airport": plan.get("destination_airport"),
			"airline": plan.get("airline"),
			"flight_number": plan.get("flight_number") or "TBA",
			"departure_date": dep_d,
			"departure_time": dep_t,
			"arrival_date": arr_d,
			"arrival_time": arr_t,
			"dangerous_goods_allowed": 1,
		},
	)

	consol.air_planning_status = "Submitted"
	consol.planning_owner = frappe.session.user

	idx = 0
	for line in items or []:
		sh = line.get("air_shipment")
		if not sh:
			continue
		idx += 1
		consol.append("consolidation_planning_lines", {"air_shipment": sh})
		s = frappe.get_doc("Air Shipment", sh)
		pkg_ref = f"{sh}-{idx}"
		consol.append(
			"consolidation_packages",
			{
				"package_reference": pkg_ref,
				"air_freight_job": sh,
				"shipper": s.shipper,
				"consignee": s.consignee,
				"package_type": "Box",
				"package_count": 1,
				"package_weight": s.total_weight or s.chargeable or 1,
				"package_volume": s.total_volume or 0,
			},
		)

	return consol
