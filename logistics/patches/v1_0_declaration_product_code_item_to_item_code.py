# Migrate Declaration Product Code: item (Link) -> item_code (Data) before schema sync
# Copy item to item_code so model sync can safely replace the field
from __future__ import unicode_literals

import frappe


def execute():
	if not frappe.db.table_exists("Declaration Product Code"):
		return

	columns = [c.get("Field") for c in frappe.db.sql("SHOW COLUMNS FROM `tabDeclaration Product Code`", as_dict=1)]
	if "item" in columns and "item_code" not in columns:
		frappe.db.sql("ALTER TABLE `tabDeclaration Product Code` ADD COLUMN item_code VARCHAR(140)")
		frappe.db.sql("UPDATE `tabDeclaration Product Code` SET item_code = item WHERE item IS NOT NULL")
	frappe.db.commit()
