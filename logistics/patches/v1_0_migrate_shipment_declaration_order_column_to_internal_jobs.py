# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Move legacy shipment.declaration_order link into internal_job_details before the column is dropped."""

import frappe

from logistics.utils.internal_job_detail_copy import (
	get_declaration_order_job_no_from_shipment_doc,
	link_declaration_order_on_shipment,
)


def execute():
	for dt in ("Sea Shipment", "Air Shipment"):
		if not frappe.db.has_column(dt, "declaration_order"):
			continue
		rows = frappe.get_all(
			dt,
			filters={"declaration_order": ["is", "set"]},
			fields=["name", "declaration_order"],
		)
		for r in rows:
			col_do = (r.declaration_order or "").strip()
			if not col_do:
				continue
			try:
				doc = frappe.get_doc(dt, r.name)
			except Exception:
				continue
			if get_declaration_order_job_no_from_shipment_doc(doc):
				frappe.db.set_value(dt, r.name, "declaration_order", None)
				continue
			link_declaration_order_on_shipment(dt, r.name, col_do)
			frappe.db.set_value(dt, r.name, "declaration_order", None)
	frappe.db.commit()
