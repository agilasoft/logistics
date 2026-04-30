# Copyright (c) 2026, Agilasoft and contributors
# Licensed under the MIT License. See license.txt

"""Before schema sync removes ``Exchange Rate Source Rate``, snapshot its rows for Source Exchange Rate migration."""

import frappe


def execute():
	"""Create `_tmp_ersr_mig` if the legacy child table still exists and backup is not there yet."""
	if not frappe.db.table_exists("tabExchange Rate Source Rate"):
		return
	if frappe.db.table_exists("_tmp_ersr_mig"):
		return
	frappe.db.sql(
		"CREATE TABLE `_tmp_ersr_mig` AS SELECT * FROM `tabExchange Rate Source Rate`"
	)
	frappe.db.commit()
