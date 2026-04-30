# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and contributors
# Report list view (doctype/view/report/...) calls JSON.parse on Report.json.
# Script Report fixtures often omit `json`, leaving NULL/empty values and a blank page + console error.

import frappe


def execute():
	frappe.db.sql(
		"""
		UPDATE `tabReport`
		SET `json` = '{}'
		WHERE `json` IS NULL OR TRIM(IFNULL(`json`, '')) = ''
		"""
	)
	frappe.db.commit()
