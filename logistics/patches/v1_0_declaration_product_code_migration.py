# Migrate Commercial Invoice Line Items to use Declaration Product Code
# For existing rows with product_code (old Link to Item), create or get Declaration Product Code
# and set declaration_product_code + item
from __future__ import unicode_literals

import frappe


def execute():
	if not frappe.db.table_exists("Declaration Product Code"):
		return

	# Get all Commercial Invoice Line Item rows that have product_code (old Item link) but no declaration_product_code
	rows = frappe.db.sql(
		"""
		SELECT name, parent, parenttype, product_code
		FROM `tabCommercial Invoice Line Item`
		WHERE product_code IS NOT NULL AND product_code != ''
		AND (declaration_product_code IS NULL OR declaration_product_code = '')
		""",
		as_dict=1,
	)

	for row in rows:
		item_code = row.product_code
		if not item_code or not frappe.db.exists("Item", item_code):
			continue

		# Get or create Declaration Product Code (item, importer=blank, exporter=blank)
		dp_code = _get_or_create_declaration_product_code(item_code)
		if dp_code:
			frappe.db.set_value(
				"Commercial Invoice Line Item",
				row.name,
				{"declaration_product_code": dp_code, "item": item_code},
				update_modified=False,
			)

	frappe.db.commit()


def _get_or_create_declaration_product_code(item_code):
	"""Get or create Declaration Product Code for item with blank importer/exporter."""
	existing = frappe.db.sql(
		"""
		SELECT name FROM `tabDeclaration Product Code`
		WHERE item_code = %s AND (importer IS NULL OR importer = '') AND (exporter IS NULL OR exporter = '')
		LIMIT 1
		""",
		item_code,
		as_dict=1,
	)
	if existing:
		return existing[0].name

	doc = frappe.new_doc("Declaration Product Code")
	doc.item_code = item_code
	doc.product_code = item_code
	doc.importer = ""
	doc.exporter = ""
	doc.insert(ignore_permissions=True)
	return doc.name
