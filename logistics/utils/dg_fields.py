# Copyright (c) 2026, www.agilasoft.com and contributors
# For license information, please see license.txt
"""Standard dangerous-goods field names shared across freight and transport documents."""

import frappe
from frappe import _

# Parent-level: same fieldname on Air/Sea Shipment, Air/Sea Booking, Transport Order, Transport Job.
PARENT_DG_FLAG = "contains_dangerous_goods"
PARENT_DG_FIELDS = (
	"dg_declaration_complete",
	"dg_compliance_status",
	"dg_emergency_contact",
	"dg_emergency_phone",
	"dg_emergency_email",
)

# Package/line-level: copy when present on source row and on target child DocType meta.
PACKAGE_DG_FIELDS = (
	"contains_dangerous_goods",
	"dg_substance",
	"un_number",
	"proper_shipping_name",
	"dg_class",
	"packing_group",
	"dg_division",
	"subsidiary_risks",
	"packing_instruction",
	"net_quantity_per_package",
	"flash_point",
	"emergency_contact_name",
	"emergency_contact_phone",
	"emergency_contact_email",
	"handling_instructions",
	"segregation_requirements",
	"special_provisions",
	"transport_mode_restrictions",
	"erg_code",
	"environmental_hazards",
	"temp_controlled",
	"min_temperature",
	"max_temperature",
	"is_radioactive",
	"transport_index",
	"radiation_level",
	"criticality_safety_index",
	"shippers_declaration_status",
	"dg_declaration_number",
	"additional_handling_instructions",
)

# Any of these on a package row counts as “this line has DG data” for validation and copying flags.
PACKAGE_DG_INDICATOR_FIELDS = (
	"dg_substance",
	"un_number",
	"proper_shipping_name",
	"dg_class",
	"packing_group",
)


def package_indicates_dangerous_goods(pkg):
	"""True if the package row has any dangerous-goods identification filled in."""
	return any(getattr(pkg, fn, None) for fn in PACKAGE_DG_INDICATOR_FIELDS)


def dg_child_row_display_label(pkg, commodity_doctype="Commodity"):
	"""Readable label for DG validation messages (row index + commodity description or goods text)."""
	idx = getattr(pkg, "idx", None)
	row_part = _("Row {0}").format(idx) if idx else _("Package")
	commodity = getattr(pkg, "commodity", None)
	if commodity:
		lookup = frappe.db.get_value(
			commodity_doctype,
			commodity,
			("description", "code"),
			as_dict=True,
		)
		if lookup:
			detail = (lookup.description or "").strip() or (lookup.code or "").strip() or str(commodity)
		else:
			detail = str(commodity)
		return _("{0}: {1}").format(row_part, detail[:200])
	gd = (getattr(pkg, "goods_description", None) or "").strip()
	if gd:
		line = gd.split("\n", 1)[0].strip()[:200]
		return _("{0}: {1}").format(row_part, line)
	return row_part


def copy_parent_dg_header(source, target):
	"""Copy parent-level DG fields from source to target (freight ↔ transport)."""
	if hasattr(target, PARENT_DG_FLAG) and hasattr(source, PARENT_DG_FLAG):
		v = getattr(source, PARENT_DG_FLAG, None)
		if v is not None:
			setattr(target, PARENT_DG_FLAG, int(v) if v else 0)
	for fn in PARENT_DG_FIELDS:
		if hasattr(target, fn) and hasattr(source, fn):
			v = getattr(source, fn, None)
			if v is not None and v != "":
				setattr(target, fn, v)


def transport_order_package_row_from_shipment_pkg(shipment, pkg):
	"""Build a Transport Order Package dict from an Air Shipment Packages or Sea Freight Packages row."""
	to_meta = frappe.get_meta("Transport Order Package")
	common = (
		"commodity",
		"description",
		"uom",
		"no_of_packs",
		"weight",
		"weight_uom",
		"volume",
		"volume_uom",
		"length",
		"width",
		"height",
		"dimension_uom",
		"goods_description",
		"hs_code",
		"reference_no",
	)
	row = {}
	for f in common:
		if to_meta.has_field(f) and hasattr(pkg, f) and getattr(pkg, f) is not None:
			row[f] = getattr(pkg, f)
	for f in PACKAGE_DG_FIELDS:
		if f == "contains_dangerous_goods":
			continue
		if to_meta.has_field(f) and hasattr(pkg, f) and getattr(pkg, f) is not None:
			row[f] = getattr(pkg, f)
	if to_meta.has_field("contains_dangerous_goods"):
		parent_dg = bool(getattr(shipment, "contains_dangerous_goods", 0))
		line_dg = package_indicates_dangerous_goods(pkg)
		if parent_dg or line_dg:
			row["contains_dangerous_goods"] = 1
	return row
