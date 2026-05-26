# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""Special Project: remove legacy Billings child rows; backfill Company for Charges tab."""

import frappe


def execute():
	if frappe.db.table_exists("tabSpecial Project Billing"):
		frappe.db.sql(
			"DELETE FROM `tabSpecial Project Billing` WHERE parenttype = %s",
			("Special Project",),
		)

	gd_co = frappe.db.get_single_value("Global Defaults", "default_company")
	rows = frappe.db.sql(
		"SELECT name, project, company FROM `tabSpecial Project` WHERE IFNULL(company,'') = ''",
		as_dict=True,
	)
	for row in rows or []:
		co = row.get("company")
		if not co and row.get("project"):
			co = frappe.db.get_value("Project", row.project, "company")
		if not co and gd_co:
			co = gd_co
		if co:
			frappe.db.set_value("Special Project", row.name, "company", co, update_modified=False)

	for row in frappe.db.sql(
		"""SELECT sp.name, sp.company FROM `tabSpecial Project` sp
		WHERE IFNULL(sp.cost_center,'') = '' AND IFNULL(sp.company,'') != ''""",
		as_dict=True,
	):
		cc = frappe.db.get_value("Company", row.company, "cost_center")
		if cc:
			frappe.db.set_value("Special Project", row.name, "cost_center", cc, update_modified=False)
