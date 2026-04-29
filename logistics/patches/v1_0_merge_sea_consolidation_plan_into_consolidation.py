# Copyright (c) 2026, AgilaSoft and contributors
# See license.txt

import frappe


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
		changed = False
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
				changed = True
		if submitted_any and doc.sea_planning_status != "Submitted":
			doc.sea_planning_status = "Submitted"
			changed = True
		if changed:
			doc.flags.ignore_validate = True
			doc.save(ignore_permissions=True)


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
		plan = frappe.get_doc("Sea Consolidation Plan", pname)
		plan.create_sea_consolidation_from_plan()
