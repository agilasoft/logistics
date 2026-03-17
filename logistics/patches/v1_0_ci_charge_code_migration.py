# Create CI Charge Code records and migrate Commercial Invoice Charges
from __future__ import unicode_literals

import frappe


DEFAULT_CHARGE_CODES = [
	("ADD", "Other Additional Charges"),
	("COM", "Commission"),
	("DED", "Other Deduction Charges"),
	("DIS", "Discount"),
	("EXW", "Ex-Works Amount"),
	("FIF", "Foreign Inland Freight"),
	("LCH", "Landing Charges (Local Charges)"),
	("OFT", "International Freight"),
	("ONS", "International Insurance"),
	("OTH", "Other Charges"),
]


def execute():
	if not frappe.db.table_exists("CI Charge Code"):
		return

	# Create default CI Charge Code records
	for code, description in DEFAULT_CHARGE_CODES:
		if not frappe.db.exists("CI Charge Code", code):
			doc = frappe.new_doc("CI Charge Code")
			doc.code = code
			doc.description = description
			doc.insert(ignore_permissions=True)

	# Migrate existing Commercial Invoice Charges: map old charge_code to CI Charge Code
	# Old format was Select with values like "ADD: Other Additional Charges" or "ADD"
	rows = frappe.db.sql(
		"""
		SELECT name, charge_code
		FROM `tabCommercial Invoice Charges`
		WHERE charge_code IS NOT NULL AND charge_code != ''
		""",
		as_dict=1,
	)

	for row in rows:
		old_val = row.charge_code
		# Extract code: "ADD: Other Additional Charges" -> "ADD", or "ADD" -> "ADD"
		new_code = old_val.split(":")[0].strip() if ":" in old_val else old_val.strip()
		if frappe.db.exists("CI Charge Code", new_code):
			frappe.db.set_value(
				"Commercial Invoice Charges",
				row.name,
				"charge_code",
				new_code,
				update_modified=False,
			)

	frappe.db.commit()
