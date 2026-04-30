# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

import frappe
from frappe.utils import get_table_name

# Align Sales Quote Charge / Change Request Charge / Cost Sheet Charge service_type with Load Type module keys.
_SERVICE_TYPE_MAP = (
	("Air", "air"),
	("Sea", "sea"),
	("Transport", "transport"),
	("Customs", "custom"),
	("Warehousing", "warehousing"),
)


def execute():
	for doctype in ("Sales Quote Charge", "Change Request Charge", "Cost Sheet Charge"):
		if not frappe.db.exists("DocType", doctype):
			continue
		table = get_table_name(doctype)
		for old, new in _SERVICE_TYPE_MAP:
			frappe.db.sql(
				"UPDATE `{}` SET `service_type`=%s WHERE `service_type`=%s".format(table),
				(new, old),
			)
