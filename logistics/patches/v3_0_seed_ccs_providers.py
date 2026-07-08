# Copyright (c) 2026, www.agilasoft.com and contributors
# See license.txt

from __future__ import unicode_literals

import frappe


PROVIDERS = (
	{
		"provider_code": "CHAMP_TRAXON",
		"provider_name": "CHAMP TRAXON cargoHUB",
		"connector_type": "champ_traxon",
		"description": "Global air cargo community hub for Cargo-XML and Cargo-IMP messaging.",
		"protocol": "HTTP REST",
		"requires_pima_routing": 1,
		"documentation_url": "https://www.champ.aero/products/ecargo/traxon-cargohub",
	},
	{
		"provider_code": "WISE",
		"provider_name": "WiseTech Global CCS",
		"connector_type": "wise",
		"description": "WiseTech cargo community connectivity for e-AWB and airline messaging.",
		"protocol": "HTTP REST",
		"requires_pima_routing": 1,
	},
	{
		"provider_code": "DESCARTES",
		"provider_name": "Descartes GLN",
		"connector_type": "descartes",
		"description": "Descartes Global Logistics Network for air cargo EDI.",
		"protocol": "HTTP REST",
		"requires_pima_routing": 1,
	},
	{
		"provider_code": "CCNHUB",
		"provider_name": "CCNhub",
		"connector_type": "ccnhub",
		"description": "IATA-sponsored cargo community hub for e-freight participants.",
		"protocol": "HTTP REST",
		"requires_pima_routing": 1,
	},
	{
		"provider_code": "CUSTOM",
		"provider_name": "Custom CCS Provider",
		"connector_type": "generic",
		"description": "Generic connector for a private or regional Cargo Community System.",
		"protocol": "HTTP REST",
		"requires_pima_routing": 1,
	},
)


def execute():
	if not frappe.db.exists("DocType", "CCS Provider"):
		return

	for row in PROVIDERS:
		if frappe.db.exists("CCS Provider", row["provider_code"]):
			doc = frappe.get_doc("CCS Provider", row["provider_code"])
			for key, value in row.items():
				setattr(doc, key, value)
			doc.is_active = 1
			doc.flags.ignore_permissions = True
			doc.save(ignore_permissions=True)
			continue

		doc = frappe.get_doc({"doctype": "CCS Provider", **row, "is_active": 1})
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)

	frappe.db.commit()
	print("Seeded CCS Provider master records.")
