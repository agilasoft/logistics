# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and Contributors
# See license.txt
"""Backfill Freight Agent.covered_unlocs from default_unloco."""

import frappe


def execute():
	rows = frappe.db.sql(
		"""
		SELECT name, default_unloco
		FROM `tabFreight Agent`
		WHERE IFNULL(default_unloco, '') != ''
		""",
	)
	if not rows:
		return

	for name, default_unloco in rows:
		default_unloco = (default_unloco or "").strip()
		if not default_unloco:
			continue
		existing = {
			(r.unloco or "").strip()
			for r in frappe.get_all(
				"Freight Agent Covered Location",
				filters={
					"parent": name,
					"parenttype": "Freight Agent",
					"parentfield": "covered_unlocs",
				},
				fields=["unloco"],
			)
			if (r.get("unloco") or "").strip()
		}
		if default_unloco in existing:
			continue
		doc = frappe.get_doc("Freight Agent", name)
		doc.append("covered_unlocs", {"unloco": default_unloco})
		doc.save(ignore_permissions=True)

	frappe.db.commit()
