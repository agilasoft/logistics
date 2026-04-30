# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and Contributors
# See license.txt
"""Backfill `Cargo Terminal Operator.served_unlocs` from distinct (sea_cto, port) on Shipping Line CTO."""

import frappe
from collections import defaultdict


def execute():
	rows = frappe.db.sql(
		"""
		SELECT DISTINCT slc.sea_cto, slc.port
		FROM `tabShipping Line CTO` slc
		WHERE IFNULL(slc.sea_cto, '') != ''
		AND IFNULL(slc.port, '') != ''
		""",
	)
	if not rows:
		return
	by_cto: dict[str, list[str]] = defaultdict(list)
	for sea_cto, port in rows:
		by_cto[sea_cto].append(port)
	for cto_name, ports in by_cto.items():
		if not frappe.db.exists("Cargo Terminal Operator", cto_name):
			continue
		doc = frappe.get_doc("Cargo Terminal Operator", cto_name)
		existing = {(r.unloco or "").strip() for r in (doc.served_unlocs or []) if (r.unloco or "").strip()}
		changed = False
		for p in ports:
			p = (p or "").strip()
			if p and p not in existing:
				doc.append("served_unlocs", {"unloco": p})
				existing.add(p)
				changed = True
		if changed:
			doc.save(ignore_permissions=True)
	frappe.db.commit()
