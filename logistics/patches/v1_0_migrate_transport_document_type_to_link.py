# Migrate Declaration Order / Declaration transport_document_type from Select to Link.
# Creates Transport Document Type master rows and assigns them to all active Customs Transport Modes.
from __future__ import unicode_literals

import frappe


STANDARD_LABELS = [
	"Bill of Lading",
	"Air Waybill",
	"CMR",
	"Railway Bill",
	"Courier Receipt",
	"Other",
]


def _customs_transport_modes():
	modes = frappe.get_all(
		"Transport Mode",
		filters={"customs": 1, "is_active": 1},
		pluck="name",
	)
	if modes:
		return modes
	return frappe.get_all("Transport Mode", filters={"is_active": 1}, pluck="name") or []


def _ensure_transport_document_type(document_type_name, mode_names):
	if not mode_names:
		return
	if frappe.db.exists("Transport Document Type", document_type_name):
		doc = frappe.get_doc("Transport Document Type", document_type_name)
	else:
		doc = frappe.new_doc("Transport Document Type")
		doc.document_type_name = document_type_name

	existing = {r.transport_mode for r in (doc.transport_modes or [])}
	for m in mode_names:
		if m not in existing:
			doc.append("transport_modes", {"transport_mode": m})
	doc.save(ignore_permissions=True)


def _is_rail_mode(row):
	mn = (row.get("mode_name") or "").lower()
	mc = (row.get("mode_code") or "").lower()
	return "rail" in mn or mc in ("rail", "railway", "rai")


def execute():
	if not frappe.db.exists("DocType", "Transport Document Type"):
		return

	mode_names = _customs_transport_modes()
	if not mode_names:
		return

	labels = set(STANDARD_LABELS)
	for t in frappe.db.sql(
		"""
		SELECT DISTINCT transport_document_type FROM `tabDeclaration Order`
		WHERE IFNULL(transport_document_type,'') != ''
		UNION
		SELECT DISTINCT transport_document_type FROM `tabDeclaration`
		WHERE IFNULL(transport_document_type,'') != ''
		"""
	):
		if t and t[0]:
			labels.add(t[0])

	for label in sorted(labels):
		_ensure_transport_document_type(label, mode_names)

	railway_name = "Railway Bill"
	if frappe.db.exists("Transport Document Type", railway_name):
		for row in frappe.get_all("Transport Mode", fields=["name", "mode_name", "mode_code"]):
			if _is_rail_mode(row):
				frappe.db.set_value(
					"Transport Mode",
					row.name,
					"default_transport_document_type",
					railway_name,
					update_modified=False,
				)

	frappe.db.commit()
