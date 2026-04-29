# Copyright (c) 2026, AgilaSoft and contributors
# See license.txt

import frappe
from frappe import _
from frappe.utils import getdate, today


def execute():
	if not frappe.db.table_exists("Sea Consolidation Plan"):
		return

	_merge_linked_plan_lines_into_consolidations()
	_create_consolidations_from_orphan_submitted_plans()
	frappe.db.commit()
	frappe.db.sql("DELETE FROM `tabSea Consolidation Plan Item`")
	frappe.db.sql("DELETE FROM `tabSea Consolidation Plan`")
	frappe.db.commit()


def _merge_linked_plan_lines_into_consolidations():
	for row in frappe.db.sql(
		"""
		SELECT DISTINCT pi.linked_sea_consolidation AS name
		FROM `tabSea Consolidation Plan Item` pi
		WHERE IFNULL(pi.linked_sea_consolidation, '') != ''
		""",
		as_dict=True,
	):
		name = row.name
		if not frappe.db.exists("Sea Consolidation", name):
			continue
		doc = frappe.get_doc("Sea Consolidation", name)
		existing = {r.sea_shipment for r in doc.get("consolidation_planning_lines") or []}
		submitted_any = False
		lines_changed = False
		for item in frappe.db.sql(
			"""
			SELECT pi.sea_shipment AS sea_shipment, p.docstatus AS plan_docstatus
			FROM `tabSea Consolidation Plan Item` pi
			INNER JOIN `tabSea Consolidation Plan` p ON p.name = pi.parent
			WHERE pi.linked_sea_consolidation = %(c)s
			""",
			{"c": name},
			as_dict=True,
		):
			if item.plan_docstatus == 1:
				submitted_any = True
			sh = item.sea_shipment
			if sh and sh not in existing:
				doc.append("consolidation_planning_lines", {"sea_shipment": sh})
				existing.add(sh)
				lines_changed = True
		need_planning_status_submitted = submitted_any and (doc.sea_planning_status or "Draft") != "Submitted"
		if lines_changed:
			doc.flags.ignore_validate = True
			doc.flags.ignore_validate_update_after_submit = True
			doc.save(ignore_permissions=True)
		# Avoid UpdateAfterSubmitError on read-only `sea_planning_status`: apply after save via DB.
		if need_planning_status_submitted:
			frappe.db.set_value(
				"Sea Consolidation",
				name,
				"sea_planning_status",
				"Submitted",
				update_modified=True,
			)


def _create_consolidations_from_orphan_submitted_plans():
	for pname in frappe.get_all(
		"Sea Consolidation Plan",
		filters={"docstatus": 1},
		pluck="name",
	):
		has_link = frappe.db.sql(
			"""
			SELECT 1 FROM `tabSea Consolidation Plan Item`
			WHERE parent = %s AND IFNULL(linked_sea_consolidation, '') != ''
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
			"origin_port",
			"destination_port",
			"target_etd",
			"target_eta",
			"shipping_line",
			"vessel_name",
			"voyage_number",
		]
		plan_row = frappe.db.get_value("Sea Consolidation Plan", pname, fields, as_dict=True)
		if not plan_row:
			continue
		items = frappe.get_all(
			"Sea Consolidation Plan Item",
			filters={"parent": pname},
			fields=["sea_shipment"],
			order_by="idx asc",
		)
		consol = _build_sea_consolidation_from_plan_data(plan_row, items)
		consol.insert(ignore_permissions=True)


def _build_sea_consolidation_from_plan_data(plan, items):
	"""Recreate logic from removed Sea Consolidation Plan.create_sea_consolidation_from_plan (see git history)."""
	from logistics.sea_freight.doctype.sea_freight_settings.sea_freight_settings import SeaFreightSettings

	ss = SeaFreightSettings.get_settings(plan["company"])
	cost_center = ss.default_cost_center if ss else None
	profit_center = ss.default_profit_center if ss else None
	if not cost_center:
		frappe.throw(_("Set Default Cost Center in Sea Freight Settings for company {0}.").format(plan["company"]))
	if not profit_center:
		frappe.throw(_("Set Default Profit Center in Sea Freight Settings for company {0}.").format(plan["company"]))

	consol = frappe.new_doc("Sea Consolidation")
	consol.naming_series = "SC-{MM}-{YYYY}-{####}"
	consol.consolidation_date = getdate(plan.get("plan_date")) or getdate(today())
	consol.consolidation_type = plan.get("consolidation_type")
	consol.status = "Draft"
	consol.company = plan.get("company")
	consol.branch = plan.get("branch")
	consol.cost_center = cost_center
	consol.profit_center = profit_center
	consol.origin_port = plan.get("origin_port")
	consol.destination_port = plan.get("destination_port")
	consol.etd = plan.get("target_etd")
	consol.eta = plan.get("target_eta")
	consol.shipping_line = plan.get("shipping_line")
	consol.vessel_name = plan.get("vessel_name") or "TBA"
	consol.voyage_number = plan.get("voyage_number") or "TBA"

	consol.append(
		"consolidation_routes",
		{
			"route_type": "Direct",
			"origin_port": plan.get("origin_port"),
			"destination_port": plan.get("destination_port"),
			"shipping_line": plan.get("shipping_line"),
			"vessel_name": plan.get("vessel_name") or "TBA",
			"voyage_number": plan.get("voyage_number") or "TBA",
			"etd": plan.get("target_etd"),
			"eta": plan.get("target_eta"),
			"dangerous_goods_allowed": 1,
		},
	)

	for line in items or []:
		sh = line.get("sea_shipment")
		if sh:
			consol.append(
				"consolidation_planning_lines",
				{"sea_shipment": sh},
			)
	consol.sea_planning_status = "Submitted"

	idx = 0
	for line in items or []:
		idx += 1
		sh = line.get("sea_shipment")
		if not sh:
			continue
		s = frappe.get_doc("Sea Shipment", sh)
		pkg_ref = f"{sh}-{idx}"
		consol.append(
			"consolidation_packages",
			{
				"package_reference": pkg_ref,
				"sea_shipment": sh,
				"shipper": s.shipper,
				"consignee": s.consignee,
				"package_type": "Box",
				"package_count": 1,
				"package_weight": s.total_weight or 1,
				"package_volume": s.total_volume or 0,
			},
		)

	return consol
