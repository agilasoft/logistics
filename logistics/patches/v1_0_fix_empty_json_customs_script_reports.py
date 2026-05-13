# Copyright (c) 2026, Agilasoft Cloud Technologies Inc. and contributors
# Script Report fixtures without `json` left NULL/empty in DB; Report view JSON.parse fails.

import frappe


def execute():
	frappe.db.sql(
		"""
		UPDATE `tabReport`
		SET `json` = '{}'
		WHERE `module` = 'Customs'
			AND `report_type` = 'Script Report'
			AND (`json` IS NULL OR TRIM(IFNULL(`json`, '')) = '')
		"""
	)
	frappe.db.commit()
