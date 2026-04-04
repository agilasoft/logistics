import frappe


def execute():
	"""Migrate Customs Authority records to Issuing Authority and ensure links remain valid."""
	if not frappe.db.table_exists("Customs Authority"):
		return
	if not frappe.db.table_exists("Issuing Authority"):
		return

	customs_rows = frappe.get_all(
		"Customs Authority",
		fields=[
			"name",
			"code",
			"customs_authority_name",
			"country",
			"is_active",
			"website",
			"phone",
			"email",
			"address_line_1",
			"address_line_2",
			"city",
			"state",
			"postal_code",
		],
	)

	for row in customs_rows:
		code = row.get("code") or row.get("name")
		exists = frappe.db.exists("Issuing Authority", code)
		if exists:
			continue
		doc = frappe.get_doc(
			{
				"doctype": "Issuing Authority",
				"code": code,
				"customs_authority_name": row.get("customs_authority_name") or row.get("name"),
				"country": row.get("country"),
				"is_active": 1 if row.get("is_active") is None else row.get("is_active"),
				"website": row.get("website"),
				"phone": row.get("phone"),
				"email": row.get("email"),
				"address_line_1": row.get("address_line_1"),
				"address_line_2": row.get("address_line_2"),
				"city": row.get("city"),
				"state": row.get("state"),
				"postal_code": row.get("postal_code"),
			}
		)
		doc.insert(ignore_permissions=True, ignore_if_duplicate=True)

	# Touch Permit Application links so they resolve to Issuing Authority
	if frappe.db.table_exists("Permit Application"):
		for pa in frappe.get_all("Permit Application", fields=["name", "issuing_authority"]):
			if not pa.issuing_authority:
				continue
			# If an Issuing Authority with that name exists, leave as-is
			if frappe.db.exists("Issuing Authority", pa.issuing_authority):
				continue
			# If there is a Customs Authority row with that code but no Issuing Authority, try to create it on-the-fly
			if frappe.db.exists("Customs Authority", pa.issuing_authority) and not frappe.db.exists(
				"Issuing Authority", pa.issuing_authority
			):
				src = frappe.get_doc("Customs Authority", pa.issuing_authority)
				doc = frappe.get_doc(
					{
						"doctype": "Issuing Authority",
						"code": src.code or src.name,
						"customs_authority_name": src.customs_authority_name or src.name,
						"country": src.country,
						"is_active": 1 if src.is_active is None else src.is_active,
						"website": src.website,
						"phone": src.phone,
						"email": src.email,
						"address_line_1": src.address_line_1,
						"address_line_2": src.address_line_2,
						"city": src.city,
						"state": src.state,
						"postal_code": src.postal_code,
					}
				)
				doc.insert(ignore_permissions=True, ignore_if_duplicate=True)
