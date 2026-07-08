# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Install Client Script records from JSON fixtures under pricing_center/client_scripts/."""

from __future__ import unicode_literals

import json
import os

import frappe


def sync_pricing_center_client_scripts():
	"""Upsert Client Scripts shipped as JSON in pricing_center/client_scripts/."""
	base_dir = os.path.join(
		frappe.get_app_path("logistics"),
		"pricing_center",
		"client_scripts",
	)
	if not os.path.isdir(base_dir):
		return

	for filename in sorted(os.listdir(base_dir)):
		if not filename.endswith(".json"):
			continue
		path = os.path.join(base_dir, filename)
		with open(path, encoding="utf-8") as handle:
			data = json.load(handle)
		data["doctype"] = "Client Script"
		name = data.get("name")
		if not name:
			frappe.log_error(f"Client Script fixture missing name: {path}", "Pricing Center Client Scripts")
			continue
		if frappe.db.exists("Client Script", name):
			doc = frappe.get_doc("Client Script", name)
			doc.update(data)
			doc.save(ignore_permissions=True)
		else:
			frappe.get_doc(data).insert(ignore_permissions=True)

	frappe.clear_cache(doctype="Client Script")
