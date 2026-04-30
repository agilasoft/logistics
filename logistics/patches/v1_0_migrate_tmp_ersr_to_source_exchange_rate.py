# Copyright (c) 2026, Agilasoft and contributors
# Licensed under the MIT License. See license.txt

"""Insert **Source Exchange Rate** from pre-sync backup table ``_tmp_ersr_mig`` and drop the backup."""

import frappe
from frappe.utils import getdate, today


def execute():
	if not frappe.db.table_exists("tabSource Exchange Rate"):
		return
	if not frappe.db.table_exists("_tmp_ersr_mig"):
		return

	rows = frappe.db.sql("SELECT * FROM `_tmp_ersr_mig`", as_dict=True)
	for r in rows:
		parent = r.get("parent")
		currency = r.get("currency")
		rate = r.get("rate")
		if not parent or not currency or rate is None:
			continue
		d = r.get("valid_from") or r.get("valid_to")
		if not d:
			d = today()
		d = getdate(d)
		if frappe.db.sql(
			"""
			SELECT name FROM `tabSource Exchange Rate`
			WHERE exchange_rate_source=%s AND currency=%s AND date=%s
			LIMIT 1
			""",
			(parent, currency, d),
		):
			continue
		doc = frappe.get_doc(
			{
				"doctype": "Source Exchange Rate",
				"exchange_rate_source": parent,
				"currency": currency,
				"exchange_rate": rate,
				"date": d,
			}
		)
		doc.insert(ignore_permissions=True)

	frappe.db.sql_ddl("DROP TABLE IF EXISTS `_tmp_ersr_mig`")
	frappe.db.commit()
