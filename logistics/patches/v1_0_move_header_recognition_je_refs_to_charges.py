# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt

"""
Before model sync: add charge-row JE link columns if missing, copy values from parent job
so they survive removal of wip_adjustment_journal_entry / accrual_journal_entry /
accrual_adjustment_journal_entry from job doctypes.
"""

from __future__ import unicode_literals

import frappe
from frappe.utils import get_table_name


def _add_link_column_if_missing(doctype, fieldname):
	if frappe.db.has_column(doctype, fieldname):
		return
	table = get_table_name(doctype)
	frappe.db.sql_ddl(
		"""ALTER TABLE `{}` ADD COLUMN `{}` varchar(140) DEFAULT NULL""".format(table, fieldname)
	)


def execute():
	parent_child = (
		("Air Shipment", "Air Shipment Charges", "charges"),
		("Sea Shipment", "Sea Shipment Charges", "charges"),
		("Transport Job", "Transport Job Charges", "charges"),
		("Warehouse Job", "Warehouse Job Charges", "charges"),
		("Declaration", "Declaration Charges", "charges"),
	)

	for _parent_dt, child_dt, _field in parent_child:
		if not frappe.db.table_exists(child_dt):
			continue
		_add_link_column_if_missing(child_dt, "wip_adjustment_journal_entry")
		_add_link_column_if_missing(child_dt, "accrual_adjustment_journal_entry")

	for parent_dt, child_dt, _ in parent_child:
		if not frappe.db.table_exists(parent_dt) or not frappe.db.table_exists(child_dt):
			continue
		parent_tab = get_table_name(parent_dt)
		child_tab = get_table_name(child_dt)

		if frappe.db.has_column(parent_dt, "wip_adjustment_journal_entry"):
			frappe.db.sql(
				"""
				UPDATE `{child}` c
				INNER JOIN `{parent}` p ON p.name = c.parent AND c.parenttype = %(pt)s
				SET c.wip_adjustment_journal_entry = p.wip_adjustment_journal_entry
				WHERE IFNULL(c.wip_adjustment_journal_entry, '') = ''
				  AND IFNULL(p.wip_adjustment_journal_entry, '') != ''
				  AND IFNULL(c.wip_recognition_journal_entry, '') != ''
				""".format(child=child_tab, parent=parent_tab),
				{"pt": parent_dt},
			)

		if frappe.db.has_column(parent_dt, "accrual_adjustment_journal_entry"):
			frappe.db.sql(
				"""
				UPDATE `{child}` c
				INNER JOIN `{parent}` p ON p.name = c.parent AND c.parenttype = %(pt)s
				SET c.accrual_adjustment_journal_entry = p.accrual_adjustment_journal_entry
				WHERE IFNULL(c.accrual_adjustment_journal_entry, '') = ''
				  AND IFNULL(p.accrual_adjustment_journal_entry, '') != ''
				  AND IFNULL(c.accrual_recognition_journal_entry, '') != ''
				""".format(child=child_tab, parent=parent_tab),
				{"pt": parent_dt},
			)

		if frappe.db.has_column(parent_dt, "accrual_journal_entry"):
			frappe.db.sql(
				"""
				UPDATE `{child}` c
				INNER JOIN `{parent}` p ON p.name = c.parent AND c.parenttype = %(pt)s
				SET c.accrual_recognition_journal_entry = p.accrual_journal_entry
				WHERE IFNULL(c.accrual_recognition_journal_entry, '') = ''
				  AND IFNULL(p.accrual_journal_entry, '') != ''
				""".format(child=child_tab, parent=parent_tab),
				{"pt": parent_dt},
			)

	frappe.db.commit()
