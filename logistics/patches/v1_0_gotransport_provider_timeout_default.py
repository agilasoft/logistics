# Copyright (c) 2026 Agilasoft. All rights reserved.
"""Normalize timeout on existing GoTransport-typed Telematics Provider records.

The GoTransport AI integration brief requires ``request_timeout_sec >= 15`` —
0 (the Frappe Int default) is treated as "undefined" by the GoTransport
provider and falls back to its own default. This patch raises any pre-existing
GoTransport provider record that's still at 0/NULL/<15 up to 15 seconds so
the first poll after upgrade behaves correctly.
"""

import frappe


def execute():
	if not frappe.db.table_exists("Telematics Provider"):
		return

	rows = frappe.db.sql(
		"""
		select name, ifnull(request_timeout_sec, 0) as timeout
		from   `tabTelematics Provider`
		where  provider_type = 'GOTRANSPORT'
		""",
		as_dict=True,
	)
	updated = 0
	for r in rows:
		if int(r.get("timeout") or 0) >= 15:
			continue
		frappe.db.set_value(
			"Telematics Provider", r["name"], "request_timeout_sec", 15,
			update_modified=False,
		)
		updated += 1
	if updated:
		frappe.db.commit()
		frappe.logger().info(
			"v1_0_gotransport_provider_timeout_default: bumped request_timeout_sec to 15 on %d record(s)",
			updated,
		)
