# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Link existing header WIP/accrual JEs to charge rows (per-line recognition indicators)."""

from __future__ import unicode_literals

import frappe


def execute():
	"""Set wip_recognition_journal_entry / accrual_recognition_journal_entry on charge rows from parent header."""
	mapping = (
		("Air Shipment", "Air Shipment Charges"),
		("Sea Shipment", "Sea Shipment Charges"),
		("Transport Job", "Transport Job Charges"),
		("Warehouse Job", "Warehouse Job Charges"),
		("Declaration", "Declaration Charges"),
	)

	for parent_dt, child_dt in mapping:
		if not frappe.db.table_exists(child_dt):
			continue
		meta = frappe.get_meta(child_dt)
		if not meta.has_field("wip_recognition_journal_entry") and not meta.has_field(
			"accrual_recognition_journal_entry"
		):
			continue

		pmeta = frappe.get_meta(parent_dt)
		parent_je_fields = []
		if pmeta.has_field("wip_journal_entry"):
			parent_je_fields.append("wip_journal_entry")
		if pmeta.has_field("accrual_journal_entry"):
			parent_je_fields.append("accrual_journal_entry")
		if not parent_je_fields:
			continue

		parent_names = set()
		for _fn in parent_je_fields:
			for _n in frappe.get_all(parent_dt, filters={_fn: ["is", "set"]}, pluck="name"):
				parent_names.add(_n)
		for pname in parent_names:
			row = frappe.db.get_value(parent_dt, pname, parent_je_fields, as_dict=True) or {}
			wip_je = row.get("wip_journal_entry")
			acc_je = row.get("accrual_journal_entry")
			for cname in frappe.get_all(
				child_dt,
				filters={"parent": pname, "parenttype": parent_dt},
				pluck="name",
			):
				if meta.has_field("wip_recognition_journal_entry") and wip_je:
					cur = frappe.db.get_value(child_dt, cname, "wip_recognition_journal_entry")
					if not cur:
						frappe.db.set_value(
							child_dt,
							cname,
							"wip_recognition_journal_entry",
							wip_je,
							update_modified=False,
						)
				if meta.has_field("accrual_recognition_journal_entry") and acc_je:
					cur = frappe.db.get_value(child_dt, cname, "accrual_recognition_journal_entry")
					if not cur:
						frappe.db.set_value(
							child_dt,
							cname,
							"accrual_recognition_journal_entry",
							acc_je,
							update_modified=False,
						)

	frappe.db.commit()
