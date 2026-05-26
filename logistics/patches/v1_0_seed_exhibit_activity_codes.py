# Copyright (c) 2026, Agilasoft and contributors
# For license information, please see license.txt

"""Seed standard Exhibit activity codes linked to lifecycle stages."""

from __future__ import annotations

import frappe
from frappe.modules.import_file import import_file_by_path


STAGE_DESCRIPTIONS = {
	"Pre-Show": "We handle everything before the show opens.",
	"Logistics": "Coordinated freight to get everything there on time.",
	"On-Site": "Professional supervision during the event.",
	"Post-Show": "We take care of everything after the show closes.",
}

# stage, code, name, sort_order, photo_required, description
EXHIBIT_ACTIVITY_CODES = (
	(
		"Pre-Show",
		"asset_retrieval",
		"Asset Retrieval",
		1,
		1,
		"Your exhibits pulled from our secure, climate-controlled storage facility.",
	),
	(
		"Pre-Show",
		"staging_qc",
		"Staging & QC",
		2,
		1,
		"Professional staging with photo documentation for quality assurance.",
	),
	(
		"Pre-Show",
		"refurbishment",
		"Refurbishment",
		3,
		0,
		"Any needed repairs or graphic updates completed before shipping.",
	),
	(
		"Logistics",
		"freight_coordination",
		"Freight Coordination",
		1,
		0,
		"Carrier selection, label creation, and advanced warehouse shipping.",
	),
	(
		"Logistics",
		"real_time_tracking",
		"Real-Time Tracking",
		2,
		0,
		"Live shipment updates and proactive exception handling.",
	),
	(
		"Logistics",
		"venue_delivery",
		"Venue Delivery",
		3,
		0,
		"Direct-to-show floor delivery coordinated with show management.",
	),
	(
		"On-Site",
		"installation_supervision",
		"Installation Supervision",
		1,
		0,
		"On-site project manager coordinates I&D, labor, and vendors.",
	),
	(
		"On-Site",
		"quality_control",
		"Quality Control",
		2,
		0,
		"Final inspection and real-time issue resolution.",
	),
	(
		"On-Site",
		"documentation",
		"Documentation",
		3,
		1,
		"Photo documentation of installed booth for your records.",
	),
	(
		"Post-Show",
		"dismantle_supervision",
		"Dismantle Supervision",
		1,
		0,
		"Coordinated teardown with labor and freight partners.",
	),
	(
		"Post-Show",
		"return_shipping",
		"Return Shipping",
		2,
		0,
		"Exhibits shipped back to our warehouse facility.",
	),
	(
		"Post-Show",
		"storage_reporting",
		"Storage & Reporting",
		3,
		0,
		"Assets inspected, stored, and available for your next event.",
	),
)


def execute():
	path = frappe.get_app_path(
		"logistics",
		"exhibits",
		"doctype",
		"activity_code",
		"activity_code.json",
	)
	if frappe.db.exists("DocType", "Activity Code"):
		import_file_by_path(path, force=True, ignore_version=True, reset_permissions=True)

	for stage, description in STAGE_DESCRIPTIONS.items():
		if frappe.db.exists("Lifecycle Stage", stage):
			frappe.db.set_value(
				"Lifecycle Stage",
				stage,
				"description",
				description,
				update_modified=False,
			)

	for stage, code, name, sort_order, photo_required, description in EXHIBIT_ACTIVITY_CODES:
		if not frappe.db.exists("Lifecycle Stage", stage):
			continue
		values = {
			"activity_name": name,
			"lifecycle_stage": stage,
			"sort_order": sort_order,
			"description": description,
			"photo_required": photo_required,
			"for_exhibits": 1,
			"for_special_project": 0,
		}
		if frappe.db.exists("Activity Code", code):
			frappe.db.set_value("Activity Code", code, values, update_modified=False)
			continue
		doc = frappe.new_doc("Activity Code")
		doc.activity_code = code
		doc.update(values)
		doc.insert(ignore_permissions=True)

	frappe.db.commit()
